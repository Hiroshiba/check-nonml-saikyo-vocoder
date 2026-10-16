"""Minimal official FWCEP compatibility port; no transform runs at import.

Derived from sigproc/freqwarp.py at commit
289d9dffe1f6ba84fa1fe962d6fb6e1062ec1cf6, blob
4b64131ff55f9383334817dc43305071662946f5 (functions at lines 40–107),
and sigproc.py lin2mel, lines 85–86.
Copyright (C) 2016 Engineering Department, University of Cambridge, UK.
Original author: Gilles Degottex <gad27@cam.ac.uk>.
Licensed under the Apache License, Version 2.0:
https://www.apache.org/licenses/LICENSE-2.0
Distributed WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
See LICENSE-PML-SIGPROC.txt for the full license.

Modified 2026-10-16: Python3 port with explicit Python2 integer-fs floor-Hz
coordinates, explicit shape division, input copies and finite/support checks.
The source's doubled full-order Nyquist-quefrency endpoint is retained.
Payload float32 conversion is the caller's responsibility. Input floating dtype
is preserved; interpolation/FFT arithmetic follows installed NumPy as in the
literal source reference. No independent precision-changing cast is applied.
"""

import numbers
import numpy as np


def _integer(value, name, minimum):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral):
        raise TypeError(
            name + " must be an integer for the declared compatibility path"
        )
    value = int(value)
    if value < minimum:
        raise ValueError(name + " is below its supported minimum")
    return value


def _input(value, name):
    a = np.array(value, copy=True)
    if a.ndim not in (1, 2) or any(n == 0 for n in a.shape):
        raise ValueError(name + " must be a nonempty vector or row matrix")
    if a.dtype.kind not in "fi":
        raise TypeError(name + " must contain real floating or signed integer values")
    if a.dtype.kind == "i":
        a = a.astype(np.float64)
    if not np.isfinite(a).all():
        raise ValueError(name + " contains nonfinite values")
    return a


def _grid(fs, nfft):
    # Original lines 58–59 / 98–99: Python2 int/int array division.
    linear = fs * np.arange(nfft // 2 + 1) // nfft
    # Original sigproc.lin2mel, including its natural-log normalization.
    mel = 1125.0 * np.log(1.0 + linear / 700.0)
    nyquist_mel = 1125.0 * np.log(1.0 + (0.5 * fs) / 700.0)
    warped = 0.5 * fs * mel / nyquist_mel
    if np.any(np.diff(linear) <= 0) or np.any(np.diff(warped) <= 0):
        raise ValueError("Floor-Hz grid must be strictly increasing")
    return linear, warped


def encode_log(log_half, fs=16000, order=59):
    """Encode half natural-log amplitude; order59 returns 60 coefficients."""
    fs = _integer(fs, "fs", 1)
    a = _input(log_half, "log_half")
    if a.shape[-1] < 2:
        raise ValueError("At least DC and Nyquist bins are required")
    nfft = (a.shape[-1] - 1) * 2
    order = _integer(order, "order", 0)
    if order > nfft // 2:
        raise ValueError("order exceeds the source half-cepstrum support")
    linear, warped = _grid(fs, nfft)

    def row(x):
        # Original lines 62,65,68–69. Keep interpolation direction and scaling.
        envelope = np.interp(linear, warped, x)
        coefficients = np.fft.irfft(envelope)
        coefficients = coefficients[: 1 + order].copy()
        coefficients[1:] *= 2
        return coefficients

    if a.ndim == 1:
        result = row(a)
    else:
        result = np.zeros((a.shape[0], 1 + order))
        for i in range(a.shape[0]):
            result[i, :] = row(a[i, :])
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite encoded coefficients")
    return result


def decode_log(coeff, fs=16000, nfft=4096):
    """Decode to half natural-log amplitude, preserving source endpoint rules."""
    fs = _integer(fs, "fs", 1)
    nfft = _integer(nfft, "nfft", 2)
    if nfft % 2:
        raise ValueError("nfft must be even")
    a = _input(coeff, "coeff")
    if a.shape[-1] > nfft // 2 + 1:
        raise ValueError("Coefficient count exceeds source half-cepstrum support")
    linear, warped = _grid(fs, nfft)

    def row(x):
        # Original lines 102,105: zero-pad, real part, then inverse interpolation.
        warped_log = np.real(np.fft.rfft(x, nfft))
        return np.interp(warped, linear, warped_log)

    if a.ndim == 1:
        result = row(a)
    else:
        result = np.zeros((a.shape[0], nfft // 2 + 1))
        for i in range(a.shape[0]):
            result[i, :] = row(a[i, :])
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite decoded log spectrum")
    return result
