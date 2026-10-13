"""Independent, deterministic diagnostic signals; none uses a vocoder decoder.

These stimuli measure acoustic properties and meter calibration, not perceptual speech quality.
F0 truth is sample-wise Hz, with zero meaning known unvoiced/nonperiodic.
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def _level(x: np.ndarray, peak: float = 0.6) -> np.ndarray:
    p = float(np.max(np.abs(x))) if x.size else 0.0
    return x * (peak / p) if p else x


def _ramp(x: np.ndarray, sr: int) -> np.ndarray:
    x = x.copy()
    n = min(int(0.02 * sr), len(x) // 2)
    if n:
        r = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
        x[:n] *= r
        x[-n:] *= r[::-1]
    return x


def make_synthetic_cases(sr: int = 24000, seed: int = 20261011) -> list[dict]:
    """Return ten labeled diagnostics. Supported rates: 16, 24 and 48 kHz."""
    if sr not in (16000, 24000, 48000):
        raise ValueError("diagnostic sample rate must be 16000, 24000 or 48000")
    rng = np.random.default_rng(seed)
    cases = []

    def add(name, kind, x, truth=None):
        x = np.asarray(x, dtype=np.float64)
        cases.append({"id": f"{name}_{sr}", "kind": kind, "x": x,
                      "sr": sr, "f0_truth": np.zeros_like(x) if truth is None else np.asarray(truth, dtype=np.float64),
                      "generator": "independent-analytic-fixtures-v1", "input_seed": seed})

    t = np.arange(round(1.2 * sr)) / sr
    add("sine_120", "known_periodic", _ramp(0.5 * np.sin(2*np.pi*120*t), sr), np.full_like(t, 120))

    for f0 in (110, 220):
        x = sum(np.sin(2*np.pi*k*f0*t + 0.13*k*k) / k**1.3
                for k in range(1, int(min(6000, sr*0.45) // f0)+1))
        add(f"harmonic_{f0}", "known_periodic", _ramp(_level(x), sr), np.full_like(t, f0))

    x = sum(np.sin(2*np.pi*k*150*t + 0.07*k) / k for k in range(2, 16))
    add("missing_fundamental_150", "known_periodic", _ramp(_level(x), sr), np.full_like(t, 150))

    sweep_t = np.arange(round(1.5 * sr)) / sr
    f0 = 90 + 150 * (0.5 - 0.5*np.cos(np.pi*sweep_t/sweep_t[-1]))
    phase = 2*np.pi*np.cumsum(f0)/sr
    x = sum(np.sin(k*phase + 0.09*k*k)/k**1.4 for k in range(1, 20))
    add("harmonic_sweep_90_240", "known_periodic_sweep", _ramp(_level(x), sr), f0)

    # A separate source-filter family: oversampled impulses and fixed IIR
    # resonators, then anti-alias downsampling. This is not additive HNM.
    osr = 4 * sr
    high_t = np.arange(round(1.2 * osr)) / osr
    pulse = (np.diff(np.floor(90*high_t), prepend=-1) > 0).astype(float)
    for center, bandwidth in ((650, 85), (1150, 110), (2500, 160)):
        radius = np.exp(-np.pi*bandwidth/osr)
        a = [1, -2*radius*np.cos(2*np.pi*center/osr), radius*radius]
        pulse = signal.lfilter([1-radius], a, pulse)
    vowel = signal.resample_poly(pulse, 1, 4)[:len(t)]
    add("pulse_iir_vowel_90", "known_source_filter", _ramp(_level(vowel), sr), np.full_like(t, 90))

    nt = np.arange(round(1.5 * sr)) / sr
    noise = signal.sosfilt(signal.butter(4, [300, min(6000, sr*0.44)], fs=sr,
                                       btype="bandpass", output="sos"), rng.standard_normal(len(nt)))
    noise *= 0.55 + 0.45*np.sin(2*np.pi*6*nt)
    add("am_noise_6hz", "known_unvoiced", _ramp(_level(noise), sr))

    mt = np.arange(round(1.6 * sr)) / sr
    voiced = (mt < 0.55) | (mt >= 1.05)
    periodic = sum(np.sin(2*np.pi*k*170*mt)/k**1.3 for k in range(1, 20))
    unvoiced = signal.sosfilt(signal.butter(3, [500, min(6000, sr*0.44)], fs=sr,
                                          btype="bandpass", output="sos"), rng.standard_normal(len(mt)))
    mixed = np.where(voiced, periodic, unvoiced)
    add("voiced_unvoiced_boundaries", "known_mixed", _ramp(_level(mixed), sr), np.where(voiced, 170.0, 0.0))

    silence = np.zeros(round(0.8 * sr))
    add("silence", "silence", silence)
    impulse = silence.copy()
    impulse[round(0.3 * sr)] = 0.5
    add("impulse", "transient_diagnostic", impulse)
    return cases


def make_pitch_stress_cases(sr: int = 24000) -> list[dict]:
    """Broadband bandlimited pulses to expose integer-lag F0-estimator bias.

    The analytic cosine sum has a known period even when sr/F0 is noninteger.
    Equal harmonics extend to just below Nyquist. Two initial phases challenge
    endpoint filtering. These are meter-calibration stimuli, not speech quality.
    """
    if sr not in (16000, 24000, 48000):
        raise ValueError("supported diagnostic rates: 16000, 24000, 48000")
    t = np.arange(sr) / sr
    cases = []
    for f0 in (70.3, 90.7, 120.0, 160.0, 180.0, 220.0, 437.3, 650.0):
        harmonic_count = int((sr/2-1)/f0)
        for offset_cycles in (0.0, 0.37):
            phase = 2*np.pi*(f0*t+offset_cycles)
            x = np.zeros_like(t)
            for k in range(1, harmonic_count+1):
                x += np.cos(k*phase)
            x *= 0.6 / harmonic_count
            cases.append({"id": f"broadband_pulse_{f0:g}_phase{offset_cycles:g}_{sr}",
                          "kind": "meter_calibration_broadband_pulse", "x": x, "sr": sr,
                          "f0_truth": np.full_like(t, f0), "fundamental_hz": f0,
                          "harmonic_count": harmonic_count, "offset_cycles": offset_cycles,
                          "generator": "analytic-flat-harmonic-bank-v1"})
    return cases
