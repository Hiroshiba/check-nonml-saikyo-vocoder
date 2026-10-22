"""元の固定120評価を保ったままLayer0の±3半音だけを追加生成する。"""
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

from scripts.all_metrics_llsm_control import augment_llsm
from scripts.apron_fixed120.common import (MANIFEST_SHA256, bind_run, input_cases,
                                           latest_attempt, new_attempt, now, require_threads,
                                           save_wave, sha, source_hashes, versions, write)
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli
from vocoderbench.references.adapters_dsp import build_llsm
from vocoderbench.references.current_base import record as current_record
from vocoderbench.references.worker import seed_all

from .common import (CONDITIONS, CONTROL, SEMITONES, driver_hashes,
                     original_native, separate_output, write_new)


def saved_success(output: Path, case: dict, original_ref: dict):
    attempt, row = latest_attempt(output, case['id'])
    if attempt is None:
        return None, None
    if row is None:
        return attempt, None
    if (row.get('case') != case['id']
            or row.get('input_sha256') != case['input']['sha256']
            or row.get('original_result_sha256') != original_ref['result']['sha256']):
        raise ValueError(f'保存済み試行の入力・元結果が違います: {case["id"]}')
    if row.get('status') == 'measured':
        if set(row.get('branches', {})) != set(CONDITIONS):
            raise ValueError(f'完了済みの枝が不足しています: {case["id"]}')
        for name in CONDITIONS:
            item = row['branches'][name]
            descriptor = item['output']
            path = output / 'cases' / case['id'] / descriptor['path']
            if (item['status'] != 'measured' or not path.is_file()
                    or path.stat().st_size != descriptor['bytes']
                    or sha(path) != descriptor['sha256']):
                raise ValueError(f'完了済みの補助波形が不一致です: {path}')
    return attempt, row


