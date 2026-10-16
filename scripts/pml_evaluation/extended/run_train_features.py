"""Independent fixed dev-clean train-only PML features; no resynthesis."""

from portable_context import REPO, CORPORA
from pathlib import Path
import argparse
import traceback
import time
import numpy as np
from run_edits import ROOT, read, write, freeze, sha
from extract_features import matrix
from vocoderbench.pml import encode
from vocoderbench.metrics import estimate_f0_yin
from vocoderbench.assessment.acoustics import spectral_slope
from vocoderbench.assessment.common import NotApplicable


def targets(x):
    f = estimate_f0_yin(x, 16000)["f0_hz"]
    v = f > 0
    power = float(np.mean(x * x))
    try:
        s = spectral_slope(x, 16000, 300, 5000)
    except NotApplicable:
        s = None
    return dict(
        log_f0=float(np.log(f[v]).mean()) if v.any() else None,
        rms_dbfs=10 * np.log10(power) if power > 0 else None,
        spectral_slope=s,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    corpora = CORPORA
    manifest = corpora / "readout-train/inputs.json"
    train = read(manifest)
    evaluation = read(ROOT / "input-contract.json")["cases"]
    out = ROOT / "extended/train"
    if len(train) != 120 or len({r["speaker"] for r in train}) != 40:
        raise ValueError("Fixed train size differs")
    for key in ["id", "speaker"]:
        if {r[key] for r in train} & {r[key] for r in evaluation}:
            raise ValueError("Train/evaluation overlap")
    if {r["sha256"] for r in train} & {r["input"]["sha256"] for r in evaluation}:
        raise ValueError("Train/evaluation audio overlap")
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        drivers={
            p.name: sha(p)
            for p in [
                Path(__file__),
                Path(__file__).with_name("run_edits.py"),
                Path(__file__).with_name("extract_features.py"),
            ]
        },
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        original_train_manifest_sha256=sha(manifest),
        evaluation_manifest_sha256=sha(ROOT / "input-contract.json"),
        role="train only, fixed120/40 independent speakers; no resynthesis",
        features="F0float64 FWCEP60float32 NM2049bool widened exactly to2110 float64; no PDD",
        seed=0,
        statistics="recording equal means and second moments; no evaluation fitting",
        targets="existing YIN65..700 log F0 mean voiced, full RMS dBFS, spectral slope300..5000",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    rows = []
    for r in train:
        path = corpora / "readout-train/audio" / f"{r['id']}.npy"
        dest = out / r["id"] / "record.json"
        if not path.exists():
            raise FileNotFoundError(path)
        if sha(path) != r["sha256"]:
            raise ValueError("Train input changed")
        if dest.exists():
            row = read(dest)
            if row["contract_sha256"] != sig or row["input_sha256"] != r["sha256"]:
                raise ValueError("Train resume mismatch")
            if (
                row["status"] == "measured"
                and sha(row["moments"]["path"]) != row["moments"]["sha256"]
            ):
                raise ValueError("Train moments changed")
            rows.append(row)
            continue
        row = dict(
            case=r["id"],
            speaker=r["speaker"],
            input_sha256=r["sha256"],
            contract_sha256=sig,
            status="running",
        )
        try:
            x = np.load(path, allow_pickle=False)
            tick = time.perf_counter()
            p = encode(x, 16000, seed=0)
            m = matrix(p)
            wall = time.perf_counter() - tick
            dest.parent.mkdir(parents=True, exist_ok=True)
            mom = dest.parent / "moments.npz"
            np.savez_compressed(mom, mean=m.mean(0), second_moment=(m * m).mean(0))
            row.update(
                status="measured",
                moments=dict(path=str(mom), sha256=sha(mom)),
                shape=list(m.shape),
                targets=targets(x),
                analysis_wall_seconds=wall,
            )
        except Exception as e:
            row.update(status="failed", reason=str(e), traceback=traceback.format_exc())
        write(dest, row)
        rows.append(row)
        write(out / "progress.json", dict(completed=len(rows), planned=120))
        print(r["id"], row["status"], flush=True)
    write(out / "summary.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    main()
