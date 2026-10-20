"""Research-only mixed precision NPZ write/read sensitivity. Standard .pml unchanged."""

from portable_context import REPO
from pathlib import Path
import time
import traceback
import numpy as np
from run_edits import ROOT, read, write, freeze, sha, CONDITIONS, audio
from vocoderbench.pml import load, decode, edit_parameters
from vocoderbench.pml.parameters import PMLParameters


class IntegrityError(RuntimeError):
    pass


def main():
    raise RuntimeError('旧PML版専用の新規生成は廃止しました。現在のRAW_FULLを旧方式名で生成しません。保存済み結果の読取り・集計とsource-freeze契約は維持します。')
    out = ROOT / "extended/quantization"
    spec = read(ROOT / "input-contract.json")
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        driver_sha256=sha(__file__),
        shared_driver_sha256=sha(Path(__file__).with_name("run_edits.py")),
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        input_contract_sha256=sha(ROOT / "input-contract.json"),
        dtype=["float16", "float32"],
        quantized_fields=["fwcep", "f0"],
        preserved_fields=[
            "noise_mask_bits",
            "seed",
            "n_samples",
            "sample_rate",
            "pitch_shift_semitones",
        ],
        archive="actual numpy savez NPZ, uncompressed, read back before synthesis, NM packbits bitorder big",
        import_types=dict(fwcep="float32", f0="float64", noise_mask="bool"),
        conditions={"unedited": {}, **CONDITIONS},
        interpretation="research mixed precision NPZ sensitivity; not standard .pml format or public API change",
        invalid="nonfinite or parameter-domain violation recorded failed; no clipping/normalization",
        seed=0,
        capacity="actual NPZ bytes/bits including headers separate from standard .pml bitrate",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    rows = []
    for c in spec["cases"]:
        src = ROOT / "native" / c["id"] / "record.json"
        r = read(src)
        if (
            r["status"] == "measured"
            and sha(r["payload"]["path"]) != r["payload"]["sha256"]
        ):
            raise ValueError("Native payload changed")
        for dtype in ["float16", "float32"]:
            folder = out / "native" / c["id"] / dtype
            payload = folder / "research-parameters.npz"
            meta = folder / "payload.json"
            restored = None
            failure = None
            info = None
            try:
                if r["status"] != "measured":
                    raise ValueError("Native source failed")
                p = load(r["payload"]["path"])
                folder.mkdir(parents=True, exist_ok=True)
                if meta.exists():
                    info = read(meta)
                    if (
                        info["contract_sha256"] != sig
                        or info["native_record_sha256"] != sha(src)
                        or sha(payload) != info["sha256"]
                    ):
                        raise IntegrityError(
                            "Stored quantization contract/input changed"
                        )
                else:
                    arrays = dict(
                        fwcep=p.fwcep.astype(dtype),
                        f0=p.f0.astype(dtype),
                        nm_packed=np.packbits(p.noise_mask, axis=1, bitorder="big"),
                        n_samples=np.array(p.n_samples, dtype="<i8"),
                        sample_rate=np.array(p.sample_rate, dtype="<i8"),
                        seed=np.array(p.seed, dtype="<u4"),
                        pitch_shift_semitones=np.array(
                            p.pitch_shift_semitones, dtype="<f8"
                        ),
                    )
                    np.savez(payload, **arrays)
                    size = payload.stat().st_size
                    duration = p.n_samples / p.sample_rate
                    info = dict(
                        path=str(payload),
                        sha256=sha(payload),
                        bytes=size,
                        bits=8 * size,
                        bits_per_source_second=8 * size / duration,
                        source_seconds=duration,
                        nominal_storage_dtype=dtype,
                        field_dtypes={k: str(v.dtype) for k, v in arrays.items()},
                        contract_sha256=sig,
                        native_record_sha256=sha(src),
                        standard_pml_bytes=Path(r["payload"]["path"]).stat().st_size,
                    )
                    write(meta, info)
                with np.load(payload, allow_pickle=False) as q:
                    mask = np.unpackbits(
                        q["nm_packed"], axis=1, count=2049, bitorder="big"
                    ).astype(bool)
                    restored = PMLParameters(
                        fwcep=q["fwcep"],
                        f0=q["f0"],
                        noise_mask=mask,
                        n_samples=int(q["n_samples"]),
                        sample_rate=int(q["sample_rate"]),
                        seed=int(q["seed"]),
                        pitch_shift_semitones=float(q["pitch_shift_semitones"]),
                    )
            except IntegrityError:
                raise
            except Exception as e:
                failure = dict(reason=str(e), traceback=traceback.format_exc())
            for name, kwargs in {"unedited": {}, **CONDITIONS}.items():
                dest = folder / name / "record.json"
                if dest.exists():
                    row = read(dest)
                    if row["contract_sha256"] != sig or row[
                        "native_record_sha256"
                    ] != sha(src):
                        raise ValueError("Quantization decode resume mismatch")
                    if (
                        row["status"] == "measured"
                        and sha(row["audio"]["path"]) != row["audio"]["sha256"]
                    ):
                        raise ValueError("Quantized audio changed")
                    rows.append(row)
                    continue
                row = dict(
                    case=c["id"],
                    speaker=c["speaker"],
                    method=native["method"],
                    condition=name,
                    precision=dtype,
                    contract_sha256=sig,
                    native_record_sha256=sha(src),
                    payload=info,
                    status="failed",
                )
                if failure:
                    row.update(**failure, failure_stage="quantize_save_restore")
                else:
                    try:
                        edited = (
                            edit_parameters(restored, **kwargs) if kwargs else restored
                        )
                        start = time.perf_counter()
                        y = decode(edited)
                        wall = time.perf_counter() - start
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        path = dest.parent / "wave.npy"
                        np.save(path, y, allow_pickle=False)
                        row.update(
                            status="measured",
                            audio=audio(path),
                            decode_wall_seconds=wall,
                            edit=kwargs,
                        )
                    except Exception as e:
                        row.update(
                            reason=str(e),
                            traceback=traceback.format_exc(),
                            failure_stage="edit_decode",
                        )
                write(dest, row)
                rows.append(row)
            write(out / "progress.json", dict(completed=len(rows), planned=1200))
            print(c["id"], dtype, flush=True)
    write(out / "inventory.json", dict(contract_sha256=sig, rows=rows, planned=1200))


if __name__ == "__main__":
    main()
