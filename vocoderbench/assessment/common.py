"""保存済み入力を厳密に読み、欠測を成功値に変えない共通処理。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile


class NotApplicable(ValueError):
    """定義域外。処理失敗とは区別して記録する。"""


def finite(value: Any, name: str = "value") -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{name}: 空配列・非有限値は使えません")
    return array


def number(value: Any, name: str = "value") -> float:
    array = finite(value, name)
    if array.ndim != 0:
        raise ValueError(f"{name}: スカラーが必要です")
    return float(array)


def integer(value: Any, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{minimum}以上の整数が必要です")
    return int(value)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> Any:
    def reject(value):
        raise ValueError(f"JSONの非有限値は使えません: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def ok(value: float | None, unit: str, **details: Any) -> dict:
    return {"status": "ok", "value": value, "unit": unit, **details}


def error_summary(errors: Any) -> dict:
    values = np.asarray(errors, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("誤差系列は有限な1次元配列が必要です")
    if not len(values):
        return {"count": 0, "mean": None, "mae": None, "rmse": None, "abs_p95": None, "abs_max": None}
    return {"count": len(values), "mean": float(values.mean()), "mae": float(np.abs(values).mean()),
            "rmse": float(np.sqrt(np.mean(values**2))), "abs_p95": float(np.percentile(np.abs(values), 95)),
            "abs_max": float(np.abs(values).max())}


class Inputs:
    """相対パスはmanifest基準。I/Oとハッシュ確認も各反復の時間に含む。"""

    def __init__(self, root: Path):
        self.root = root
        self.hashes: dict[str, str] = {}

    def path(self, name: str) -> Path:
        if not isinstance(name, str) or not name:
            raise ValueError("空でないファイルパスが必要です")
        path = (self.root / name).resolve()
        before = digest(path)
        previous = self.hashes.setdefault(str(path), before)
        if previous != before:
            raise ValueError(f"実行中に入力が変更されました: {path}")
        return path

    def json(self, name: str) -> Any:
        path = self.path(name)
        data = read_json(path)
        self.path(name)
        return data

    def array(self, name: str) -> np.ndarray:
        path = self.path(name)
        data = finite(np.load(path, allow_pickle=False), name)
        self.path(name)
        return data

    def audio(self, spec: str | dict) -> tuple[np.ndarray, int]:
        spec = {"path": spec} if isinstance(spec, str) else spec
        path = self.path(spec["path"])
        if path.suffix.lower() == ".npy":
            rate = integer(spec["sample_rate"])
            samples = np.load(path, allow_pickle=False)
        else:
            rate, samples = wavfile.read(path)
            if "sample_rate" in spec and rate != integer(spec["sample_rate"]):
                raise ValueError("WAVの標本化周波数と指定が異なります")
            if samples.dtype.kind == "u":
                if samples.dtype.itemsize != 1:
                    raise ValueError("未対応の符号なしPCMです")
                samples = (samples.astype(float) - 128) / 128
            elif samples.dtype.kind == "i":
                samples = samples.astype(float) / (2 ** (8 * samples.dtype.itemsize - 1))
            elif samples.dtype.kind != "f":
                raise ValueError("未対応のWAV形式です")
        samples = finite(samples, str(path))
        if samples.ndim != 1:
            raise ValueError("モノラル波形が必要です。自動ダウンミックスはしません")
        self.path(spec["path"])
        return samples, integer(int(rate))

    def pair(self, job: dict, same_length: bool = True) -> tuple[np.ndarray, np.ndarray, int]:
        x, rate = self.audio(job["reference"])
        y, output_rate = self.audio(job["output"])
        if rate != output_rate:
            raise ValueError("標本化周波数が不一致です。自動再標本化はしません")
        if same_length and len(x) != len(y):
            raise ValueError("波形長が不一致です。自動切り詰め・整列はしません")
        return x, y, rate


def trajectory(spec: Any, times: np.ndarray, name: str) -> np.ndarray:
    """スカラーまたは{times,values}。区間外へ外挿しない。"""
    if not isinstance(spec, dict):
        return np.full(len(times), number(spec, name))
    knots, values = finite(spec["times"], name), finite(spec["values"], name)
    if knots.ndim != 1 or values.shape != knots.shape or len(knots) < 2 or np.any(np.diff(knots) <= 0):
        raise ValueError(f"{name}: 単調増加時刻と同形の値が必要です")
    if len(times) and (times.min() < knots[0] or times.max() > knots[-1]):
        raise ValueError(f"{name}: 指定軌跡が評価区間を覆っていません")
    return np.interp(times, knots, values)


def frames(x: np.ndarray, rate: int, ms: float = 20, hop_ms: float = 5):
    n, hop = max(4, round(rate * ms / 1000)), max(1, round(rate * hop_ms / 1000))
    if len(x) < n:
        raise NotApplicable("完全な解析窓がありません")
    starts = np.arange(0, len(x) - n + 1, hop)
    views = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    return views, (starts + (n - 1) / 2) / rate, int(len(x) - (starts[-1] + n))
