"""16 kHzモノラル音声をPML特徴へ解析し、保存特徴だけから復号する。"""
from pathlib import Path
import json
import logging
import time

import numpy as np
from scipy.io import wavfile

from . import pml
from .logging_utils import LoggedArgumentParser, run_cli


def read_audio(path):
    sr, x = wavfile.read(path)
    if x.ndim != 1:
        raise ValueError('モノラルWAVが必要です。自動ダウンミックスはしません')
    if x.dtype.kind == 'u' and x.dtype.itemsize == 1:
        x = (x.astype(float) - 128) / 128
    elif x.dtype.kind == 'i':
        x = x.astype(float) / (2 ** (8 * x.dtype.itemsize - 1))
    elif x.dtype.kind != 'f':
        raise ValueError('対応外のWAV形式です')
    return np.asarray(x, dtype=np.float64), sr


def main():
    parser = LoggedArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    enc = sub.add_parser('encode', help='WAVから保存特徴を生成')
    enc.add_argument('input', type=Path)
    enc.add_argument('output', type=Path)
    enc.add_argument('--seed', type=int, default=20261015)
    enc.add_argument('--reaper-trace-npz', type=Path,
                     help='未加工REAPER観測5配列を別NPZへ保存（コピー負荷を解析時間に含む）')
    dec = sub.add_parser('decode', help='保存特徴だけからFLOAT WAVを生成')
    dec.add_argument('input', type=Path)
    dec.add_argument('output', type=Path)
    dec.add_argument('--seed', type=int)
    dec.add_argument('--pitch-semitones', type=float, default=0)
    dec.add_argument('--gain-db', type=float, default=0)
    for child in (enc, dec):
        child.add_argument('--timing-json', type=Path, help='I/Oを除く解析または復号RTFを保存')
    args = parser.parse_args()
    reaper_path = getattr(args, 'reaper_trace_npz', None)
    outputs = [path for path in (args.output, args.timing_json, reaper_path) if path is not None]
    resolved = [path.resolve() for path in [args.input, *outputs]]
    if len(set(resolved)) != len(resolved):
        raise ValueError('入力・音声/特徴量・計測JSON・診断NPZは別のパスを指定してください')
    for path in outputs:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'出力先が存在します。別の出力先を指定してください: {path}')
    if args.command == 'encode':
        x, sr = read_audio(args.input)
        trace = {} if reaper_path is not None else None
        begin = time.perf_counter()
        params = pml.encode(x, sr, seed=args.seed, trace=trace)
        seconds = time.perf_counter() - begin
        if trace is not None:
            reaper_arrays = trace['reaper']
            del trace
        pml.save(params, args.output)
        if reaper_path is not None:
            with reaper_path.open('xb') as handle:
                np.savez(handle, allow_pickle=False, **reaper_arrays)
        duration = len(x) / sr
        result = {'analysis_seconds': seconds, 'analysis_rtf': seconds / duration}
        if reaper_path is not None:
            result['reaper_trace_capture_included'] = True
    else:
        params = pml.load(args.input)
        params = pml.edit_parameters(params, pitch_semitones=args.pitch_semitones, gain_db=args.gain_db)
        begin = time.perf_counter()
        y = pml.decode(params, seed=args.seed)
        seconds = time.perf_counter() - begin
        with args.output.open('xb') as handle:
            wavfile.write(handle, params.sample_rate, y.astype(np.float32))
        duration = params.n_samples / params.sample_rate
        result = {'decode_seconds': seconds, 'decode_rtf': seconds / duration}
    result.update(method='pml-lowband-fwcep60-v1', seconds_audio=duration,
                  measurement='単発・ウォームアップなし。I/Oを除く壁時計。正式速度順位には使わない')
    if reaper_path is not None:
        result['measurement'] += '。REAPER診断コピー負荷を含む。診断なしの速度順位に混ぜない'
    if args.timing_json:
        with args.timing_json.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    logging.info('処理完了: %s / %s', args.output, result)
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'pml'))
