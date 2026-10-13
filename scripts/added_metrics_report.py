"""完了済みの固定追加指標だけを日本語本番HTML/JSONへ保存する。再計測・テスト・Pages生成はしない。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli  # noqa: E402
from added_metrics_report_data import (  # noqa: E402
    CONDITIONS, LABELS, METHODS, comparison_rows, coverage, playback_headroom, quality_summary, summarize, synthesis_rows, timings,
)
from added_metrics_report_html import render  # noqa: E402
from added_metrics_report_sources import (  # noqa: E402
    collect_audio, digest, export_sources, public_name, read, sanitize, save,
)

DEFAULT_RUN = ROOT / "runs/added-metrics-20261014"
DEFAULT_OUTPUT = ROOT / "experiments/2026-10-14/added-quality-control-metrics/results/run-001"
HISTORY = ROOT / "experiments/2026-10-13/formal-hnm-v3-references/results/run-001"


def load_batches(run, pattern, count, expected_rows):
    paths = sorted(run.glob(pattern))
    if len(paths) != count:
        raise ValueError(f"最終報告には全{count}分割の保存済み結果が必要です: {pattern} ({len(paths)})")
    reports = [read(path) for path in paths]
    rows = [row for report in reports for row in report["rows"]]
    if len(rows) != expected_rows:
        raise ValueError(f"予定{expected_rows}行の完了前には最終報告しません: {pattern} ({len(rows)})")
    return reports, rows


def completed_inputs(run, assessment_path, asr_path, dataset):
    entries = dataset["entries"]
    if len(entries) != 120 or len({e["speaker"] for e in entries}) != 40:
        raise ValueError("固定120録音40話者専用です")
    synthesis = [read(run / "audio" / e["id"] / m / "synthesis.json") for e in entries for m in METHODS]
    if any(r.get("status") != "measured" or any(r["outputs"].get(c, {}).get("status") != "measured"
                                               for c in CONDITIONS) for r in synthesis):
        raise ValueError("1200出力の合成が完了していません")
    mos_reports, mos = load_batches(run, "mos/batch-*/results.json", 12, 1320)
    ecapa_reports, ecapa = load_batches(run, "quality/ecapa-*/results.json", 12, 1200)
    erb_reports, erb = load_batches(run, "quality/erb-*/results.json", 12, 240)
    scoreq_reports, scoreq = [], []
    if any((run / "quality").glob("scoreq-*")):
        scoreq_reports, scoreq = load_batches(run, "quality/scoreq-[0-9][0-9]/results.json", 12, 240)
        expected = {(entry["id"], method) for entry in entries for method in METHODS}
        if {(row["case"], row["method"]) for row in scoreq} != expected:
            raise ValueError("SCOREQの保存結果が固定120録音×2方式に一致しません")
        if any(row.get("metric") != "scoreq" for row in scoreq):
            raise ValueError("SCOREQの結果に別の指標が混入しています")
    acoustic_reports, acoustic = load_batches(run, "assessment-acoustic-[0-9][0-9]/results.json", 12, 1440)
    curve_reports, curves = load_batches(run, "assessment-curves-[0-9][0-9]/results.json", 12, 480)
    if any(r.get("status") == "pending" for r in acoustic + curves + ecapa + erb + scoreq):
        raise ValueError("処理中の行を完成結果へ変えません")
    if any(report["configuration"] != mos_reports[0]["configuration"] for report in mos_reports):
        raise ValueError("MOS分割間の科学設定が不一致です")
    equivalence = read(run / "preparation/mos-scientific-equivalence.json")
    if not equivalence["scientific_configuration_identical"]:
        raise ValueError("MOSの科学設定同一性が確定していません")
    origins = Counter(r["origin"] for r in mos)
    if origins != {"reused_previous_same_float32_audio": 360, "new_inference": 960}:
        raise ValueError("今回の引用360／新規960の範囲と保存結果が一致しません")
    assessment, asr = read(assessment_path), read(asr_path)
    if assessment["completed_job_rows"] != 1920 or assessment["planned_jobs"] != 1920:
        raise ValueError("1920 jobの集計を保存してから報告してください")
    if sum(asr["assessment_counts"].values()) != 110 or sum(asr["recognition_counts"].values()) != 165:
        raise ValueError("ASRの165推論・110 jobの保存が不足しています")
    return {"synthesis": synthesis, "mos": mos, "mos_configuration": mos_reports[0]["configuration"],
            "quality_reports": ecapa_reports + erb_reports + scoreq_reports, "quality_rows": ecapa + erb + scoreq,
            "scoreq_rows": scoreq,
            "assessment_reports": acoustic_reports + curve_reports, "assessment_rows": acoustic + curves,
            "assessment": assessment, "asr": asr,
            "serialized_size": read(run / "assessment-acoustic-inputs/serialized-size.json")}


def evidence_links(provenance):
    links = []
    important = {"synthesis-contract.json": "合成条件・実装hash・依存環境",
                 "synthesis-execution.json": "合成の開始／完了・予定数",
                 "ecapa-processes.json": "ECAPAの分割実行・再開履歴",
                 "mos-processes.json": "MOSの分割実行・再開履歴",
                 "erb-processes.json": "ERBの分割実行・再開履歴",
                 "scoreq-processes.json": "SCOREQの分割実行・再開履歴",
                 "preparation/mos-scientific-equivalence.json": "MOS再利用の全科学設定照合",
                 "preparation/synthesis-prior-file-hash-ledger.json": "旧無編集音声のファイルhash照合・旧比較項目の訂正",
                 "preparation/scoreq-official-download.json": "SCOREQ公式モデル取得の失敗",
                 "preparation/scoreq-retry-002.json": "SCOREQ取得再試行の失敗",
                 "preparation/scoreq-final-availability.json": "SCOREQ公式再取得の最終状態・実モデルhash",
                 "asr/configuration.json": "ASR固定モデル・重みhash・正規化・入力対象",
                 "quality/ecapa-00/results.json": "ECAPAの実モデルhash・初期化・初回と反復",
                 "quality/erb-00/results.json": "20 ms ERBの定義・初回と反復",
                 "quality/scoreq-00/results.json": "SCOREQ natural/refの実モデルhash・初期化・初回と反復",
                 "mos/batch-00/contract.json": "UTMOSv2固定重み・fold・実行環境"}
    public = {item["public_json"] for item in provenance["files"] if item.get("public_json")}
    for source, label in important.items():
        name = public_name(Path(source))
        if name in public:
            links.append({"path": name, "label": label})
    return links


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/clean_speech_v1.json")
    parser.add_argument("--assessment-summary", type=Path)
    parser.add_argument("--asr-summary", type=Path)
    args = parser.parse_args()
    run, output = args.run_root.resolve(), args.output.resolve()
    if output != DEFAULT_OUTPUT:
        raise ValueError("この完成報告の保存先は指定済みrun-001だけです")
    if output.exists():
        raise FileExistsError("保存済みの結果は上書きしません")
    assessment_path = args.assessment_summary or run / "assessment-summary/summary.json"
    asr_path = args.asr_summary or run / "asr/summary.json"
    dataset = read(args.dataset)
    inputs = completed_inputs(run, assessment_path, asr_path, dataset)
    summary = quality_summary(inputs["mos"], inputs["quality_rows"], dataset["entries"])
    scoreq_rows = inputs["scoreq_rows"]
    scoreq_attempted = bool(scoreq_rows)
    if not scoreq_attempted:
        scoreq_rows = [{"case": entry["id"], "speaker": entry["speaker"], "method": method,
                       "metric": "scoreq", "condition": "unedited", "value": None, "status": "unavailable",
                       "evaluation_attempted": False,
                       "reason": "SCOREQ推論結果未保存。公式取得失敗・再取得の最終状態は取得記録へ。代用値なし。",
                       "acquisition_evidence": "raw--preparation--scoreq-official-download.json"}
                      for entry in dataset["entries"] for method in METHODS]
        summary.append({"metric": "scoreq", "condition": "unedited", "evaluation_attempted": False,
                        **summarize(scoreq_rows, dataset["entries"])})
    scoreq_group = next(group for group in summary if group["metric"] == "scoreq")
    scoreq_measured = sum(item["valid_cases"] for item in scoreq_group["methods"].values())
    scoreq_state = {"planned_rows": 240, "measured_rows": scoreq_measured,
                    "evaluation_attempted": scoreq_attempted,
                    "status": "measured" if scoreq_measured == 240 else "partial" if scoreq_measured else "unavailable",
                    "status_counts": dict(Counter(row["status"] for row in scoreq_rows)),
                    "status_rows": "scoreq-status.json",
                    "scope": "無編集再合成だけのnatural/ref距離。保存済み初回値を使用。"
                             "推論なしの行は予定分母の明示であり測定値ではない。欠測をゼロにしない。"}
    rows, sizes = synthesis_rows(inputs["synthesis"], dataset["entries"], inputs["serialized_size"])
    historical = read(HISTORY / "results.json")
    historical_summary = read(HISTORY / "summary.json")
    generated = datetime.now(timezone.utc).isoformat()
    timing = timings(inputs["mos"], inputs["quality_reports"], inputs["synthesis"], inputs["asr"], inputs["assessment"])
    initialization = [{"source": str(p.relative_to(ROOT)), **read(p)}
                      for p in sorted(run.glob("mos/batch-*/initialization.json"))]
    timing["mos"]["initialization"] = initialization
    timing["mos"]["initialization_recorded_seconds"] = sum(r["seconds"] for r in initialization)
    execution = read(run / "synthesis-execution.json")
    timing["synthesis"]["execution"] = execution
    timing["synthesis"]["elapsed_wall_seconds"] = (
        datetime.fromisoformat(execution["finished_at_utc"]) - datetime.fromisoformat(execution["started_at_utc"])).total_seconds()
    timing["assessment"] = {"initialization_scope": "assessment本体は学習モデルを初期化しない。品質点は保存済み証跡。",
        "first_wall_seconds": sum(r.get("timing", {}).get("first_wall_seconds", 0) or 0 for r in inputs["assessment_rows"]),
        "repeat_wall_seconds": sum(r.get("timing", {}).get("warm_median_seconds", 0) or 0 for r in inputs["assessment_rows"]),
        "repetitions": 1}
    payload = {"schema_version": 6, "study_role": "added_quality_control_metrics", "generated_at": generated,
        "formal_base": read(run / "synthesis-contract.json")["formal_base"], "comparison_reference": "hnm",
        "method_labels": LABELS, "index_methods": ["identity", *METHODS], "selected_methods": list(METHODS),
        "planned_cases": 120, "planned_speakers": 40, "planned_outputs": 1200, "planned_assessment_jobs": 1920,
        "scope": "固定LibriSpeech英語・16 kHzの120録音40話者。追加品質・限定制御の記述的実測。独立最終評価と人間校正なし。",
        "resynthesis": [r for r in rows if r["condition"] == "unedited"],
        "operations": [r for r in rows if r["condition"] != "unedited"],
        "quality_summary": summary, "assessment_summary": inputs["assessment"], "asr_summary": inputs["asr"],
        "comparison_summary": comparison_rows(summary, inputs["assessment"], sizes),
        "serialized_size": sizes, "timing_summary": timing, "playback_headroom": playback_headroom(rows),
        "coverage": coverage(summary, inputs["assessment"], inputs["asr"], sizes, inputs["assessment_rows"]),
        "scoreq_status": scoreq_state,
        "historical_reference": {"source": str((HISTORY / "results.json").relative_to(ROOT)),
            "source_sha256": digest(HISTORY / "results.json"), "source_json_link": os.path.relpath(HISTORY / "results.json", output),
            "generated_at": historical["generated_at"],
            "method_labels": historical["method_labels"], "summary": historical_summary["全体"],
            "scope": "2026-10-13の過去8方式の歴史値。残6方式は今回の追加指標未測定。"},
        "interpretation": {"overall_ranking": "not_computed", "human_calibration": "not_available",
            "independent_final_evaluation": "not_available", "native_48khz_recordings": "not_evaluated",
            "correlated_diagnostics": ["erb_20ms", "auditory_local_40ms"],
            "averaging": "各発話初回値→話者内有効発話平均→話者等重み。WORLD−HNMは同一発話の差を先に計算。",
            "missing_policy": "欠測・部分・対象外・失敗はnullと理由を保持。ゼロ補完しない。",
            "representation": "実圧縮NPZ全体の1点。理論情報率または品質–表現量曲線ではない。"},
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "scripts").glob("added_metrics_report*.py"))}}
    audio = collect_audio(run, dataset)
    output.mkdir(parents=True, exist_ok=False)
    extras = {"dataset-manifest": args.dataset, "historical-summary": HISTORY / "summary.json", "assessment-speaker-summary": assessment_path,
              "asr-summary": asr_path}
    provenance = export_sources(run, output, output.parents[1] / "archives", extras)
    payload["evidence_links"] = evidence_links(provenance)
    payload["provenance_index"] = "provenance-index.json"
    payload["source_file_count"] = provenance["source_files"]
    save(output / "quality-speaker-summary.json", {"aggregation": payload["interpretation"]["averaging"], "groups": summary})
    save(output / "serialized-size.json", sizes)
    save(output / "scoreq-status.json", sanitize({**scoreq_state, "rows": scoreq_rows}))
    if not scoreq_attempted:
        save(output / "unmeasured-scoreq.json", {**scoreq_state, "rows": scoreq_rows})
    save(output / "execution-summary.json", sanitize(timing))
    save(output / "audio_samples.json", audio)
    save(output / "results.json", sanitize(payload))
    (output / "index.html").write_text(render(sanitize(payload), audio), encoding="utf-8")
    logging.info("完成した本番の追加指標レポートを保存しました: %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli(main, "added-metrics-report"))
