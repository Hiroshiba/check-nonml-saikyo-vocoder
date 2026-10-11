"""LLSM2 layer 0 comparator with externally supplied F0.

SPDX-License-Identifier: GPL-3.0-or-later
Input times must start at zero and have a uniform hop. Output is trimmed to
the input's sample count; raw native length and trimming are reported.
"""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import threading
import numpy as np

_LOCK = threading.Lock()
_LIB = None


def _library():
    global _LIB
    if _LIB is None:
        path = Path(os.environ.get("NONML_LLSM_LIBRARY", Path(__file__).parent / "build/libllsm_adapter.so"))
        _LIB = ctypes.CDLL(str(path.resolve()))
        arr = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS")
        _LIB.nonml_llsm_reconstruct.argtypes = [arr, ctypes.c_int, ctypes.c_int, arr, ctypes.c_int,
                                               ctypes.c_double, ctypes.c_uint, arr, ctypes.c_int]
        _LIB.nonml_llsm_reconstruct.restype = ctypes.c_int
    return _LIB


def reconstruct(x, sr: int, f0, time, *, seed: int = 0):
    """Return `(mono_waveform, metadata)` for an unedited LLSM layer 0 pass.

    Supported adapter contract: 16-96 kHz mono, >=40 ms, finite signal/F0,
    F0=0 or 40-2000 Hz, uniform sample-aligned frame times from 0 (hop<=50 ms).
    Zero F0 denotes unvoiced. This is an implementation bound, not a quality
    guarantee. Same-seed determinism is local to the pinned build/libc.
    """
    if any(np.iscomplexobj(a) for a in (x, f0, time)):
        raise ValueError("complex input is unsupported")
    x = np.asarray(x, dtype=np.float64)
    f0 = np.asarray(f0, dtype=np.float64)
    time = np.asarray(time, dtype=np.float64)
    if x.ndim != 1 or f0.ndim != 1 or time.ndim != 1:
        raise ValueError("x, f0 and time must be 1-D")
    if not isinstance(sr, (int, np.integer)) or not 16000 <= sr <= 96000 or len(x) < max(1, int(sr * .04)):
        raise ValueError("requires 16-96 kHz and at least 40 ms input")
    if len(f0) != len(time) or len(f0) < 2:
        raise ValueError("f0 and time need equal lengths >= 2")
    if not all(np.isfinite(a).all() for a in (x, f0, time)):
        raise ValueError("nonfinite input")
    if np.any((f0 != 0) & ((f0 < 40) | (f0 > 2000))):
        raise ValueError("F0 must be 0 (unvoiced) or in [40, 2000] Hz")
    if not isinstance(seed, (int, np.integer)) or seed < 0 or seed > 2**32 - 2:
        raise ValueError("seed must lie in [0, 2**32-2]")
    hop = float(time[1] - time[0])
    if not 1/sr <= hop <= .05 or abs(time[0]) > 1e-9 or not np.allclose(np.diff(time), hop, rtol=0, atol=1e-9):
        raise ValueError("frame times must start at 0 and be uniformly spaced")
    if abs(hop * sr - round(hop * sr)) > 1e-6:
        raise ValueError("frame hop must be sample-aligned")
    raw_expected = int(np.floor((len(f0) + 1) * hop * sr + .5))
    if raw_expected < len(x):
        raise ValueError("F0 timeline is too short to synthesize the input duration")
    if time[-1] > len(x) / sr + hop:
        raise ValueError("F0 timeline exceeds input by more than one hop")
    if max(len(x), len(f0), raw_expected + 2) > np.iinfo(np.int32).max:
        raise ValueError("array length exceeds native integer capacity")
    x = np.ascontiguousarray(x)
    f0 = np.ascontiguousarray(f0)
    dst = np.zeros(raw_expected + 2, dtype=np.float64)
    # Upstream uses libc global srand/rand; do not call this library concurrently
    # from C. Use separate worker processes for parallel comparisons.
    with _LOCK:
        ny = _library().nonml_llsm_reconstruct(x, len(x), sr, f0, len(f0), hop, int(seed), dst, len(dst))
    if ny < 0:
        raise RuntimeError(f"LLSM adapter error {ny}")
    if ny < len(x) or not np.isfinite(dst[:ny]).all():
        raise RuntimeError("LLSM produced invalid/short output")
    y = dst[:len(x)].copy()
    metadata = {"method": "llsm-layer0-czt-external-f0", "sample_rate": int(sr),
                "input_samples": len(x), "output_samples": len(y), "native_output_samples": int(ny),
                "trimmed_tail_samples": int(ny - len(x)), "fixed_delay_samples": 0,
                "hop_seconds": hop, "seed": int(seed), "f0_refine": False,
                "native_rng_seed": int(seed) + 1, "rng": "libc srand/rand; same pinned runtime only",
                "normalization": "none", "residual_waveform_bypass": False,
                "noise_band_edges_hz": [f for f in (2000, 4000, 8000) if f < sr / 2]}
    return y, metadata
