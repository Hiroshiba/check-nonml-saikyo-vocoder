"""Candidate-view versus newly calibrated PML on identical retained support."""

import argparse
import logging
import sys
import numpy as np
from contracts import Context, read, write, resolve, sha, ContractError
from abx_evaluate import fixed_abx


def terminal(ctx, kind, method, view):
    directory = ctx.root / "results" / kind / method / view
    summary = read(directory / "summary.json")
    if (
        summary["validation_state"] != "validated_end"
        or summary["contract"]["source_freeze_sha256"] != ctx.sig
        or summary["contract"]["method"] != method
        or summary["contract"]["view"] != view
    ):
        raise ContractError("Comparison source terminal mismatch")
    for item in summary["artifacts"]:
        resolve(directory, item)
    path = directory / ("raw-triplets.json" if kind == "abx" else "raw-recordings.json")
    if sha(path) != summary["raw_sha256"]:
        raise ContractError("Comparison raw data changed")
    return read(path), {
        "path": str(directory / "summary.json"),
        "sha256": sha(directory / "summary.json"),
    }


def interval(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return np.quantile(values, [0.025, 0.975]).tolist() if len(values) else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--context", required=True)
    p.add_argument(
        "--view",
        choices=["canonical_complex4099", "amp3075", "rawcomplex4099"],
        required=True,
    )
    a = p.parse_args()
    ctx = Context(a.context, "paired-comparison")
    out = ctx.root / "results/comparison" / a.view
    if out.exists():
        raise ContractError("Existing comparison attempt must be preserved")
    out.mkdir(parents=True)
    provenance = []
    results = {}
    support = {}
    fixed, items, _ = fixed_abx(ctx)
    candidate, cp = terminal(ctx, "abx", "candidate", a.view)
    pml, pp = terminal(ctx, "abx", "pml", "pml2110")
    provenance.extend([cp, pp])

    def key(r):
        return tuple(r[k] for k in ["a", "b", "x", "condition"])

    if [key(r) for r in candidate] != [key(r) for r in fixed["triplets"]] or [
        key(r) for r in pml
    ] != [key(r) for r in candidate]:
        raise ContractError("Fixed ABX comparison denominator changed")
    selected = [
        i
        for i, (c, b) in enumerate(zip(candidate, pml))
        if c["status"] == b["status"] == "measured"
    ]
    support["abx"] = {
        "planned": 4960,
        "paired_measured": len(selected),
        "triplet_indices": selected,
    }
    if selected:
        path = resolve(ctx.root, ctx.config["abx_statistics"])
        sys.path.insert(0, str(path.parent))
        import frozen_abx_statistics as stats

        errors = np.array([[candidate[i]["error"], pml[i]["error"]] for i in selected])
        rows = [candidate[i] for i in selected]
        keys, values, counts = stats.make_strata(rows, errors, items)
        point, arrays, metadata = stats.bootstrap(keys, values, counts)
        np.savez_compressed(out / "abx-bootstrap.npz", **arrays)
        for i, condition in enumerate(stats.CONDITIONS):
            for j, estimand in enumerate(stats.ESTIMANDS):
                c, b = point[i, j]
                delta = c - b
                draws = arrays["values"][:, i, j]
                results["abx/" + condition + "/" + estimand] = {
                    "candidate": float(c) if np.isfinite(c) else None,
                    "pml": float(b) if np.isfinite(b) else None,
                    "candidate_minus_pml": float(delta) if np.isfinite(delta) else None,
                    "delta_ci95": interval(draws[:, 0] - draws[:, 1]),
                    "lower_better": True,
                    "rank": None,
                }
        support["abx"]["bootstrap"] = metadata
    candidate, cp = terminal(ctx, "readout", "candidate", a.view)
    pml, pp = terminal(ctx, "readout", "pml", "pml2110")
    provenance.extend([cp, pp])
    expected = [
        (r["case"], target)
        for target in ["log_f0", "rms_dbfs", "spectral_slope"]
        for r in ctx.test
    ]
    if [(r["case"], r["target"]) for r in candidate] != expected or [
        (r["case"], r["target"]) for r in pml
    ] != expected:
        raise ContractError("Readout comparison denominator changed")
    for target in ["log_f0", "rms_dbfs", "spectral_slope"]:
        pairs = [
            (c, b)
            for c, b in zip(candidate, pml)
            if c["target"] == target and c["status"] == b["status"] == "measured"
        ]
        for c, b in pairs:
            if c["speaker"] != b["speaker"] or c["truth"] != b["truth"]:
                raise ContractError("Readout comparison target mismatch")
        speakers = sorted({c["speaker"] for c, b in pairs})
        support["readout/" + target] = {
            "planned": 120,
            "paired_measured": len(pairs),
            "speakers": speakers,
            "cases": [c["case"] for c, b in pairs],
        }
        if not speakers:
            continue
        errors = np.array(
            [
                [
                    np.mean(
                        [r[k]["absolute_error"] for r in pairs if r[0]["speaker"] == s]
                    )
                    for k in [0, 1]
                ]
                for s in speakers
            ]
        )
        point = errors.mean(0)
        draws = np.random.default_rng(20261014).integers(
            0, len(speakers), size=(2000, len(speakers))
        )
        boot = errors[draws].mean(1)
        np.savez_compressed(out / (target + "-bootstrap.npz"), draws=draws, values=boot)
        results["readout/" + target] = {
            "candidate": float(point[0]),
            "pml": float(point[1]),
            "candidate_minus_pml": float(point[0] - point[1]),
            "delta_ci95": interval(boot[:, 0] - boot[:, 1])
            if len(speakers) >= 2
            else None,
            "lower_better": True,
            "rank": None,
        }
    for item in provenance:
        resolve(ctx.root, item)
    ctx.end()
    write(
        out / "summary.json",
        {
            "validation_state": "validated_end",
            "source_freeze_sha256": ctx.sig,
            "view": a.view,
            "formal_base": "pml",
            "scale_reference": "new centered recording-equal PML calibration",
            "results": results,
            "support": support,
            "source_summaries": provenance,
            "artifacts": [
                {"path": p.name, "sha256": sha(p)}
                for p in sorted(out.iterdir())
                if p.is_file()
            ],
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.captureWarnings(True)
    try:
        main()
    except BaseException:
        logging.exception("Paired comparison interruption")
        raise
