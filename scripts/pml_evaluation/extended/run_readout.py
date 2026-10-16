"""Train-only ridge, independent fixed evaluation; speaker-macro MAE and bootstrap."""

from pathlib import Path
import numpy as np
from run_edits import ROOT, sha, read, write, freeze
from run_train_features import targets

KEYS = ["log_f0", "rms_dbfs", "spectral_slope"]
ALPHA = 1.0
SEED = 20261014
REPLICATES = 2000


def main():
    out = ROOT / "extended/readout"
    tr = read(ROOT / "extended/train/summary.json")["rows"]
    ev = read(ROOT / "input-contract.json")["cases"]
    if len(tr) != 120 or any(r["status"] != "measured" for r in tr):
        raise RuntimeError("Independent120 calibration not complete")
    if {r["speaker"] for r in tr} & {r["speaker"] for r in ev}:
        raise ValueError("Speaker leakage")
    sources = []
    train = []
    evaluation = []
    truth = []
    for r in tr:
        if r["contract_sha256"] != sha(ROOT / "extended/train/contract.json"):
            raise ValueError("Train row contract changed")
        p = Path(r["moments"]["path"])
        if sha(p) != r["moments"]["sha256"]:
            raise ValueError("Train moments changed")
        train.append(np.load(p)["mean"])
        sources.append(dict(case=r["case"], sha256=sha(p)))
    for c in ev:
        r = read(ROOT / "extended/features" / c["id"] / "record.json")
        p = Path(r["features"]["path"])
        if r["contract_sha256"] != sha(ROOT / "extended/features/contract.json") or r[
            "native_record_sha256"
        ] != sha(ROOT / "native" / c["id"] / "record.json"):
            raise ValueError("Evaluation provenance changed")
        if r["status"] != "measured" or sha(p) != r["features"]["sha256"]:
            raise ValueError("Evaluation features unavailable/changed")
        evaluation.append(np.load(p)["mean"])
        sources.append(dict(case=c["id"], sha256=sha(p)))
        inp = Path(c["input"]["path"])
        inp = inp if inp.is_absolute() else ROOT.parent / inp
        if sha(inp) != c["input"]["sha256"]:
            raise ValueError("Evaluation original changed")
        truth.append(targets(np.load(inp, allow_pickle=False)))
    contract = dict(
        drivers={
            p.name: sha(p)
            for p in [
                Path(__file__),
                Path(__file__).with_name("run_train_features.py"),
                Path(__file__).with_name("run_edits.py"),
            ]
        },
        train_contract_sha256=sha(ROOT / "extended/train/contract.json"),
        train_summary_sha256=sha(ROOT / "extended/train/summary.json"),
        features_contract_sha256=sha(ROOT / "extended/features/contract.json"),
        sources=sources,
        alpha=ALPHA,
        seed=SEED,
        bootstrap_replicates=REPLICATES,
        targets=KEYS,
        scaling="per-target valid train recording means population std; std<=1e-12->1",
        aggregation="recording absolute error then speaker equal MAE; no evaluation fitting",
        comparison="PML-alone fixed120; historical all-method common support must be intersected before rankings",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    train = np.asarray(train)
    evaluation = np.asarray(evaluation)
    rows = []
    summaries = {}
    if (
        train.shape != (120, 2110)
        or evaluation.shape != (120, 2110)
        or not np.isfinite(train).all()
        or not np.isfinite(evaluation).all()
    ):
        raise ValueError("Readout matrix shape/finite invalid")
    predictions = np.full((len(ev), len(KEYS)), np.nan)
    for j, key in enumerate(KEYS):
        y = np.asarray(
            [r["targets"][key] if r["targets"][key] is not None else np.nan for r in tr]
        )
        valid = np.isfinite(y)
        if valid.sum() < 2:
            summaries[key] = dict(
                status="not_applicable", reason="fewer_than_two_valid_train_targets"
            )
            continue
        x = train[valid]
        center = x.mean(0)
        std = x.std(0)
        std = np.where(std > 1e-12, std, 1.0)
        x = (x - center) / std
        yc = y[valid].mean()
        u, s, vt = np.linalg.svd(x, full_matrices=False)
        coef = (vt.T * (s / (s * s + ALPHA))) @ (u.T @ (y[valid] - yc))
        predictions[:, j] = ((evaluation - center) / std) @ coef + yc
        path = out / f"{key}-model.npz"
        np.savez_compressed(
            path,
            center=center,
            scale=std,
            coefficients=coef,
            target_center=yc,
            train_valid=valid,
        )
        actual = np.asarray([r[key] if r[key] is not None else np.nan for r in truth])
        ok = np.isfinite(actual) & np.isfinite(predictions[:, j])
        speakers = sorted({c["speaker"] for c, k in zip(ev, ok) if k})
        errs = predictions[:, j] - actual
        vals = np.asarray(
            [
                np.abs(errs)[ok & np.array([c["speaker"] == s for c in ev])].mean()
                for s in speakers
            ]
        )
        baseline = np.asarray(
            [
                np.abs(actual - yc)[
                    ok & np.array([c["speaker"] == s for c in ev])
                ].mean()
                for s in speakers
            ]
        )
        if len(vals):
            draws = np.random.default_rng(SEED).integers(
                0, len(vals), size=(REPLICATES, len(vals))
            )
            boot = vals[draws].mean(1)
            bp = out / f"{key}-bootstrap.npz"
            np.savez_compressed(bp, draws=draws, values=boot)
            summaries[key] = dict(
                status="measured",
                speaker_macro_mae=float(vals.mean()),
                ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
                constant_train_mean_speaker_macro_mae=float(baseline.mean()),
                recordings=int(ok.sum()),
                speakers=len(speakers),
                model_sha256=sha(path),
                bootstrap_sha256=sha(bp),
                train_valid=int(valid.sum()),
            )
        else:
            summaries[key] = dict(
                status="not_applicable", reason="no valid evaluation targets"
            )
    for i, c in enumerate(ev):
        rows.append(
            dict(
                case=c["id"],
                speaker=c["speaker"],
                targets=truth[i],
                predictions={
                    k: float(predictions[i, j])
                    if np.isfinite(predictions[i, j])
                    else None
                    for j, k in enumerate(KEYS)
                },
            )
        )
    write(
        out / "results.json", dict(contract_sha256=sig, summaries=summaries, rows=rows)
    )


if __name__ == "__main__":
    main()
