"""Export saved PML representation without quantization or decoder changes."""

from portable_context import REPO

from pathlib import Path
import traceback
import numpy as np
from run_edits import ROOT, sha, read, write, freeze
from vocoderbench.pml.storage import load_parameters as load


def matrix(p):
    # float64 widening preserves f0 float64, fwcep float32 values, and mask bits exactly.
    return np.column_stack((p.f0, p.fwcep, p.noise_mask)).astype(np.float64)


def main():
    spec = read(ROOT / "input-contract.json")
    out = ROOT / "extended/features"
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        driver_sha256=sha(__file__),
        shared_driver_sha256=sha(Path(__file__).with_name("run_edits.py")),
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        dimension_count=2110,
        columns=[
            dict(
                field="continuous_synthesis_clock_hz", width=1, source_dtype="float64"
            ),
            dict(field="fwcep", width=60, source_dtype="float32"),
            dict(
                field="noise_mask_before_lowband_extension_smoothing",
                width=2049,
                source_dtype="bool",
            ),
        ],
        frame_step_seconds=0.005,
        export_dtype="float64",
        storage="lossless compressed npz",
        interpretation="readout-only; no PDD; positive F0 in unvoiced regions is scheduler not voicing; decoder unchanged",
        calibration="train only; speaker and utterance disjoint train/evaluation; no fitted statistics here",
        unsupported=["interpolation", "requantization"],
        planned_cases=len(spec["cases"]),
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    rows = []
    for c in spec["cases"]:
        dest = out / c["id"] / "record.json"
        if dest.exists():
            row = read(dest)
            src = ROOT / "native" / c["id"] / "record.json"
            nr = read(src)
            if row["contract_sha256"] != sig or row["native_record_sha256"] != sha(src):
                raise ValueError("Feature contract/input changed")
            if (
                nr["status"] == "measured"
                and sha(nr["payload"]["path"]) != nr["payload"]["sha256"]
            ):
                raise ValueError("Payload changed")
            if (
                row["status"] == "measured"
                and sha(row["features"]["path"]) != row["features"]["sha256"]
            ):
                raise ValueError("Feature file changed")
            rows.append(row)
            continue
        source = ROOT / "native" / c["id"] / "record.json"
        r = read(source)
        row = dict(
            case=c["id"],
            speaker=c["speaker"],
            contract_sha256=sig,
            native_record_sha256=sha(source),
        )
        try:
            if r["status"] != "measured":
                row.update(status="upstream_failed", reason=r.get("reason"))
            else:
                if sha(r["payload"]["path"]) != r["payload"]["sha256"]:
                    raise ValueError("Payload changed")
                p = load(r["payload"]["path"])
                m = matrix(p)
                path = dest.parent / "features.npz"
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    path,
                    features=m,
                    times=p.times,
                    mean=m.mean(axis=0),
                    second_moment=(m * m).mean(axis=0),
                )
                duration = p.n_samples / p.sample_rate
                row.update(
                    status="measured",
                    features=dict(
                        path=str(path),
                        sha256=sha(path),
                        bytes=path.stat().st_size,
                        shape=list(m.shape),
                    ),
                    payload=dict(
                        path=r["payload"]["path"],
                        sha256=r["payload"]["sha256"],
                        actual_bytes=Path(r["payload"]["path"]).stat().st_size,
                        seconds=duration,
                        kbps=8
                        * Path(r["payload"]["path"]).stat().st_size
                        / duration
                        / 1000,
                    ),
                    logical_per_frame=dict(
                        fwcep_bytes=240,
                        f0_bytes=8,
                        packed_nm_bytes=257,
                        total_bytes=505,
                    ),
                    note="feature export bytes are not decoder bitrate; payload actual file includes header",
                )
        except Exception as e:
            row.update(status="failed", reason=str(e), traceback=traceback.format_exc())
        write(dest, row)
        rows.append(row)
    write(out / "inventory.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    main()
