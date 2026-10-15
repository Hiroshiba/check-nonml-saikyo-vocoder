"""保存補助値だけの話者macro集約と日本語HTML。再測定しない。"""
from collections import Counter
import html

from common_windows import BASE, CONDITIONS, METHODS, RUN, batch_gate, evidence, read
from all_metrics_rankings_core import finite, matrix_summary, pending, state_counts
from vocoderbench.quality_core import sha256


def result_path(group, condition, case):
    return BASE / 'measurements' / group / condition / f'{case}.json'


def validate_result_sources(data):
    for key in ('batch_manifest', 'batch_gate'):
        item = data.get(key)
        if item and sha256(item['path']) != item['sha256']:
            raise ValueError(f'補助結果の{key}証跡が変化しています')
    for row in data['rows']:
        proofs = [row[k] for k in ('strict_primary_evidence', 'strict_primary_contract_evidence') if k in row]
        proofs += [r['record_evidence'] for r in row.get('source_records', {}).values()]
        proofs += [r['scientific_contract_evidence'] for r in row.get('source_records', {}).values()]
        for item in proofs:
            if sha256(item['path']) != item['sha256']:
                raise ValueError(f'補助結果のraw/元strict/科学契約SHAが変化しています: {item["path"]}')


def load_rows(specs, condition, group, signature, members=METHODS):
    rows, sources = [], []
    for spec in specs:
        path = result_path(group, condition, spec['id'])
        if path.exists():
            data = read(path)
            if (data['contract_sha256'] != signature or data['case'] != spec['id'] or data['condition'] != condition
                    or data['group_id'] != group or data['speaker'] != spec['speaker'] or data['members'] != list(members)):
                raise ValueError('保存補助結果の契約/case/condition不一致')
            validate_result_sources(data)
            sources.append(evidence(path))
            for row in data['rows']:
                if (row['case'], row['speaker'], row['condition'], row['group_id']) != (spec['id'], spec['speaker'], condition, group):
                    raise ValueError('補助rowのcase/speaker/condition/group_idが予定と不一致')
                rows.append({**row, 'raw_result': str(path), 'raw_result_sha256': sources[-1]['sha256']})
        else:
            for method in METHODS:
                rows.append({'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
                    'condition': condition, 'status': 'pending_measurement', 'value': None,
                    'reason': '正式全終端batch receiptまたはこの補助計測を待機'})
    identities = [(r['case'], r['method']) for r in rows]
    if len(identities) != len(set(identities)) or set(identities) != {(s['id'], m) for s in specs for m in METHODS}:
        raise ValueError('予定120×全8方式の状態が不完全です')
    if any(r['status'] in ('measured', 'analytic_identity') and not finite(r['value']) for r in rows):
        raise ValueError('補助成功値が非有限または欠落しています')
    return rows, sources


