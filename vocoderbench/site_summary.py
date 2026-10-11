"""一覧へ載せる比較指標と短い音声例を保存済みの記録から作る。"""
import html
import json
from statistics import median

LABELS = {'world_harvest': 'WORLD Harvest', 'world_dio': 'WORLD DIO',
          'llsm_world_dio': 'LLSM（WORLD DIOの音高）', 'identity': '原音（再合成の正解参照）'}
CURRENT_LABELS = {'hnm': '自作HNM', 'world_harvest': 'WORLD（Harvest）', 'identity': '原音'}


def esc(value):
    return html.escape(str(value), quote=True)


def brief(results):
    data = json.loads((results / 'results.json').read_text(encoding='utf-8'))
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
    refs = {r['case']: r for r in selected if r['method'] == reference}
    body = []
    for method in dict.fromkeys(r['method'] for r in selected if r['method'] != 'identity'):
        records = [r for r in selected if r['method'] == method]
        values, deltas = [], []
        for r in records:
            value = r.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            base = refs.get(r['case'], {}).get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            if value is not None:
                values.append(value)
                if base is not None:
                    deltas.append(value - base)
        failed = sum(r['status'] != 'measured' or r.get('measurement', {}).get('status') != 'ok' for r in records)
        cells = [LABELS.get(method, method), f'{median(values):.3f}' if values else '未測定',
                 f'{median(deltas):+.3f}' if deltas else '比較不能', f'{len(values)}/{len(records)}', failed]
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の比較。差分の相手：{esc(LABELS.get(reference, reference))}。'
            '誤差は小さいほど原音に近く、差分が負なら比較相手より小さい値です。知覚品質の順位ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>スペクトル誤差中央値 dB</th>'
            '<th>対応する差分の中央値 dB</th><th>有効／全件</th><th>処理・測定失敗</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _brief_supplement(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['groups']['全体']
    rows = []
    missing = False
    for method, group in summary.items():
        cells = [data['method_labels'][method]]
        for key in ('mos', 'envelope'):
            metric = group['metrics'][key]
            cells.append(f'{metric["mean"]:.3f}' if metric['mean'] is not None else '未測定')
            missing |= metric['valid'] != data['planned_cases']
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    base = summary['hnm']['metrics']['envelope']['mean']
    candidate = summary['candidate']['metrics']['envelope']['mean']
    comparison = ''
    if base and candidate is not None:
        change = (candidate / base - 1) * 100
        comparison = f'<p>音量変動の再現誤差は、候補が当時のベースより平均{abs(change):.1f}%{"減少" if change < 0 else "増加"}。</p>'
    note = '<p>一部未測定です。比較できる範囲は詳細を確認してください。</p>' if missing else ''
    return (comparison + '<div class="scroll"><table><tr><th>方式</th>'
            '<th>自動MOS<br>高いほど良い</th><th>音量変動の再現誤差<br>低いほど良い</th></tr>'
            + ''.join(rows) + '</table></div>' + note
            + '<p><small>日本語12録音の補助評価。自動MOSは、この言語・発声での妥当性を未確認です。</small></p>')


def _brief_expanded(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['全体']
    rows = []
    for method, group in summary.items():
        mos, envelope = group['metrics']['mos'], group['metrics']['envelope']
        delta = envelope['difference_from_base']['mean_difference']
        mos_text = f'{mos["mean"]:.3f}' if mos['mean'] is not None else '未測定'
        error_text = f'{envelope["mean"]:.3f}' if envelope['mean'] is not None else '未測定'
        delta_text = f'{delta:+.3f}' if delta is not None else '—'
        values = [data['method_labels'][method], mos_text, error_text, delta_text,
                  f'{mos["valid"]}/{data["planned_cases"]}']
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    return ('<div class="scroll"><table><tr><th>方式</th><th>予測MOS ↑</th><th>包絡誤差 ↓</th>'
            '<th>ベースとの差 ↓</th><th>MOS有効数</th></tr>'+''.join(rows)+'</table></div>')


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
                 f'{median(deltas):+.3f}' if deltas else '—', f'{len(values)}/{len(records)}',
                 f'{len(deltas)}/{len(records)}', f'{failed}/{len(records)}']
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の再合成。差分は{esc(CURRENT_LABELS.get(reference, reference))}比。'
            '誤差は小さいほど原音に近く、知覚品質の順位ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>誤差中央値 dB</th>'
            '<th>差分中央値 dB</th><th>有効／全件</th><th>比較可能／全件</th><th>失敗／全件</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def short_audio(results):
    path = results / 'audio_samples.json'
    if not path.exists():
        measurements = json.loads((results / 'results.json').read_text(encoding='utf-8'))
        if measurements.get('study_role') == 'supplement_to_completed_fixed_120':
            parent = results.parents[2] / 'noise-envelope/results/run-001'
            return ('<p><small>日本語の音声は公開していません。以下は親の120録音比較で公開済みの英語例です。</small></p>'
                    + short_audio(parent))
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
        order = ['candidate', 'identity', 'hnm', 'world_harvest']
        samples = sorted((s for s in samples if s['method'] in labels),
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
        return (f'<p>同じ区間の音声（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）</p>'
                '<div class="audio-grid">'+''.join(cards)+'</div>')
    return (f'<p>短い音声例：{esc(chosen["label"])}（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）。'
            '同じ原音・区間を各方式で比較できます。</p><div class="audio-grid">'+''.join(cards)+'</div>')
