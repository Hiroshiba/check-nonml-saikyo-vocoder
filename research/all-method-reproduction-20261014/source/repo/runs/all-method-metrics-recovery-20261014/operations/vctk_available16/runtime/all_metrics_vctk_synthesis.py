"""VCTK availability16を全8既存方式の固定native構成で無編集再合成する。"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import sys
import time

import torch

from all_metrics_common import METHODS, ROOT, freeze, now, read
from all_metrics_synthesis import ADAPTER_SOURCES, case_run, completed, seed_all
from all_metrics_vctk_inputs import NATIVE_RATES, VCTK_RUN
from vocoderbench import methods
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json
from vocoderbench.references.common import verify_prepared
from scripts.all_metrics_control_adapters import build_control_adapter


def build_vctk_adapter(method, cache):
    adapter = build_control_adapter(method, cache / 'src', cache / 'models',
                                    VCTK_RUN / 'adapter-work' / method)
    if method in ('hnm', 'world_harvest'):
        # This separate study calls the existing 48 kHz-capable API; main adapters stay frozen.
        adapter.sr = 48000
        adapter.encode = lambda wave, path: methods.encode(method, wave, 48000)
        adapter.info['vctk_native_configuration'] = {
            'sample_rate': 48000, 'encode': 'existing methods.encode(method, wave, 48000)',
            'decode': 'unchanged existing methods.decode(method, parameters)',
            'main_study_rate': 16000, 'new_vocoder': False}
    if adapter.sr != NATIVE_RATES[method]:
        raise ValueError('事前固定したVCTK native SRと一致しません')
    return adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', required=True, choices=METHODS)
    parser.add_argument('--batch', required=True, type=int)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.batch < 2:
        raise ValueError('正式16録音の2バッチのみが対象です')
    args.output_root, args.runtime_cache = VCTK_RUN, ROOT / '.cache/references'
    args.inputs = VCTK_RUN / 'input-batches' / f'{args.batch:02d}.json'
    args.threads, args.seed = 2, 0
    args.encode_only, args.unedited_only, args.waveform_only = False, True, True
    args.edits_only = False
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    prepared = (verify_prepared(args.runtime_cache, args.method) if args.method not in METHODS[:2]
                else {'method': args.method, 'formal_base': read(ROOT / 'BASELINE.json'),
                      'world_lock_sha256': sha256(ROOT / 'vocoderbench/world.lock.json')})
    seed_all(0)
    start = time.perf_counter()
    adapter = build_vctk_adapter(args.method, args.runtime_cache)
    initialization = time.perf_counter() - start
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py',
             ROOT / 'scripts/all_metrics_synthesis.py', Path(__file__).parent / 'all_metrics_vctk_inputs.py',
             *(ROOT / 'scripts' / name for name in ADAPTER_SOURCES),
             *sorted((ROOT / 'vocoderbench/references').glob('adapters_*.py')),
             ROOT / 'vocoderbench/references/common.py', ROOT / 'vocoderbench/references/worker.py']
    if args.method in METHODS[:2]:
        paths += [ROOT / 'scripts/all_metrics_base_controls.py', ROOT / 'vocoderbench/world.py',
                  ROOT / 'vocoderbench/methods.py', *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    contract = {
        'schema_version': 1, 'study': 'VCTK availability16 independent 48 kHz input-system supplement',
        'method': args.method, 'prepared': prepared,
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        'input_contract_sha256': sha256(VCTK_RUN / 'input-contract.json'),
        'inputs_sha256': sha256(VCTK_RUN / 'inputs.json'),
        'threads': 2, 'seed': 0, 'unedited_only': True, 'waveform_only': True,
        'native_sample_rate': adapter.sr, 'native_sample_rates_all_methods': NATIVE_RATES,
        'adapter_info': adapter.info,
        'runtime': {'python': sys.version, 'platform': platform.platform(),
                    'packages': {p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'input_resampling': {'function': 'scipy.signal.resample_poly', 'window': ['kaiser', 5.0],
                             'padtype': 'constant', 'from_sample_rate': 48000},
        'input_quantization': 'MagPhase official API only: PCM16; all others float64 input',
        'waveform_postprocessing': 'none: full native length retained, no trim/pad/normalization',
        'representation_storage': False, 'readout_feature_storage': False,
        'randomness': 'seed0 reset immediately before encode and again immediately before decode',
        'timing': 'single formal encode/decode per case, no warmup or rehearsal runs'}
    contract_path = VCTK_RUN / 'synthesis-contracts' / f'{args.method}.json'
    freeze(contract_path, contract)
    signature = sha256(contract_path)
    write_json(VCTK_RUN / 'synthesis-initializations' / f'{args.method}-{time.time_ns()}.json',
               {'started_at_utc': now(), 'seconds': initialization, 'batch': args.batch,
                'input_manifest_sha256': sha256(args.inputs), 'contract_sha256': signature})
    specs = read(args.inputs)
    for spec in specs:
        case_run(adapter, spec, args, signature)
    return int(any(not completed(VCTK_RUN / 'native' / args.method / spec['id'],
                                 ['unedited'], signature, waveform_only=True) for spec in specs))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-vctk-synthesis'))
