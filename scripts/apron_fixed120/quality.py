"""保存済みnative波形だけを固定4指標で評価する。"""
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

from vocoderbench.extended_metrics import _estoi
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli
from vocoderbench.quality_backends import EcapaSimilarity, ScoreqReference, UtmosLocal
from vocoderbench.quality_core import offline_environment

from .common import (ASSET_SHA256, CONDITIONS, MANIFEST_SHA256, bind_run,
                     input_cases, latest_attempt, new_attempt, now, read, require_threads, sha,
                     source_hashes, versions, write)


METRICS = ('utmosv2', 'ecapa', 'scoreq', 'estoi')
MODEL_CLASSES = {'utmosv2': UtmosLocal, 'ecapa': EcapaSimilarity,
                 'scoreq': ScoreqReference}


def expected_conditions(metric):
    return CONDITIONS if metric in ('utmosv2', 'ecapa') else ('apron_0', 'llsm2_0')


def asset_options(asset_root: Path, metric: str):
    paths = {'utmosv2': ('mos/weights/fold0_s42_best_model.pth',
                         'mos/wav2vec2_config/config.json',
                         'mos/wav2vec2_config/preprocessor_config.json'),
             'ecapa': ('ecapa/embedding_model.ckpt',),
             'scoreq': ('scoreq/fixed_nmr_telephone.onnx',), 'estoi': ()}[metric]
    checked = {}
    for relative in paths:
        path = asset_root / relative
        if not path.is_file() or sha(path) != ASSET_SHA256[relative]:
            raise ValueError(f'固定品質資産が欠落・不一致です: {path}')
        checked[relative] = {'path': str(path.resolve()), 'bytes': path.stat().st_size,
                             'sha256': ASSET_SHA256[relative]}
    options = {}
    if metric == 'utmosv2':
        options = {'checkpoint': checked[paths[0]]['path'], 'config': checked[paths[1]]['path'],
                   'preprocessor_config': checked[paths[2]]['path']}
    elif metric == 'ecapa':
        options = {'embedding_model': checked[paths[0]]['path']}
    elif metric == 'scoreq':
        options = {'model': checked[paths[0]]['path'], 'domain': 'natural'}
    return checked, options


def native_rows(native_output: Path, cases, owner: int):
    contract_path = native_output / 'contract.json'
    contract = read(contract_path)
    summary = read(native_output / 'summary.json')
    if (contract.get('kind') != 'apron_fixed120_native' or contract.get('owner') != owner
            or contract.get('case_ids') != [case['id'] for case in cases]
            or contract.get('input_manifest_sha256') != MANIFEST_SHA256
            or contract.get('planned_branches') != list(CONDITIONS)
            or contract.get('source_hashes') != source_hashes()
            or summary.get('finished_cases') != len(cases)
            or summary.get('planned_outputs') != len(cases) * len(CONDITIONS)):
        raise ValueError('native結果の担当・入力・科学source契約が違います')
    rows = {}
    for case in cases:
        _, row = latest_attempt(native_output, case['id'])
        if not row:
            raise ValueError(f'native個票が欠落しています: {case["id"]}')
        if (row['case'] != case['id'] or row['input_sha256'] != case['input']['sha256']
                or row.get('status') not in ('measured', 'failed')):
            raise ValueError(f'native個票の入力識別が違います: {case["id"]}')
        for branch in row.get('branches', {}).values():
            if branch.get('status') == 'measured':
                item = branch['output']
                path = native_output / 'cases' / case['id'] / item['path']
                if (not path.is_file() or path.stat().st_size != item['bytes']
                        or sha(path) != item['sha256']):
                    raise ValueError(f'native波形のbytes/SHAが違います: {path}')
        rows[case['id']] = row
    return contract_path, rows


def _input_wave(case):
    wave = np.load(case['absolute_input'], allow_pickle=False)
    if wave.ndim != 1 or not np.isfinite(wave).all():
        raise ValueError('品質参照の元入力が不正です')
    return wave


def _output_wave(native_output: Path, case_id: str, branch):
    item = branch['output']
    path = native_output / 'cases' / case_id / item['path']
    if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError('評価直前のnative波形SHAが変わりました')
    wave = np.load(path, allow_pickle=False)
    if (wave.ndim != 1 or len(wave) != item['samples']
            or item['sample_rate'] != 24000
            or wave.dtype not in (np.dtype('float32'), np.dtype('float64'))
            or not np.isfinite(wave).all()):
        raise ValueError('native波形のshape・標本化周波数・有限性が不正です')
    return wave


