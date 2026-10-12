"""全長の不一致を保持したまま、原音参照指標と予測MOSを記録する。"""
import logging
import math
import traceback

import numpy as np
from scipy.signal import resample_poly

from .. import audio_samples
from ..extended_metrics import measure_extended
from ..metrics import compare_waveforms
from .common import digest, read, write


def measure(args, cases, methods, public):
    samples, rows, originals = [], [], []
    evaluator = None
    if args.mos:
        from ..mos import MosEvaluator
        evaluator = MosEvaluator(cache_root=args.mos_cache, repetitions=1, seed=20261012, threads=4)
        evaluator.prepare()
    for case in cases:
        x, sr = case['x'], case['sr']
        identity = {'case': case['id'], 'method': 'identity', 'status': 'measured'}
        identity['mos'] = evaluator.predict(x, sr, language=case['language'], style=case['style']) if evaluator else {
            'status': 'not_requested', 'value': None}
        originals.append(identity)
        if case['id'] in public:
            audio_samples.collect(samples, case, 'identity', x)
        for method in methods:
            result = args.output / 'native' / method / f'{case["id"]}.json'
            row = read(result) if result.exists() else {'case': case['id'], 'method': method,
                       'status': 'failed', 'error': 'ワーカーが結果を保存できませんでした。ログを確認してください'}
            row.update(kind='natural_speech', language=case['language'], style=case['style'], speaker=case['speaker'])
            row['mos'] = {'status': 'not_requested' if evaluator is None else 'failed', 'value': None}
            try:
                if row['status'] == 'measured':
                    wave_path = result.with_suffix('.npy')
                    if digest(wave_path) != row['output_sha256']:
                        raise ValueError('保存出力が測定記録のSHA-256と一致しません')
                    y_native = np.load(wave_path, allow_pickle=False)
                    nsr = row['native_sample_rate']
                    if evaluator:
                        row['mos'] = evaluator.predict(y_native, nsr, language=case['language'], style=case['style'])
                    y = y_native
                    divisor = math.gcd(sr, nsr)
                    if nsr != sr:
                        y = resample_poly(y, sr // divisor, nsr // divisor)
                    # This remains the strict full-length diagnostic, including length_mismatch.
                    row['measurement'] = compare_waveforms(x, y, sr)
                    n = min(len(x), len(y))
                    row['common_prefix'] = {'samples': n, 'sample_rate': sr,
                        'reference_coverage': n/len(x), 'output_coverage': n/len(y),
                        'alignment': 'none', 'gain_normalization': 'none',
                        'measurement': compare_waveforms(x[:n], y[:n], sr),
                        'extended': measure_extended(x[:n], y[:n], sr)}
                    if case['id'] in public:
                        audio_samples.collect(samples, {**case, 'sr': nsr}, method, y_native)
            except Exception:
                logging.exception('評価に失敗: %s / %s', case['id'], method)
                row['status'] = 'evaluation_failed'
                row['evaluation_error'] = traceback.format_exc()
            rows.append(row)
            # Partial evaluation survives an interrupted MOS run.
            write(args.output / 'evaluation_partial.json', {'resynthesis': rows, 'calibration': originals})
    if evaluator:
        write(args.output / 'mos_provenance.json', evaluator.provenance)
    write(args.output / 'audio_samples.json', {'schema_version': 1, 'samples': samples,
        'selection_note': '許諾された英語例の先頭最大2秒。出力は各方式のネイティブ帯域・全長のまま。音量補正なし。'})
    return rows, originals
