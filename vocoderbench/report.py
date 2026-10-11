"""保存済みの測定値から、日本語で読める比較結果HTMLを作る。"""
import html
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .audio_report import section as audio_section
from .site_summary import CURRENT_LABELS


def esc(value):
    return html.escape(str(value))


def fmt(value, digits=3):
    return '—' if value is None else f'{value:.{digits}f}'


METHODS = {'world_dio': 'WORLD・DIO解析', 'world_harvest': 'WORLD・Harvest解析',
           'llsm_world_dio': 'LLSM・WORLDの音高を使用', 'identity': '原音コピー（測定器の検査用）'}
STATUSES = {'measured': '処理完了', 'ok': '測定完了', 'failed': '処理失敗',
            'undefined': '測定なし', 'error': '処理エラー',
            'length_mismatch': '長さ不一致', 'empty_signal': '空の信号', 'nonfinite_input_or_output': '入力または出力に無効な数値'}
OPERATIONS = {'gain_up6': '音量 +6 dB', 'gain_down6': '音量 −6 dB',
              'pitch_up3': '音高 +3半音', 'pitch_down3': '音高 −3半音', 'time_1p25': '時間長 1.25倍'}
INPUTS = {'sine_': '正弦波', 'harmonic_sweep_': '音高が連続的に変わる調波音',
          'harmonic_': '調波音', 'missing_fundamental_': '基本波を除いた調波音',
          'pulse_iir_vowel_': 'パルス列と共鳴器による母音様音', 'am_noise_': '音量が周期的に変わる雑音',
          'voiced_unvoiced_boundaries_': '有声・無声の切替', 'silence_': '無音',
          'impulse_': '瞬間的なパルス', 'librispeech_': 'LibriSpeechの自然音声'}


def label(value, names):
    """機械用の識別子も残し、説明と元データを対応づける。"""
    return f'{names[value]}（{value}）' if value in names else f'未分類（{value}）'


def input_label(value):
    description = next((name for prefix, name in INPUTS.items() if value.startswith(prefix)), '入力')
    return f'{description}（{value}）'


def _table(headers, rows):
    heading = ''.join(f'<th>{esc(cell)}</th>' for cell in headers)
    body = ''.join('<tr>'+''.join(f'<td>{esc(cell)}</td>' for cell in row)+'</tr>' for row in rows)
    return f'<div class="scroll"><table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>'


def _pitch_cells(pitch):
    return [fmt(pitch.get('abs_error_cents_p95')),
            f"{pitch.get('valid_voiced_frames', '—')}/{pitch.get('expected_voiced_frames', '—')}",
            pitch.get('missing_voiced_frames', '—'), pitch.get('false_voiced_frames', '—')]


