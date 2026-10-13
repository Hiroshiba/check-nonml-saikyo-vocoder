"""公式全文正解がある固定55録音を同一ローカルASRで正式測定する。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import configure_logging, run_cli  # noqa: E402

RUN = ROOT / "runs/added-metrics-20261014"
MODEL = "facebook/wav2vec2-base-960h"
REVISION = "22aad52d435eb6dbaf354bdad9b0da84ce7d6156"
ASSETS = ROOT / ".cache/asr" / REVISION
METHODS = ("original", "hnm", "world_harvest")
ASSET_FILES = ("config.json", "preprocessor_config.json", "tokenizer_config.json",
               "special_tokens_map.json", "vocab.json", "README.md", "model.safetensors")
SCOPE = ("固定120録音中、切出しなしで公式全文正解が使える英語55録音32話者の補助測定。"
         "合計225.935秒、原音/HNM v3/WORLD Harvestの165波形。残65録音は切出し正解未整備。"
         "同一固定wav2vec2 greedy CTC、16kHz全長・1波形ずつ・CPU2スレッド。"
         "原音CER上限0.20、超過は原値を残しpartial。句読点除去なし。"
         "これはASRを介した限定的な内容保持測定であり、人間の自然さ・理解度ではない。")


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text())


def wave_path(case, method):
    directory = RUN / "audio" / case
    return directory / "original.npy" if method == "original" else directory / method / "unedited.npy"


def record_path(output, case, method):
    return output / "recognitions" / f"{case}__{method}.json"


def configuration(entries):
    return {
        "schema_version": 1, "recognizer": MODEL, "recognizer_revision": REVISION,
        "model_card_url": f"https://huggingface.co/{MODEL}/blob/{REVISION}/README.md",
        "asset_sha256": {name: digest(ASSETS / name) for name in ASSET_FILES},
        "asset_bytes": {name: (ASSETS / name).stat().st_size for name in ASSET_FILES},
        "asset_urls": {name: f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}" for name in ASSET_FILES},
        "model_metadata_sha256": digest(RUN / "preparation/asr-metadata.json"),
        "source_sha256": {"scripts/added_metrics_asr.py": digest(__file__)},
        "source_manifest_sha256": digest(ROOT / "data/clean_speech_v1.json"),
        "assessment_source_sha256": {p.name: digest(p) for p in sorted((ROOT / "vocoderbench/assessment").glob("*.py"))},
        "scope": SCOPE, "planned_cases": 55, "planned_speakers": 32,
        "planned_waveforms": 165, "planned_assessment_jobs": 110, "excluded_cases": 65,
        "excluded_reason": "切出し波形に対応する公式部分転記が未整備",
        "planned_duration_seconds": sum(e["excerpt_samples"] / e["sample_rate"] for e in entries),
        "selection": "source_samples == excerpt_samples and excerpt_start_sample == 0",
        "selected_case_ids": [e["id"] for e in entries], "methods": METHODS,
        "decoding": "argmax logits then CTC collapse; no language model; batch_size=1",
        "sample_rate": 16000, "normalization": "nfkc_casefold_whitespace",
        "word_tokenization": "whitespace", "maximum_reference_cer": .20,
        "preprocessing": {"waveform": "full original array cast float32",
                          "resampling": "none", "trimming": "none", "clipping": "none",
                          "feature_extractor": read(ASSETS / "preprocessor_config.json")},
        "execution": {"device": "cpu", "dtype": "float32", "torch_threads": 2,
                      "torch_interop_threads": 1, "inference_mode": True, "model_eval": True,
                      "trust_remote_code": False, "local_files_only": True, "use_safetensors": True},
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "logical_cpu_count": os.cpu_count(), "packages": {
                            p: importlib.metadata.version(p) for p in
                            ("numpy", "torch", "transformers", "safetensors", "tokenizers")}},
    }


def infer(path, entry, method, processor, model, torch, np):
    started, cpu = time.perf_counter(), time.process_time()
    before = digest(path)
    wave = np.load(path, allow_pickle=False)
    if wave.ndim != 1 or len(wave) != entry["excerpt_samples"] or not np.isfinite(wave).all():
        raise ValueError("正式対象の波形形状・長さ・有限値が不一致です")
    if entry["sample_rate"] != 16000:
        raise ValueError("固定ASRは16kHzのみです。自動再標本化しません")
    pcm32 = wave.astype("<f4")
    raw_hash = hashlib.sha256(wave.astype("<f8").tobytes()).hexdigest()
    if method == "original":
        pcm_hash = hashlib.sha256(np.rint(wave * 32768).astype("<i2").tobytes()).hexdigest()
        if pcm_hash != entry["decoded_pcm_sha256"]:
            raise ValueError("原音PCMの固定コーパスhashと不一致です")
    else:
        synthesis = read(path.parent / "synthesis.json")["outputs"]["unedited"]
        if synthesis["audio"]["file_sha256"] != before:
            raise ValueError("合成記録の音声hashと不一致です")
    inputs = processor(pcm32, sampling_rate=16000, return_tensors="pt", padding=False)
    prepared_hash = hashlib.sha256(inputs.input_values.numpy().astype("<f4").tobytes()).hexdigest()
    inference_start, inference_cpu = time.perf_counter(), time.process_time()
    with torch.inference_mode():
        logits = model(**inputs).logits
        tokens = torch.argmax(logits, dim=-1)
    inference_wall = time.perf_counter() - inference_start
    inference_process = time.process_time() - inference_cpu
    text = processor.batch_decode(tokens)[0]
    if digest(path) != before:
        raise ValueError("認識中に音声ファイルが変更されました")
    return {"status": "measured", "case": entry["id"], "method": method, "speaker": entry["speaker"],
            "truth": entry["transcript"], "text": text, "language": entry["language"],
            "audio_path": str(path.relative_to(ROOT)), "audio_sha256": before,
            "samples": len(wave), "sample_rate": 16000, "duration_seconds": len(wave) / 16000,
            "source_float64_sha256": raw_hash, "input_float32_sha256": hashlib.sha256(pcm32.tobytes()).hexdigest(),
            "preprocessed_float32_sha256": prepared_hash, "logit_frames": int(logits.shape[1]),
            "recognizer": MODEL, "recognizer_revision": REVISION, "finished_at_utc": now(),
            "inference_wall_seconds": inference_wall, "inference_process_cpu_seconds": inference_process,
            "total_wall_seconds": time.perf_counter() - started, "total_process_cpu_seconds": time.process_time() - cpu}


def status_snapshot(output, entries):
    rows = []
    for entry in entries:
        for method in METHODS:
            path = record_path(output, entry["id"], method)
            row = read(path) if path.exists() else {"status": "pending_audio", "case": entry["id"], "method": method}
            rows.append({k: row[k] for k in ("case", "method", "status")})
    counts = dict(Counter(row["status"] for row in rows))
    save(output / "progress.json", {"updated_at_utc": now(), "planned_waveforms": 165,
                                    "counts": counts, "rows": rows})
    return counts


def evidence(output, entries):
    jobs = []
    for entry in entries:
        case = entry["id"]
        reference_file = record_path(output, case, "original")
        reference = read(reference_file) if reference_file.exists() else {}
        for method in METHODS[1:]:
            result_file = record_path(output, case, method)
            result = read(result_file) if result_file.exists() else {}
            sidecar = output / "sidecars" / f"{case}__{method}.json"
            if reference.get("status") == result.get("status") == "measured":
                save(sidecar, {"truth": entry["transcript"], "reference_text": reference["text"],
                    "output_text": result["text"], "evidence_kind": "asr_output", "recognizer": MODEL,
                    "recognizer_revision": REVISION, "language": entry["language"],
                    "normalization": "nfkc_casefold_whitespace", "word_tokenization": "whitespace",
                    "reference_audio_sha256": reference["audio_sha256"], "output_audio_sha256": result["audio_sha256"],
                    "truth_source": "data/clean_speech_v1.json: official LibriSpeech full transcript",
                    "recognition_configuration_sha256": digest(output / "configuration.json"),
                    "reference_recognition": str(reference_file.relative_to(output)),
                    "output_recognition": str(result_file.relative_to(output))})
            jobs.append({"id": f"{case}__{method}__incremental_content", "case": case,
                "metric": "incremental_content", "condition": "unedited", "method": method, "seed": 0,
                "speaker": entry["speaker"], "language": entry["language"], "style": entry["style"], "kind": "speech",
                "reference": {"path": str(wave_path(case, "original")), "sample_rate": 16000},
                "output": {"path": str(wave_path(case, method)), "sample_rate": 16000},
                "transcripts": str(sidecar), "maximum_reference_cer": .20})
    save(output / "assessment-manifest.json", {"schema_version": 1, "baseline_method": "hnm", "scope": SCOPE, "jobs": jobs})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RUN / "asr")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log = configure_logging("added-metrics-asr")
    entries = [e for e in read(ROOT / "data/clean_speech_v1.json")["entries"]
               if e["source_samples"] == e["excerpt_samples"] and e["excerpt_start_sample"] == 0]
    if len(entries) != 55 or len({e["speaker"] for e in entries}) != 32:
        raise ValueError("事前固定した55録音32話者と一致しません")
    config = configuration(entries)
    config_path = output / "configuration.json"
    if config_path.exists():
        if read(config_path) != json.loads(json.dumps(config)):
            raise ValueError("再開時のモデル・ソース・入力・環境条件が変わっています")
    else:
        save(config_path, config)
    execution_path = output / "execution.json"
    execution = read(execution_path) if execution_path.exists() else {"sessions": []}
    session = {"started_at_utc": now(), "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "log_path": str(log), "reused": 0}
    execution["sessions"].append(session)
    save(execution_path, execution)
    status_snapshot(output, entries)
    start = time.perf_counter()
    import numpy as np
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    processor = Wav2Vec2Processor.from_pretrained(ASSETS, local_files_only=True, trust_remote_code=False)
    model = Wav2Vec2ForCTC.from_pretrained(ASSETS, local_files_only=True, trust_remote_code=False,
                                        use_safetensors=True).eval().to("cpu")
    session["initialization_wall_seconds"] = time.perf_counter() - start
    session["model_parameter_count"] = sum(p.numel() for p in model.parameters())
    save(execution_path, execution)
    seen = set()
    while True:
        waiting = 0
        synthesis_done = "finished_at_utc" in read(RUN / "synthesis-execution.json")
        for entry in entries:
            for method in METHODS:
                key = (entry["id"], method)
                if key in seen:
                    continue
                path = wave_path(*key)
                destination = record_path(output, *key)
                if destination.exists():
                    previous = read(destination)
                    if previous["status"] == "measured" and digest(path) != previous["audio_sha256"]:
                        raise ValueError("再開対象の保存済み成功音声hashが変わりました")
                    seen.add(key)
                    session["reused"] += 1
                    continue
                if not path.exists() and not synthesis_done:
                    waiting += 1
                    continue
                synthesis_path = path.parent / "synthesis.json"
                if method != "original" and not synthesis_done:
                    synthesis = read(synthesis_path) if synthesis_path.exists() else {}
                    if synthesis.get("outputs", {}).get("unedited", {}).get("status") != "measured":
                        waiting += 1
                        continue
                started = time.perf_counter()
                try:
                    result = infer(path, entry, method, processor, model, torch, np)
                except Exception as error:
                    logging.exception("正式ASR失敗: %s %s", *key)
                    result = {"status": "unavailable" if not path.exists() else "failed", "case": entry["id"],
                              "method": method, "reason": f"{type(error).__name__}: {error}",
                              "traceback": traceback.format_exc(), "failed_at_utc": now(),
                              "total_wall_seconds": time.perf_counter() - started}
                save(destination, result)
                seen.add(key)
                counts = status_snapshot(output, entries)
                logging.info("正式ASR %d/165: %s %s %s; %s", len(seen), *key, result["status"], counts)
        if not waiting:
            break
        session.update(waiting_waveforms=waiting, updated_at_utc=now())
        save(execution_path, execution)
        logging.info("合成波形の生成待ち: %d/165", waiting)
        time.sleep(30)
    session.update(finished_at_utc=now(), counts=status_snapshot(output, entries))
    save(execution_path, execution)
    evidence(output, entries)
    if not (output / "assessment").exists():
        from vocoderbench.assessment.runner import evaluate
        code = evaluate(output / "assessment-manifest.json", output / "assessment", 1)
        session["assessment_exit_code"] = code
        save(execution_path, execution)
    return int(session["counts"].get("measured", 0) != 165)


if __name__ == "__main__":
    raise SystemExit(run_cli(main, "added-metrics-asr"))
