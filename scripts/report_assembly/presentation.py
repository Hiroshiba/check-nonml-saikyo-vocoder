"""日本語light/dark表示。保存値を整形するだけで並べ替え・順位算出はしない。"""

from hashlib import sha256
from html import escape

from common import FEATURE_AXES, VIEWS

NAMES = {"pml": "現ベース PML", "world_harvest": "WORLD Harvest", "candidate": "候補 aHM＋Cartesian編集",
         "ahm_cartesian_node_editor_v1": "候補 aHM＋Cartesian編集", "original": "原音（参考）"}
CONDITIONS = {"native": "無編集", "pitch_minus3": "−3半音", "pitch_plus3": "＋3半音", "case": "録音単位",
              "within_speaker": "同一話者", "across_speaker": "話者間"}
TARGET_NAMES = {"log_f0": "対数F0", "rms_dbfs": "音量 RMS dBFS", "spectral_slope": "スペクトル傾斜"}
VIEW_NAMES = dict(zip(VIEWS, ("主観測：位相基準を統一", "補助観測：振幅", "診断観測：元の複素表現"), strict=True))
VIEW_NAMES["pml2110"] = "PML表現"
ESTIMANDS = {"flat_stratum": "層の等重み平均", "x_speaker_macro": "X話者の等重み平均",
             "nested_phone_context": "音素・文脈の入れ子平均"}
REASONS = {"none": "欠測なし", "generation_failed": "生成失敗", "metric_failed": "指標計算失敗",
           "model_initialization_failed": "測定器初期化失敗", "unsupported_operation": "操作未対応",
           "outside_scope": "対象範囲外", "full_transcript_unavailable": "全文転記なし",
           "reference_cer_gate_exceeded": "参照CERの条件超過", "insufficient_voiced_support": "有声区間不足",
           "no_low_energy_segment": "低エネルギー区間なし", "length_mismatch": "長さ不一致",
           "output_shorter_than_fixed_window": "固定窓より短い出力", "invalid_f0": "F0無効",
           "diagnostic_failed": "診断失敗", "other_classified_failure": "その他の分類済み失敗",
           "feature_observation_failed": "特徴観測失敗", "payload_not_available": "特徴入力なし",
           "insufficient_train_targets": "学習用正解値不足"}
CATEGORIES = {"analysis": "解析", "decode": "復号", "edit": "編集", "io": "読み書き",
    "analysis_components_with_instrumentation": "計測器を含む解析要素（AIR・最終fit）",
    "initial_f0_components": "初期F0解析の各要素", "initial_f0_io": "初期F0の読み書き",
    "pipeline_observation_not_codec_speed": "処理工程の観測値（codec速度ではない）",
    "native_intermediate_payload": "無編集の中間payload", "complete_formal_payload": "完全な正式payload",
    "complete_edited_payload": "編集済み正式payload", "payload_preparation_with_io": "読み書きを含むpayload準備",
    "decode_with_profile": "profileを含む復号", "reference_diagnostic": "q1測定の参照用診断",
    "parameter_diagnostic_not_formal_edit": "パラメータ診断（正式編集時間ではない）",
    "unclassified_observation": "分類未確定の保存観測"}
STYLE = """
:root{color-scheme:light dark;--bg:#f8fafc;--fg:#182335;--panel:#fff;--line:#c5cdd8;--link:#174ba3}
@media(prefers-color-scheme:dark){:root{--bg:#111827;--fg:#edf2f8;--panel:#1c2638;--line:#536278;--link:#a5c9ff}}
body{font:16px/1.7 system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:1240px;margin:24px auto;padding:0 20px}
a{color:var(--link)}h1{font-size:1.7rem}h2{margin-top:2.3rem}h3{font-size:1.12rem}small{overflow-wrap:anywhere}
section,.note{padding:16px;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:16px 0}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:8px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
td{min-width:80px}details{margin:14px 0}summary{cursor:pointer}nav ul{columns:2;column-width:280px}section{scroll-margin-top:12px}
.rank{display:inline-block;border:3px solid currentColor;border-radius:7px;padding:1px 9px;font-weight:bold;white-space:nowrap}
.r1{color:#332700;background:#f6cd4b}.r2{color:#243044;background:#d0d8e3}.r3{color:#35200e;background:#dbaf88}
.missing{font-weight:bold}code{overflow-wrap:anywhere}audio{max-width:100%}
"""


def esc(value):
    return escape(str(value), quote=True)


def number(value):
    return "—" if value is None else f"{value:.6g}"


def ci(value):
    return "区間なし" if value is None else f"[{number(value[0])}, {number(value[1])}]"


def support(value):
    return "保存なし" if value is None else str(value)


def saved_number(value):
    return "保存なし" if value is None else number(value)


