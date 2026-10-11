"""JSON-safe engineering diagnostics independent of candidate analyzers.

No metric here predicts MOS or establishes perceptual transparency.
The reference is never time-warped, gain-normalized or automatically aligned.
"""
from __future__ import annotations

import numpy as np
from scipy import fft, signal

POWER_FLOOR = 1e-12  # -120 dBFS power, not a measured noise floor.


def _rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else None


def _dbfs_rms(x):
    rms = _rms(x)
    return float(20*np.log10(max(rms, np.sqrt(POWER_FLOOR)))) if rms is not None else None


def estimate_f0_yin(x, sr, frame_ms=80.0, hop_ms=10.0, fmin=65.0, fmax=700.0,
                    threshold=0.15, rms_threshold=1e-5, prefilter_hz=2000.0):
    """Independent YIN-style difference estimator, not a ground-truth oracle.

    Only complete frames are analyzed. A rejected periodicity estimate is zero.
    A fixed 2 kHz sixth-order Butterworth forward/backward filter addresses
    noninteger-period broadband pulses, whose integer-lag differences can miss
    a genuine period. It affects ONLY this F0 diagnostic, never acoustic scores.
    Even endpoint reflection (up to 80 ms) avoids the spurious leading impulse
    produced by odd reflection of an endpoint pulse. Endpoint frames remain in
    the scores; filtering is not permission to omit failures. ``None`` disables
    the filter for calibration comparisons, not per-candidate score selection.
    min_cmnd is retained so callers can inspect the voicing decision. This
    estimator is unvalidated when the periodicity exists only above 2 kHz.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or not np.all(np.isfinite(x)) or sr <= 0:
        raise ValueError("expected finite mono samples and positive sample rate")
    n = max(8, round(frame_ms*sr/1000))
    hop = max(1, round(hop_ms*sr/1000))
    lo = max(2, int(np.floor(sr/fmax)))
    hi = min(n//2, int(np.ceil(sr/fmin)))
    if hi <= lo:
        raise ValueError("frame/rate incompatible with F0 range")
    if prefilter_hz is not None:
        if not 0 < prefilter_hz < sr/2:
            raise ValueError("prefilter cutoff must be below Nyquist")
        if len(x) > 1:
            sos = signal.butter(6, prefilter_hz, fs=sr, output="sos")
            x = signal.sosfiltfilt(sos, x, padtype="even", padlen=min(n, len(x)-1))
    starts = np.arange(0, max(0, len(x)-n+1), hop, dtype=int)
    values, confidence = [], []
    for start in starts:
        frame = x[start:start+n]
        if _rms(frame) < rms_threshold:
            values.append(0.0); confidence.append(1.0); continue
        frame = frame-frame.mean()
        # A DC offset has energy but no periodic AC component. Without this
        # check an all-zero difference curve can be mistaken for high F0.
        if _rms(frame) < rms_threshold:
            values.append(0.0); confidence.append(1.0); continue
        power = np.r_[0.0, np.cumsum(frame*frame)]
        spectrum = fft.rfft(frame, fft.next_fast_len(2*n-1))
        ac = fft.irfft(spectrum*np.conj(spectrum), fft.next_fast_len(2*n-1))[:hi+1]
        lags = np.arange(hi+1)
        diff = np.maximum(0.0, power[n-lags] + power[n]-power[lags] - 2*ac)
        cmnd = np.ones(hi+1)
        denom = np.cumsum(diff[1:])
        cmnd[1:] = diff[1:] * np.arange(1, hi+1) / np.maximum(denom, 1e-30)
        confidence.append(float(np.min(cmnd[lo:hi+1])))
        tau = lo
        while tau <= hi and cmnd[tau] >= threshold:
            tau += 1
        if tau > hi:
            values.append(0.0); continue
        while tau < hi and cmnd[tau+1] < cmnd[tau]:
            tau += 1
        refined = float(tau)
        if 1 <= tau < hi:
            a, b, c = cmnd[tau-1:tau+2]
            denom = a-2*b+c
            if abs(denom) > 1e-15:
                refined += float(np.clip(0.5*(a-c)/denom, -0.5, 0.5))
        values.append(float(sr/refined))
    return {"f0_hz": np.asarray(values), "min_cmnd": np.asarray(confidence),
            "start_samples": starts, "center_samples": starts+n//2,
            "frame_samples": n, "hop_samples": hop,
            "prefilter": {"kind": "butterworth-forward-backward", "order_per_pass": 6,
                          "cutoff_hz": prefilter_hz, "pad_type": "even", "max_pad_samples": n}
                          if prefilter_hz is not None else {"kind": "none"},
            "method": "independent-yin-difference-v2-prefiltered" if prefilter_hz is not None else "independent-yin-difference-v1-unfiltered"}


def pitch_metrics(output, sr, f0_truth):
    """Compare output F0 to independently known sample-wise truth only.

    Mixed voiced/unvoiced truth windows are counted explicitly as boundaries.
    Their cent scores are undefined; they are not silently called successes.
    """
    output = np.asarray(output, dtype=float)
    truth = np.asarray(f0_truth, dtype=float)
    if truth.shape != output.shape or truth.ndim != 1:
        raise ValueError("f0_truth must have one value per output sample")
    if np.any(~np.isfinite(truth)) or np.any(truth < 0):
        raise ValueError("truth must be finite nonnegative Hz")
    estimates = estimate_f0_yin(output, sr)
    n = estimates["frame_samples"]
    errors, octave_errors = [], 0
    voiced_count = unvoiced_count = boundary_count = missing = false_voiced = 0
    for start, f0 in zip(estimates["start_samples"], estimates["f0_hz"]):
        gt = truth[start:start+n]
        voiced_fraction = float(np.mean(gt > 0))
        if 0 < voiced_fraction < 1:
            boundary_count += 1
            continue
        if voiced_fraction == 0:
            unvoiced_count += 1
            false_voiced += int(f0 > 0)
            continue
        voiced_count += 1
        if f0 <= 0:
            missing += 1
            continue
        target = float(np.median(gt))
        cents = float(1200*np.log2(f0/target))
        errors.append(abs(cents))
        octave_errors += int(abs(cents) > 600)
    return {"estimator": estimates["method"], "frame_ms": 80.0, "hop_ms": 10.0,
            "prefilter": estimates["prefilter"],
            "validated_scope": "independent synthetic calibration; requires sufficient periodic energy below 2 kHz; not validated for natural speech",
            "fmin_hz": 65.0, "fmax_hz": 700.0,
            "total_frames": len(estimates["f0_hz"]), "expected_voiced_frames": voiced_count,
            "expected_unvoiced_frames": unvoiced_count, "boundary_frames": boundary_count,
            "boundary_policy": "mixed-truth windows counted but excluded from cent and UV summaries",
            "valid_voiced_frames": len(errors), "missing_voiced_frames": missing,
            "false_voiced_frames": false_voiced, "gross_pitch_error_frames": octave_errors,
            "abs_error_cents_median": float(np.median(errors)) if errors else None,
            "abs_error_cents_p95": float(np.percentile(errors, 95)) if errors else None,
            "voiced_detection_rate": (voiced_count-missing)/voiced_count if voiced_count else None,
            "unvoiced_false_positive_rate": false_voiced/unvoiced_count if unvoiced_count else None,
            "score_status": "ok" if errors else "no_valid_voiced_frames",
            "uncovered_tail_samples": int(len(output)-(estimates["start_samples"][-1]+n)) if len(estimates["start_samples"]) else len(output)}


def _stft_metrics(x, y, sr):
    rows = []
    for ms in (5, 20, 80):
        n = max(4, round(ms*sr/1000))
        hop = max(1, n//4)
        # Explicit padding preserves the advertised window even for short input.
        if len(x) < n:
            a, b = np.pad(x, (0, n-len(x))), np.pad(y, (0, n-len(y)))
        else:
            a, b = x, y
        kwargs = dict(fs=sr, window="hann", nperseg=n, noverlap=n-hop,
                      nfft=n, boundary="zeros", padded=True)
        sx, sy = np.abs(signal.stft(a, **kwargs)[2]), np.abs(signal.stft(b, **kwargs)[2])
        floor = max(float(sx.max())*1e-5, 1e-10)
        denom = float(np.linalg.norm(sx))
        db_error = float(np.mean(np.abs(20*np.log10(np.maximum(sx, floor))-20*np.log10(np.maximum(sy, floor)))))
        rows.append({"window_ms": ms, "window_samples": n, "hop_samples": hop,
                     "log_magnitude_mae_db": db_error,
                     "spectral_convergence": float(np.linalg.norm(sy-sx)/denom) if denom else None,
                     "spectral_convergence_status": "ok" if denom else "zero_reference_energy",
                     "amplitude_floor": floor})
    return rows


def _band_metrics(x, y, sr):
    n = len(x)
    frequencies = fft.rfftfreq(n, 1/sr)
    weights = np.full(len(frequencies), 2.0)
    weights[0] = 1.0
    if n % 2 == 0:
        weights[-1] = 1.0
    px = abs(fft.rfft(x))**2 * weights / n**2
    py = abs(fft.rfft(y))**2 * weights / n**2
    edges = sorted(set([0.0]+[float(v) for v in (200, 500, 1000, 2000, 4000, 8000, 16000) if v < sr/2]+[sr/2]))
    ref_total = float(px.sum())
    rows, active_errors = [], []
    for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (frequencies >= lo) & ((frequencies <= hi) if i == len(edges)-2 else (frequencies < hi))
        a, b = float(px[mask].sum()), float(py[mask].sum())
        error = float(10*np.log10(max(b, POWER_FLOOR)/max(a, POWER_FLOOR)))
        active = a > max(POWER_FLOOR, ref_total*1e-6)
        rows.append({"low_hz": lo, "high_hz": hi, "reference_power": a, "output_power": b,
                     "delta_db": error, "reference_active": active})
        if active:
            active_errors.append(abs(error))
    return {"bands": rows, "power_floor": POWER_FLOOR,
            "active_band_count": len(active_errors), "band_count": len(rows),
            "active_band_mae_db": float(np.mean(active_errors)) if active_errors else None,
            "active_policy": "reference power > max(1e-12, total reference power * 1e-6)",
            "status": "ok" if active_errors else "no_active_reference_bands"}


def compare_waveforms(reference, output, sr, f0_truth=None):
    """Measure identity resynthesis without concealing length/finite failures."""
    x, y = np.asarray(reference, dtype=float), np.asarray(output, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or not isinstance(sr, (int, np.integer)) or sr <= 0:
        raise ValueError("expected mono samples and a positive integer sample rate")
    finite_x, finite_y = bool(np.isfinite(x).all()), bool(np.isfinite(y).all())
    result = {"status": "ok", "reference_samples": len(x), "output_samples": len(y),
              "length_delta_samples": len(y)-len(x), "sample_rate": int(sr),
              "reference_finite": finite_x, "output_finite": finite_y,
              "alignment": "none", "gain_normalization": "none", "mr_stft": None,
              "band_energy": None, "rms_gain_error_db": None, "pitch": None,
              "output_rms_dbfs": _dbfs_rms(y) if finite_y else None,
              "output_peak": float(np.max(abs(y))) if len(y) and finite_y else None}
    if not finite_x or not finite_y:
        result["status"] = "nonfinite_input_or_output"
        return result
    if len(x) != len(y):
        result["status"] = "length_mismatch"
        return result
    if not len(x):
        result["status"] = "empty_signal"
        return result
    rx, ry = _rms(x), _rms(y)
    result["reference_rms_dbfs"] = _dbfs_rms(x)
    result["rms_gain_error_db"] = float(20*np.log10(max(ry, np.sqrt(POWER_FLOOR))/rx)) if rx > 0 else None
    result["rms_gain_status"] = "ok" if rx > 0 else "zero_reference_energy"
    result["mr_stft"] = _stft_metrics(x, y, sr)
    result["mr_stft_log_magnitude_mae_db"] = float(np.mean([r["log_magnitude_mae_db"] for r in result["mr_stft"]]))
    result["band_energy"] = _band_metrics(x, y, sr)
    if f0_truth is not None:
        result["pitch"] = pitch_metrics(y, sr, f0_truth)
    return result
