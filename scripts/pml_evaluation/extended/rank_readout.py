"""Append PML probe to restored historical predictions on identical inputs/targets/support."""

from portable_context import HISTORICAL
import numpy as np
from run_edits import ROOT, read, write, freeze, sha

OLD = HISTORICAL / "feature-assessment"
old = read(OLD / "readout-rankings/raw-recordings.json")
prior = read(OLD / "readout-rankings/results.json")
cfg = read(OLD / "readout-rankings/contract.json")
new = read(ROOT / "extended/readout/results.json")
spec = read(ROOT / "input-contract.json")
tr = read(ROOT / "extended/train/summary.json")["rows"]
out = ROOT / "extended/readout-comparison"
if (
    sha(OLD / "readout-rankings/raw-recordings.json") != prior["raw_recordings_sha256"]
    or sha(OLD / "readout-rankings/contract.json") != prior["contract_sha256"]
):
    raise ValueError("Historical provenance mismatch")
if cfg["alpha"] != 1 or cfg["seed"] != 20261014:
    raise ValueError("Historical protocol differs")
new_by = {r["case"]: r for r in new["rows"]}
old_by = {r["case"]: r for r in old}
inputs = {r["id"]: r for r in spec["cases"]}
if set(new_by) != set(old_by) or set(new_by) != set(inputs):
    raise ValueError("Evaluation cohort differs")
evidence = []
for split, records, expected in [
    ("evaluation", cfg["eval_targets"], new_by),
    ("train", cfg["train_targets"], {r["case"]: r for r in tr}),
]:
    if {r["case"] for r in records} != set(expected):
        raise ValueError("Target cohort differs")
    for r in records:
        p = OLD / "targets" / split / f"{r['case']}.json"
        t = read(p)
        if sha(p) != r["record_sha256"]:
            raise ValueError("Historical target changed")
        source_sha = (
            inputs[r["case"]]["input"]["sha256"]
            if split == "evaluation"
            else expected[r["case"]]["input_sha256"]
        )
        if t["source_sha256"] != source_sha:
            raise ValueError("Original source differs")
        targets = expected[r["case"]]["targets"]
        for k in targets:
            a, b = t["targets"][k], targets[k]
            if (a is None) != (b is None) or (
                a is not None and not np.isclose(a, b, rtol=0, atol=1e-12)
            ):
                raise ValueError("Target definition/result differs")
        evidence.append(
            dict(
                case=r["case"],
                split=split,
                record_sha256=sha(p),
                input_sha256=source_sha,
            )
        )
methods = [*cfg["methods"], "pml_fwcep60_lowband_package_v1"]
keys = ["log_f0", "rms_dbfs", "spectral_slope"]
contract = dict(
    driver_sha256=sha(__file__),
    prior_results_sha256=sha(OLD / "readout-rankings/results.json"),
    new_results_sha256=sha(ROOT / "extended/readout/results.json"),
    target_evidence=evidence,
    methods=methods,
    alpha=1,
    seed=20261014,
    replicates=2000,
    aggregation="all-nine common finite target/prediction cases; within-speaker mean then equal speaker MAE",
    comparison="fixed linear probe; not proof of information loss; dtype and feature dimensions method-specific",
    target_match_atol=1e-12,
)
freeze(out / "contract.json", contract)
result = {}
for key in keys:
    selected = []
    errors = []
    for case, r in old_by.items():
        nr = new_by[case]
        if r["speaker"] != nr["speaker"]:
            raise ValueError("Speaker mismatch")
        values = [r["predictions"][m][key] for m in cfg["methods"]] + [
            nr["predictions"][key]
        ]
        truth = nr["targets"][key]
        if truth is None or any(v is None or not np.isfinite(v) for v in values):
            continue
        selected.append(nr)
        errors.append(np.abs(np.asarray(values) - truth))
    errors = np.asarray(errors)
    speakers = sorted({r["speaker"] for r in selected})
    sv = np.stack(
        [errors[[r["speaker"] == s for r in selected]].mean(0) for s in speakers]
    )
    means = sv.mean(0)
    draws = np.random.default_rng(20261014).integers(
        0, len(speakers), (2000, len(speakers))
    )
    boot = sv[draws].mean(1)
    ci = np.quantile(boot, [0.025, 0.975], axis=0)
    path = out / f"{key}-bootstrap.npz"
    np.savez_compressed(path, draws=draws, values=boot)
    result[key] = dict(
        recordings=len(selected),
        speakers=len(speakers),
        ids=[r["case"] for r in selected],
        bootstrap_sha256=sha(path),
        methods={
            m: dict(
                speaker_macro_mae=float(means[j]),
                rank=int(1 + np.sum(means < means[j])),
                ci95=ci[:, j].tolist(),
            )
            for j, m in enumerate(methods)
        },
    )
write(
    out / "results.json",
    dict(contract_sha256=sha(out / "contract.json"), metrics=result),
)
