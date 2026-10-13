"""追加品質・制御評価の日本語本番HTML。比較を先頭に置き、目的の異なる指標を統合しない。"""
from __future__ import annotations

import html

from added_metrics_report_data import CONDITION_LABELS, LABELS, METHODS

CSS = """
:root{color-scheme:light dark;--bg:#f4f7f8;--card:#fff;--ink:#18303a;--muted:#526771;--line:#cfdde2;--accent:#076a72;--warn:#825214}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 system-ui,sans-serif}
main{max-width:1240px;margin:auto;padding:30px 24px 64px}h1{font-size:clamp(25px,4vw,38px);line-height:1.4}h2{font-size:24px;margin:0 0 14px}
h3{font-size:19px}section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;margin:24px 0}
a{color:var(--accent);overflow-wrap:anywhere}.lead,.notice{border-left:4px solid var(--accent);padding:12px 18px;background:var(--bg)}
.warning{border-color:var(--warn)}small,.muted{color:var(--muted)}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}th:first-child,td:first-child{text-align:left}
th{white-space:nowrap}.coverage td:last-child{text-align:left;min-width:330px}.coverage td:first-child{min-width:175px}
.audio-grid,.curves{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.audio-card,.curve{border:1px solid var(--line);padding:14px;border-radius:10px}
audio{width:100%;height:38px}.audio-card p{margin:0 0 8px}.stat{font-variant-numeric:tabular-nums}.note{max-width:92ch}code{overflow-wrap:anywhere}
summary{cursor:pointer;font-weight:650}details{margin:14px 0}svg{width:100%;height:auto}svg text{fill:var(--ink);font:12px system-ui,sans-serif}.axis{stroke:var(--line);stroke-width:1}.hnm{stroke:#078e9c}.world{stroke:#cc743b}footer{color:var(--muted);font-size:14px}
@media(prefers-color-scheme:dark){:root{--bg:#101a25;--card:#172634;--ink:#e0edf0;--muted:#acbec8;--line:#3a4e5c;--accent:#77d4df;--warn:#efb963}}
@media(max-width:600px){main{padding:20px 12px 44px}section{padding:16px}th,td{padding:9px 8px}.audio-grid,.curves{grid-template-columns:1fr}}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value, digits=4, signed=False):
    if value is None:
        return "未測定"
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def table(headers, rows, css=""):
    return ('<div class="scroll"><table class="' + css + '"><thead><tr>'
            + "".join(f"<th>{esc(x)}</th>" for x in headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
            + "</tbody></table></div>")


def cell(group, factor=1, signed=False):
    value = group.get("speaker_macro_mean")
    number = fmt(value * factor if value is not None else None, signed=signed)
    return number + (f'<br><small>{group["valid_cases"]}/{group["planned_cases"]}発話・'
                     f'{group["valid_speakers"]}/{group["planned_speakers"]}話者</small>' if group else "")


def paired(group, factor=1):
    value = group.get("speaker_macro_mean")
    return fmt(value * factor if value is not None else None, signed=True) + (
        f'<br><small>{group["paired_cases"]}/{group["planned_cases"]}対・'
        f'{group["paired_speakers"]}/{group["planned_speakers"]}話者</small>' if group else "")


def comparison(data):
    rows = []
    for item in data["comparison_summary"]:
        rows.append([esc(item["label"]), *[cell(item["methods"].get(m, {})) for m in METHODS],
                     paired(item.get("paired_world_harvest_minus_hnm", {}))])
    body = table(["無編集の指標", LABELS["hnm"], LABELS["world_harvest"], "対応差 WORLD−HNM"], rows)
    original = next(x for x in data["quality_summary"] if x["metric"] == "mos" and x["condition"] == "unedited")
    body += ('<p>原音の予測MOS（同条件の歴史値）：' + cell(original["methods"]["identity"]) + '</p>'
        '<p class="note">表は話者内の有効発話平均を40話者で等重みにした記述値。対応差は同一発話のWORLD−HNMを先に計算します。'
        '小数点以下の差は有意差や知覚差の証明ではありません。総合順位と方式採用は決めません。'
        'ERB 20 msと局所ERB 40 msは関連する別定義の診断で、独立した2票には数えません。'
        '局所P95は40 msの発話内フレームRMSEのP95を話者単位で平均した診断で、指標数の加算には使いません。'
        '実NPZ量は圧縮容器・ヘッダー・メタデータを含む1設定です。</p>'
        '<p><a href="quality-speaker-summary.json">全品質値・40話者・対応差</a> ／ '
        '<a href="assessment-speaker-summary.json">制御・局所誤差・表現量の40話者集計</a> ／ '
        '<a href="results.json">今回の総括JSON</a></p>')
    return '<section id="comparison"><h2>現ベースとWORLDの追加指標比較</h2>' + body + '</section>'


def history(data):
    rows = []
    historical = data["historical_reference"]
    for method, item in historical["summary"].items():
        metrics = item["metrics"]
        rows.append([esc(historical["method_labels"][method]), *[fmt(metrics[k]["mean"]) for k in ("mos", "estoi", "stft")],
                     str(metrics["mos"]["valid"]) + "/120", "今回対象" if method in METHODS else "今回の追加指標は未測定"])
    return ('<section><h2>過去8方式の歴史的参考値</h2>'
            f'<p>2026年10月13日の固定120録音の保存結果。記録日時：{esc(historical["generated_at"])}。'
            '以下は当時の発話等重み平均です。今回の新規測定や上表の話者等重みと混同しません。'
            '当時のMOSは各方式のネイティブ全長、eSTOI・STFTは方式ごとの16 kHz共通先頭区間です。</p>'
            + table(["方式", "予測MOS ↑", "eSTOI ↑", "STFT誤差 dB ↓", "MOS有効", "今回の追加測定"], rows)
            + '<p><a href="historical-summary.json">当時の集計・欠測・比較区間</a> ／ '
            f'<a href="{esc(historical["source_json_link"])}">当時の全記録（既存公開JSON）</a></p></section>')


def audio_section(audio):
    body = '<p class="notice warning">+6 dBの例は音量が大きくなります。再生機器の音量を低くしてから聴いてください。'
    body += esc(audio["selection_note"]) + '</p>'
    for case in audio["public_audio_example_ids"]:
        body += '<h3>' + esc(case) + '</h3><div class="audio-grid">'
        for sample in audio["samples"]:
            if sample["case"] != case:
                continue
            label = sample["display_label"]
            warning = ('<p class="notice warning">フルスケール超。再生環境で歪む可能性があります</p>'
                       if sample["peak_amplitude"] > 1 else '')
            body += ('<div class="audio-card"><p>' + esc(label) + '</p><audio controls preload="none" aria-label="'
                     + esc(label + " " + case) + '" src="' + esc(sample["data_uri"]) + '"></audio>'
                     + f'<small>{sample["n_samples"] / sample["sample_rate"]:.2f}秒・ピーク{sample["peak_amplitude"]:.3f}</small>'
                     + warning + '</div>')
        body += '</div>'
    return ('<section><h2>固定2録音の短い音声比較</h2>' + body + '<p>' + esc(audio["attribution"])
            + '<br><a href="https://www.openslr.org/12/">配布元</a> ／ '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> ／ '
            '<a href="audio_samples.json">抜粋のhashと形式</a></p></section>')


def assessment_table(groups, metric, scalars):
    rows = []
    for item in groups:
        if item["metric"] != metric or item["scalar"] not in scalars:
            continue
        rows.append([esc(CONDITION_LABELS.get(item["condition"], item["condition"])) + "<br>" + esc(scalars[item["scalar"]]),
                     *[cell(item["methods"][m]) for m in METHODS], paired(item["paired_world_harvest_minus_hnm"])])
    return table(["条件／指標", LABELS["hnm"], LABELS["world_harvest"], "対応差 WORLD−HNM"], rows)


def pitch_accounting(groups):
    rows = []
    for condition in ("pitch_minus3", "pitch_plus3"):
        values = {g["scalar"]: g for g in groups if g["metric"] == "pitch_tracking" and g["condition"] == condition}
        for method in METHODS:
            def total(name):
                value = values.get(name, {}).get("methods", {}).get(method, {}).get("sum_over_available_cases")
                return str(int(value)) if value is not None else "未測定"
            rows.append([esc(CONDITION_LABELS[condition] + "・" + LABELS[method]),
                total("relative_error.count"), total("expected_voiced_frames"), total("missing_voiced_frames"),
                total("false_voiced_frames"), total("expected_unvoiced_frames"), total("out_of_range_frames"), total("total_frames")])
    return table(["音高操作／方式", "誤差の有効フレーム", "参照YIN推定有声", "出力YIN未検出", "出力のみYIN有声", "参照YIN推定無声", "探索範囲外", "全フレーム"], rows)


def controls(data):
    groups = data["assessment_summary"]["groups"]
    body = '<h3>音高追従：±3半音</h3>' + assessment_table(groups, "pitch_tracking", {"value": "絶対誤差平均 cent", "relative_error.abs_p95": "発話内P95の平均 cent"})
    body += ('<p>cent誤差は両側でF0が推定できたフレームに条件付きです。出力のYIN未検出はF0を測定できない状態であり、'
             '真の発声消失を意味しません。0誤差にはせず、推定上の有声／無声と測定不能フレームを併記します。</p>'
             + pitch_accounting(groups))
    body += '<h3>音量追従：±6 dB</h3>' + assessment_table(groups, "gain_tracking", {"value": "絶対誤差平均 dB", "errors.abs_p95": "発話内P95の平均 dB", "output_peak": "出力ピーク", "over_one_fraction": "振幅1超の比率"})
    headroom = []
    for item in data["playback_headroom"]["groups"]:
        fraction = item["maximum_over_one_fraction"]
        headroom.append([esc(CONDITION_LABELS[item["condition"]] + "・" + LABELS[item["method"]]),
                         f'{item["over_one_cases"]}/{item["planned_cases"]}（有効{item["measured_cases"]}）',
                         fmt(item["maximum_peak"]), fmt(fraction * 100 if fraction is not None else None, 3)])
    body += '<h3>全長出力の再生余裕</h3>' + table(["操作／方式", "振幅1超の録音／予定", "全録音の最大ピーク", "最大の振幅1超サンプル率 %"], headroom)
    body += ('<p class="notice warning">合成波形は浮動小数点で保存し、クリッピングや音量正規化をしていません。'
             'ゲイン追従誤差が小さくても、振幅1超の出力は再生・整数化で歪む可能性があります。'
             '安全に再生できる編集幅を示す結果ではありません。全長の結果と先頭2秒の音声例は別の範囲です。</p>')
    body += '<p>制御の参照は各方式の無編集復号音。ピッチは自然音声の独立F0正解に対する精度ではありません。'
    body += 'YIN推定上の測定不能・有声／無声の不一致・範囲外・オクターブ・無音件数は<a href="assessment-speaker-summary.json">全診断集計</a>に残します。</p>'
    body += '<h3>ゲイン操作だけの干渉</h3>' + assessment_table(groups, "interference", {
        "gain.pitch_cents.response": "音高応答 cent/dB", "gain.level_db.response": "音量応答 dB/dB（期待1）",
        "gain.slope_db_per_octave.response": "傾斜応答 (dB/oct)/dB", "gain.duration_seconds.response": "時間長応答 s/dB"})
    body += '<p>±6 dBの中央差分。理想一様ゲインの期待応答は音量1、音高・傾斜・時間0。知覚的独立性の正解ではありません。'
    body += 'ピッチ操作の非対角期待応答は未校正です。定常一様振幅演算の整合性であり、知覚音量や動的制御全般の証明ではありません。</p>'
    return '<section><h2>自然音声の限定された制御測定</h2>' + body + '</section>'


def curve_plot(points, title, unit):
    values = [p[m] for p in points for m in METHODS if p[m] is not None]
    if not values:
        return '<p>有効な品質点がありません。</p>'
    low, high = min(values), max(values)
    pad = max((high - low) * .15, .01)
    low, high = low - pad, high + pad
    def x(i):
        return 55 + i * 125

    def y(v):
        return 170 - (v - low) / (high - low) * 130
    parts = [f'<div class="curve"><h3>{esc(title)}</h3><svg role="img" aria-label="{esc(title)}" viewBox="0 0 365 218">',
             '<line class="axis" x1="55" y1="40" x2="55" y2="170"/><line class="axis" x1="55" y1="170" x2="305" y2="170"/>']
    for v in (low, (low + high) / 2, high):
        parts.append(f'<text x="48" y="{y(v) + 4:.1f}" text-anchor="end">{v:.3f}</text>')
    for i, point in enumerate(points):
        parts.append(f'<text x="{x(i)}" y="190" text-anchor="middle">{esc(point["amount"])} {esc(unit)}</text>')
    for method, css in zip(METHODS, ("hnm", "world"), strict=True):
        present = [(i, p[method]) for i, p in enumerate(points) if p[method] is not None]
        if len(present) == len(points):
            coordinates = " ".join(f"{x(i)},{y(value):.2f}" for i, value in present)
            parts.append(f'<polyline class="{css}" fill="none" stroke-width="2.5" points="{coordinates}"/>')
        for i, value in present:
            parts.append(f'<circle class="{css}" fill="var(--card)" stroke-width="2.5" cx="{x(i)}" cy="{y(value):.2f}" r="4"/>')
    parts.append('</svg><small>青緑：HNM v3／橙：WORLD。線は測定3点を結ぶだけで、中間値の推定ではありません。</small></div>')
    return ''.join(parts)


def quality_curves(data):
    groups = data["quality_summary"]
    indexed = {(g["metric"], g["condition"]): g for g in groups}
    charts, rows = [], []
    for control, unit, settings in (("音高", "cent", [(-300, "pitch_minus3"), (0, "unedited"), (300, "pitch_plus3")]),
                                    ("音量", "dB", [(-6, "gain_minus6"), (0, "unedited"), (6, "gain_plus6")])):
        for metric, label in (("mos", "予測MOS"), ("speaker_ecapa", "固定原音ECAPA")):
            points = []
            for amount, condition in settings:
                group = indexed[(metric, condition)]
                points.append({"amount": amount, **{m: group["methods"][m]["speaker_macro_mean"] for m in METHODS}})
                rows.append([esc(f"{control} {amount:+} {unit}・{label}"), *[cell(group["methods"][m]) for m in METHODS],
                             paired(group["paired_world_harvest_minus_hnm"])])
            charts.append(curve_plot(points, control + "操作 × " + label, unit))
    return ('<section><h2>編集量別の品質：2つの軸を分ける</h2><p>非参照UTMOSv2と固定原音に対するECAPAを別々に表示します。'
            '意図した編集を原音へのERB/SCOREQ距離で罰しません。3点だけから使用可能な編集幅や連続応答を決めません。'
            'ゲインによる予測MOS変化は、音量を上げれば人間が自然と感じるという根拠ではありません。'
            'UTMOSv2は保存した浮動小数点波形への予測であり、再生機器でのクリッピングを反映したMOSではありません。</p>'
            '<div class="curves">' + ''.join(charts) + '</div>' + table(["操作・品質軸", LABELS["hnm"], LABELS["world_harvest"], "対応差 WORLD−HNM"], rows)
            + '<p>同一発話の無編集点との差は<a href="assessment-speaker-summary.json">曲線集計JSON</a>へ。'
            '絶対値と差分、品質指標間の単位を混ぜません。</p></section>')


def asr_section(asr):
    rows = []
    for metric in ("cer", "wer"):
        for aggregation, label in (("speaker_macro", "話者等重み"), ("utterance_macro", "発話等重み"), ("micro", "全文字／全語重み")):
            values = []
            for method in METHODS:
                stats = asr["methods"][method]["reference_usable"]["overall"][metric][aggregation]
                fields = [stats[k] if aggregation == "micro" else stats[k]["mean"] for k in ("reference_rate", "output_rate", "delta")]
                values.extend([fmt(fields[0] * 100 if fields[0] is not None else None, 3),
                               fmt(fields[1] * 100 if fields[1] is not None else None, 3),
                               fmt(fields[2] * 100 if fields[2] is not None else None, 3, True)])
            rows.append([esc(metric.upper() + "・" + label), *values])
    valid = asr["methods"]["hnm"]["reference_usable"]["overall"]
    body = (f'<p>全文正解を使える55/120録音・32話者の補助評価。原音CER≤20%を満たす'
            f'{valid["case_count"]}/55録音・{valid["speaker_count"]}話者で下表を集計。'
            f'上限超過は{len(asr["quality_gate"]["excluded_cases"])}録音。超過分も生値を保存します。</p>')
    body += table(["誤り率／重み", "HNM 原音%", "HNM 出力%", "HNM 増分pt", "WORLD 原音%", "WORLD 出力%", "WORLD 増分pt"], rows)
    body += '<p>重みで小差の順序が変わり得ます。単一認識器と短い全文発話の結果を、自然さ・全120録音・一般的優越へ読み替えません。'
    body += '元ASRを正解にはせず公式転記を使用。<a href="asr-summary.json">話者別・対応差・全生値側の集計</a>を参照してください。</p>'
    return '<section><h2>ASRによる内容保持の補助評価</h2>' + body + '</section>'


def evidence_section(data):
    timing = data["timing_summary"]
    quality_names = "SCOREQ／ECAPA／ERB" if data["scoreq_status"]["evaluation_attempted"] else "ECAPA／ERB"
    text = (f'<p>MOS：新規推論{timing["mos"]["origins"].get("new_inference", 0)}行、'
            f'歴史値再利用{timing["mos"]["reused_rows"]}行。新規推論の記録時間合計は'
            f'{timing["mos"]["new_inference_recorded_seconds"]:.1f}秒。再利用値に付属する過去の秒数は今回へ加算しません。</p>'
            f'<p>UTMOSv2はfold 0・seed 20261012・抽出1回。{quality_names}／assessmentは初回＋1反復。'
            '反復を独立録音数には数えません。各工程は同時実行した区間があり、CPU競合と分割ごとの初期化を含みます。'
            '4スレッド（ASRは2）の秒数は厳密な速度順位ではなく、工程時間の和を実経過時間と扱いません。</p>')
    links = [("provenance-index.json", "全保存物の索引・変換前後hash・アーカイブ所在"),
             ("execution-summary.json", "新規時間・再利用・初期化・処理状態"),
             ("execution-logs.json", "全実行ログ・警告・失敗スタック（パス秘匿済み）"),
             ("assessment-speaker-summary.json", "40話者の制御・局所誤差・対応差"),
             ("quality-speaker-summary.json", "40話者のMOS・ECAPA・ERBと対応差"),
             ("dataset-manifest.json", "固定120録音・40話者・音声出典"),
             ("asr-summary.json", "ASRの32話者と原音上限"), ("serialized-size.json", "実NPZ保存量"),
             ("scoreq-status.json", "SCOREQ全240予定の実測値・欠測理由")]
    for item in data["evidence_links"]:
        links.append((item["path"], item["label"]))
    text += '<ul>' + ''.join(f'<li><a href="{esc(path)}">{esc(label)}</a></li>' for path, label in links) + '</ul>'
    text += '<p>各生結果JSONには入力hash、モデル・実装・依存環境、初回／反復値、欠測理由を保持。'
    text += '圧縮証跡はGit保存のみでPages非公開。全長音声・重みは非公開で、JSON内の相対音声パスはデータ参照です。</p>'
    return '<section><h2>再現条件・失敗・再開・保存証跡</h2>' + text + '</section>'


def render(data, audio):
    coverage_rows = [[esc(f'{r["number"]}. {r["label"]}'), esc(r["status"]),
                     (str(r["measured"]) + "/" + str(r["planned"])) if r["measured"] is not None and r["planned"] is not None else "—",
                     esc(r["reason"])] for r in data["coverage"]]
    body = '<h1>固定自然音声の追加品質・制御指標</h1>' + comparison(data)
    body += '<p class="lead">16 kHz英語・固定120録音40話者の開発集合。HNM v3とWORLDの無編集240＋操作960出力。'
    body += '48 kHz原収録実績、独立最終評価、人間による校正はありません。</p>'
    body += history(data) + audio_section(audio) + controls(data) + quality_curves(data) + asr_section(data["asr_summary"])
    body += '<section><h2>18項目の測定範囲と不足</h2><p>件数は各項目の単位であり、足し合わせた総合被覆率は作りません。'
    body += '「部分」は入力や操作範囲が限定されている項目を含みます。</p>'
    body += table(["項目", "到達点", "有効／予定", "今回の範囲・未測定の理由"], coverage_rows, "coverage") + '</section>'
    body += evidence_section(data)
    body += '<footer>本レポートはAI作成。記録：' + esc(data["generated_at"]) + '。静的解析と音質評価は別です。'
    body += '本レポート保存でテスト・自己検査・再decode・Pages生成予行は実施していません。</footer>'
    return '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + '<title>固定自然音声の追加品質・制御指標</title><style>' + CSS + '</style></head><body><main>' + body + '</main></body></html>'
