"""追加指標の値・ベースとの差・欠測・各回の計算時間を表示する。"""
from __future__ import annotations

from collections import Counter
from html import escape
import json
import os
from pathlib import Path

from .quality_core import write_json

STATUSES = {'measured': '測定済み', 'failed': '失敗', 'partial_failure': '一部失敗',
            'unavailable': '資産・依存不足', 'not_configured': '未設定',
            'not_applicable': '対象外', 'pending': '未実行'}


def text(value):
    return escape(str(value))


def number(value):
    return '—' if value is None else f'{value:.6g}'


def render(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    baseline = report['input']['baseline']
    formal_base = report['input'].get('formal_base')
    base_description = json.dumps(formal_base, ensure_ascii=False) if formal_base else '未指定'
    rows = report['rows']
    lookup = {(r['metric'], r['case'], r['method']): r for r in rows}
    summary = {}
    for metric in report['metrics']:
        selected = [r for r in rows if r['metric'] == metric]
        summary[metric] = {'planned': len(selected), 'statuses': dict(Counter(r['status'] for r in selected)),
                           'initialization': report['metrics'][metric]}
    write_json(output / 'summary.json', summary)
    table = []
    for row in rows:
        measured = row.get('measurement', {})
        value = row.get('value')
        base = lookup.get((row['metric'], row['case'], baseline), {})
        difference = value - base['value'] if value is not None and base.get('value') is not None else None
        warm = measured.get('warm_wall_seconds', {})
        reason = row.get('reason') or measured.get('first', {}).get('reason') or ''
        table.append('<tr>' + ''.join(f'<td>{value}</td>' for value in (
            text(row['case']), text(row['method']), text(row['label']), text(row['unit']),
            number(value), number(difference), text(STATUSES.get(row['status'], row['status'])),
            number(measured.get('first', {}).get('wall_seconds')), number(warm.get('median')),
            text(f"{warm.get('count', 0)}/{measured.get('planned_repetitions', report['repetitions'])}"), text(reason))) + '</tr>')
    source_link = ''
    if report['input'].get('original_report'):
        relative = os.path.relpath(report['input']['original_report'], output)
        source_link = f'<p><a href="{escape(relative, quote=True)}">元の比較と音声</a>（同じ配置で閲覧してください）</p>'
    details = text(json.dumps({'metrics': report['metrics'], 'environment': report['environment']},
                              ensure_ascii=False, indent=2))
    html = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>保存音声の追加品質指標</title><style>
:root{{color-scheme:light dark}}body{{font-family:system-ui,sans-serif;max-width:1450px;margin:auto;padding:24px;line-height:1.6}}
table{{border-collapse:collapse;min-width:100%;font-size:.9rem}}th,td{{border:1px solid #8888;padding:6px;text-align:left}}
.scroll{{overflow:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}h1{{font-size:1.6rem}}
</style><h1>保存音声の追加品質指標</h1>
<p>比較基準: <strong>{text(baseline)}</strong>。差は「その方式−比較基準」です。品質の優劣・採否を自動認定しません。</p>
<p>元記録の開発ベース指定: {text(base_description)}。比較基準の指定は正式baseの選定とは別です。</p>
<p>SCOREQ・ERBは低いほど近く、予測MOS・ViSQOL・話者類似度は高い方向です。異なる指標を合算しません。
未設定・資産不足・対象外・失敗は0点ではありません。</p>{source_link}
<div class="scroll"><table><thead><tr><th>音声</th><th>方式</th><th>指標</th><th>単位</th><th>値</th><th>比較基準との差</th>
<th>状態</th><th>初回秒</th><th>反復中央値秒</th><th>有効反復</th><th>理由</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<h2>測定範囲</h2><p>保存済み音声が対象です。参照距離SCOREQ・ViSQOL・ERBは無編集再合成用で、意図した編集の罰則にしません。
適用条件を満たす編集点は、非参照MOSと固定参照の話者類似度を別工程から渡せます。
ECAPAの同一長・同一標本化周波数の条件は維持し、話者保持を目的としない声質変更へ一律要求しません。
一般的な主観品質や日本語・特殊発声での評価精度は未校正です。
反復は同一音声・同一seedでの処理時間測定であり、独立した話者や聴取評定には数えません。
初回秒はケースごとの最初の呼び出しで、最初のケース以外はモデル自体は温まっています。</p>
<p>初期化はモデル読み込みと資産hash確認を含めて別計測します。ViSQOL CLIは各回にプロセス起動・モデル読み込み・WAV入出力を含み、
そのCPU秒は親プロセスのみです。各回の値と時間は<a href="results.json">results.json</a>に保存しています。</p>
<p><a href="quality-evidence-index.json">品質証跡の一覧</a>に、原音MOSと各出力のMOS・話者類似度（要求分のみ）を記録します。
原音の参照型自己比較は行いません。欠測の証跡も残し、音声hashがないものは曲線に利用できません。</p>
<details><summary>評価器の来歴・初期化・環境</summary><pre>{details}</pre></details></html>'''
    (output / 'index.html').write_text(html, encoding='utf-8')


def render_similarity(result, path):
    rows = []
    for name, group in result['comparison'].get('groups', {}).items():
        rows.append('<tr>' + ''.join(f'<td>{value}</td>' for value in (
            text(name), number(group['spearman_rho']), number(group['rated_neighbor_top1_agreement']), str(group['valid_pairs']),
            str(group['planned_pairs']), str(group['speakers_with_valid_pairs']),
            text(STATUSES.get(group['status'], group['status'])))) + '</tr>')
    metadata = text(json.dumps(result['feature_metadata'], ensure_ascii=False, indent=2))
    html = f"""<!doctype html><html lang="ja"><meta charset="utf-8"><title>既存話者類似度評定と特徴距離</title>
<style>:root{{color-scheme:light dark}}body{{font-family:system-ui;max-width:1000px;margin:auto;padding:24px}}td,th{{padding:8px;border:1px solid #8888}}pre{{white-space:pre-wrap}}</style>
<h1>既存話者類似度評定と特徴距離</h1><p>評定groupごとに示します。相関を総合品質や再合成音への人間評定とみなしません。</p>
<table><tr><th>group</th><th>Spearman相関</th><th>評定対内の最近傍一致</th><th>有効対</th><th>予定対</th><th>有効話者</th><th>状態</th></tr>{''.join(rows)}</table>
<p>話者対は独立標本ではないため、単純なp値や信頼区間は出していません。比較不能・欠測を0に置き換えません。</p>
<p>時間は特徴抽出・読込を除いた距離と集約の時間です。生値・各回の時間は同名のJSONを参照してください。</p>
<pre>{metadata}</pre></html>"""
    Path(path).write_text(html, encoding='utf-8')
