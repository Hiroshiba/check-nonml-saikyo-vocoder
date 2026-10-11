"""拡充比較の日本語HTML。比較表と同一区間の音声を冒頭に置く。"""
import html
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from .benchmark_summary import METRICS, build_summary
from .benchmark_io import LABELS

CSS = '''
:root{color-scheme:light dark;--bg:#f5f7fa;--fg:#1e3044;--panel:#fff;--line:#ccd7e0;--link:#006879}
@media(prefers-color-scheme:dark){:root{--bg:#101823;--fg:#e0e9f2;--panel:#192637;--line:#405064;--link:#75dce0}}
body{background:var(--bg);color:var(--fg);font:16px/1.7 system-ui,sans-serif;margin:0}
main{max-width:1120px;margin:auto;padding:28px 22px 72px}h1{font-size:28px}h2{margin-top:32px;font-size:22px}
a{color:var(--link)}.scroll{overflow:auto}table{border-collapse:collapse;min-width:650px;width:100%;font-size:14px}
td,th{padding:9px;border-bottom:1px solid var(--line);text-align:right}td:first-child,th:first-child{text-align:left}
.box{background:var(--panel);padding:18px;border:1px solid var(--line);border-radius:10px;margin:18px 0}
.audio{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}audio{width:100%}
small{opacity:.85}details{margin:20px 0}summary{cursor:pointer}code{overflow-wrap:anywhere}
'''


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, signed=False):
    return '未測定' if value is None else format(value, '+.3f' if signed else '.3f')


def overview(data, summary):
    cells = []
    for method, row in summary['全体'].items():
        values = [esc(data['method_labels'][method])]
        for key in ('mos', 'estoi', 'envelope', 'stft'):
            metric = row['metrics'][key]
            values.append(f'{number(metric["mean"])}<br><small>{metric["valid"]}/{data["planned_cases"]}</small>')
        values.append(f'{row["processing_success"]}/{data["planned_cases"]}')
        cells.append('<tr>' + ''.join(f'<td>{v}</td>' for v in values) + '</tr>')
    mos = [row['mos']['value'] for row in data['calibration'] if row['mos'].get('value') is not None]
    reference = number(sum(mos) / len(mos)) if mos else '未測定'
    return ('<div class="scroll"><table><thead><tr><th>方式</th><th>予測MOS ↑</th><th>eSTOI ↑</th>'
            '<th>10 ms包絡誤差 ↓</th><th>スペクトル誤差 dB ↓</th><th>処理成功</th></tr></thead>'
            f'<tbody>{"".join(cells)}</tbody></table></div><p>原音の予測MOS：{reference} '
            f'（{len(mos)}/{data["planned_cases"]}）。各値は発話平均、下段は有効／予定件数。</p>')


def detail_table(scope):
    rows = []
    for method, group in scope.items():
        for key, label, _ in METRICS:
            m = group['metrics'][key]
            delta = m['difference_from_base']
            ci = delta['speaker_bootstrap_95']
            interval = '—' if ci is None else f'[{number(ci[0], True)}, {number(ci[1], True)}]'
            cells = [LABELS[method], label, number(m['mean']), number(m['worst_5_percent_mean']),
                     number(delta['mean_difference'], True), interval,
                     f'{m["valid"]}/{m["total"]}', f'{delta["paired"]}/{delta["total"]}']
            rows.append('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in cells) + '</tr>')
    return ('<div class="scroll"><table><thead><tr><th>方式</th><th>指標</th><th>平均</th>'
            '<th>悪い側5%平均</th><th>ベースとの差</th><th>差の95%区間</th><th>有効</th><th>対比較</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def decision_section(path):
    if not path.exists():
        return ''
    decision = json.loads(path.read_text())
    rows = []
    for item in decision['conditions']:
        values = [item['label'], item['observed'], item['required'], item['outcome']]
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in values) + '</tr>')
    return (f'<div class="box"><strong>{esc(decision["title"])}</strong>'
            f'<p>{esc(decision["reason"])}</p><details><summary>事前条件ごとの判定</summary>'
            '<div class="scroll"><table><tr><th>条件</th><th>実測</th><th>事前規則</th><th>結果</th></tr>'
            + ''.join(rows) + '</table></div></details>'
            '<p><a href="audit.json">欠測・反復・振幅の確認記録</a> ／ '
            '<a href="decision.json">採否記録</a></p></div>')


