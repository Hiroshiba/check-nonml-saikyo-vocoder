"""Existing human-rating statistic on the exact old 80-pair support; train-only scale."""

from portable_context import ROOT, CORPORA, HISTORICAL, ASV_INPUT
from pathlib import Path
import numpy as np
from run_edits import read, write, freeze, sha
from human_statistics import bootstrap, ci, ranks, METRICS

BASE = ROOT / "auxiliary"
INPUT = ASV_INPUT
PROVENANCE = HISTORICAL / "asv-human-contract.json"
OLD = HISTORICAL / "human-availability100"
OLD_DISTANCES = OLD / "conditional-private-evidence/pair-distances.json"


def main():
    selection = read(INPUT / "selection.json")
    old = read(PROVENANCE)["data"]
    keys = old["common_pairs"]
    lookup = {(r["sample_a"], r["sample_b"]): r for r in selection["pairs"]}
    pairs = [lookup[tuple(k)] for k in keys]
    train = read(ROOT / "extended/train/summary.json")
    rows = train["rows"]
    if len(rows) != 120 or any(r["status"] != "measured" for r in rows):
        raise ValueError("All120 independent train moments required")
    means = []
    seconds = []
    train_sources = {}
    train_manifest = CORPORA / "readout-train/inputs.json"
    train_inputs = {r["id"]: r for r in read(train_manifest)}
    train_sig = sha(ROOT / "extended/train/contract.json")
    if train["contract_sha256"] != train_sig:
        raise ValueError("Train summary contract differs")
    if len({r["case"] for r in rows}) != 120 or len({r["speaker"] for r in rows}) != 40:
        raise ValueError("Train identity count differs")
    for r in rows:
        original = train_inputs[r["case"]]
        if (
            r["input_sha256"] != original["sha256"]
            or r["speaker"] != original["speaker"]
        ):
            raise ValueError("Train original identity differs")
        rp = ROOT / "extended/train" / r["case"] / "record.json"
        if read(rp) != r or r["contract_sha256"] != train_sig:
            raise ValueError("Train record provenance differs")
        train_sources[r["case"]] = dict(
            record_sha256=sha(rp), input_sha256=r["input_sha256"], speaker=r["speaker"]
        )
        p = r["moments"]["path"]
        if sha(p) != r["moments"]["sha256"]:
            raise ValueError("Train moment changed")
        with np.load(p, allow_pickle=False) as z:
            if any(
                z[k].shape != (2110,) or not np.isfinite(z[k]).all()
                for k in ("mean", "second_moment")
            ):
                raise ValueError("Train moments invalid")
            means.append(z["mean"])
            seconds.append(z["second_moment"])
    center = np.mean(means, axis=0)
    var = np.maximum(np.mean(seconds, axis=0) - center * center, 0)
    scale = np.sqrt(var)
    scale[scale <= 1e-12] = 1
    ids = sorted({s for k in keys for s in k})
    data = {}
    sources = {}
    for s in ids:
        rp = BASE / "features" / Path(s).stem / "record.json"
        r = read(rp)
        if (
            r["contract_sha256"] != sha(BASE / "contract.json")
            or r["sample"] != s
            or r["speaker"] != selection["identities"][s]
        ):
            raise ValueError("ASV feature identity/contract differs")
        if r["status"] != "measured":
            raise ValueError(
                "Common recording failed; explicit reduced-support handling required: "
                + s
            )
        if sha(r["mean"]["path"]) != r["mean"]["sha256"]:
            raise ValueError("Mean changed")
        data[s] = np.load(r["mean"]["path"], allow_pickle=False)
        if (
            data[s].shape != (2110,)
            or data[s].dtype != np.float64
            or not np.isfinite(data[s]).all()
        ):
            raise ValueError("ASV mean invalid")
        sources[s] = sha(rp)
    pml_distances = np.asarray(
        [
            np.linalg.norm((data[r["sample_a"]] - data[r["sample_b"]]) / scale)
            for r in pairs
        ]
    )
    old_rows = read(OLD_DISTANCES)
    old_lookup = {(r["sample_a"], r["sample_b"]): r for r in old_rows}
    methods = read(OLD / "conditional-rankings/results.json")["methods"] + [
        "pml_fwcep60_lowband_package_v1"
    ]
    for r in pairs:
        o = old_lookup[(r["sample_a"], r["sample_b"])]
        if any(o[k] != r[k] for k in ("human_rating", "a_speaker", "b_speaker")):
            raise ValueError("Old pair labels differ")
    distances = np.asarray(
        [
            [
                old_lookup[(r["sample_a"], r["sample_b"])]["distances"][m]
                for m in methods[:-1]
            ]
            + [float(d)]
            for r, d in zip(pairs, pml_distances)
        ]
    )
    np.savez_compressed(BASE / "calibration.npz", center=center, scale=scale)
    contract = dict(
        method_implementation=read(ROOT / "native-contract.json")["method"],
        train_manifest_sha256=sha(train_manifest),
        train_record_sources=train_sources,
        calibration_sha256=sha(BASE / "calibration.npz"),
        driver_sha256=sha(__file__),
        statistic_sha256=sha(Path(__file__).with_name("human_statistics.py")),
        selection_sha256=sha(INPUT / "selection.json"),
        old_support_source_sha256=sha(PROVENANCE),
        train_summary_sha256=sha(ROOT / "extended/train/summary.json"),
        feature_contract_sha256=sha(BASE / "contract.json"),
        feature_records=sources,
        seed=20261014,
        replicates=2000,
        old_distances_sha256=sha(OLD_DISTANCES),
        methods=methods,
        scope="same80pairs100recordings as previous7successful methods; MagPhase failed100 previously; fixed human labels; not synthesis MOS",
        training="120recordings equal; frame population moments; std<=1e-12 becomes1",
        ties="atol1e-12 rtol1e-9",
    )
    freeze(BASE / "aggregation-contract.json", contract)
    point, arrays, metadata, anchors, chance = bootstrap(pairs, distances)
    np.savez_compressed(BASE / "bootstrap.npz", **arrays)
    write(
        BASE / "pair-distances.json",
        [
            dict(
                sample_a=r["sample_a"],
                sample_b=r["sample_b"],
                a_speaker=r["a_speaker"],
                b_speaker=r["b_speaker"],
                human_rating=r["human_rating"],
                distances={m: float(d[i]) for i, m in enumerate(methods)},
            )
            for r, d in zip(pairs, distances)
        ],
    )
    rankings = {
        metric: ranks({m: float(point[i, j]) for i, m in enumerate(methods)}, methods)
        for j, metric in enumerate(METRICS)
    }
    results = {
        m: {
            metric: dict(
                value=float(point[i, j]) if np.isfinite(point[i, j]) else None,
                status="measured"
                if np.isfinite(point[i, j])
                else "undefined_constant_or_insufficient_support",
                rank=rankings[metric][m],
                **ci(arrays["values"][:, i, j]),
            )
            for j, metric in enumerate(METRICS)
        }
        for i, m in enumerate(methods)
    }
    write(
        BASE / "human-results.json",
        dict(
            methods=methods,
            results=results,
            metadata=metadata,
            anchors={m: anchors[i] for i, m in enumerate(methods)},
            chance={
                m: float(chance[i]) if np.isfinite(chance[i]) else None
                for i, m in enumerate(methods)
            },
            original_plan=dict(pairs=84, recordings=105),
            conditional_cohort=dict(
                pairs=len(pairs), recordings=len(ids), acquired_recordings=104
            ),
            excluded_method=dict(
                magphase="historical extraction failed all100; not ranked"
            ),
            contract_sha256=sha(BASE / "aggregation-contract.json"),
            uncertainty="Conditional on fixed human pair means and observed speaker graph; no rater resampling or multiple-comparison correction. Not formal nominal coverage guarantee.",
            calibration_sha256=sha(BASE / "calibration.npz"),
            bootstrap_sha256=sha(BASE / "bootstrap.npz"),
            pair_distances_sha256=sha(BASE / "pair-distances.json"),
        ),
    )
    print(results["pml_fwcep60_lowband_package_v1"], flush=True)


if __name__ == "__main__":
    main()
