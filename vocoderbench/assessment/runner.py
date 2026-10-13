"""13項目の追加評価CLI。評価の失敗・部分測定・初回と反復時間を保存する。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import html
import importlib
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import shutil
import time

from ..logging_utils import LoggedArgumentParser, configure_logging, run_cli
from .common import Inputs, NotApplicable, digest, integer, read_json, save_json

CATALOG = {
    "incremental_content": (4, "増分CER／WER", "acoustics", "content"),
    "auditory_local": (6, "聴覚帯域・局所構造", "acoustics", "auditory"),
    "pitch_tracking": (7, "ピッチ制御追従", "controls", "pitch"),
    "gain_tracking": (8, "振幅制御追従", "controls", "gain"),
    "local_time": (9, "局所時間制御", "controls", "local_time"),
    "timbre_tracking": (10, "スペクトル傾斜制御", "acoustics", "timbre"),
    "interference": (11, "制御間の干渉", "controls", "interference"),
    "quality_curve": (12, "編集量別の品質", "curves", "quality_curve"),
    "phoneme_abx": (14, "音素ABX", "representation", "abx"),
    "attribute_access": (15, "属性へのアクセス", "representation", "attribute_access"),
    "interpolation": (16, "特徴補間", "curves", "interpolation"),
    "robustness": (17, "不完全入力への頑健性", "curves", "robustness"),
    "information_rate": (18, "表現量・品質・制御", "curves", "information_rate"),
}


def attempt(function, job, inputs):
    start, cpu = time.perf_counter(), time.process_time()
    try:
        result = function(job, inputs)
        json.dumps(result, allow_nan=False)
    except NotApplicable as error:
        logging.warning("指標の対象外: %s: %s", job["id"], error, stack_info=True)
        result = {"status": "not_applicable", "value": None, "reason": str(error)}
    except (FileNotFoundError, ImportError) as error:
        logging.exception("入力または依存不足: %s", job["id"])
        result = {"status": "unavailable", "value": None, "reason": str(error)}
    except Exception as error:
        logging.exception("指標の計算失敗: %s", job["id"])
        result = {"status": "failed", "value": None, "reason": f"{type(error).__name__}: {error}"}
    if result["status"] != "ok":
        logging.warning("完全測定ではありません: %s: %s", job["id"], result.get("reason", result["status"]), stack_info=True)
    return {"wall_seconds": time.perf_counter()-start, "process_cpu_seconds": time.process_time()-cpu, "result": result}


def compare(rows, baseline):
    def key(row):
        job = row["spec"]
        return job["metric"], job["case"], job["condition"], job["seed"]
    references = {key(row): row for row in rows if row["spec"]["method"] == baseline}
    for row in rows:
        base = references.get(key(row))
        row["baseline_job"] = base["spec"]["id"] if base else None
        valid = base and base["status"] == row["status"] == "ok"
        a, b = (base["result"].get("value") if base else None), row["result"].get("value")
        same_unit = base and base["result"].get("unit") == row["result"].get("unit")
        row["delta_from_baseline"] = b-a if valid and same_unit and a is not None and b is not None else None


def render(report, path):
    def escape(value):
        return html.escape(str(value))
    def fmt(value):
        return "—" if value is None else f"{value:.6g}"
    body = []
    for row in report["rows"]:
        spec, result = row["spec"], row["result"]
        body.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in (
            CATALOG[spec["metric"]][1], spec["case"], spec["method"], spec["condition"], spec["seed"],
            row["status"], fmt(result.get("value")), result.get("unit", ""), fmt(row["delta_from_baseline"]),
            fmt(row["timing"]["first_wall_seconds"]), fmt(row["timing"]["warm_median_seconds"]))) + "</tr>")
    details = "".join(f"<details><summary>{escape(row['spec']['id'])}</summary><pre>"
                      f"{escape(json.dumps(row, ensure_ascii=False, indent=2))}</pre></details>" for row in report["rows"])
    page = """<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>方式非依存の内容・制御・特徴表現の追加指標</title><style>