def pcm_sha(wave):
    return hashlib.sha256(np.asarray(wave, dtype='<f8').tobytes()).hexdigest()


def evaluate_one(case, name, metric, native_row, native_output, backend):
    entry = {'case': case['id'], 'speaker': case['speaker'], 'method': name.split('_')[0],
             'condition': name, 'metric': metric, 'status': 'pending', 'value': None,
             'common_samples': case['common_samples']}
    branch = (native_row or {}).get('branches', {}).get(name)
    if not branch or branch.get('status') != 'measured':
        return {**entry, 'status': 'upstream_failed',
                'reason': (branch or {}).get('error', 'native出力がありません')}
    try:
        x = _input_wave(case)
        y_native = _output_wave(native_output, case['id'], branch)
        entry['native_output_sha256'] = branch['output']['sha256']
        entry['native_output_samples'] = len(y_native)
        if metric == 'utmosv2':
            scope = 'native_full_length'
            entry['output_pcm_float64_sha256'] = pcm_sha(y_native)
            entry['output_samples'] = len(y_native)
            entry['reference_samples'] = None
            value, detail = backend.score(None, y_native, 24000)
            used = len(y_native)
        else:
            y16 = resample_poly(y_native.astype(np.float64), 2, 3)
            if metric == 'ecapa' and name in ('apron_minus3', 'apron_plus3'):
                scope = 'edited_full_length'
                reference, output = x, y16
            else:
                scope = 'frozen_common_16k_prefix'
                n = case['common_samples']
                if min(len(x), len(y16)) < n:
                    return {**entry, 'status': 'not_applicable', 'reason': 'fixed_window_unavailable',
                            'native_output_sha256': branch['output']['sha256']}
                reference, output = x[:n], y16[:n]
            used = len(output)
            entry['reference_pcm_float64_sha256'] = pcm_sha(reference)
            entry['output_pcm_float64_sha256'] = pcm_sha(output)
            entry['reference_samples'] = len(reference)
            entry['output_samples'] = len(output)
            if metric == 'estoi':
                detail = _estoi(reference, output, 16000, True)
                value = detail.get('value')
                if detail.get('status') != 'measured':
                    return {**entry, 'status': detail.get('status', 'failed'),
                            'reason': detail.get('reason') or detail.get('error'),
                            'detail': detail, 'scope': scope, 'evaluated_samples': used}
            else:
                value, detail = backend.score(reference, output, 16000)
        if not np.isfinite(value):
            raise ValueError('品質値が非有限数です')
        return {**entry, 'status': 'measured', 'value': float(value), 'detail': detail,
                'scope': scope, 'evaluated_samples': used,
                'evaluated_sample_rate': 24000 if metric == 'utmosv2' else 16000,
                'reference': 'none' if metric == 'utmosv2' else 'fixed_original_excerpt'}
    except Exception as error:
        logging.exception('品質個票の計測失敗: %s %s %s', case['id'], name, metric)
        return {**entry, 'status': 'failed', 'reason': f'{type(error).__name__}: {error}',
                'traceback': traceback.format_exc()}


