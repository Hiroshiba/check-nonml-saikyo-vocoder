"""Raw high-band power feature and predeclared cell amplitudes; no AM fit."""
import numpy as np
from scipy import signal

FS = 16000
EPS = 1e-12


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(name, value):
    require(np.isfinite(value).all(), "nonfinite:" + name)


def filters():
    ell = np.arange(65, dtype=np.float64)
    window = .5 - .5 * np.cos(2 * np.pi * ell / 64)
    b = (2 * 1500 / FS) * np.sinc((2 * 1500 / FS) * (ell - 32)) * window
    h = -b / b.sum()
    h[32] += 1
    h /= np.sum(h * (-1.0) ** ell)
    offsets = np.arange(-48, 49, dtype=np.float64)
    gaussian = np.exp(-(offsets ** 2) / (2 * 9.6 ** 2))
    gaussian /= gaussian.sum()
    return h, gaussian


def raw_features(x, source_f0):
    x = np.asarray(x, dtype=np.float64)
    source_f0 = np.asarray(source_f0, dtype=np.float64)
    require(x.ndim == 1 and len(x) >= 3200, "invalid_source_wave_shape")
    finite("source_wave", x)
    finite("source_F0", source_f0)
    require(np.max(np.abs(x)) <= 1, "source_exceeds_full_scale")
    require(source_f0.ndim == 1 and len(source_f0) >= 2 and np.all((source_f0 > 50) & (source_f0 < 700)), "unsupported_source_F0")
    h, gaussian = filters()
    z = signal.convolve(x, h, mode="same", method="direct")
    power_full = signal.convolve(z ** 2, gaussian, mode="same", method="direct")
    A = power_full[::8].copy()
    finite("A_raw", A)
    require(np.all(A >= 0), "negative_A_raw")
    A_samples = np.interp(np.arange(len(x)), np.arange(len(A)) * 8, A)
    L = np.zeros(len(source_f0))
    radius = np.rint(1.5 * FS / source_f0).astype(np.int64)
    centers = np.rint(np.arange(len(source_f0)) * .005 * FS).astype(np.int64)
    truncated = np.zeros(len(L), dtype=bool)
    supports = np.zeros((len(L), 2), dtype=np.int64)
    for j, (center, r) in enumerate(zip(centers, radius)):
        offsets = np.arange(-r, r + 1)
        n = center + offsets
        w = .5 * (1 + np.cos(np.pi * offsets / r))
        w[np.abs(offsets) >= r] = 0
        inside = (n >= 0) & (n < len(x))
        truncated[j] = not np.all(inside)
        use = inside & (w > 0)
        n, q = n[use], w[use] ** 2
        require(len(n) > 0 and q.sum() > 0, "empty_L_raw_support")
        q /= q.sum()
        L[j] = q @ A_samples[n]
        supports[j] = (n[0], n[-1])
    finite("L_raw", L)
    return {"A_raw": A, "L_raw": L, "highpass_FIR": h, "gaussian_FIR": gaussian,
            "L_radius": radius, "L_positive_support_samples": supports,
            "L_truncated": truncated,
            "A_gaussian_boundary_support": (np.arange(len(A)) * 8 < 48) | (np.arange(len(A)) * 8 + 48 >= len(x))}, A_samples
