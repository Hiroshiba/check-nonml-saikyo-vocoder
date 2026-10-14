"""18評価群×全8方式を必ず表示。複数派生軸の件数を独立録音数へ足さない。"""
from __future__ import annotations

from collections import Counter

from all_metrics_common import METHODS
from all_metrics_rankings_core import finite, pending

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


def coverage(groups):
    rows = []
    for family, label in FAMILIES.items():
        members = [group for group in groups if group['family'] == family]
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
                'counting_note': '件数は派生軸ごとの状態。重複する録音・話者を合算しない。'}
        rows.append({'family': family, 'label': label, 'derived_axes': len(members), 'methods': cells})
    return {'family_count': 18, 'method_count': 8, 'cells': 144, 'rows': rows,
        'meaning': '18群内の派生軸を独立した評価項目・投票へ数えない。既存音響/速度は別欄。'}
