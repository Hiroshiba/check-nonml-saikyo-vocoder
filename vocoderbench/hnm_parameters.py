"""独自HNMの音響パラメータ。元波形や複素残差は保存しない。"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np

SCHEMA_VERSION = 1
METHOD = "independent_hnm_v1"


@dataclass
class HNMParameters:
    f0: np.ndarray
    frame_times: np.ndarray
    frequency_grid: np.ndarray
    harmonic_envelope: np.ndarray
    noise_psd: np.ndarray
    relative_phase: np.ndarray | None
    periodicity: np.ndarray
    sample_rate: int
    n_samples: int
    max_harmonics: int = 96
    schema_version: int = SCHEMA_VERSION
    method: str = METHOD
    status: str = "ok"
    analysis_metadata: dict = field(default_factory=dict)

    @property
    def time(self):
        return self.frame_times

    @property
    def scalar_count(self):
        arrays = (self.f0, self.frame_times, self.frequency_grid, self.harmonic_envelope,
                  self.noise_psd, self.periodicity)
        return sum(a.size for a in arrays) + (0 if self.relative_phase is None else self.relative_phase.size)


def validate(params: HNMParameters) -> None:
    if params.schema_version != SCHEMA_VERSION or params.method != METHOD:
        raise ValueError("対応していない独自HNMの保存形式です")
    if not isinstance(params.sample_rate, (int, np.integer)) or not 8000 <= params.sample_rate <= 96000:
        raise ValueError("サンプルレートは8000〜96000 Hzの整数が必要です")
    if not isinstance(params.n_samples, (int, np.integer)) or params.n_samples <= 0:
        raise ValueError("出力サンプル数は正の整数が必要です")
    if not isinstance(params.max_harmonics, (int, np.integer)) or not 1 <= params.max_harmonics <= 256:
        raise ValueError("調波数の上限は1〜256の整数が必要です")
    for name in ("f0", "frame_times", "frequency_grid", "harmonic_envelope", "noise_psd", "periodicity"):
        a = np.asarray(getattr(params, name))
        if np.iscomplexobj(a) or not np.all(np.isfinite(a)):
            raise ValueError(f"{name}に実数の有限値以外が含まれています")
    t, f0, grid = params.frame_times, params.f0, params.frequency_grid
    if t.ndim != 1 or len(t) < 2 or t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError("時刻は0から始まる単調増加の配列が必要です")
    if f0.shape != t.shape or params.periodicity.shape != t.shape:
        raise ValueError("F0・周期性・時刻のフレーム数が一致しません")
    if np.any((f0 < 0) | (f0 >= params.sample_rate / 2)):
        raise ValueError("F0は0以上かつNyquist周波数未満が必要です")
    if np.any((params.periodicity < 0) | (params.periodicity > 1)):
        raise ValueError("周期性は0〜1が必要です")
    if grid.ndim != 1 or len(grid) < 8 or grid[0] != 0 or np.any(np.diff(grid) <= 0):
        raise ValueError("周波数格子は0から始まる単調増加の配列が必要です")
    if not np.isclose(grid[-1], params.sample_rate / 2):
        raise ValueError("周波数格子はNyquist周波数まで必要です")
    shape = (len(t), len(grid))
    for name in ("harmonic_envelope", "noise_psd"):
        a = getattr(params, name)
        if a.shape != shape or np.any(a < 0):
            raise ValueError(f"{name}の形または非負値の条件が不正です")
    if params.relative_phase is not None:
        phase = params.relative_phase
        if phase.shape != (len(t), params.max_harmonics) or not np.all(np.isfinite(phase)):
            raise ValueError("相対位相の形または有限値の条件が不正です")
    if t[-1] + 1 / params.sample_rate < (params.n_samples - 1) / params.sample_rate:
        raise ValueError("パラメータの時刻範囲が出力サンプル数を覆っていません")


def virtual_f0(params: HNMParameters) -> np.ndarray:
    """無声区間の位相時計を補間する。そこで周期振幅は発生させない。"""
    voiced = params.f0 > 0
    if not np.any(voiced):
        return np.full_like(params.f0, 140.0)
    return np.interp(params.frame_times, params.frame_times[voiced], params.f0[voiced])


def phase_clock(params: HNMParameters) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(params.n_samples) / params.sample_rate
    f0 = np.interp(t, params.frame_times, virtual_f0(params))
    phase = np.zeros(params.n_samples)
    if params.n_samples > 1:
        phase[1:] = np.cumsum((f0[1:] + f0[:-1]) * np.pi / params.sample_rate)
    return f0, phase


def save(params: HNMParameters, path) -> None:
    validate(params)
    metadata = {key: getattr(params, key) for key in
                ("sample_rate", "n_samples", "max_harmonics", "schema_version", "method", "status", "analysis_metadata")}
    metadata["has_phase_detail"] = params.relative_phase is not None
    arrays = {key: getattr(params, key) for key in
              ("f0", "frame_times", "frequency_grid", "harmonic_envelope", "noise_psd", "periodicity")}
    arrays["relative_phase"] = np.empty((0, 0)) if params.relative_phase is None else params.relative_phase
    with Path(path).open("wb") as stream:
        np.savez_compressed(stream, **arrays, metadata=np.array(json.dumps(metadata)))


def load(path) -> HNMParameters:
    with np.load(path, allow_pickle=False) as data:
        expected = {"f0", "frame_times", "frequency_grid", "harmonic_envelope", "noise_psd", "periodicity", "relative_phase", "metadata"}
        if set(data.files) != expected:
            raise ValueError("保存ファイルに想定外の項目があります")
        meta = json.loads(str(data["metadata"].item()))
        has_phase = meta.pop("has_phase_detail")
        arrays = {key: data[key].copy() for key in expected - {"metadata", "relative_phase"}}
        params = HNMParameters(**arrays, relative_phase=data["relative_phase"].copy() if has_phase else None, **meta)
    validate(params)
    return params
