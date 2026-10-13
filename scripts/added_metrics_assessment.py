"""固定120発話の保存波形から追加評価入力と実保存量を作る。指標式は変更しない。

実行例（実測入力の作成。開発確認では実行しない）:
  PYTHONPATH=. uv run --locked python scripts/added_metrics_assessment.py \
    --run-root runs/added-metrics-20261014 --output runs/added-assessment-inputs \
    --decoder-revision bbc9e70 --quality-evidence-index runs/quality/quality-evidence-index.json

生成manifestは既存の python -m vocoderbench.assessment へ渡す。
実保存量は1条件だけの記述的測定であり、PR30の表現量曲線とは区別する。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
import time

from vocoderbench.assessment.common import Inputs, digest, read_json, save_json
from vocoderbench.logging_utils import LoggedArgumentParser, configure_logging, run_cli

METHODS = ("hnm", "world_harvest")
CONDITIONS = ("unedited", "pitch_minus3", "pitch_plus3", "gain_minus6", "gain_plus6")
QUALITY = ["predicted_mos", "speaker_similarity"]
METRICS = ("auditory_local", "pitch_tracking", "gain_tracking", "interference", "quality_curve")
ROOT = Path(__file__).resolve().parents[1]
SCOPE = (
    "固定LibriSpeech英語40話者120発話・16 kHz・各方式seed 0。HNM現ベースとWORLD。"
    "局所ERBは40 ms窓・5 ms hop・32帯域で、PR27の20 ms ERBとは別定義。"
    "ピッチ±300 cent、ゲイン±6 dBの定常操作のみ。制御参照は各方式の無編集復号音。"
    "動的操作・絶対F0真値・知覚品質の優劣・使用可能な編集幅へ一般化しない。"
    "干渉はゲイン操作1列のみ。理想一様振幅スケールの不変性を期待値にし、"
    "知覚的独立性の正解とはしない。ピッチ操作の非対角期待応答は未校正。"
    "品質証跡は別工程のUTMOSv2と固定原音参照のECAPA。欠測はnull/partialのまま残す。"
    "実保存量は公開saveの圧縮NPZ全体の1点で、理論情報率や品質–表現量曲線ではない。"
)


def collect_indexes(paths):
    by_audio, records = defaultdict(list), []
    for path in paths:
        path = path.resolve()
        record = {"path": str(path), "sha256": None, "status": "unavailable"}
        try:
            record["sha256"] = digest(path)
            index = read_json(path)
            for point in index["points"]:
                audio = (path.parent / point["audio_path"]).resolve()
                by_audio[str(audio)].append((path, point))
            record.update(status="ok", points=len(index["points"]))
        except Exception as error:
            logging.exception("品質証跡一覧を読めません: %s", path)
            record["reason"] = f"{type(error).__name__}: {error}"
        records.append(record)
    return by_audio, records


def merge_evidence(audio, destination, candidates, provenance):
    """同一実ファイルとhashで対応を固定。異なる評価器を一つの証跡へ束ねる。"""
    scores, sources, errors, conflicts = {}, [], [], set()
    try:
        audio_hash = digest(audio)
    except Exception as error:
        logging.exception("品質証跡の対象波形を読めません: %s", audio)
        provenance.append({"output": str(audio), "status": "unavailable", "reason": str(error)})
        return None
    for index_path, point in candidates:
        evidence_path = (index_path.parent / point["quality_evidence"]).resolve()
        try:
            data = read_json(evidence_path)
            if (data.get("case"), data.get("method")) != (point["case"], point["method"]):
                raise ValueError("品質証跡と一覧のcase/methodが一致しません")
            if not (point.get("audio_sha256") == data.get("audio_sha256") == audio_hash):
                raise ValueError("音声・一覧・品質証跡のSHA256が一致しません")
            if (index_path.parent / data["audio_path"]).resolve() != audio:
                raise ValueError("品質証跡の実ファイルパスが一致しません")
            source = {"index": str(index_path), "evidence": str(evidence_path),
                      "evidence_sha256": digest(evidence_path), "case": point["case"], "method": point["method"]}
            sources.append(source)
            for metric, score in data.get("scores", {}).items():
                if metric not in QUALITY:
                    continue
                item = dict(score)
                if item.get("source_result"):
                    source_result = (evidence_path.parent / item["source_result"]).resolve()
                    item["source_result"] = str(source_result)
                    item["source_result_sha256"] = digest(source_result)
                # 同一評価器を複数実行した値は、都合のよい一方を選ばない。
                if metric in scores and scores[metric] != item:
                    conflicts.add(metric)
                    raise ValueError(f"同一音声の{metric}に重複する異なる証跡があります")
                scores[metric] = item
        except Exception as error:
            logging.exception("品質証跡を採用できません: %s", evidence_path)
            errors.append({"path": str(evidence_path), "reason": f"{type(error).__name__}: {error}"})
    for metric in conflicts:
        scores.pop(metric, None)
    record = {"output": str(audio), "audio_sha256": audio_hash, "sources": sources,
              "errors": errors, "missing_metrics": [key for key in QUALITY if key not in scores]}
    record["status"] = "ok" if not record["missing_metrics"] else "partial"
    provenance.append(record)
    if not scores:
        return None
    save_json(destination, {"schema_version": 1, "audio_sha256": audio_hash, "audio_path": str(audio),
                            "scores": scores, "sources": sources, "merge_errors": errors})
    return str(destination)


def make_jobs(entries, run_root, output, indexes, metrics):
    jobs, evidence_records = [], []
    evidence_folder = output / "quality-evidence"
    if "quality_curve" in metrics:
        evidence_folder.mkdir()
    for case in entries:
        identifier = case["id"]
        original = {"path": str(run_root / "audio" / identifier / "original.npy"), "sample_rate": 16000}
        for method in METHODS:
            folder = run_root / "audio" / identifier / method
            audio = {condition: {"path": str(folder / f"{condition}.npy"), "sample_rate": 16000}
                     for condition in CONDITIONS}
            common = {"case": identifier, "method": method, "seed": 0, "speaker": case["speaker"],
                      "language": case["language"], "style": case["style"], "kind": "speech"}

            def add(metric, condition, **params):
                if metric in metrics:
                    jobs.append({**common, "id": f"{identifier}__{method}__{metric}__{condition}",
                                 "metric": metric, "condition": condition, **params})

            add("auditory_local", "unedited", reference=original, output=audio["unedited"])
            controls = (("pitch_tracking", "pitch_minus3", "target_cents", -300),
                        ("pitch_tracking", "pitch_plus3", "target_cents", 300),
                        ("gain_tracking", "gain_minus6", "target_gain_db", -6),
                        ("gain_tracking", "gain_plus6", "target_gain_db", 6))
            for metric, condition, target, amount in controls:
                add(metric, condition, reference=audio["unedited"], output=audio[condition], **{target: amount})
            add("interference", "gain_central_difference", low_hz=300, high_hz=5000,
                attribute_scales={"pitch_cents": 100, "level_db": 1,
                                  "slope_db_per_octave": 1, "duration_seconds": .01},
                expected_response_basis="理想一様ゲインの不変性。尺度は表示用工学単位で知覚閾値ではない。",
                sweeps=[{"control": "gain", "control_unit": "dB", "delta": 6, "control_scale": 1,
                         "minus": audio["gain_minus6"], "plus": audio["gain_plus6"],
                         "expected_response": {"pitch_cents": 0, "level_db": 1,
                                               "slope_db_per_octave": 0, "duration_seconds": 0}}])
            if "quality_curve" not in metrics:
                continue
            sidecars = {}
            for condition in CONDITIONS:
                path = Path(audio[condition]["path"])
                sidecars[condition] = merge_evidence(
                    path, evidence_folder / f"{identifier}__{method}__{condition}.json",
                    indexes.get(str(path), []), evidence_records)
            for control, unit, amounts, conditions in (
                ("pitch", "cent", [-300, 0, 300], ["pitch_minus3", "unedited", "pitch_plus3"]),
                ("gain", "dB", [-6, 0, 6], ["gain_minus6", "unedited", "gain_plus6"]),
            ):
                points = [{"amount": amount, "output": audio[condition],
                           **({"quality_evidence": sidecars[condition]} if sidecars[condition] else {})}
                          for amount, condition in zip(amounts, conditions, strict=True)]
                add("quality_curve", f"{control}_three_points", reference=audio["unedited"],
                    control=control, control_unit=unit, points=points, quality_metrics=QUALITY)
    return jobs, evidence_records


def measure_saved_bytes(entries, run_root, revision):
    """実ファイルの保存量1点。別の量子化条件や符号化条件を捏造しない。"""
    rows, inputs = [], Inputs(run_root)
    for case in entries:
        for method in METHODS:
            start, cpu = time.perf_counter(), time.process_time()
            folder = run_root / "audio" / case["id"] / method
            artifact = folder / "representation.npz"
            row = {"case": case["id"], "speaker": case["speaker"], "method": method, "seed": 0,
                   "condition": "native_compressed_npz", "status": "unavailable", "value": None,
                   "unit": "bit/s", "serialized_bytes": None, "serialized_bits_per_second": None,
                   "rate_denominator_seconds": None, "artifact": str(artifact), "artifact_sha256": None,
                   "decoder_revision": revision, "curve_status": "not_measured",
                   "curve_reason": "同一方式の実表現条件は1点。PR30曲線に必要な2条件以上がない。"}
            try:
                original_path = run_root / "audio" / case["id"] / "original.npy"
                original, rate = inputs.audio({"path": str(original_path), "sample_rate": 16000})
                unedited = folder / "unedited.npy"
                inputs.audio({"path": str(unedited), "sample_rate": 16000})
                artifact_path = inputs.path(str(artifact))
                size, duration = artifact_path.stat().st_size, len(original) / rate
                if size <= 0:
                    raise ValueError("空の表現ファイルは測定できません")
                synthesis_path = folder / "synthesis.json"
                synthesis = read_json(synthesis_path)
                if synthesis.get("representation", {}).get("sha256") != inputs.hashes[str(artifact)]:
                    raise ValueError("合成記録と実表現ファイルのSHA256が一致しません")
                if synthesis.get("outputs", {}).get("unedited", {}).get("audio", {}).get("file_sha256") != inputs.hashes[str(unedited)]:
                    raise ValueError("合成記録と無編集復号音のSHA256が一致しません")
                row.update(status="ok", value=8 * size / duration, serialized_bytes=size,
                           serialized_bits_per_second=8 * size / duration, rate_denominator_seconds=duration,
                           artifact_sha256=inputs.hashes[str(artifact)],
                           original_sha256=inputs.hashes[str(original_path)],
                           unedited_sha256=inputs.hashes[str(unedited)], synthesis_record=str(synthesis_path),
                           synthesis_record_sha256=digest(synthesis_path), synthesis_status=synthesis.get("status"))
            except Exception as error:
                logging.exception("実保存量の測定に失敗: %s %s", case["id"], method)
                row.update(status="unavailable" if isinstance(error, (FileNotFoundError, ImportError)) else "failed",
                           reason=f"{type(error).__name__}: {error}")
            row.update(wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu)
            rows.append(row)
    return {"schema_version": 1, "baseline_method": "hnm", "rows": rows, "input_sha256": inputs.hashes,
            "planned_rows": len(entries) * len(METHODS), "counts": dict(Counter(row["status"] for row in rows)),
            "byte_scope": "公開saveが保存した圧縮NPZ実ファイル全体。ZIP/NPYヘッダーとJSONメタデータ込み。",
            "not_included": "デコーダープログラム・共有ライブラリの配布サイズ。通信路符号化や量子化研究ではない。",
            "decode_correspondence": "別工程の合成記録による宣言。ここでは保存表現を再decodeしない。",
            "timing_scope": "実ファイル読み取り・SHA256・bytes測定。encode/decode/品質推論を含まない。"}


def aggregation_contract(entries):
    return {
        "population": {"cases": len(entries), "speakers": len({r["speaker"] for r in entries}),
                       "methods": list(METHODS), "repetitions_are_independent_samples": False},
        "group_keys": ["metric", "condition", "method", "scalar_name", "unit"],
        "scalar_order": "各発話で初回結果の指標値→同じ話者内の有効発話平均→話者等重み平均。",
        "paired_difference": "同じcase/condition/seedのWORLD−HNM。有効な対だけで話者内平均→話者等重み平均。",
        "denominators": "予定発話120、実測有効発話、対比較可能発話、予定話者40、有効話者と全status件数を並記。",
        "missing": "欠測/部分測定/対象外/失敗は元状態とnullを保持。0補完しない。品質曲線は各証跡点の状態で判断。",
        "auditory_local": ["value (dB)", "local_frame_rmse.abs_p95 (dB)",
                           "reference_active_cells / total_band_frame_cells"],
        "pitch_tracking": ["value (cent)", "relative_error.abs_p95 (cent)", "relative_error.count",
                           "expected_voiced_frames", "missing_voiced_frames", "false_voiced_frames",
                           "expected_unvoiced_frames", "unmapped_frames", "out_of_range_frames",
                           "gross_error_over_600_cents", "octave_error_frames", "total_frames"],
        "gain_tracking": ["value (dB)", "errors.abs_p95 (dB)", "errors.count", "reference_silent_frames",
                          "silent_output_frames", "output_peak", "over_one_fraction", "total_frames"],
        "interference": "gain列の属性ごとresponseとnormalized_errorを別々に集計。行列全体を総合点にしない。",
        "quality_curve": "control/amount/metricを分離。絶対値と同じ発話の無編集値との差を別々に集計。",
        "serialized_size": "実bytes/原音秒を方式ごとに集計。理論パラメータbit率とも表現量曲線とも別。",
        "uncertainty": "実装する場合は話者単位の再標本化。発話フレームや時間反復を独立標本数にしない。",
    }


def main():
    parser = LoggedArgumentParser(description="固定音声の追加評価入力と実保存量1点を作成する")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/clean_speech_v1.json")
    parser.add_argument("--decoder-revision", required=True)
    parser.add_argument("--metrics", nargs="+", choices=METRICS, default=list(METRICS))
    parser.add_argument("--quality-evidence-index", type=Path, action="append", default=[])
    parser.add_argument("--synthesis-record", type=Path, action="append", default=[])
    args = parser.parse_args()
    start, cpu = time.perf_counter(), time.process_time()
    run_root, output = args.run_root.resolve(), args.output.resolve()
    dataset = read_json(args.dataset)
    entries = dataset["entries"]
    if len(entries) != 120 or len({case["speaker"] for case in entries}) != 40:
        raise ValueError("この実測は凍結した40話者120発話専用です")
    if any(case["sample_rate"] != 16000 for case in entries):
        raise ValueError("固定集合は16 kHzのまま使用します")
    output.mkdir(parents=True, exist_ok=False)
    indexes, index_records = collect_indexes(args.quality_evidence_index) if "quality_curve" in args.metrics else ({}, [])
    jobs, evidence = make_jobs(entries, run_root, output, indexes, set(args.metrics))
    manifest = {"schema_version": 1, "baseline_method": "hnm", "scope": SCOPE, "jobs": jobs}
    save_json(output / "manifest.json", manifest)
    shards = []
    for offset in range(0, len(entries), 10):
        cases = {case["id"] for case in entries[offset:offset + 10]}
        selected = [job for job in jobs if job["case"] in cases]
        path = output / f"manifest-{offset // 10:02d}.json"
        save_json(path, {**manifest, "jobs": selected})
        shards.append({"path": str(path), "sha256": digest(path), "cases": len(cases), "jobs": len(selected)})
    save_json(output / "serialized-size.json", measure_saved_bytes(entries, run_root, args.decoder_revision))
    save_json(output / "aggregation-contract.json", aggregation_contract(entries))
    source_paths = [Path(__file__), ROOT / "vocoderbench/world.py", ROOT / "BASELINE.json",
                    *sorted((ROOT / "vocoderbench").glob("hnm*.py"))]
    metadata = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "dataset": str(args.dataset.resolve()), "dataset_sha256": digest(args.dataset),
                "formal_base": read_json(ROOT / "BASELINE.json"), "decoder_revision": args.decoder_revision,
                "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in source_paths},
                "synthesis_records": [{"path": str(path.resolve()), "sha256": digest(path)}
                                      for path in args.synthesis_record],
                "planned_jobs": len(jobs), "planned_by_metric": dict(Counter(j["metric"] for j in jobs)),
                "selected_metrics": list(dict.fromkeys(args.metrics)),
                "shards": shards, "sharding_scope": "実行単位10発話。話者統計は全120発話を統合してから行う。",
                "quality_indexes": index_records, "quality_evidence_resolution": evidence,
                "wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu,
                "scope": SCOPE}
    save_json(output / "preparation.json", metadata)
    logging.info("追加評価入力を保存しました: %s (%s件)", output, len(jobs))
    for handler in logging.getLogger().handlers:
        handler.flush()
    log = configure_logging("added-metrics-assessment")
    shutil.copy2(log, output / "run.log")
    save_json(output / "run-log.json", {"source_sha256": digest(output / "run.log"),
                                        "text": (output / "run.log").read_text(encoding="utf-8")})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli(main, "added-metrics-assessment"))
