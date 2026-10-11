"""Reproduce the critic's independent metric audits without native vocoders.

Usage: python scripts/audit_metrics.py --output reports/initial-comparison
Synthetic inputs are generated here, independently of the comparison fixtures.
Passing these mechanical checks does not certify perceptual quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench import metrics  # noqa: E402


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, assertion):
        try:
            passed = bool(assertion())
            row = {"check": name, "status": "passed" if passed else "failed"}
        except Exception as error:
            row = {"check": name, "status": "failed", "error": f"{type(error).__name__}: {error}"}
        checks.append(row)

    sr = 24000
    t = np.arange(sr) / sr
    amplitude = .55 + .3 * np.sin(2 * np.pi * 3 * t)
    x = amplitude * (.22 * np.sin(2 * np.pi * 180 * t)
                     + .12 * np.sin(2 * np.pi * 720 * t)
                     + .1 * np.sin(2 * np.pi * 1620 * t)
                     + .08 * np.sin(2 * np.pi * 3600 * t))
    x[:500] *= np.linspace(0, 1, 500)
    x[-500:] *= np.linspace(1, 0, 500)
    invalid_nan, invalid_inf = x.copy(), x.copy()
    invalid_nan[len(x) // 2] = np.nan
    invalid_inf[len(x) // 2] = np.inf
    challenges = {
        "copy": x.copy(), "gain": x * .5,
        "shift": np.r_[np.zeros(240), x[:-240]],
        "lowpass": sosfilt(butter(8, 1000, fs=sr, output="sos"), x),
        "crop": x[:-2400], "nan": invalid_nan, "inf": invalid_inf,
        "silence": np.zeros_like(x), "out_of_range": x * 10,
    }
    report = {}
    for name, y in challenges.items():
        try:
            report[name] = metrics.compare_waveforms(x, y, sr)
        except Exception as error:
            report[name] = {"audit_exception": f"{type(error).__name__}: {error}"}
    for name, y, truth in (
        ("known_pitch", x, np.full(len(x), 180.)),
        ("missing_voice", np.zeros_like(x), np.full(len(x), 180.)),
        ("silence_truth", np.zeros_like(x), np.zeros_like(x)),
        ("dc_truth_unvoiced", np.full_like(x, .1), np.zeros_like(x)),
        ("very_short_voiced", x[:100], np.full(100, 180.)),
    ):
        try:
            report[name] = metrics.pitch_metrics(y, sr, truth)
        except Exception as error:
            report[name] = {"audit_exception": f"{type(error).__name__}: {error}"}
    check("all_metric_calls_recorded", lambda: all("audit_exception" not in r for r in report.values()))
    check("copy_is_identical", lambda: report["copy"]["status"] == "ok"
          and report["copy"]["mr_stft_log_magnitude_mae_db"] < 1e-10)
    check("gain_sign_and_units", lambda: abs(report["gain"]["rms_gain_error_db"] - 20 * np.log10(.5)) < 1e-10)
    check("shift_is_not_hidden", lambda: report["shift"]["mr_stft_log_magnitude_mae_db"] > .1)
    check("lowpass_band_loss", lambda: report["lowpass"]["band_energy"]["active_band_mae_db"] > 3)
    check("crop_is_length_failure", lambda: report["crop"]["status"] == "length_mismatch"
          and report["crop"]["length_delta_samples"] == -2400)
    for name in ("nan", "inf"):
        check(f"{name}_is_invalid", lambda name=name: report[name]["status"] == "nonfinite_input_or_output")
    check("missing_voice_is_not_zero_error", lambda: report["missing_voice"]["valid_voiced_frames"] == 0
          and report["missing_voice"]["missing_voiced_frames"] == report["missing_voice"]["expected_voiced_frames"]
          and report["missing_voice"]["abs_error_cents_p95"] is None)
    check("silence_pitch_is_undefined", lambda: report["silence_truth"]["abs_error_cents_p95"] is None)
    check("dc_is_not_periodicity", lambda: report["dc_truth_unvoiced"]["false_voiced_frames"] == 0)
    check("overflow_range_not_normalized", lambda: report["out_of_range"]["output_peak"] > 1
          and abs(report["out_of_range"]["rms_gain_error_db"] - 20) < 1e-10)
    check("short_signal_is_unevaluated", lambda: report["very_short_voiced"]["total_frames"] == 0
          and report["very_short_voiced"]["abs_error_cents_p95"] is None)
    check("known_pitch_calibrated", lambda: report["known_pitch"]["missing_voiced_frames"] == 0
          and report["known_pitch"]["abs_error_cents_p95"] < 5)
    basic_checks = list(checks)

    rows = []
    for f0 in (160., 180., 220.):
        harmonics = np.arange(1, int((sr / 2 - 1) // f0) + 1)
        signal = np.cos(2 * np.pi * f0 * t[:, None] * harmonics).sum(axis=1) / len(harmonics)
        for label, y in (("raw_analytic", signal),
                         ("external_2000hz_lowpass", sosfiltfilt(butter(6, 2000, fs=sr, output="sos"), signal))):
            try:
                row = metrics.pitch_metrics(y, sr, np.full(len(y), f0))
            except Exception as error:
                row = {"audit_exception": f"{type(error).__name__}: {error}"}
            row.update(true_f0_hz=f0, stimulus=label, harmonic_count=len(harmonics))
            rows.append(row)
            check(f"wideband_{f0:g}_{label}", lambda row=row: row["valid_voiced_frames"] == row["expected_voiced_frames"]
                  and row["expected_voiced_frames"] > 0 and row["gross_pitch_error_frames"] == 0
                  and row["abs_error_cents_p95"] < 5)
    provenance = {
        "metric_sha256": hashlib.sha256(Path(metrics.__file__).read_bytes()).hexdigest(),
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reference_float64_sha256": hashlib.sha256(x.astype("<f8").tobytes()).hexdigest(),
        "scope": "independent mechanical metric audit; not perceptual validation",
        "assertion_scope": "thresholds check these known stimuli, not user quality requirements",
    }
    report["audit_provenance"] = provenance
    report["checks"] = basic_checks
    report["audit_status"] = "passed" if all(c["status"] == "passed" for c in basic_checks) else "failed"
    wide_checks = checks[len(basic_checks):]
    wide = {**provenance, "sampling": "24kHz analytic sum of equal-amplitude integer harmonics strictly below Nyquist",
            "rows": rows, "checks": wide_checks,
            "audit_status": "passed" if all(c["status"] == "passed" for c in wide_checks) else "failed"}
    write_json(output / "metric_audit_results.json", report)
    write_json(output / "wideband_pitch_results.json", wide)
    for row in checks:
        print(f"{row['status'].upper()}: {row['check']}", flush=True)
    failed = sum(row["status"] != "passed" for row in checks)
    print(f"Metric audit: {len(checks) - failed} passed, {failed} failed; output: {output}", flush=True)
    return failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    raise SystemExit(1 if run(arguments.output) else 0)
