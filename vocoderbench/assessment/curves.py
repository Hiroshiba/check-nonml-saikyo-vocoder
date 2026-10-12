"""#12、#16〜18。保存された復号音・実表現ファイル・評価証跡を曲線にする。"""
from __future__ import annotations

import numpy as np

from .acoustics import auditory, content
from .common import NotApplicable, error_summary, number, ok
from .controls import attributes, gain, pitch


def points(job, parameter):
    rows = job["points"]
    if len(rows) < 2:
        raise ValueError("曲線には2条件以上が必要です")
    values = [number(row[parameter], parameter) for row in rows]
    if len(set(values)) != len(values):
        raise ValueError("曲線の操作量が重複しています。同一条件のseedは別jobへ分けてください")
    return [rows[i] for i in np.argsort(values)]


def evidence(point, job, inputs, signatures):
    required = job.get("quality_metrics", [])
    if len(set(required)) != len(required) or set(required)-{"predicted_mos", "speaker_similarity"}:
        raise ValueError("品質証跡はpredicted_mosとspeaker_similarityを指定してください")
    data = inputs.json(point["quality_evidence"]) if point.get("quality_evidence") else None
    if data is not None:
        spec = point["output"]
        path = inputs.path(spec if isinstance(spec, str) else spec["path"])
        if data["audio_sha256"] != inputs.hashes[str(path)]:
            raise ValueError("品質証跡と復号音のハッシュが不一致です")
    result = {}
    for metric in required:
        item = data.get("scores", {}).get(metric) if data else None
        if job["kind"] != "speech":
            result[metric] = {"status": "not_applicable", "value": None, "reason": "人工プローブに音声品質を適用しない"}
        elif not item:
            result[metric] = {"status": "not_configured", "value": None}
        else:
            if not item.get("evaluator") or not item.get("configuration_sha256") or not item.get("unit"):
                raise ValueError("評価器と設定・重みを識別するハッシュと単位が必要です")
            signature = (item["evaluator"], item["configuration_sha256"], item["unit"])
            if signatures.setdefault(metric, signature) != signature:
                raise ValueError("曲線の途中で評価器・設定・重み・単位が変更されています")
            if item["status"] == "ok":
                result[metric] = {**item, "value": number(item["value"])}
            else:
                result[metric] = {**item, "value": None}
    return result


def quality_curve(job, inputs):
    rows, signatures = [], {}
    ordered = points(job, "amount")
    if not job.get("control") or not job.get("control_unit") or 0 not in [r["amount"] for r in ordered]:
        raise ValueError("操作名・単位と、操作量0の無編集条件が必要です")
    for point in ordered:
        y, sr = inputs.audio(point["output"])
        scores = evidence(point, job, inputs, signatures)
        cer = None
        if point.get("transcripts"):
            cer = content({**job, "output": point["output"], "transcripts": point["transcripts"]}, inputs)
        rows.append({"amount": number(point["amount"]), "output": point["output"], "quality": scores,
                     "content": cer, "output_peak": float(abs(y).max()), "duration_seconds": len(y)/sr})
    baseline = next(row for row in rows if row["amount"] == 0)
    def audio_path(spec):
        return inputs.path(spec if isinstance(spec, str) else spec["path"])
    if inputs.hashes[str(audio_path(baseline["output"]))] != inputs.hashes[str(audio_path(job["reference"]))]:
        raise ValueError("操作量0の音声と無編集参照が一致しません")
    for row in rows:
        row["delta_from_unedited"] = {}
        for metric, item in row["quality"].items():
            base = baseline["quality"][metric]
            row["delta_from_unedited"][metric] = item["value"]-base["value"] if item["status"] == base["status"] == "ok" else None
    if not any(row["quality"] or row["content"] for row in rows):
        raise ValueError("品質・内容保持の証跡がありません。音声の長さだけでは品質曲線になりません")
    missing = sum(item["status"] != "ok" for row in rows for item in row["quality"].values())
    result = ok(None, "編集量別の品質・内容保持", points=rows, missing_quality_values=missing,
                requested_quality_metrics=job.get("quality_metrics", []),
                definition="非参照品質と内容保持を別表示。編集音を未編集原音への参照距離で罰しない")
    if missing or not job.get("quality_metrics") or any(r["content"] and r["content"]["status"] != "ok" for r in rows):
        result.update(status="partial", reason="品質評価器の値が不足、または内容保持のみの部分測定です")
    return result


