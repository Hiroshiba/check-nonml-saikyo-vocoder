"""既存音響診断の明示registry。数値fieldを無差別に品質順位へしない。"""
from __future__ import annotations

from all_metrics_common import METHODS, RUN
from all_metrics_rankings_core import finite
from all_metrics_rankings_inputs import definition, value_row

ALLOWED = ('measured', 'ok', 'estimated_consistency_not_ground_truth')


def descriptors():
    values = []

    def add(key, label, unit, direction, path, transform=None, family=0):
        values.append({'id': key, 'label': label, 'unit': unit, 'direction': direction,
                       'path': path, 'transform': transform, 'family': family})

    for index, window in enumerate((5, 20, 80)):
        for field, label, unit in [('log_magnitude_mae_db', '対数振幅MAE', 'dB'),
                                   ('spectral_convergence', 'スペクトル相対誤差', 'ratio')]:
            add(f'existing.stft{window}.{field}', f'{window}ms STFT {label}', unit, 'lower',
                ('measurement', 'mr_stft', index, field))
    add('existing.band_mae', '全時間帯域エネルギーMAE', 'dB', 'lower',
        ('measurement', 'band_energy', 'active_band_mae_db'))
    add('existing.mrstft_mean', '3窓平均MR-STFT対数振幅MAE', 'dB', 'lower',
        ('measurement', 'mr_stft_log_magnitude_mae_db'))
    add('existing.rms_signed', '符号付きRMS差（診断）', 'dB', None, ('measurement', 'rms_gain_error_db'))
    add('existing.rms_absolute', 'RMS絶対差', 'dB', 'lower', ('measurement', 'rms_gain_error_db'), 'absolute')
    add('existing.estoi', 'eSTOI明瞭性推定', 'score', 'higher', ('extended', 'intelligibility', 'estoi', 'value'))
    for field, label, unit in [('output_energy_fraction', '低エネルギー区間の出力エネルギー比', 'fraction'),
                               ('output_rms_dbfs', '低エネルギー区間の出力RMS', 'dBFS'),
                               ('output_peak', '低エネルギー区間の出力peak', 'amplitude')]:
        add('existing.quiet.' + field, label + '（診断）', unit, None, ('extended', 'quiet_regions', field))
    for field, label, unit in [('rms_dbfs', '共通区間RMS', 'dBFS'), ('peak', 'peak', 'amplitude'),
                              ('crest_factor_db', '波高率', 'dB')]:
        add('existing.level.' + field, label + '（診断）', unit, None, ('extended', 'level', 'output', field))
    for field, label, unit in [('at_or_above_full_scale_fraction', '振幅1以上の比率', 'fraction'),
                              ('near_full_scale_fraction', '振幅0.999以上の比率', 'fraction'),
                              ('longest_full_scale_run_samples', '振幅1以上の最長連続長', 'samples')]:
        add('existing.fullscale.' + field, label + '（診断）', unit, None, ('extended', 'full_scale', 'output', field))
    for field, label, direction in [('absolute_difference_cents_median', '推定音高差中央値', 'lower'),
                                    ('absolute_difference_cents_p95', '推定音高差P95', 'lower'),
                                    ('paired_voiced_fraction', '推定有声対応率', 'higher')]:
        add('existing.pitch.' + field, label, 'fraction' if field.endswith('fraction') else 'cent', direction,
            ('extended', 'pitch_consistency', field))
    add('existing.pitch.missing_fraction', '原音推定有声に対する出力有声未検出率', 'fraction', 'lower',
        ('extended', 'pitch_consistency'), 'pitch_missing_rate')
    add('6.local_erb40', '40ms局所聴覚帯域距離', 'dB', 'lower', ('auditory_local', 'value'), family=6)
    for band, label in enumerate(('全帯域', '300–1000Hz', '1000–3000Hz', '3000–6000Hz')):
        for window, ms in enumerate((10, 40)):
            base = ('extended', 'temporal', 'bands', band, 'windows', window)
            for field, text, unit, direction in [('log_rms_mae_db', '対数RMS MAE', 'dB', 'lower'),
                ('rms_envelope_nrmse', 'RMS包絡正規化RMSE', 'ratio', 'lower'),
                ('envelope_correlation', '包絡相関', 'correlation', 'higher'),
                ('rms_gain_error_db', '符号付き包絡RMS差（診断）', 'dB', None)]:
                add(f'existing.envelope.{band}.{ms}.{field}', f'{label} {ms}ms {text}', unit,
                    direction, (*base, 'metrics', field))
            add(f'existing.modulation.{band}.{ms}', f'{label} {ms}ms 変調帯域MAE', 'dB', 'lower',
                (*base, 'modulation_bands', 'active_band_mae_db'))
    return values


def extract(raw, descriptor):
    node, states = raw, []
    try:
        for key in descriptor['path']:
            if isinstance(node, dict) and 'status' in node:
                states.append(node['status'])
            node = node[key]
        if isinstance(node, dict) and 'status' in node:
            states.append(node['status'])
    except (KeyError, IndexError, TypeError):
        state = next((s for s in states if s not in ALLOWED), 'missing_metric_evidence')
        return None, state, {}
    state = next((s for s in states if s not in ALLOWED), 'measured')
    if state != 'measured':
        return None, state, {}
    transform = descriptor['transform']
    detail = {}
    if transform == 'pitch_missing_rate':
        numerator = node.get('reference_voiced_output_unvoiced_frames')
        denominator = node.get('reference_estimated_voiced_frames')
        detail = {'numerator': numerator, 'denominator': denominator,
                  'total_frames': node.get('total_frames')}
        node = numerator / denominator if finite(numerator) and finite(denominator) and denominator > 0 else None
    elif transform == 'absolute' and finite(node):
        node = abs(node)
    return node, 'measured' if node is not None else 'not_applicable', detail


def groups(specs, sources):
    descriptors_ = descriptors()
    output = [definition(item['id'], item['label'], item['family'], item['unit'], item['direction'], specs,
        '全8の固定16kHz共通先頭区間。自然F0絶対真値・知覚総合品質ではない。',
        extraction_path=list(item['path']), transform=item['transform']) for item in descriptors_]
    for spec in specs:
        for method in METHODS:
            raw = sources.row(RUN / 'acoustic/measurements' / f'{spec["id"]}__{method}.json', spec, method,
                              contract=(RUN / 'acoustic/contract.json', 'contract_sha256'))
            for item, group in zip(descriptors_, output):
                value, state, detail = extract(raw, item)
                group['rows'].append(value_row(raw, value, state, **detail))
    return output
