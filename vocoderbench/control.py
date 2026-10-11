"""Copy-only physical edits for WORLD-shaped parameter dataclasses.

The accepted edit ranges are numerical/operational guards, not an assertion of
audible quality. Parameter interpolation is not a physiological voice model.
No encoder or synthesizer is imported here.
"""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import Any, Callable

import numpy as np


PITCH_RANGE = (-24.0, 24.0)
GAIN_RANGE = (-60.0, 60.0)
TIME_RANGE = (0.25, 4.0)


def _scalar(value: float, name: str, bounds: tuple[float, float]) -> float:
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
        raise ValueError(f"{name} must be a finite scalar")
    value = float(value)
    if not np.isfinite(value) or not bounds[0] <= value <= bounds[1]:
        raise ValueError(f"{name} must be within {bounds}; this is an operational guard")
    return value


def _validate(params: Any) -> None:
    if not is_dataclass(params) or isinstance(params, type):
        raise TypeError("parameters must be a dataclass instance")
    f0 = np.asarray(params.f0)
    time = np.asarray(params.time)
    sp = np.asarray(params.spectral_envelope)
    ap = np.asarray(params.aperiodicity)
    if f0.ndim != 1 or f0.size < 2 or time.shape != f0.shape:
        raise ValueError("at least two matching F0/time frames are required")
    if sp.ndim != 2 or sp.shape[0] != f0.size or sp.shape[1] < 2 or ap.shape != sp.shape:
        raise ValueError("spectral envelope and aperiodicity must match the F0 frames")
    if any(not np.all(np.isfinite(a)) for a in (f0, time, sp, ap)):
        raise ValueError("parameters must contain only finite values")
    if isinstance(params.sample_rate, (bool, np.bool_)) or not isinstance(params.sample_rate, (int, np.integer)) or params.sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer")
    if isinstance(params.n_samples, (bool, np.bool_)) or not isinstance(params.n_samples, (int, np.integer)) or params.n_samples <= 0:
        raise ValueError("n_samples must be a positive integer")
    period = _scalar(params.frame_period, "frame_period", (0.01, 1000.0))
    expected = np.arange(f0.size, dtype=np.float64) * period / 1000.0
    if not np.allclose(time, expected, rtol=0.0, atol=1e-10):
        raise ValueError("time must start at zero on the fixed frame_period grid")
    if np.any(f0 < 0) or np.any(f0 >= params.sample_rate / 2):
        raise ValueError("F0 must be zero (unvoiced) or positive below Nyquist")
    if np.any(sp < 0) or np.any(ap < 0) or np.any(ap > 1):
        raise ValueError("spectral power must be nonnegative; aperiodicity must be in [0, 1]")


def _brackets(time: np.ndarray, positions: np.ndarray):
    left = np.clip(np.searchsorted(time, positions, side="right") - 1, 0, len(time) - 2)
    right = left + 1
    weight = np.clip((positions - time[left]) / (time[right] - time[left]), 0.0, 1.0)
    return left, right, weight


