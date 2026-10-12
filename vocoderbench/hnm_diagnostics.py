"""自作表現の解析誤差・細部の影響を数値として記録する。"""
from dataclasses import replace

import numpy as np

from . import hnm
from .metrics import pitch_metrics


def feature_pitch(params, truth, sr):
    if truth is None:
        return {'status': 'natural_speech_has_no_ground_truth'}
    indices = np.minimum(np.rint(params.time * sr).astype(int), len(truth) - 1)
    target = truth[indices]
    expected, detected = target > 0, params.f0 > 0
    valid = expected & detected
    errors = abs(1200 * np.log2(params.f0[valid] / target[valid]))
    return {'status': 'known_truth_at_parameter_frame_times',
            'expected_voiced_frames': int(expected.sum()), 'valid_voiced_frames': int(valid.sum()),
            'missing_voiced_frames': int((expected & ~detected).sum()),
            'false_voiced_frames': int((~expected & detected).sum()),
            'abs_error_cents_p95': float(np.percentile(errors, 95)) if len(errors) else None}


def inspect(case, params):
    if case['sr'] != 16000 or case['id'] not in ('harmonic_110_16000', 'harmonic_220_16000'):
        return []
    rows = []
    for details in (True, False):
        selected = params if details else hnm.without_details(params)
        for semitones in (-3, 3):
            edited = hnm.edit_parameters(selected, pitch_semitones=semitones)
            y = hnm.decode(edited, seed=0)
            rows.append({'case': case['id'], 'diagnostic': 'phase_detail_pitch', 'status': 'measured',
                         'details': details, 'pitch_semitones': semitones,
                         'label': f'位相細部{"あり" if details else "なし"}・音高{semitones:+}半音',
                         'pitch': pitch_metrics(y, case['sr'], case['f0_truth'] * 2 ** (semitones / 12))})
    noise = hnm.decode(replace(params, harmonic_envelope=np.zeros_like(params.harmonic_envelope)), seed=0)
    rows.append({'case': case['id'], 'diagnostic': 'noise_only_periodicity', 'label': '雑音成分だけの周期性', 'status': 'measured',
                 'pitch': pitch_metrics(noise, case['sr'], np.zeros(len(noise))),
                 'rms': float(np.sqrt(np.mean(noise ** 2)))})
    return rows
