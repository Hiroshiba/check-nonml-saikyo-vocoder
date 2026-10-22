"""固定120録音のLayer1 3条件とLayer0無編集を保存する。"""
from __future__ import annotations

import logging
from pathlib import Path
import sys
import traceback

import numpy as np
from scipy.signal import resample_poly
from threadpoolctl import threadpool_limits
import torch

from vocoderbench.apron.engine import Layer1Engine
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli
from vocoderbench.references.adapters_dsp import build_llsm
from vocoderbench.references.current_base import record as current_record
from vocoderbench.references.worker import seed_all

from .common import (CONDITIONS, MANIFEST_SHA256, bind_run, input_cases,
                     latest_attempt, new_attempt, now, require_threads, save_wave, sha,
                     source_hashes, versions, write)


def _verify_descriptor(case_root: Path, descriptor: dict) -> None:
    path = case_root / descriptor['path']
    if (not path.is_file() or path.stat().st_size != descriptor['bytes']
            or sha(path) != descriptor['sha256']):
        raise ValueError(f'保存済みnative原本が不一致: {path}')


def _old_success(case_root: Path, previous: dict | None):
    branches = {}
    representation = None
    if previous:
        for name in CONDITIONS:
            item = previous.get('branches', {}).get(name, {})
            if item.get('status') == 'measured':
                _verify_descriptor(case_root, item['output'])
                branches[name] = item
        item = previous.get('representation')
        if item:
            for name in ('arrays.npz', 'metadata.json'):
                _verify_descriptor(case_root, item[name])
            representation = item
    return branches, representation


def _failure(error: Exception) -> dict:
    logging.exception('native枝が失敗しました')
    return {'status': 'failed', 'error': f'{type(error).__name__}: {error}',
            'traceback': traceback.format_exc()}