def _retime_f0(f0: np.ndarray, time: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """Nearest-frame voicing cells; log F0 only inside contiguous voiced islands.

    A voicing transition is halfway between adjacent input frames. At an exact
    midpoint the right-hand frame wins. A very short interval can disappear
    when the output grid undersamples it; this is measured, not concealed.
    """
    boundaries = (time[:-1] + time[1:]) / 2.0
    cells = np.searchsorted(boundaries, positions, side="right")
    output = np.zeros(len(positions), dtype=np.float64)
    voiced = f0 > 0
    changes = np.diff(np.r_[False, voiced, False].astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1
    for start, end in zip(starts, ends):
        selected = (cells >= start) & (cells <= end)
        if np.any(selected):
            output[selected] = np.exp(np.interp(
                positions[selected], time[start:end + 1], np.log(f0[start:end + 1])
            ))
    return output


def edit_parameters(
    params: Any,
    *,
    pitch_semitones: float = 0.0,
    gain_db: float = 0.0,
    time_scale: float = 1.0,
) -> Any:
    """Return a new dataclass without mutating or sharing input arrays.

    Duration scale is output_duration/input_duration. ``n_samples`` uses
    positive round-half-up. The native decoder may produce more samples; callers
    must report raw length and crop/pad separately from this requested length.

    Power is interpolated geometrically; exact zero endpoints and pairs of
    zero endpoints remain zero. A mixed zero/positive interval uses the smallest
    normal float64 power as its numerical log floor. Aperiodicity is a linear
    amplitude ratio and uses ordinary linear interpolation.
    """
    _validate(params)
    pitch = _scalar(pitch_semitones, "pitch_semitones", PITCH_RANGE)
    gain = _scalar(gain_db, "gain_db", GAIN_RANGE)
    scale = _scalar(time_scale, "time_scale", TIME_RANGE)
    old_f0 = np.asarray(params.f0, dtype=np.float64)
    old_time = np.asarray(params.time, dtype=np.float64)
    old_sp = np.asarray(params.spectral_envelope, dtype=np.float64)
    old_ap = np.asarray(params.aperiodicity, dtype=np.float64)

    if scale == 1.0:
        f0, time, sp, ap = (a.copy() for a in (old_f0, old_time, old_sp, old_ap))
        count = int(params.n_samples)
    else:
        count = int(np.floor(params.n_samples * scale + 0.5))
        if count < 1:
            raise ValueError("edited duration has no output samples")
        frame_step = params.frame_period / 1000.0
        frame_count = max(2, int(np.floor(count / (frame_step * params.sample_rate))) + 1)
        time = np.arange(frame_count, dtype=np.float64) * frame_step
        source_positions = time / scale
        f0 = _retime_f0(old_f0, old_time, source_positions)
        left, right, weights = _brackets(old_time, source_positions)
        weights = weights[:, None]
        low, high = old_sp[left], old_sp[right]
        floor = np.finfo(np.float64).tiny
        sp = np.exp((1.0 - weights) * np.log(np.maximum(low, floor))
                    + weights * np.log(np.maximum(high, floor)))
        sp[(low == 0) & (high == 0)] = 0.0
        sp = np.where(weights == 0, low, np.where(weights == 1, high, sp))
        ap = (1.0 - weights) * old_ap[left] + weights * old_ap[right]

    if pitch:
        f0[f0 > 0] *= 2.0 ** (pitch / 12.0)
    if gain:
        with np.errstate(over="ignore"):
            sp *= 10.0 ** (gain / 10.0)
    result = replace(
        params,
        f0=np.ascontiguousarray(f0),
        time=np.ascontiguousarray(time),
        spectral_envelope=np.ascontiguousarray(sp),
        aperiodicity=np.ascontiguousarray(ap),
        n_samples=count,
    )
    _validate(result)
    return result


def make_synthetic_parameters(
    parameter_factory: Callable[..., Any],
    *,
    sample_rate: int = 16000,
    duration_s: float = 0.5,
    f0_hz: float = 140.0,
    spectral_power: float = 0.001,
    aperiodicity: float = 0.001,
    frame_period: float = 5.0,
    fft_size: int = 1024,
) -> Any:
    """Build flat-envelope decoder inputs without invoking an encoder.

    This is a decoder/API fixture, not an independent model of natural speech.
    An all-unvoiced fixture uses f0_hz=0 and aperiodicity=1.
    """
    duration = _scalar(duration_s, "duration_s", (0.001, 60.0))
    period = _scalar(frame_period, "frame_period", (0.1, 100.0))
    if isinstance(sample_rate, (bool, np.bool_)) or not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer")
    if isinstance(fft_size, (bool, np.bool_)) or not isinstance(fft_size, (int, np.integer)) or fft_size < 16 or fft_size & (fft_size - 1):
        raise ValueError("fft_size must be a power of two of at least 16")
    frequency = _scalar(f0_hz, "f0_hz", (0.0, float(sample_rate / 2)))
    if frequency >= sample_rate / 2:
        raise ValueError("f0_hz must be below Nyquist")
    power = _scalar(spectral_power, "spectral_power", (0.0, 1000.0))
    ap = _scalar(aperiodicity, "aperiodicity", (0.0, 1.0))
    count = int(np.floor(duration * sample_rate + 0.5))
    frames = max(2, int(np.floor(count / (period / 1000.0 * sample_rate))) + 1)
    params = parameter_factory(
        f0=np.full(frames, frequency, dtype=np.float64),
        time=np.arange(frames, dtype=np.float64) * period / 1000.0,
        spectral_envelope=np.full((frames, fft_size // 2 + 1), power, dtype=np.float64),
        aperiodicity=np.full((frames, fft_size // 2 + 1), ap, dtype=np.float64),
        sample_rate=int(sample_rate),
        frame_period=period,
        n_samples=count,
    )
    _validate(params)
    return params


# Short alias for a comparison runner.
edit = edit_parameters
