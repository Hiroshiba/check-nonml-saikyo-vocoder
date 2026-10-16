"""固定120録音のPML解析・実保存・復号。公開用に引数化した研究入口。"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def freeze(path, value):
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError(f'再開時の測定条件が異なります: {path}')
    if not path.exists():
        write(path, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # 数値ライブラリを読む前に指定。環境差は保存し、同時実行は利用者が避ける。
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '2'
    import numpy as np
    from vocoderbench.pml import decode, encode, load, save

    output = args.output.resolve()
    spec = json.loads(args.input_manifest.read_text())
    cases = spec['cases']
    if len(cases) != 120 or len({c['id'] for c in cases}) != 120:
        raise ValueError('固定120録音の重複しない入力が必要です')
    for case in cases:
        if case['input']['sample_rate'] != 16000 or not 0 < case['common_samples'] <= case['input']['excerpt_samples']:
            raise ValueError('入力周波数・共通窓の長さが不正です')
        if Path(case['id']).name != case['id']:
            raise ValueError('録音IDにディレクトリを含められません')
    resolved = {**spec, 'cases': [{**c, 'input': {**c['input'], 'path': str((args.input_root / c['input']['path']).resolve())}} for c in cases]}
    freeze(output / 'input-contract.json', resolved)
    source = ROOT / 'vocoderbench/pml'
    contract = dict(
        method='pml_fwcep60_lowband_package_v1', seed=0,
        input_sha256=sha(output / 'input-contract.json'),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(source.glob('*.py'))},
        driver_sha256=sha(__file__), driver_version='portable-native-v1',
        sample_rate=16000, source_normalization=False, clip=False,
        worker_count=1, blas_threads=2, python=platform.python_version(),
        timing='Sequential analysis/save/load/decode; wall and CPU; no warmup. Not a same-machine historical speed ranking.',
        formal_base='hnm-v3', adoption='pending',
    )
    freeze(output / 'native-contract.json', contract)
    signature = sha(output / 'native-contract.json')
    for index, case in enumerate(cases):
        folder = output / 'native' / case['id']
        target = folder / 'record.json'
        inp = (args.input_root / case['input']['path']).resolve()
        if sha(inp) != case['input']['sha256']:
            raise ValueError('元入力のSHAが異なります')
        if target.exists():
            old = json.loads(target.read_text())
            if old['contract_sha256'] != signature:
                raise ValueError('保存済み録音の測定条件が異なります')
            if old['status'] == 'measured':
                if any(sha(old[k]['path']) != old[k]['sha256'] for k in ('audio', 'payload')):
                    raise ValueError('保存済み成果物のSHAが異なります')
                continue
            raise ValueError(f'未完了記録があります。別outputで再実行してください: {target}')
        row = dict(case=case['id'], speaker=case['speaker'], method=contract['method'],
                   contract_sha256=signature, status='running',
                   input={**case['input'], 'path': str(inp)})
        write(target, row)
        try:
            if sha(inp) != case['input']['sha256']:
                raise ValueError('元入力のSHAが異なります')
            x = np.load(inp, allow_pickle=False)
            if x.ndim != 1 or len(x) != case['input']['excerpt_samples']:
                raise ValueError('入力の形状・長さが固定契約と異なります')
            wall, cpu = time.perf_counter(), time.process_time()
            parameters = encode(x, 16000, seed=0)
            analysis, analysis_cpu = time.perf_counter() - wall, time.process_time() - cpu
            payload = folder / 'parameters.pml'
            wall = time.perf_counter()
            save(parameters, payload)
            save_seconds = time.perf_counter() - wall
            del parameters
            wall = time.perf_counter()
            parameters = load(payload)
            load_seconds = time.perf_counter() - wall
            wall, cpu = time.perf_counter(), time.process_time()
            y = decode(parameters)
            decoding, decode_cpu = time.perf_counter() - wall, time.process_time() - cpu
            wave = folder / 'wave.npy'
            np.save(wave, y, allow_pickle=False)
            seconds = len(x) / 16000
            row.update(
                status='measured', common_samples=case['common_samples'],
                audio=dict(path=str(wave), sha256=sha(wave), samples=len(y), sample_rate=16000,
                           bytes=wave.stat().st_size, peak=float(np.max(np.abs(y))),
                           over_one_samples=int(np.count_nonzero(np.abs(y) > 1))),
                payload=dict(path=str(payload), sha256=sha(payload), bytes=payload.stat().st_size,
                             bytes_per_second=payload.stat().st_size / seconds, frames=len(parameters.f0)),
                timing=dict(analysis_wall_seconds=analysis, analysis_cpu_seconds=analysis_cpu,
                            analysis_rtf=analysis / seconds, save_wall_seconds=save_seconds,
                            load_wall_seconds=load_seconds, decode_wall_seconds=decoding,
                            decode_cpu_seconds=decode_cpu, decode_rtf=decoding / seconds),
            )
        except Exception as error:
            logging.exception('解析・復号に失敗: %s', case['id'])
            row.update(status='failed', reason=str(error), traceback=traceback.format_exc())
        write(target, row)
        logging.info('%d/120 %s %s', index + 1, case['id'], row['status'])
    write(output / 'native-summary.json', dict(
        contract_sha256=signature,
        rows=[json.loads((output / 'native' / c['id'] / 'record.json').read_text()) for c in cases],
    ))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        main()
    except Exception:
        logging.exception('正式PML解析・復号が中断しました')
        raise
