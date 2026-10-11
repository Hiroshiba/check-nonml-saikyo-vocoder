"""操作座標と、エンコーダーを経由しない合成入力。"""
from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from .hnm_parameters import HNMParameters, validate


def edit_parameters(params: HNMParameters, *, pitch_semitones=0.0, gain_db=0.0, time_scale=1.0) -> HNMParameters:
    validate(params)
    if not all(np.isfinite(value) for value in (pitch_semitones, gain_db, time_scale)) or time_scale <= 0:
        raise ValueError("操作量は有限値、時間倍率は正の値が必要です")
    if not -24 <= pitch_semitones <= 24 or not -60 <= gain_db <= 60 or not 0.25 <= time_scale <= 4:
        raise ValueError("実装範囲は音高±24半音、ゲイン±60 dB、時間倍率0.25〜4です。品質保証範囲ではありません")
    gain = 10 ** (gain_db / 20)
    edited = replace(params, f0=params.f0.copy() * 2 ** (pitch_semitones / 12),
                     frame_times=params.frame_times.copy() * time_scale,
                     frequency_grid=params.frequency_grid.copy(),
                     harmonic_envelope=params.harmonic_envelope.copy() * gain,
                     noise_psd=params.noise_psd.copy() * gain ** 2,
                     relative_phase=None if params.relative_phase is None else params.relative_phase.copy(),
                     periodicity=params.periodicity.copy(),
                     n_samples=max(1, math.floor(params.n_samples * time_scale + 0.5)),
                     analysis_metadata=dict(params.analysis_metadata))
    validate(edited)
    return edited


def without_details(params: HNMParameters) -> HNMParameters:
    validate(params)
    return replace(params, relative_phase=None)


def make_synthetic_parameters(*, f0_hz=140.0, sample_rate=16000, duration=0.5,
                              gain_db=-12.0, noise_fraction=0.0,
                              aperiodicity=None, max_harmonics=96) -> HNMParameters:
    """F0と有限帯域の形だけから作る。相対位相の細部は持たない。"""
    if aperiodicity is not None:
        noise_fraction = float(aperiodicity)
    if not 0 <= noise_fraction <= 1 or duration <= 0 or not np.isfinite(duration):
        raise ValueError("雑音割合は0〜1、長さは正の有限値が必要です")
    n = round(duration * sample_rate)
    times = np.arange(int(np.ceil(n / sample_rate / 0.005)) + 1) * 0.005
    grid = np.linspace(0, sample_rate / 2, 513)
    level = 10 ** (gain_db / 20)
    envelope = level / (1 + (grid / 250) ** 1.4)
    envelope *= np.sqrt(1 - noise_fraction) if f0_hz > 0 else 0
    density = np.full_like(grid, level ** 2 * (noise_fraction if f0_hz > 0 else 1) / (sample_rate / 2))
    params = HNMParameters(f0=np.full(len(times), float(f0_hz)), frame_times=times,
                           frequency_grid=grid, harmonic_envelope=np.tile(envelope, (len(times), 1)),
                           noise_psd=np.tile(density, (len(times), 1)), relative_phase=None,
                           periodicity=np.full(len(times), float(f0_hz > 0)),
                           sample_rate=sample_rate, n_samples=n, max_harmonics=max_harmonics)
    validate(params)
    return params
