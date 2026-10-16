"""Summarize full-length edited/quantized quality with paired speaker support."""

from collections import defaultdict, Counter
import argparse
import numpy as np
from run_edits import ROOT, read, write, sha

p = argparse.ArgumentParser()
p.add_argument("stage", choices=["quality", "quantization-quality"])
p.add_argument("metric", choices=["speaker_ecapa", "utmosv2"])
a = p.parse_args()
folder = ROOT / "extended" / a.stage / a.metric
data = read(folder / "summary.json")
groups = defaultdict(list)
for r in data["rows"]:
    groups[r["condition"]].append(r)
result = {}
for name, rows in groups.items():
    by = defaultdict(list)
    for r in rows:
        if r["status"] == "measured":
            by[r["speaker"]].append(r["value"])
    vals = np.asarray([np.mean(v) for v in by.values()])
    s = dict(
        status_counts=dict(Counter(r["status"] for r in rows)),
        planned=len(rows),
        valid_recordings=sum(len(v) for v in by.values()),
        valid_speakers=len(by),
    )
    if len(vals):
        draws = np.random.default_rng(20261014).integers(
            0, len(vals), (2000, len(vals))
        )
        boot = vals[draws].mean(1)
        s.update(
            speaker_macro_mean=float(vals.mean()),
            ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
        )
    result[name] = s
write(
    folder / "aggregate.json",
    dict(
        driver_sha256=sha(__file__),
        source_summary_sha256=sha(folder / "summary.json"),
        metric=a.metric,
        stage=a.stage,
        scope="full length original speaker reference for ECAPA; reference-free UTMOS; not common prefix main-quality ranking",
        by_condition=result,
    ),
)
