"""Aggregate measured precision sensitivity, capacity and native edit tracking separately."""

from collections import defaultdict, Counter
import numpy as np
from run_edits import ROOT, read, write, sha

out = ROOT / "extended/quantization-measurements"
data = read(out / "summary.json")
results = {}


def summarize(pairs):
    by = defaultdict(list)
    for speaker, value in pairs:
        if value is not None and np.isfinite(value):
            by[speaker].append(value)
    x = np.asarray([np.mean(v) for v in by.values()])
    r = dict(recordings=sum(len(v) for v in by.values()), speakers=len(by))
    if len(x):
        boot = x[
            np.random.default_rng(20261014).integers(0, len(x), (2000, len(x)))
        ].mean(1)
        r.update(
            speaker_macro=float(x.mean()),
            ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
        )
    return r


for dtype in ["float16", "float32"]:
    rows = [r for r in data["rows"] if r["precision"] == dtype]
    s = dict(status_counts=dict(Counter(r["status"] for r in rows)), planned=120)
    s["auditory"] = summarize(
        [(r["speaker"], r.get("auditory", {}).get("value")) for r in rows]
    )
    s["absolute_attribute_changes"] = {
        k: summarize(
            [
                (
                    r["speaker"],
                    abs(r["attribute_deltas"][k]["signed_delta"])
                    if r.get("attribute_deltas", {}).get(k, {}).get("signed_delta")
                    is not None
                    else None,
                )
                for r in rows
            ]
        )
        for k in ["pitch_cents", "level_db", "slope_db_per_octave", "duration_seconds"]
    }
    s["controls"] = {}
    for name in ["pitch_minus3", "pitch_plus3", "gain_minus6", "gain_plus6"]:
        cr = [
            (r["speaker"], next(x for x in r["controls"] if x["condition"] == name))
            for r in rows
        ]
        v = summarize([(sp, c.get("measurement", {}).get("value")) for sp, c in cr])
        v["status_counts"] = dict(Counter(c["status"] for sp, c in cr))
        if name.startswith("pitch"):
            v["frame_denominators"] = {
                k: sum(c.get("measurement", {}).get(k, 0) for sp, c in cr)
                for k in [
                    "expected_voiced_frames",
                    "expected_unvoiced_frames",
                    "missing_voiced_frames",
                    "false_voiced_frames",
                    "out_of_range_frames",
                    "total_frames",
                ]
            }
        s["controls"][name] = v
    payloads = [r["payload"] for r in rows if r.get("payload")]
    s["research_npz_capacity"] = dict(
        successful_payloads=len(payloads),
        actual_total_bytes=sum(p["bytes"] for p in payloads),
        actual_total_bits=sum(p["bits"] for p in payloads),
        source_seconds=sum(p["source_seconds"] for p in payloads),
        standard_pml_total_bytes=sum(p["standard_pml_bytes"] for p in payloads),
    )
    if payloads:
        s["research_npz_capacity"]["actual_kbps"] = (
            s["research_npz_capacity"]["actual_total_bits"]
            / s["research_npz_capacity"]["source_seconds"]
            / 1000
        )
    results[dtype] = s
write(
    out / "aggregate.json",
    dict(
        driver_sha256=sha(__file__),
        source_summary_sha256=sha(out / "summary.json"),
        scope="research mixed precision NPZ only; standard PML serialization unchanged; no inferred perceptual JND",
        precisions=results,
    ),
)