def measure_case(case: dict, output: Path, apron: Layer1Engine, layer0, retry: bool):
    case_root = output / 'cases' / case['id']
    previous_path, previous = latest_attempt(output, case['id'])
    if previous_path is not None and previous is None and not retry:
        raise ValueError(f'中断済み試行があり、明示的な再開指定が必要です: {previous_path}')
    succeeded, representation = _old_success(case_root, previous)
    if previous:
        if previous.get('status') == 'measured':
            if set(succeeded) != set(CONDITIONS):
                raise ValueError(f'完了済みnative枝が欠落しています: {case["id"]}')
            return previous
        if not retry:
            return previous
    attempt = new_attempt(output, case['id'])
    row = {'schema_version': 1, 'case': case['id'], 'speaker': case['speaker'],
           'started_at_utc': now(), 'status': 'running',
           'input_sha256': case['input']['sha256'], 'branches': dict(succeeded),
           'representation': representation}
    write(attempt / 'result.json', row)
    try:
        x = np.load(case['absolute_input'], allow_pickle=False)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError('元入力が単一チャンネルの有限値ではありません')
        x24 = np.ascontiguousarray(resample_poly(x, 3, 2), dtype=np.float64)
        row['native_input'] = {'sample_rate': 24000, 'samples': len(x24),
                               'resampling': 'scipy.signal.resample_poly(3,2)',
                               'float64_sha256': __import__('hashlib').sha256(x24.tobytes()).hexdigest()}
        write(attempt / 'result.json', row)
    except Exception as error:
        failure = _failure(error)
        for name in CONDITIONS:
            row['branches'].setdefault(name, failure)
        row.update(status='failed', finished_at_utc=now())
        write(attempt / 'result.json', row)
        return row

    if not representation and any(name not in row['branches'] for name in CONDITIONS[:3]):
        try:
            seed_all(0)
            destination = attempt / 'layer1'
            apron.analyze_to_saved(x24, 24000, destination)
            representation = {}
            for name in ('arrays.npz', 'metadata.json'):
                path = destination / name
                representation[name] = {'path': str(path.relative_to(case_root)),
                                        'bytes': path.stat().st_size, 'sha256': sha(path)}
            row['representation'] = representation
            write(attempt / 'result.json', row)
        except Exception as error:
            failure = _failure(error)
            for name in CONDITIONS[:3]:
                row['branches'].setdefault(name, {**failure, 'status': 'upstream_failed'})
            write(attempt / 'result.json', row)

    for name, semitones in zip(CONDITIONS[:3], (0, -3, 3), strict=True):
        if name in row['branches']:
            continue
        try:
            seed_all(0)
            source = case_root / representation['metadata.json']['path']
            wave, sample_rate = apron.decode_from_saved(source.parent,
                                                         pitch_semitones=semitones)
            if sample_rate != 24000:
                raise ValueError('Layer1 native出力は24 kHzが必要です')
            descriptor = save_wave(attempt / f'{name}.npy', wave)
            descriptor['path'] = str((attempt / f'{name}.npy').relative_to(case_root))
            row['branches'][name] = {'status': 'measured', 'semitones': semitones,
                                     'seed_before_decode': 0, 'output': descriptor}
        except Exception as error:
            row['branches'][name] = _failure(error)
        write(attempt / 'result.json', row)

    if 'llsm2_0' not in row['branches']:
        pointer = None
        try:
            seed_all(0)
            pointer = layer0.encode(x24, attempt / 'layer0.input.wav')
            seed_all(0)
            wave = layer0.decode(pointer)
            descriptor = save_wave(attempt / 'llsm2_0.npy', wave)
            descriptor['path'] = str((attempt / 'llsm2_0.npy').relative_to(case_root))
            row['branches']['llsm2_0'] = {'status': 'measured', 'semitones': 0,
                                         'seed_before_analysis': 0, 'seed_before_decode': 0,
                                         'output': descriptor}
        except Exception as error:
            row['branches']['llsm2_0'] = _failure(error)
        finally:
            if pointer is not None:
                try:
                    layer0.release(pointer)
                except Exception as error:
                    logging.exception('Layer0 native chunkの解放に失敗')
                    row['branches']['llsm2_0'] = _failure(error)
        write(attempt / 'result.json', row)

    row['status'] = ('measured' if all(row['branches'][name]['status'] == 'measured'
                                      for name in CONDITIONS) else 'failed')
    row['finished_at_utc'] = now()
    write(attempt / 'result.json', row)
    return row


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--runtime-cache', type=Path, required=True)
    parser.add_argument('--owner', type=int, choices=(0, 1, 2), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    require_threads(1)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    output = args.output.resolve()
    if any(output == root or output in root.parents or root in output.parents for root in
           (args.input_root.resolve(), args.runtime_cache.resolve())):
        raise ValueError('出力は入力・依存キャッシュから独立させてください')
    cases = input_cases(args.input_manifest, args.input_root, args.owner)
    identity = current_record(args.runtime_cache)
    if identity['baseline']['method'] != 'apron':
        raise ValueError('Apronが現在の固定baseではありません')
    contract = {'schema_version': 1, 'kind': 'apron_fixed120_native', 'owner': args.owner,
                'case_ids': [row['id'] for row in cases], 'planned_branches': list(CONDITIONS),
                'input_manifest_sha256': MANIFEST_SHA256,
                'input_root': str(args.input_root.resolve()),
                'runtime_cache': str(args.runtime_cache.resolve()),
                'base': identity, 'source_hashes': source_hashes(),
                'runtime_versions': versions(), 'dsp_threads': 1,
                'native_sample_rate': 24000, 'analysis_seed': 0, 'each_decode_seed': 0}
    bind_run(output, contract)
    apron = Layer1Engine(args.runtime_cache / 'native/libllsm_speed.so', identity['native_sha256'])
    layer0 = build_llsm(args.runtime_cache / 'src', args.runtime_cache / 'models', output)
    rows = []
    with threadpool_limits(limits=1):
        for case in cases:
            rows.append(measure_case(case, output, apron, layer0, args.retry_failed))
            observed = {r['case']: r for r in rows}
            write(output / 'summary.json', {'schema_version': 1, 'owner': args.owner,
                  'planned_cases': len(cases), 'planned_outputs': len(cases) * len(CONDITIONS),
                  'measured_outputs': sum(r.get('branches', {}).get(name, {}).get('status') == 'measured'
                                          for r in rows for name in CONDITIONS),
                  'finished_cases': len(rows),
                  'rows': [{'case': item['id'],
                            'status': observed[item['id']]['status'] if item['id'] in observed else 'not_run'}
                           for item in cases]})
    return 0 if all(r.get('status') == 'measured' for r in rows) else 2


if __name__ == '__main__':
    sys.exit(run_cli(main, 'apron-fixed120-native'))
