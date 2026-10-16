"""Fixed official subset ABX on PML readout, without new triplets or fitted eval scale."""

from portable_context import ROOT, REPO

import argparse
import logging
import sys
import time
import traceback
from functools import lru_cache
from pathlib import Path

import numpy as np
import scipy

from abx_inputs import (
    OUT,
    calibration,
    feature_records,
    freeze,
    inputs,
    read,
    sha,
    write,
)
from frozen_abx_statistics import (
    CONDITIONS,
    ESTIMANDS,
    REPLICATES,
    SEED,
    bootstrap,
    make_strata,
)
from vocoderbench.assessment.representation import dtw


def run_distances(data, items, records, scale, sig, retry_failed=False):
    @lru_cache(maxsize=4)
    def feature(identifier):
        r = records[identifier]
        with np.load(r["features"]["path"], allow_pickle=False) as z:
            m, t = z["features"], z["times"]
        if (
            m.shape != tuple(r["features"]["shape"])
            or m.shape[1] != 2110
            or m.dtype != np.float64
            or not np.isfinite(m).all()
            or t.shape != (len(m),)
            or not np.isfinite(t).all()
            or np.any(np.diff(t) <= 0)
        ):
            raise ValueError("Invalid exported native features/times")
        return m, t

    def token(identifier):
        r = items[identifier]
        m, t = feature(r["recording_id"])
        a, b = np.searchsorted(
            t, [r["onset_seconds"], r["offset_seconds"]], side="left"
        )
        if a == b:
            raise ValueError("No native frame in token")
        return m[a:b]

    pairs = sorted(
        {
            tuple(sorted((row[k], row["x"])))
            for row in data["triplets"]
            for k in ("a", "b")
        }
    )
    cache = {}
    for i, key in enumerate(pairs):
        path = OUT / "distances" / f"{i:05d}.json"
        if path.exists():
            row = read(path)
            if row["contract_sha256"] != sig or row["tokens"] != list(key):
                raise ValueError("Distance resume contract mismatch")
            if retry_failed and row["status"] == "failed":
                historical = OUT / "failure_history" / f"{i:05d}-{time.time_ns()}.json"
                write(historical, row)
                path.unlink()
        if not path.exists():
            row = {"tokens": list(key), "contract_sha256": sig}
            try:
                if any(items[k]["recording_id"] not in records for k in key):
                    row.update(
                        status="not_applicable",
                        value=None,
                        reason="missing_token_features",
                    )
                else:
                    value = dtw(
                        token(key[0]), token(key[1]), "euclidean", 1 / scale, 2_000_000
                    )
                    if not np.isfinite(value):
                        raise ValueError("Nonfinite distance")
                    row.update(status="measured", value=value)
            except Exception:
                logging.getLogger(__name__).exception("ABX pair failed: %s", key)
                row.update(
                    status="failed", value=None, traceback=traceback.format_exc()
                )
            write(path, row)
        cache[key] = row
        if (i + 1) % 100 == 0:
            write(
                OUT / "status.json",
                {
                    "status": "running",
                    "completed_pairs": i + 1,
                    "planned_pairs": len(pairs),
                },
            )
            print("pairs", i + 1, "/", len(pairs), flush=True)
    raw = []
    for row in data["triplets"]:
        distances = [
            cache[tuple(sorted((row[k], row["x"])))]["value"] for k in ("a", "b")
        ]
        if any(v is None for v in distances):
            raw.append({**row, "status": "unavailable", "error": None})
        else:
            a, b = distances
            tie = abs(a - b) <= 1e-12
            raw.append(
                {
                    **row,
                    "status": "measured",
                    "distance_ax": a,
                    "distance_bx": b,
                    "tie": tie,
                    "error": 0.5 if tie else float(a > b),
                }
            )
    write(OUT / "raw-triplets.json", raw)
    return raw


