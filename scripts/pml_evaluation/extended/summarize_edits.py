"""Speaker-macro measured edit results; retain all planned statuses and denominators."""

from collections import Counter, defaultdict
import numpy as np
from run_edits import ROOT, read, write, sha

spec = read(ROOT / "input-contract.json")
rows = []
for c in spec["cases"]:
    for condition in [
        "pitch_minus3",
        "pitch_plus3",
        "gain_minus6",
        "gain_plus6",
        "gain_interference",
    ]:
        p = ROOT / "extended/measurements" / f"{c['id']}__{condition}.json"
        row = (
            read(p)
            if p.exists()
            else dict(
                case=c["id"],
                speaker=c["speaker"],
                condition=condition,
                status="pending",
            )
        )
        rows.append({**row, "cohort": c["cohort"]})
summary = {}
for condition in [
    "pitch_minus3",
    "pitch_plus3",
    "gain_minus6",
    "gain_plus6",
    "gain_interference",
]:
    selected = [r for r in rows if r["condition"] == condition]
    g = defaultdict(list)
    for r in selected:
        v = r.get("measurement", {}).get("value")
        if v is not None and np.isfinite(v):
            g[r["speaker"]].append(v)
    values = np.array([np.mean(v) for v in g.values()])
    s = dict(
        status_counts=dict(Counter(r["status"] for r in selected)),
        planned=len(selected),
        valid_recordings=sum(len(v) for v in g.values()),
        valid_speakers=len(g),
    )
    if len(values):
        boot = values[
            np.random.default_rng(20261014).integers(
                0, len(values), (2000, len(values))
            )
        ].mean(1)
        s.update(
            speaker_macro=float(values.mean()),
            ci95=np.quantile(boot, [0.025, 0.975]).tolist(),
        )
    if condition.startswith("pitch"):
        keys = [
            "expected_voiced_frames",
            "expected_unvoiced_frames",
            "missing_voiced_frames",
            "false_voiced_frames",
            "out_of_range_frames",
            "unmapped_frames",
            "total_frames",
        ]
        s["frame_denominators"] = {
            k: sum(r.get("measurement", {}).get(k, 0) for r in selected) for k in keys
        }
        s["common_voiced_frames"] = sum(
            r.get("measurement", {}).get("relative_error", {}).get("count", 0)
            for r in selected
        )
    if condition == "gain_interference":
        s.pop("valid_recordings")
        s.pop("valid_speakers")
        s["attributes"] = {}
        for attr in [
            "pitch_cents",
            "level_db",
            "slope_db_per_octave",
            "duration_seconds",
        ]:
            groups = defaultdict(list)
            for r in selected:
                for cell in r.get("measurement", {}).get("matrix", []):
                    if (
                        cell["attribute"] == attr
                        and cell["normalized_error"] is not None
                    ):
                        groups[r["speaker"]].append(abs(cell["normalized_error"]))
            vals = np.asarray([np.mean(v) for v in groups.values()])
            s["attributes"][attr] = dict(
                valid_recordings=sum(len(v) for v in groups.values()),
                valid_speakers=len(groups),
                speaker_macro_absolute_normalized_error=float(vals.mean())
                if len(vals)
                else None,
            )
    summary[condition] = s
write(
    ROOT / "extended/edit-summary.json",
    dict(
        driver_sha256=sha(__file__),
        contract_sha256=sha(ROOT / "extended/contract.json"),
        scope="all fixed120; individual support retained; not historical common-method ranking",
        summary=summary,
        rows=rows,
    ),
)
