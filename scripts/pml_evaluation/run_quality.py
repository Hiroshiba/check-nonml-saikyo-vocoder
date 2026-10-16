"""凍結した新PML120録音へ既存指標を適用し、指標ごと・録音ごと保存。"""

import argparse
import vocoderbench
from pathlib import Path
import json
import hashlib
import logging
import time
import traceback
import gc
import numpy as np
from vocoderbench.quality_backends import (
    ScoreqReference,
    EcapaSimilarity,
    ErbDistance,
    UtmosLocal,
)
from vocoderbench.quality_core import NotApplicable, environment
from vocoderbench.metrics import compare_waveforms
from vocoderbench.extended_metrics import measure_extended
from vocoderbench.assessment.acoustics import auditory
from vocoderbench.assessment.common import NotApplicable as AcousticNotApplicable

REPO = Path(vocoderbench.__file__).resolve().parents[1]
ROOT = Path("runs/pml-package-evaluation-20261016").resolve()


def add_run_arguments(parser):
    parser.add_argument("--run-root", type=Path, default=ROOT)


def configure(args):
    global ROOT
    ROOT = args.run_root.resolve()
    return ROOT


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(".part")
    t.write_text(json.dumps(v, indent=2, allow_nan=False) + "\n")
    t.replace(p)


def freeze(p, v):
    if p.exists() and read(p) != v:
        raise ValueError("Frozen contract mismatch")
    if not p.exists():
        write(p, v)


def verify_native():
    native = read(ROOT / "native-summary.json")
    contract = read(ROOT / "native-contract.json")
    signature = sha(ROOT / "native-contract.json")
    if native["contract_sha256"] != signature:
        raise ValueError("Native summary contract hash mismatch")
    if contract["input_sha256"] != sha(ROOT / "input-contract.json"):
        raise ValueError("Native input contract mismatch")
    for name, expected in contract["source_sha256"].items():
        if sha(REPO / name) != expected:
            raise ValueError("Frozen native source modified: " + name)
    if contract["driver_sha256"] != sha(Path(__file__).with_name("run_native.py")):
        raise ValueError("Native public driver mismatch")
    if any(row["contract_sha256"] != signature for row in native["rows"]):
        raise ValueError("Native row contract mismatch")
    return native


