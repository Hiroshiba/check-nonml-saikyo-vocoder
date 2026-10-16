"""Quantized unedited perceptual/attribute sensitivity and within-point edit tracking."""

from portable_context import REPO
from pathlib import Path
import traceback
import numpy as np
from run_edits import ROOT, read, write, freeze, sha, CONDITIONS
from vocoderbench.assessment.common import Inputs, NotApplicable
from vocoderbench.assessment.controls import pitch, gain, attributes
from vocoderbench.assessment.acoustics import auditory


def main():
    out = ROOT / "extended/quantization-measurements"
    spec = read(ROOT / "input-contract.json")
    inputs = Inputs(ROOT)
    native_source = read(ROOT / "native-contract.json")
    for name, digest in native_source["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        driver_sha256=sha(__file__),
        shared_driver_sha256=sha(Path(__file__).with_name("run_edits.py")),
        quantization_contract_sha256=sha(ROOT / "extended/quantization/contract.json"),
        reference="same native unedited for auditory/attribute; each quantized unedited for edits",
        auditory="existing32ERB triangles40msHann5ms hop no align/gain/resample",
        attributes="existing YIN65..700, RMS, spectral slope300..5000, duration",
        quality_scope="quantized unedited only; separate UTMOS/ECAPA stage",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    rows = []
    for c in spec["cases"]:
        native_path = ROOT / "native" / c["id"] / "record.json"
        native = read(native_path)
        for dtype in ["float16", "float32"]:
            folder = ROOT / "extended/quantization/native" / c["id"] / dtype
            sources = [
                native_path,
                *[folder / n / "record.json" for n in ["unedited", *CONDITIONS]],
            ]
            dest = out / "measurements" / f"{c['id']}__{dtype}.json"
            if any(not p.exists() for p in sources):
                raise RuntimeError("Quantization still pending")
            records = [read(p) for p in sources]
            evidence = {str(p): sha(p) for p in sources}
            for r in records:
                if (
                    r["status"] == "measured"
                    and sha(r["audio"]["path"]) != r["audio"]["sha256"]
                ):
                    raise ValueError("Audio changed")
            if dest.exists():
                row = read(dest)
                if row["contract_sha256"] != sig or row["source_records"] != evidence:
                    raise ValueError("Quantization measurement changed")
                rows.append(row)
                continue
            row = dict(
                case=c["id"],
                speaker=c["speaker"],
                precision=dtype,
                contract_sha256=sig,
                source_records=evidence,
                status="upstream_failed",
                controls=[],
            )
            base = records[1]
            if base["status"] == "measured" and native["status"] == "measured":
                try:
                    x = np.load(native["audio"]["path"], allow_pickle=False)
                    y = np.load(base["audio"]["path"], allow_pickle=False)
                    av, bv = (
                        attributes(x, 16000, 300, 5000),
                        attributes(y, 16000, 300, 5000),
                    )
                    deltas = {
                        k: dict(
                            status="measured"
                            if av[k] is not None and bv[k] is not None
                            else "not_applicable",
                            native_reference=av[k],
                            output=bv[k],
                            signed_delta=bv[k] - av[k]
                            if av[k] is not None and bv[k] is not None
                            else None,
                        )
                        for k in av
                    }
                    heard = auditory(
                        dict(reference=native["audio"], output=base["audio"]), inputs
                    )
                    row.update(
                        status="measured",
                        attributes=bv,
                        attribute_deltas=deltas,
                        auditory=heard,
                        payload=base["payload"],
                    )
                except NotApplicable as e:
                    row.update(status="not_applicable", reason=str(e))
                except Exception as e:
                    row.update(
                        status="failed", reason=str(e), traceback=traceback.format_exc()
                    )
            for (name, kwargs), edit in zip(CONDITIONS.items(), records[2:]):
                cr = dict(
                    condition=name,
                    status="upstream_failed",
                    reference="same precision unedited",
                )
                if base["status"] == "measured" and edit["status"] == "measured":
                    try:
                        job = dict(reference=base["audio"], output=edit["audio"])
                        v = (
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
                        cr.update(
                            status="measured" if v["status"] == "ok" else v["status"],
                            measurement=v,
                        )
                    except NotApplicable as e:
                        cr.update(status="not_applicable", reason=str(e))
                    except Exception as e:
                        cr.update(
                            status="failed",
                            reason=str(e),
                            traceback=traceback.format_exc(),
                        )
                else:
                    cr["upstream_statuses"] = [base["status"], edit["status"]]
                row["controls"].append(cr)
            write(dest, row)
            rows.append(row)
            print(c["id"], dtype, flush=True)
    write(out / "summary.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    main()
