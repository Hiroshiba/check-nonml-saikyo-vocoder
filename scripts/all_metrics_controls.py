"""native波形の厳密読込とpitch/gain評価。復旧後に再実装した新run用source。"""
from __future__ import annotations

import hashlib

import numpy as np

from all_metrics_common import ROOT
from vocoderbench.assessment.common import Inputs, NotApplicable, error_summary, ok
from vocoderbench.assessment.controls import gain, pitch
from vocoderbench.metrics import estimate_f0_yin
from vocoderbench.quality_core import sha256


def checked_audio(record):
    """実file/PCM/長さ/SRを照合する。存在しない旧波形をhashだけで復元扱いしない。"""
    if record.get('status') != 'measured':
        raise ValueError('成功済みnative波形の記録が必要です')
    info = record['audio']
    if sha256(info['path']) != info['file_sha256']:
        raise ValueError('native波形file SHA256が不一致です')
    wave = np.load(info['path'], allow_pickle=False)
    if wave.ndim != 1 or wave.dtype.kind != 'f' or not len(wave) or not np.isfinite(wave).all():
        raise ValueError('native波形は空でない有限1次元float配列が必要です')
    rate = info['sample_rate']
    if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
        raise ValueError('native標本化周波数は正の整数が必要です')
    if len(wave) != info['samples'] or abs(info['seconds'] - len(wave) / rate) > 1e-12:
        raise ValueError('native波形の標本数または秒数が不一致です')
    pcm = hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()
    if pcm != info['float64_sha256']:
        raise ValueError('native波形のfloat64 PCM SHA256が不一致です')
    return wave.astype(np.float64), rate


def relative_epoch_pitch(x, y, rate, mapping, cents):
    """MagPhaseの保存native epoch対応だけを使う。両端追加・正規化・外挿なし。"""
    a, b = (estimate_f0_yin(z, rate) for z in (x, y))
    ta, tb = a['center_samples'] / rate, b['center_samples'] / rate
    if not len(ta) or not len(tb):
        raise NotApplicable('80 msの完全なF0解析窓がありません')
    reference = np.asarray(mapping['reference_seconds'], dtype=float)
    output = np.asarray(mapping['output_seconds'], dtype=float)
    if (reference.ndim != 1 or reference.shape != output.shape or len(reference) < 2
            or not np.isfinite(reference).all() or not np.isfinite(output).all()
            or np.any(np.diff(reference) <= 0) or np.any(np.diff(output) <= 0)):
        raise ValueError('保存epoch対応は同形の有限・狭義単調時刻が必要です')
    source_times = np.interp(tb, output, reference)
    covered = (tb >= output[0]) & (tb <= output[-1]) & (source_times >= ta[0]) & (source_times <= ta[-1])
    indices = np.clip(np.searchsorted(ta, source_times), 0, len(ta) - 1)
    left = np.maximum(indices - 1, 0)
    indices = np.where(abs(ta[left] - source_times) <= abs(ta[indices] - source_times), left, indices)
    expected = a['f0_hz'][indices] * np.exp2(cents / 1200)
    in_range = (expected == 0) | ((expected >= 65) & (expected <= 700))
    selected = covered & in_range
    voiced, observed = expected > 0, b['f0_hz'] > 0
    both = selected & voiced & observed
    errors = 1200 * np.log2(b['f0_hz'][both] / expected[both])
    summary = error_summary(errors)
    result = ok(summary['mae'], 'cent', relative_error=summary, total_frames=len(tb),
        valid_voiced_frames=int(both.sum()), expected_voiced_frames=int((selected & voiced).sum()),
        expected_unvoiced_frames=int((selected & ~voiced).sum()),
        missing_voiced_frames=int((selected & voiced & ~observed).sum()),
        false_voiced_frames=int((selected & ~voiced & observed).sum()),
        unmapped_frames=int((~covered).sum()), out_of_range_frames=int((covered & ~in_range).sum()),
        frame_seconds=tb.tolist(), estimated_output_f0_hz=b['f0_hz'].tolist(),
        time_mapping=mapping, estimator=a['method'],
        limits='既知native epoch対応内のみ。pure pitchまたは独立F0真値精度ではない。')
    result['expected_relative_f0_hz'] = [float(value) if valid else None for value, valid in zip(expected, covered)]
    if not len(errors):
        result.update(status='not_applicable', reason='比較可能な両有声frameがありません')
    return result


def evaluate_control_pair(baseline, output):
    if any(baseline.get(key) != output.get(key) for key in ('case', 'method')):
        raise ValueError('操作と無編集参照のcase/methodが一致しません')
    x, rate = checked_audio(baseline)
    y, other = checked_audio(output)
    if rate != other:
        raise ValueError('同方式native操作の標本化周波数が変わりました')
    condition = output['condition'].split('__')[-1]
    quantities = {'pitch_minus3': -300., 'pitch_plus3': 300., 'gain_minus6': -6., 'gain_plus6': 6.}
    if condition not in quantities:
        raise ValueError(f'未定義のpitch/gain条件です: {condition}')
    control = 'pitch' if condition.startswith('pitch_') else 'gain'
    amount = quantities[condition] / 100 if control == 'pitch' else quantities[condition]
    if output.get('controls', {}).get('control') != control or output['controls'].get('amount') != amount:
        raise ValueError('native操作記録の物理量または操作量が予定条件と不一致です')
    job = {'reference': baseline['audio'], 'output': output['audio']}
    if condition.startswith('pitch_'):
        if output.get('method') == 'magphase':
            if 'parameter_frame_times' not in output:
                raise ValueError('MagPhase pitchの保存native epoch対応がありません')
            measurement = relative_epoch_pitch(x, y, rate, output['parameter_frame_times'], quantities[condition])
        else:
            measurement = pitch({**job, 'target_cents': quantities[condition]}, Inputs(ROOT))
            measurement['valid_voiced_frames'] = measurement['relative_error']['count']
    else:
        measurement = gain({**job, 'target_gain_db': quantities[condition]}, Inputs(ROOT))
    measurement.update(direction='lower', control_reference='same_method_native_unedited_decoded',
        missing_is_zero=False, reference_samples=len(x), output_samples=len(y), sample_rate=rate,
        duration_delta_seconds=(len(y) - len(x)) / rate,
        external_waveform_dsp=False, clipping_or_level_correction=False)
    return {'metric': 'relative_pitch_tracking' if condition.startswith('pitch_') else 'native_gain_tracking',
            'measurement': measurement}


def main():
    from all_metrics_control_eval import main as run
    return run()


if __name__ == '__main__':
    from vocoderbench.logging_utils import run_cli
    raise SystemExit(run_cli(main, 'all-metrics-controls'))
