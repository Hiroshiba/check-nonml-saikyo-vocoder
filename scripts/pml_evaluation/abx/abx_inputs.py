"""Fixed official subset ABX on PML readout, without new triplets or fitted eval scale."""

from portable_context import ROOT, REPO, CORPORA

import hashlib
import json
from pathlib import Path

import numpy as np

BASE = ROOT.parent


OUT = ROOT / "extended/abx"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    tmp.replace(path)


def freeze(path, data):
    if path.exists() and read(path) != data:
        raise ValueError(f"Frozen contract mismatch: {path}")
    if not path.exists():
        write(path, data)


def inputs():
    manifest = CORPORA / "abxls120-triphones.json"
    audit_path = CORPORA / "abxls120-source-identity.json"
    label = CORPORA / "preserved-sources/abx-labels/triphone-test-clean.item"
    original = REPO / "data/clean_speech_v1.json"
    data = read(manifest)
    if data["label_sha256"] != sha(label) or data[
        "frozen_audio_manifest_sha256"
    ] != sha(original):
        raise ValueError("ABX official label/original manifest hash mismatch")
    specs = read(ROOT / "input-contract.json")["cases"]
    train = read(CORPORA / "readout-train/inputs.json")
    if len(train) != 120 or len({r["speaker"] for r in train}) != 40:
        raise ValueError("Fixed train must contain 120 recordings/40 speakers")
    for key in ["id", "speaker"]:
        if {r[key] for r in specs} & {r[key] for r in train}:
            raise ValueError("Train/evaluation overlap: " + key)
    if {r["input"]["sha256"] for r in specs} & {r["sha256"] for r in train}:
        raise ValueError("Train/evaluation input hash overlap")
    known = {r["id"]: r for r in specs}
    originals = {r["id"]: r for r in read(original)["entries"]}
    items = {r["id"]: r for r in data["items"]}
    if len(items) != len(data["items"]):
        raise ValueError("Duplicate token ID")
    for item in items.values():
        spec = known[item["recording_id"]]
        if (
            item["speaker"] != spec["speaker"]
            or not 0
            <= item["onset_seconds"]
            < item["offset_seconds"]
            <= spec["input"]["excerpt_samples"] / 16000
        ):
            raise ValueError("Token source speaker/bounds mismatch")
    seen = set()
    for row in data["triplets"]:
        ids = tuple(row[k] for k in ("a", "b", "x"))
        if len(set(ids)) != 3 or ids in seen:
            raise ValueError("Duplicate triplet or repeated token")
        seen.add(ids)
        a, b, x = (items[k] for k in ids)
        cond = "within_speaker" if a["speaker"] == x["speaker"] else "across_speaker"
        if (
            a["phone"] != x["phone"]
            or a["phone"] == b["phone"]
            or len({r["context"] for r in (a, b, x)}) != 1
            or a["speaker"] != b["speaker"]
            or cond != row["condition"]
        ):
            raise ValueError("Triplet label/speaker contract mismatch")
    audit_rows = read(audit_path)["entries"]
    audit = {r["id"]: r for r in audit_rows}
    used = {
        items[k]["recording_id"]
        for row in data["triplets"]
        for k in (row["a"], row["b"], row["x"])
    }
    if len(audit) != len(audit_rows) or used - set(audit):
        raise ValueError("Incomplete official PCM identity audit")
    for identifier in used:
        r = audit[identifier]
        if (
            r["status"] != "ok"
            or r["identical_full_source_pcm"] is not True
            or r["abxls_pcm_sha256"] != r["frozen_librispeech_pcm_sha256"]
            or r["frozen_librispeech_pcm_sha256"]
            != originals[identifier]["decoded_pcm_sha256"]
        ):
            raise ValueError("Unverified official PCM identity: " + identifier)
    paths = [
        manifest,
        audit_path,
        label,
        original,
        ROOT / "input-contract.json",
        CORPORA / "readout-train/inputs.json",
    ]
    return data, items, specs, train, {str(p): sha(p) for p in paths}


def calibration(train):
    means, seconds, records, pending = [], [], {}, []
    for spec in train:
        path = ROOT / "extended/train" / spec["id"] / "record.json"
        if not path.exists():
            pending.append({"case": spec["id"], "status": "pending"})
            continue
        r = read(path)
        if r["status"] != "measured":
            pending.append(
                {"case": spec["id"], "status": r["status"], "reason": r.get("reason")}
            )
            continue
        if (
            r["input_sha256"] != spec["sha256"]
            or r["speaker"] != spec["speaker"]
            or r["contract_sha256"] != sha(ROOT / "extended/train/contract.json")
            or sha(r["moments"]["path"]) != r["moments"]["sha256"]
        ):
            raise ValueError("Train provenance mismatch: " + spec["id"])
        with np.load(r["moments"]["path"], allow_pickle=False) as z:
            m, s = z["mean"], z["second_moment"]
        if (
            m.shape != (2110,)
            or s.shape != m.shape
            or m.dtype != np.float64
            or s.dtype != np.float64
            or not np.isfinite([m, s]).all()
        ):
            raise ValueError("Train moment shape/dtype/finite mismatch")
        means.append(m)
        seconds.append(s)
        records[spec["id"]] = sha(path)
    if pending:
        write(
            OUT / "status.json",
            {
                "status": "pending"
                if any(r["status"] == "pending" for r in pending)
                else "incomplete",
                "reason": "full_train_required_no_reduced_fit",
                "issues": pending,
            },
        )
        return None
    center = np.mean(means, axis=0)
    scale = np.sqrt(np.maximum(np.mean(seconds, axis=0) - center**2, 0))
    return center, np.where(scale > 1e-12, scale, 1), records


def feature_records(specs):
    records = {}
    issues = []
    for spec in specs:
        path = ROOT / "extended/features" / spec["id"] / "record.json"
        if not path.exists():
            issues.append({"case": spec["id"], "status": "pending"})
            continue
        r = read(path)
        if r["status"] != "measured":
            issues.append({"case": spec["id"], "status": r["status"]})
            continue
        if (
            r["contract_sha256"] != sha(ROOT / "extended/features/contract.json")
            or r["native_record_sha256"]
            != sha(ROOT / "native" / spec["id"] / "record.json")
            or sha(r["features"]["path"]) != r["features"]["sha256"]
        ):
            raise ValueError("Evaluation feature provenance mismatch")
        records[spec["id"]] = r
    if any(r["status"] == "pending" for r in issues):
        write(OUT / "status.json", {"status": "pending", "issues": issues})
        return None
    return records, issues
