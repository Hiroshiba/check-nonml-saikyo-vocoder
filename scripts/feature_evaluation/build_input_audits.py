"""Read-only full120 source/payload audit from all ten terminal generation chunks."""

import argparse
import hashlib
from pathlib import Path
import sys
import numpy as np
from contracts import read, write, sha, resolve, ContractError


def checked_receipt(path, plan, plan_sha, chunk, stage):
    data = read(path)
    if (
        data["schema_version"] != 2
        or data["validation_state"] != "validated_end"
        or data["stage_id"] != stage
        or data["run_plan_sha256"] != plan_sha
        or data["chunk_id"] != chunk["id"]
        or data["case_ids"] != chunk["case_ids"]
        or data["frozen_digests"] != plan["frozen_digests"]
    ):
        raise ContractError("Generation terminal receipt mismatch")
    for item in data["artifacts"]:
        resolve(path.parent, item)
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--bindings", type=Path, required=True)
    p.add_argument("--candidate-run", type=Path, required=True)
    p.add_argument("--pml-receipts", type=Path, required=True)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    plan = read(a.plan)
    plan_sha = sha(a.plan)
    ids = [r["case"] for r in plan["cases"]]
    if len(ids) != 120 or len(set(ids)) != 120 or len(plan["chunks"]) != 10:
        raise ContractError("Fixed120/ten chunks required")
    evidence = {
        str(a.plan.resolve()): plan_sha,
        str(a.bindings.resolve()): sha(a.bindings),
    }
    bindings = read(a.bindings)
    for kind, digest in plan["frozen_digests"].items():
        path = (a.bindings.parent / bindings[kind]["path"]).resolve()
        if sha(path) != digest:
            raise ContractError("Common binding changed")
        evidence[str(path)] = digest
        data = read(path)
        if kind != "cohort":
            for item in data["files"]:
                file = resolve(path.parent, item)
                evidence[str(file)] = item["sha256"]
    run = a.candidate_run.resolve()
    candidate = []
    pml = []
    freeze_path = run / "source-review-manifest.json"
    if evidence.get(str(freeze_path)) != sha(freeze_path):
        raise ContractError("Candidate freeze not bound by common generation manifest")
    candidate_freeze = read(freeze_path)
    for group, base in [
        ("local_source_hashes", run),
        ("external_source_hashes", run.parent),
    ]:
        for name, digest in candidate_freeze[group].items():
            file = (base / name).resolve()
            if sha(file) != digest:
                raise ContractError("Candidate source/runtime changed")
            evidence[str(file)] = digest
    pml_paths = read(a.pml_receipts)
    if len(pml_paths) != 10:
        raise ContractError("Ten PML terminal receipts required")
    for file in (a.repository.resolve() / "vocoderbench/pml").glob("*.py"):
        if evidence.get(str(file)) != sha(file):
            raise ContractError("PML loader source is outside frozen common bindings")
    sys.path.insert(0, str(a.repository.resolve()))
    from vocoderbench.pml import load

    for chunk, pml_item in zip(plan["chunks"], pml_paths):
        receipt = run / "chunk-receipts" / (chunk["id"] + ".json")
        data = checked_receipt(receipt, plan, plan_sha, chunk, "candidate-generation")
        evidence[str(receipt)] = sha(receipt)
        if data["source_freeze_sha256"] != sha(run / "source-review-manifest.json"):
            raise ContractError("Wrong candidate freeze")
        for case in chunk["case_ids"]:
            path = run / "case-status" / (case + ".json")
            row = read(path)
            spec = next(s for s in plan["cases"] if s["case"] == case)
            if (
                row["case"] != case
                or row["source_input_sha256"] != spec["input_sha256"]
            ):
                raise ContractError("Candidate case/input changed")
            evidence[str(path)] = sha(path)
            for item in row["retained_files"]:
                file = resolve(run, item)
                evidence[str(file)] = item["sha256"]
            for stage in row["stages"]:
                for pk, hk in [("sourcepath", "sha256"), ("logpath", "log_sha256")]:
                    if stage.get(hk):
                        file = run / stage[pk]
                        if sha(file) != stage[hk]:
                            raise ContractError("Candidate stage evidence changed")
                        evidence[str(file)] = stage[hk]
            if row.get("archive"):
                archive_receipt = resolve(
                    run,
                    {
                        "path": row["archive"]["receipt"],
                        "sha256": row["archive"]["receipt_sha256"],
                    },
                )
                d = read(archive_receipt)
                archive = resolve(
                    run, {"path": d["archive"], "sha256": d["archive_sha256"]}
                )
                evidence[str(archive_receipt)] = sha(archive_receipt)
                evidence[str(archive)] = d["archive_sha256"]
            native = run / "implementation-native/results" / case
            ok = any(
                s["stage"] == "native-analysis" and s["status"] == "ok"
                for s in row["stages"]
            )
            item = {
                "case": case,
                "speaker": spec["speaker"],
                "samples": spec["samples"],
                "sample_rate": spec["sample_rate"],
                "input_sha256": spec["input_sha256"],
                "status": "measured" if ok else "upstream_failed",
            }
            if ok:
                for key, rel in [
                    ("payload_manifest", "payload/manifest.json"),
                    ("raw_f0", "raw_f0.npy"),
                    ("input_times", "input_times.npy"),
                    ("original_voiced_mask", "original_voiced_mask.npy"),
                ]:
                    file = native / rel
                    if str(file) not in evidence:
                        raise ContractError(
                            "Native feature asset not in terminal retained inventory"
                        )
                    item[key] = {"path": str(file), "sha256": evidence[str(file)]}
            candidate.append(item)
        path = resolve(a.pml_receipts.parent, pml_item)
        pml_receipt = checked_receipt(path, plan, plan_sha, chunk, "pml-generation")
        evidence[str(path)] = sha(path)
        summary = path.parent / "summary.json"
        evidence[str(summary)] = sha(summary)
        records = read(summary)["cases"]
        if not any(
            (path.parent / item["path"]).resolve() == summary.resolve()
            and item["sha256"] == sha(summary)
            for item in pml_receipt["artifacts"]
        ):
            raise ContractError("PML summary absent from terminal receipt")
        if [r["case"] for r in records] != chunk["case_ids"]:
            raise ContractError("PML case order mismatch")
        for record in records:
            case = record["case"]
            spec = next(s for s in plan["cases"] if s["case"] == case)
            if (
                record["validation_state"] != "validated_end"
                or record["input_sha256"] != spec["input_sha256"]
                or record["encode_status"] not in ["measured", "failed"]
            ):
                raise ContractError("PML encode not terminal")
            for item in record["artifacts"]:
                file = resolve(path.parent, item)
                evidence[str(file)] = item["sha256"]
            item = {
                "case": case,
                "speaker": spec["speaker"],
                "samples": spec["samples"],
                "sample_rate": spec["sample_rate"],
                "input_sha256": spec["input_sha256"],
                "status": record["encode_status"],
            }
            if record["encode_status"] == "measured":
                payload = resolve(path.parent, record["payload"])
                params = load(payload)
                audit = record["encode_audit"]
                if (
                    params.n_samples != spec["samples"]
                    or params.sample_rate != 16000
                    or params.seed != 0
                    or params.pitch_shift_semitones != 0
                ):
                    raise ContractError("PML original params contract mismatch")
                for name, desc in audit["fields"].items():
                    values = np.ascontiguousarray(getattr(params, name))
                    if (
                        list(values.shape) != desc["shape"]
                        or values.dtype.str != desc["dtype"]
                        or hashlib.sha256(values.tobytes()).hexdigest()
                        != desc["sha256"]
                    ):
                        raise ContractError("PML encode array audit changed")
                item["payload"] = {"path": str(payload), "sha256": sha(payload)}
                evidence[str(payload)] = sha(payload)
            pml.append(item)
    if [r["case"] for r in candidate] != ids or [r["case"] for r in pml] != ids:
        raise ContractError("Full120 audit coverage mismatch")
    for file, digest in evidence.items():
        if sha(file) != digest:
            raise ContractError("Evidence changed during final audit")
    common = {
        "validation_state": "validated_end",
        "planned_cases": 120,
        "case_ids": ids,
        "run_plan_sha256": plan_sha,
        "frozen_digests": plan["frozen_digests"],
        "artifacts": [
            {"path": file, "sha256": digest}
            for file, digest in sorted(evidence.items())
        ],
    }
    write(
        a.output / "candidate-full120-audit.json",
        {**common, "kind": "candidate-full120", "rows": candidate},
    )
    write(
        a.output / "pml-full120-encode-audit.json",
        {**common, "kind": "pml-encode-full120", "rows": pml},
    )


if __name__ == "__main__":
    main()