def group_summary(rows, members, label):
    valid = {m: {r['case'] for r in rows if r['method'] == m and
                  r['status'] in ('measured', 'analytic_identity') and finite(r['value'])} for m in METHODS}
    common = set.intersection(*(valid[m] for m in members)) if members else set()
    result = matrix_summary(rows, list(members), common, 'lower')
    states = {m: state_counts([r for r in rows if r['method'] == m]) for m in METHODS}
    source_states = {m: {side: dict(Counter(r.get('upstream_statuses', {}).get(side, 'pending_measurement')
                       for r in rows if r['method'] == m)) for side in ('native', 'point')} for m in METHODS}
    diagnostics = {}
    for method in METHODS:
        local = [r for r in rows if r['method'] == method]
        deltas = [r['full_length_delta']['signed_seconds'] for r in local
                  if r.get('full_length_delta', {}).get('status') == 'measured_metadata']
        coverage = [d['coverage'] for r in local for d in r.get('derivations', {}).values() if d.get('coverage') is not None]
        cuts = {side: [r['derivations'][side]['omitted_tail_seconds'] for r in local
                      if r.get('derivations', {}).get(side, {}).get('omitted_tail_seconds') is not None] for side in ('native', 'point')}
        diagnostics[method] = {'signed_length_delta_seconds_min': min(deltas) if deltas else None,
            'signed_length_delta_seconds_max': max(deltas) if deltas else None,
            'length_delta_observations': len(deltas), 'minimum_pair_coverage': min(coverage) if coverage else None,
            'maximum_omitted_tail_seconds': {side: max(values) if values else None for side, values in cuts.items()},
            'strict_primary_auditory_status_counts': dict(Counter((r.get('strict_primary_auditory') or {}).get('status',
                r.get('upstream_statuses', {}).get('point', 'pending_measurement')) for r in local))}
    result.update(length_and_coverage=diagnostics, label=label, comparable_methods=list(members), excluded_methods=[m for m in METHODS if m not in members],
        all_eight_methods=list(members) == list(METHODS), planned_recordings_per_method=120,
        planned_speakers_per_method=40, method_states=states, upstream_wave_status_counts=source_states,
        terminal=not any(pending(r['status']) for r in rows), limited_group=len(common) < 100,
        unit='dB', direction='lower', rows=rows,
        scope='量子化point対同方式native。事後追加の固定共通16k先頭窓・40ms ERB聴覚差。',
        overall_winner=None, source_length_and_coverage='各raw_resultのcommon_window/all_sourcesとfull_length_deltaに全長・切落とし・coverageを保存')
    return result


def summarize(signature):
    specs = read(RUN / 'inputs.json')
    if len(specs) != 120 or len({s['speaker'] for s in specs}) != 40:
        raise ValueError('固定主120録音40話者以外は集約しません')
    groups, inventory = [], []
    for condition in CONDITIONS:
        rows, sources = load_rows(specs, condition, 'all-eight', signature)
        primary = group_summary(rows, METHODS, '全8方式固定・共通先頭区間補助')
        inventory += sources
        path = BASE / 'membership' / f'{condition}.json'
        conditional = {'status': 'pending_all_planned_points_terminal', 'value': None,
            'reason': '全120×8の当精度point終端まで成功方式集合を固定しません'}
        if path.exists():
            selection = read(path)
            if selection['contract_sha256'] != signature:
                raise ValueError('成功方式集合の契約が不一致です')
            inventory.append(evidence(path))
            if selection['members'] == list(METHODS):
                conditional = {'status': 'same_as_primary', 'same_as_primary': True,
                    'measurement_reference': 'all-eight', 'summary_reference': 'primary',
                    'selection': selection, 'new_measurements': 0}
            else:
                conditional_rows, conditional_sources = load_rows(specs, condition, 'successful-methods', signature, selection['members'])
                inventory += conditional_sources
                conditional = group_summary(conditional_rows, selection['members'], '終端後の成功wave方式固定・限定補助')
                conditional.update(selection=selection, same_as_primary=False)
        groups.append({'condition': condition, 'family_ids': [17, 18], 'primary': primary, 'conditional': conditional})
    return {'protocol_id': 'posthoc_quantization_common_prefix_16k_v1', 'post_hoc': True,
        'contract_sha256': signature, 'contract_file_sha256': sha256(BASE / 'contract.json'),
        'overall_study_complete': False, 'overall_winner': None, 'groups': groups,
        'batch_gates': [batch_gate(b) for b in range(12)], 'result_inventory': inventory,
        'limitations': ['元strict全長primary/NAを変更しない独立補助。',
            '共通先頭区間の差であり、全長・高域・知覚品質を代表しない。',
            '20ms ERB品質群と異なる40ms/5ms/32帯域の聴覚差。',
            '精度別に共通窓を定め、精度間で同じ窓とは主張しない。',
            '#18のpayload bit/sは元入力秒数が分母。同じ聴覚値を引用し追加の独立指標に数えない。',
            '順位は話者macro。seed20261014/2000話者bootstrapの記述95%区間、多重比較未調整。',
            '共通録音100未満は限定群。未完工程と失敗を0や最下位へ変えない。']}