def summarize(raw, items):
    selected = [r for r in raw if r["status"] == "measured"]
    if not selected:
        return {"status": "incomplete", "reason": "no_measured_triplets"}
    keys, values, counts = make_strata(
        selected, np.array([[r["error"]] for r in selected]), items
    )
    point, arrays, metadata = bootstrap(keys, values, counts)
    np.savez_compressed(OUT / "speaker-bootstrap.npz", **arrays)
    write(
        OUT / "strata.json",
        [
            {"stratum": list(k), "count": int(n), "error": float(v[0])}
            for k, n, v in zip(keys, counts, values)
        ],
    )
    estimands = {}
    for c, condition in enumerate(CONDITIONS):
        for e, estimand in enumerate(ESTIMANDS):
            draws = arrays["values"][:, c, e, 0]
            draws = draws[np.isfinite(draws)]
            estimands[condition + "/" + estimand] = {
                "value": float(point[c, e, 0]) if np.isfinite(point[c, e, 0]) else None,
                "ci95": np.quantile(draws, [0.025, 0.975]).tolist()
                if len(draws)
                else None,
                "valid_replicates": len(draws),
                "rank": None,
                "unit": "error_fraction",
            }
    return {
        "status": "measured" if len(selected) == len(raw) else "incomplete",
        "planned_triplets": len(raw),
        "measured_triplets": len(selected),
        "estimands": estimands,
        "bootstrap": metadata,
        "limits": [
            "Official 6-second subset, not full abxLS benchmark",
            "PML-only scores; rankings require common-triplet recomputation with comparators",
            "Fixed speaker-graph conditional descriptive bootstrap; multiplicity uncorrected; CI excludes synthesis/model seed variation",
            "NM has 2049 of 2110 dimensions; equal per-dimension train scaling is not equal feature-block weighting",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-only", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()
    data, items, specs, train, sources = inputs()
    inventory = {
        "source_hashes": sources,
        "counts": data["counts"],
        "feature_dimensions": 2110,
        "unique_pairs": len(
            {
                tuple(sorted((r[k], r["x"])))
                for r in data["triplets"]
                for k in ("a", "b")
            }
        ),
    }
    write(OUT / "inventory.json", inventory)
    if args.inventory_only:
        return
    fitted = calibration(train)
    records = feature_records(specs)
    if fitted is None or records is None:
        return
    center, scale, train_records = fitted
    records, exclusions = records
    contract = {
        "method": "pml",
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "inputs": sources,
        "drivers": {p.name: sha(p) for p in Path(__file__).parent.glob("*.py")},
        "dtw_source_sha256": sha(REPO / "vocoderbench/assessment/representation.py"),
        "train_contract_sha256": sha(ROOT / "extended/train/contract.json"),
        "feature_contract_sha256": sha(ROOT / "extended/features/contract.json"),
        "train_records": train_records,
        "evaluation_records": {
            k: sha(ROOT / "extended/features" / k / "record.json") for k in records
        },
        "exclusions": exclusions,
        "distance": "euclidean, minimum total cost path divided by chosen path length",
        "scale": "train utterance-equal frame population std; std<=1e-12 ->1; no eval fitting",
        "token_window": "onset<=actual native timestamp<offset",
        "tie_atol": 1e-12,
        "tie_error": 0.5,
        "max_cells": 2_000_000,
        "downsample": False,
        "seed": SEED,
        "replicates": REPLICATES,
        "dimension_count": 2110,
    }
    freeze(OUT / "contract.json", contract)
    sig = sha(OUT / "contract.json")
    np.savez_compressed(OUT / "calibration.npz", center=center, scale=scale)
    raw = run_distances(data, items, records, scale, sig, args.retry_failed)
    result = summarize(raw, items)
    result["contract_sha256"] = sig
    result["artifacts"] = {
        str(p.relative_to(OUT)): sha(p)
        for p in [
            OUT / "raw-triplets.json",
            OUT / "strata.json",
            OUT / "speaker-bootstrap.npz",
            OUT / "calibration.npz",
        ]
        if p.exists()
    }
    write(OUT / "results.json", result)
    write(OUT / "status.json", {"status": result["status"], "analysis_complete": True})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
