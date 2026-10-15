"""保存済みHNM/WORLD表現から正式読み出し特徴を抽出する。再合成しない。"""
from __future__ import annotations

import argparse
import importlib.metadata
import logging
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np

from all_metrics_common import ROOT, RUN, freeze, now, read
from all_metrics_synthesis import ADAPTER_SOURCES, save_representation
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def fixed_schema(schema):
    """時間座標とframe数だけを各録音のmetadataへ残す。列意味は固定する。"""
    return {key: value for key, value in schema.items()
            if key not in ('frame_count', 'frame_times_seconds')}


def extract(adapter, spec, args, signature):
    folder = args.output_root / 'native' / args.method / spec['id']
    target = folder / 'features.json'
    if target.exists():
        old = read(target)
        if old.get('status') == 'measured':
            if old['contract_sha256'] != signature or sha256(folder / 'features.npy') != old['sha256']:
                raise ValueError('保存済み読み出し特徴の研究条件またはhash不一致')
            return
        if not args.retry_failed:
            return
        write_json(folder / 'failure_history' / f'latent-features-{time.time_ns()}.json', old)
    row = {'case': spec['id'], 'method': args.method, 'started_at_utc': now(),
           'contract_sha256': signature, 'origin': 'existing_native_representation_export',
           'new_analysis_seconds': 0.0, 'new_synthesis_seconds': 0.0}
    start, cpu = time.perf_counter(), time.process_time()
    try:
        source = folder / 'representation.npz'
        source_record = read(folder / 'representation.json')
        if sha256(source) != source_record['sha256'] or sha256(spec['path']) != spec['sha256']:
            raise ValueError('保存済み表現または固定入力のhash不一致')
        z = adapter.load_native(source)
        payload = save_representation(adapter, z, folder / 'representation_payload.npz')
        write_json(folder / 'representation_payload.json', {**row, **payload, 'status': 'measured',
            'native_representation_sha256': source_record['sha256'], 'adapter_info': adapter.info})
        features, schema = adapter.readout_features(z)
        features = np.asarray(features, dtype=np.float32)
        if features.ndim != 2 or not np.isfinite(features).all():
            raise ValueError('有限なframe×dimensionの読み出し特徴が必要')
        schema_path = args.output_root / 'feature-schemas' / f'{args.method}.json'
        freeze(schema_path, fixed_schema(schema))
        temporary = folder / 'features.part'
        with temporary.open('wb') as stream:
            np.save(stream, features, allow_pickle=False)
        temporary.replace(folder / 'features.npy')
        row.update(status='measured', schema=schema, schema_sha256=sha256(schema_path),
            sha256=sha256(folder / 'features.npy'), shape=list(features.shape),
            representation_sha256=payload['sha256'], native_representation_sha256=source_record['sha256'])
    except Exception:
        logging.exception('保存済み表現からの正式特徴抽出失敗: %s %s', args.method, spec['id'])
        row.update(status='failed', error=traceback.format_exc())
    row.update(finished_at_utc=now(), export_seconds=time.perf_counter() - start,
               export_process_cpu_seconds=time.process_time() - cpu)
    write_json(target, row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=('hnm', 'world_harvest'), required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, default=RUN)
    parser.add_argument('--runtime-cache', type=Path, default=ROOT / '.cache/references')
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    from scripts.all_metrics_control_adapters import build_control_adapter
    started = now()
    tick = time.perf_counter()
    adapter = build_control_adapter(args.method, args.runtime_cache / 'src',
        args.runtime_cache / 'models', args.output_root / 'latent-adapter-work' / args.method)
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py',
        ROOT / 'scripts/all_metrics_synthesis.py', ROOT / 'scripts/all_metrics_base_controls.py',
        *(ROOT / 'scripts' / name for name in ADAPTER_SOURCES), ROOT / 'vocoderbench/world.py',
        ROOT / 'vocoderbench/methods.py', *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    contract = {'schema_version': 1, 'stage': 'existing_native_feature_export', 'method': args.method,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        'input_contract_sha256': sha256(args.output_root / 'input-contract.json'),
        'adapter_info': adapter.info, 'runtime': {'python': sys.version, 'platform': platform.platform(),
            'packages': {p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'feature_schema': 'fixed columns/units; frame_count and frame_times_seconds are per-case',
        'native_representation_and_waveform': 'read only; no encode or decode',
        'world_cache': os.environ.get('NONML_WORLD_CACHE')}
    contract_path = args.output_root / 'latent-contracts' / args.method / 'feature-export.json'
    freeze(contract_path, contract)
    signature = sha256(contract_path)
    write_json(args.output_root / 'latent-initializations' / f'features-{args.method}-{time.time_ns()}.json',
        {'started_at_utc': started, 'seconds': time.perf_counter() - tick, 'inputs': str(args.inputs),
         'input_manifest_sha256': sha256(args.inputs), 'contract_sha256': signature})
    cases = read(args.inputs)
    if not 0 < len(cases) <= 10:
        raise ValueError('正式研究のprocessは1〜10録音に限定する')
    for spec in cases:
        extract(adapter, spec, args, signature)
    return int(any(read(args.output_root / 'native' / args.method / spec['id'] / 'features.json')['status']
                   != 'measured' for spec in cases))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-features'))
