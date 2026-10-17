"""Fixed-triplet ABX with one view at a time and two-recording feature cache."""

import argparse
from functools import lru_cache
import logging
import sys
import traceback
import numpy as np
from contracts import Context, read, write, resolve, sha, ContractError
from moments import recording_equal_scale
from observations import observe, DIMENSIONS
from saved_features import moment_records


def fixed_abx(ctx):
    path = resolve(ctx.root, ctx.config["abx_triplets"])
    data = read(path)
    items = {r["id"]: r for r in data["items"]}
    specs = {r["case"]: r for r in ctx.test}
    label = resolve(ctx.root, ctx.config["abx_labels"])
    original = resolve(ctx.root, ctx.config["original_cohort"])
    if (
        len(items) != len(data["items"])
        or len(data["triplets"]) != 4960
        or data["label_sha256"] != sha(label)
        or data["frozen_audio_manifest_sha256"] != sha(original)
    ):
        raise ContractError("Fixed official ABX sources changed")
    identity = read(resolve(ctx.root, ctx.config["abx_identity"]))
    verified = {r["id"]: r for r in identity["entries"]}
    originals = {r["id"]: r for r in read(original)["entries"]}
    seen = set()
    for r in items.values():
        s = specs[r["recording_id"]]
        if (
            r["speaker"] != s["speaker"]
            or not 0 <= r["onset_seconds"] < r["offset_seconds"] <= s["samples"] / 16000
        ):
            raise ContractError("ABX token identity/bounds mismatch")
    for r in data["triplets"]:
        ids = tuple(r[k] for k in ["a", "b", "x"])
        if len(set(ids)) != 3 or ids in seen:
            raise ContractError("ABX triplet duplicated")
        seen.add(ids)
        a, b, x = [items[k] for k in ids]
        if (
            a["phone"] != x["phone"]
            or a["phone"] == b["phone"]
            or len({v["context"] for v in [a, b, x]}) != 1
            or a["speaker"] != b["speaker"]
        ):
            raise ContractError("ABX label contract mismatch")
        if r["condition"] != (
            "within_speaker" if a["speaker"] == x["speaker"] else "across_speaker"
        ):
            raise ContractError("ABX condition mismatch")
        for v in [a, b, x]:
            proof = verified[v["recording_id"]]
            if (
                proof["status"] != "ok"
                or proof["identical_full_source_pcm"] is not True
                or proof["abxls_pcm_sha256"] != proof["frozen_librispeech_pcm_sha256"]
                or proof["frozen_librispeech_pcm_sha256"]
                != originals[v["recording_id"]]["decoded_pcm_sha256"]
            ):
                raise ContractError("ABX PCM identity unverified")
    return data, items, path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--context", required=True)
    p.add_argument("--method", choices=["candidate", "pml"], required=True)
    p.add_argument("--view", choices=list(DIMENSIONS), required=True)
    a = p.parse_args()
    ctx = Context(a.context, "abx")
    train, train_path = moment_records(ctx, "train", a.method, a.view)
    test, test_path = moment_records(ctx, "test", a.method, a.view)
    if any(r["status"] != "measured" for r in train):
        raise ContractError("Full train120 required; no reduced calibration fit")
    center, scale, scale_info = recording_equal_scale(
        [r["mean"] for r in train], [r["variance"] for r in train]
    )
    data, items, abx_path = fixed_abx(ctx)
    audit_path, source = ctx.input_audit("test", a.method)
    records = {r["case"]: r for r in source["rows"]}
    valid = {r["case"] for r in test if r["status"] == "measured"}
    sys.path.insert(0, ctx.config["repository"])
    from vocoderbench.assessment.representation import dtw

    stats_path = resolve(ctx.root, ctx.config["abx_statistics"])
    sys.path.insert(0, str(stats_path.parent))
    import frozen_abx_statistics as stats

    out = ctx.root / "results/abx" / a.method / a.view
    contract = {
        "source_freeze_sha256": ctx.sig,
        "view": a.view,
        "method": a.method,
        "train_summary_sha256": sha(train_path),
        "test_summary_sha256": sha(test_path),
        "test_input_audit_sha256": sha(audit_path),
        "fixed_triplets_sha256": sha(abx_path),
        "distance": "euclidean total-cost-minimizing path / chosen path length",
        "max_cells": 2000000,
        "tie_atol": 1e-12,
        "scale": "centered recording-equal total variance",
        "scale_info": scale_info,
    }
    if out.exists():
        raise ContractError("ABX attempt exists; preserve before explicit new attempt")
    out.mkdir(parents=True)
    write(out / "started.json", contract)
    np.savez_compressed(out / "calibration.npz", center=center, scale=scale)

    @lru_cache(maxsize=2)
    def features(case):
        return observe(ctx, a.method, a.view, records[case], audit_path.parent)[:2]

    def token(key):
        item = items[key]
        m, t = features(item["recording_id"])
        lo, hi = np.searchsorted(
            t, [item["onset_seconds"], item["offset_seconds"]], side="left"
        )
        if lo == hi:
            raise ValueError("No actual native frame in token")
        return m[lo:hi]

    pairs = sorted(
        {tuple(sorted([r[k], r["x"]])) for r in data["triplets"] for k in ["a", "b"]}
    )
    distances = {}
    for i, pair in enumerate(pairs):
        ctx.verify()
        row = {"tokens": list(pair), "status": "unavailable", "value": None}
        if all(items[key]["recording_id"] in valid for key in pair):
            try:
                value = dtw(
                    token(pair[0]), token(pair[1]), "euclidean", 1 / scale, 2000000
                )
                if not np.isfinite(value):
                    raise ValueError("Nonfinite DTW")
                row.update(status="measured", value=float(value))
            except (ValueError, FloatingPointError):
                logging.exception("ABX distance failed: %s", pair)
                row.update(
                    status="failed",
                    reason_code="distance_failed",
                    traceback=traceback.format_exc(),
                )
        else:
            row["reason_code"] = "feature_unavailable"
        write(out / "pairs" / f"{i:05d}.json", row)
        distances[pair] = row
    raw = []
    for r in data["triplets"]:
        values = [distances[tuple(sorted([r[k], r["x"]]))]["value"] for k in ["a", "b"]]
        if any(v is None for v in values):
            raw.append({**r, "status": "unavailable", "error": None})
        else:
            da, db = values
            tie = abs(da - db) <= 1e-12
            raw.append(
                {
                    **r,
                    "status": "measured",
                    "distance_ax": da,
                    "distance_bx": db,
                    "tie": tie,
                    "error": 0.5 if tie else float(da > db),
                }
            )
    write(out / "raw-triplets.json", raw)
    usable = [r for r in raw if r["status"] == "measured"]
    summaries = {}
    if usable:
        keys, values, counts = stats.make_strata(
            usable, np.array([[r["error"]] for r in usable]), items
        )
        point, arrays, metadata = stats.bootstrap(keys, values, counts)
        np.savez_compressed(out / "bootstrap.npz", **arrays)
        for i, condition in enumerate(stats.CONDITIONS):
            for j, estimand in enumerate(stats.ESTIMANDS):
                draws = arrays["values"][:, i, j, 0]
                draws = draws[np.isfinite(draws)]
                value = point[i, j, 0]
                summaries[condition + "/" + estimand] = {
                    "value": float(value) if np.isfinite(value) else None,
                    "ci95": np.quantile(draws, [0.025, 0.975]).tolist()
                    if len(draws)
                    else None,
                    "rank": None,
                }
    moment_records(ctx, "train", a.method, a.view)
    moment_records(ctx, "test", a.method, a.view)
    if (
        sha(train_path) != contract["train_summary_sha256"]
        or sha(test_path) != contract["test_summary_sha256"]
    ):
        raise ContractError("Moments changed during ABX")
    ctx.input_audit("test", a.method)
    ctx.end()
    write(
        out / "summary.json",
        {
            "validation_state": "validated_end",
            "contract": contract,
            "planned_triplets": 4960,
            "measured_triplets": len(usable),
            "summaries": summaries,
            "raw_sha256": sha(out / "raw-triplets.json"),
            "comparison": "own support only; paired support comparison required before ranking",
            "artifacts": [
                {"path": str(p.relative_to(out)), "sha256": sha(p)}
                for p in sorted(out.rglob("*"))
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
        logging.exception("ABX operational/contract interruption")
        raise
