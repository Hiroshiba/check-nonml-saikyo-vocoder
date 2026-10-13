"""保存済みreferenceスキーマの目的別指標。波形や測定器は再実行しない。"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    path: tuple
    family: str
    higher: bool | None = False
    transform: str = ''


COMMON = ('common_prefix',)
MEASUREMENT = (*COMMON, 'measurement')
EXTENDED = (*COMMON, 'extended')
PITCH = (*EXTENDED, 'pitch_consistency')
METRICS = [
    Metric('mos', '予測MOS ↑', ('mos', 'value'), '全長の予測音質', True),
    Metric('estoi', 'eSTOI ↑', (*EXTENDED, 'intelligibility', 'estoi', 'value'), '明瞭性', True),
    Metric('stft', 'スペクトル誤差 dB ↓', (*MEASUREMENT, 'mr_stft_log_magnitude_mae_db'), 'スペクトル'),
    Metric('band', '帯域エネルギー絶対誤差 dB ↓', (*MEASUREMENT, 'band_energy', 'active_band_mae_db'), 'スペクトル'),
    Metric('level', 'レベル絶対誤差 dB ↓', (*MEASUREMENT, 'rms_gain_error_db'), '音量', transform='absolute'),
    Metric('signed_level', '符号付きレベル差 dB', (*MEASUREMENT, 'rms_gain_error_db'), '音量', None),
    Metric('pitch', 'F0推定差 P95 cent ↓', (*PITCH, 'absolute_difference_cents_p95'), 'F0推定整合性'),
    Metric('pitch_median', 'F0推定差 中央値 cent ↓', (*PITCH, 'absolute_difference_cents_median'), 'F0推定整合性'),
    Metric('voicing_loss', '参照有声推定の欠測率 ↓', (*PITCH, 'reference_voiced_output_unvoiced_frames'), 'F0推定整合性', transform='voicing_loss'),
    Metric('paired_voicing', '参照有声推定の両有声率 ↑', (*PITCH, 'paired_voiced_fraction'), 'F0推定整合性', True),
    Metric('full_scale', '振幅1以上の割合 ↓', (*EXTENDED, 'full_scale', 'output', 'at_or_above_full_scale_fraction'), '振幅上限'),
    Metric('near_full_scale', '振幅0.999以上の割合', (*EXTENDED, 'full_scale', 'output', 'near_full_scale_fraction'), '振幅上限', None),
    Metric('full_scale_run', '振幅1以上の最長連続標本数', (*EXTENDED, 'full_scale', 'output', 'longest_full_scale_run_samples'), '振幅上限', None),
    Metric('quiet_rms', '低エネルギー区間の出力RMS dBFS', (*EXTENDED, 'quiet_regions', 'output_rms_dbfs'), '低エネルギー区間', None),
    Metric('quiet_peak', '低エネルギー区間の出力ピーク', (*EXTENDED, 'quiet_regions', 'output_peak'), '低エネルギー区間', None),
    Metric('quiet_energy', '低エネルギー区間の出力エネルギー比', (*EXTENDED, 'quiet_regions', 'output_energy_fraction'), '低エネルギー区間', None),
    Metric('rtf', 'RTF（単回診断）', ('rtf',), '全長・処理時間', None),
    Metric('length_ms', '符号付き生成長差 ms', ('length_delta_samples',), '全長・処理時間', None, 'milliseconds'),
    Metric('reference_coverage', '原音の被覆率', (*COMMON, 'reference_coverage'), '全長・処理時間', None),
    Metric('output_coverage', '出力の被覆率', (*COMMON, 'output_coverage'), '全長・処理時間', None),
    Metric('native_peak', 'ネイティブ全長出力ピーク', ('output_peak',), '全長・処理時間', None),
    Metric('native_rms', 'ネイティブ全長出力RMS', ('output_rms',), '全長・処理時間', None),
    Metric('analysis_s', '解析秒数（単回）', ('analysis_s',), '全長・処理時間', None),
    Metric('synthesis_s', '合成秒数（単回）', ('synthesis_s',), '全長・処理時間', None),
]
for key, label in (('rms_dbfs', 'RMS dBFS'), ('peak', 'ピーク振幅'),
                   ('peak_dbfs', 'ピーク dBFS'), ('crest_factor_db', 'クレストファクター dB'),
                   ('mean', '波形平均')):
    METRICS.append(Metric('output_' + key, '共通区間出力' + label,
                          (*EXTENDED, 'level', 'output', key), '音量', None))
for window in (5, 20, 80):
    for key, label in (('log_magnitude_mae_db', '振幅dB誤差'), ('spectral_convergence', '相対スペクトル誤差')):
        METRICS.append(Metric(f'stft_{window}_{key}', f'{window} ms窓 {label} ↓',
                             (*MEASUREMENT, 'mr_stft', ('window_ms', window), key), 'スペクトル'))
for low, high in ((0, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000)):
    METRICS.append(Metric(f'band_{low}_{high}', f'{low}–{high} Hz 符号付き差 dB',
                         (*MEASUREMENT, 'band_energy', 'bands', ('low_hz', low), 'delta_db'), '帯域別音量', None))
for band_index, band in enumerate(('全帯域', '300–1000 Hz', '1000–3000 Hz', '3000–6000 Hz')):
    for window in (10, 40):
        path = (*EXTENDED, 'temporal', 'bands', ('name', band), 'windows', ('window_ms', window))
        family = f'時間包絡：{band}・{window} ms'
        for key, label, higher in (('rms_envelope_nrmse', '包絡NRMSE ↓', False),
                                   ('log_rms_mae_db', '包絡dB絶対誤差 ↓', False),
                                   ('envelope_correlation', '包絡相関 ↑', True),
                                   ('rms_gain_error_db', '包絡の符号付きレベル差 dB', None)):
            name = 'envelope' if band_index == 0 and window == 10 and key == 'rms_envelope_nrmse' else f'temporal_{band_index}_{window}_{key}'
            METRICS.append(Metric(name, f'{band} {window} ms {label}', (*path, 'metrics', key), family, higher))
        name = 'modulation' if band_index == 0 and window == 40 else f'modulation_{band_index}_{window}'
        METRICS.append(Metric(name, f'{band} {window} ms 変調絶対誤差 dB ↓',
                             (*path, 'modulation_bands', 'active_band_mae_db'), family))
        for low, high in ((2, 8), (8, 20), (20, 50)):
            METRICS.append(Metric(f'modulation_{band_index}_{window}_{low}', f'変調{low}–{high} Hz 符号付き差 dB',
                                 (*path, 'modulation_bands', 'bands', ('low_hz', low), 'delta_db'), family, None))
METRICS = tuple(METRICS)
BY_KEY = {metric.key: metric for metric in METRICS}
SUCCESS = {'ok', 'measured', 'estimated_consistency_not_ground_truth'}
REASONS = {'not_run': '記録がなく未実行', 'not_measured': '未測定', 'not_requested': '未要求',
           'failed': '処理失敗', 'evaluation_failed': '評価処理失敗', 'length_mismatch': '長さ不一致',
           'no_reference_quiet_blocks': '参照の低エネルギー区間なし',
           'less_than_one_second_of_envelope': '包絡が1秒未満',
           'no_complete_frames': '完全な分析窓なし', 'outside_nyquist': '対象帯域がNyquist以上',
           'insufficient_active_frames': 'eSTOIの有効フレーム不足',
           'reference_no_ac_energy': '参照の交流成分なし', 'output_no_ac_energy': '出力の交流成分なし',
           'no_active_reference_bands': '参照の有効帯域なし',
           'zero_reference_energy': '参照エネルギーがゼロ', 'nonfinite_waveform': '非有限波形',
           'empty_waveform': '空波形', 'numerically_unreliable': '数値計算が不安定'}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def extract(row, metric):
    """値と欠測理由を返す。保存値だけを集計し、欠測をゼロへ補完しない。"""
    if row.get('status') in {'failed', 'not_run'}:
        status = row['status']
        return None, str(row.get('error') or REASONS[status])
    node, ancestors = row, []
    for part in metric.path:
        if isinstance(node, dict):
            ancestors.append(node)
        if isinstance(part, tuple):
            node = next((item for item in node if item.get(part[0]) == part[1]), None) if isinstance(node, list) else None
        else:
            node = node.get(part) if isinstance(node, dict) else None
    parent = ancestors[-1] if ancestors else {}
    status = parent.get(str(metric.path[-1]) + '_status')
    if status and status not in SUCCESS:
        return None, REASONS.get(status, f'記録された状態: {status}')
    if metric.key == 'mos' and parent.get('status') != 'measured':
        status = parent.get('status', 'not_measured')
        return None, str(parent.get('reason') or parent.get('error') or REASONS.get(status, status))
    if finite(node):
        if metric.transform == 'absolute':
            node = abs(node)
        elif metric.transform == 'milliseconds':
            rate = row.get('native_sample_rate')
            if not finite(rate) or rate <= 0:
                return None, 'ネイティブ標本化周波数が不明'
            node = 1000 * node / rate
        elif metric.transform == 'voicing_loss':
            denominator = ancestors[-1].get('reference_estimated_voiced_frames', 0)
            if not denominator:
                return None, '参照が有声と推定されたフレームなし'
            node /= denominator
        return float(node), None
    for item in reversed(ancestors):
        if item.get('reason') or item.get('error'):
            return None, str(item.get('reason') or item['error'])
        status = item.get('status')
        if status and status not in SUCCESS:
            return None, REASONS.get(status, f'記録された状態: {status}')
    parent = ancestors[-1] if ancestors else {}
    if metric.key.startswith('pitch') and parent.get('both_estimated_voiced_frames') == 0:
        return None, '原音・出力の双方が有声と推定されたフレームなし'
    if metric.key == 'paired_voicing' and not parent.get('reference_estimated_voiced_frames'):
        return None, '参照が有声と推定されたフレームなし'
    if parent.get('output_zero_energy') or parent.get('zero_energy'):
        return None, '出力エネルギーがゼロで対数値などが未定義'
    if parent.get('active_band_count') == 0:
        return None, '参照の有効帯域なし'
    if parent.get('reference_mean_power') == 0:
        return None, '参照エネルギーがゼロで比が未定義'
    if metric.path[-1] == 'envelope_correlation':
        return None, '相関の分母がゼロまたはフレーム不足'
    if node is not None:
        return None, '非有限値または数値以外の記録'
    return None, '値が未記録・未定義（元JSONに追加理由なし）'
