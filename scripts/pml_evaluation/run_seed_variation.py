"""自作PMLのseed1〜7追加反復。seed0は既存正式音響値を引用、音声は重複保存しない。"""

from pathlib import Path
import argparse
import hashlib
import logging
import time
import traceback
import numpy as np
from run_quality import (
    read,
    write,
    freeze,
    sha,
    verify_native,
    Pair,
    add_run_arguments,
    configure,
)
from vocoderbench.pml import load, decode
from vocoderbench.metrics import compare_waveforms
from vocoderbench.extended_metrics import (
    _level,
    _full_scale,
    _quiet_regions,
    _pitch_consistency,
    _guard,
)
from vocoderbench.temporal_metrics import measure_temporal
from vocoderbench.assessment.acoustics import auditory
from vocoderbench.assessment.common import NotApplicable
from vocoderbench.quality_backends import ErbDistance


def extended_without_estoi(x, y):
    return dict(
        status="measured",
        intelligibility={
            "estoi": dict(
                status="not_requested",
                value=None,
                reason="既定条件によりeSTOIはseed0のみ",
            )
        },
        level={"reference": _level(x), "output": _level(y)},
        full_scale={"reference": _full_scale(x), "output": _full_scale(y)},
        quiet_regions=_guard("quiet", lambda: _quiet_regions(x, y, 16000)),
        pitch_consistency=_guard("pitch", lambda: _pitch_consistency(x, y, 16000)),
        temporal=_guard("temporal", lambda: measure_temporal(x, y, 16000)),
    )


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    add_run_arguments(parser)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    ROOT = configure(args)
    spec = read(ROOT / "input-contract.json")
    native = {r["case"]: r for r in verify_native()["rows"]}
    if len(native) != 120 or any(r["status"] != "measured" for r in native.values()):
        raise ValueError("Seed variation requires completed successful native120")
    out = ROOT / "results/seed-variation"
    contract = dict(
        method="pml_fwcep60_lowband_package_v1",
        native_contract_sha256=sha(ROOT / "native-contract.json"),
        input_contract_sha256=sha(ROOT / "input-contract.json"),
        driver_sha256=sha(Path(__file__)),
        quality_driver_sha256=sha(Path(__file__).with_name("run_quality.py")),
        seeds=list(range(8)),
        new_seeds=list(range(1, 8)),
        seed0_acoustic_sha256=sha(ROOT / "results/acoustic/summary.json"),
        seed0_erb_sha256=sha(ROOT / "results/erb/summary.json"),
        scope="same historical eight-method common prefix; same encoded parameters, only synthesis RNG seed varies",
        mos="seed0 only",
        estoi="seed0 only",
        waveform_storage="new waveforms ephemeral; float64 PCM SHA saved; regenerate from fixed payload/seed",
        statistics="aggregate within recording across seeds first; seed is not an independent recording/speaker",
    )
    freeze(out / "contract.json", contract)
    signature = sha(out / "contract.json")
    erb = ErbDistance({}, ROOT, out / "work", 2)
    for i, c in enumerate(spec["cases"]):
        n = native[c["id"]]
        payload = Path(n["payload"]["path"])
        inp = Path(c["input"]["path"])
        inp = inp if inp.is_absolute() else ROOT.parent / inp
        if sha(payload) != n["payload"]["sha256"] or sha(inp) != c["input"]["sha256"]:
            raise ValueError("Seed source hash mismatch")
        params = load(payload)
        count = c["common_samples"]
        x = np.load(inp, allow_pickle=False)[:count]
        for seed in range(1, 8):
            target = out / "measurements" / c["id"] / f"seed{seed}.json"
            if target.exists():
                old = read(target)
                if old["contract_sha256"] != signature:
                    raise ValueError("Seed resume mismatch")
                if not (args.retry_failed and old["status"] == "failed"):
                    continue
                write(
                    out / "history" / f"{c['id']}-seed{seed}-{time.time_ns()}.json", old
                )
            row = dict(
                case=c["id"],
                speaker=c["speaker"],
                method=contract["method"],
                seed=seed,
                contract_sha256=signature,
                status="pending",
                payload_sha256=n["payload"]["sha256"],
                reference_sha256=c["input"]["sha256"],
            )
            try:
                tick = time.perf_counter()
                y = decode(params, seed=seed)
                row["full_pcm_float64_sha256"] = hashlib.sha256(
                    y.astype("<f8").tobytes()
                ).hexdigest()
                row["full_peak"] = float(np.max(abs(y)))
                row["full_over_one_samples"] = int(np.count_nonzero(abs(y) > 1))
                y = y[:count]
                row.update(
                    measurement=compare_waveforms(x, y, 16000),
                    extended=extended_without_estoi(x, y),
                    erb20_value=erb.score(x, y, 16000)[0],
                )
                try:
                    row["auditory_local"] = auditory({}, Pair(x, y))
                except NotApplicable as e:
                    row["auditory_local"] = dict(
                        status="not_applicable", value=None, reason=str(e)
                    )
                row.update(status="measured", wall_seconds=time.perf_counter() - tick)
            except Exception as e:
                logging.exception("Seed failed %s %s", c["id"], seed)
                row.update(
                    status="failed", reason=str(e), traceback=traceback.format_exc()
                )
            write(target, row)
        write(
            out / "progress.json",
            dict(completed_cases=i + 1, planned_cases=120, new_seeds_per_case=7),
        )
        logging.info("Seeds %d/120 %s", i + 1, c["id"])
    write(
        out / "summary.json",
        dict(
            contract_sha256=signature,
            rows=[read(p) for p in sorted((out / "measurements").glob("*/*.json"))],
            seed0_acoustic=str(ROOT / "results/acoustic/summary.json"),
            seed0_erb=str(ROOT / "results/erb/summary.json"),
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
