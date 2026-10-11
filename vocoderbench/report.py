"""Self-contained HTML, generated strictly from recorded measurements."""
import html
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def esc(value):
    return html.escape(str(value))


def fmt(value, digits=3):
    return '—' if value is None else f'{value:.{digits}f}'


def render(data, path):
    ref = {r['case']:r for r in data['resynthesis'] if r['method']==data['comparison_reference']}
    rows, groups = [], defaultdict(list)
    for r in data['resynthesis']:
        m = r.get('measurement',{})
        metric = m.get('mr_stft_log_magnitude_mae_db')
        base_metric = ref.get(r['case'],{}).get('measurement',{}).get('mr_stft_log_magnitude_mae_db')
        delta = metric-base_metric if metric is not None and base_metric is not None else None
        pitch = m.get('pitch') or {}
        voiced = f"{pitch.get('valid_voiced_frames','—')} / {pitch.get('expected_voiced_frames','—')}"
        row = [r['case'],r['method'],r['status']+'/'+m.get('status','undefined'),
               fmt(metric),fmt(delta),fmt((m.get('band_energy') or {}).get('active_band_mae_db')),
               fmt(m.get('rms_gain_error_db')),fmt(pitch.get('abs_error_cents_p95')),voiced,
               pitch.get('false_voiced_frames','—'),m.get('length_delta_samples','—'),fmt(r.get('repeat_max_abs_diff'),9)]
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in row)+'</tr>')
        if r['method']!='identity':
            group='自然音声' if r['kind']=='natural_speech' else '合成診断信号'
            groups[(group,r['method'])].append(r)
    summaries=[]
    for (group,method), records in groups.items():
        vals=[r['measurement']['mr_stft_log_magnitude_mae_db'] for r in records
              if r.get('measurement',{}).get('mr_stft_log_magnitude_mae_db') is not None]
        failures=sum(r['status']!='measured' or r.get('measurement',{}).get('status')!='ok' for r in records)
        summaries.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [group,method,len(records),len(vals),failures,
                  fmt(float(np.median(vals)) if vals else None)])+'</tr>')
    op_rows=[]
    for r in data['operations']:
        p=r.get('pitch_against_known_truth') or {}
        rel=r.get('relative_pitch') or {}
        op_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [r['case'],r['method'],r['operation'],r['status'],
                    fmt(r.get('gain_tracking_error_db'),6),fmt(p.get('abs_error_cents_p95')),fmt(rel.get('p95_error_cents')),
                    f"{rel.get('valid_pairs','—')}/{rel.get('total_frames','—')}",f"{p.get('valid_voiced_frames','—')}/{p.get('expected_voiced_frames','—')}",p.get('missing_voiced_frames','—'),p.get('false_voiced_frames','—'),r.get('length_error_samples','—'),
                    fmt((r.get('event') or {}).get('error_ms'))])+'</tr>')
    failure_details=[r for r in data['resynthesis'] if r['status']!='measured' or r.get('measurement',{}).get('status')!='ok']
    cal_values=[(r['measurement'].get('pitch') or {}).get('abs_error_cents_p95') for r in data['calibration']]
    cal_values=[v for v in cal_values if v is not None]
    max_cal=max(cal_values) if cal_values else None
    natural=[c for c in data['cases'] if c['kind']=='natural_speech']
    natural_speakers=len(set(c.get('speaker',c['id']) for c in natural))
    natural_seconds=sum(c['n_samples']/c['sr'] for c in natural)
    ref_label=esc(data['comparison_reference'])
    cal_missing=sum((r['measurement'].get('pitch') or {}).get('missing_voiced_frames',0) for r in data['calibration'])
    cal_false=sum((r['measurement'].get('pitch') or {}).get('false_voiced_frames',0) for r in data['calibration'])
    base=data['formal_base']
    base_label='正式base未選定' if base['method'] is None else f"正式base: {base['method']}"
    content=f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>非MLボコーダー 比較基盤の初回測定</title>
