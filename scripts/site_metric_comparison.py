"""一覧の用途別比較。保存済みの値・順位を引用し、統計量を計算しない。"""
import html
import math


def esc(value):
    return html.escape(str(value), quote=True)


def support(cohort):
    """通常・専用集計の保存済み分母を、単位を変えず読み取る。"""
    if 'common_valid_recordings' in cohort:
        return {'recordings': cohort['common_valid_recordings'],
                'speakers': cohort['common_valid_speakers']}
    saved = cohort['cohort']
    if 'common_recordings' in saved:
        return {'recordings': saved['common_recordings'], 'speakers': saved['common_speakers']}
    return {key: saved['common'][key] for key in
            ('recordings', 'speakers', 'pairs', 'b_anchors', 'b_speakers', 'triplets')
            if key in saved['common']}


def selected(group, spec):
    view = spec['view']
    if view not in ('primary', 'conditional'):
        raise ValueError('一覧の集計区分が不正です')
    cohort = group.get(view)
    if not isinstance(cohort, dict) or not isinstance(cohort.get('methods'), dict):
        raise ValueError(f'保存済み比較群がありません: {group["id"]}/{view}')
    if (support(cohort) != spec['support']
            or cohort['comparable_methods'] != spec['methods']):
        raise ValueError(f'一覧の比較方式・分母が保存記録と一致しません: {group["id"]}')
    return cohort


def metric_heading(group, cohort, spec, report):
    counts = support(cohort)
    parts = [f'{counts["recordings"]}録音・{counts["speakers"]}話者']
    for key, label in (('pairs', '対'), ('triplets', '三つ組'), ('b_anchors', '基準録音'),
                       ('b_speakers', '基準話者')):
        if key in counts:
            parts.append(f'{counts[key]}{label}')
    scope = '条件付き補助' if spec['view'] == 'conditional' else spec['cohort_label']
    arrow = {'higher': '↑', 'lower': '↓'}.get(group.get('direction'), '')
    return (f'<th scope="col"><a href="{esc(report)}#group-{esc(group["id"])}">'
            f'{esc(spec["label"])}</a> {arrow}'
            f'<br><small>{esc(scope)}・{len(spec["methods"])}方式'
            f'<br>{esc(" / ".join(parts))}</small></th>')


def metric_cell(group, cohort, method):
    if method not in cohort['comparable_methods']:
        return '<td class="metric-unavailable">比較対象外</td>'
    cell = cohort['methods'].get(method, {})
    value = cell.get('value')
    if value is None:
        return '<td class="metric-unavailable">比較不成立<br><small>順位なし</small></td>'
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'一覧の保存値が有限数ではありません: {group["id"]}/{method}')
    # 小さい非ゼロ値を0.000と表示せず、原数値をtitleにも残す。
    number = f'<span title="保存値: {esc(value)}">{value:.6g}</span>'
    rank = cell.get('rank') if group.get('rankable') else None
    if rank is None:
        return f'<td>{number}<br><small>順位なし</small></td>'
    if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= len(cohort['comparable_methods']):
        raise ValueError(f'保存順位が不正です: {group["id"]}/{method}')
    tied = sum(other.get('rank') == rank for other in cohort['methods'].values()) > 1
    label = ('同率' if tied else '') + f'{rank}位'
    emphasis = f' rank-{rank}' if rank <= 3 else ''
    tag = 'strong' if rank <= 3 else 'span'
    return f'<td>{number}<br><{tag} class="rank{emphasis}">{label}</{tag}></td>'


def section_table(groups, section, labels, report):
    chosen = [(groups[spec['group']], spec) for spec in section['metrics']]
    cohorts = [selected(group, spec) for group, spec in chosen]
    headings = ''.join(metric_heading(group, cohort, spec, report)
                       for (group, spec), cohort in zip(chosen, cohorts, strict=True))
    rows = []
    for method, label in labels.items():
        cells = ''.join(metric_cell(group, cohort, method)
                        for (group, _), cohort in zip(chosen, cohorts, strict=True))
        rows.append(f'<tr><th scope="row">{esc(label)}</th>{cells}</tr>')
    return ('<div class="scroll"><table class="metric-comparison">'
            f'<caption>{esc(section["title"])}</caption><thead><tr><th scope="col">方式</th>'
            + headings + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def comparison(data, item, *, expanded):
    groups = {group['id']: group for group in data['groups']}
    labels = item['method_labels']
    if (list(labels) != data['methods']
            or data['formal_base']['comparison_reference'] != item['reference_method']):
        raise ValueError('登録した比較方式・当時のベースが保存結果と一致しません')
    blocks = []
    for section in item['metric_sections']:
        if section['expanded'] != expanded:
            continue
        body = f'<p class="metric-note">{esc(section["note"])}</p>'
        body += section_table(groups, section, labels, item['path'] + '/index.html')
        if section['expanded']:
            blocks.append(f'<section class="metric-section"><h3>{esc(section["title"])}</h3>{body}</section>')
        else:
            blocks.append('<details class="metric-section"><summary>'
                          f'{esc(section["title"])}（{len(section["metrics"])}指標）</summary>'
                          + body + '</details>')
    return ''.join(blocks)