def anchor(axis):
    return "axis-" + sha256((axis["id"] + "\0" + axis["condition"]).encode()).hexdigest()[:20]


def table(headers, rows):
    head = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def reasons(counts):
    return "、".join(f"{esc(REASONS.get(key, '分類済み理由'))}：{count}件 <small>({esc(key)})</small>"
                    for key, count in counts.items()) or "理由件数の保存なし"


def ordinary(axis, label):
    rows = []
    common = axis["common_support"]
    for method in ("pml", "ahm_cartesian_node_editor_v1", "world_harvest", "original"):
        if method not in axis["methods"]:
            continue
        row = (axis["own_support_unranked"][method] if method == "original" else common["methods"].get(method))
        rank = row["rank"] if row is not None else None
        badge = "順位なし" if rank is None else f'<strong class="rank r{rank}">{rank}位</strong>'
        delta = "比較対象外"
        pair = axis["pairwise_pml"].get(method)
        if pair is not None:
            value = pair["methods"][method]["pml_difference"]
            delta = f'{number(value["value"])} {ci(value["ci95"])}<br>{pair["common_valid_recordings"]}/120録音・{pair["common_valid_speakers"]}/40話者'
        state = axis["method_states"][method]
        rows.append([esc(NAMES[method]), badge, number(row["value"]) if row else "比較対象外",
                     ci(row["ci95"]) if row else "—", f'{state["measured_recordings"]}/120', delta])
    direction = {"higher": "大きいほど良い", "lower": "小さいほど良い", "diagnostic": "診断値・順位なし"}[axis["direction"]]
    result = f'<section id="{anchor(axis)}"><h3>{esc(label["label"])} <small>{esc(label["unit"])}</small></h3>'
    result += f'<p>{CONDITIONS[axis["condition"]]}／{direction}。主比較の共通支持：{common["common_valid_recordings"]}/120録音・{common["common_valid_speakers"]}/40話者。</p>'
    result += table(["方式", "保存順位", "共通支持の値（原音は単独支持）", "95%区間", "成功／予定録音", "現PMLとの差・対応支持"], rows)
    result += '<details><summary>欠測理由・単独支持の参考値</summary><ul>'
    for method in axis["methods"]:
        own = axis["own_support_unranked"][method]
        result += f'<li>{esc(NAMES[method])}：{number(own["value"])} {ci(own["ci95"])}、{own["valid_recordings"]}/120録音・{own["valid_speakers"]}/40話者。{reasons(axis["method_states"][method]["reason_counts"])}</li>'
    if axis["structurally_unsupported_methods"]:
        result += '<li>全120件で操作未対応のため共通比較から除外：' + '、'.join(esc(NAMES[m]) for m in axis["structurally_unsupported_methods"]) + '</li>'
    return result + '</ul></details></section>'


