"""指輪（LLSM2 Layer1）の固定24 kHz保存・復号入口。"""

import argparse
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from .logging_utils import run_cli
from .references.current_base import record
from .yubiwa import Layer1Engine, SAMPLE_RATE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-cache', required=True, type=Path,
                        help='固定revisionを準備したLLSM2の隔離キャッシュ')
    commands = parser.add_subparsers(dest='operation', required=True)
    encode = commands.add_parser('encode', help='24 kHz単声道音声をLayer1で保存')
    encode.add_argument('input', type=Path)
    encode.add_argument('output', type=Path)
    decode = commands.add_parser('decode', help='保存Layer1を独立復元して24 kHzで復号')
    decode.add_argument('input', type=Path)
    decode.add_argument('output', type=Path)
    decode.add_argument('--pitch-semitones', type=int, choices=(-3, 0, 3), default=0)
    args = parser.parse_args()
    record(args.runtime_cache)
    engine = Layer1Engine(args.runtime_cache / 'native/libllsm_speed.so')
    if args.operation == 'encode':
        x, rate = sf.read(args.input, dtype='float64', always_2d=False)
        if rate != SAMPLE_RATE or np.asarray(x).ndim != 1:
            raise ValueError('入力は24 kHzの単声道音声に限定します。再標本化しません')
        engine.analyze_to_saved(x, rate, args.output)
        logging.info('Layer1を保存: %s', args.output)
    else:
        if args.output.exists():
            raise FileExistsError(args.output)
        y, rate = engine.decode_from_saved(args.input, pitch_semitones=args.pitch_semitones)
        sf.write(args.output, y, rate, subtype='FLOAT')
        logging.info('Layer1を復号: %s / %d Hz / %d samples', args.output, rate, len(y))
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'yubiwa'))