def write_summary(output, owner, metric, cases, rows):
    observed = {row['case']: row for row in rows}
    recorded = [item for row in rows for item in row.get('rows', [])]
    planned = len(cases) * len(expected_conditions(metric))
    write(output / 'summary.json', {'schema_version': 1, 'owner': owner,
          'metric': metric, 'planned_cases': len(cases),
          'planned_values': planned,
          'visited_cases': len(rows),
          'finished_cases': sum(row.get('status') in ('measured', 'complete_with_missing')
                                for row in rows),
          'measured_values': sum(item['status'] == 'measured' for item in recorded),
          'missing_values': sum(item['status'] != 'measured' for item in recorded),
          'not_run_values': planned - len(recorded),
          'rows': [{'case': case['id'],
                    'status': observed[case['id']]['status'] if case['id'] in observed else 'not_run'}
                   for case in cases]})


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, required=True)
    parser.add_argument('--native-output', type=Path, required=True)
    parser.add_argument('--owner', type=int, choices=(0, 1, 2), required=True)
    parser.add_argument('--metric', choices=METRICS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    require_threads(2)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cases = input_cases(args.input_manifest, args.input_root, args.owner)
    native_contract, saved = native_rows(args.native_output, cases, args.owner)
    assets, options = asset_options(args.asset_root, args.metric)
    output = args.output.resolve()
    protected = (args.input_root.resolve(), args.asset_root.resolve(), args.native_output.resolve())
    if any(output == p or output in p.parents or p in output.parents for p in protected):
        raise ValueError('品質出力は入力・資産・native出力から独立させてください')
    contract = {'schema_version': 1, 'kind': 'apron_fixed120_quality',
                'owner': args.owner, 'metric': args.metric,
                'case_ids': [case['id'] for case in cases],
                'conditions': list(expected_conditions(args.metric)),
                'input_manifest_sha256': MANIFEST_SHA256,
                'native_contract_sha256': sha(native_contract),
                'native_result_sha256': {
                    case['id']: sha(args.native_output / 'cases' / case['id'] /
                                    sorted((args.native_output / 'cases' / case['id']).glob('attempt-*'))[-1].name /
                                    'result.json') if saved[case['id']] else None
                    for case in cases},
                'native_output': str(args.native_output.resolve()),
                'input_root': str(args.input_root.resolve()),
                'assets': assets, 'source_hashes': source_hashes(),
                'runtime_versions': versions(), 'quality_threads': 2,
                'missing_values': 'null_with_status_and_reason'}
    bind_run(output, contract)
    backend = None
    initialization_error = None
    rows = []
    with threadpool_limits(limits=2):
      for case in cases:
        previous_path, old = latest_attempt(output, case['id'])
        if previous_path is not None and old is None and not args.retry_failed:
            raise ValueError(f'中断済み試行があり、明示的な再開指定が必要です: {previous_path}')
        if old and old.get('status') == 'measured':
            old_rows = old.get('rows', [])
            if ({item['condition'] for item in old_rows} != set(expected_conditions(args.metric))
                    or len(old_rows) != len(expected_conditions(args.metric))
                    or any(item['status'] != 'measured' or not np.isfinite(item['value'])
                           for item in old_rows)):
                raise ValueError(f'完了済み品質個票の集合・値が不正です: {case["id"]}')
            rows.append(old)
            write_summary(output, args.owner, args.metric, cases, rows)
            continue
        if old and not args.retry_failed:
            rows.append(old)
            write_summary(output, args.owner, args.metric, cases, rows)
            continue
        attempt = new_attempt(output, case['id'])
        old_success = {item['condition']: item for item in (old or {}).get('rows', [])
                       if item['status'] == 'measured'}
        row = {'schema_version': 1, 'case': case['id'], 'metric': args.metric,
               'started_at_utc': now(), 'status': 'running', 'rows': []}
        write(attempt / 'result.json', row)
        for condition in expected_conditions(args.metric):
            if condition in old_success:
                item = old_success[condition]
            else:
                branch = (saved[case['id']] or {}).get('branches', {}).get(condition)
                if not branch or branch.get('status') != 'measured':
                    item = evaluate_one(case, condition, args.metric, saved[case['id']],
                                        args.native_output, None)
                else:
                    if backend is None and args.metric in MODEL_CLASSES and initialization_error is None:
                        try:
                            with offline_environment():
                                backend = MODEL_CLASSES[args.metric](options, args.asset_root,
                                                                     output / 'work', 2)
                            provenance = output / 'model-provenance.json'
                            if provenance.exists() and read(provenance) != backend.provenance:
                                raise ValueError('以前の品質モデル来歴と一致しません')
                            if not provenance.exists():
                                write(provenance, backend.provenance)
                        except Exception:
                            logging.exception('品質モデルの初期化失敗')
                            initialization_error = traceback.format_exc()
                    if initialization_error is not None:
                        item = {'case': case['id'], 'condition': condition, 'metric': args.metric,
                                'status': 'failed', 'value': None,
                                'reason': 'model_initialization_failed', 'traceback': initialization_error}
                    else:
                        with offline_environment():
                            item = evaluate_one(case, condition, args.metric, saved[case['id']],
                                                args.native_output, backend)
            row['rows'].append(item)
            write(attempt / 'result.json', row)
        row['status'] = ('measured' if all(item['status'] == 'measured' for item in row['rows'])
                         else 'complete_with_missing')
        row['finished_at_utc'] = now()
        write(attempt / 'result.json', row)
        rows.append(row)
        write_summary(output, args.owner, args.metric, cases, rows)
    write_summary(output, args.owner, args.metric, cases, rows)
    return 0 if all(row.get('status') == 'measured' for row in rows) else 2


if __name__ == '__main__':
    sys.exit(run_cli(main, 'apron-fixed120-quality'))
