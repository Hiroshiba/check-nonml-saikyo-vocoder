"""正式GT全文55録音の原音と新PML全長へ旧契約の固定CTCを実行。"""

from pathlib import Path
import argparse
import hashlib
import time
import logging
import traceback
import importlib.metadata
import numpy as np
from run_quality import (
    REPO,
    read,
    write,
    freeze,
    sha,
    verify_native,
    add_run_arguments,
    configure,
)
from vocoderbench.assessment.acoustics import content
from vocoderbench.assessment.common import Inputs


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    add_run_arguments(ap)
    ap.add_argument("--dataset", type=Path, default=REPO / "data/clean_speech_v1.json")
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()
    ROOT = configure(args)
    import torch
    from transformers import AutoModelForCTC, AutoProcessor

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    asset = ROOT / "assets/asr"
    out = ROOT / "results/asr"
    dataset = args.dataset.resolve()
    entries = {c["id"]: c for c in read(dataset)["entries"]}
    spec = read(ROOT / "input-contract.json")
    native = {r["case"]: r for r in verify_native()["rows"]}
    selected = [
        c
        for c in spec["cases"]
        if entries[c["id"]]["source_samples"] == entries[c["id"]]["excerpt_samples"]
        and entries[c["id"]]["excerpt_start_sample"] == 0
    ]
    if len(selected) != 55 or len({c["speaker"] for c in selected}) != 32:
        raise ValueError("Expected fixed full-transcript cohort of 55")
    contract = dict(
        method="pml_fwcep60_lowband_package_v1",
        recognizer="facebook/wav2vec2-base-960h",
        recognizer_revision="22aad52d435eb6dbaf354bdad9b0da84ce7d6156",
        asset_sha256={p.name: sha(p) for p in sorted(asset.iterdir())},
        source_sha256={
            str(p.relative_to(REPO)) if p.is_relative_to(REPO) else p.name: sha(p)
            for p in [
                Path(__file__),
                Path(__file__).with_name("run_quality.py"),
                REPO / "vocoderbench/assessment/acoustics.py",
                REPO / "vocoderbench/assessment/common.py",
            ]
        },
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        dataset_sha256=sha(dataset),
        input_contract_sha256=sha(ROOT / "input-contract.json"),
        selected_case_ids=[c["id"] for c in selected],
        decoding="argmax logits then CTC collapse; no language model; batch_size=1",
        normalization="nfkc_casefold_whitespace",
        word_tokenization="whitespace",
        maximum_reference_cer=0.20,
        sample_rate=16000,
        scope="full native unedited 16k wave, no crop/alignment/gain/silence removal, cast float32 before processor",
        threads=2,
        interop_threads=1,
        packages={
            n: importlib.metadata.version(n)
            for n in (
                "numpy",
                "scipy",
                "torch",
                "transformers",
                "safetensors",
                "tokenizers",
            )
        },
    )
    freeze(out / "contract.json", contract)
    sig = sha(out / "contract.json")
    tick = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        asset, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCTC.from_pretrained(
        asset, local_files_only=True, trust_remote_code=False, use_safetensors=True
    ).eval()
    write(out / "initialization.json", dict(seconds=time.perf_counter() - tick))
    rows = []
    for c in spec["cases"]:
        target = out / "measurements" / f"{c['id']}.json"
        row = dict(
            case=c["id"],
            speaker=c["speaker"],
            method=contract["method"],
            contract_sha256=sig,
            status="not_applicable",
            value=None,
        )
        if target.exists():
            previous = read(target)
            if previous["contract_sha256"] != sig:
                raise ValueError("Resume contract mismatch")
            if c in selected and previous["status"] in ("measured", "partial"):
                inp = Path(c["input"]["path"])
                inp = inp if inp.is_absolute() else ROOT.parent / inp
                if previous["reference_sha256"] != sha(inp) or previous[
                    "output_sha256"
                ] != sha(native[c["id"]]["audio"]["path"]):
                    raise ValueError("ASR result input hash mismatch")
            if not (args.retry_failed and previous["status"] == "failed"):
                rows.append(previous)
                continue
            write(out / "history" / f"{c['id']}-{time.time_ns()}.json", previous)
        if c not in selected:
            row["reason"] = "切出し65録音の公式部分GTは未整備"
        else:
            try:
                n = native[c["id"]]
                if n["status"] != "measured":
                    raise ValueError("Native unavailable")
                inp = Path(c["input"]["path"])
                inp = inp if inp.is_absolute() else ROOT.parent / inp
                paths = dict(original=inp, output=Path(n["audio"]["path"]))
                expected = dict(
                    original=c["input"]["sha256"], output=n["audio"]["sha256"]
                )
                texts = {}
                for name, p in paths.items():
                    if sha(p) != expected[name]:
                        raise ValueError("ASR input hash mismatch")
                    rp = out / "recognitions" / f"{c['id']}__{name}.json"
                    if rp.exists():
                        rec = read(rp)
                        if (
                            rec["input_sha256"] != expected[name]
                            or rec["contract_sha256"] != sig
                        ):
                            raise ValueError("ASR cache mismatch")
                    else:
                        wave = np.load(p, allow_pickle=False).astype(np.float32)
                        tick = time.perf_counter()
                        prepared = processor(
                            wave,
                            sampling_rate=16000,
                            return_tensors="pt",
                            padding=False,
                        )
                        with torch.inference_mode():
                            logits = model(**prepared).logits
                        text = processor.batch_decode(torch.argmax(logits, dim=-1))[0]
                        rec = dict(
                            text=text,
                            contract_sha256=sig,
                            input_sha256=expected[name],
                            input_float32_sha256=hashlib.sha256(
                                wave.astype("<f4").tobytes()
                            ).hexdigest(),
                            preprocessed_float32_sha256=hashlib.sha256(
                                prepared.input_values.numpy().astype("<f4").tobytes()
                            ).hexdigest(),
                            logit_frames=int(logits.shape[1]),
                            wall_seconds=time.perf_counter() - tick,
                        )
                        write(rp, rec)
                    texts[name] = rec["text"]
                sidecar = out / "sidecars" / f"{c['id']}.json"
                data = dict(
                    truth=entries[c["id"]]["transcript"],
                    reference_text=texts["original"],
                    output_text=texts["output"],
                    evidence_kind="asr_output",
                    recognizer=contract["recognizer"],
                    recognizer_revision=contract["recognizer_revision"],
                    language="en",
                    normalization=contract["normalization"],
                    word_tokenization="whitespace",
                    reference_audio_sha256=expected["original"],
                    output_audio_sha256=expected["output"],
                )
                freeze(sidecar, data)
                measured = content(
                    dict(
                        transcripts=str(sidecar),
                        reference=str(paths["original"]),
                        output=str(paths["output"]),
                        maximum_reference_cer=0.20,
                    ),
                    Inputs(ROOT),
                )
                row.update(
                    status="measured"
                    if measured["status"] == "ok"
                    else measured["status"],
                    measurement=measured,
                    value=measured["value"],
                    sidecar_sha256=sha(sidecar),
                    reference_sha256=expected["original"],
                    output_sha256=expected["output"],
                )
            except Exception as e:
                logging.exception("ASR failure %s", c["id"])
                row.update(
                    status="failed", reason=str(e), traceback=traceback.format_exc()
                )
        write(target, row)
        rows.append(row)
        logging.info("ASR %d/120 %s %s", len(rows), c["id"], row["status"])
    write(out / "summary.json", dict(contract_sha256=sig, rows=rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
