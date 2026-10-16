"""Aggregate saved native timings on the historical fixed70 and main120 IDs."""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-summary", type=Path, required=True)
    parser.add_argument("--historical-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    native = json.loads(args.native_summary.read_text())
    with gzip.open(args.historical_results, "rt") as stream:
        historical = json.load(stream)
    indexed = {r["case"]: r for r in native["rows"]}
    assert len(indexed) == len(native["rows"]) == 120
    output = dict(
        method="pml_fwcep60_lowband_package_v1",
        additional_measurement=False,
        source_sha256={
            "native-summary.json": sha(args.native_summary),
            "historical-results.json.gz": sha(args.historical_results),
            "aggregate_timing_cohorts.py": sha(Path(__file__)),
        },
        native_contract_sha256=native["contract_sha256"],
        formulas=dict(
            speaker_equal_weight_rtf="mean over speakers(mean over recordings of wall_seconds / original_input_seconds)",
            recording_equal_weight_rtf="mean over recordings(wall_seconds / original_input_seconds)",
            duration_weighted_rtf="sum(wall_seconds) / sum(original_input_seconds)",
        ),
        display="Show analysis and decode separately for fixed70 and main120. Use speaker_equal_weight_rtf to match the historical display aggregation. Do not mix with the previously reported duration_weighted_rtf.",
        limitations=[
            "No cross-run speed rank or equality of host load is claimed.",
            "Single sequential native run, two threads, no warmup exclusion. Analysis includes first-use import costs, unlike excluded historical initialization.",
            "Save/load are separate and excluded. The same historical fixed70 identities do not certify identical timing conditions.",
        ],
        cohorts={},
    )
    for name, group_id, expected, speakers_expected in [
        ("fixed70", "speed.storage_policy70.analysis", 70, 24),
        ("main120", "speed.analysis", 120, 40),
    ]:
        group = next(g for g in historical["groups"] if g["id"] == group_id)
        ids = group["planned_case_ids"]
        assert len(ids) == len(set(ids)) == expected and set(ids) <= set(indexed)
        rows = []
        for case in ids:
            row = indexed[case]
            assert (
                row["status"] == "measured"
                and row["contract_sha256"] == native["contract_sha256"]
            )
            inp = row["input"]
            seconds = inp["excerpt_samples"] / inp["sample_rate"]
            old = [
                r for r in historical["native_length_and_timing"] if r["case"] == case
            ]
            assert len(old) == 8 and all(
                r["speaker"] == row["speaker"]
                and abs(r["source_seconds"] - seconds) < 1e-12
                for r in old
            )
            rows.append(
                dict(
                    case=case,
                    speaker=row["speaker"],
                    original_input_seconds=seconds,
                    analysis_wall_seconds=row["timing"]["analysis_wall_seconds"],
                    decode_wall_seconds=row["timing"]["decode_wall_seconds"],
                )
            )
        assert len({r["speaker"] for r in rows}) == speakers_expected
        cohort = dict(
            recordings=expected,
            speakers=speakers_expected,
            case_ids=ids,
            selection_source_group=group_id,
            original_input_seconds=sum(r["original_input_seconds"] for r in rows),
            rows=rows,
        )
        for phase in ["analysis", "decode"]:
            field = phase + "_wall_seconds"
            by_speaker = defaultdict(list)
            for row in rows:
                by_speaker[row["speaker"]].append(
                    row[field] / row["original_input_seconds"]
                )
            total = sum(r[field] for r in rows)
            cohort[phase] = dict(
                total_wall_seconds=total,
                speaker_equal_weight_rtf=statistics.mean(
                    statistics.mean(v) for v in by_speaker.values()
                ),
                recording_equal_weight_rtf=statistics.mean(
                    r[field] / r["original_input_seconds"] for r in rows
                ),
                duration_weighted_rtf=total / cohort["original_input_seconds"],
            )
        output["cohorts"][name] = cohort
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    for name, c in output["cohorts"].items():
        print(name, c["original_input_seconds"], c["analysis"], c["decode"])


if __name__ == "__main__":
    main()
