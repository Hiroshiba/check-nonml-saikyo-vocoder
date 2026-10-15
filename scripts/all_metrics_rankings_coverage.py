"""18評価群×全8方式を必ず表示。複数派生軸の件数を独立録音数へ足さない。"""
from __future__ import annotations

from collections import Counter

from all_metrics_common import METHODS
from all_metrics_rankings_core import finite, pending, state_counts

FAMILIES = {
    1: 'UTMOSv2予測MOS', 2: 'SCOREQ参照あり距離', 3: 'ViSQOL Audio独立48kHz群',
    4: '増分CER/WER', 5: 'ECAPA話者類似度', 6: '局所聴覚帯域距離',
    7: '音高操作追従', 8: '音量操作追従', 9: '局所時間・全長', 10: '音色・傾斜',
    11: '操作干渉', 12: '編集量と予測品質の曲線', 13: '既存人間評定と近傍一致',
    14: '音素ABX', 15: '線形読み出し', 16: '補間', 17: '表現量子化への頑健性',
    18: '品質と表現量',
}
LABELS = {'measured': '実測値あり', 'partial': '一部の軸に実測値あり', 'pending': '未完了',
          'not_applicable': '適用外', 'unsupported': '未対応', 'failed': '失敗',
          'no_valid_values': '有効値なし', 'mixed_terminal': '適用外・失敗等が混在',
          'measured_no_common': '実測値あり・主共通群なし'}


def cell_status(group, method):
    state = group['method_states'][method]
    kinds = state.get('status_category_counts', {})
    if not state['terminal'] or any(pending(key) for key in state['status_counts']):
        return 'pending'
    if state['finite_values']:
        cell = (group.get('primary') or {}).get('methods', {}).get(method, {})
        if group.get('observation_unit') == 'method_fixed_assets' or finite(cell.get('value')):
            return 'measured'
        return 'measured_no_common'
    observed = {key for key, count in kinds.items() if count}
    if observed == {'unsupported'}:
        return 'unsupported'
    if observed == {'not_applicable'}:
        return 'not_applicable'
    if observed <= {'failed'} and observed:
        return 'failed'
    if len(observed) > 1:
        return 'mixed_terminal'
    return 'no_valid_values'


def retain_group_conditional(group):
    """他群の未完で消さず、この群の予定集合と状態だけで保存済み補助を検証する。"""
    conditional = group.get('conditional')
    if conditional is None:
        return
    rows, cases = group.get('rows', []), set(group.get('planned_case_ids', []))
    identities = [(r['method'], r['case']) for r in rows]
    expected = {(m, c) for m in METHODS for c in cases}
    if (not cases or len(identities) != len(set(identities)) or set(identities) != expected
            or group.get('terminal') is not True or set(group['method_states']) != set(METHODS)):
        raise ValueError('条件付き表には当該群の固定全予定状態が必要です: ' + group['id'])
    invalid = {'missing_metric_evidence', 'failed_nonfinite_value', 'failed_timing_phase_evidence'}
    for method in METHODS:
        state = state_counts([r for r in rows if r['method'] == method])
        if state != group['method_states'][method] or not state['terminal']:
            raise ValueError('条件付き群の保存状態件数または終端証拠が不一致')
        if invalid.intersection(state['status_counts']):
            group['conditional'] = None
            group['conditional_withheld_reason'] = '当該群の実測値・計時証拠が不完全。別群の未完とは区別。'
            return
    valid = {m: {r['case'] for r in rows if r['method'] == m and finite(r['value'])} for m in METHODS}
    members = [m for m in group['methods'] if valid[m]]
    common = cases.intersection(*(valid[m] for m in members)) if members else set()
    if (conditional['comparable_methods'] != members or set(conditional['methods']) != set(members)
            or set(conditional['case_ids']) != common
            or conditional['common_valid_recordings'] != len(common)
            or conditional['excluded_methods'] != [m for m in group['methods'] if m not in members]):
        raise ValueError('条件付き表が全有効方式の固定規則・共通集合と不一致')
    group['group_terminal_evidence'] = {'all_planned_rows_terminal': True,
        'planned_rows': len(rows), 'planned_recordings_per_method': len(cases),
        'status_only_selection_verified': True, 'comparable_methods': members,
        'common_recordings': len(common), 'global_final_gate_replaced': False}


def supplement_details(group, method):
    return {'group_id': group['id'], 'label': group['label'], 'anchor': '#group-' + group['id'],
        'status': cell_status(group, method), 'status_label': LABELS[cell_status(group, method)],
        'counts': group['method_states'][method],
        'primary': {k: group['primary'][k] for k in ('common_valid_recordings', 'common_valid_speakers', 'cohort')
                    if k in group['primary']},
        'conditional': {k: group['conditional'][k] for k in ('common_valid_recordings', 'common_valid_speakers', 'cohort')
                        if k in group['conditional']} if group.get('conditional') else None,
        'conditional_included': method in (group.get('conditional') or {}).get('comparable_methods', []),
        'does_not_replace_original': True}


def coverage(groups):
    rows = []
    for family, label in FAMILIES.items():
        members = [group for group in groups if group['family'] == family and not group.get('supplementary')]
        supplements = [group for group in groups if group['family'] == family and group.get('supplementary')]
        cells = {}
        for method in METHODS:
            details = [{'group_id': group['id'], 'status': cell_status(group, method),
                        'comparable': method in group['methods'],
                        'counts': group['method_states'][method],
                        'primary_common_recordings': (group.get('primary') or {}).get('common_valid_recordings'),
                        'primary_cohort': (group.get('primary') or {}).get('cohort')}
                       for group in members]
            counts = Counter(item['status'] for item in details)
            statuses = set(counts)
            if not details or 'pending' in statuses:
                status = 'pending'
            elif statuses <= {'measured', 'measured_no_common'}:
                status = 'measured_no_common' if statuses == {'measured_no_common'} else 'measured'
            elif statuses & {'measured', 'measured_no_common'}:
                status = 'partial'
            elif len(statuses) == 1:
                status = next(iter(statuses))
            else:
                status = 'mixed_terminal'
            cells[method] = {'status': status, 'label': LABELS[status],
                'derived_axis_status_counts': dict(counts), 'derived_axes': details,
                'availability_supplements': [supplement_details(group, method) for group in supplements],
                'counting_note': '件数は派生軸ごとの状態。重複する録音・話者を合算しない。'}
        rows.append({'family': family, 'label': label, 'derived_axes': len(members), 'methods': cells})
    return {'family_count': 18, 'method_count': 8, 'cells': 144, 'rows': rows,
        'meaning': '18群内の派生軸を独立した評価項目・投票へ数えない。既存音響/速度は別欄。'}
