"""Minimal pinned sigproc helpers for the PML source-compatibility port.
Copyright(C)2016 Engineering Department, University of Cambridge, UK.
Apache-2.0; see LICENSE-PML-SIGPROC.txt. Original author Gilles Degottex.
Modified2026-10-15: selected three functions; preserve Python2 integer-array division
when fs is integer, plus explicit integer-index division.
Source sigproc@289d9dffe1f6ba84fa1fe962d6fb6e1062ec1cf6.
The unconventional high-pass 1−lowpass amplitude and in-place zero replacement
are intentionally retained, rather than replaced by similarly named filters.
"""

import numpy as np


def mag2db(a):
    return 20.0 * np.log10(np.abs(a))


def butter2hspec(fc, o, fs, dftlen, high=False):
    """
    Supposed to be the amplitude response of a Butterworth filter
    fc: cut-off [Hz]
    o: order
    fs: sampling frequency [Hz]
    """

    numerator = fs * np.arange(dftlen // 2 + 1)
    F = (
        numerator // dftlen
        if np.issubdtype(numerator.dtype, np.integer)
        else numerator / dftlen
    )
    H = 1.0 / np.sqrt(1.0 + (F / fc) ** (2 * o))

    if high:
        H = 1.0 - H

    return H


def hspec2minphasehspec(X, replacezero=False):
    if replacezero:
        X[X == 0.0] = np.finfo(X[0]).resolution
    dftlen = (len(X) - 1) * 2
    cc = np.fft.irfft(np.log(X))
    cc = cc[: dftlen // 2 + 1]
    cc[1:-1] *= 2
    return np.exp(np.fft.rfft(cc, dftlen))