:root{color-scheme:light dark}body{font-family:system-ui,sans-serif;max-width:1250px;margin:2rem auto;padding:0 1rem;line-height:1.6}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:.45rem;border:1px solid #888;text-align:left}
.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:1rem 0}a{color:inherit}
</style><h1>方式非依存の内容・制御・特徴表現の追加指標</h1>"""
    page += f"<h2>ベースと比較対象</h2><p>比較基準: <strong>{escape(report['baseline_method'])}</strong>。"
    page += "各方式・条件・seedを分離。総合点や方式採用判定は作りません。比較基準の行がない差は未測定です。</p>"
    page += "<div class=scroll><table><thead><tr>" + "".join(f"<th>{text}</th>" for text in (
        "指標", "ケース", "方式", "条件", "seed", "状態", "値", "単位", "ベースとの差", "初回 秒", "反復中央値 秒"))
    page += "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    page += f"<h2>確認範囲</h2><p>{escape(report['scope'])}</p><p>{escape(report['timing_scope'])}</p>"
    page += f"<p>状態別件数: {escape(report['counts'])}。欠測・対象外・部分測定を0にしません。</p>"
    page += "<p>波形・特徴・モデル推論の生成は別工程です。保存済み認識結果の集計時間をASR推論時間と表示しません。"
    page += "初回と反復を独立発話として数えません。話者・言語・発声様式は各行の詳細に保持します。</p>"
    page += "<p><a href='results.json'>全測定JSON</a> · <a href='manifest.json'>入力条件</a> · <a href='run-log.json'>実行ログ（JSON）</a></p>"
    page += "<h2>各行の生値・適用限界</h2>" + details + "</html>"
    path.write_text(page, encoding="utf-8")


def evaluate(manifest, output, repetitions):
    repetitions = integer(repetitions)
    if repetitions > 100:
        raise ValueError("反復は100回以下にしてください")
    log = configure_logging("assessment")
    source = Path(manifest).resolve()
    spec = read_json(source)
    if spec.get("schema_version") != 1 or not spec.get("baseline_method") or not spec.get("scope") or not spec.get("jobs"):
        raise ValueError("schema_version=1、比較基準、確認範囲、jobsが必要です")
    seen, combinations = set(), set()
    for job in spec["jobs"]:
        if job.get("metric") not in CATALOG or job.get("kind") not in ("speech", "artificial_probe"):
            raise ValueError("未対応の指標または入力種別です")
        for field in ("id", "case", "condition", "method", "speaker", "language", "style"):
            if not isinstance(job.get(field), str) or not job[field]:
                raise ValueError(f"空でない文字列が必要です: {field}")
        integer(job["seed"], 0)
        combination = (job["metric"], job["case"], job["condition"], job["method"], job["seed"])
        if job["id"] in seen or combination in combinations:
            raise ValueError("job IDまたは同じ測定条件が重複しています")
        seen.add(job["id"])
        combinations.add(combination)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / "manifest.json", spec)
    inputs = Inputs(source.parent)
    package = Path(__file__).parent
    report = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "baseline_method": spec["baseline_method"], "scope": spec["scope"], "repetitions": repetitions,
              "timing_scope": "共通import・起動は除外。指標importは初期化欄。各回に入力I/O・SHA256・原音解析・集計を含む。外部生成・モデル推論は含まない。",
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "numpy": importlib.metadata.version("numpy"), "scipy": importlib.metadata.version("scipy")},
              "manifest_sha256": digest(source), "source_sha256": {p.name: digest(p) for p in sorted(package.glob("*.py"))},
              "rows": [], "initialization": {}}
    for name in ("metrics.py", "logging_utils.py"):
        report["source_sha256"]["../"+name] = digest(package.parent/name)
    functions = {}
    for metric in dict.fromkeys(job["metric"] for job in spec["jobs"]):
        _, _, module, function = CATALOG[metric]
        start = time.perf_counter()
        try:
            functions[metric] = getattr(importlib.import_module("."+module, __package__), function)
            report["initialization"][metric] = {"status": "ok", "seconds": time.perf_counter()-start}
        except Exception as error:
            logging.exception("指標を読み込めません: %s", metric)
            report["initialization"][metric] = {"status": "unavailable", "seconds": time.perf_counter()-start, "reason": str(error)}
    for job in spec["jobs"]:
        function = functions.get(job["metric"])
        if function is None:
            result = {"status": "unavailable", "value": None, "reason": "指標モジュールを読み込めません"}
            runs = [{"wall_seconds": None, "process_cpu_seconds": None, "result": result}]
        else:
            runs = [attempt(function, job, inputs) for _ in range(repetitions+1)]
        result = runs[0]["result"]
        statuses = [run["result"]["status"] for run in runs]
        status = result["status"] if len(set(statuses)) == 1 else "inconsistent_repetitions"
        warm = [run["wall_seconds"] for run in runs[1:]]
        import numpy as np
        timing = {"first_wall_seconds": runs[0]["wall_seconds"], "first_cpu_seconds": runs[0]["process_cpu_seconds"],
                  "warm_median_seconds": float(np.median(warm)) if warm else None,
                  "warm_p95_seconds": float(np.percentile(warm, 95)) if warm else None,
                  "warm_min_seconds": min(warm) if warm else None, "warm_max_seconds": max(warm) if warm else None}
        report["rows"].append({"spec": job, "status": status, "result": result, "timing": timing, "runs": runs})
        report["input_sha256"] = inputs.hashes
        report["counts"] = dict(Counter(row["status"] for row in report["rows"]))
        compare(report["rows"], spec["baseline_method"])
        save_json(output / "results.json", report)
        render(report, output / "index.html")
    logging.info("測定終了: %s", report["counts"])
    for handler in logging.getLogger().handlers:
        handler.flush()
    shutil.copy2(log, output / "run.log")
    save_json(output / "run-log.json", {"source_name": "run.log",
              "source_sha256": digest(output / "run.log"),
              "text": (output / "run.log").read_text(encoding="utf-8")})
    return 0 if all(row["status"] == "ok" for row in report["rows"]) else 1


def main():
    parser = LoggedArgumentParser(description="方式非依存の内容・制御・特徴表現を追加評価する")
    parser.add_argument("--list-metrics", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.list_metrics:
        for key, (number, label, _, _) in CATALOG.items():
            print(f"{number:02d}\t{key}\t{label}")
        return 0
    if args.manifest is None or args.output is None:
        parser.error("--manifestと--outputが必要です")
    return evaluate(args.manifest, args.output, args.repetitions)


def cli():
    return run_cli(main, "assessment")
