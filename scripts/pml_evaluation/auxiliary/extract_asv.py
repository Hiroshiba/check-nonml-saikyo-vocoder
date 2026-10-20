"""Frozen PML native representation on fixed full-length ASV human-rating inputs."""

from portable_context import ROOT, REPO, ASV_INPUT
from pathlib import Path
import hashlib
import time
import traceback
import numpy as np
from run_edits import read, write, freeze, sha
from extract_features import matrix
from vocoderbench.pml import encode

BASE = ROOT / "auxiliary"
INPUT = ASV_INPUT


def main():
    raise RuntimeError('旧PML版専用の新規生成は廃止しました。現在のRAW_FULLを旧方式名で生成しません。保存済み結果の読取り・集計とsource-freeze契約は維持します。')
    selection = read(INPUT / "selection.json")
    native = read(ROOT / "native-contract.json")
    for name, h in native["source_sha256"].items():
        if sha(REPO / name) != h:
            raise ValueError("Frozen source changed " + name)
    contract = dict(
        driver_sha256=sha(__file__),
        matrix_driver_sha256=sha(
            Path(__file__).parents[1] / "extended/extract_features.py"
        ),
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        selection_sha256=sha(INPUT / "selection.json"),
        role="full-length original recording features; not resynthesis/human MOS",
        features="native2110 float64 lossless widening F0 + FWCEP60 + NM2049; frame-equal mean",
        seed=0,
        threads=2,
        planned=105,
        available=104,
        calibration="independent dev-clean train120 recording-equal native-frame population moments; never fit on ASV",
        no_decode=True,
    )
    freeze(BASE / "contract.json", contract)
    sig = sha(BASE / "contract.json")
    rows = []
    for sample, speaker in selection["identities"].items():
        stem = Path(sample).stem
        path = INPUT / "audio-inputs" / f"asvspoof2019_{stem}.npy"
        dest = BASE / "features" / stem / "record.json"
        if not path.exists():
            row = dict(
                sample=sample,
                speaker=speaker,
                status="input_unavailable",
                contract_sha256=sig,
            )
            write(dest, row)
            rows.append(row)
            continue
        receipt = read(INPUT / "audio-records" / f"{stem}.json")
        h = sha(path)
        if h != receipt["input"]["sha256"]:
            raise ValueError("Restored input hash differs")
        if dest.exists():
            row = read(dest)
            if row["contract_sha256"] != sig or row.get("input_sha256") != h:
                raise ValueError("Resume provenance differs")
            if (
                row["status"] == "measured"
                and sha(row["mean"]["path"]) != row["mean"]["sha256"]
            ):
                raise ValueError("Mean changed")
            rows.append(row)
            continue
        row = dict(
            sample=sample,
            speaker=speaker,
            input_sha256=h,
            input_receipt_sha256=sha(INPUT / "audio-records" / f"{stem}.json"),
            contract_sha256=sig,
        )
        try:
            x = np.load(path, allow_pickle=False)
            tick = time.perf_counter()
            p = encode(x, 16000, seed=0)
            m = matrix(p)
            dest.parent.mkdir(parents=True, exist_ok=True)
            out = dest.parent / "mean.npy"
            np.save(out, m.mean(0), allow_pickle=False)
            row.update(
                status="measured",
                mean=dict(path=str(out), sha256=sha(out)),
                frame_shape=list(m.shape),
                frame_dtype=str(m.dtype),
                frame_canonical_sha256=hashlib.sha256(
                    m.astype("<f8").tobytes()
                ).hexdigest(),
                source_samples=len(x),
                full_duration_seconds=len(x) / 16000,
                analysis_wall_seconds=time.perf_counter() - tick,
            )
        except Exception as e:
            row.update(status="failed", reason=str(e), traceback=traceback.format_exc())
        write(dest, row)
        rows.append(row)
        write(BASE / "progress.json", dict(completed=len(rows), planned=105))
        print(sample, row["status"], flush=True)
    write(BASE / "feature-summary.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    main()
