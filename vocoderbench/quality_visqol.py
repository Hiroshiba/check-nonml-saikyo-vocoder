"""Google公式ViSQOL CLIのAudio mode。移植版の時間と混同しない。"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

from .quality_core import NotApplicable, file_asset, read_json


class VisqolAudio:
    label, unit, direction = 'ViSQOL Audio（公式CLI）', 'MOS-LQO', 'higher'

    def __init__(self, options, base, work, threads):
        self.provenance = {'algorithm': 'Google-ViSQOL-Audio-CLI',
                           'source': 'https://github.com/google/visqol',
                           'required_sample_rate': 48000, 'wav_quantization': 'round-to-nearest-PCM16-no-clipping',
                           'timing_scope': '毎回のプロセス起動・モデル読込・一時WAV入出力を含む',
                           'process_cpu_scope': 'Python親プロセスのみ。子プロセスCPU時間は未測定。'}
        self.binary = file_asset(options, 'binary', base, self.provenance)
        self.model = file_asset(options, 'model', base, self.provenance)
        if not os.access(self.binary, os.X_OK):
            raise ValueError('ViSQOL binaryに実行権限がありません')
        self.timeout = float(options.get('timeout_seconds', 120))
        if not np.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('timeout_secondsは正の有限値が必要です')
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)

    def score(self, x, y, sr):
        if sr != 48000:
            raise NotApplicable('ViSQOL Audioは48 kHzのみ。このコマンドはアップサンプリングしません')
        def pcm16(z):
            raw = np.rint(z * 32768)
            if raw.min() < -32768 or raw.max() > 32767:
                raise ValueError('ViSQOLのPCM16範囲を超過。クリップ・音量補正して採点しません')
            return raw.astype('<i2')
        reference, output = pcm16(x), pcm16(y)
        with tempfile.TemporaryDirectory(dir=self.work) as directory:
            folder = Path(directory)
            wavfile.write(folder / 'reference.wav', sr, reference)
            wavfile.write(folder / 'output.wav', sr, output)
            command = [str(self.binary), '--reference_file', str(folder / 'reference.wav'),
                       '--degraded_file', str(folder / 'output.wav'),
                       '--similarity_to_quality_model', str(self.model),
                       '--use_speech_mode=false', '--use_lattice_model=false',
                       '--results_csv', str(folder / 'scores.csv'),
                       '--output_debug', str(folder / 'debug.json')]
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
            if result.stdout:
                logging.info('ViSQOL出力:\n%s', result.stdout.rstrip())
            if result.stderr:
                logging.warning('ViSQOL標準エラー:\n%s', result.stderr.rstrip())
            result.check_returncode()
            with (folder / 'scores.csv').open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != 1 or 'moslqo' not in rows[0]:
                raise ValueError('ViSQOLのCSV出力形式または件数が不一致です')
            return float(rows[0]['moslqo']), {'backend': 'official_cli',
                                            'includes_subprocess_startup_and_wav_io': True,
                                            'quantization_bits': 16, 'resampling': 'none',
                                            'csv_bands': {k: v for k, v in rows[0].items() if k not in ('reference', 'degraded')},
                                            'debug': read_json(folder / 'debug.json')}
