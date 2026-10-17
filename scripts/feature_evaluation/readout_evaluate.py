"""Fixed-alpha train-mean-scaled readout with explicit missing evaluation rows."""

import argparse
import logging
import numpy as np
from contracts import Context, write, sha, ContractError
from saved_features import moment_records, target_records
from moments import ridge_fit_predict
from observations import DIMENSIONS

KEYS = ("log_f0", "rms_dbfs", "spectral_slope")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--context", required=True)
    p.add_argument("--method", choices=["candidate", "pml"], required=True)
    p.add_argument("--view", choices=list(DIMENSIONS), required=True)
    a = p.parse_args()
    ctx = Context(a.context, "readout")
    train, tp = moment_records(ctx, "train", a.method, a.view)
    test, ep = moment_records(ctx, "test", a.method, a.view)
    train_targets, ttp = target_records(ctx, "train")
    test_targets, etp = target_records(ctx, "test")
    if any(r["status"] != "measured" for r in train):
        raise ContractError("All train120 feature means required; no reduced fit")
    out = ctx.root / "results/readout" / a.method / a.view
    if out.exists():
        raise ContractError("Readout attempt exists; preserve before explicit recovery")
    out.mkdir(parents=True)
    contract = {
        "source_freeze_sha256": ctx.sig,
        "method": a.method,
        "view": a.view,
        "train_summary_sha256": sha(tp),
        "test_summary_sha256": sha(ep),
        "train_targets_summary_sha256": sha(ttp),
        "test_targets_summary_sha256": sha(etp),
        "alpha": 1.0,
        "seed": 20261014,
        "bootstrap_replicates": 2000,
        "scaling": "target-valid train recording mean population std; <=1e-12 to1",
    }
    write(out / "started.json", contract)
    train_matrix = np.array([r["mean"] for r in train])
    valid_features = np.array([r["status"] == "measured" for r in test])
    selected = [i for i, v in enumerate(valid_features) if v]
    test_matrix = np.array(
        [test[i]["mean"] for i in selected], dtype=np.float64
    ).reshape(len(selected), DIMENSIONS[a.view])
    raw = []
    summaries = {}
    for key in KEYS:
        y = np.array(
            [
                r["targets"].get(key)
                if r["status"] == "measured" and r["targets"].get(key) is not None
                else np.nan
                for r in train_targets
            ],
            dtype=np.float64,
        )
        if np.isfinite(y).sum() < 2:
            summaries[key] = {
                "status": "not_applicable",
                "reason_code": "insufficient_train_targets",
            }
            raw.extend(
                {
                    "case": r["case"],
                    "speaker": r["speaker"],
                    "target": key,
                    "status": "not_applicable",
                    "reason_code": "insufficient_train_targets",
                    "prediction": None,
                    "truth": None,
                    "absolute_error": None,
                }
                for r in test
            )
            continue
        predictions, model, diagnostic = ridge_fit_predict(train_matrix, test_matrix, y)
        np.savez_compressed(out / (key + "-model.npz"), **model)
        prediction = dict(zip(selected, predictions))
        errors = []
        truth = []
        speakers = []
        for i, r in enumerate(test):
            actual = test_targets[i].get("targets", {}).get(key)
            row = {
                "case": r["case"],
                "speaker": r["speaker"],
                "target": key,
                "status": "unavailable",
                "prediction": float(prediction[i]) if i in prediction else None,
                "truth": actual,
                "absolute_error": None,
            }
            if i not in prediction:
                row["reason_code"] = "feature_unavailable"
            elif actual is None or not np.isfinite(actual):
                row["reason_code"] = "target_unavailable"
            else:
                value = abs(float(prediction[i]) - actual)
                row.update(status="measured", reason_code="none", absolute_error=value)
                errors.append(value)
                truth.append(actual)
                speakers.append(r["speaker"])
            raw.append(row)
        groups = sorted(set(speakers))
        mae = np.array(
            [np.mean([v for v, s in zip(errors, speakers) if s == g]) for g in groups]
        )
        baseline = np.array(
            [
                np.mean(
                    [
                        abs(v - model["target_center"])
                        for v, s in zip(truth, speakers)
                        if s == g
                    ]
                )
                for g in groups
            ]
        )
        summary = {
            "status": "measured" if len(mae) else "not_applicable",
            "recordings": len(errors),
            "speakers": len(groups),
            "diagnostics": diagnostic,
            "model_sha256": sha(out / (key + "-model.npz")),
            "rank": None,
            "planned_recordings": 120,
        }
        if len(mae):
            draws = np.random.default_rng(20261014).integers(
                0, len(mae), size=(2000, len(mae))
            )
            boot = mae[draws].mean(1)
            np.savez_compressed(
                out / (key + "-bootstrap.npz"), draws=draws, values=boot
            )
            summary.update(
                speaker_macro_mae=float(mae.mean()),
                ci95=np.quantile(boot, [0.025, 0.975]).tolist()
                if len(groups) >= 2
                else None,
                constant_train_mean_speaker_macro_mae=float(baseline.mean()),
            )
        summaries[key] = summary
    moment_records(ctx, "train", a.method, a.view)
    moment_records(ctx, "test", a.method, a.view)
    if (
        sha(tp) != contract["train_summary_sha256"]
        or sha(ep) != contract["test_summary_sha256"]
    ):
        raise ContractError("Moments changed during readout")
    target_records(ctx, "train")
    target_records(ctx, "test")
    if (
        sha(ttp) != contract["train_targets_summary_sha256"]
        or sha(etp) != contract["test_targets_summary_sha256"]
    ):
        raise ContractError("Targets changed during readout")
    ctx.input_audit("train", a.method)
    ctx.input_audit("test", a.method)
    ctx.end()
    write(out / "raw-recordings.json", raw)
    write(
        out / "summary.json",
        {
            "validation_state": "validated_end",
            "contract": contract,
            "summaries": summaries,
            "raw_sha256": sha(out / "raw-recordings.json"),
            "planned_cases": 120,
            "comparison": "own support; candidate/PML paired support must be recomputed from raw rows",
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
        logging.exception("Readout operational/contract interruption")
        raise
