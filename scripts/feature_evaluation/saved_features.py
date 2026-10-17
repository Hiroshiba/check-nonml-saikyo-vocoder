"""Load immutable moment/target records with full denominator preservation."""

import numpy as np
from contracts import read, resolve, sha, ContractError
from observations import DIMENSIONS


def moment_records(ctx, split, method, view):
    base = ctx.root / "results" / split / method / view
    path = base / "summary.json"
    summary = read(path)
    specs = ctx.train if split == "train" else ctx.test
    ids = [r["case"] for r in specs]
    source, _ = ctx.input_audit(split, method)
    wanted = {
        "source_freeze_sha256": ctx.sig,
        "split": split,
        "method": method,
        "view": view,
        "input_audit_sha256": sha(source),
    }
    if (
        len(summary["rows"]) != 120
        or summary["validation_state"] != "validated_end"
        or summary["case_ids"] != ids
        or summary["contract"] != wanted
    ):
        raise ContractError("Moment terminal contract mismatch")
    rows = []
    for item, case in zip(summary["rows"], ids):
        if item["case"] != case:
            raise ContractError("Moment case order mismatch")
        record_path = resolve(base, item["record"])
        row = read(record_path)
        if (
            row["case"] != case
            or row["contract"] != wanted
            or row["status"] != item["status"]
        ):
            raise ContractError("Moment provenance mismatch")
        if row["status"] == "measured":
            moment_path = resolve(record_path.parent, row["moments"])
            with np.load(moment_path, allow_pickle=False) as z:
                mean = z["mean"]
                variance = z["centered_variance"]
                times = z["times"]
            if (
                mean.shape != (DIMENSIONS[view],)
                or variance.shape != mean.shape
                or not np.isfinite([mean, variance]).all()
                or np.any(variance < 0)
                or not np.isfinite(times).all()
                or times.ndim != 1
                or not len(times)
                or np.any(np.diff(times) <= 0)
            ):
                raise ContractError("Moment shape/finite/time mismatch")
            row = {**row, "mean": mean, "variance": variance}
        rows.append(row)
    if len(rows) != 120:
        raise ContractError("Moment count mismatch")
    return rows, path


def target_records(ctx, split):
    base = ctx.root / "results" / split / "targets"
    summary = read(base / "summary.json")
    specs = ctx.train if split == "train" else ctx.test
    wanted = {
        "source_freeze_sha256": ctx.sig,
        "split": split,
        "method": None,
        "view": None,
        "input_audit_sha256": None,
    }
    if (
        summary["contract"] != wanted
        or len(summary["rows"]) != 120
        or summary["validation_state"] != "validated_end"
        or summary["case_ids"] != [r["case"] for r in specs]
    ):
        raise ContractError("Target denominator mismatch")
    rows = []
    for item, spec in zip(summary["rows"], specs):
        path = resolve(base, item["record"])
        row = read(path)
        if (
            row["case"] != spec["case"]
            or item["case"] != spec["case"]
            or item["status"] != row["status"]
            or row["contract"] != wanted
        ):
            raise ContractError("Target provenance mismatch")
        rows.append(row)
    if len(rows) != 120:
        raise ContractError("Target count mismatch")
    return rows, base / "summary.json"
