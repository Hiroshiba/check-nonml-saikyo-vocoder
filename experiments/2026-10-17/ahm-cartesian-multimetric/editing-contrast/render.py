import json
from pathlib import Path
p = Path('editing-contrast-diagnostic-20261018')
d = json.loads((p / 'results.json').read_text())
fields = ('metric', 'condition', 'planned_recordings', 'paired_recordings', 'paired_speakers', 'value_order', 'speaker_equal_means', 'candidate_edit_change', 'pml_edit_change', 'difference_of_changes', 'difference_ci95')
projection = {k: d[k] for k in ('scope', 'source_summary_sha256', 'cohort_sha256', 'sources', 'bootstrap', 'plan_sha256', 'script_sha256', 'numpy_version')}
projection['results'] = [{k: r[k] for k in fields} for r in d['results']]
(p / 'scalar-results.json').write_text(json.dumps(projection, ensure_ascii=False, indent=2) + '\n')
rows = []
for r in projection['results']:
    name = '自動MOS' if r['metric'] == '1.native_mos' else 'ECAPA'
    q = '−3半音' if r['condition'] == 'pitch_minus3' else '＋3半音'
    vals = r['speaker_equal_means']
    ci = r['difference_ci95']
    rows.append(f"<tr><th>{name}<br>{q}</th><td>{r['paired_recordings']}/120録音<br>{r['paired_speakers']}話者</td><td>{vals[0]:.6f} → {vals[1]:.6f}<br>差 {r['candidate_edit_change']:+.6f}</td><td>{vals[2]:.6f} → {vals[3]:.6f}<br>差 {r['pml_edit_change']:+.6f}</td><td>{r['difference_of_changes']:+.6f}<br>[{ci[0]:+.6f}, {ci[1]:+.6f}]</td></tr>")
s = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>編集前後の差を同じ録音で比べる</title><style>body{max-width:1150px;margin:30px auto;padding:0 20px;font:16px/1.7 system-ui;color:#243346}table{width:100%;border-collapse:collapse;background:white}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}.scroll{overflow:auto}.note{background:#fff0cd;padding:16px}small{color:#546271}@media(prefers-color-scheme:dark){body{background:#17212d;color:#e4eaf2}table,.scroll{background:#202d3b}td,th{border-color:#425265}.note,.notice{background:#423720;color:#f1e8d6}a{color:#99c8ff}small{color:#bac6d5}}</style><h1>編集前後の差を同じ録音で比べる</h1><p class="note">既存主評価の保存値を使った事後的な追加集約です。新しい音声・モデル推論はありません。候補の採用、音質の因果的説明、未見データでの確認を意味しません。</p><h2>現PMLとの比較</h2><p>候補は無編集時に高い自動MOSを持ちますが、音高編集後の低下はPMLより大きくなっています。同じ録音で無編集・編集の両方を持つものだけを比較しました。単に異なる支持の平均値を引いた結果ではありません。</p><div class="scroll"><table><thead><tr><th>指標・条件</th><th>対応支持</th><th>候補：無編集→編集</th><th>PML：無編集→編集</th><th>編集前後差の候補−PML<br>95%記述区間</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div><p>差の差 = (候補編集−候補無編集) − (PML編集−PML無編集)。負なら、この指標で候補の編集前後差がPMLより低い方向です。録音ごとの対応差から話者内平均、40話者等重み平均を計算。話者bootstrap 2,000回、seed 20261018、多重比較未補正。</p><h2>この結果から分けて考えること</h2><ul><li>音高追従と編集後の自然さ・話者類似度は別です。追従指標が良くても他の性質を保てるとは限りません。</li><li>自動MOSは人間の新しい評定ではありません。ECAPAは意図した音高変更にも反応し得るため、低下だけで声質破壊を断定しません。</li><li>元の開発集合を使った探索です。失敗した録音は0補完せず、予定120との差を残しています。</li><li>端点保持候補の同一環境評価とは別の、旧Cartesian候補の主評価保存値です。計測環境や候補版を混ぜません。</li></ul><h2>出典</h2><p><a href="scalar-results.json">元精度の集約数値・出典SHA</a> ／ <a href="PLAN-ja.md">事後診断の計画</a> ／ <a href="../ordinary/ordinary.html">元の全79軸・短音声</a></p><p>再計算したのはこの編集差とその記述区間だけです。元の主評価・順位・音声・測定値は変更していません。</p></html>'
(p / 'index.html').write_text(s)
print(len(s.encode()))
