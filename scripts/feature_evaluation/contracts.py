"""Frozen scientific input/output contracts; not a test harness."""

import hashlib
import json
import os
import sys
from pathlib import Path


class ContractError(RuntimeError):
    pass


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def resolve(base, row):
    path = (Path(base) / row["path"]).resolve()
    if sha(path) != row["sha256"]:
        raise ContractError("Artifact changed: " + str(path))
    return path


def audit(path, case_ids, kind):
    path = Path(path)
    data = read(path)
    if (
        data["validation_state"] != "validated_end"
        or data["kind"] != kind
        or data["case_ids"] != case_ids
        or len(data["rows"]) != len(case_ids)
    ):
        raise ContractError("Incomplete/wrong input audit")
    if [r["case"] for r in data["rows"]] != case_ids or any(
        r["status"] not in ["measured", "failed", "upstream_failed", "not_applicable"]
        for r in data["rows"]
    ):
        raise ContractError("Audit rows must cover all cases terminally")
    if not data["artifacts"]:
        raise ContractError("Audit evidence missing")
    for item in data["artifacts"]:
        resolve(path.parent, item)
    return data


class Context:
    def __init__(self, directory, stage):
        self.root = Path(directory).resolve()
        self.config = read(self.root / "settings.json")
        self.auth = read(self.root / "execution-authorization.json")
        self.freeze_path = self.root / "source-freeze.json"
        self.sig = sha(self.freeze_path)
        if (
            self.auth.get("approved") is not True
            or self.auth.get("source_freeze_sha256") != self.sig
            or stage not in self.auth.get("stages", [])
        ):
            raise PermissionError("Feature science is not authorized")
        for key in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            if os.environ.get(key) != "1":
                raise RuntimeError("Feature science requires one thread")
        if Path(sys.prefix).resolve() != Path(self.config["python_prefix"]).resolve():
            raise RuntimeError("Wrong feature runtime")
        self.verify()
        self.train = read(resolve(self.root, self.config["train_inputs"]))
        self.test = read(resolve(self.root, self.config["test_inputs"]))
        if (
            len(self.train) != 120
            or len(self.test) != 120
            or len({r["speaker"] for r in self.train}) != 40
            or len({r["speaker"] for r in self.test}) != 40
        ):
            raise ValueError("Fixed train/test cardinality mismatch")
        from collections import Counter

        for specs in [self.train, self.test]:
            if len({r["case"] for r in specs}) != 120 or set(
                Counter(r["speaker"] for r in specs).values()
            ) != {3}:
                raise ContractError("Expected unique120 and40 speakers times3")
            if any(
                r["sample_rate"] != 16000 or r["input"]["sha256"] != r["input_sha256"]
                for r in specs
            ):
                raise ContractError("Input rate/hash contract mismatch")
        for key in [
            "case",
            "speaker",
            "source_utterance_id",
            "input_sha256",
            "source_sha256",
            "source_pcm_sha256",
        ]:
            if {r[key] for r in self.train} & {r[key] for r in self.test}:
                raise ValueError("Train/test leakage: " + key)
        self.plan = resolve(self.root, self.config["run_plan"])
        self.candidate = self.input_audit("test", "candidate")[1]
        self.pml = self.input_audit("test", "pml")[1]
        self.stage = stage

    def verify(self):
        if sha(self.freeze_path) != self.sig:
            raise RuntimeError("Feature source freeze changed")
        for item in read(self.freeze_path)["files"]:
            resolve(self.root, item)
        cfg = self.config
        import shutil

        if (
            shutil.disk_usage(self.root).free
            < cfg["minimum_free_bytes"] + cfg["active_headroom_bytes"]
        ):
            raise RuntimeError("Disk floor/headroom unavailable")

    def input_audit(self, split, method):
        if split == "test":
            record = (
                self.auth["candidate_full120_audit"]
                if method == "candidate"
                else self.auth["pml_full120_encode_audit"]
            )
        elif split == "train":
            record = self.auth["train_generation_audits"][method]
        else:
            raise ValueError("Unknown split")
        path = resolve(self.root, record)
        ids = [r["case"] for r in (self.train if split == "train" else self.test)]
        kind = (
            {"candidate": "candidate-full120", "pml": "pml-encode-full120"}
            if split == "test"
            else {"candidate": "candidate-train120", "pml": "pml-train120"}
        )[method]
        data = audit(path, ids, kind)
        specs = self.train if split == "train" else self.test
        for row, spec in zip(data["rows"], specs):
            for key in ["case", "speaker", "samples", "sample_rate", "input_sha256"]:
                if row[key] != spec[key]:
                    raise ContractError("Audit input identity mismatch: " + key)
        if split == "test" and data["run_plan_sha256"] != sha(self.plan):
            raise ContractError("Test audit common plan mismatch")
        return path, data

    def end(self):
        self.verify()
        self.input_audit("test", "candidate")
        self.input_audit("test", "pml")
