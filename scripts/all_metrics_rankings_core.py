"""正式rawの状態・方向・共通分母を保った話者等重み集約。測定はしない。"""
from __future__ import annotations

from collections import Counter, defaultdict
import math

import numpy as np

from all_metrics_common import METHODS

SEED = 20261014
REPLICATES = 2000
SUCCESS = ('measured', 'ok')


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def pending(status):
    return (not isinstance(status, str) or status.startswith(('pending', 'upstream_pending'))
            or status in ('running', 'not_run', 'not_requested', 'missing_status',
                          'quality_failure_evidence_insufficient'))


def special_terminal(data):
    if data.get('terminal') is False or data.get('analysis_complete') is False:
        return False
    return data.get('terminal') is True or data.get('analysis_complete') is True


def status_kind(status):
    if pending(status):
        return 'pending'
    if status in SUCCESS or status == 'analytic_identity':
        return 'success'
    if status == 'unsupported':
        return 'unsupported'
    if status in ('not_applicable', 'undefined', 'no_valid_values', 'no_common_pairs',
                  'no_common_triplets', 'reference_cer_gate_exceeded'):
        return 'not_applicable'
    if 'failed' in status or 'failure' in status or status in ('missing_metric_evidence', 'unavailable', 'incomplete',
                                                             'numerically_unreliable'):
        return 'failed'
    return 'other_terminal'


def normalize(row, admissible=SUCCESS):
    result = dict(row)
    status = result.get('status', 'pending_record')
    value = result.get('value')
    result.setdefault('origin_status', status)
    if value is not None and not finite(value):
        status, value = 'failed_nonfinite_value', None
    elif status in admissible and value is None:
        status = 'missing_metric_evidence'
    elif status not in admissible:
        value = None
    result.update(status=status, value=value)
    return result


def competition_ranks(values, direction):
    ranks = {method: None for method in values}
    if direction is None:
        return ranks
    if direction not in ('lower', 'higher'):
        raise ValueError(f'不明な順位方向: {direction}')
    ordered = sorted((method for method, value in values.items() if finite(value)),
                     key=lambda method: values[method], reverse=direction == 'higher')
    anchor, rank = None, None
    for position, method in enumerate(ordered, 1):
        value = values[method]
        if anchor is None or not math.isclose(value, anchor, abs_tol=1e-12, rel_tol=1e-9):
            anchor, rank = value, position
        ranks[method] = rank
    return ranks


def state_counts(rows):
    counts = Counter(row['status'] for row in rows)
    kinds = Counter()
    for status, count in counts.items():
        kinds[status_kind(status)] += count
    return {'status_counts': dict(counts), 'status_category_counts': dict(kinds),
            'direct_measured': sum(row['status'] in SUCCESS and finite(row['value']) for row in rows),
            'analytic_identity': sum(row['status'] == 'analytic_identity' and finite(row['value']) for row in rows),
            'finite_values': sum(finite(row['value']) for row in rows),
            'planned_records': len(rows), 'terminal': not any(pending(row['status']) for row in rows)}


def matrix_summary(rows, members, cases, direction):
    """全方式に同じ話者drawを使い、HNM差も同じ録音から作る。"""
    selected = [row for row in rows if row['case'] in cases and row['method'] in members]
    speakers = sorted({str(row['speaker']) for row in selected})
    indexed = {(row['method'], row['case']): row for row in selected}
    speaker_cases = defaultdict(list)
    if members:
        for case in sorted(cases):
            speaker_cases[str(indexed[members[0], case]['speaker'])].append(case)
    matrix = np.array([[np.mean([indexed[method, case]['value'] for case in speaker_cases[speaker]])
                        for method in members] for speaker in speakers], dtype=float)
    means = matrix.mean(axis=0) if speakers else np.full(len(members), np.nan)
    boot = np.empty((0, len(members)))
    if len(speakers) >= 2:
        draws = np.random.default_rng(SEED).integers(0, len(speakers), (REPLICATES, len(speakers)))
        boot = matrix[draws].mean(axis=1)
    values = {method: float(value) if np.isfinite(value) else None for method, value in zip(members, means)}
    ranks = competition_ranks(values, direction)
    result = {}
    base = members.index('hnm') if 'hnm' in members else None
    for index, method in enumerate(members):
        delta = means[index] - means[base] if base is not None else np.nan
        interval = np.quantile(boot[:, index], [.025, .975]).tolist() if len(boot) else None
        paired = (np.quantile(boot[:, index] - boot[:, base], [.025, .975]).tolist()
                  if len(boot) and base is not None else None)
        result[method] = {'value': values[method], 'rank': ranks[method], 'ci95': interval,
            'status': 'measured' if values[method] is not None else 'no_common_valid_recordings',
            'valid_recordings': len(cases), 'valid_speakers': len(speakers),
            'speaker_means': {speaker: float(matrix[s, index]) for s, speaker in enumerate(speakers)},
            'hnm_difference': {'value': float(delta) if np.isfinite(delta) else None, 'ci95': paired,
                'definition': '同じ録音の方式−HNM→話者内平均→話者等重み'},
            'recording_equal_mean_auxiliary': float(np.mean([indexed[method, case]['value'] for case in cases]))
                if cases else None}
    return {'methods': result, 'common_valid_recordings': len(cases), 'common_valid_speakers': len(speakers),
            'case_ids': sorted(cases), 'speaker_ids': speakers,
            'valid_bootstrap_replicates': len(boot), 'requested_bootstrap_replicates': REPLICATES,
            'interval_limitation': '話者構成に関する記述的95%区間。2話者未満は区間なし。多重比較未補正。'}


