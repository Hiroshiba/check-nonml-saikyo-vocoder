"""独自の自己相関F0と、有限容量の調波・雑音解析。"""
from __future__ import annotations

import logging

import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d

from .hnm_parameters import HNMParameters, phase_clock, validate


def _frame(x, center, size):
    half = size // 2
    indices = np.arange(center - half, center - half + size)
    out = np.zeros(size)
    valid = (indices >= 0) & (indices < len(x))
    out[valid] = x[indices[valid]]
    return out


def _pitch_track(x, sr, times, f0_floor, f0_ceil):
    """評価用YINとは独立した正規化自己相関・候補連続性によるF0。"""
    size = round(sr * max(0.050, 3.5 / f0_floor))
    size += size % 2
    minimum = max(2, int(sr / f0_ceil))
    maximum = min(size // 2, int(np.ceil(sr / f0_floor)))
    f0, confidence = np.zeros(len(times)), np.zeros(len(times))
    previous = 0.0
    # 高域雑音を抑えるが、基音が欠けた入力でも周期全体を見られる帯域を残す。
    cutoff = min(4000, sr * 0.4)
    filtered = signal.sosfiltfilt(signal.butter(3, cutoff, fs=sr, output="sos"), x)
    for i, time in enumerate(times):
        frame = _frame(filtered, round(time * sr), size)
        frame -= np.mean(frame)
        if np.mean(frame ** 2) < 1e-16:
            previous = 0.0
            continue
        correlation = signal.correlate(frame, frame, mode="full", method="fft")[size - 1:]
        energy = np.concatenate(([0.0], np.cumsum(frame ** 2)))
        lags = np.arange(maximum + 1)
        denominator = np.sqrt(np.maximum(energy[size - lags] * (energy[size] - energy[lags]), 1e-30))
        normalized = correlation[:maximum + 1] / denominator
        peaks, _ = signal.find_peaks(normalized[minimum:maximum + 1])
        peaks += minimum
        if not len(peaks):
            previous = 0.0
            continue
        values = normalized[peaks]
        best_strength = float(np.max(values))
        threshold = 0.45 if previous > 0 else 0.55
        if best_strength < threshold:
            confidence[i] = max(0.0, best_strength)
            previous = 0.0
            continue
        # 倍周期候補が僅かに強いだけなら最短の周期を選ぶ。
        near_best = peaks[values >= max(threshold, best_strength - 0.06)]
        scores = normalized[near_best] - 0.015 * np.log2(near_best / near_best[0])
        if previous > 0:
            scores -= 0.025 * np.minimum(np.abs(np.log2((sr / near_best) / previous)), 2)
        lag = int(near_best[np.argmax(scores)])
        a, b, c = normalized[lag - 1:lag + 2]
        denominator2 = a - 2 * b + c
        offset = 0.5 * (a - c) / denominator2 if abs(denominator2) > 1e-12 else 0.0
        refined = lag + float(np.clip(offset, -0.5, 0.5))
        estimate = sr / refined
        if f0_floor <= estimate <= f0_ceil:
            f0[i], confidence[i] = estimate, float(np.clip(b, 0, 1))
            previous = estimate
    return f0, confidence


def _harmonic_fit(x, sr, center, f0, limit):
    size = round(sr * max(0.024, 4.0 / f0))
    size += size % 2
    window = np.hanning(size)
    frame = _frame(x, center, size)
    nfft = 2 ** int(np.ceil(np.log2(size * 8)))
    grid = np.fft.rfftfreq(nfft, 1 / sr)
    spectrum = np.fft.rfft(frame * window, nfft)
    # FFT原点をフレーム中心へ戻した後に補間し、位相の回転による補間減衰を防ぐ。
    centered = spectrum * np.exp(2j * np.pi * grid * (size // 2) / sr)
    harmonics = np.arange(1, min(limit, int(sr * 0.48 / f0)) + 1)
    frequencies = harmonics * f0
    fitted = np.interp(frequencies, grid, centered.real) + 1j * np.interp(frequencies, grid, centered.imag)
    return frequencies, 2 * np.abs(fitted) / np.sum(window), np.angle(fitted)


def _relative_phases(absolute, f0, clock, max_harmonics):
    relative = np.zeros_like(absolute)
    voiced = f0 > 0
    changes = np.diff(np.concatenate(([False], voiced, [False])).astype(int))
    islands = list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))
    for h in range(1, max_harmonics + 1):
        for start, end in islands:
            phase = np.unwrap(absolute[start:end, h - 1] - h * clock[start:end])
            relative[start:end, h - 1] = phase
        # 無声部の振幅は0。位相は隣接有声点を補間し、再開フレームの値を保持する。
        if np.any(voiced):
            indices = np.arange(len(f0))
            relative[:, h - 1] = np.interp(indices, indices[voiced], relative[voiced, h - 1])
    return relative


def encode(x, sr: int, *, frame_period=5.0, f0_floor=65.0, f0_ceil=700.0,
           max_harmonics=96, envelope_bins=513) -> HNMParameters:
    x = np.asarray(x)
    if x.ndim != 1 or np.iscomplexobj(x) or not np.all(np.isfinite(x)):
        raise ValueError("入力は有限な実数のモノラル音声が必要です")
    if not isinstance(sr, (int, np.integer)) or not 8000 <= sr <= 96000:
        raise ValueError("サンプルレートは8000〜96000 Hzの整数が必要です")
    if len(x) < max(64, round(sr * 0.050)):
        raise ValueError("解析には50 ms以上の入力が必要です")
    if not 1 <= frame_period <= 10 or not 35 <= f0_floor < f0_ceil <= 1400:
        raise ValueError("フレーム周期またはF0探索範囲が実装範囲外です")
    x = x.astype(np.float64)
    times = np.arange(int(np.ceil(len(x) / sr / (frame_period / 1000))) + 1) * frame_period / 1000
    grid = np.linspace(0, sr / 2, envelope_bins)
    f0, confidence = _pitch_track(x, sr, times, f0_floor, f0_ceil)
    envelope, noise_psd = np.zeros((len(times), len(grid))), np.zeros((len(times), len(grid)))
    absolute_phase = np.zeros((len(times), max_harmonics))
    params = HNMParameters(f0, times, grid, envelope, noise_psd, None, confidence,
                           int(sr), len(x), max_harmonics=max_harmonics,
                           status="silent_input" if not np.any(x) else "ok")
    params.analysis_metadata = {
        "f0_estimator": "normalized-autocorrelation-continuity-v1",
        "f0_floor_hz": f0_floor, "f0_ceil_hz": f0_ceil,
        "frame_count": len(times), "voiced_frames": int(np.count_nonzero(f0)),
        "low_confidence_frames": int(np.count_nonzero((confidence > 0) & (confidence < 0.55))),
        "unvoiced_or_unresolved_frames": int(np.count_nonzero(f0 == 0)),
        "phase_detail": "unwrapped-relative-harmonic-phase",
        "envelope_description": "fixed-Hz harmonic amplitude envelope; not physiological parameters",
        "stored_waveform_or_complex_residual": False,
    }
    _, clock = phase_clock(params)
    frame_clock = np.interp(times, np.arange(len(x)) / sr, clock)
    noise_size = round(sr * 0.020)
    noise_size += noise_size % 2
    noise_window = np.hanning(noise_size)
    local_times = (np.arange(noise_size) - noise_size // 2) / sr
    for i, time in enumerate(times):
        center = round(time * sr)
        noise_frame = _frame(x, center, noise_size)
        if f0[i] > 0:
            frequencies, amps, phases = _harmonic_fit(x, sr, center, f0[i], max_harmonics)
            # 差の波形はここだけで用い、帯域パワーへ集約して破棄する。
            periodic = np.sum(amps[:, None] * np.cos(2 * np.pi * frequencies[:, None] * local_times + phases[:, None]), axis=0)
            weighted_periodic = periodic * noise_window
            denominator = float(np.sum(weighted_periodic ** 2))
            if denominator > 1e-20:
                gain = np.clip(np.sum(noise_frame * noise_window * weighted_periodic) / denominator, 0, 2)
                amps *= gain
                periodic *= gain
            envelope[i] = np.interp(grid, frequencies, amps, left=amps[0], right=0.0)
            absolute_phase[i, :len(phases)] = phases
            noise_frame -= periodic
        frequencies, density = signal.periodogram(noise_frame, sr, window=noise_window, detrend=False, scaling="density")
        density = gaussian_filter1d(density, max(1.0, len(density) / 128))
        noise_psd[i] = np.interp(grid, frequencies, density)
        represented_power = float(np.trapezoid(noise_psd[i], grid))
        # 有限窓内の調波同士の干渉を雑音と誤認しないよう、実際の差を測る。
        target_power = float(np.sum(noise_window ** 2 * noise_frame ** 2) / np.sum(noise_window ** 2))
        if represented_power > 0:
            noise_psd[i] *= target_power / represented_power
    params.relative_phase = _relative_phases(absolute_phase, f0, frame_clock, max_harmonics)
    if np.any(f0 > 0) and np.any((f0 > 0) & (sr * 0.48 / np.maximum(f0, 1) > max_harmonics)):
        logging.info("調波数上限%dを超える帯域は雑音パワー表現に含めます", max_harmonics)
    validate(params)
    return params