def features(appendix):
    result = '<h2 id="features">特徴空間ABX・固定読み出し</h2><p>独立train120録音・40話者、test120録音・別40話者。ABX予定4960三つ組。候補3viewは同じ候補の主観測・補助・診断であり、3方式・3票ではありません。特徴順位はすべて未付与です。</p>'
    for item in appendix["paired"]:
        rows = []
        for axis in FEATURE_AXES:
            row = item["values"].get(axis)
            if axis.startswith("abx/"):
                _, condition, estimand = axis.split("/")
                title = f'ABX {CONDITIONS[condition]}・{ESTIMANDS[estimand]}'
                saved = item["abx_by_condition"][condition]["point_support"]
                denominator = f'条件別予定：保存なし。全体 {item["support"]["abx"]["paired_measured"]}/4960三つ組'
                if saved is not None:
                    denominator += f'<br>条件内 {saved["triplets"]}三つ組・{saved["speakers"]}話者・X {saved["x_speakers"]}話者・{saved["strata"]}層'
            else:
                title = '読み出し ' + TARGET_NAMES[axis.split("/")[1]]
                saved = item["support"][axis]
                denominator = f'{saved["paired_measured"]}/120録音・{saved["speaker_count"]}/40話者'
            rows.append([title, number(row["candidate"]) if row else "保存なし",
                         number(row["pml"]) if row else "保存なし",
                         f'{number(row["candidate_minus_pml"])} {ci(row["delta_ci95"])}' if row else "保存なし",
                         denominator, "未付与"])
        result += f'<section><h3>{VIEW_NAMES[item["view"]]}</h3><p>同じ測定支持上の候補−新たに尺度調整した現PML。値は小さいほど良い。</p>'
        result += table(["軸", "候補", "現PML", "対応差・95%区間", "対応支持", "順位"], rows)
        result += '<p>' + '／'.join(f'{CONDITIONS[key]}の保存bootstrap反復：{support(row["drawn_replicates"])}'
                                  for key, row in item["abx_by_condition"].items()) + '</p></section>'
    result += '<h3>単独支持の読み出し・定数train平均基準・次元診断</h3><p>以下の基準値は各方式の単独支持です。上の対応支持と同一とは限らず、差や順位を新規計算していません。行列rankは数値行列の階数であり、性能順位ではありません。</p>'
    rows = []
    for item in appendix["readout_own_support"]:
        for row in item["targets"]:
            d = row["diagnostics"] or {}
            rows.append([f'{NAMES[item["method"]]}<br>{VIEW_NAMES[item["view"]]}', TARGET_NAMES[row["target"]],
                         f'{number(row["speaker_macro_mae"])} {ci(row["ci95"])}',
                         saved_number(row["constant_train_mean_speaker_macro_mae"]),
                         f'{support(row["recordings"])}/120録音・{support(row["speakers"])}/40話者',
                         f'有効train {support(d.get("valid_train"))}/120<br>次元 {support(d.get("dimensions"))}・定数次元 {support(d.get("constant_dimensions"))}<br>行列rank {support(d.get("matrix_rank"))}<br>定数予測値 {saved_number(d.get("constant_prediction"))}',
                         esc(REASONS.get(row["reason_code"], "理由件数は終端summaryに保存なし"))])
    result += table(["方式・表現", "対象", "単独支持の誤差・95%区間", "定数train平均基準の誤差", "測定／予定", "保存診断", "欠測情報"], rows)
    result += '<details><summary>ABX単独支持と尺度調整・moments欠測</summary>'
    rows = [[f'{NAMES[r["method"]]}／{VIEW_NAMES[r["view"]]}', f'{r["measured_triplets"]}/4960',
             f'train {r["scale"]["recording_count"]}/120・定数次元 {r["scale"]["constant_dimensions"]}',
             '距離失敗・token支持欠落の理由件数：保存なし'] for r in appendix["abx_own_support"]]
    result += table(["方式・表現", "単独支持三つ組／予定", "保存尺度情報", "欠測情報"], rows) + '<ul>'
    for row in appendix["moment_failures"]:
        result += f'<li>{"学習" if row["split"] == "train" else "評価"} {NAMES[row["method"]]}／{VIEW_NAMES[row["view"]]}：予定120、保存測定成功 {row["status_counts"].get("measured", 0)}。{reasons(row["reason_counts"])}</li>'
    return result + '</ul></details><p><a href="feature-appendix.json">特徴のscalar付録</a>・<a href="feature-public.json">元の特徴公開JSON</a>。条件別予定数や未保存理由数は推測せず「保存なし」とします。F0読み出しには直接保存されたF0列があり、高次元表現はtrain録音数を超えます。</p>'


def costs(annotation):
    result = '<h2 id="costs">計算時間・保存量（別の観測群）</h2><p>元報告の状態は partial_derived_preparation_not_final のままです。下表は保存観測の範囲の注記であり、最終速度比較を意味しません。RTFの分母は原入力の全抜粋秒です。品質の共通窓秒や話者等重み平均・bootstrap区間とは別の統計です。</p>'
    result += table(["方式", "条件", "成功／予定", "失敗等の終端", "未観測"], [
        [NAMES[r["method"]], CONDITIONS[r["condition"]], f'{r["successful_support"]}/120',
         str(r["failed_or_other_terminal_support"]), str(r["unobserved_support"])] for r in annotation["coverage"]])
    rows = []
    for r in annotation["observations"]:
        rate = r.get("rtf", r.get("bytes_per_second"))
        rates = "—" if rate is None else f'{number(rate["mean"])} / {number(rate["median"])}'
        if "bits_per_second" in r:
            rates += f'<br>bit/s {number(r["bits_per_second"]["mean"])} / {number(r["bits_per_second"]["median"])}'
        rows.append([f'{NAMES[r["method"]]}／{CONDITIONS[r["condition"]]}',
                     f'{esc(CATEGORIES.get(r["category"], "保存観測項目"))}<br><small>{esc(r["metric"])}</small>',
                     f'{number(r["values"]["mean"])} / {number(r["values"]["median"])} {"秒" if r["unit"] == "seconds" else "byte"}',
                     f'{r["measured_support"]}/120（欠測等 {r["missing_or_failed"]}）',
                     support(r["successful_condition_support"]), rates])
    result += table(["方式・条件", "観測項目", "平均 / 中央値", "観測支持／予定", "同じ観測内の条件成功数", "RTFまたはbyte/sの平均 / 中央値"], rows)
    return result + '<p>候補の1threadは作業者報告で契約未照合、PML/WORLDの2threadは契約確認値です。方式間速度順位・codec合計時間は作りません。候補の純編集時間、profileなし復号、純全解析、入出力単独時間、共有資産量は未測定です。total−renderを編集費とは扱いません。native直接decodeはq1の参照用診断です。</p><p><a href="cost.json">元の費用JSON</a>・<a href="cost-coverage.json">同一計画・終端出典と保存範囲の別注記</a></p>'


