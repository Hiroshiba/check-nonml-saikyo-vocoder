"""Frozen PML payload native edit evaluation. No new synthesis algorithm or tests."""

from portable_context import ROOT, REPO

from pathlib import Path
import json
import hashlib
import time
import traceback
import argparse
import numpy as np

from vocoderbench.pml import load, decode, edit_parameters
from vocoderbench.assessment.common import Inputs, NotApplicable
from vocoderbench.assessment.controls import pitch, gain, interference

CONDITIONS = {
    "pitch_minus3": {"pitch_semitones": -3.0},
    "pitch_plus3": {"pitch_semitones": 3.0},
    "gain_minus6": {"gain_db": -6.0},
    "gain_plus6": {"gain_db": 6.0},
}


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(".part")
    t.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    t.replace(p)


def freeze(p, v):
    if p.exists() and read(p) != v:
        raise ValueError("Frozen contract mismatch: " + str(p))
    if not p.exists():
        write(p, v)


def audio(path):
    y = np.load(path, allow_pickle=False)
    return dict(
        path=str(path),
        sha256=sha(path),
        file_sha256=sha(path),
        float64_sha256=hashlib.sha256(y.astype("<f8").tobytes()).hexdigest(),
        samples=len(y),
        sample_rate=16000,
        peak=float(abs(y).max()),
        over_one_samples=int((abs(y) > 1).sum()),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["decode", "measure"], required=True)
    args = ap.parse_args()
    if not (ROOT / "native-summary.json").exists():
        raise RuntimeError("Native RTF phase not finished")
    spec = read(ROOT / "input-contract.json")
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        method=native["method"],
        seed=0,
        source_contract_sha256=sha(ROOT / "native-contract.json"),
        input_sha256=sha(ROOT / "input-contract.json"),
        driver_sha256=sha(__file__),
        conditions=CONDITIONS,
        reference="same method full-length unedited native decode",
        pitch_estimator="existing YIN 65..700 Hz; 80ms window/10ms hop; out-of-range separately counted",
        gain="FWCEP coefficient0 native edit; no output gain/clip/normalization",
        unsupported=[
            "time_scale1p25",
            "slope_minus3",
            "slope_plus3",
            "interpolation",
            "requantization",
        ],
        timing="edit decoding wall only, not fair native speed ranking",
        repetitions=1,
    )
    out = ROOT / "extended"
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    inputs = Inputs(ROOT)
    for c in spec["cases"]:
        source = ROOT / "native" / c["id"] / "record.json"
        native_row = read(source)
        if native_row["status"] == "measured":
            for k in ["audio", "payload"]:
                if sha(native_row[k]["path"]) != native_row[k]["sha256"]:
                    raise ValueError("Native artifact changed")
        for name, kwargs in CONDITIONS.items():
            folder = out / "native" / c["id"] / name
            target = folder / "record.json"
            if args.stage == "decode":
                if target.exists():
                    old = read(target)
                    if old["contract_sha256"] != sig or old[
                        "native_record_sha256"
                    ] != sha(source):
                        raise ValueError("Resume contract/input mismatch")
                    if (
                        old["status"] == "measured"
                        and sha(old["audio"]["path"]) != old["audio"]["sha256"]
                    ):
                        raise ValueError("Edit audio changed")
                    continue
                row = dict(
                    case=c["id"],
                    speaker=c["speaker"],
                    method=native["method"],
                    condition=name,
                    contract_sha256=sig,
                    native_record_sha256=sha(source),
                    status="running",
                    edit=kwargs,
                )
                try:
                    if native_row["status"] != "measured":
                        row.update(
                            status="upstream_failed",
                            reason=native_row.get("reason", "native encode failed"),
                        )
                    else:
                        p = load(native_row["payload"]["path"])
                        try:
                            p = edit_parameters(p, **kwargs)
                        except ValueError as e:
                            row.update(
                                status="unsupported",
                                reason=str(e),
                                scope="fixed parameter domain; not skipped success",
                            )
                        else:
                            start = time.perf_counter()
                            y = decode(p)
                            wall = time.perf_counter() - start
                            folder.mkdir(parents=True, exist_ok=True)
                            path = folder / "wave.npy"
                            np.save(path, y, allow_pickle=False)
                            row.update(
                                status="measured",
                                audio=audio(path),
                                decode_wall_seconds=wall,
                                controls={
                                    "control": "pitch" if "pitch" in name else "gain",
                                    "amount": next(iter(kwargs.values())),
                                },
                            )
                except Exception as e:
                    row.update(
                        status="failed", reason=str(e), traceback=traceback.format_exc()
                    )
                write(target, row)
            else:
                dest = out / "measurements" / f"{c['id']}__{name}.json"
                if dest.exists():
                    old = read(dest)
                    if (
                        old["contract_sha256"] != sig
                        or old.get("edited_record_sha256") != sha(target)
                        or old.get("native_record_sha256") != sha(source)
                    ):
                        raise ValueError("Measurement contract/input changed")
                    er = read(target)
                    if (
                        er["status"] == "measured"
                        and sha(er["audio"]["path"]) != er["audio"]["sha256"]
                    ):
                        raise ValueError("Edited audio changed")
                    continue
                row = dict(
                    case=c["id"],
                    speaker=c["speaker"],
                    condition=name,
                    contract_sha256=sig,
                    native_record_sha256=sha(source),
                    status="pending_audio",
                )
                if target.exists():
                    edit = read(target)
                    row["edited_record_sha256"] = sha(target)
                    if edit["status"] != "measured":
                        row.update(
                            status="upstream_failed",
                            reason=edit.get("reason"),
                            upstream_status=edit["status"],
                        )
                    else:
                        if sha(edit["audio"]["path"]) != edit["audio"]["sha256"]:
                            raise ValueError("Edit audio changed")
                        job = dict(reference=native_row["audio"], output=edit["audio"])
                        try:
                            value = (
                                pitch(
                                    {
                                        **job,
                                        "target_cents": kwargs["pitch_semitones"] * 100,
                                    },
                                    inputs,
                                )
                                if "pitch_semitones" in kwargs
                                else gain(
                                    {**job, "target_gain_db": kwargs["gain_db"]}, inputs
                                )
                            )
                            row.update(
                                status="measured"
                                if value["status"] == "ok"
                                else value["status"],
                                measurement=value,
                            )
                        except NotApplicable as e:
                            row.update(status="not_applicable", reason=str(e))
                        except Exception as e:
                            row.update(
                                status="failed",
                                reason=str(e),
                                traceback=traceback.format_exc(),
                            )
                if row["status"] != "pending_audio":
                    write(dest, row)
        if args.stage == "measure":
            dest = out / "measurements" / f"{c['id']}__gain_interference.json"
            if dest.exists():
                old = read(dest)
                paths = [
                    out / "native" / c["id"] / n / "record.json"
                    for n in ("gain_minus6", "gain_plus6")
                ]
                if old["contract_sha256"] != sig or old.get("source_record_sha256") != [
                    sha(p) for p in paths
                ]:
                    raise ValueError("Interference contract/input changed")
                for pth in paths:
                    er = read(pth)
                    if (
                        er["status"] == "measured"
                        and sha(er["audio"]["path"]) != er["audio"]["sha256"]
                    ):
                        raise ValueError("Interference audio changed")
            else:
                row = dict(
                    case=c["id"],
                    speaker=c["speaker"],
                    condition="gain_interference",
                    contract_sha256=sig,
                    native_record_sha256=sha(source),
                    status="pending_audio",
                )
                paths = [
                    out / "native" / c["id"] / n / "record.json"
                    for n in ("gain_minus6", "gain_plus6")
                ]
                if all(p.exists() for p in paths):
                    records = [read(p) for p in paths]
                    row["source_record_sha256"] = [sha(p) for p in paths]
                    if any(r["status"] != "measured" for r in records):
                        row.update(
                            status="upstream_failed",
                            upstream_statuses=[r["status"] for r in records],
                        )
                    else:
                        try:
                            for r in records:
                                if sha(r["audio"]["path"]) != r["audio"]["sha256"]:
                                    raise ValueError("Edit audio changed")
                            scales = {
                                "pitch_cents": 100.0,
                                "level_db": 1.0,
                                "slope_db_per_octave": 1.0,
                                "duration_seconds": 0.1,
                            }
                            job = dict(
                                low_hz=300.0,
                                high_hz=5000.0,
                                attribute_scales=scales,
                                sweeps=[
                                    dict(
                                        control="gain",
                                        control_unit="dB",
                                        delta=6.0,
                                        control_scale=1.0,
                                        minus=records[0]["audio"],
                                        plus=records[1]["audio"],
                                        expected_response=dict(
                                            pitch_cents=0.0,
                                            level_db=1.0,
                                            slope_db_per_octave=0.0,
                                            duration_seconds=0.0,
                                        ),
                                    )
                                ],
                            )
                            value = interference(job, inputs)
                            row.update(
                                status="measured"
                                if value["status"] == "ok"
                                else value["status"],
                                measurement=value,
                            )
                        except Exception as e:
                            row.update(
                                status="failed",
                                reason=str(e),
                                traceback=traceback.format_exc(),
                            )
                    write(dest, row)
        print(args.stage, c["id"], flush=True)
    write(
        out / f"{args.stage}-inventory.json",
        dict(
            contract_sha256=sig,
            planned_cases=len(spec["cases"]),
            conditions=list(CONDITIONS),
            records=[
                read(p)
                for p in sorted(
                    (
                        out / ("native" if args.stage == "decode" else "measurements")
                    ).rglob("record.json" if args.stage == "decode" else "*.json")
                )
            ],
        ),
    )


if __name__ == "__main__":
    main()
