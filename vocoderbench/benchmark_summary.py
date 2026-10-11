"""固定比較の目的別集計。発話内seedを独立話者として数えない。"""
from collections import defaultdict
import numpy as np

# key, 表示, 大きいほど良いか。全体品質の加重総合点は作らない。
METRICS = (
    ('mos', '予測MOS ↑', True), ('estoi', 'eSTOI ↑', True),
    ('envelope', '10 ms包絡誤差 ↓', False), ('stft', 'スペクトル誤差 dB ↓', False),
    ('band', '帯域誤差 dB ↓', False), ('level', 'レベル絶対誤差 dB ↓', False),
    ('modulation', '変調誤差 dB ↓', False), ('pitch', 'F0推定差 p95 cent ↓', False),
    ('voicing_loss', '参照有声推定の欠測率 ↓', False),
    ('full_scale', '振幅上限超過率 ↓', False),
)


def value(row, key):
    ext = row.get('extended', {})
    seeds = row.get('seed_summary', {})
    mapping = {'envelope': '全帯域_10ms_rms_envelope_nrmse', 'stft': 'mr_stft_db',
               'band': 'band_mae_db', 'modulation': '全帯域_40ms_modulation_mae_db'}
    if key in mapping:
        return seeds.get(mapping[key], {}).get('mean')
    if key == 'mos':
        return row.get('mos', {}).get('value')
    if key == 'estoi':
        return (ext.get('intelligibility') or {}).get('estoi', {}).get('value')
    if key == 'level':
        values = [r.get('values', {}).get('rms_gain_error_db') for r in row.get('seed_diagnostics', [])]
        valid = [abs(v) for v in values if v is not None]
        return float(np.mean(valid)) if valid else None
    if key == 'pitch':
        return (ext.get('pitch_consistency') or {}).get('absolute_difference_cents_p95')
    if key == 'voicing_loss':
        item = ext.get('pitch_consistency') or {}
        denominator = item.get('reference_estimated_voiced_frames', 0)
        return item.get('reference_voiced_output_unvoiced_frames', 0) / denominator if denominator else None
    if key == 'full_scale':
        return (ext.get('full_scale') or {}).get('output', {}).get('at_or_above_full_scale_fraction')
    raise ValueError(key)


def summarize(rows, key, higher=False):
    values = [value(row, key) for row in rows]
    valid = np.asarray([v for v in values if v is not None and np.isfinite(v)])
    count = max(1, int(np.ceil(len(valid) * .05)))
    tail = np.sort(valid)[:count] if higher else np.sort(valid)[-count:]
    return {'valid': len(valid), 'total': len(rows),
            'mean': float(np.mean(valid)) if len(valid) else None,
            'median': float(np.median(valid)) if len(valid) else None,
            'worst_5_percent_mean': float(np.mean(tail)) if len(valid) else None}


def paired(rows, references, key, repetitions=2000):
    clusters = defaultdict(list)
    for row in rows:
        a, b = value(row, key), value(references.get(row['case'], {}), key)
        if a is not None and b is not None and np.isfinite(a) and np.isfinite(b):
            clusters[(row['speaker_group'], row['speaker'])].append(a - b)
    groups = list(clusters.values())
    if not groups:
        return {'paired': 0, 'total': len(rows), 'mean_difference': None, 'speaker_bootstrap_95': None}
    values = [v for group in groups for v in group]
    rng = np.random.default_rng(20261012)
    sample_sums, sample_counts = np.zeros(repetitions), np.zeros(repetitions)
    for language in sorted({language for language, _ in clusters}):
        stratum = [v for (lang, _), v in clusters.items() if lang == language]
        sums, counts = np.array([sum(g) for g in stratum]), np.array([len(g) for g in stratum])
        selections = rng.integers(len(stratum), size=(repetitions, len(stratum)))
        sample_sums += sums[selections].sum(axis=1)
        sample_counts += counts[selections].sum(axis=1)
    means = sample_sums / sample_counts
    return {'paired': len(values), 'total': len(rows), 'speakers': len(groups),
            'mean_difference': float(np.mean(values)),
            'speaker_bootstrap_95': np.percentile(means, [2.5, 97.5]).tolist() if len(groups) >= 2 else None,
            'bootstrap_repetitions': repetitions, 'bootstrap_seed': 20261012}


def build_summary(data):
    rows = data['resynthesis']
    reference = data['comparison_reference']
    refs = {row['case']: row for row in rows if row['method'] == reference}
    scopes = {'全体': rows}
    for group in sorted({r['speaker_group'] for r in rows}):
        scopes[f'en/normal/{group}'] = [r for r in rows if r['speaker_group'] == group]
    result = {}
    for scope, subset in scopes.items():
        result[scope] = {}
        for method in dict.fromkeys(r['method'] for r in subset):
            selected = [r for r in subset if r['method'] == method]
            result[scope][method] = {'rows': len(selected),
                'processing_success': sum(r['status'] == 'measured' for r in selected),
                'metrics': {key: {**summarize(selected, key, higher), 'difference_from_base': paired(selected, refs, key)}
                            for key, _, higher in METRICS}}
    return result