class Pair:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def pair(self, job):
        return self.x, self.y, 16000


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    add_run_arguments(ap)
    ap.add_argument(
        "--model-cache",
        type=Path,
        help="UTMOS directory with weights/ and wav2vec2_config/",
    )
    ap.add_argument(
        "metric", choices=["scoreq", "speaker_ecapa", "erb", "acoustic", "utmosv2"]
    )
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()
    ROOT = configure(args)
    spec = read(ROOT / "input-contract.json")
    native = verify_native()
    method = "pml_fwcep60_lowband_package_v1"
    metric = args.metric
    common = metric != "utmosv2"
    options = {}
    cls = None
    if metric == "scoreq":
        options = dict(
            model=str(ROOT / "assets/scoreq/fixed_nmr_telephone.onnx"), domain="natural"
        )
        cls = ScoreqReference
    if metric == "speaker_ecapa":
        options = dict(embedding_model=str(ROOT / "assets/ecapa/embedding_model.ckpt"))
        cls = EcapaSimilarity
    if metric == "erb":
        cls = ErbDistance
    if metric == "utmosv2":
        if args.model_cache is None:
            ap.error("utmosv2 requires --model-cache")
        cache = args.model_cache.resolve()
        options = dict(
            checkpoint=str(cache / "weights/fold0_s42_best_model.pth"),
            config=str(cache / "wav2vec2_config/config.json"),
            preprocessor_config=str(cache / "wav2vec2_config/preprocessor_config.json"),
        )
        cls = UtmosLocal
    output = ROOT / "results" / metric
    contract = dict(
        metric=metric,
        method=method,
        input_contract_sha256=sha(ROOT / "input-contract.json"),
        native_contract_sha256=native["contract_sha256"],
        source_sha256={
            str(p.relative_to(REPO)) if p.is_relative_to(REPO) else p.name: sha(p)
            for p in [
                Path(__file__),
                *sorted((REPO / "vocoderbench").rglob("*.py")),
            ]
        },
        assets={
            k: dict(path=v, sha256=sha(v)) for k, v in options.items() if k != "domain"
        },
        options=options,
        threads=2,
        repetitions=1,
        environment=environment(),
        scope="published all-eight fixed 16k common leading window"
        if common
        else "native full-length unedited",
        normalization=False,
        alignment=False,
        seed="native synthesis 0; predictor extraction 20261012",
        scientific_comparison="Historical same-evaluator results may be compared only on same cohort and window. Package dependency/provenance differences remain disclosed.",
    )
    freeze(output / "contract.json", contract)
    sig = sha(output / "contract.json")
    start = time.perf_counter()
    backend = cls(options, ROOT, output / "work", 2) if cls else None
    if backend:
        write(
            output / "initialization.json",
            dict(seconds=time.perf_counter() - start, provenance=backend.provenance),
        )
    natives = {r["case"]: r for r in native["rows"]}
    rows = []
    for i, c in enumerate(spec["cases"]):
        path = output / "measurements" / f"{c['id']}.json"
        n = natives[c["id"]]
        if path.exists():
            old = read(path)
            if old["contract_sha256"] != sig:
                raise ValueError("Resume contract mismatch")
            if old["status"] == "measured":
                inp = Path(c["input"]["path"])
                inp = inp if inp.is_absolute() else ROOT.parent / inp
                if old["audio_sha256"] != sha(n["audio"]["path"]) or old[
                    "reference_sha256"
                ] != sha(inp):
                    raise ValueError("Resume input/output mismatch")
            if not (args.retry_failed and old["status"] in ("failed", "pending")):
                rows.append(old)
                continue
            write(output / "history" / f"{c['id']}-{time.time_ns()}.json", old)
        row = dict(
            case=c["id"],
            speaker=c["speaker"],
            method=method,
            metric=metric,
            status="pending",
            value=None,
            contract_sha256=sig,
        )
        try:
            if n["status"] != "measured":
                raise ValueError("Native synthesis unavailable: " + n["status"])
            inp = Path(c["input"]["path"])
            inp = inp if inp.is_absolute() else ROOT.parent / inp
            if (
                sha(inp) != c["input"]["sha256"]
                or sha(n["audio"]["path"]) != n["audio"]["sha256"]
            ):
                raise ValueError("Input hash mismatch")
            x = np.load(inp, allow_pickle=False).astype(np.float64)
            y = np.load(n["audio"]["path"], allow_pickle=False).astype(np.float64)
            count = c["common_samples"] if common else len(y)
            if common and (count is None or count > min(len(x), len(y))):
                raise NotApplicable("Fixed common window unavailable")
            if common:
                x, y = x[:count], y[:count]
            row.update(
                audio_sha256=n["audio"]["sha256"],
                reference_sha256=c["input"]["sha256"],
                evaluated_samples=count,
                reference_pcm_sha256=hashlib.sha256(
                    x.astype("<f8").tobytes()
                ).hexdigest(),
                output_pcm_sha256=hashlib.sha256(y.astype("<f8").tobytes()).hexdigest(),
            )
            tick = time.perf_counter()
            if metric == "acoustic":
                row.update(
                    measurement=compare_waveforms(x, y, 16000),
                    extended=measure_extended(
                        x,
                        y,
                        16000,
                        include_pitch=True,
                        include_temporal=True,
                        is_speech=True,
                    ),
                )
                try:
                    row["auditory_local"] = auditory({}, Pair(x, y))
                except AcousticNotApplicable as error:
                    row["auditory_local"] = dict(
                        status="not_applicable", value=None, reason=str(error)
                    )
            else:
                value, detail = backend.score(
                    None if metric == "utmosv2" else x, y, 16000
                )
                if not np.isfinite(float(value)):
                    raise ValueError("評価器が非有限値を返しました")
                row.update(value=float(value), detail=detail)
            row.update(status="measured", wall_seconds=time.perf_counter() - tick)
        except NotApplicable as e:
            row.update(status="not_applicable", reason=str(e))
        except Exception as e:
            logging.exception("Quality failure %s %s", metric, c["id"])
            row.update(status="failed", reason=str(e), traceback=traceback.format_exc())
        write(path, row)
        rows.append(row)
        write(
            output / "progress.json",
            dict(
                completed=len(rows),
                planned=120,
                measured=sum(r["status"] == "measured" for r in rows),
            ),
        )
        logging.info("%s %d/120 %s %s", metric, i + 1, c["id"], row["status"])
    write(output / "summary.json", dict(contract_sha256=sig, rows=rows))
    del backend
    gc.collect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()
