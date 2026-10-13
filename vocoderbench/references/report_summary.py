"""現ベースと参照方式の保存値集計。話者単位の対応を保った層化再抽出。"""
from collections import Counter, defaultdict

import numpy as np

from .report_metrics import BY_KEY, METRICS, extract

BOOTSTRAP_SEED = 20261012
BOOTSTRAP_REPETITIONS = 2000


def attributes(row):
    return str(row.get('speaker_gender_as_distributed') or row.get('speaker_group') or '不明')


def prepared_rows(data):
    inputs = data['contract']['inputs']
    metadata = {item['id']: item for item in inputs}
    if len(metadata) != len(inputs) or len(inputs) != data['planned_cases']:
        raise ValueError('測定契約の入力ID・予定件数が一致しません')
    records = {}
    for row in data['resynthesis'] + data.get('calibration', []):
        key = row['case'], row['method']
        if key in records:
            raise ValueError(f'同じ録音・方式の行が重複しています: {key}')
        if row['case'] not in metadata or row['method'] not in [*data['selected_methods'], 'identity']:
            raise ValueError(f'測定契約外の行があります: {key}')
        records[key] = row
    rows = []
    for method in [*data['selected_methods'], 'identity']:
        for case, item in metadata.items():
            record = records.get((case, method), {'case': case, 'method': method, 'status': 'not_run'})
            rows.append({**item, **record})
    return rows


def describe(rows, metric):
    values, missing = [], []
    for row in rows:
        value, reason = extract(row, metric)
        if value is None:
            missing.append({'case': row['case'], 'reason': reason})
        else:
            values.append(value)
    valid = np.asarray(values, dtype=float)
    count = max(1, int(np.ceil(len(valid) * .05)))
    tail = np.sort(valid)[:count] if metric.higher else np.sort(valid)[-count:]
    return {'valid': len(values), 'total': len(rows),
            'mean': float(np.mean(valid)) if len(valid) else None,
            'median': float(np.median(valid)) if len(valid) else None,
            'minimum': float(np.min(valid)) if len(valid) else None,
            'maximum': float(np.max(valid)) if len(valid) else None,
            'worst_5_percent_mean': float(np.mean(tail)) if len(valid) and metric.higher is not None else None,
            'missing_reasons': dict(Counter(item['reason'] for item in missing)),
            'missing_cases': missing}


def paired(rows, references, metric):
    clusters, values, missing_speaker = defaultdict(list), [], 0
    for row in rows:
        a, _ = extract(row, metric)
        b, _ = extract(references.get(row['case'], {}), metric)
        if a is None or b is None:
            continue
        difference = a - b
        values.append(difference)
        if not row.get('speaker'):
            missing_speaker += 1
            continue
        # 配布元の男女属性内で話者を復元抽出。録音数による重みは従来集計と同じ。
        clusters[(attributes(row), row['speaker'])].append(difference)
    result = {'paired': len(values), 'total': len(rows), 'speakers': len(clusters),
              'mean_difference': float(np.mean(values)) if values else None,
              'speaker_bootstrap_95': None, 'bootstrap_seed': BOOTSTRAP_SEED,
              'bootstrap_repetitions': BOOTSTRAP_REPETITIONS,
              'speaker_metadata_missing': missing_speaker,
              'speakers_by_stratum': dict(Counter(group for group, _ in clusters))}
    if not values:
        result['ci_unavailable_reason'] = '双方に有効値のある録音なし'
        return result
    if missing_speaker:
        result['ci_unavailable_reason'] = '有効な対に話者情報の欠落あり'
        return result
    if len(clusters) < 2:
        result['ci_unavailable_reason'] = '有効な話者が2人未満'
        return result
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    sums, counts = np.zeros(BOOTSTRAP_REPETITIONS), np.zeros(BOOTSTRAP_REPETITIONS)
    for stratum in sorted({group for group, _ in clusters}):
        groups = [group for (label, _), group in sorted(clusters.items()) if label == stratum]
        group_sums, group_counts = np.array([sum(g) for g in groups]), np.array([len(g) for g in groups])
        selections = rng.integers(len(groups), size=(BOOTSTRAP_REPETITIONS, len(groups)))
        sums += group_sums[selections].sum(axis=1)
        counts += group_counts[selections].sum(axis=1)
    result['speaker_bootstrap_95'] = np.percentile(sums / counts, [2.5, 97.5]).tolist()
    result['ci_unavailable_reason'] = None
    return result


def method_summary(rows, references):
    return {'rows': len(rows), 'planned': len(rows),
            'processing_success': sum(row['status'] == 'measured' for row in rows),
            'full_length_matches': sum(row.get('measurement', {}).get('status') == 'ok' for row in rows),
            'speakers': len({row['speaker'] for row in rows if row.get('speaker')}),
            'metrics': {metric.key: {**describe(rows, metric),
                        'difference_from_base': paired(rows, references, metric)} for metric in METRICS}}


def build_summary(data):
    rows = prepared_rows(data)
    synthesized = [row for row in rows if row['method'] != 'identity']
    originals = [row for row in rows if row['method'] == 'identity']
    refs = {row['case']: row for row in synthesized if row['method'] == data['comparison_reference']}
    scopes = {'全体': synthesized}
    for attribute in sorted({attributes(row) for row in synthesized}):
        scopes[f'配布属性/{attribute}'] = [row for row in synthesized if attributes(row) == attribute]
    result = {name: {method: method_summary([r for r in subset if r['method'] == method], refs)
                     for method in data['selected_methods']} for name, subset in scopes.items()}
    result['original_mos'] = {'全体': describe(originals, BY_KEY['mos'])}
    for attribute in sorted({attributes(row) for row in originals}):
        result['original_mos'][f'配布属性/{attribute}'] = describe(
            [row for row in originals if attributes(row) == attribute], BY_KEY['mos'])
    result['protocol'] = {'schema': 'current-base-reference-summary-v1',
        'aggregation': '録音を等重みとする有効値平均。反復seed・フレームは標本数にしない。',
        'difference': '同じ録音で双方が有効な値の方式−現ベース。',
        'bootstrap': '配布元の男女属性内で話者を復元抽出し、選ばれた話者の全有効録音対を保持。',
        'bootstrap_seed': BOOTSTRAP_SEED, 'bootstrap_repetitions': BOOTSTRAP_REPETITIONS,
        'bootstrap_scope': '固定集合の話者再抽出に対する記述的95%区間。多重比較補正なし。',
        'acoustic_scope': '方式ごとの原音との共通先頭区間。対差でも評価区間長は方式ごとに異なる。',
        'synthesis_seed': data['contract'].get('seed'),
        'original_acoustics': '原音の自己音響比較は実施しない。原音はMOSのみ。'}
    result['metric_definitions'] = {m.key: {'label': m.label, 'family': m.family,
        'higher_is_better': m.higher, 'path': list(m.path), 'transform': m.transform} for m in METRICS}
    return result