def _render_current(data, path):
    """第2版は比較と音声を先頭へ置き、全数値の詳細を折りたたむ。"""
    path = Path(path)
    reference = data['comparison_reference']
    def name(method):
        return CURRENT_LABELS.get(method, method)
    refs = {r['case']: r for r in data['resynthesis'] if r['method'] == reference}
    groups, all_rows = defaultdict(list), []
    for row in data['resynthesis']:
        measurement = row.get('measurement', {})
        value = measurement.get('mr_stft_log_magnitude_mae_db')
        base_value = refs.get(row['case'], {}).get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
        delta = value - base_value if value is not None and base_value is not None else None
        group = '自然音声' if row['kind'] == 'natural_speech' else '人工信号'
        if row['method'] != 'identity':
            groups[(group, row['method'])].append((row, value, delta))
        all_rows.append([input_label(row['case']), name(row['method']),
                         STATUSES.get(row['status'], row['status']),
                         STATUSES.get(measurement.get('status', 'undefined'), '測定なし'),
                         fmt(value), fmt(delta), fmt((measurement.get('band_energy') or {}).get('active_band_mae_db')),
                         fmt(measurement.get('rms_gain_error_db')), *_pitch_cells(measurement.get('pitch') or {}),
                         measurement.get('length_delta_samples', '—'), fmt(row.get('repeat_max_abs_diff'), 9)])
    summaries = []
    for (group, method), records in sorted(groups.items(), key=lambda item: (item[0][0] != '自然音声', item[0][1] != reference, item[0][1])):
        values = [value for _, value, _ in records if value is not None]
        deltas = [delta for _, _, delta in records if delta is not None]
        failed = sum(row['status'] != 'measured' or row.get('measurement', {}).get('status') != 'ok'
                     for row, _, _ in records)
        summaries.append([group, name(method), fmt(float(np.median(values)) if values else None),
                          fmt(float(np.median(deltas)) if deltas else None),
                          f'{len(values)}/{len(records)}', f'{len(deltas)}/{len(records)}', f'{failed}/{len(records)}'])
    summary_table = _table(['入力群', '方式', 'MR-STFT中央値 dB', '差分中央値 dB',
                            '有効／全件', '比較可能／全件', '処理・測定失敗／全件'], summaries)
    pitch_headers = ['真値F0 P95 cent', '測定できた／真値の有声フレーム', '有声の欠測', '誤有声']
    all_table = _table(['入力', '方式', '処理', '測定', 'MR-STFT dB', '差分 dB', '帯域差 dB',
                        'RMS差 dB', *pitch_headers, '長さ差 サンプル', '再実行最大差'], all_rows)
    operation_rows = []
    for row in data.get('operations', []):
        relative = row.get('relative_pitch') or {}
        operation_rows.append([input_label(row['case']), name(row['method']),
                               OPERATIONS.get(row['operation'], row['operation']),
                               STATUSES.get(row['status'], row['status']), fmt(row.get('gain_tracking_error_db'), 6), fmt((row.get('band_change_after_pitch') or {}).get('active_band_mae_db')),
                               *_pitch_cells(row.get('pitch_against_known_truth') or {}),
                               fmt(relative.get('p95_error_cents')),
                               f"{relative.get('valid_pairs', '—')}/{relative.get('total_frames', '—')}",
                               row.get('length_error_samples', '—'), fmt((row.get('event') or {}).get('error_ms'))])
    operation_table = _table(['入力', '方式', '操作', '状態', 'ゲイン追従誤差 dB', '音高編集後の帯域変化 dB', *pitch_headers,
                              '相対F0誤差 P95 cent', '相対比較可能／全フレーム', '長さ誤差 サンプル',
                              'イベント誤差 ms'], operation_rows)
    decoder_rows = []
    for row in data.get('decoder_only', []):
        decoder_rows.append([name(row.get('method', '未記録')), row.get('f0_hz', '—'),
                             STATUSES.get(row['status'], row['status']), row.get('output_samples', '—'),
                             {True: 'はい', False: 'いいえ'}.get(row.get('finite'), '未確認'),
                             *_pitch_cells(row.get('pitch') or {})])
    decoder_table = _table(['方式', '指定F0 Hz', '状態', '出力サンプル数', '全値が有限', *pitch_headers], decoder_rows)
    diagnostic_rows = []
    for row in data.get('diagnostics', []):
        pitch = row.get('pitch') or row.get('pitch_against_known_truth') or row.get('measurement', {}).get('pitch') or {}
        diagnostic_rows.append([input_label(row.get('case', '未記録')), name(row.get('method', 'hnm')),
                                row.get('label', row.get('variant', row.get('diagnostic', '詳細JSONを参照'))),
                                STATUSES.get(row.get('status', 'undefined'), row.get('status', '測定なし')),
                                *_pitch_cells(pitch)])
    diagnostic_table = _table(['入力', '方式', '条件', '状態', *pitch_headers], diagnostic_rows)
    calibration_rows = [[input_label(row['case']), *_pitch_cells(row.get('measurement', {}).get('pitch') or {})]
                        for row in data.get('calibration', [])]
    calibration_table = _table(['入力', *pitch_headers], calibration_rows)
    failures = [row for row in data['resynthesis'] if row['status'] != 'measured' or row.get('measurement', {}).get('status') != 'ok']
    failures += [row for key in ('operations', 'decoder_only', 'diagnostics') for row in data.get(key, [])
                 if row.get('status') in ('failed', 'error')]
    natural = [case for case in data.get('cases', []) if case['kind'] == 'natural_speech']
    speakers = len({case.get('speaker', case['id']) for case in natural})
    seconds = sum(case['n_samples']/case['sr'] for case in natural)
    base = data['formal_base']
    repo = 'https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/'
    review = repo + 'docs/WORKFLOW.md'
    root = Path(__file__).resolve().parents[1]
    for parent in path.resolve().parents:
        if (parent/'reviews/discussion.md').is_file() and parent.is_relative_to(root):
            review = repo + str((parent/'reviews/discussion.md').relative_to(root))
            break
    iteration = data.get('development_iteration')
    iteration_section = ('<details><summary>初代作成中の改善記録</summary><pre>' + esc(json.dumps(iteration, ensure_ascii=False, indent=2)) + '</pre></details>') if iteration else ''
    provenance = {key: data.get(key) for key in ('environment', 'parent_commit', 'data_status', 'formal_base', 'native_builds')}
    content = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>自作HNMとWORLD（Harvest）の比較</title><style>
