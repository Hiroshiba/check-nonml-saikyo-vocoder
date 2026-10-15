"""一覧へ載せる比較指標と短い音声例を保存済みの記録から作る。"""
import html
import json
from statistics import median

LABELS = {'world_harvest': 'WORLD Harvest', 'world_dio': 'WORLD DIO',
          'llsm_world_dio': 'LLSM（WORLD DIOの音高）', 'identity': '原音（再合成の正解参照）'}
CURRENT_LABELS = {'hnm': '自作HNM', 'world_harvest': 'WORLD（Harvest）', 'identity': '原音'}
INDEX_METRICS = (
    ('mos', '予測MOS ↑'), ('estoi', '明瞭性 eSTOI ↑'),
    ('stft', 'スペクトル誤差 dB ↓'), ('band', '帯域の音量誤差 dB ↓'),
    ('envelope', '音量変動の誤差 ↓'), ('level', '音量差 dB ↓'),
)


def esc(value):
    return html.escape(str(value), quote=True)


def brief(results):
    data = json.loads((results / 'results.json').read_text(encoding='utf-8'))
    if data.get('study_role') == 'added_quality_control_metrics':
        return _brief_added_metrics(data)
    if data.get('study_role') == 'existing_references':
        from .references.report import table
        return '<p>' + esc(data['scope']) + '</p>' + table(data)
    if data.get('study_role') == 'current_base_and_references':
        return ('<p>現ベースと既存方式の固定比較。MOSはネイティブ全長、他は方式ごとの16 kHz共通先頭区間。'
                '単一合成seed。HNMとの差・95%区間・有効件数・被覆率は詳細に表示します。</p>'
                + _brief_expanded(data, results))
    if data.get('study_role') == 'supplement_to_completed_fixed_120':
        return _brief_supplement(data, results)
    if data.get('schema_version', 1) >= 3:
        return _brief_expanded(data, results)
    if data.get('schema_version', 1) >= 2:
        return _brief_current(data)
    rows = data['resynthesis']
    natural = any(row['kind'] == 'natural_speech' for row in rows)
    selected = [r for r in rows if (r['kind'] == 'natural_speech') == natural]
    reference = data['comparison_reference']
    body = []
    for method in dict.fromkeys(r['method'] for r in selected if r['method'] != 'identity'):
        records = [r for r in selected if r['method'] == method]
        values = []
        for r in records:
            value = r.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            if value is not None:
                values.append(value)
        failed = sum(r['status'] != 'measured' or r.get('measurement', {}).get('status') != 'ok' for r in records)
        cells = [LABELS.get(method, method), f'{median(values):.3f}' if values else '未測定',
                 f'{len(values)}/{len(records)}', failed]
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の比較。比較相手：{esc(LABELS.get(reference, reference))}。'
            '誤差は小さいほど原音に近く、知覚品質の順位ではありません。対応差は詳細に保存しています。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>スペクトル誤差中央値 dB</th>'
            '<th>有効／全件</th><th>処理・測定失敗</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _brief_added_metrics(data):
    rows = []
    for item in data['comparison_summary']:
        if item['metric'] not in ('mos', 'speaker_ecapa', 'erb', 'scoreq'):
            continue
        cells = [item['label']]
        for method in ('hnm', 'world_harvest'):
            metric = item['methods'].get(method, {})
            value = metric.get('speaker_macro_mean')
            cells.append(f"{value:.3f}（{metric['valid_cases']}/120）" if value is not None else '未測定')
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    scoreq_count = data['scoreq_status']['measured_rows']
    return ('<p>固定120録音40話者の追加品質・制御測定。話者等重み。'
            '無編集MOSは同条件の歴史値、編集MOS・ECAPA・ERB等を追加実測。'
            f'SCOREQ有効{scoreq_count}/240件、ASRは55録音の補助集合。総合順位は作りません。</p>'
            '<div class="scroll"><table><thead><tr><th>指標</th><th>HNM v3（現ベース）</th>'
            '<th>WORLD（Harvest）</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def _brief_supplement(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['groups']['全体']
    return _metric_table(data, summary)


def _brief_expanded(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['全体']
    return _metric_table(data, summary)


def _metric_table(data, summary):
    """各方式の保存済み平均値を、品質の異なる観点で並べる。"""
    rows = []
    for method, group in summary.items():
        cells = [data['method_labels'][method]]
        for key, _ in INDEX_METRICS:
            metric = group['metrics'][key]
            value = metric['mean']
            text = f'{value:.3f}' if value is not None else '未測定'
            if value is not None and metric['valid'] != data['planned_cases']:
                text += '（部分測定）'
            cells.append(text)
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    headings = '<th>方式</th>' + ''.join(f'<th>{esc(label)}</th>' for _, label in INDEX_METRICS)
    return ('<div class="scroll"><table><thead><tr>' + headings + '</tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')


def _brief_current(data):
    rows = data['resynthesis']
    natural = any(row['kind'] == 'natural_speech' for row in rows)
    selected = [r for r in rows if (r['kind'] == 'natural_speech') == natural]
    reference = data['comparison_reference']
    refs = {r['case']: r for r in selected if r['method'] == reference}
    body = []
    for method in dict.fromkeys(r['method'] for r in selected if r['method'] != 'identity'):
        records = [r for r in selected if r['method'] == method]
        values, deltas = [], []
        for row in records:
            value = row.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            base = refs.get(row['case'], {}).get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            if value is not None:
                values.append(value)
                if base is not None:
                    deltas.append(value - base)
        failed = sum(r['status'] != 'measured' or r.get('measurement', {}).get('status') != 'ok' for r in records)
        cells = [CURRENT_LABELS.get(method, method), f'{median(values):.3f}' if values else '—',
                 f'{len(values)}/{len(records)}',
                 f'{len(deltas)}/{len(records)}', f'{failed}/{len(records)}']
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の再合成。比較相手：{esc(CURRENT_LABELS.get(reference, reference))}。対応差は詳細に保存しています。'
            '誤差は小さいほど原音に近く、知覚品質の順位ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>誤差中央値 dB</th>'
            '<th>有効／全件</th><th>比較可能／全件</th><th>失敗／全件</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def short_audio(results, *, heading='同じ区間の音声'):
    path = results / 'audio_samples.json'
    if not path.exists():
        measurements = json.loads((results / 'results.json').read_text(encoding='utf-8'))
        if measurements.get('study_role') == 'supplement_to_completed_fixed_120':
            parent = results.parents[2] / 'noise-envelope/results/run-001'
            return short_audio(parent, heading='英語の音声例')
        return '<p><small>この過去の記録には音声例を保存していません。</small></p>'
    data = json.loads(path.read_text(encoding='utf-8'))
    measurements = json.loads((results / 'results.json').read_text(encoding='utf-8'))
    current = measurements.get('schema_version', 1) >= 2
    labels = measurements.get('method_labels', CURRENT_LABELS if current else LABELS)
    samples = data.get('samples', [])
    refs = [s for s in samples if s['method'] == 'identity']
    if not refs:
        return '<p>比較できる原音の音声例がありません。</p>'
    chosen = next((s for s in refs if s['case'].startswith('librispeech_')), refs[0])
    cards = []
    if current:
        order = measurements.get('index_methods', ['candidate', 'identity', 'hnm', 'world_harvest'])
        visible = order if 'index_methods' in measurements else labels
        samples = sorted((s for s in samples if s['method'] in labels and s['method'] in visible),
                         key=lambda s: order.index(s['method']) if s['method'] in order else len(order))
    for sample in samples:
        if sample['case'] != chosen['case']:
            continue
        uri = sample['data_uri']
        if not uri.startswith('data:audio/wav;base64,'):
            raise ValueError('音声例はWAV形式で保存してください')
        cards.append(f'<div><p>{esc(labels.get(sample["method"], sample["method"]))}</p>'
                     f'<audio controls preload="none" aria-label="{esc(labels.get(sample["method"], sample["method"]))}" '
                     f'src="{esc(uri)}"></audio></div>')
    if current:
        return (f'<p>{esc(heading)}（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）</p>'
                '<div class="audio-grid">'+''.join(cards)+'</div>')
    return (f'<p>短い音声例：{esc(chosen["label"])}（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）。'
            '同じ原音・区間を各方式で比較できます。</p><div class="audio-grid">'+''.join(cards)+'</div>')
