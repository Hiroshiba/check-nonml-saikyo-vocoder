"""一つの方式を隔離環境で読み込み、入力群を順に再合成する。"""
import argparse
import ctypes
import importlib
import logging
import math
import os
from pathlib import Path
import platform
import random
import sys
import time
import traceback

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import torch

from ..logging_utils import run_cli
from .catalog import METHODS
from .common import digest, now, read, verify_prepared, write


BUILDERS = {
    'world_harvest': ('adapters_dsp', 'build_world_harvest'),
    'llsm2': ('adapters_dsp', 'build_llsm'), 'magphase': ('adapters_dsp', 'build_magphase'),
    'facodec': ('adapters_neural', 'build_facodec'), 'hifiglot': ('adapters_neural', 'build_hifiglot'),
    'dac': ('adapters_neural', 'build_dac'), 'golf': ('adapters_source', 'build_golf'),
    'sifigan': ('adapters_source', 'build_sifigan'),
}


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    # LLSM2's C noise path uses the process RNG; record the seed even where an upstream ignores it.
    ctypes.CDLL(None).srand(ctypes.c_uint(seed))


def run_case(adapter, spec, args):
    path = args.output / f'{spec["id"]}.json'
    if path.exists():
        previous = read(path)
        if previous['status'] == 'measured' or not args.retry_failed:
            return
        write(args.output / 'failure_history' / f'{spec["id"]}-{time.time_ns()}.json', previous)
    row = {'case': spec['id'], 'method': args.method, 'status': 'failed', 'started_at': now(),
           'native_sample_rate': adapter.sr, 'seed': args.seed, 'metrics_include_timing': False}
    output_path = args.output / f'{spec["id"]}.npy'
    output_path.unlink(missing_ok=True)
    z = None
    try:
        check_input = Path(spec['path'])
        if digest(check_input) != spec['sha256']:
            raise ValueError('入力の固定ハッシュが一致しません')
        x = np.load(check_input, allow_pickle=False).astype(np.float64)
        if x.ndim != 1 or len(x) < int(spec['sample_rate'] * .1) or not np.isfinite(x).all():
            raise ValueError('入力は100 ms以上の有限なモノラル波形にしてください')
        start = time.perf_counter()
        divisor = math.gcd(spec['sample_rate'], adapter.sr)
        if spec['sample_rate'] != adapter.sr:
            x = resample_poly(x, adapter.sr // divisor, spec['sample_rate'] // divisor)
        x = np.ascontiguousarray(x)
        wav = args.output / f'{spec["id"]}.input.wav'
        if args.method == 'magphase':
            # REAPER receives integer WAV; quantization is explicit and its exact samples are retained.
            if np.max(np.abs(x)) > 1:
                raise ValueError('MagPhaseのPCM16入力範囲を超えました。暗黙にクリップしません')
            sf.write(wav, x, adapter.sr, subtype='PCM_16')
            x, _ = sf.read(wav, dtype='float64')
            row['input_quantization'] = 'PCM16 (MagPhase/REAPER file API only)'
        else:
            row['input_quantization'] = 'none'
        row['resampling_and_input_io_s'] = time.perf_counter() - start
        row['native_input_samples'] = len(x)
        row['native_input_sha256'] = __import__('hashlib').sha256(x.astype('<f8').tobytes()).hexdigest()
        duration = len(x) / adapter.sr
        seed_all(args.seed)
        with torch.inference_mode():
            t0 = time.perf_counter()
            z = adapter.encode(x, wav)
            t1 = time.perf_counter()
            y = adapter.decode(z)
            t2 = time.perf_counter()
        if hasattr(y, 'as_tensor'):
            y = y.as_tensor()
        if isinstance(y, torch.Tensor):
            y = y.detach().cpu().numpy()
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if not len(y) or not np.isfinite(y).all():
            raise ValueError('出力波形が空または非有限値です')
        if np.max(np.abs(x)) > 1e-8 and np.max(np.abs(y)) < 1e-10:
            raise ValueError('非無音入力に対して無音が返されました')
        np.save(output_path, y, allow_pickle=False)
        row.update(status='measured', output_sha256=digest(output_path), output_samples=len(y),
                   length_delta_samples=len(y)-len(x), analysis_s=t1-t0, synthesis_s=t2-t1,
                   total_s=t2-t0, rtf=(t2-t0)/duration, output_peak=float(np.max(np.abs(y))),
                   output_rms=float(np.sqrt(np.mean(y*y))), finished_at=now())
        if hasattr(adapter, 'stage_times'):
            row['analysis_stages'] = dict(adapter.stage_times)
    except Exception:
        logging.exception('既存方式の解析・合成に失敗: %s / %s', args.method, spec['id'])
        row['error'] = traceback.format_exc()
    finally:
        if z is not None and hasattr(adapter, 'release'):
            adapter.release(z)
    write(path, row)
    logging.info('%s / %s: %s', args.method, spec['id'], row['status'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=METHODS, required=True)
    parser.add_argument('--runtime-cache', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    start = time.perf_counter()
    seed_all(args.seed)
    if args.method == 'hnm':
        from .current_base import build, record
        spec = record()
        contract = read(args.output.parent.parent / 'contract.json')
        if spec != contract['current_base']:
            raise ValueError('現在のベースのコード・依存・識別子が固定条件と一致しません')
        adapter = build(args.seed)
    else:
        spec = verify_prepared(args.runtime_cache, args.method)
        module, name = BUILDERS[args.method]
        adapter = getattr(importlib.import_module('.' + module, __package__), name)(
            args.runtime_cache / 'src', args.runtime_cache / 'models', args.output)
    write(args.output / 'implementation.json', {'method': args.method, 'prepared': spec,
          'runtime': {'python': sys.version, 'torch': torch.__version__, 'threads': args.threads,
                      'cpu_count': os.cpu_count(), 'processor': platform.processor(), 'device': 'cpu'},
          'initialization_s': time.perf_counter()-start, 'details': adapter.info})
    cases = read(args.inputs)
    for case in cases:
        run_case(adapter, case, args)
    return int(any(read(args.output / f'{c["id"]}.json')['status'] != 'measured' for c in cases))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'reference-worker'))