def aggregate(group):
    definition = {key: value for key, value in group.items() if key not in ('rows', 'by_method')}
    direction = group.get('direction')
    if direction == 'descriptive':
        direction = None
    if direction not in ('lower', 'higher', None):
        raise ValueError('順位方向はlower/higher/Noneを明示してください')
    definition.update(direction=direction, rankable=direction is not None)
    if group.get('observation_unit') == 'method_fixed_assets':
        if group.get('rows') or group.get('speaker_bootstrap_eligible') is not False:
            raise ValueError('固定共有資産を録音へ複写・bootstrapできません')
        constants = [normalize(row, group.get('admissible_status', SUCCESS))
                     for row in group.get('method_constants', [])]
        if {row['method'] for row in constants} != set(METHODS) or len(constants) != len(METHODS):
            raise ValueError('全8方式の固定資産状態が必要です')
        definition.update(method_constants=constants, rows=[], primary=None, conditional=None,
            method_states={row['method']: state_counts([row]) for row in constants},
            terminal=all(not pending(row['status']) for row in constants), rankable=False, direction=None)
        return definition
    members = list(group['methods'])
    if not members or len(members) != len(set(members)) or set(members)-set(METHODS):
        raise ValueError('比較対象methodsが不正です')
    rows = [normalize(row, group.get('admissible_status', SUCCESS)) for row in group['rows']]
    identities = [(row['method'], row['case']) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError(f'録音×方式の重複: {group["id"]}')
    expected_cases = set(group['planned_case_ids'])
    expected = {(method, case) for method in METHODS for case in expected_cases}
    if set(identities) != expected:
        raise ValueError(f'全8方式の予定状態行が不完全: {group["id"]}')
    speaker_by_case = {}
    for row in rows:
        if row['case'] in speaker_by_case and speaker_by_case[row['case']] != row['speaker']:
            raise ValueError('同じ録音の話者が方式によって異なります')
        speaker_by_case[row['case']] = row['speaker']
    valid = {method: {row['case'] for row in rows if row['method'] == method and finite(row['value'])}
             for method in METHODS}
    common = expected_cases.intersection(*(valid[method] for method in members))
    states = {method: state_counts([row for row in rows if row['method'] == method]) for method in METHODS}
    terminal = all(state['terminal'] for state in states.values())
    primary = matrix_summary(rows, members, common, direction)
    primary.update(label='宣言比較方式の共通群', comparable_methods=members,
                   all_eight_methods=members == list(METHODS))
    auxiliary = {}
    for method in METHODS:
        auxiliary[method] = matrix_summary(rows, [method], valid[method], None)['methods'][method]
        auxiliary[method]['rank'] = None
    conditional = None
    if terminal:
        selected = [method for method in members if valid[method]]
        shared = expected_cases.intersection(*(valid[method] for method in selected)) if selected else set()
        conditional = matrix_summary(rows, selected, shared, direction)
        conditional.update(label='終端後の成功方式固定・補助群', comparable_methods=selected,
            excluded_methods=[method for method in members if method not in selected],
            selection='全予定状態の終端後、許容状態の有限値が1件以上の全方式を固定。共通数で方式を選ばない。',
            same_as_primary=selected == members)
    definition.update(rows=rows, method_states=states, terminal=terminal, primary=primary,
        conditional=conditional, available_case_auxiliary=auxiliary,
        planned_recordings_per_method=len(expected_cases),
        planned_speakers_per_method=len(set(speaker_by_case.values())),
        bootstrap={'unit': 'speaker', 'replicates': REPLICATES, 'seed': SEED},
        aggregation='同じ録音→話者内平均→話者等重み。全有効値の方式別平均は無順位補助。')
    return definition
