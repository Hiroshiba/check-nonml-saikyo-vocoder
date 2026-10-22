"""Layer0編集のUTMOSと、同じ全長範囲にそろえたECAPAだけを追加評価する。"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import sys
import traceback

import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
import torch

from scripts.apron_fixed120.common import (MANIFEST_SHA256, bind_run, input_cases,
                                           latest_attempt, new_attempt, now, read,
                                           require_threads, sha, source_hashes, versions, write)
from scripts.apron_fixed120.quality import asset_options
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli
from vocoderbench.quality_backends import EcapaSimilarity, UtmosLocal
from vocoderbench.quality_core import offline_environment

from .common import (CONDITIONS, FULL_ECAPA, driver_hashes, file_record,
                     original_native, separate_output, supplemental_native, write_new)


BACKENDS = {'utmosv2': UtmosLocal, 'ecapa': EcapaSimilarity}


def expected(metric: str) -> tuple:
    return CONDITIONS if metric == 'utmosv2' else FULL_ECAPA


def original_quality(root: Path, cases: list, owner: int, metric: str,
                     native_contract_sha: str, native_rows: dict, assets: dict):
    contract_path = root / 'contract.json'
    contract = read(contract_path)
    original_conditions = ('apron_0', 'apron_minus3', 'apron_plus3', 'llsm2_0')
    if (contract.get('kind') != 'apron_fixed120_quality'
            or contract.get('owner') != owner or contract.get('metric') != metric
            or contract.get('case_ids') != [case['id'] for case in cases]
            or contract.get('conditions') != list(original_conditions)
            or contract.get('input_manifest_sha256') != MANIFEST_SHA256
            or contract.get('native_contract_sha256') != native_contract_sha
            or contract.get('assets') != assets
            or contract.get('source_hashes') != source_hashes()
            or contract.get('runtime_versions') != versions()):
        raise ValueError(f'元{metric}品質の資産・入力・source/runtimeが不一致です')
    required = (('apron_0', 'apron_minus3', 'apron_plus3', 'llsm2_0')
                if metric == 'utmosv2' else ('apron_minus3', 'apron_plus3'))
    refs = {}
    for case in cases:
        attempt, row = latest_attempt(root, case['id'])
        if (attempt is None or row is None or row.get('status') != 'measured'
                or row.get('case') != case['id'] or row.get('metric') != metric):
            raise ValueError(f'元{metric}の完了個票がありません: {case["id"]}')
        items = {item['condition']: item for item in row.get('rows', [])}
        if (len(items) != 4 or len(row['rows']) != 4
                or set(items) != set(original_conditions)):
            raise ValueError(f'元{metric}の条件が不正です: {case["id"]}')
        if (metric == 'ecapa' and any(items[name].get('scope') !=
                'frozen_common_16k_prefix' for name in ('apron_0', 'llsm2_0'))):
            raise ValueError(f'元無編集ECAPAの先頭区間契約が違います: {case["id"]}')
        refs[case['id']] = {'result': file_record(attempt / 'result.json'), 'rows': {}}
        for name in required:
            item = items[name]
            scope = ('native_full_length' if metric == 'utmosv2'
                     else 'edited_full_length')
            wave_sha = native_rows[case['id']]['branches'][name]['output']['sha256']
            if (item.get('status') != 'measured' or not np.isfinite(item['value'])
                    or item.get('scope') != scope
                    or item.get('native_output_sha256') != wave_sha):
                raise ValueError(f'元{metric}の範囲・波形・値が不一致です: {case["id"]} {name}')
            refs[case['id']]['rows'][name] = {
                'value': item['value'], 'scope': scope,
                'native_output_sha256': wave_sha,
                'evaluated_samples': item['evaluated_samples'],
                'output_pcm_float64_sha256': item['output_pcm_float64_sha256']}
    provenance = root / 'model-provenance.json'
    if not provenance.is_file():
        raise ValueError(f'元{metric}の実モデル来歴がありません: {provenance}')
    return contract_path, provenance, refs


def load_wave(root: Path, case_id: str, branch: dict):
    item = branch['output']
    path = root / 'cases' / case_id / item['path']
    if (not path.is_file() or path.stat().st_size != item['bytes']
            or sha(path) != item['sha256']):
        raise ValueError(f'波形の原bytes/SHAが不一致です: {path}')
    wave = np.load(path, allow_pickle=False)
    if (wave.ndim != 1 or len(wave) != item['samples']
            or item['sample_rate'] != 24000
            or wave.dtype not in (np.dtype('float32'), np.dtype('float64'))
            or not np.isfinite(wave).all()):
        raise ValueError(f'波形のヘッダー・有限性が不一致です: {path}')
    return wave


def pcm_sha(wave) -> str:
    return hashlib.sha256(np.asarray(wave, dtype='<f8').tobytes()).hexdigest()


def evaluate(case: dict, name: str, metric: str, old_rows: dict,
             new_rows: dict, old_root: Path, new_root: Path, backend):
    entry = {'case': case['id'], 'speaker': case['speaker'],
             'method': 'apron' if name == 'apron_0' else 'llsm2',
             'condition': name, 'metric': metric, 'status': 'pending',
             'value': None, 'common_samples': case['common_samples']}
    source = old_rows[case['id']] if name in ('apron_0', 'llsm2_0') else new_rows[case['id']]
    branch = source.get('branches', {}).get(name, {})
    if source.get('status') != 'measured' or branch.get('status') != 'measured':
        return {**entry, 'status': 'upstream_failed',
                'reason': branch.get('error', '補助nativeが未完了です')}
    try:
        native_root = old_root if name in ('apron_0', 'llsm2_0') else new_root
        y = load_wave(native_root, case['id'], branch)
        entry['native_output_sha256'] = branch['output']['sha256']
        entry['native_output_samples'] = len(y)
        if metric == 'utmosv2':
            value, detail = backend.score(None, y, 24000)
            entry.update(scope='native_full_length', output_samples=len(y),
                         reference_samples=None, output_pcm_float64_sha256=pcm_sha(y))
            evaluated = len(y)
        else:
            x = np.load(case['absolute_input'], allow_pickle=False)
            if x.ndim != 1 or not np.isfinite(x).all():
                raise ValueError('参照入力が単一チャンネルの有限値ではありません')
            y16 = resample_poly(y.astype(np.float64), 2, 3)
            if not np.isfinite(y16).all():
                raise ValueError('16 kHz変換後の波形が非有限です')
            value, detail = backend.score(x, y16, 16000)
            entry.update(scope='edited_full_length', reference_samples=len(x),
                         output_samples=len(y16),
                         reference_pcm_float64_sha256=pcm_sha(x),
                         output_pcm_float64_sha256=pcm_sha(y16))
            evaluated = len(y16)
        if not np.isfinite(value):
            raise ValueError('品質値が非有限です')
        return {**entry, 'status': 'measured', 'value': float(value), 'detail': detail,
                'evaluated_samples': evaluated,
                'evaluated_sample_rate': 24000 if metric == 'utmosv2' else 16000,
                'reference': 'none' if metric == 'utmosv2' else 'fixed_original_full_excerpt'}
    except Exception as error:
        logging.exception('補助品質個票が失敗しました: %s %s %s', case['id'], name, metric)
        return {**entry, 'status': 'failed',
                'reason': f'{type(error).__name__}: {error}',
                'traceback': traceback.format_exc()}


def measure_case(case, output, metric, old_rows, new_rows, old_root, new_root,
                 backend, init_error, retry):
    attempt, old = latest_attempt(output, case['id'])
    if attempt is not None:
        if old is None and not retry:
            raise ValueError(f'中断記録の再開には--retry-failedが必要です: {attempt}')
        if old is not None and (old['status'] == 'measured' or not retry):
            if old.get('case') != case['id'] or old.get('metric') != metric:
                raise ValueError(f'保存済み品質個票の録音・指標が違います: {case["id"]}')
            items = old.get('rows', [])
            if old['status'] == 'measured' and (
                    len(items) != len(expected(metric))
                    or {item['condition'] for item in items} != set(expected(metric))
                    or any(item['status'] != 'measured' or not np.isfinite(item['value'])
                           for item in items)):
                raise ValueError(f'保存済み品質値が不正です: {case["id"]}')
            return old
    attempt = new_attempt(output, case['id'])
    row = {'schema_version': 1, 'case': case['id'], 'metric': metric,
           'started_at_utc': now(), 'rows': []}
    write_new(attempt / 'start.json', row)
    for name in expected(metric):
        item = ({'case': case['id'], 'condition': name, 'metric': metric,
                 'status': 'failed', 'value': None,
                 'reason': 'model_initialization_failed', 'traceback': init_error}
                if init_error else None)
        if item is None:
            with offline_environment():
                item = evaluate(case, name, metric, old_rows, new_rows,
                                old_root, new_root, backend)
        row['rows'].append(item)
        write_new(attempt / f'{name}.json', item)
    row['status'] = ('measured' if all(item['status'] == 'measured' for item in row['rows'])
                     else 'complete_with_missing')
    row['finished_at_utc'] = now()
    write_new(attempt / 'result.json', row)
    return row


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, required=True)
    parser.add_argument('--original-native', type=Path, required=True)
    parser.add_argument('--supplement-native', type=Path, required=True)
    parser.add_argument('--original-utm', type=Path, required=True)
    parser.add_argument('--original-ecapa', type=Path, required=True)
    parser.add_argument('--owner', type=int, choices=(0, 1, 2), required=True)
    parser.add_argument('--metric', choices=BACKENDS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    require_threads(2)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cases = input_cases(args.input_manifest, args.input_root, args.owner)
    old_contract, old_contract_data, old_rows, old_refs = original_native(
        args.original_native, cases, args.owner)
    new_contract, new_rows = supplemental_native(
        args.supplement_native, cases, args.owner, sha(old_contract))
    new_contract_data = read(new_contract)
    if (new_contract_data.get('base') != old_contract_data['base']
            or new_contract_data.get('original_references') != old_refs):
        raise ValueError('補助nativeと元実行のbuild・個票参照が一致しません')
    assets, options = asset_options(args.asset_root, args.metric)
    utm_contract, utm_provenance, utm_refs = original_quality(
        args.original_utm, cases, args.owner, 'utmosv2', sha(old_contract),
        old_rows, asset_options(args.asset_root, 'utmosv2')[0])
    ecapa_contract, ecapa_provenance, ecapa_refs = original_quality(
        args.original_ecapa, cases, args.owner, 'ecapa', sha(old_contract),
        old_rows, asset_options(args.asset_root, 'ecapa')[0])
    output = separate_output(args.output, args.input_root, args.asset_root,
                             args.original_native, args.supplement_native,
                             args.original_utm, args.original_ecapa, args.input_manifest)
    contract = {'schema_version': 1, 'kind': 'apron_pitch_control_quality',
                'owner': args.owner, 'metric': args.metric,
                'case_ids': [case['id'] for case in cases],
                'conditions': list(expected(args.metric)),
                'planned_values': len(cases) * len(expected(args.metric)),
                'input_manifest_sha256': MANIFEST_SHA256,
                'original_native_contract_sha256': sha(old_contract),
                'supplement_native_contract_sha256': sha(new_contract),
                'original_utm_contract_sha256': sha(utm_contract),
                'original_ecapa_contract_sha256': sha(ecapa_contract),
                'original_utm_provenance_sha256': sha(utm_provenance),
                'original_ecapa_provenance_sha256': sha(ecapa_provenance),
                'original_native_references': old_refs,
                'original_utm_references': utm_refs,
                'original_ecapa_references': ecapa_refs,
                'input_root': str(args.input_root.resolve()),
                'original_native_root': str(args.original_native.resolve()),
                'supplement_native_root': str(args.supplement_native.resolve()),
                'assets': assets, 'source_hashes': source_hashes(),
                'driver_hashes': driver_hashes('quality'), 'runtime_versions': versions(),
                'quality_threads': 2, 'scope': 'native_full_length' if args.metric == 'utmosv2'
                           else 'edited_full_length'}
    bind_run(output, contract)
    backend = None
    init_error = None
    rows = []
    with threadpool_limits(limits=2):
        try:
            with offline_environment():
                backend = BACKENDS[args.metric](options, args.asset_root,
                                                output / 'work', 2)
            old_provenance = utm_provenance if args.metric == 'utmosv2' else ecapa_provenance
            if backend.provenance != read(old_provenance):
                raise ValueError('実モデル来歴が元品質実行と一致しません')
            provenance = output / 'model-provenance.json'
            if provenance.exists():
                if read(provenance) != backend.provenance:
                    raise ValueError('補助実行のモデル来歴が以前と一致しません')
            else:
                write_new(provenance, backend.provenance)
        except Exception:
            logging.exception('補助品質モデルの初期化・来歴照合に失敗しました')
            init_error = traceback.format_exc()
            write_new(output / f'initialization-failure-{now().replace(":", "-")}.json',
                      {'error': init_error, 'at_utc': now()})
        for case in cases:
            rows.append(measure_case(case, output, args.metric, old_rows, new_rows,
                                     args.original_native, args.supplement_native,
                                     backend, init_error, args.retry_failed))
            measured = [item for row in rows for item in row.get('rows', [])]
            write(output / 'summary.json', {
                'schema_version': 1, 'owner': args.owner, 'metric': args.metric,
                'planned_cases': len(cases),
                'planned_values': len(cases) * len(expected(args.metric)),
                'finished_cases': len(rows),
                'measured_values': sum(item['status'] == 'measured' for item in measured),
                'missing_values': sum(item['status'] != 'measured' for item in measured),
                'not_run_values': len(cases) * len(expected(args.metric)) - len(measured),
                'rows': [{'case': case['id'], 'status': next(
                    (row['status'] for row in rows if row['case'] == case['id']), 'not_run')}
                    for case in cases]})
    return 0 if all(row['status'] == 'measured' for row in rows) else 2


if __name__ == '__main__':
    sys.exit(run_cli(main, 'apron-pitch-control-quality'))