def measure_case(case: dict, output: Path, adapter, original_ref: dict, retry: bool):
    previous_path, previous = saved_success(output, case, original_ref)
    if previous_path is not None:
        if previous is None and not retry:
            raise ValueError(f'中断記録の再開には--retry-failedが必要です: {previous_path}')
        if previous is not None and (previous['status'] == 'measured' or not retry):
            return previous
    attempt = new_attempt(output, case['id'])
    row = {'schema_version': 1, 'case': case['id'], 'speaker': case['speaker'],
           'started_at_utc': now(), 'input_sha256': case['input']['sha256'],
           'original_result_sha256': original_ref['result']['sha256'],
           'original_wave_sha256': original_ref['waves'], 'branches': {}}
    write_new(attempt / 'start.json', row)
    chunk = None
    try:
        x = np.load(case['absolute_input'], allow_pickle=False)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError('元入力が単一チャンネルの有限値ではありません')
        x24 = np.ascontiguousarray(resample_poly(x, 3, 2), dtype=np.float64)
        row['native_input'] = {
            'sample_rate': 24000, 'samples': len(x24),
            'resampling': 'scipy.signal.resample_poly(3,2)',
            'float64_sha256': hashlib.sha256(x24.tobytes()).hexdigest()}
        if row['native_input'] != original_ref['native_input']:
            raise ValueError('24 kHz解析入力が元実行と一致しません')
        seed_all(0)
        chunk = adapter.encode(x24, attempt / 'layer0.input.wav')
        if not chunk:
            raise ValueError('Layer0解析chunkが空です')
        for name in CONDITIONS:
            edited = None
            try:
                edited = adapter.edit(chunk, CONTROL[name])
                seed_all(0)
                wave = adapter.decode(edited)
                descriptor = save_wave(attempt / f'{name}.npy', wave)
                descriptor['path'] = str((attempt / f'{name}.npy').relative_to(
                    output / 'cases' / case['id']))
                row['branches'][name] = {
                    'status': 'measured', 'semitones': SEMITONES[name],
                    'seed_before_decode': 0, 'output': descriptor}
            except Exception as error:
                logging.exception('補助native枝が失敗しました: %s %s', case['id'], name)
                row['branches'][name] = {
                    'status': 'failed', 'error': f'{type(error).__name__}: {error}',
                    'traceback': traceback.format_exc()}
            finally:
                if edited is not None:
                    try:
                        adapter.release(edited)
                    except Exception as error:
                        logging.exception('編集chunkの解放に失敗しました')
                        row['branches'][name] = {
                            'status': 'failed', 'error': f'{type(error).__name__}: {error}',
                            'traceback': traceback.format_exc()}
            write_new(attempt / f'{name}.json', row['branches'][name])
    except Exception as error:
        logging.exception('Layer0入力・解析が失敗しました: %s', case['id'])
        failure = {'status': 'upstream_failed',
                   'error': f'{type(error).__name__}: {error}',
                   'traceback': traceback.format_exc()}
        for name in CONDITIONS:
            if name not in row['branches']:
                row['branches'][name] = failure
                write_new(attempt / f'{name}.json', failure)
    finally:
        if chunk is not None:
            try:
                adapter.release(chunk)
            except Exception as error:
                logging.exception('解析chunkの解放に失敗しました')
                row['release_error'] = {'error': f'{type(error).__name__}: {error}',
                                        'traceback': traceback.format_exc()}
    row['status'] = ('measured' if not row.get('release_error') and
                     all(row['branches'].get(name, {}).get('status') == 'measured'
                         for name in CONDITIONS) else 'failed')
    row['finished_at_utc'] = now()
    write_new(attempt / 'result.json', row)
    return row


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--runtime-cache', type=Path, required=True)
    parser.add_argument('--original-native', type=Path, required=True)
    parser.add_argument('--owner', type=int, choices=(0, 1, 2), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    require_threads(1)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cases = input_cases(args.input_manifest, args.input_root, args.owner)
    old_contract_path, old_contract, _, refs = original_native(
        args.original_native, cases, args.owner)
    identity = current_record(args.runtime_cache)
    if identity != old_contract['base']:
        raise ValueError('Layer0のsource/native/assetsが元実行と一致しません')
    output = separate_output(args.output, args.input_root, args.runtime_cache,
                             args.original_native, args.input_manifest)
    contract = {'schema_version': 1, 'kind': 'apron_pitch_control_native',
                'owner': args.owner, 'case_ids': [case['id'] for case in cases],
                'conditions': list(CONDITIONS), 'native_sample_rate': 24000,
                'analysis_seed': 0, 'each_decode_seed': 0, 'dsp_threads': 1,
                'input_manifest_sha256': MANIFEST_SHA256,
                'input_root': str(args.input_root.resolve()),
                'runtime_cache': str(args.runtime_cache.resolve()),
                'original_native_root': str(args.original_native.resolve()),
                'original_native_contract_sha256': sha(old_contract_path),
                'original_references': refs, 'base': identity,
                'source_hashes': source_hashes(), 'driver_hashes': driver_hashes('native'),
                'runtime_versions': versions()}
    bind_run(output, contract)
    adapter = build_llsm(args.runtime_cache / 'src', args.runtime_cache / 'models', output)
    augment_llsm(adapter, args.runtime_cache / 'src')
    rows = []
    with threadpool_limits(limits=1):
        for case in cases:
            rows.append(measure_case(case, output, adapter, refs[case['id']],
                                     args.retry_failed))
            write(output / 'summary.json', {
                'schema_version': 1, 'owner': args.owner,
                'planned_cases': len(cases), 'planned_outputs': len(cases) * 2,
                'finished_cases': len(rows),
                'measured_outputs': sum(row.get('status') == 'measured' and
                                        row['branches'][name]['status'] == 'measured'
                                        for row in rows for name in CONDITIONS),
                'rows': [{'case': item['id'], 'status': next(
                    (row['status'] for row in rows if row['case'] == item['id']), 'not_run')}
                    for item in cases]})
    return 0 if all(row['status'] == 'measured' for row in rows) else 2


if __name__ == '__main__':
    sys.exit(run_cli(main, 'apron-pitch-control-native'))
