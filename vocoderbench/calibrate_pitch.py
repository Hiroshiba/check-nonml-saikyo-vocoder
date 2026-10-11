"""Rebuild meter calibration and prefilter ablation without candidate decoders."""
from pathlib import Path
import hashlib
import json

import numpy as np

from .fixtures import make_synthetic_cases, make_pitch_stress_cases
from .metrics import estimate_f0_yin, pitch_metrics


def run(output):
    rows, ablations = [], []
    for sr in (16000, 24000, 48000):
        synthetic = make_synthetic_cases(sr)
        stress = make_pitch_stress_cases(sr)
        for c in synthetic + stress:
            result = pitch_metrics(c["x"], sr, c["f0_truth"])
            rows.append({"id": c["id"], "sample_rate": sr, "kind": c["kind"], **result})
        for c in stress:
            for cutoff in (None, 1500.0, 2000.0, 3000.0):
                p = estimate_f0_yin(c["x"], sr, prefilter_hz=cutoff)
                valid = p["f0_hz"] > 0
                errors = np.abs(1200*np.log2(p["f0_hz"][valid]/c["fundamental_hz"]))
                ablations.append({"id": c["id"], "sample_rate": sr,
                                  "fundamental_hz": c["fundamental_hz"],
                                  "offset_cycles": c["offset_cycles"],
                                  "prefilter": p["prefilter"], "total_frames": len(valid),
                                  "missing_frames": int(np.sum(~valid)),
                                  "gross_error_frames": int(np.sum(errors > 600)),
                                  "abs_error_cents_p95": float(np.percentile(errors, 95)) if len(errors) else None,
                                  "abs_error_cents_max": float(np.max(errors)) if len(errors) else None})
    ablation_summary = []
    for cutoff in (None, 1500.0, 2000.0, 3000.0):
        selected = [r for r in ablations if r["prefilter"].get("cutoff_hz") == cutoff]
        ablation_summary.append({"cutoff_hz": cutoff, "case_count": len(selected),
                                 "total_frames": sum(r["total_frames"] for r in selected),
                                 "missing_frames": sum(r["missing_frames"] for r in selected),
                                 "gross_error_frames": sum(r["gross_error_frames"] for r in selected),
                                 "max_case_abs_error_cents_p95": max(r["abs_error_cents_p95"] for r in selected if r["abs_error_cents_p95"] is not None),
                                 "max_single_frame_abs_error_cents": max(r["abs_error_cents_max"] for r in selected if r["abs_error_cents_max"] is not None)})
    root = Path(__file__).resolve().parent
    report = {"schema_version": 2, "estimator_revision": "v2-fixed-lowpass-2000hz",
              "scope": "Independent known synthetic stimuli, not natural speech, MOS or perceptual pitch.",
              "input_seed": 20261011, "known_case_count": len(rows),
              "original_signal_case_count": 30, "broadband_pulse_case_count": 48,
              "max_case_f0_abs_error_cents_p95": max(r["abs_error_cents_p95"] for r in rows if r["abs_error_cents_p95"] is not None),
              "total_missing_voiced_frames": sum(r["missing_voiced_frames"] for r in rows),
              "total_false_voiced_frames": sum(r["false_voiced_frames"] for r in rows),
              "total_gross_pitch_error_frames": sum(r["gross_pitch_error_frames"] for r in rows),
              "source_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                                for name in ("metrics.py", "fixtures.py", "calibrate_pitch.py")},
              "ablation_summary": ablation_summary, "ablation_rows": ablations, "rows": rows}
    Path(output).write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("rows", "ablation_rows")}, indent=2))


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("calibration.json"))
    run(parser.parse_args().output)
