"""Observe saved representations, retaining only centered moments and time coverage."""

import argparse
import logging
import traceback
import numpy as np
from contracts import Context, read, write, sha, resolve, ContractError
from moments import centered_moments
from observations import observe, DIMENSIONS, targets


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--context", required=True)
    p.add_argument("--split", choices=["train", "test"], required=True)
    p.add_argument("--method", choices=["candidate", "pml"])
    p.add_argument("--view", choices=list(DIMENSIONS))
    p.add_argument("--targets-only", action="store_true")
    a = p.parse_args()
    if a.targets_only and (a.method is not None or a.view is not None):
        p.error("targets-only must omit method/view")
    ctx = Context(a.context, "targets" if a.targets_only else "moments")
    specs = ctx.train if a.split == "train" else ctx.test
    if not a.targets_only and (not a.method or not a.view):
        p.error("method/view required")
    audit_path, data = (
        (None, None) if a.targets_only else ctx.input_audit(a.split, a.method)
    )
    records = {r["case"]: r for r in data["rows"]} if data else {}
    folder = (
        ctx.root
        / "results"
        / a.split
        / ("targets" if a.targets_only else a.method + "/" + a.view)
    )
    token = {
        "source_freeze_sha256": ctx.sig,
        "split": a.split,
        "method": a.method,
        "view": a.view,
        "input_audit_sha256": sha(audit_path) if audit_path else None,
    }
    rows = []
    for spec in specs:
        case = spec["case"]
        dest = folder / case
        path = dest / "record.json"
        ctx.verify()
        if path.exists():
            row = read(path)
            if row["contract"] != token or row["case"] != case:
                raise ContractError("Moment resume provenance changed")
            for item in row.get("artifacts", []):
                resolve(path.parent, item)
            rows.append(row)
            continue
        if dest.exists():
            raise ContractError(
                "Partial case retained; move whole attempt before retry"
            )
        dest.mkdir(parents=True)
        write(dest / "started.json", {"case": case, "contract": token})
        row = {
            "case": case,
            "speaker": spec["speaker"],
            "contract": token,
            "status": "failed",
            "artifacts": [],
        }
        if a.targets_only:
            source = resolve(ctx.root, spec["input"])
            try:
                row.update(status="measured", targets=targets(ctx, source, spec))
            except (ValueError, FloatingPointError):
                logging.exception("Target observation failed: %s", case)
                row.update(
                    reason_code="target_observation_failed",
                    traceback=traceback.format_exc(),
                )
        elif records[case]["status"] != "measured":
            row.update(status="upstream_failed", reason_code="payload_not_available")
        else:
            try:
                matrix, times, diag = observe(
                    ctx, a.method, a.view, records[case], audit_path.parent
                )
            except (ValueError, FloatingPointError):
                logging.exception("Feature observation failed: %s", case)
                row.update(
                    reason_code="feature_observation_failed",
                    traceback=traceback.format_exc(),
                )
            else:
                if matrix.shape[1] != DIMENSIONS[a.view]:
                    raise ContractError("Unexpected feature dimension")
                mean, variance = centered_moments(matrix)
                moment = dest / "moments.npz"
                np.savez_compressed(
                    moment, mean=mean, centered_variance=variance, times=times
                )
                row.update(
                    status="measured",
                    diagnostics=diag,
                    shape=list(matrix.shape),
                    moments={"path": moment.name, "sha256": sha(moment)},
                    artifacts=[{"path": moment.name, "sha256": sha(moment)}],
                )
                del matrix
        ctx.verify()
        write(path, row)
        rows.append(row)
    ctx.end()
    if audit_path:
        ctx.input_audit(a.split, a.method)
    summary = folder / "summary.json"
    result = {
        "validation_state": "validated_end",
        "contract": token,
        "planned_cases": 120,
        "case_ids": [r["case"] for r in specs],
        "rows": [
            {
                "case": r["case"],
                "status": r["status"],
                "record": {
                    "path": str(
                        (folder / r["case"] / "record.json").relative_to(folder)
                    ),
                    "sha256": sha(folder / r["case"] / "record.json"),
                },
            }
            for r in rows
        ],
    }
    if summary.exists():
        if read(summary) != result:
            raise ContractError("Terminal moment summary changed")
    else:
        write(summary, result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.captureWarnings(True)
    try:
        main()
    except BaseException:
        logging.exception("Operational/contract stop; no terminal receipt")
        raise
