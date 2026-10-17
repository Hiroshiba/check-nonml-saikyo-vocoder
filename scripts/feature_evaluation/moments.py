"""Centered population moments and recording-equal total variance."""

import numpy as np


def centered_moments(matrix):
    x = np.asarray(matrix)
    if x.dtype != np.float64 or x.ndim != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Invalid feature matrix")
    mean = x.mean(axis=0)
    delta = x - mean
    variance = np.mean(delta * delta, axis=0)
    if not np.isfinite([mean, variance]).all() or np.any(variance < 0):
        raise ValueError("Invalid centered moments")
    return mean, variance


def recording_equal_scale(means, variances):
    m = np.asarray(means, dtype=np.float64)
    v = np.asarray(variances, dtype=np.float64)
    if (
        m.ndim != 2
        or m.shape != v.shape
        or len(m) != 120
        or not np.isfinite([m, v]).all()
        or np.any(v < 0)
    ):
        raise ValueError("Complete fixed120 centered moments required")
    center = m.mean(0)
    total = np.mean(v + (m - center) ** 2, axis=0)
    scale = np.sqrt(total)
    if not np.isfinite(scale).all():
        raise ValueError("Nonfinite train scale")
    constant = scale <= 1e-12
    return (
        center,
        np.where(constant, 1.0, scale),
        {
            "recording_count": 120,
            "constant_dimensions": int(constant.sum()),
            "minimum_total_variance": float(total.min()),
            "method": "mean(within_record_population_variance + squared_record_mean_deviation)",
        },
    )


def ridge_fit_predict(train, test, target, alpha=1.0):
    if alpha != 1.0:
        raise ValueError("Ridge alpha is frozen at one")
    x = np.asarray(train, dtype=np.float64)
    ev = np.asarray(test, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    if (
        len(x) != 120
        or x.ndim != 2
        or ev.ndim != 2
        or ev.shape[1] != x.shape[1]
        or y.shape != (120,)
        or not np.isfinite(x).all()
        or not np.isfinite(ev).all()
    ):
        raise ValueError("Invalid readout matrices")
    valid = np.isfinite(y)
    if valid.sum() < 2:
        raise ValueError("Fewer than two valid train targets")
    center = x[valid].mean(0)
    rawscale = x[valid].std(0)
    scale = np.where(rawscale > 1e-12, rawscale, 1.0)
    z = (x[valid] - center) / scale
    yc = y[valid].mean()
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    coef = (vt.T * (s / (s * s + alpha))) @ (u.T @ (y[valid] - yc))
    predicted = ((ev - center) / scale) @ coef + yc
    rank = (
        int(np.sum(s > np.max(z.shape) * np.finfo(np.float64).eps * s[0]))
        if len(s) and s[0] > 0
        else 0
    )
    return (
        predicted,
        {
            "center": center,
            "scale": scale,
            "coefficients": coef,
            "target_center": yc,
            "train_valid": valid,
        },
        {
            "alpha": alpha,
            "valid_train": int(valid.sum()),
            "constant_dimensions": int((rawscale <= 1e-12).sum()),
            "matrix_rank": rank,
            "dimensions": x.shape[1],
            "scaling": "target-valid train recording means; population std",
            "constant_prediction": float(yc),
        },
    )
