"""比較レポートへ載せる実音声の固定区間を、無加工で保存する。"""
import base64
import hashlib
import io
import json

import numpy as np
from scipy.io import wavfile


def collect(samples, case, method, waveform):
    # 方式によって聴きやすい区間を選び直さない。
    selected = case['kind'] == 'natural_speech' or case['id'] == 'harmonic_110_16000'
    if not selected:
        return
    sr = case['sr']
    excerpt = np.asarray(waveform[:min(len(waveform), 2 * sr)], dtype=np.float32)
    if not np.isfinite(excerpt).all():
        return
    buffer = io.BytesIO()
    wavfile.write(buffer, sr, excerpt)
    wav = buffer.getvalue()
    samples.append({
        'case': case['id'], 'method': method,
        'label': '自然音声の固定先頭区間' if case['kind'] == 'natural_speech' else '110 Hzの調波音',
        'data_uri': 'data:audio/wav;base64,' + base64.b64encode(wav).decode('ascii'),
        'sample_rate': sr, 'start_sample': 0, 'n_samples': len(excerpt),
        'reference_kind': 'original_waveform' if method == 'identity' else 'resynthesis',
        'wav_sha256': hashlib.sha256(wav).hexdigest(),
        'peak_amplitude': float(np.max(np.abs(excerpt))) if len(excerpt) else 0.0,
        'format': 'WAV IEEE float32; no gain normalization, clipping or resampling',
    })


def save(samples, output):
    output.mkdir(parents=True, exist_ok=True)
    data = {
        'schema_version': 1,
        'selection_note': '自然音声2区間と110 Hz調波音の固定先頭最大2秒。方式間で同じ区間を使用。'
        '波形は浮動小数点WAVに保存し、音量正規化・クリッピング・リサンプリングはしていません。'
        '再生機器の音量は低めから調整してください。音声例だけから全体の品質を判定しません。',
        'samples': samples,
    }
    (output / 'audio_samples.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8'
    )
