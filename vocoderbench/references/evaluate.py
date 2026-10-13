"""全長の不一致を保持したまま、原音参照指標と予測MOSを記録する。"""
import hashlib
import logging
import math
import traceback

import numpy as np
from scipy.signal import resample_poly

from .. import audio_samples
from ..extended_metrics import measure_extended
from ..metrics import compare_waveforms
from .common import digest, read, write
from .evaluation_cache import EvaluationCache, MosMeasurements


def acoustic(row, previous, x, y_native, sr, retry_failed, cache):
    if previous.get('status') == 'measured' and all(
            key in previous for key in ('measurement', 'common_prefix')):
        row.update(measurement=previous['measurement'], common_prefix=previous['common_prefix'])
        logging.info('保存済みの音響評価を再利用: %s / %s', row['case'], row['method'])
        return
    if previous.get('status') == 'evaluation_failed':
        if not retry_failed:
            row.update(status='evaluation_failed', evaluation_error=previous.get('evaluation_error'))
            return
        cache.archive(previous, '失敗した音響評価を明示指定で再試行')
    nsr = row['native_sample_rate']
    divisor = math.gcd(sr, nsr)
    y = resample_poly(y_native, sr // divisor, nsr // divisor) if nsr != sr else y_native
    # 全長診断のlength_mismatchと、共通先頭区間の補助指標を分離する。
    row['measurement'] = compare_waveforms(x, y, sr)
    n = min(len(x), len(y))
    row['common_prefix'] = {'samples': n, 'sample_rate': sr,
        'reference_coverage': n/len(x), 'output_coverage': n/len(y),
        'alignment': 'none', 'gain_normalization': 'none',
        'measurement': compare_waveforms(x[:n], y[:n], sr),
        'extended': measure_extended(x[:n], y[:n], sr)}


def measure(args, cases, methods, public):
    samples, rows, originals = [], [], []
    cache = EvaluationCache(args.output)
    mos = MosMeasurements(args, cache)
    for case in cases:
        x, sr = case['x'], case['sr']
        reference = {'pcm_sha256': hashlib.sha256(x.astype('<f8').tobytes()).hexdigest(),
                     'sample_rate': sr, 'language': case['language'], 'style': case['style'], 'speaker': case['speaker'],
                     'speaker_gender_as_distributed': case.get('speaker_gender_as_distributed', 'unknown')}
        identity = {'case': case['id'], 'method': 'identity', 'status': 'measured',
                    'evaluation_input': reference, 'speaker': case['speaker'],
                    'speaker_gender_as_distributed': case.get('speaker_gender_as_distributed', 'unknown'),
                    'language': case['language'], 'style': case['style']}
        previous = cache.lookup(case['id'], 'identity', reference)
        identity['mos'] = mos.measure(identity, previous, x, sr, case)
        cache.save(identity)
        originals.append(identity)
        if case['id'] in public:
            audio_samples.collect(samples, case, 'identity', x)
        for method in methods:
            result = args.output / 'native' / method / f'{case["id"]}.json'
            row = {'case': case['id'], 'method': method, 'status': 'failed',
                   'mos': {'status': 'not_requested' if not args.mos else 'not_measured', 'value': None}}
            try:
                if not result.exists():
                    raise FileNotFoundError('ワーカーが結果を保存できませんでした。ログを確認してください')
                row.update(read(result))
                if row['status'] == 'measured':
                    wave_path = result.with_suffix('.npy')
                    if digest(wave_path) != row['output_sha256']:
                        raise ValueError('保存出力が測定記録のSHA-256と一致しません')
                    y_native = np.load(wave_path, allow_pickle=False)
                    nsr = row['native_sample_rate']
                    signature = {'reference': reference, 'output_sha256': row['output_sha256'],
                                 'native_sample_rate': nsr}
                    previous = cache.lookup(case['id'], method, signature)
                    row['evaluation_input'] = signature
                    # 音響だけの再実行でも、同じ波形に対する既存MOSは維持する。
                    row['mos'] = previous.get('mos', row['mos'])
                    acoustic(row, previous, x, y_native, sr, args.retry_failed, cache)
                    if row['status'] == 'measured':
                        # MOS実行中に中断しても完了済みの音響評価を残す。
                        row.update(kind='natural_speech', language=case['language'],
                                   style=case['style'], speaker=case['speaker'],
                                   speaker_gender_as_distributed=case.get('speaker_gender_as_distributed', 'unknown'))
                        cache.save(row)
                        row['mos'] = mos.measure(row, previous, y_native, nsr, case)
                        if case['id'] in public:
                            audio_samples.collect(samples, {**case, 'sr': nsr}, method, y_native)
            except Exception:
                logging.exception('評価に失敗: %s / %s', case['id'], method)
                row['status'] = 'evaluation_failed'
                row['evaluation_error'] = traceback.format_exc()
            row.update(kind='natural_speech', language=case['language'], style=case['style'], speaker=case['speaker'],
                                   speaker_gender_as_distributed=case.get('speaker_gender_as_distributed', 'unknown'))
            rows.append(row)
            cache.save(row)
    write(args.output / 'audio_samples.json', {'schema_version': 1, 'samples': samples,
        'selection_note': '許諾された英語例の先頭最大2秒。出力は各方式のネイティブ帯域・全長のまま。音量補正なし。'})
    return rows, originals
