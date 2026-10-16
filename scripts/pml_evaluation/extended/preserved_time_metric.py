"""原音で固定した局所電力eventを要求時刻写像で評価する新run用実装。"""

from __future__ import annotations

import numpy as np
from scipy import signal

from vocoderbench.assessment.common import error_summary, ok

HALF_WIDTH = 0.05
MINIMUM_PEAK_RATIO = 0.05
EVENT_RULE = {
    "power_window_seconds": 0.005,
    "minimum_peak_spacing_seconds": 0.12,
    "candidate_height_fraction_of_original_peak_power": 0.1,
    "absolute_power_floor": 1e-14,
    "search_half_width_seconds": HALF_WIDTH,
    "minimum_observed_to_reference_peak_ratio": MINIMUM_PEAK_RATIO,
    "selection": "original waveform only; scipy.signal.find_peaks; no output-dependent selection",
}


def envelope(wave, rate):
    window = max(1, round(0.005 * rate))
    return signal.convolve(wave * wave, np.ones(window) / window, mode="same")


def original_events(wave, rate):
    power = envelope(wave, rate)
    threshold = max(1e-14, float(power.max()) * 0.1)
    peaks, _ = signal.find_peaks(
        power, height=threshold, distance=max(1, round(0.12 * rate))
    )
    return [
        {
            "event_id": f"event_{index:04d}",
            "original_event_seconds": float(sample / rate),
            "original_peak_power": float(power[sample]),
        }
        for index, sample in enumerate(peaks)
    ]


def find_peak(power, rate, center, reference_peak):
    if center - HALF_WIDTH < 0 or center + HALF_WIDTH > len(power) / rate:
        return {
            "status": "window_outside_waveform",
            "observed_seconds": None,
            "peak_power": None,
        }
    begin = int(np.ceil((center - HALF_WIDTH) * rate))
    end = min(len(power), int(np.floor((center + HALF_WIDTH) * rate)) + 1)
    offset = int(np.argmax(power[begin:end]))
    peak = float(power[begin + offset])
    detected = peak >= max(1e-14, reference_peak * MINIMUM_PEAK_RATIO)
    return {
        "status": "ok" if detected else "weak_or_missing",
        "peak_power": peak,
        "observed_seconds": (begin + offset) / rate if detected else None,
    }


def evaluate_time(
    events,
    original,
    original_rate,
    baseline,
    rate,
    output,
    output_rate,
    scale=1.0,
    preservation=False,
):
    a, b = envelope(baseline, rate), envelope(output, output_rate)
    rows = []
    for event in events:
        row = {
            **event,
            "error_ms": None,
            "expected_seconds": None,
            "observed_seconds": None,
            "status": "pending_detection",
        }
        if preservation:
            reference = {
                "status": "ok",
                "observed_seconds": event["original_event_seconds"],
                "peak_power": event["original_peak_power"],
            }
        else:
            reference = find_peak(
                a, rate, event["original_event_seconds"], event["original_peak_power"]
            )
        row["baseline_detection"] = reference
        row["original_to_unedited_offset_ms"] = (
            (reference["observed_seconds"] - event["original_event_seconds"]) * 1000
            if reference["status"] == "ok"
            else None
        )
        if reference["status"] != "ok":
            row["status"] = "baseline_" + reference["status"]
        else:
            row["expected_seconds"] = scale * reference["observed_seconds"]
        rows.append(row)
    mapped = [row for row in rows if row["expected_seconds"] is not None]
    for index, row in enumerate(mapped):
        if any(
            abs(row["expected_seconds"] - other["expected_seconds"]) <= 2 * HALF_WIDTH
            for other in mapped[:index] + mapped[index + 1 :]
        ):
            row["status"] = "mapped_search_windows_overlap"
            continue
        reference = row["baseline_detection"]
        detected = find_peak(
            b, output_rate, row["expected_seconds"], reference["peak_power"]
        )
        row.update(
            status=detected["status"],
            observed_seconds=detected["observed_seconds"],
            output_peak_power=detected["peak_power"],
        )
        if detected["status"] == "ok":
            row["error_ms"] = (
                detected["observed_seconds"] - row["expected_seconds"]
            ) * 1000
    errors = error_summary([row["error_ms"] for row in rows if row["status"] == "ok"])
    reference_duration = (
        len(original) / original_rate if preservation else len(baseline) / rate
    )
    requested_duration = scale * reference_duration
    duration_error = len(output) / output_rate - requested_duration
    result = ok(
        errors["mae"],
        "ms",
        errors=errors,
        events=rows,
        event_count=len(rows),
        detected_events=errors["count"],
        missing_events=len(rows) - errors["count"],
        duration_error_seconds=duration_error,
        absolute_duration_error_seconds=abs(duration_error),
        reference_duration_seconds=reference_duration,
        requested_duration_seconds=requested_duration,
        output_duration_seconds=len(output) / output_rate,
        requested_scale=scale,
        time_map="t_out = requested_scale * detected_unedited_event_time"
        if not preservation
        else "identity original event time",
        endpoint_renormalization=False,
        waveform_alignment=False,
        selection=EVENT_RULE,
        definition="5 ms移動電力peakの局所event診断。自然音素の真の境界ではない。",
    )
    if errors["count"] != len(rows) or not rows:
        result.update(
            status="partial" if errors["count"] else "not_applicable",
            reason="未検出・窓外・比較不能eventを個別保持。長さ誤差とは独立。",
        )
    return result
