"""保存済み追加指標を、固定分母と話者単位を保って報告用に集計する。"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from statistics import mean, median

METHODS = ("hnm", "world_harvest")
LABELS = {"identity": "原音", "hnm": "HNM v3（現ベース）", "world_harvest": "WORLD（Harvest）"}
CONDITIONS = ("unedited", "pitch_minus3", "pitch_plus3", "gain_minus6", "gain_plus6")
CONDITION_LABELS = {"unedited": "無編集", "pitch_minus3": "−3半音", "pitch_plus3": "+3半音",
                    "gain_minus6": "−6 dB", "gain_plus6": "+6 dB"}
METRIC_LABELS = {"mos": "予測MOS ↑", "speaker_ecapa": "ECAPA類似度 ↑", "erb": "ERB 20 ms誤差 dB ↓",
                 "auditory_local": "局所ERB 40 ms誤差 dB ↓", "auditory_local_p95": "局所ERB 40 ms・発話内P95 dB ↓",
                 "serialized_bytes_per_second": "実NPZ bytes/秒"}


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def describe(values):
    return {"mean": mean(values) if values else None, "median": median(values) if values else None,
            "minimum": min(values) if values else None, "maximum": max(values) if values else None}


def split_method(method):
    parts = method.split("__", 1)
    return parts[0], parts[1] if len(parts) == 2 else "unedited"


def summarize(rows, entries, methods=METHODS):
    """初回値を集約。時間反復は入力しない。WORLD−HNMは同一発話を先に差分化。"""
    planned = {row["id"]: row["speaker"] for row in entries}
    speakers = sorted(set(planned.values()))
    expected = Counter(planned.values())
    result, by_method = {"methods": {}}, {}
    for method in methods:
        selected = [row for row in rows if row["method"] == method]
        indexed = {row["case"]: row for row in selected}
        if len(indexed) != len(selected) or not set(indexed).issubset(planned):
            raise ValueError("固定集合外または重複した発話を集計できません")
        valid = {key: row["value"] for key, row in indexed.items()
                 if row["status"] in ("ok", "measured") and finite(row.get("value"))}
        speaker_rows = []
        for speaker in speakers:
            values = [value for case, value in valid.items() if planned[case] == speaker]
            speaker_rows.append({"speaker": speaker, "planned_cases": expected[speaker],
                                 "valid_cases": len(values), **describe(values)})
        means = [row["mean"] for row in speaker_rows if row["mean"] is not None]
        counts = Counter(row["status"] for row in selected)
        counts.update({"missing_result": len(entries) - len(selected)})
        result["methods"][method] = {"planned_cases": len(entries), "valid_cases": len(valid),
            "missing_cases": len(entries) - len(valid), "planned_speakers": len(speakers),
            "valid_speakers": len(means), "complete_speakers": sum(
                row["valid_cases"] == row["planned_cases"] for row in speaker_rows),
            "speaker_macro_mean": mean(means) if means else None,
            "utterance_macro": describe(list(valid.values())), "speaker_rows": speaker_rows,
            "status_counts": dict(counts)}
        by_method[method] = valid
    if all(method in by_method for method in METHODS):
        a, b = (by_method[method] for method in METHODS)
        pairs = [{"case": case, "speaker": planned[case], "value": b[case] - a[case]}
                 for case in planned if case in a and case in b]
        speaker_rows = []
        for speaker in speakers:
            values = [row["value"] for row in pairs if row["speaker"] == speaker]
            speaker_rows.append({"speaker": speaker, "planned_cases": expected[speaker],
                                 "paired_cases": len(values), **describe(values)})
        means = [row["mean"] for row in speaker_rows if row["mean"] is not None]
        result["paired_world_harvest_minus_hnm"] = {"planned_cases": len(entries), "paired_cases": len(pairs),
            "planned_speakers": len(speakers), "paired_speakers": len(means),
            "complete_speakers": sum(row["paired_cases"] == row["planned_cases"] for row in speaker_rows),
            "speaker_macro_mean": mean(means) if means else None, "speaker_rows": speaker_rows, "case_rows": pairs}
    return result


def quality_summary(mos_rows, quality_rows, entries):
    groups = defaultdict(list)
    for row in mos_rows:
        method, condition = split_method(row["method"])
        measurement = row["measurement"]
        groups[("mos", condition)].append({"case": row["case"], "method": method,
            "value": measurement.get("value"), "status": measurement["status"], "origin": row["origin"]})
    for row in quality_rows:
        method, condition = split_method(row["method"])
        groups[(row["metric"], condition)].append({"case": row["case"], "method": method,
                                                 "value": row.get("value"), "status": row["status"]})
    result = []
    for (metric, condition), rows in sorted(groups.items()):
        methods = ("identity", *METHODS) if metric == "mos" and condition == "unedited" else METHODS
        result.append({"metric": metric, "condition": condition, **summarize(rows, entries, methods)})
    return result


def synthesis_rows(records, entries, measured_sizes):
    by_case = {row["id"]: row for row in entries}
    saved_sizes = {(row["case"], row["method"]): row for row in measured_sizes["rows"]}
    rows, sizes = [], []
    for record in records:
        entry = by_case[record["case"]]
        for condition in CONDITIONS:
            output = record["outputs"].get(condition, {})
            rows.append({"case": record["case"], "speaker": entry["speaker"], "method": record["method"],
                "condition": condition, "kind": "natural_speech", "status": output.get("status", "missing"),
                "measurement": {"status": "ok" if output.get("status") == "measured" else "missing"},
                "audio": output.get("audio"), "controls": output.get("controls"),
                "wall_seconds": output.get("wall_seconds"), "process_cpu_seconds": output.get("process_cpu_seconds")})
        measured = saved_sizes.get((record["case"], record["method"]), {})
        size, duration = measured.get("serialized_bytes"), measured.get("rate_denominator_seconds")
        valid = measured.get("status") == "ok" and finite(size) and finite(duration) and duration > 0
        sizes.append({"case": record["case"], "method": record["method"], "speaker": entry["speaker"],
                      "status": "measured" if valid else measured.get("status", "missing"),
                      "value": size / duration if valid else None, "serialized_bytes": size,
                      "duration_seconds": duration, "artifact_sha256": measured.get("artifact_sha256"),
                      "source_status": measured.get("status"), "reason": measured.get("reason")})
    return rows, {"metric": "serialized_bytes_per_second", "condition": "native_compressed_npz",
                  "unit": "bytes/s", "source": "assessment準備で実ファイルhashを合成記録と照合し計測したNPZ bytes。ヘッダー・メタデータ込み。",
                  "rows": sizes, **summarize(sizes, entries)}



def playback_headroom(rows):
    groups = []
    for condition in ("gain_minus6", "gain_plus6"):
        for method in METHODS:
            selected = [r for r in rows if r["condition"] == condition and r["method"] == method]
            valid = [r for r in selected if r["status"] == "measured" and finite((r.get("audio") or {}).get("peak"))]
            fractions = [r["audio"]["over_one_fraction"] for r in valid if finite(r["audio"].get("over_one_fraction"))]
            groups.append({"condition": condition, "method": method, "planned_cases": 120,
                           "measured_cases": len(valid), "over_one_cases": sum(r["audio"]["peak"] > 1 for r in valid),
                           "maximum_peak": max((r["audio"]["peak"] for r in valid), default=None),
                           "maximum_over_one_fraction": max(fractions, default=None),
                           "source": "合成保存時に全長浮動小数点波形から記録したpeak/over_one_fraction",
                           "interpretation": "合成波形はclipしていない。振幅1超は再生機器・整数化で歪む可能性。追従誤差や予測MOSは再生系の安全性を保証しない。"})
    return {"groups": groups, "waveform_clipped": False, "gain_normalization_applied": False}


def comparison_rows(quality, assessment, sizes):
    unedited = {item["metric"]: item for item in quality if item["condition"] == "unedited"}
    for item in assessment["groups"]:
        if item["metric"] == "auditory_local":
            if item["scalar"] == "value":
                unedited["auditory_local"] = item
            elif item["scalar"] == "local_frame_rmse.abs_p95":
                unedited["auditory_local_p95"] = item
    unedited["serialized_bytes_per_second"] = sizes
    rows = []
    for metric, label in METRIC_LABELS.items():
        item = unedited.get(metric, {})
        rows.append({"metric": metric, "label": label, "methods": item.get("methods", {}),
                     "paired_world_harvest_minus_hnm": item.get("paired_world_harvest_minus_hnm", {})})
    rows.append({"metric": "scoreq", "label": "SCOREQ natural/ref距離 ↓", "methods": unedited["scoreq"]["methods"],
                 "paired_world_harvest_minus_hnm": unedited["scoreq"]["paired_world_harvest_minus_hnm"],
                 "reason": "推論結果未保存。全240予定を欠測として保持。" if unedited["scoreq"].get("evaluation_attempted") is False
                 else "保存済みnatural/refの初回値。取得失敗・再取得・モデルhashは公開証跡に保持。"})
    return rows


def coverage(quality, assessment, asr, sizes, assessment_rows):
    counts = Counter()
    for group in quality:
        counts[group["metric"]] += sum(v["valid_cases"] for k, v in group["methods"].items() if k != "identity")
    metric_rows = defaultdict(list)
    for group in assessment["groups"]:
        if group["scalar"] == "value":
            metric_rows[group["metric"]].append(group)
    def valid(metric):
        return sum(x["valid_cases"] for g in metric_rows[metric] for x in g["methods"].values())
    asr_valid = sum(x["reference_usable"]["overall"]["case_count"] for x in asr["methods"].values())
    def job_valid(metric):
        return sum(row["status"] == "ok" for row in assessment_rows if row["spec"]["metric"] == metric)

    definitions = [
        (1, "UTMOSv2予測MOS", "実測" if counts["mos"] == 1200 else "部分", counts["mos"], 1200,
         "原音120と無編集240は同一float32・SR・長さ・科学設定の歴史値を再利用。編集960は新規。人間校正なし。"),
        (2, "SCOREQ natural/ref", "実測" if counts["scoreq"] == 240 else "部分" if counts["scoreq"] else "未測定",
         counts["scoreq"], 240,
         "無編集240予定の参照距離。公式重みの取得失敗・再取得履歴、推論の成否と実モデルhashを保存。"
         "結果がない点はnull。代用モデル・ゼロ補完なし。人間校正なし。"),
        (3, "ViSQOL Audio", "対象外", 0, 240, "48 kHz入力の仕様に対して本集合は16 kHz。upsampleで48 kHz原録音の実績にはしない。"),
        (4, "ASR増分CER/WER", "部分", asr_valid, 240,
         "切出しなし公式全文55/120録音・32話者のみ。原音CER>20%はpartialのまま。残65録音は部分正解未整備。"),
        (5, "ECAPA話者埋込み", "実測" if counts["speaker_ecapa"] == 1200 else "部分", counts["speaker_ecapa"], 1200,
         "全編集点で固定原音参照。知覚的話者類似度や同話者・異話者の校正はない。"),
        (6, "ERB／局所聴覚誤差", "実測" if valid("auditory_local") == 240 and counts["erb"] == 240 else "部分",
         valid("auditory_local"), 240, "20 ms ERBと40 ms auditory_localを別定義で記録。関連診断なので独立した2票と数えない。"),
        (7, "音高操作追従", "部分", valid("pitch_tracking"), 480,
         "各方式の無編集復号を基準に±300 centのみ。自然音声の独立F0真値・動的軌跡なし。"),
        (8, "音量操作追従", "部分", valid("gain_tracking"), 480,
         "±6 dBの定常RMS応答のみ。動的操作・知覚ラウドネスは未測定。"),
        (9, "局所時間制御", "未測定", 0, None, "自然音声の独立イベント位置・時間操作出力がない。"),
        (10, "音色操作追従", "未測定", 0, None, "知覚音色の正解と対応する操作出力がない。干渉の傾斜値で代用しない。"),
        (11, "制御間の干渉", "部分", job_valid("interference"), 240,
         "ゲイン列の中央差分のみ。理想一様振幅スケールの期待値。ピッチ列・知覚的独立性は未校正。"),
        (12, "編集量別の品質曲線", "部分", job_valid("quality_curve"), 480,
         "pitch/gain各3点。予測MOSと固定原音ECAPAは別軸。使用可能な編集幅・連続曲線への一般化なし。"),
        (13, "人間評定との近傍一致", "未測定", 0, None, "該当する既存人間評定と特徴の対がない。"),
        (14, "音素ABX", "未測定", 0, None, "音素境界・比較三つ組・固定距離校正の入力がない。"),
        (15, "属性の読み出し", "未測定", 0, None, "独立な属性正解と学習／評価分離を用意していない。"),
        (16, "表現補間", "未測定", 0, None, "対応を定義した表現補間点と復号音がない。"),
        (17, "表現の頑健性", "未測定", 0, None, "各表現に意味のある摂動条件と復号音がない。"),
        (18, "情報量・品質との関係", "部分", sum(x["valid_cases"] for x in sizes["methods"].values()), 240,
         "実NPZ全体のbytes/秒を1設定で測定。理論情報率・量子化条件別のPR30品質–表現量曲線は未達。"),
    ]
    return [{"number": n, "label": label, "status": status, "measured": measured, "planned": planned, "reason": reason}
            for n, label, status, measured, planned, reason in definitions]


def timings(mos_rows, quality_reports, synthesis, asr, assessment):
    new = [r for r in mos_rows if r["origin"] == "new_inference"]
    reused = [r for r in mos_rows if r["origin"] != "new_inference"]
    measurements = [r for report in quality_reports for r in report["rows"]]
    return {"mos": {"origins": dict(Counter(r["origin"] for r in mos_rows)),
                       "new_inference_recorded_seconds": sum(r["measurement"].get("seconds", 0) or 0 for r in new),
                       "reused_rows": len(reused), "reused_historical_seconds_excluded": True},
            "quality": {"first_wall_seconds": sum(r.get("measurement", {}).get("first", {}).get("wall_seconds", 0) or 0 for r in measurements),
                        "repeat_wall_seconds": sum(sum(x.get("wall_seconds", 0) or 0 for x in r.get("measurement", {}).get("repetitions", [])) for r in measurements),
                        "initialization_seconds": sum(m.get("seconds", 0) or 0 for p in quality_reports for m in p["metrics"].values())},
            "synthesis": {"analysis_seconds": sum(r.get("analysis_seconds", 0) for r in synthesis),
                          "decode_wall_seconds": sum(x.get("wall_seconds", 0) for r in synthesis for x in r["outputs"].values())},
            "asr": asr["timing"], "assessment_status_counts": assessment["assessment_status_counts"],
            "note": "同時実行・分割初期化を含む記録。各工程の和は全体経過時間ではない。初回＋1反復で速度安定性は主張しない。"}
