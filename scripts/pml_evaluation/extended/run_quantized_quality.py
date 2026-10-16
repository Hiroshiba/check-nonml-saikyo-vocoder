"""Quantized unedited full-length MOS and speaker preservation; no edited quality inference."""

from portable_context import REPO, MODEL_CACHE

from pathlib import Path
import argparse
import time
import traceback
import numpy as np
from run_edits import ROOT, read, write, freeze, sha
from vocoderbench.quality_backends import EcapaSimilarity, UtmosLocal
from vocoderbench.quality_core import environment, NotApplicable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metric", choices=["speaker_ecapa", "utmosv2"])
    a = ap.parse_args()
    metric = a.metric
    if metric == "speaker_ecapa":
        options = dict(embedding_model=str(ROOT / "assets/ecapa/embedding_model.ckpt"))
        cls = EcapaSimilarity
    else:
        cache = MODEL_CACHE
        options = dict(
            checkpoint=str(cache / "weights/fold0_s42_best_model.pth"),
            config=str(cache / "wav2vec2_config/config.json"),
            preprocessor_config=str(cache / "wav2vec2_config/preprocessor_config.json"),
        )
        cls = UtmosLocal
    out = ROOT / "extended/quantization-quality" / metric
    spec = read(ROOT / "input-contract.json")
    native = read(ROOT / "native-contract.json")
    for name, digest in native["source_sha256"].items():
        if sha(REPO / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    contract = dict(
        metric=metric,
        method=native["method"],
        driver_sha256=sha(__file__),
        shared_driver_sha256=sha(Path(__file__).with_name("run_edits.py")),
        edit_contract_sha256=sha(ROOT / "extended/quantization/contract.json"),
        source_contract_sha256=sha(ROOT / "native-contract.json"),
        assets={k: dict(path=v, sha256=sha(v)) for k, v in options.items()},
        options=options,
        threads=2,
        repetitions=1,
        environment=environment(),
        scope="native full-length120 recordings x2quantized unedited; no quantized edit ML quality",
        reference="original full-length speaker identity reference for ECAPA; no reference for UTMOS",
        normalization=False,
        alignment=False,
        seed="native synthesis0; predictor extraction20261012",
        interpretation="Speaker similarity is not pitch target accuracy; original is not a correct edited waveform target.",
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    backend = cls(options, ROOT, out / "work", 2)
    write(out / "initialization.json", dict(provenance=backend.provenance))
    rows = []
    for c in spec["cases"]:
        for name in ["float16", "float32"]:
            dest = out / "measurements" / f"{c['id']}__{name}.json"
            source = (
                ROOT
                / "extended/quantization/native"
                / c["id"]
                / name
                / "unedited/record.json"
            )
            if dest.exists():
                old = read(dest)
                if old["contract_sha256"] != sig:
                    raise ValueError("Quality contract changed")
                if old.get("source_record_sha256") != sha(source):
                    raise ValueError("Edited source record changed")
                if old["status"] == "measured":
                    inp = Path(c["input"]["path"])
                    inp = inp if inp.is_absolute() else ROOT.parent / inp
                    if sha(inp) != c["input"]["sha256"]:
                        raise ValueError("Original changed")
                    nr = read(source)
                    if sha(nr["audio"]["path"]) != old["audio_sha256"]:
                        raise ValueError("Edited audio changed")
                rows.append(old)
                continue
            row = dict(
                case=c["id"],
                speaker=c["speaker"],
                condition=name,
                metric=metric,
                method=native["method"],
                contract_sha256=sig,
                status="pending_audio",
                value=None,
            )
            if not source.exists():
                rows.append(row)
                continue
            n = read(source)
            row["source_record_sha256"] = sha(source)
            if n["status"] != "measured":
                row.update(
                    status="upstream_failed",
                    upstream_status=n["status"],
                    reason=n.get("reason"),
                )
            else:
                try:
                    inp = Path(c["input"]["path"])
                    inp = inp if inp.is_absolute() else ROOT.parent / inp
                    if (
                        sha(inp) != c["input"]["sha256"]
                        or sha(n["audio"]["path"]) != n["audio"]["sha256"]
                    ):
                        raise ValueError("Audio hash mismatch")
                    y = np.load(n["audio"]["path"], allow_pickle=False)
                    x = (
                        np.load(inp, allow_pickle=False)
                        if metric == "speaker_ecapa"
                        else None
                    )
                    tick = time.perf_counter()
                    value, detail = backend.score(x, y, 16000)
                    if not np.isfinite(float(value)):
                        raise ValueError("Predictor returned nonfinite value")
                    row.update(
                        status="measured",
                        value=float(value),
                        detail=detail,
                        wall_seconds=time.perf_counter() - tick,
                        audio_sha256=n["audio"]["sha256"],
                        reference_sha256=c["input"]["sha256"]
                        if x is not None
                        else None,
                        evaluated_samples=len(y),
                    )
                except NotApplicable as e:
                    row.update(status="not_applicable", reason=str(e))
                except Exception as e:
                    row.update(
                        status="failed", reason=str(e), traceback=traceback.format_exc()
                    )
            write(dest, row)
            rows.append(row)
            write(out / "progress.json", dict(completed=len(rows), planned=240))
            print(metric, c["id"], name, row["status"], flush=True)
    write(out / "summary.json", dict(contract_sha256=sig, rows=rows, planned=240))


if __name__ == "__main__":
    main()
