"""WORLD（Harvest）の解析・合成用ctypesアダプター。

Scope: mono float64, 16--96 kHz, offline analysis of at least 100 ms.
学習済みモデルは使用しない。HarvestはF0推定、WORLDがボコーダー本体。
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
from functools import lru_cache
import json
import math
import os
from pathlib import Path

import numpy as np

REVISION = "c794856b537758a3d300757db2e5e31685a822c2"
SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent
DoublePointer = ct.POINTER(ct.c_double)
RowPointers = ct.POINTER(DoublePointer)


@dataclass
class WorldParameters:
    f0: np.ndarray
    time: np.ndarray
    spectral_envelope: np.ndarray
    aperiodicity: np.ndarray
    sample_rate: int
    frame_period: float
    n_samples: int
    method: str = "harvest"
    schema_version: int = SCHEMA_VERSION
    source_revision: str = REVISION
    status: str = "ok"


class _HarvestOption(ct.Structure):
    _fields_ = [("f0_floor", ct.c_double), ("f0_ceil", ct.c_double),
                ("frame_period", ct.c_double)]


class _CheapTrickOption(ct.Structure):
    _fields_ = [("q1", ct.c_double), ("f0_floor", ct.c_double), ("fft_size", ct.c_int)]


class _D4COption(ct.Structure):
    _fields_ = [("threshold", ct.c_double)]


def _ptr(array: np.ndarray) -> DoublePointer:
    return array.ctypes.data_as(DoublePointer)


def _rows(array: np.ndarray):
    # The caller keeps array alive until the native call returns.
    return (DoublePointer * array.shape[0])(*[_ptr(row) for row in array])


def library_path() -> Path:
    override = os.environ.get("NONML_WORLD_LIBRARY")
    if override:
        return Path(override).resolve()
    cache = Path(os.environ.get("NONML_WORLD_CACHE", ROOT / ".cache" / "world"))
    return cache.resolve() / REVISION / "libworld.so"


@lru_cache(maxsize=1)
def _lib():
    path = library_path()
    if not path.is_file():
        raise RuntimeError(f"Build WORLD first with {ROOT / 'build_world.py'} (missing {path})")
    lib = ct.CDLL(str(path))
    signatures = {
        "InitializeHarvestOption": ([ct.POINTER(_HarvestOption)], None),
        "InitializeCheapTrickOption": ([ct.c_int, ct.POINTER(_CheapTrickOption)], None),
        "InitializeD4COption": ([ct.POINTER(_D4COption)], None),
        "GetSamplesForHarvest": ([ct.c_int, ct.c_int, ct.c_double], ct.c_int),
        "Harvest": ([DoublePointer, ct.c_int, ct.c_int, ct.POINTER(_HarvestOption), DoublePointer, DoublePointer], None),
        "CheapTrick": ([DoublePointer, ct.c_int, ct.c_int, DoublePointer, DoublePointer, ct.c_int,
                        ct.POINTER(_CheapTrickOption), RowPointers], None),
        "D4C": ([DoublePointer, ct.c_int, ct.c_int, DoublePointer, DoublePointer, ct.c_int,
                 ct.c_int, ct.POINTER(_D4COption), RowPointers], None),
        "Synthesis": ([DoublePointer, ct.c_int, RowPointers, RowPointers, ct.c_int, ct.c_double,
                        ct.c_int, ct.c_int, DoublePointer], None),
    }
    for name, (args, result) in signatures.items():
        function = getattr(lib, name)
        function.argtypes = args
        function.restype = result
    return lib


def _sample_rate(value) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError("sample_rate must be an integer")
    value = int(value)
    if not 16000 <= value <= 96000:
        raise ValueError("supported sample rates are 16000 through 96000 Hz")
    return value


def _sample_count(value, name="n_samples") -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    value = int(value)
    if not 0 < value < 2**31:
        raise ValueError(f"{name} must be positive and fit an int32")
    return value


def _array(value, ndim: int, name: str) -> np.ndarray:
    array = np.asarray(value)
    if np.iscomplexobj(array) or array.ndim != ndim:
        raise ValueError(f"{name} must be a real {ndim}-dimensional array")
    array = np.ascontiguousarray(array, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains nonfinite values")
    return array


def validate(params: WorldParameters) -> None:
    """Reject unsafe native inputs; no silent clipping or repair."""
    sr = _sample_rate(params.sample_rate)
    _sample_count(params.n_samples)
    if params.schema_version != SCHEMA_VERSION or params.source_revision != REVISION:
        raise ValueError("unsupported WORLD parameter schema or source revision")
    fp = params.frame_period
    if not isinstance(fp, (int, float, np.number)) or not math.isfinite(fp) or not 1 <= fp <= 20:
        raise ValueError("frame_period must be 1 through 20 ms")
    f0 = _array(params.f0, 1, "f0")
    time = _array(params.time, 1, "time")
    sp = _array(params.spectral_envelope, 2, "spectral_envelope")
    ap = _array(params.aperiodicity, 2, "aperiodicity")
    frames = f0.size
    if frames < 2 or frames >= 2**31 or time.shape != f0.shape:
        raise ValueError("at least 2 matching f0/time frames are required")
    if sp.shape != ap.shape or sp.shape[0] != frames:
        raise ValueError("spectral_envelope/aperiodicity dimensions must match f0")
    fft_size = (sp.shape[1] - 1) * 2
    if fft_size < 16 or fft_size > 65536 or fft_size & (fft_size - 1):
        raise ValueError("spectral bins must imply a power-of-two FFT size (16--65536)")
    if np.any(sp <= 0) or np.any((ap < 0) | (ap > 1)):
        raise ValueError("spectral power must be positive and aperiodicity in [0, 1]")
    minimum_f0 = sr // fft_size + 1.0  # Match the integer division in upstream C++.
    if np.any(f0 < 0) or np.any(f0 >= sr / 2) or np.any((f0 > 0) & (f0 < minimum_f0)):
        raise ValueError(f"voiced F0 must reach WORLD synthesis floor {minimum_f0:g} Hz and be below Nyquist")
    if not np.allclose(time, np.arange(frames) * float(fp) / 1000.0, rtol=0, atol=1e-10):
        raise ValueError("time must be the uniform zero-origin frame grid")
    coverage = math.floor(frames * float(fp) * sr / 1000.0 + 1e-8)
    if params.n_samples > coverage:
        raise ValueError("n_samples exceeds the parameter time coverage")


def encode(x, sr: int, method: str = "harvest", *, frame_period: float = 5.0) -> WorldParameters:
    """Analyze mono audio; exact silence is measured by the native algorithm too.

    Inputs under 100 ms are rejected instead of being silently padded. The adapter
    supports normalized floating-point audio; it does not normalize the level.
    """
    sr = _sample_rate(sr)
    x = _array(x, 1, "x")
    _sample_count(x.size, "input length")
    if x.size < math.ceil(sr * 0.1):
        raise ValueError("WORLD analysis requires at least 100 ms in this adapter")
    if method != "harvest":
        raise ValueError("この比較アダプターはHarvestだけを使用します")
    if not math.isfinite(frame_period) or not 1 <= frame_period <= 20:
        raise ValueError("frame_period must be 1 through 20 ms")
    lib = _lib()
    option = _HarvestOption()
    lib.InitializeHarvestOption(ct.byref(option))
    option.frame_period = frame_period
    n_frames = lib.GetSamplesForHarvest(sr, x.size, frame_period)
    time, f0 = np.empty(n_frames), np.empty(n_frames)
    lib.Harvest(_ptr(x), x.size, sr, ct.byref(option), _ptr(time), _ptr(f0))
    cheaptrick = _CheapTrickOption()
    lib.InitializeCheapTrickOption(sr, ct.byref(cheaptrick))
    sp = np.empty((n_frames, cheaptrick.fft_size // 2 + 1))
    ap = np.empty_like(sp)
    sp_rows, ap_rows = _rows(sp), _rows(ap)
    lib.CheapTrick(_ptr(x), x.size, sr, _ptr(time), _ptr(f0), n_frames, ct.byref(cheaptrick), sp_rows)
    d4c = _D4COption()
    lib.InitializeD4COption(ct.byref(d4c))
    lib.D4C(_ptr(x), x.size, sr, _ptr(time), _ptr(f0), n_frames, cheaptrick.fft_size, ct.byref(d4c), ap_rows)
    params = WorldParameters(f0, time, sp, ap, sr, float(frame_period), int(x.size), method=method,
                             status="silent_input" if not np.any(x) else "ok")
    validate(params)
    return params


def decode(params: WorldParameters, n_samples: int | None = None) -> np.ndarray:
    """Synthesize directly to the requested length, with no post crop or padding.

    Full sample coverage is validated separately from quality at the boundaries.
    Stock offline WORLD resets its internal RNG on every invocation.
    """
    validate(params)
    n = params.n_samples if n_samples is None else _sample_count(n_samples)
    coverage = math.floor(len(params.f0) * params.frame_period * params.sample_rate / 1000.0 + 1e-8)
    if n > coverage:
        raise ValueError("requested n_samples exceeds the parameter time coverage")
    f0 = _array(params.f0, 1, "f0")
    sp = _array(params.spectral_envelope, 2, "spectral_envelope")
    ap = _array(params.aperiodicity, 2, "aperiodicity")
    y = np.empty(n, dtype=np.float64)
    sp_rows, ap_rows = _rows(sp), _rows(ap)
    _lib().Synthesis(_ptr(f0), f0.size, sp_rows, ap_rows, (sp.shape[1] - 1) * 2,
                     params.frame_period, params.sample_rate, n, _ptr(y))
    if not np.all(np.isfinite(y)):
        raise RuntimeError("WORLD returned nonfinite samples")
    return y


def save(params: WorldParameters, path) -> None:
    """Store only acoustic parameters and JSON metadata (never an input waveform)."""
    validate(params)
    metadata = {name: getattr(params, name) for name in
                ("sample_rate", "frame_period", "n_samples", "method", "schema_version", "source_revision", "status")}
    with Path(path).open("wb") as stream:
        np.savez_compressed(stream, f0=params.f0, time=params.time,
                            spectral_envelope=params.spectral_envelope,
                            aperiodicity=params.aperiodicity,
                            metadata=np.array(json.dumps(metadata)))


def load(path) -> WorldParameters:
    """Load a validated parameter archive with pickle disabled."""
    with np.load(path, allow_pickle=False) as data:
        expected = {"f0", "time", "spectral_envelope", "aperiodicity", "metadata"}
        if set(data.files) != expected:
            raise ValueError("unexpected WORLD archive fields")
        metadata = json.loads(str(data["metadata"].item()))
        required = {"sample_rate", "frame_period", "n_samples", "method", "schema_version", "source_revision", "status"}
        if set(metadata) != required:
            raise ValueError("unexpected WORLD metadata fields")
        params = WorldParameters(*(data[name].copy() for name in
                                   ("f0", "time", "spectral_envelope", "aperiodicity")), **metadata)
    validate(params)
    return params