def render(report):
    esc = html.escape
    def show(value):
        return '—' if value is None else f'{value:.6g}'
    parts = ['<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
        '<title>量子化の共通先頭区間：事後追加の聴覚差補助</title>',
        '<style>:root{color-scheme:light dark}body{font-family:system-ui;margin:2rem;max-width:100rem}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #888;padding:.4rem;text-align:right}th:first-child,td:first-child{text-align:left}p{max-width:75rem}</style>',
        '<h1>量子化の共通先頭区間：事後追加の聴覚差補助</h1>',
        '<p>同方式nativeに対する40 ms ERB絶対差（dB、小さい方が近い）。元の厳格全長primary・NAは変更していません。追加合成・追加推論なし。全18項目の完成や総合勝者を示すものではありません。</p>']
    for group in report['groups']:
        parts.append(f'<h2>{esc(group["condition"])}</h2>')
        for key in ('primary', 'conditional'):
            summary = group[key]
            if 'methods' not in summary:
                parts.append('<p>' + ('成功方式集合は全8と同一。上の全8補助値を引用し再計算していません。' if summary.get('same_as_primary') else '成功方式条件付き群は全120×8終端後に固定します。現在は未選定です。') + '</p>')
                continue
            parts.append(f'<h3>{esc(summary["label"])}</h3><p>共通{summary["common_valid_recordings"]}/120録音、{summary["common_valid_speakers"]}/40話者。' +
                ('限定群（100録音未満）。' if summary['limited_group'] else '') + ('全予定状態は終端。' if summary['terminal'] else '未完を含む途中集計。') + '</p>')
            parts.append('<table><tr><th>方式</th><th>順位</th><th>話者平均 dB</th><th>95%区間</th><th>HNM差 dB</th><th>HNM差95%区間</th><th>実測</th><th>厳密同一</th><th>失敗/適用外/未完</th></tr>')
            for method in METHODS:
                value = summary['methods'].get(method, {})
                counts = summary['method_states'][method]
                c = counts['status_category_counts']
                interval = value.get('ci95')
                ci = '—' if interval is None else f'{show(interval[0])} ～ {show(interval[1])}'
                delta_interval = value.get('hnm_difference', {}).get('ci95')
                delta_ci = '—' if delta_interval is None else f'{show(delta_interval[0])} ～ {show(delta_interval[1])}'
                parts.append('<tr>' + ''.join(f'<td>{esc(str(x))}</td>' for x in [method, show(value.get('rank')), show(value.get('value')), ci,
                    show(value.get('hnm_difference', {}).get('value')), delta_ci, counts['direct_measured'], counts['analytic_identity'],
                    f'{c.get("failed", 0)}/{c.get("not_applicable", 0)}/{c.get("pending", 0)}']) + '</tr>')
            parts.append('</table><table><tr><th>方式</th><th>量子化−native全長差 秒（最小～最大）</th><th>両側の最小coverage</th><th>native末尾切落とし最大 秒</th><th>point末尾切落とし最大 秒</th><th>元strict聴覚状態</th></tr>')
            for method in METHODS:
                d = summary['length_and_coverage'][method]
                parts.append('<tr>' + ''.join('<td>' + esc(str(x)) + '</td>' for x in [method,
                    f"{show(d['signed_length_delta_seconds_min'])} ～ {show(d['signed_length_delta_seconds_max'])}",
                    show(d['minimum_pair_coverage']), show(d['maximum_omitted_tail_seconds']['native']),
                    show(d['maximum_omitted_tail_seconds']['point']), d['strict_primary_auditory_status_counts']]) + '</tr>')
            parts.append('</table>')
            if summary.get('excluded_methods'):
                parts.append('<p>成功waveが1件もないため固定集合から除外：' + esc(', '.join(summary['excluded_methods'])) + '。全8群の分母と欠測は上に保持しています。</p>')
    parts.append('<h2>適用範囲</h2><ul>' + ''.join('<li>' + esc(x) + '</li>' for x in report['limitations']) + '</ul>')
    parts.append('<p>native/pointの全長、変換長、末尾切落とし、coverage、長さ差、raw/source hashは同封の詳細JSONに保存しています。共有資産を含む総bitrateではありません。</p></html>')
    return ''.join(parts)
