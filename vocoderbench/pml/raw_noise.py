"""Frozen RAW modulation with only observation collection removed.

Derived from frozen generator noise_control.py. Preserve callback order,
shape/dtype/D0/a/GN guards and necessary interpolation/modulation FFT.
No D1, a-squared summaries, hashes, geometry lists, or finish materialization.
"""

import numpy as np

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

EPS = 1e-12


class RawNoiseControl:
    def __init__(self, A_samples, L_raw):
        self.A, self.L = A_samples, L_raw
        self.calls = 0

    def __call__(self, *, noise, normalized_GN, D0, nfft, pulse_index,
                 pulse_time, leftbnd, rightbnd, spec_row):
        require(pulse_index == self.calls, "unexpected_noise_callback_order")
        require(nfft == 4096 and 0 <= spec_row < len(self.L), "callback_FFT_or_row")
        require(rightbnd - leftbnd == len(noise) and len(noise) > 0, "callback_length")
        require(noise.dtype == np.float64 and np.isfinite(D0) and D0 > 0, "invalid_noise_or_D0")
        n = np.arange(leftbnd, rightbnd)
        inside = (n >= 0) & (n < len(self.A))
        valid = n[inside]
        a = np.ones(len(n))
        ratio = (self.A[valid] + EPS) / (self.L[spec_row] + EPS)
        ratio[(self.A[valid] <= EPS) & (self.L[spec_row] <= EPS)] = 1
        a[inside] = np.sqrt(ratio)
        require(np.isfinite(a).all(), "nonfinite_a")
        modulated_fft = np.fft.rfft(a * noise, nfft)
        output = modulated_fft / D0
        require(np.isfinite(output).all(), "nonfinite_GN")
        self.calls += 1
        return output
