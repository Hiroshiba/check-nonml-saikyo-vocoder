"""Reaggregate saved comparator triplets and PML on exactly common support."""

from portable_context import REPO, HISTORICAL

import json
from pathlib import Path

import numpy as np
from abx_inputs import OUT, freeze, inputs, read, sha, write
from frozen_abx_statistics import CONDITIONS, ESTIMANDS, bootstrap, make_strata

METHODS = (
    "hnm",
    "world_harvest",
    "facodec",
    "hifiglot",
    "golf",
    "sifigan",
    "llsm2",
    "magphase",
    "pml",
)
OLD = HISTORICAL / "feature-assessment/abx-rankings"


def key(row):
    return tuple(row[k] for k in ("a", "b", "x", "condition"))


def main():
    data, items, _, _, sources = inputs()
    planned = data["triplets"]
    expected = [key(r) for r in planned]
    errors = np.full((len(planned), len(METHODS)), np.nan)
    origins = {}
    for col, method in enumerate(METHODS):
        path = (
            OUT / "raw-triplets.json"
            if method == "pml"
            else OLD / "raw" / f"{method}.json"
        )
        loaded = read(path)
        rows = loaded if method == "pml" else loaded["triplets"]
        by_key = {key(r): r for r in rows}
        if len(by_key) != len(rows) or set(by_key) != set(expected):
            raise ValueError("Saved comparator triplet set differs: " + method)
        for i, identifier in enumerate(expected):
            row = by_key[identifier]
            if row["status"] == "measured":
                value = row["error"]
                if value not in (0.0, 0.5, 1.0):
                    raise ValueError("Invalid ABX error")
                errors[i, col] = value
        origins[method] = {"path": str(path), "sha256": sha(path)}
    folder = OUT / "comparison"
    old_contract = read(OLD / "contract.json")
    if (
        old_contract["manifest_sha256"]
        != sources[next(p for p in sources if p.endswith("abxls120-triphones.json"))]
    ):
        raise ValueError("Historical contract uses a different triplet manifest")
    expected_contract = {
        "distance": "euclidean",
        "max_dtw_cells": 2000000,
        "tie_atol": 1e-12,
        "tie_error": 0.5,
        "downsampling": False,
        "bootstrap_seed": 20261014,
        "bootstrap_replicates": 2000,
    }
    if any(old_contract[k] != v for k, v in expected_contract.items()):
        raise ValueError("Historical distance/aggregation contract differs")
    historical_sources = old_contract["sources_sha256"]
    for source, current in [
        (
            "scripts/all_metrics_features_abx_statistics.py",
            Path(__file__).with_name("frozen_abx_statistics.py"),
        ),
        (
            "vocoderbench/assessment/representation.py",
            REPO / "vocoderbench/assessment/representation.py",
        ),
    ]:
        if historical_sources[source] != sha(current):
            raise ValueError("Historical DTW/statistics source differs")
    contract = {
        "methods": list(METHODS),
        "sources": origins,
        "old_contract_sha256": sha(OLD / "contract.json"),
        "pml_contract_sha256": sha(OUT / "contract.json"),
        "driver_sha256": sha(__file__),
        "statistics_sha256": sha(Path(__file__).with_name("frozen_abx_statistics.py")),
        "support": "intersection of measured fixed triplets across all nine methods",
        "rank": "competition, exact numerical tolerance rtol1e-9 atol1e-12",
        "formal_base": "adoption pending; old hnm retained only as historical measurement comparator",
    }
    freeze(folder / "contract.json", contract)
    keep = np.isfinite(errors).all(axis=1)
    selected = [r for r, k in zip(planned, keep) if k]
    if not selected:
        write(
            folder / "results.json",
            {"status": "incomplete", "reason": "no_common_triplets", "rank": None},
        )
        return
    keys, values, counts = make_strata(selected, errors[keep], items)
    point, arrays, metadata = bootstrap(keys, values, counts)
    np.savez_compressed(folder / "speaker-bootstrap.npz", **arrays)
    write(folder / "common-triplets.json", selected)
    write(
        folder / "strata.json",
        [
            {
                "stratum": list(k),
                "count": int(n),
                "values": dict(zip(METHODS, map(float, v))),
            }
            for k, n, v in zip(keys, counts, values)
        ],
    )
    estimands = {}
    for c, condition in enumerate(CONDITIONS):
        for e, estimand in enumerate(ESTIMANDS):
            p = point[c, e]
            order = sorted(range(len(METHODS)), key=lambda i: p[i])
            ranks = {}
            anchor = None
            rank = None
            for position, index in enumerate(order, 1):
                if not np.isfinite(p[index]):
                    continue
                if anchor is None or not np.isclose(
                    p[index], anchor, rtol=1e-9, atol=1e-12
                ):
                    rank = position
                    anchor = p[index]
                ranks[index] = rank
            rows = {}
            for m, method in enumerate(METHODS):
                draws = arrays["values"][:, c, e, m]
                draws = draws[np.isfinite(draws)]
                rows[method] = {
                    "value": float(p[m]) if np.isfinite(p[m]) else None,
                    "rank": ranks.get(m),
                    "ci95": np.quantile(draws, [0.025, 0.975]).tolist()
                    if len(draws)
                    else None,
                    "valid_replicates": len(draws),
                }
            estimands[condition + "/" + estimand] = {
                "methods": rows,
                "unit": "error_fraction",
                "higher_is_better": False,
            }
    result = {
        "status": "measured" if keep.all() else "incomplete",
        "methods": list(METHODS),
        "planned_triplets": len(planned),
        "common_triplets": int(keep.sum()),
        "missing_by_method": {
            m: int((~np.isfinite(errors[:, i])).sum()) for i, m in enumerate(METHODS)
        },
        "estimands": estimands,
        "bootstrap": metadata,
        "contract_sha256": sha(folder / "contract.json"),
        "limits": [
            "Historical fixed subset, not full official benchmark",
            "Train-calibrated per-coordinate Euclidean metric; blocks and dimension counts differ by method",
            "Speaker-bootstrap CI excludes synthesis/model seed variation; multiplicity uncorrected",
        ],
    }
    result["artifacts"] = {
        p.name: sha(p)
        for p in (
            folder / "speaker-bootstrap.npz",
            folder / "common-triplets.json",
            folder / "strata.json",
        )
    }
    write(folder / "results.json", result)
    print(json.dumps(estimands, ensure_ascii=False))


if __name__ == "__main__":
    main()
