"""共通位相時計による調波と、帯域PSDから生成した雑音の合成。"""
from __future__ import annotations

import numpy as np

from .hnm_parameters import HNMParameters, phase_clock, validate, virtual_f0


def _noise(params: HNMParameters, seed: int) -> np.ndarray:
    sr, n = params.sample_rate, params.n_samples
    nfft = 2 ** int(np.ceil(np.log2(sr * 0.020)))
    half = nfft // 2
    grid = np.fft.rfftfreq(nfft, 1 / sr)
    window = np.hanning(nfft)
    out, norm = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(seed)
    powers = np.trapezoid(params.noise_psd, params.frequency_grid, axis=1)
    active = np.flatnonzero(powers > 0)
    if not len(active):
        return out
    # 無音フレームにも色の形だけを補う。発音の有無は後段の包絡だけで決める。
    active_times = params.frame_times[active]
    insertion = np.searchsorted(active_times, params.frame_times)
    before = np.clip(insertion - 1, 0, len(active) - 1)
    after = np.clip(insertion, 0, len(active) - 1)
    nearest = np.where(np.abs(params.frame_times - active_times[before]) <=
                       np.abs(active_times[after] - params.frame_times), before, after)
    shape_indices = active[nearest]
    shapes = params.noise_psd[shape_indices] / powers[shape_indices, None]
    # 時間編集で解析フレームが疎になっても、合成窓の間隔は5 msを維持する。
    synthesis_times = np.arange(int(np.ceil(n / sr / 0.005)) + 1) * 0.005
    for time in synthesis_times:
        center = round(time * sr)
        start, end = center - half, center + half
        left, right = max(start, 0), min(end, n)
        if left >= right:
            continue
        next_frame = int(np.searchsorted(params.frame_times, time, side="right"))
        i0 = max(0, min(next_frame - 1, len(params.frame_times) - 1))
        i1 = min(next_frame, len(params.frame_times) - 1)
        weight = 0.0 if i0 == i1 else (time - params.frame_times[i0]) / (params.frame_times[i1] - params.frame_times[i0])
        shape = (1 - weight) * shapes[i0] + weight * shapes[i1]
        psd = np.interp(grid, params.frequency_grid, shape)
        # 連続PSDの台形積分に合わせ、DC/Nyquistの期待パワーを半重みにする。
        expected_power = (sr / nfft) * float(np.sum(psd) - 0.5 * (psd[0] + psd[-1]))
        if expected_power <= 0:
            raise ValueError("雑音の形を合成FFT格子へ写せませんでした")
        psd = psd / expected_power
        spectrum = (rng.standard_normal(len(grid)) + 1j * rng.standard_normal(len(grid))) * np.sqrt(psd * sr * nfft / 4)
        spectrum[0] = rng.standard_normal() * np.sqrt(0.5 * psd[0] * sr * nfft)
        spectrum[-1] = rng.standard_normal() * np.sqrt(0.5 * psd[-1] * sr * nfft)
        noise = np.fft.irfft(spectrum, nfft)
        local = slice(left - start, right - start)
        out[left:right] += noise[local] * window[local]
        norm[left:right] += window[local] ** 2
    carrier = np.divide(out, np.sqrt(norm), out=np.zeros_like(out), where=norm > 1e-15)
    target_power = np.interp(np.arange(n) / sr, params.frame_times, powers)
    return carrier * np.sqrt(target_power)


def decode(params: HNMParameters, seed: int = 0) -> np.ndarray:
    validate(params)
    sr = params.sample_rate
    t = np.arange(params.n_samples) / sr
    f0, phase = phase_clock(params)
    frame_f0 = virtual_f0(params)
    voiced = params.f0 > 0
    out = np.zeros(params.n_samples)
    for h in range(1, params.max_harmonics + 1):
        frame_frequency = h * frame_f0
        amp = np.array([np.interp(f, params.frequency_grid, envelope, right=0)
                        for f, envelope in zip(frame_frequency, params.harmonic_envelope)])
        amp *= voiced
        # 調波が帯域上限を横切る際にも急に現れたり消えたりしない。
        amp *= np.clip((sr * 0.495 - frame_frequency) / (sr * 0.02), 0, 1)
        if not np.any(amp):
            continue
        sample_amp = np.interp(t, params.frame_times, amp)
        sample_amp *= np.clip((sr * 0.495 - h * f0) / (sr * 0.02), 0, 1)
        offset = 0 if params.relative_phase is None else np.interp(t, params.frame_times, params.relative_phase[:, h - 1])
        out += sample_amp * np.cos(h * phase + offset)
    if np.any(params.noise_psd):
        out += _noise(params, seed)
    if not np.all(np.isfinite(out)):
        raise RuntimeError("独自HNMの合成結果が有限値になりませんでした")
    return out
