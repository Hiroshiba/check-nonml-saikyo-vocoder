"""新run専用: 独立trainのencodeと発話等重み校正用母統計を保存する。"""
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

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_features_common import (
    PLAN, TRAIN, feature_path, npy_hash, prepare_input_contract, project, save_npz,
    schema_digest,
)
from all_metrics_synthesis import ADAPTER_SOURCES, native_input, seed_all
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json
from vocoderbench.references.common import verify_prepared


def extract(adapter, spec, method, signature, retry):
    folder = feature_path(TRAIN, method, spec['id'])
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'features.json'
    if path.exists():
        previous = read(path)
        if previous.get('contract_sha256') != signature:
            raise ValueError('独立train特徴の固定条件が不一致')
        if previous['status'] == 'measured':
            if sha256(folder / 'moments.npz') != previous['moments_sha256']:
                raise ValueError('独立train特徴母統計hash不一致')
            return
        if not retry:
            return
        write_json(folder / 'failure_history' / f'{time.time_ns()}.json', previous)
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
           'status': 'failed', 'source_sha256': spec['sha256'],
           'contract_sha256': signature, 'started_at_utc': now(),
           'implementation_origin': 'new_recovery_run_source_not_restored_original'}
    z, temporary_input = None, None
    tick = time.perf_counter()
    try:
        seed_all(0)
        wave, wav, info = native_input(spec, adapter, method, folder)
        temporary_input = wav if method == 'magphase' else None
        with torch.inference_mode():
            z = adapter.encode(wave, wav)
        features, schema = adapter.readout_features(z)
        features = np.asarray(features, dtype=np.float32)
        matrix, fixed = project(features, schema, method)
        freeze(TRAIN / 'schemas' / f'{method}.json', fixed)
        mean = matrix.mean(axis=0)
        second = np.mean(matrix * matrix, axis=0)
        if not np.isfinite(mean).all() or not np.isfinite(second).all():
            raise ValueError('独立train母統計が非有限')
        save_npz(folder / 'moments.npz', mean=mean, second_moment=second)
        frame_hash = npy_hash(features)
        row.update(status='measured', input=info, schema=schema,
                   projected_schema_sha256=schema_digest(fixed),
                   shape=list(features.shape), frame_dtype=str(features.dtype),
                   sha256=frame_hash, frame_npy_sha256=frame_hash,
                   frame_canonical_sha256=hashlib.sha256(
                       features.astype('<f4', copy=False).tobytes(order='C')).hexdigest(),
                   storage='moments_only', moments_sha256=sha256(folder / 'moments.npz'),
                   moments_definition='float64 within-utterance frame-equal population moments',
                   full_frame_storage='not retained; SHA identifies transient NPY serialization',
                   decoder_payload_storage='not retained; no decoding')
    except Exception:
        logging.exception('独立train特徴抽出失敗: %s %s', method, spec['id'])
        row['error'] = traceback.format_exc()
    finally:
        if z is not None and hasattr(adapter, 'release'):
            adapter.release(z)
        if temporary_input is not None:
            temporary_input.unlink(missing_ok=True)
    row.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter()-tick)
    write_json(path, row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=METHODS, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    train, _ = prepare_input_contract()
    specs = read(args.inputs)
    expected = {row['id']: row for row in train}
    if not 0 < len(specs) <= 10 or len({row['id'] for row in specs}) != len(specs):
        raise ValueError('独立train processは重複しない1〜10録音')
    if any(expected.get(row['id']) != row for row in specs):
        raise ValueError('batchが固定独立train入力の部分集合ではありません')
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
                                    TRAIN / 'adapter-work' / args.method)
    sources = [Path(__file__), PLAN, ROOT / 'scripts/all_metrics_features_common.py',
        ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_synthesis.py',
        ROOT / 'scripts/all_metrics_base_controls.py',
        *(ROOT / 'scripts' / name for name in ADAPTER_SOURCES),
        *sorted((ROOT / 'vocoderbench/references').glob('adapters_*.py')),
        ROOT / 'vocoderbench/world.py', ROOT / 'vocoderbench/methods.py',
        *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    contract = {'schema_version': 1, 'stage': 'independent_train_encode_only',
        'implementation_origin': 'new_recovery_run_source_not_restored_original',
        'method': args.method, 'input_contract_sha256': sha256(TRAIN / 'input-contract.json'),
        'train_inputs_sha256': sha256(RUN / 'corpora/readout-train/inputs.json'),
        'sources_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        'prepared': prepared, 'adapter_info': adapter.info, 'seed': 0, 'threads': 2,
        'runtime': {'python': sys.version, 'packages': {p: importlib.metadata.version(p)
                    for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'decode': False, 'storage': 'float64 mean and second moment; transient frame hashes',
        'evaluation_fit': False}
    contract_path = TRAIN / 'contracts' / f'{args.method}.json'
    freeze(contract_path, contract)
    for spec in specs:
        extract(adapter, spec, args.method, sha256(contract_path), args.retry_failed)
    return int(any(read(feature_path(TRAIN, args.method, spec['id']) / 'features.json')['status']
                   != 'measured' for spec in specs))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-features-train'))
