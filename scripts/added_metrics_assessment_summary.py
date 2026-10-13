"""固定120発話の追加評価を話者単位に集計する。欠測と予定分母を保持する。"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import math
from pathlib import Path
import time

import numpy as np

from vocoderbench.assessment.common import digest, read_json, save_json
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("hnm", "world_harvest")
ATTRIBUTES = {"pitch_cents": "cent/dB", "level_db": "dB/dB",
              "slope_db_per_octave": "(dB/oct)/dB", "duration_seconds": "s/dB"}
QUALITY_UNITS = {"predicted_mos": "predicted MOS", "speaker_similarity": "cosine"}
FIELDS = {
    "auditory_local": [("value", "dB"), ("local_frame_rmse.abs_p95", "dB"),
                       ("reference_active_cells", "count"), ("total_band_frame_cells", "count")],
    "pitch_tracking": [("value", "cent"), ("relative_error.abs_p95", "cent"),
                       *[(name, "count") for name in (
                           "relative_error.count", "expected_voiced_frames", "expected_unvoiced_frames",
                           "missing_voiced_frames", "false_voiced_frames", "unmapped_frames", "out_of_range_frames",
                           "gross_error_over_600_cents", "octave_error_frames", "total_frames")]],
    "gain_tracking": [("value", "dB"), ("errors.abs_p95", "dB"), ("errors.mean", "dB"),
                      ("output_peak", "amplitude"), ("over_one_fraction", "fraction"),
                      *[(name, "count") for name in ("errors.count", "reference_silent_frames",
                                                    "silent_output_frames", "total_frames")]],
}


def nested(data, path):
    value = data
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def spec_identity(spec, measured_hashes=None):
    """証跡の保存先だけが違う分割実行を、保存内容が同一の場合に限り統合する。"""
    if spec["metric"] != "quality_curve":
        return spec
    points = []
    for point in spec["points"]:
        point = dict(point)
        if point.get("quality_evidence"):
            path = Path(point["quality_evidence"])
            if not path.is_absolute():
                raise ValueError("この集計の品質証跡は生成scriptの絶対パスを指定してください")
            actual = digest(path)
            recorded = (measured_hashes or {}).get(str(path.resolve()))
            if recorded is not None and recorded != actual:
                raise ValueError("測定後に品質証跡の内容が変わっています")
            point["quality_evidence"] = {"file_sha256": actual}
        points.append(point)
    return {**spec, "points": points}


def extract(report, manifest, size_report, entries):
    by_id = {row["spec"]["id"]: row for row in report["rows"]}
    rows = []

    def emit(spec, scalar, unit, value, status, usable, **extra):
        rows.append({**{key: spec[key] for key in ("case", "speaker", "method", "seed", "metric", "condition")},
                     "job_id": spec["id"], "scalar": scalar, "unit": unit, "status": status,
                     "value": value if usable and finite(value) else None,
                     "value_status": "measured" if usable and finite(value) else "missing", **extra})

    for spec in manifest["jobs"]:
        row = by_id.get(spec["id"], {})
        status, result = row.get("status", "pending"), row.get("result", {})
        metric = spec["metric"]
        if metric in FIELDS:
            for name, unit in FIELDS[metric]:
                usable = status == "ok" or (unit == "count" and status in ("partial", "not_applicable"))
                emit(spec, name, unit, nested(result, name), status, usable)
        elif metric == "interference":
            cells = {(cell["control"], cell["attribute"]): cell for cell in result.get("matrix", [])}
            for attribute, unit in ATTRIBUTES.items():
                cell = cells.get(("gain", attribute), {})
                cell_status = cell.get("status", status if status != "ok" else "missing")
                usable = status in ("ok", "partial") and cell_status == "ok"
                for name, dimension in (("response", unit), ("normalized_error", "normalized")):
                    emit(spec, f"gain.{attribute}.{name}", dimension, cell.get(name), cell_status, usable,
                         upstream_status=status)
        elif metric == "quality_curve":
            points = {point["amount"]: point for point in result.get("points", [])}
            zero = points.get(0, {})
            for requested in spec["points"]:
                amount = requested["amount"]
                point = points.get(amount, {})
                for name, default_unit in QUALITY_UNITS.items():
                    score = point.get("quality", {}).get(name, {})
                    base = zero.get("quality", {}).get(name, {})
                    point_status = score.get("status", status if status != "ok" else "missing")
                    usable = status in ("ok", "partial") and point_status == "ok"
                    unit = score.get("unit", default_unit)
                    emit(spec, f"amount={amount}.{name}.value", unit, score.get("value"), point_status, usable,
                         upstream_status=status, amount=amount, control=spec["control"])
                    delta = point.get("delta_from_unedited", {}).get(name)
                    delta_usable = usable and base.get("status") == "ok" and base.get("unit") == unit
                    emit(spec, f"amount={amount}.{name}.delta_from_unedited", unit, delta,
                         point_status if delta_usable else "baseline_or_point_missing", delta_usable,
                         upstream_status=status, amount=amount, control=spec["control"])
    sizes = {(row["case"], row["method"]): row for row in size_report["rows"]}
    for case in entries:
        for method in METHODS:
            row = sizes.get((case["id"], method), {})
            status = row.get("status", "pending")
            spec = {"case": case["id"], "speaker": case["speaker"], "method": method, "seed": 0,
                    "metric": "serialized_size_single_point", "condition": "native_compressed_npz",
                    "id": f"{case['id']}__{method}__serialized_size"}
            for name, unit in (("serialized_bytes", "bytes"), ("serialized_bits_per_second", "bit/s")):
                emit(spec, name, unit, row.get(name), status, status == "ok")
    return rows


def stats(values):
    return {"mean": float(np.mean(values)) if values else None,
            "median": float(np.median(values)) if values else None,
            "min": min(values) if values else None, "max": max(values) if values else None}


def summarize(rows, entries):
    groups = defaultdict(list)
    speakers = sorted({row["speaker"] for row in entries})
    expected = Counter(row["speaker"] for row in entries)
    case_ids = {row["id"] for row in entries}
    for row in rows:
        groups[(row["metric"], row["condition"], row["scalar"], row["unit"])].append(row)
    summaries = []
    for (metric, condition, scalar, unit), group in sorted(groups.items()):
        summary = {"metric": metric, "condition": condition, "scalar": scalar, "unit": unit, "methods": {}}
        by_method = {}
        for method in METHODS:
            selected = [row for row in group if row["method"] == method]
            by_case = {row["case"]: row for row in selected}
            if len(by_case) != len(selected):
                raise ValueError(f"同じ発話の集計値が重複しています: {metric} {condition} {scalar} {method}")
            if not set(by_case).issubset(case_ids):
                raise ValueError("固定集合の外の発話を集計できません")
            by_method[method] = by_case
            speaker_rows = []
            for speaker in speakers:
                available = [row["value"] for row in selected if row["speaker"] == speaker
                             and row["value_status"] == "measured"]
                speaker_rows.append({"speaker": speaker, "planned_cases": expected[speaker],
                                     "valid_cases": len(available), "missing_cases": expected[speaker]-len(available),
                                     **stats(available)})
            valid = [row["value"] for row in selected if row["value_status"] == "measured"]
            means = [row["mean"] for row in speaker_rows if row["mean"] is not None]
            summary["methods"][method] = {
                "planned_cases": len(entries), "valid_cases": len(valid), "missing_cases": len(entries)-len(valid),
                "planned_speakers": len(speakers), "valid_speakers": len(means),
                "complete_speakers": sum(row["valid_cases"] == row["planned_cases"] for row in speaker_rows),
                "status_counts": dict(Counter(row["status"] for row in selected)),
                "speaker_macro_mean": float(np.mean(means)) if means else None,
                "utterance_micro": stats(valid), "speaker_rows": speaker_rows,
                "sum_over_available_cases": sum(valid) if unit == "count" and valid else None,
            }
        pairs = []
        for case in entries:
            a, b = (by_method[method].get(case["id"], {}) for method in METHODS)
            usable = a.get("value_status") == b.get("value_status") == "measured"
            pairs.append({"case": case["id"], "speaker": case["speaker"], "status": "paired" if usable else "missing",
                          "value": b["value"] - a["value"] if usable else None})
        paired_speakers = []
        for speaker in speakers:
            values = [row["value"] for row in pairs if row["speaker"] == speaker and row["status"] == "paired"]
            paired_speakers.append({"speaker": speaker, "planned_cases": expected[speaker],
                                   "paired_cases": len(values), **stats(values)})
        means = [row["mean"] for row in paired_speakers if row["mean"] is not None]
        summary["paired_world_harvest_minus_hnm"] = {
            "planned_cases": len(entries), "paired_cases": sum(row["status"] == "paired" for row in pairs),
            "planned_speakers": len(speakers), "paired_speakers": len(means),
            "complete_speakers": sum(row["paired_cases"] == row["planned_cases"] for row in paired_speakers),
            "speaker_macro_mean": float(np.mean(means)) if means else None,
            "speaker_rows": paired_speakers, "case_rows": pairs,
        }
        summaries.append(summary)
    return summaries


def main():
    parser = LoggedArgumentParser(description="追加評価の予定分母と話者単位の比較を保存する")
    parser.add_argument("--assessment-results", type=Path, required=True, action="extend", nargs="+")
    parser.add_argument("--assessment-manifest", type=Path, required=True)
    parser.add_argument("--serialized-size", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/clean_speech_v1.json")
    args = parser.parse_args()
    started = time.perf_counter()
    reports = [read_json(path) for path in args.assessment_results]
    report = {"rows": [row for data in reports for row in data["rows"]]}
    identifiers = [row["spec"]["id"] for row in report["rows"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("統合する結果に同じjobが複数あります")
    report["counts"] = dict(Counter(row["status"] for row in report["rows"]))
    manifest_path = args.assessment_manifest
    manifest = read_json(manifest_path)
    planned = {job["id"]: job for job in manifest["jobs"]}
    if not set(identifiers).issubset(planned):
        raise ValueError("結果に全件manifestへ登録されていないjobがあります")
    for data in reports:
        for row in data["rows"]:
            measured = spec_identity(row["spec"], data.get("input_sha256"))
            if measured != spec_identity(planned[row["spec"]["id"]]):
                raise ValueError("結果と全件manifestの測定条件・品質証跡内容が一致しません")
    if any(data["baseline_method"] != "hnm" for data in reports):
        raise ValueError("比較基準がHNM以外の結果を統合できません")
    if any(data["source_sha256"] != reports[0]["source_sha256"] for data in reports):
        raise ValueError("異なる指標実装の結果を統合できません")
    sizes = read_json(args.serialized_size)
    entries = read_json(args.dataset)["entries"]
    if len(entries) != 120 or len({row["speaker"] for row in entries}) != 40:
        raise ValueError("固定40話者120発話の集計専用です")
    rows = extract(report, manifest, sizes, entries)
    groups = summarize(rows, entries)
    sources = [*args.assessment_results, manifest_path, args.serialized_size, args.dataset, Path(__file__)]
    summary = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "baseline_method": "hnm", "planned_cases": len(entries), "planned_speakers": 40,
               "source_sha256": {str(path.resolve()): digest(path) for path in sources},
               "planned_jobs": len(manifest["jobs"]), "completed_job_rows": len(report["rows"]),
               "assessment_status_counts": report["counts"], "result_shards": len(reports), "groups": groups,
               "metric_repetitions": sorted({data["repetitions"] for data in reports}),
               "metric_source_sha256": reports[0]["source_sha256"],
               "evidence_equivalence": "品質証跡のみ、保存先が異なっても実ファイルSHA256一致なら同一。その他のjob条件は完全一致。",
               "wall_seconds": time.perf_counter() - started,
               "aggregation": "発話の初回値→話者内有効発話平均→話者等重み平均。差は同一発話WORLD−HNMを先に計算。",
               "missing_policy": "予定120発話・40話者を固定。欠測はnull。有効数/対可能数/完全話者数を併記。",
               "scope": "時間反復やフレームを独立標本としない。信頼区間・有意差・総合順位は算出していない。"
                        "statusは元状態、value_statusは当該セルの取得可否。部分曲線の有効な品質点と欠測点は分ける。"}
    args.output.mkdir(parents=True, exist_ok=False)
    save_json(args.output / "summary.json", summary)
    save_json(args.output / "scalar-rows.json", {"schema_version": 1, "rows": rows})
    logging.info("話者単位の追加評価集計を保存しました: %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli(main, "added-metrics-assessment-summary"))
