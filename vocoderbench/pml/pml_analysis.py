"""Restricted PML analysis port; upstream mapping and changes in PORT_MAP.md.
Copyright(C) 2016 Engineering Department, University of Cambridge, UK.
Apache License 2.0. Modified 2026-10-15: Python3 isolated adapter/diagnostics.
"""

import warnings
import numpy as np
from scipy import signal as sig
from scipy import interpolate, ndimage
import pyworld
from .pml_pdd import analyze_pdd


def f0_postprocess(raw_f0s, f0_min=65.0, f0_max=700.0, shift=0.005):
    f = np.asarray(raw_f0s).copy()  # Preserve source dtype for threshold/assignments.
    if not np.issubdtype(f.dtype, np.floating):
        f = f.astype(np.float64)
    if f.ndim == 1:
        f = np.column_stack((shift * np.arange(len(f)), f))
    if f.ndim != 2 or f.shape[1] != 2 or len(f) < 3:
        raise ValueError("Expected at least three [time,F0] rows")
    if not np.isfinite(f).all() or not np.all(np.diff(f[:, 0]) > 0):
        raise ValueError("Invalid raw F0 values or times")
    diag = dict(
        raw_frames=len(f),
        raw_dtype=str(f.dtype),
        raw_unvoiced=int((f[:, 1] <= 0).sum()),
        all_unvoiced_fallback=not bool((f[:, 1] > 0).any()),
        f0_min=float(f0_min),
        f0_max=float(f0_max),
        shift=float(shift),
        step_removal=True,
    )
    if diag["all_unvoiced_fallback"]:
        warnings.warn("No positive F0: official fallback to f0_min", RuntimeWarning)
        f[:, 1] = f0_min
    voiced = f[:, 1] > 0
    f[:, 1] = np.interp(f[:, 0], f[voiced, 0], f[voiced, 1])
    diag["clipped_frames"] = int(((f[:, 1] < f0_min) | (f[:, 1] > f0_max)).sum())
    f[:, 1] = np.clip(f[:, 1], f0_min, f0_max)
    # Exact f0s_rmsteps normal path, including assignment back to source dtype.
    voiced = np.where(f[:, 1] > 0)[0]
    step = np.mean(np.diff(f[:, 0]))
    fc = (1.0 / step) / 4.0
    hshift = (1.0 / fc) / 8.0
    grid = np.arange(0.0, f[-1, 0], hshift)
    data = np.interp(grid, f[voiced, 0], f[voiced, 1])
    b, a = sig.butter(8, fc / (0.5 / hshift), btype="low")
    smooth = sig.filtfilt(b, a, data)
    f[voiced, 1] = np.interp(f[voiced, 0], grid, smooth)
    jitter = np.std(np.diff(f[:, 0]))
    threshold = 2 * np.finfo(f[0, 0]).resolution
    diag.update(
        time_step_std=float(jitter),
        resample_threshold=float(threshold),
        resampled=bool(jitter > threshold),
    )
    if diag["resampled"]:
        warnings.warn(
            "Nonuniform F0 grid: official regular-grid resampling", RuntimeWarning
        )
        vcs = f.copy()
        vcs[vcs[:, 1] > 0, 1] = 1
        nts = np.arange(f[0, 0], f[-1, 0], shift)
        vf = interpolate.interp1d(
            vcs[:, 0], vcs[:, 1], kind="nearest", bounds_error=False, fill_value=0
        )
        positive = f[:, 1] > 0
        vals = np.interp(nts, f[positive, 0], f[positive, 1])
        vals[vf(nts) == 0] = 0.0
        f = np.column_stack((nts, vals))
    diag.update(
        output_frames=len(f),
        post_steps_outside_bounds=int(((f[:, 1] < f0_min) | (f[:, 1] > f0_max)).sum()),
    )
    if not np.isfinite(f).all() or not (f[:, 1] > 0).all():
        raise ValueError("Invalid postprocessed F0; no extra repair")
    return f, diag


def noise_mask(f0s, pdd, fs, threshold=0.75):
    shift = np.mean(np.diff(f0s[:, 0]))
    nfft = (pdd.shape[1] - 1) * 2
    mask = pdd.copy()
    mask[pdd <= threshold] = 0.0
    mask[pdd > threshold] = 1.0
    struct = np.ones(
        (int(np.round((1.0 / 70.0) / shift)), int(np.round(70.0 * nfft / float(fs))))
    )
    harm = 1.0 - mask
    harm = ndimage.binary_opening(harm, structure=struct)
    harm = ndimage.binary_closing(harm, structure=struct)
    mask = 1.0 - harm
    for n in range(len(f0s)):
        mask[n, : int(np.round(1.5 * f0s[n, 1] * nfft / float(fs)))] = 0.0
    return mask


def analyze(
    wav, fs, raw_f0s, f0_min=65.0, f0_max=700.0, shift=0.005, dftlen=4096, seed=123
):
    x = np.ascontiguousarray(wav, dtype=np.float64)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("Expected finite mono waveform")
    f0s, fd = f0_postprocess(raw_f0s, f0_min, f0_max, shift)
    times = np.ascontiguousarray(f0s[:, 0], dtype=np.float64)
    cf0 = np.ascontiguousarray(f0s[:, 1], dtype=np.float64)
    refined = pyworld.stonemask(x, cf0, times, fs)
    power = pyworld.cheaptrick(x, refined, times, fs, fft_size=dftlen)
    if not np.isfinite(power).all() or (power < 0).any():
        raise ValueError("Invalid CheapTrick power")
    spec = np.sqrt(power)  # Explicit calibrated adapter; NOT literal 10*sqrt(power).
    pdd, pd = analyze_pdd(x, fs, f0s, dftlen, seed)
    mask = noise_mask(f0s, pdd, fs)
    features = dict(f0s=f0s, SPEC=spec, PDD=pdd, NM=mask, refined_ct_f0=refined)
    diag = dict(
        f0=fd,
        pdd=pd,
        spectral_units="sqrt(CheapTrick power); synthesis ener_multT0=True",
        stonemask_scope="CheapTrick only; PDD/synthesis retain postprocessed F0",
        dftlen=int(dftlen),
        pdd_threshold=0.75,
        mask_clean=True,
        mask_fraction=float(mask.mean()),
    )
    return features, diag
