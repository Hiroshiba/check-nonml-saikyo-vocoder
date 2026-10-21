"""正式120録音の量子化・入力端点補間・既存時間操作。10録音ごと逐次保存。"""
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

import torch

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_latent_interpolation import interpolation_case, time_case
from all_metrics_latent_io import native_representation, release, shared_assets
from all_metrics_latent_quantization import quantize_case
from all_metrics_synthesis import ADAPTER_SOURCES, seed_all
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json
from vocoderbench.references.common import verify_prepared


def contract(adapter, args, prepared):
    files = [Path(__file__), ROOT / 'scripts/all_metrics_latent_io.py',
        ROOT / 'scripts/all_metrics_latent_quantization.py', ROOT / 'scripts/all_metrics_latent_provenance.py', ROOT / 'scripts/all_metrics_latent_interpolation.py',
        ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_synthesis.py',
        ROOT / 'scripts/all_metrics_base_controls.py', *(ROOT / 'scripts' / name for name in ADAPTER_SOURCES),
        *sorted((ROOT / 'vocoderbench/references').glob('adapters_*.py')),
        ROOT / 'vocoderbench/world.py', ROOT / 'vocoderbench/control.py',
        *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    asset_path = args.output_root / 'latent-contracts' / args.method / 'shared-assets.json'
    freeze(asset_path, shared_assets(adapter, args))
    value = {'schema_version': 1, 'stage': args.stage, 'method': args.method, 'seed': args.seed,
        'threads': args.threads, 'native_sample_rate': adapter.sr,
        'input_contract_sha256': sha256(args.output_root / 'input-contract.json'),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in files},
        'prepared': prepared, 'adapter_info': adapter.info,
        'shared_asset_manifest_sha256': sha256(asset_path),
        'capabilities': adapter.capabilities,
        'runtime': {'python': sys.version, 'platform': platform.platform(),
            'packages': {p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'world_cache': os.environ.get('NONML_WORLD_CACHE'),
        'quantization': {'storage_dtype_points': ['float16', 'float32'],
            'mixed_precision': True, 'points_independently_derived_from_original_native_representation': True,
            'file_io': 'real NPZ write then read then import into original decoder type',
            'controls': 'each supported native pitch/gain operation after restoring the stored payload',
            'reuse': 'same canonical decoder array/structure/settings hash permits existing seed0 wave citation; no self-decode test',
            'bitrate_scope': 'per-utterance compressed NPZ payload bytes including structure, separate fixed shared assets; not self-contained total'},
        'interpolation': {'endpoint_kind': 'input_gain_reencode', 'input_gain_db': [0.0, -6.0],
            'alpha': [0.0, 0.5, 1.0], 'rule': adapter.interpolation_rule,
            'source_input': 'fixed original float64 NPY times 10**(-6/20), then same native_input resampling/PCM16 policy',
            'left_endpoint': 'reuse existing original native representation and waveform',
            'right_endpoint': 'new encode of known input attenuation; persist actual decoder payload and decode seed0',
            'midpoint_failures': 'unaligned structure/UV/pitchmarks are not_applicable, no DTW/resize or alignment',
            'endpoint_scope': 'independent physical endpoints retained even if interpolation is not applicable',
            'not_a_native_gain_control_claim': True},
        'time_scale': {'amount': 1.25, 'methods': ['hnm', 'world_harvest'],
            'api': 'existing edit_time', 'length_rounding': 'positive round half up',
            'no_original_reencoding': True, 'local_phoneme_ground_truth': False},
        'waveform_postprocessing': 'none',
        'waveform_storage': 'Only exact elementwise float64→float32→float64 round-trip permits float32 NPY; otherwise preserve float64. Both PCM hashes, stored dtype and reversibility recorded. Existing native waveforms unchanged.', 'invalid_payload': 'fail without clipping/floor/repair',
        'derived_payload_retention': {'retained': False,
            'quantization': 'actual write-close-read-import then all official point decodes; retain bytes/file SHA/canonical array hashes and sources; release per point after terminal rows',
            'interpolation': 'retain reencoded endpoint until alpha1 and alpha0p5 terminal rows, then release endpoint and midpoint payloads',
            'resume': 'validate retained wave and permanent provenance; regenerated canonical arrays must match or stop without replacing past evidence',
            'time_stage': 'new recovery-run time payloads remain retained; any later policy revision requires its own ledger and preserved actual wave'},
        'execution': 'one case at a time, at most ten fixed cases per process; fixed source hashes; no tests or dry runs'}
    path = args.output_root / 'latent-contracts' / args.method / f'{args.stage}.json'
    freeze(path, value)
    return sha256(path)


def expected_conditions(adapter, stage):
    if stage == 'quantization':
        return [name + suffix for name in ('quantized_float16', 'quantized_float32')
                for suffix in ['', *('__' + c for c in adapter.capabilities)]]
    if stage == 'interpolation':
        return ['interpolation_input_gain_alpha' + alpha for alpha in ('0', '0p5', '1')]
    return ['time_scale1p25']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('quantization', 'interpolation', 'time'))
    parser.add_argument('--method', required=True, choices=METHODS)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--runtime-cache', required=True, type=Path)
    parser.add_argument('--output-root', type=Path, default=RUN)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if args.stage == 'time' and args.method not in METHODS[:2]:
        raise ValueError('独立した既存時間操作はHNM/WORLDだけに適用します')
    specs = read(args.inputs)
    if not 0 < len(specs) <= 10:
        raise ValueError('正式研究のprocessは1〜10録音に限定します')
    from scripts.all_metrics_control_adapters import build_control_adapter
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    prepared = (verify_prepared(args.runtime_cache, args.method) if args.method not in METHODS[:2]
                else {'method': args.method, 'formal_base': read(ROOT / 'BASELINE.json'),
                      'world_lock_sha256': sha256(ROOT / 'vocoderbench/world.lock.json')})
    seed_all(args.seed)
    started, tick = now(), time.perf_counter()
    adapter = build_control_adapter(args.method, args.runtime_cache / 'src',
        args.runtime_cache / 'models', args.output_root / 'latent-adapter-work' / args.method)
    signature = contract(adapter, args, prepared)
    write_json(args.output_root / 'latent-initializations' / f'{args.stage}-{args.method}-{time.time_ns()}.json',
        {'started_at_utc': started, 'seconds': time.perf_counter() - tick,
         'input_manifest_sha256': sha256(args.inputs), 'contract_sha256': signature})
    runner = {'quantization': quantize_case, 'interpolation': interpolation_case, 'time': time_case}[args.stage]
    failed = False
    for spec in specs:
        z = None
        folder = args.output_root / 'native' / args.method / spec['id']
        progress = {'case': spec['id'], 'method': args.method, 'stage': args.stage,
                    'contract_sha256': signature, 'started_at_utc': now()}
        try:
            if sha256(spec['path']) != spec['sha256']:
                raise ValueError('固定原音hash不一致')
            native_path = folder / 'unedited.json'
            native = read(native_path) if native_path.exists() else {'status': 'pending_native'}
            if native['status'] != 'measured':
                status = 'pending_native' if native['status'].startswith('pending') else 'upstream_failed'
                for name in expected_conditions(adapter, args.stage):
                    target = folder / f'{name}.json'
                    previous = read(target) if target.exists() else None
                    if previous and previous.get('status') == 'measured':
                        raise ValueError('派生成功に対応するnativeが未成功へ変化しています')
                    failure = {'case': spec['id'], 'speaker': spec['speaker'], 'method': args.method,
                               'condition': name, 'status': status, 'value': None, 'contract_sha256': signature,
                               'reason': 'native基準が未成功のため、この正式派生条件は復号していない',
                               'native_source_status': native['status'], 'native_record': str(native_path),
                               'native_record_sha256': sha256(native_path) if native_path.exists() else None}
                    if previous != failure:
                        if previous:
                            write_json(folder / 'failure_history' / f'{name}-{time.time_ns()}.json', previous)
                        write_json(target, failure)
                progress.update(status=status, conditions={name: status for name in expected_conditions(adapter, args.stage)})
                failed = True
                continue
            z, source = native_representation(adapter, folder, args.method)
            runner(adapter, z, source, spec, args, signature, folder)
            progress['conditions'] = {name: read(folder / f'{name}.json')['status']
                for name in expected_conditions(adapter, args.stage)}
            if any(status not in ('measured', 'not_applicable') for status in progress['conditions'].values()):
                failed = True
        except Exception:
            logging.exception('正式表現研究case失敗: %s %s %s', args.stage, args.method, spec['id'])
            progress.update(status='failed', error=traceback.format_exc())
            for name in expected_conditions(adapter, args.stage):
                target = folder / f'{name}.json'
                previous = read(target) if target.exists() else None
                if previous and previous.get('status') in ('measured', 'not_applicable'):
                    continue
                if previous:
                    write_json(folder / 'failure_history' / f'{name}-{time.time_ns()}.json', previous)
                write_json(target, {**progress, 'condition': name, 'value': None,
                                    'failure_stage': 'native_payload_or_stage_execution'})
            progress['conditions'] = {name: read(folder / f'{name}.json')['status']
                                      for name in expected_conditions(adapter, args.stage)}
            failed = True
        finally:
            release(adapter, z)
            progress['finished_at_utc'] = now()
            target = folder / f'latent-{args.stage}-progress.json'
            if target.exists():
                write_json(folder / 'failure_history' / f'{target.stem}-{time.time_ns()}.json', read(target))
            write_json(target, progress)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-worker'))