def render(summary, labels, appendix, cost, audio, recorded_at):
    result = '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>aHM固定Cartesian編集と現PML・WORLDの統合比較</title><style>' + STYLE + '</style></head><body><main>'
    result += '<h1>aHM固定Cartesian編集と現PML・WORLDの統合比較</h1><p>現ベース：PML pml-lowband-fwcep60-v1。候補の採用は未決定です。通常品質71軸＋編集8軸は固定120録音・40話者の全区間が終端。特徴も必要な終端成果が揃っています。終端には測定失敗や未対応を含みます。</p>'
    result += '<p><a href="ordinary.html">凍結された全79軸・短音声の原HTMLを開く</a>（元bytesを変更せず収録）</p>'
    result += '<nav><a href="#ordinary">全79軸の原HTML</a>／<a href="#audio">短音声・帰属</a>／<a href="#features">特徴ABX・読み出し</a>／<a href="#costs">費用</a>／<a href="#provenance">来歴</a></nav>'
    result += '<h2>現PML・候補・WORLDの比較</h2><p>総合点・平均順位・勝ち数は作りません。以下の順位は保存済み共通支持順位をそのまま表示し、同順位と順位の飛びを保持します。予測MOSは新しい人の聴取評定ではありません。</p>'
    mos = next(axis for axis in summary["axes"] if axis["id"] == "1.native_mos" and axis["condition"] == "native")
    result += ordinary(mos, labels[mos["id"], mos["condition"]]).replace(f'id="{anchor(mos)}"', 'id="mos-overview"', 1)
    result += '<h2 id="audio">短音声・出典と帰属</h2><p>固定2録音の無編集・先頭2秒以内、16kHz mono。<a href="ordinary.html">原HTML内で聴き比べる</a>／<a href="audio-attribution.html">作者・LibriVox由来・ライセンス・非推奨表示</a>／<a href="audio-manifest.json">承認済み短音声manifest</a></p>'
    result += table(["固定録音", "方式", "音声・状態"], [[esc(r["case"]), NAMES[r["method"]],
        f'<audio controls preload="none" src="{esc(r["src"])}"></audio>'
        if r["status"] == "available" else "上流生成失敗・差替えなし"] for r in audio])
    result += '<section id="ordinary"><h2>通常品質71軸＋編集8軸</h2><p><a href="ordinary.html">保存済み全79軸の比較表を開く</a>。原HTMLをそのまま保持し、全表を再実装していません。軸単位の深いリンクは元HTMLに未提供です。共通支持順位と方式ごとのPML対応差は支持集合が異なることがあります。95%区間は話者bootstrapの記述的区間・多重比較未補正です。</p></section>'
    result += '<section id="features"><h2>特徴空間ABX・固定読み出し</h2><p>独立train120録音・40話者、test120録音・別40話者。ABX予定4960三つ組。候補3viewと現PMLの全必要終端が揃っています。特徴順位は未付与です。</p><p><a href="features.html">対応値・支持、単独支持の定数基準・次元診断、欠測情報を見る</a>／<a href="feature-appendix.json">scalar付録</a></p></section>'
    result += '<section id="costs"><h2>計算時間・保存量</h2><p>元報告は partial_derived_preparation_not_final のままです。方式間速度順位はありません。条件別成功/失敗/未観測と、保存された平均/中央値を別の観測群として示します。</p><p><a href="costs.html">費用と観測範囲・測定条件を見る</a>／<a href="cost-coverage.json">別の範囲注記</a></p></section>'
    result += '<h2 id="provenance">来歴と対象範囲</h2><p>旧結果は今回の同一支持のPML差や現順位へ混ぜていません。歴史結果の79軸に行があっても、今回へ厳密に流用できる軸は0という別監査を維持します。48kHz対応・総合優越・候補採用をこの表示から新たに宣言しません。</p>'
    result += f'<p>組立て記録日時：{esc(recorded_at)}。入力の科学結果へ日時を後付けしていません。</p><p><a href="ordinary-summary.json">通常評価の原集約JSON</a>／<a href="plan.json">固定計画</a>／<a href="axis-metadata.json">表示ラベル</a>／<a href="provenance.json">出典SHA・保存対応と制限</a>／<a href="artifact-manifest.json">成果物byte数・SHA一覧</a></p>'
    return result + '</main></body></html>'


def detail_page(title, body):
    return '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>' + esc(title) + '</title><style>' + STYLE + '</style></head><body><main><p><a href="index.html">統合比較の入口へ戻る</a>／<a href="ordinary.html">全79軸の原HTML</a></p><h1>' + esc(title) + '</h1>' + body + '<p><a href="provenance.json">出典SHAと制限</a></p></main></body></html>'