:root{{color-scheme:light dark;--ink:#172a3a;--muted:#506375;--line:#d8e2ea;--accent:#156d79;--bg:#f6f8fb;--surface:#fff;--head:#e7eef5;--link:#126d8a}}
body{{font:15px/1.7 system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0}}main{{max-width:1250px;margin:auto;padding:32px 24px 64px}}
h1{{font-size:28px;margin:0 0 12px}}h2{{font-size:22px;margin-top:32px}}h3{{font-size:17px}}p{{max-width:1050px}}a{{color:var(--link)}}small{{color:var(--muted)}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:var(--surface)}}th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th{{background:var(--head)}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}td:first-child{{white-space:normal;min-width:9em;overflow-wrap:anywhere}}
.scroll{{overflow:auto;border:1px solid var(--line);border-radius:8px}}.audio-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}audio{{width:100%}}
details{{margin:16px 0;border:1px solid var(--line);border-radius:8px;padding:14px;background:var(--surface)}}summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}
a:focus-visible,summary:focus-visible,audio:focus-visible{{outline:2px solid var(--accent);outline-offset:3px}}@media(prefers-color-scheme:dark){{:root{{--ink:#e6edf4;--muted:#b3c1d0;--line:#3b4b60;--accent:#68c8c6;--bg:#0f1724;--surface:#182438;--head:#23334a;--link:#7fdae8}}}}
</style><main><h1>自作HNMとWORLD（Harvest）の比較</h1>
<p>ベース：<strong>{esc(name(base.get('method') or reference))}</strong>。誤差は小さいほど原音に近く、差分は{esc(name(reference))}比です。知覚品質の勝敗ではありません。</p>
{summary_table}
{audio_section(path.parent, base.get('method'), compact=True)}
<details><summary>比較条件と指標の読み方</summary>
<p>{esc(base.get('reason', ''))}</p><p>自然音声は{speakers}話者・{len(natural)}区間・計{fmt(seconds, 1)}秒です。人工信号は評価対象のデコーダーとは独立に生成しています。</p>
<p>MR-STFTは5・20・80 ms窓のスペクトル誤差です。表はケース中央値、差分は対応するケース同士の差の中央値です。自動時間整列・ゲイン正規化は行いません。—は欠測・未定義であり、ゼロ誤差ではありません。</p>
<p>F0は音高に対応する基本周波数、100 centは1半音、P95は誤差の95パーセンタイルです。有声の欠測と誤有声は別に示します。F0測定には固定2 kHz低域通過処理を含む独立YIN型測定器を使います。自然音声の絶対正解F0はありません。</p>
<p>WORLD（Harvest）はWORLDボコーダーにHarvestによるF0抽出を組み合わせた既存比較です。自作HNMは独自の解析・合成系です。原音は比較の参照であり、手法の順位には含めません。今回の測定だけで自然性、共鳴保持、多話者への一般化を保証しません。</p>
<p><a href="{repo}docs/EVALUATION.md">測定仕様</a> ／ <a href="{repo}docs/F0_CALIBRATION.md">音高測定器の校正</a> ／ <a href="{esc(review)}">5人の議論</a></p></details>
<details><summary>再合成の全ケースとF0欠測</summary>{all_table}</details>
<details><summary>操作の追従と欠測</summary><p>ゲイン・音高・時間長の変更を測定します。真値F0との誤差と、未操作出力からの相対変化推定は別の値です。全長一致は局所タイミングの保持を保証しません。帯域変化は未操作出力との差で、音高変更に伴う正常な変化も含む診断値です。</p>{operation_table}</details>
<details><summary>エンコーダーを通さない合成</summary><p>手作り特徴からの合成です。全値が有限でも、聴感品質の合格を示すものではありません。</p>{decoder_table}</details>
<details><summary>細部表現などの診断</summary>{diagnostic_table}<details><summary>診断の全値</summary><pre>{esc(json.dumps(data.get('diagnostics', []), ensure_ascii=False, indent=2))}</pre></details></details>
<details><summary>原音に対する音高測定器の校正</summary>{calibration_table}</details>
<details><summary>処理・測定の失敗記録（{len(failures)}件）</summary><p>処理失敗がなくても、F0欠測などの品質上の問題がないとは限りません。</p><pre>{esc(json.dumps(failures, ensure_ascii=False, indent=2))}</pre></details>
{iteration_section}
<details><summary>実行環境と再現情報</summary><pre>{esc(json.dumps(provenance, ensure_ascii=False, indent=2))}</pre></details>
<p><a href="results.json">全数値JSON</a> ／ <a href="audio_samples.json">保存音声と切り出し情報</a> ／ <a href="{repo}docs/WORKFLOW.md">進め方</a></p>
</main></html>'''
    path.write_text(content, encoding='utf-8')


def render(data, path):
    if data.get('schema_version', 1) >= 2:
        return _render_current(data, path)
    audit_link = ('<a href="metric_audit_results.json">測定器監査</a>'
                  if (Path(path).parent / "metric_audit_results.json").exists()
                  else "この出力先には測定器監査の記録はありません")
    repo = 'https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/'
    review_url = repo + 'docs/WORKFLOW.md'
    root = Path(__file__).resolve().parents[1]
    for parent in Path(path).resolve().parents:
        if (parent / 'experiment.json').is_file() and (parent / 'reviews/discussion.md').is_file():
            if parent.is_relative_to(root):
                review_url = repo + str((parent / 'reviews/discussion.md').relative_to(root))
            break
    ref = {r['case']:r for r in data['resynthesis'] if r['method']==data['comparison_reference']}
    rows, groups = [], defaultdict(list)
    for r in data['resynthesis']:
        m = r.get('measurement',{})
        metric = m.get('mr_stft_log_magnitude_mae_db')
        base_metric = ref.get(r['case'],{}).get('measurement',{}).get('mr_stft_log_magnitude_mae_db')
        delta = metric-base_metric if metric is not None and base_metric is not None else None
        pitch = m.get('pitch') or {}
        voiced = f"{pitch.get('valid_voiced_frames','—')} / {pitch.get('expected_voiced_frames','—')}"
        row = [input_label(r['case']),label(r['method'],METHODS),
               label(r['status'],STATUSES)+'／'+label(m.get('status','undefined'),STATUSES),
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
        deltas = [r['measurement']['mr_stft_log_magnitude_mae_db'] - ref[r['case']]['measurement']['mr_stft_log_magnitude_mae_db']
                  for r in records if r.get('measurement', {}).get('mr_stft_log_magnitude_mae_db') is not None
                  and ref.get(r['case'], {}).get('measurement', {}).get('mr_stft_log_magnitude_mae_db') is not None]
        failures=sum(r['status']!='measured' or r.get('measurement',{}).get('status')!='ok' for r in records)
        summaries.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [group,label(method,METHODS),len(records),len(vals),failures,
                  fmt(float(np.median(vals)) if vals else None),fmt(float(np.median(deltas)) if deltas else None)])+'</tr>')
    op_rows=[]
    for r in data['operations']:
        p=r.get('pitch_against_known_truth') or {}
        rel=r.get('relative_pitch') or {}
        op_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [input_label(r['case']),label(r['method'],METHODS),
                    label(r['operation'],OPERATIONS),label(r['status'],STATUSES),
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
    base_label='正式ベース手法は未選定' if base['method'] is None else f"正式ベース手法：{base['method']}"
    decoder_rows = []
    for item in data['decoder_only']:
        pitch = item.get('pitch') or {}
        values = ["無声指定（F0=0 Hz）" if item['f0_hz'] == 0 else f"音高 {item['f0_hz']:g} Hz 指定",
                  label(item['status'], STATUSES), item.get('output_samples', '—'),
                  {True: 'はい', False: 'いいえ'}.get(item.get('finite'), '未確認'),
                  fmt(pitch.get('abs_error_cents_p95')),
                  f"{pitch.get('valid_voiced_frames', '—')} / {pitch.get('expected_voiced_frames', '—')}",
                  pitch.get('false_voiced_frames', '—')]
        decoder_rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in values)+'</tr>')
    content=f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>非MLボコーダー 比較結果</title>
<style>
:root{{color-scheme:light dark;--ink:#172a3a;--muted:#506375;--line:#d8e2ea;--accent:#156d79;--bg:#f6f8fb;--surface:#fff;--head:#e7eef5;--link:#126d8a}}
body{{font:15px/1.75 system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0}}
main{{max-width:1450px;margin:auto;padding:36px 26px 70px}}h1{{font-size:30px;margin:0 0 12px}}h2{{font-size:22px;margin-top:38px}}
.tag{{letter-spacing:.12em;color:var(--accent);font-size:12px;font-weight:700}}.notice{{border-left:5px solid var(--accent);background:var(--surface);padding:18px 24px;margin:22px 0}}
p{{max-width:1000px}}table{{border-collapse:collapse;width:100%;font-size:13px;background:var(--surface)}}th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left;white-space:normal;min-width:18em;overflow-wrap:anywhere}}td:nth-child(2),td:nth-child(3){{white-space:normal;min-width:13em;overflow-wrap:anywhere}}th{{background:var(--head)}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:8px}}input{{background:var(--surface);color:var(--ink);padding:12px;border:1px solid #9fb2c3;border-radius:6px;width:min(500px,80%);margin:12px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:var(--surface);padding:16px}}a{{color:var(--link)}}small{{color:var(--muted)}}
.audio-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}audio{{width:100%}}input::placeholder{{color:var(--muted)}}a:focus-visible,input:focus-visible,audio:focus-visible{{outline:2px solid var(--accent);outline-offset:3px}}@media(prefers-color-scheme:dark){{:root{{--ink:#e6edf4;--muted:#b3c1d0;--line:#3b4b60;--accent:#68c8c6;--bg:#0f1724;--surface:#182438;--head:#23334a;--link:#7fdae8}}}}
</style><main><div class="tag">非MLボコーダー・再現可能な比較</div>
<h1>ベース手法と既存方式を比較する</h1>
<p>既存の非ML方式を同じ入力で動かし、測定の妥当性・失敗・再現性を確認した比較結果です。音質の最良や知覚的な透明性を認定する実験ではありません。</p>
<div class="notice"><strong>{esc(base_label)}</strong><br>{esc(base['reason'])}<br>各表のΔは <strong>{esc(data['comparison_reference'])}</strong> との差です。{("未選定時の表示基準であり、正式ベース手法との差ではありません。" if base["method"] is None else "その時点の正式ベース手法との差です。") }初代選定後もベース手法と版を記録して比較します。</div>
<h2>入力の種類ごとの要約</h2><p>同一条件の対応のある比較を基本にします。以下はケース中央値の診断値で、MOSでも品質順位でもありません。失敗件数を分母とともに残します。</p>
<div class="scroll"><table><thead><tr><th>群</th><th>方式</th><th>全ケース</th><th>有効スコア</th><th>処理・測定失敗</th><th>MR-STFT中央値 dB</th><th>比較相手との差分中央値 dB</th></tr></thead><tbody>{''.join(summaries)}</tbody></table></div>
{audio_section(Path(path).parent, base['method'])}
<h2>比較の役割</h2><ul><li>WORLD DIO + StoneMask と WORLD Harvest：同じCheapTrick・D4C・合成器に対する解析器の比較。</li><li>LLSM layer 0：WORLD DIOの同じF0を渡して別の解析合成表現を比較。音高の推定から合成まで独立した方式同士の比較ではありません。</li><li>原音コピー（identity）：測定器の検査だけに使う原音コピー。ボコーダーの候補や最良手法には数えません。</li></ul>
<h2>測定条件</h2><p>今回の自然音声はLibriSpeechの{natural_speakers}話者、{len(natural)}区間、合計{fmt(natural_seconds,1)}秒です（読み込めた固定先頭区間）。人工信号は加算合成、パルス列とIIR共鳴器、変調雑音、無音、インパルスで作り、評価対象デコーダーから生成していません。録音の新しい聴取評価は行っていません。</p>
<p>自動時間整列・動的時間伸縮・ゲイン正規化は行いません。MR-STFT（複数の窓長で測るスペクトル誤差）の窓長は5・20・80 msです。音高は独立YIN型測定器で既知F0に対して測定します。自然音声のF0の絶対正解はありません。—は未定義・対象外でありゼロ誤差ではありません。</p>
<p>F0診断だけに固定2 kHz・6次のバターワースフィルタによる前向き・後向き処理と、最大80 msの偶対称反射（端点の波形を鏡写しに延長する処理）を適用します。2 kHz以下に十分な周期成分が必要で、自然音声全般の精度は未校正です。STFT・帯域・レベル測定はこの前処理を使いません。<a href="https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/F0_CALIBRATION.md">78ケースの校正と追加反例</a>も確認してください。</p>
<h2>測定器の校正</h2><p>入力信号をそのまま測定した音高誤差P95のケース最大値: <strong>{fmt(max_cal)} cent</strong>。既知有声の欠測: {cal_missing}フレーム、既知無声の誤有声: {cal_false}フレーム。境界を跨ぐフレームは別計数です。詳細と欠測分母は <a href="results.json">results.json</a> に保存しています。</p>
<p>別途、原音コピー、既知の音量変更、10 msの時間ずらし、高域の除去、末尾の切り落とし、非数（NaN）、無限大（Inf）、直流成分（DC）、無音化による独立監査を行います。その記録は {audit_link}。</p>
<h2>表の読み方</h2><ul><li>F0は基本周波数で、周期的な音の高さに対応します。cent（セント）は音程差の単位で、100 centが1半音です。</li><li>P95は誤差の95パーセンタイルです。測定できたフレームの95％がこの値以下ですが、欠測は別に確認します。</li><li>Δは「対象の誤差 − 比較相手の誤差」です。負ならこの指標の誤差が比較相手より小さく、正なら大きいことを表します。音質全体の順位ではありません。</li><li>RMS差は実効値で測るレベル差です。正は原音より大きく、負は小さいことを表し、0 dBに近いほどレベルが一致します。</li><li>フレームは測定用に切り出す短い区間、サンプルは波形の1点です。有声の欠測は本来ある周期を測れなかった区間、誤有声は本来無声の区間を有声と判定したものです。</li><li>—は未定義・対象外です。計算の完了や欠測の少なさだけで、聴感上の良さを保証しません。</li></ul>
<h2>無加工再合成の全ケース</h2><p>「処理完了／測定完了（measured / ok）」は計算できたという状態です。無音化、音高欠測、レベル誤差などを含め、品質合格を意味しません。STFT・帯域差・cent誤差は小さいほど原音に近い診断値です。</p><input id="filter" aria-label="ケースまたは方式で絞り込み" placeholder="ケースまたは方式で絞り込み">
<div class="scroll"><table id="cases"><thead><tr>{''.join('<th>'+v+'</th>' for v in ['入力','比較対象','状態','MR-STFT dB','Δ対'+ref_label+' dB','帯域差 dB','RMS差 dB','F0 P95 cent','測定できた／真値の有声フレーム','誤有声（フレーム）','長さ差（サンプル）','再実行最大差'])}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>操作試験</h2><p>未操作の同方式出力からの変化を測ります。既知F0への絶対誤差と、出力間の相対変化推定を区別します。時間操作の全長一致だけでは局所イベントや末尾の保持を保証しません。LLSMの操作は今回未実装であり、合格に数えません。</p>
<div class="scroll"><table><thead><tr>{''.join('<th>'+v+'</th>' for v in ['入力','方式','操作','状態','音量追従誤差 dB','真値F0 P95 cent','相対F0 P95 cent','相対比較できた／全フレーム','真値と比較できた／有声フレーム','真値に対する欠測（フレーム）','真値に対する誤有声（フレーム）','長さ誤差（サンプル）','イベント誤差ms'])}</tr></thead><tbody>{''.join(op_rows)}</tbody></table></div>
<h2>デコーダー単体と失敗記録</h2><p>エンコーダーを通さず、手作りの特徴量から合成した結果です。「全値が有限」は非数や無限大がないことだけを示します。無声指定では音高誤差は定義しません。</p>
<div class="scroll"><table><thead><tr><th>指定</th><th>状態</th><th>出力サンプル数</th><th>全値が有限</th><th>音高誤差 P95 cent</th><th>測定できた／真値の有声フレーム</th><th>誤有声フレーム</th></tr></thead><tbody>{''.join(decoder_rows)}</tbody></table></div>
<p>以下の再合成の失敗記録は、処理できなかった、または測定状態が正常完了でなかった行です。0件でも音高欠測などの品質上の問題がないとは限りません。</p><details><summary>手作り特徴からの合成結果</summary><pre>{esc(json.dumps(data['decoder_only'],ensure_ascii=False,indent=2))}</pre></details><details><summary>再合成の処理・測定失敗 {len(failure_details)} 件</summary><pre>{esc(json.dumps(failure_details,ensure_ascii=False,indent=2))}</pre></details>
<h2>今回判断できないこと</h2><p>多話者・多言語・日本語・歌唱・ささやきへの一般化、話者類似度・表現距離の知覚的妥当性、息っぽさ等の知覚制御、動的・複合操作、長時間連続処理、未使用の最終評価データでの優位は未確認です。48 kHzの人工信号が動いても、48 kHz自然音声の品質確認にはなりません。外部MOS予測器、ViSQOL、eSTOIは今回計測していません。</p>
<h2>再現情報</h2><p>使用したPythonと数値計算ライブラリの版、実行時の親commit、自然音声の取得状態を記録しています。JSONの英語キーと識別子は、元データとの照合や自動処理のために保持しています。</p><p><a href="results.json">全数値JSON</a> ／ <a href="https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/EVALUATION.md">測定仕様</a> ／ <a href="https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/WORKFLOW.md">進め方</a> ／ <a href="{esc(review_url)}">5人の議論</a></p><pre>{esc(json.dumps({'environment':data['environment'],'parent_commit':data['parent_commit'],'data_status':data['data_status']},ensure_ascii=False,indent=2))}</pre>
<p><small>ユーザー指示の正本はリポジトリのUSER_INSTRUCTIONS.mdです。この結果と解釈はAI作成物です。</small></p></main>
<script>document.getElementById('filter').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('#cases tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));}});</script></html>'''
    Path(path).write_text(content,encoding='utf-8')