def render(data, target):
    target = Path(target)
    summary = build_summary(data)
    (target.parent / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    body = '<h1>固定120音声：雑音包絡候補・ベース・WORLDの比較</h1>'
    body += overview(data, summary)
    body += decision_section(target.parent / 'decision.json')
    body += ('<p>包絡・スペクトルは自作2方式の8 seed平均、WORLDは固定出力。'
             '帯域・レベル・変調も8 seed平均、MOS・eSTOI・F0・振幅上限率は事前固定のseed 0です。'
             '反復に失敗がある場合は有効反復だけの値なので、処理成功数と確認記録を併読してください。'
             'MOSは予測値で、新規の人間評定ではありません。</p>')
    audio_path = target.parent / 'audio_samples.json'
    if audio_path.exists():
        samples = json.loads(audio_path.read_text())['samples']
        for case in dict.fromkeys(s['case'] for s in samples):
            body += f'<h2>同一区間の音声</h2><small>{esc(case)}・先頭最大2秒・音量補正なし</small><div class="audio">'
            for sample in samples:
                if sample['case'] != case:
                    continue
                body += f'<div><p>{esc(LABELS[sample["method"]])}</p><audio controls preload="none" src="{esc(sample["data_uri"])}"></audio></div>'
            body += '</div>'
    body += ('<div class="box"><strong>評価範囲</strong><p>英語の女性20話者・男性20話者（配布メタデータ）から、'
             '各3発話の通常朗読120録音。120件を固定して繰り返す開発用比較であり、未使用の最終評価ではありません。'
             '日本語・ささやき・裏声はこの集合では未評価です。今回の再合成へのMOSの人間評定による校正も未実施です。</p>'
             '<p>UTMOSv2のfold 0・BVCC条件・抽出1回を固定しています。論文の複数モデル平均と同じ成績は主張しません。'
             'eSTOIは明瞭性、F0欄は独立解析器の推定整合性であり、自然音声の正解F0ではありません。</p></div>')
    for scope, values in summary.items():
        label = scope.replace('ja/', '日本語・').replace('en/', '英語・').replace('normal', '通常').replace('whisper', 'ささやき').replace('falsetto', '裏声').replace('/F', '・女性').replace('/M', '・男性')
        body += f'<details><summary>{esc(label)}：全指標・ベースとの差・欠測</summary>{detail_table(values)}</details>'
    body += ('<p>差は候補またはWORLDから当時のベースを引いた値。矢印は望ましい方向です。'
             '信頼区間は配布女性・男性の比率を保った話者単位の再標本化2,000回で算出し、seedや音声フレームを独立標本と数えていません。'
             '指標間の多数決や総合点は作りません。</p><p><a href="results.json">発話別の全測定値</a> ／ '
             '<a href="summary.json">集計値</a> ／ <a href="../../index.html">調査・議論・採否</a></p>')
    timestamp = datetime.fromisoformat(data['generated_at']).astimezone(ZoneInfo('Asia/Tokyo'))
    body += (f'<p><small>測定記録の生成：{timestamp:%Y年%m月%d日 %H:%M:%S}（日本時間）。'
             '音声はLibriSpeech（Panayotovほか、原録音LibriVox）、CC BY 4.0。'
             '<a href="https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/data/ATTRIBUTION.md">'
             '出典・抜粋と再合成の説明</a>。</small></p>')
    target.write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                      f'<title>固定120音声の比較</title><style>{CSS}</style><body><main>{body}</main></body></html>')
