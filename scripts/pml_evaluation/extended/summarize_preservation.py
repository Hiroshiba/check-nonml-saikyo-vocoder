"""Full-length preservation: measured events only, keep missing event denominators."""

from collections import defaultdict, Counter
import numpy as np
from run_edits import ROOT, read, write, sha

folder = ROOT / "extended/preservation"
data = read(folder / "summary.json")
result = {}
for metric in ["time_preservation", "slope_preservation"]:
    rows = [r for r in data["rows"] if r["metric"] == metric]
    by = defaultdict(list)
    for r in rows:
        m = r.get("measurement", {})
        v = m.get("value")
        if r["status"] in ("measured", "partial") and v is not None:
            by[r["speaker"]].append(v)
    values = np.array([np.mean(v) for v in by.values()])
    s = dict(
        status_counts=dict(Counter(r["status"] for r in rows)),
        planned=len(rows),
        valid_recordings=sum(len(v) for v in by.values()),
        valid_speakers=len(by),
        unit="ms" if metric == "time_preservation" else "dB/oct",
        scope="recording MAE over detected events, then speaker equal; partial rows contribute their detected events only, missing never zero"
        if metric == "time_preservation"
        else "full waveform absolute spectral slope change300..5000, then speaker equal",
    )
    if len(values):
        draws = np.random.default_rng(20261014).integers(
            0, len(values), (2000, len(values))
        )
        boot = values[draws].mean(1)
        path = folder / f"{metric}-bootstrap.npz"
        np.savez_compressed(path, draws=draws, values=boot)
        s.update(
            speaker_macro_mae=float(values.mean()),
            ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
            bootstrap_sha256=sha(path),
        )
    if metric == "time_preservation":
        s["event_denominators"] = {
            key: sum(r.get("measurement", {}).get(key, 0) for r in rows)
            for key in ["event_count", "detected_events", "missing_events"]
        }
        s["duration_absolute_error_max_seconds"] = max(
            r.get("measurement", {}).get("absolute_duration_error_seconds", 0)
            for r in rows
        )
    result[metric] = s
write(
    folder / "aggregate.json",
    dict(
        driver_sha256=sha(__file__),
        source_summary_sha256=sha(folder / "summary.json"),
        metrics=result,
    ),
)