<style>
:root{{color-scheme:light;--ink:#172a3a;--muted:#506375;--line:#d8e2ea;--accent:#156d79}}
body{{font:15px/1.75 system-ui,sans-serif;color:var(--ink);background:#f6f8fb;margin:0}}
main{{max-width:1450px;margin:auto;padding:36px 26px 70px}}h1{{font-size:30px;margin:0 0 12px}}h2{{font-size:22px;margin-top:38px}}
.tag{{letter-spacing:.12em;color:var(--accent);font-size:12px;font-weight:700}}.notice{{border-left:5px solid var(--accent);background:white;padding:18px 24px;margin:22px 0}}
p{{max-width:1000px}}table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#e7eef5}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:8px}}input{{padding:12px;border:1px solid #9fb2c3;border-radius:6px;width:min(500px,80%);margin:12px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#fff;padding:16px}}a{{color:#126d8a}}small{{color:var(--muted)}}
</style><main><div class="tag">NON ML VOCODER · REPRODUCIBLE COMPARISON</div>
<h1>比較対象と測定方法を整える</h1>
<p>既存の非ML方式を同じ入力で動かし、測定の妥当性・失敗・再現性を確認した初回結果です。音質の最良や知覚的な透明性を認定する実験ではありません。</p>
<div class="notice"><strong>{esc(base_label)}</strong><br>{esc(base['reason'])}<br>各表のΔの比較相手は <strong>{esc(data['comparison_reference'])}</strong> との差です。{("未選定時の表示基準であり、正式baseとの差ではありません。" if base["method"] is None else "その時点の正式baseとの差です。") }初代選定後もbaseとversionを記録して比較します。</div>
<h2>比較の役割</h2><ul><li>WORLD DIO + StoneMask と WORLD Harvest：同じCheapTrick・D4C・合成器に対する解析器の比較。</li><li>LLSM layer 0：WORLD DIOの同じF0を渡して別の解析合成表現を比較。独立F0推定器を持つend-to-end比較ではありません。</li><li>Identity：測定器の検査だけに使う原音コピー。ボコーダーの候補や最良手法には数えません。</li></ul>
<h2>測定条件</h2><p>今回の自然音声はLibriSpeechの{natural_speakers}話者、{len(natural)}区間、合計{fmt(natural_seconds,1)}秒です（読み込めた固定先頭区間）。人工信号は加算合成、パルス列とIIR共鳴器、変調雑音、無音、インパルスで作り、評価対象デコーダーから生成していません。録音の新しい聴取評価は行っていません。</p>
<p>自動時間整列・動的時間伸縮・ゲイン正規化は行いません。MR-STFTは5/20/80 ms。音高は独立YIN型測定器で既知F0に対して測定します。自然音声のF0の絶対正解はありません。—は未定義・対象外でありゼロ誤差ではありません。</p>
<p>F0診断だけに固定2 kHz・6次Butterworth forward/backwardと最大80 msのeven反射を適用します。2 kHz以下に十分な周期成分が必要で、自然音声全般の精度は未校正です。STFT・帯域・レベル測定はこの前処理を使いません。<a href="../../docs/F0_CALIBRATION.md">78ケースの校正と追加反例</a>も確認してください。</p>
<h2>測定器の校正</h2><p>入力信号をそのまま測定した音高誤差P95のケース最大値: <strong>{fmt(max_cal)} cent</strong>。既知有声の欠測: {cal_missing} frame、既知無声の誤有声: {cal_false} frame。境界を跨ぐフレームは別計数です。詳細と欠測分母は <a href="results.json">results.json</a> に保存しています。</p>
<p>別途、copy、既知gain、10 ms shift、lowpass、crop、NaN、Inf、DC、無音化による独立監査を行います。その記録は <a href="metric_audit_results.json">測定器監査</a> を参照してください。</p>
<h2>層別の要約</h2><p>同一条件の対応のある比較を基本にします。以下はケース中央値の診断値で、MOSでも品質順位でもありません。失敗件数を分母とともに残します。</p>
<div class="scroll"><table><thead><tr><th>群</th><th>方式</th><th>全ケース</th><th>有効スコア</th><th>処理・測定失敗</th><th>MR-STFT中央値 dB</th></tr></thead><tbody>{''.join(summaries)}</tbody></table></div>
<h2>無加工再合成の全ケース</h2><p>「measured / ok」は計算できたという状態です。無音化、音高欠測、レベル誤差などを含め、品質合格を意味しません。STFT・帯域差・cent誤差は小さいほど原音に近い診断値です。</p><input id="filter" aria-label="ケースまたは方式で絞り込み" placeholder="ケースまたは方式で絞り込み">
<div class="scroll"><table id="cases"><thead><tr>{''.join('<th>'+v+'</th>' for v in ['入力','比較対象','状態','MR-STFT dB','Δ対'+ref_label+' dB','帯域差 dB','RMS差 dB','F0 P95 cent','有声測定/真値','誤有声frame','長さ差sample','再実行最大差'])}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>操作試験</h2><p>未操作の同方式出力からの変化を測ります。既知F0への絶対誤差と、出力間の相対変化推定を区別します。時間操作の全長一致だけでは局所イベントや末尾の保持を保証しません。LLSMの操作は今回未実装であり、合格に数えません。</p>
<div class="scroll"><table><thead><tr>{''.join('<th>'+v+'</th>' for v in ['入力','方式','操作','状態','gain追従誤差 dB','真値F0 P95 cent','相対F0 P95 cent','相対有効/全frame','真値有効/有声frame','真値欠測frame','真値誤有声frame','長さ誤差sample','イベント誤差ms'])}</tr></thead><tbody>{''.join(op_rows)}</tbody></table></div>
<h2>デコーダー単体と失敗記録</h2><details><summary>手作り特徴からの合成結果</summary><pre>{esc(json.dumps(data['decoder_only'],ensure_ascii=False,indent=2))}</pre></details><details><summary>処理・測定の失敗 {len(failure_details)} 件</summary><pre>{esc(json.dumps(failure_details,ensure_ascii=False,indent=2))}</pre></details>
<h2>今回判断できないこと</h2><p>多話者・多言語・日本語・歌唱・ささやきへの一般化、話者類似度・表現距離の知覚的妥当性、息っぽさ等の知覚制御、動的・複合操作、長時間連続処理、未使用の最終評価データでの優位は未確認です。48 kHzの人工信号が動いても、48 kHz自然音声の品質確認にはなりません。外部MOS予測器、ViSQOL、eSTOIは今回計測していません。</p>
<h2>再現情報</h2><p><a href="results.json">全数値JSON</a> ／ <a href="../../docs/EVALUATION.md">測定仕様</a> ／ <a href="../../docs/WORKFLOW.md">進め方</a> ／ <a href="../../docs/reviews/discussion.md">5人の議論</a></p><pre>{esc(json.dumps({'environment':data['environment'],'parent_commit':data['parent_commit'],'data_status':data['data_status']},ensure_ascii=False,indent=2))}</pre>
<p><small>ユーザー指示の正本はリポジトリのUSER_INSTRUCTIONS.mdです。この結果と解釈はAI作成物です。</small></p></main>
<script>document.getElementById('filter').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('#cases tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));}});</script></html>'''
    Path(path).write_text(content,encoding='utf-8')
