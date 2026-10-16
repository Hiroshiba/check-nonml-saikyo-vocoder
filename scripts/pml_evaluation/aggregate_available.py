"""既存8方式の同じ支持集合に新PMLの完了指標だけ追加、話者等重み集約。"""

from pathlib import Path
import sys
import json
import gzip
import hashlib
import copy
import argparse
import vocoderbench

ROOT = Path("runs/pml-package-evaluation-20261016").resolve()
REPO = Path(vocoderbench.__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from all_metrics_rankings_core import matrix_summary, finite  # noqa: E402
from all_metrics_rankings_acoustic import descriptors, extract  # noqa: E402

METHOD = "pml_fwcep60_lowband_package_v1"
OLD = REPO / "research/all-method-final-2026-10-15"


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    global ROOT, OLD
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ROOT)
    parser.add_argument("--historical-root", type=Path, default=OLD)
    args = parser.parse_args()
    ROOT, OLD = args.run_root.resolve(), args.historical_root.resolve()
    previous = json.load(gzip.open(OLD / "results.json.gz"))
    oldrows = {}
    for p in sorted(OLD.glob("raw-values.part-*.json.gz")):
        for r in json.load(gzip.open(p))["records"]:
            if r["kind"] == "metric_recording":
                oldrows.setdefault(r["group_id"], []).append(r["row"])
    incoming = {}
    sources = {}
    for metric, identifier in [
        ("erb", "existing.erb20"),
        ("scoreq", "2.scoreq"),
        ("speaker_ecapa", "5.ecapa"),
        ("utmosv2", "1.native_mos"),
    ]:
        p = ROOT / "results" / metric / "summary.json"
        if p.exists():
            incoming[identifier] = read(p)["rows"]
            sources[str(p)] = sha(p)
    ap = ROOT / "results/acoustic/summary.json"
    if ap.exists():
        rows = read(ap)["rows"]
        sources[str(ap)] = sha(ap)
        for d in descriptors():
            incoming[d["id"]] = []
            for row in rows:
                value, status, detail = extract(row, d)
                incoming[d["id"]].append(
                    dict(
                        case=row["case"],
                        speaker=row["speaker"],
                        method=METHOD,
                        value=value,
                        status=status,
                        detail=detail,
                    )
                )
    asr = ROOT / "results/asr/summary.json"
    if asr.exists():
        rows = read(asr)["rows"]
        sources[str(asr)] = sha(asr)
        # Same mapping as all_metrics_rankings_extra.asr_groups.
        for key in ("cer", "wer"):
            group = []
            for row in rows:
                measured = row.get("measurement", {})
                score = measured.get("scores", {}).get(key, {})
                state = row["status"]
                if state in ("measured", "partial"):
                    state = score.get("status", "missing_metric_evidence")
                    if measured.get("reference_usable") is not True:
                        state = "reference_cer_gate_exceeded"
                value = score.get("delta") if state in ("measured", "ok") else None
                group.append(
                    dict(
                        case=row["case"],
                        speaker=row["speaker"],
                        method=METHOD,
                        status=state,
                        value=value,
                        denominator={
                            field: score.get(field)
                            for field in (
                                "truth_tokens",
                                "reference_errors",
                                "output_errors",
                            )
                        },
                        reference_rate=score.get("reference_rate"),
                        output_rate=score.get("output_rate"),
                    )
                )
            incoming["4.incremental_" + key] = group
    groups = []
    for g in previous["groups"]:
        if g["id"] not in incoming:
            continue
        newrows = incoming[g["id"]]
        members = list(previous["methods"]) + [METHOD]
        rows = copy.deepcopy(oldrows[g["id"]]) + newrows
        identities = [(r["method"], r["case"]) for r in rows]
        expected_cases = {c["id"] for c in read(ROOT / "input-contract.json")["cases"]}
        if len(identities) != len(set(identities)) or set(identities) != {
            (m, c) for m in members for c in expected_cases
        }:
            raise ValueError("Missing or duplicate method/case rows: " + g["id"])
        expected_speakers = {
            c["id"]: c["speaker"] for c in read(ROOT / "input-contract.json")["cases"]
        }
        if any(r["speaker"] != expected_speakers[r["case"]] for r in rows):
            raise ValueError("Speaker identity mismatch")
        valid = {
            m: {
                r["case"]
                for r in rows
                if r["method"] == m
                and r["status"] in ("measured", "ok")
                and finite(r["value"])
            }
            for m in members
        }
        cases = set.intersection(*(valid[m] for m in members))
        result = matrix_summary(rows, members, cases, g["direction"])
        groups.append(
            dict(
                id=g["id"],
                label=g["label"],
                family=g["family"],
                unit=g["unit"],
                direction=g["direction"],
                scope=g["scope"],
                primary=result,
                new_status_counts={
                    state: sum(r["status"] == state for r in newrows)
                    for state in sorted({r["status"] for r in newrows})
                },
                raw_rows=rows,
            )
        )
    output = dict(
        method=METHOD,
        formal_base="hnm-v3",
        adoption="pending",
        comparison="Historical eight + current PML; same fixed inputs/windows/evaluator per axis. Different timing runs are not ranked. Descriptive per-axis ranks only; no overall winner.",
        old_results_sha256=sha(OLD / "results.json.gz"),
        old_raw_sha256={
            p.name: sha(p) for p in sorted(OLD.glob("raw-values.part-*.json.gz"))
        },
        new_sources=sources,
        aggregation_source_sha256=sha(Path(__file__)),
        registry_source_sha256={
            str(p): sha(p)
            for p in [
                REPO / "scripts/all_metrics_rankings_core.py",
                REPO / "scripts/all_metrics_rankings_acoustic.py",
                REPO / "scripts/all_metrics_rankings_extra.py",
            ]
        },
        groups=groups,
    )
    (ROOT / "available-comparison.json").write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n"
    )
    print("Available axes", len(groups))


if __name__ == "__main__":
    main()
