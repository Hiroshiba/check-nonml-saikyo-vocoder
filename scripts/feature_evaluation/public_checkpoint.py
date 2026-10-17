"""Explicit scalar-only projection; never publish payload paths or dense arrays."""

import argparse
import logging
import math
from collections import Counter
from pathlib import Path
from contracts import Context, read, write, resolve, sha, ContractError


def scalar_values(rows):
    output = {}
    for name, row in rows.items():
        if name not in {
            "abx/" + condition + "/" + estimand
            for condition in ["within_speaker", "across_speaker"]
            for estimand in ["flat_stratum", "x_speaker_macro", "nested_phone_context"]
        } | {
            "readout/" + target for target in ["log_f0", "rms_dbfs", "spectral_slope"]
        }:
            raise ContractError("Unexpected public axis")
        result = {}
        for key in ["candidate", "pml", "candidate_minus_pml", "rank"]:
            value = row[key]
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value)
            ):
                raise ContractError("Public numeric field is not finite scalar")
            result[key] = value
        if type(row["lower_better"]) is not bool:
            raise ContractError("Public direction must be boolean")
        if row["rank"] is not None:
            raise ContractError("Feature rank must remain unassigned")
        result["lower_better"] = row["lower_better"]
        ci = row["delta_ci95"]
        if ci is not None and (
            not isinstance(ci, list)
            or len(ci) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in ci)
            or ci[0] > ci[1]
        ):
            raise ContractError("Invalid public interval")
        result["delta_ci95"] = ci
        output[name] = result
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--context", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    ctx = Context(a.context, "public-checkpoint")
    views = ["canonical_complex4099", "amp3075", "rawcomplex4099"]
    results = []
    incomplete = []
    digests = []
    for view in views:
        path = ctx.root / "results/comparison" / view / "summary.json"
        if not path.is_file():
            incomplete.append("comparison/" + view)
            results.append(
                {
                    "view": view,
                    "primary": view == "canonical_complex4099",
                    "status": "incomplete",
                    "reason_code": "comparison_terminal_unavailable",
                    "values": {},
                    "paired_support": None,
                }
            )
            continue
        data = read(path)
        if (
            data["validation_state"] != "validated_end"
            or data["source_freeze_sha256"] != ctx.sig
            or data["view"] != view
        ):
            raise ContractError("Comparison terminal mismatch")
        for item in data["artifacts"]:
            resolve(path.parent, item)
        for item in data["source_summaries"]:
            resolve(ctx.root, item)
        support = {}
        expected_support = {
            "abx": 4960,
            "readout/log_f0": 120,
            "readout/rms_dbfs": 120,
            "readout/spectral_slope": 120,
        }
        if set(data["support"]) != set(expected_support):
            raise ContractError("Public support axes differ")
        for name, row in data["support"].items():
            if (
                type(row["planned"]) is not int
                or row["planned"] != expected_support[name]
                or type(row["paired_measured"]) is not int
                or not 0 <= row["paired_measured"] <= row["planned"]
            ):
                raise ContractError("Invalid public support count")
            support[name] = {key: row[key] for key in ["planned", "paired_measured"]}
            if "speakers" in row:
                if not isinstance(row["speakers"], list) or len(row["speakers"]) > 40:
                    raise ContractError("Invalid public speaker count")
                support[name]["speaker_count"] = len(row["speakers"])
        results.append(
            {
                "view": view,
                "primary": view == "canonical_complex4099",
                "status": "validated_end",
                "values": scalar_values(data["results"]),
                "paired_support": support,
            }
        )
        digests.append(sha(path))
    failures = []
    for split in ["train", "test"]:
        for method, method_views in [("candidate", views), ("pml", ["pml2110"])]:
            for view in method_views:
                base = ctx.root / "results" / split / method / view
                path = base / "summary.json"
                if not path.is_file():
                    incomplete.append("moments/" + split + "/" + method + "/" + view)
                    failures.append(
                        {
                            "split": split,
                            "method": method,
                            "view": view,
                            "planned": 120,
                            "status_counts": {"unverified": 120},
                            "reason_counts": {"moment_terminal_unavailable": 120},
                        }
                    )
                    continue
                summary = read(path)
                if (
                    summary["validation_state"] != "validated_end"
                    or summary["planned_cases"] != 120
                    or summary["contract"]["source_freeze_sha256"] != ctx.sig
                ):
                    raise ContractError("Moment terminal mismatch")
                specs = ctx.train if split == "train" else ctx.test
                if (
                    len(summary["rows"]) != 120
                    or summary["case_ids"] != [r["case"] for r in specs]
                    or [r["case"] for r in summary["rows"]] != summary["case_ids"]
                ):
                    raise ContractError("Public denominator order mismatch")
                if any(
                    summary["contract"][key] != value
                    for key, value in [
                        ("split", split),
                        ("method", method),
                        ("view", view),
                    ]
                ):
                    raise ContractError("Public moment contract mismatch")
                reasons = Counter()
                statuses = Counter()
                for item in summary["rows"]:
                    record = read(resolve(base, item["record"]))
                    if (
                        record["case"] != item["case"]
                        or record["status"] != item["status"]
                        or record["contract"] != summary["contract"]
                    ):
                        raise ContractError("Public record mismatch")
                    if record["status"] not in [
                        "measured",
                        "failed",
                        "upstream_failed",
                    ]:
                        raise ContractError("Unknown public status")
                    statuses[record["status"]] += 1
                    if record["status"] != "measured":
                        if record["reason_code"] not in [
                            "feature_observation_failed",
                            "payload_not_available",
                        ]:
                            raise ContractError("Unknown public failure code")
                        reasons[record["reason_code"]] += 1
                failures.append(
                    {
                        "split": split,
                        "method": method,
                        "view": view,
                        "planned": 120,
                        "status_counts": dict(statuses),
                        "reason_counts": dict(reasons),
                    }
                )
                digests.append(sha(path))
    ctx.end()
    write(
        a.output,
        {
            "schema_version": 1,
            "scope": "feature-evaluation-new-run",
            "validation_state": "incomplete" if incomplete else "validated_end",
            "incomplete_components": incomplete,
            "source_freeze_sha256": ctx.sig,
            "common_plan_sha256": sha(ctx.plan),
            "formal_base": "pml",
            "planned_train": 120,
            "planned_test": 120,
            "planned_abx": 4960,
            "fixed_alpha": 1,
            "old_implementation_restored": False,
            "private_durable_backup_claim": False,
            "comparison": results,
            "failures": failures,
            "terminal_summary_sha256": digests,
            "limitations": [
                "High-dimensional readout uses more feature dimensions than training recordings.",
                "F0 readout includes a directly stored F0 column.",
                "Comparison uses common measured support; failures are reported separately.",
                "Canonical view uses one whole-utterance native clock; no token-local reset.",
            ],
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.captureWarnings(True)
    try:
        main()
    except BaseException:
        logging.exception("Public checkpoint preparation stopped")
        raise