def interpolation(job, inputs):
    ordered = points(job, "alpha")
    levels = np.asarray([p["alpha"] for p in ordered], dtype=float)
    if levels[0] != 0 or levels[-1] != 1 or len(levels) < 3:
        raise ValueError("補間は端点0・1と中間点が必要です")
    if job.get("endpoint_relation") not in ("same_phone", "aligned_utterance") or not job.get("interpolation_rule"):
        raise ValueError("意味の対応する端点と、方式固有の補間規則を明示してください")
    rows, signatures = [], {}
    for point in ordered:
        x, sr = inputs.audio(point["output"])
        inputs.path(point["feature_artifact"])
        values = attributes(x, sr, number(job["low_hz"]), number(job["high_hz"]))
        rows.append({"alpha": number(point["alpha"]), "attributes": values,
                     "quality": evidence(point, job, inputs, signatures)})
    diagnostics = {}
    for key in rows[0]["attributes"]:
        values = [row["attributes"][key] for row in rows]
        if any(value is None for value in values):
            diagnostics[key] = {"status": "not_applicable", "missing_points": values.count(None)}
            continue
        values = np.asarray(values)
        slopes = np.diff(values)/np.diff(levels)
        tolerance = number(job["attribute_tolerances"][key])
        if tolerance < 0:
            raise ValueError("単調性の許容差は非負で指定してください")
        sign = np.sign(values[-1]-values[0]) if abs(values[-1]-values[0]) > tolerance else 0
        diagnostics[key] = {"status": "ok", "values": values.tolist(), "max_abs_slope": float(abs(slopes).max()),
                            "max_abs_slope_change": float(abs(np.diff(slopes)).max()),
                            "monotonicity_tolerance": tolerance,
                            "reversal_steps": int((sign*np.diff(values) < -tolerance).sum()) if sign else None,
                            "endpoint_linear_deviation": error_summary(values-(values[0]+levels*(values[-1]-values[0])))}
    quality_dips = {}
    for key in job.get("quality_metrics", []):
        values = [row["quality"][key]["value"] for row in rows]
        quality_dips[key] = max(0.0, min(values[0], values[-1])-min(values[1:-1])) if all(v is not None for v in values) else None
    result = ok(None, "補間診断", points=rows, attributes=diagnostics, quality_dips_below_both_endpoints=quality_dips,
                definition="有限個の復号点での属性差分。連続性の証明や線形変化の要求ではない")
    if any(v is None for v in quality_dips.values()) or not quality_dips or any(v["status"] != "ok" for v in diagnostics.values()):
        result.update(status="partial", reason="品質証跡または測定可能な属性が不足しています")
    return result


def check_controls(point, job, inputs):
    rows = []
    for check in point.get("controls", []):
        if check["metric"] not in ("pitch_tracking", "gain_tracking"):
            raise ValueError("曲線の制御確認はpitch_trackingまたはgain_trackingです")
        function = pitch if check["metric"] == "pitch_tracking" else gain
        # 各表現量の無編集復号音を参照にする。原音との差を編集誤差へ混ぜない。
        params = {**check, "reference": point["output"]}
        try:
            result = function(params, inputs)
        except NotApplicable as error:
            result = {"status": "not_applicable", "value": None, "reason": str(error)}
        rows.append({"metric": check["metric"], "result": result})
    return rows


def representation_curve(job, inputs, *, rate_curve=False):
    parameter = "configuration" if rate_curve else "amount"
    if rate_curve:
        ordered = job["points"]
        if len(ordered) < 2 or len({p[parameter] for p in ordered}) != len(ordered):
            raise ValueError("異なる表現量の条件が2つ以上必要です")
        if not job.get("serialization_rule"):
            raise ValueError("量子化・ヘッダー・符号化の仕様を明示してください")
    else:
        ordered = points(job, parameter)
        if not job.get("perturbation") or not job.get("perturbation_unit") or 0 not in [p["amount"] for p in ordered]:
            raise ValueError("物理的摂動・単位と量0の条件が必要です")
    if not job.get("decoder_revision"):
        raise ValueError("復号器の版が必要です")
    reference, rate = inputs.audio(job["reference"])
    duration = len(reference)/rate
    rows, signatures = [], {}
    for point in ordered:
        artifact = inputs.path(point["feature_artifact"])
        score = auditory({"reference": job["reference"], "output": point["output"]}, inputs)
        row = {parameter: point[parameter], "auditory": score, "quality": evidence(point, job, inputs, signatures),
               "controls": check_controls(point, job, inputs), "artifact_sha256": inputs.hashes[str(artifact)]}
        if rate_curve:
            size = artifact.stat().st_size
            if not size:
                raise ValueError("空の表現ファイルは使えません")
            row.update(serialized_bytes=size, serialized_bits_per_second=8*size/duration,
                       rate_denominator_seconds=duration, byte_scope="指定した実ファイル全体。ヘッダー込み")
        rows.append(row)
    if rate_curve:
        rows.sort(key=lambda row: row["serialized_bits_per_second"])
    result = ok(None, "表現量曲線" if rate_curve else "摂動曲線", points=rows,
                definition="実際の保存表現と復号音を評価。符号化・復号・量子化の実行時間は含まない")
    missing = sum(item["status"] != "ok" for row in rows for item in row["quality"].values())
    missing_controls = any(not row["controls"] or any(c["result"]["status"] != "ok" for c in row["controls"]) for row in rows)
    if missing or not job.get("quality_metrics") or missing_controls:
        result.update(status="partial", reason="聴覚帯域誤差は測定済み。品質・制御の全軸は未完了です")
    return result


def robustness(job, inputs):
    return representation_curve(job, inputs)


def information_rate(job, inputs):
    return representation_curve(job, inputs, rate_curve=True)
