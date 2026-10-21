"""既存人間評定105全長録音のdecoder入力特徴平均を正式抽出する。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import logging
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import torch

from all_metrics_common import ROOT, freeze, now, read
from all_metrics_features_common import TRAIN, npy_hash, project, schema_digest
from all_metrics_human_data import OUT, PLAN
from all_metrics_synthesis import ADAPTER_SOURCES, native_input, seed_all
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json
from vocoderbench.references.common import verify_prepared


def extract(adapter, spec, method, signature, retry):
    folder = OUT / 'features' / method / spec['id']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'features.json'
    if path.exists():
        previous = read(path)
        if previous['contract_sha256'] != signature:
            raise ValueError('保存済み#13特徴の契約hash不一致')
        if previous['status'] == 'measured':
            if sha256(folder / 'mean.npy') != previous['mean_sha256']:
                raise ValueError('保存済み#13特徴平均hash不一致')
            return
        if not retry:
            return
        write_json(folder / 'failure_history' / f'{time.time_ns()}.json', previous)
    row = {'method': method, 'case': spec['id'], 'speaker': spec['speaker'],
        'contract_sha256': signature, 'started_at_utc': now(), 'status': 'failed'}
    z = None
    tick = time.perf_counter()
    try:
        seed_all(0)
        wave, wav, info = native_input(spec, adapter, method, folder)
        with torch.inference_mode():
            z = adapter.encode(wave, wav)
        features, schema = adapter.readout_features(z)
        features = np.asarray(features, dtype=np.float32)
        matrix, fixed_schema = project(features, schema, method)
        if fixed_schema != read(TRAIN / 'schemas' / f'{method}.json'):
            raise ValueError('#13の特徴列schemaが独立trainと不一致')
        mean = matrix.mean(axis=0)
        np.save(folder / 'mean.npy', mean, allow_pickle=False)
        row.update(status='measured', input=info, schema=schema,
            projected_schema_sha256=schema_digest(fixed_schema), mean_sha256=sha256(folder / 'mean.npy'),
            frame_shape=list(features.shape), frame_dtype=str(features.dtype),
            frame_npy_sha256=npy_hash(features),
            frame_canonical_sha256=hashlib.sha256(features.astype('<f4', copy=False).tobytes(order='C')).hexdigest(),
            full_frame_storage='not retained; transient mean-computation intermediate',
            regeneration_requirement='same sources/inputs/models/seed and frame NPY/canonical hash match')
    except Exception:
        logging.exception('正式#13特徴抽出失敗: %s %s', method, spec['id'])
        row['error'] = traceback.format_exc()
    finally:
        if z is not None and hasattr(adapter, 'release'):
            adapter.release(z)
    row.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter()-tick)
    write_json(path, row)
    logging.info('正式#13特徴: %s %s %s', method, spec['id'], row['status'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', required=True)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    from scripts.all_metrics_control_adapters import build_control_adapter
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    cache = ROOT / '.cache/references'
    prepared = (verify_prepared(cache, args.method) if args.method not in ('hnm', 'world_harvest')
                else {'formal_base': read(ROOT / 'BASELINE.json'),
                      'world_lock_sha256': sha256(ROOT / 'vocoderbench/world.lock.json')})
    seed_all(0)
    adapter = build_control_adapter(args.method, cache / 'src', cache / 'models',
                                    OUT / 'adapter-work' / args.method)
    sources = [Path(__file__), PLAN, ROOT / 'scripts/all_metrics_human_data.py',
        ROOT / 'scripts/all_metrics_features_common.py', ROOT / 'scripts/all_metrics_synthesis.py',
        ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_base_controls.py',
        *(ROOT / 'scripts' / p for p in ADAPTER_SOURCES),
        *sorted((ROOT / 'vocoderbench/references').glob('adapters_*.py')),
        ROOT / 'vocoderbench/world.py',
        *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    contract = {'method': args.method, 'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in sources},
        'prepared': prepared, 'input_contract_sha256': sha256(OUT / 'input-contract.json'),
        'train_feature_schema_sha256': sha256(TRAIN / 'schemas' / f'{args.method}.json'),
        'adapter_info': adapter.info, 'seed': 0, 'threads': 2, 'decode': False,
        'runtime': {'python': sys.version, 'packages': {p: importlib.metadata.version(p)
                                                     for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'scope': 'full-length original recording features; float64 native-frame equal mean; no decoder payload'}
    path = OUT / 'feature-contracts' / f'{args.method}.json'
    freeze(path, contract)
    specs = read(args.inputs)
    if not 0 < len(specs) <= 10:
        raise ValueError('正式processは1〜10録音')
    for spec in specs:
        extract(adapter, spec, args.method, sha256(path), args.retry_failed)
    return int(any(read(OUT / 'features' / args.method / s['id'] / 'features.json')['status'] != 'measured'
                   for s in specs))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-human-features'))
