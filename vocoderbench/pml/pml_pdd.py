"""Restricted NumPy port of pinned sigproc sinusoidal.pyx (see PORT_MAP.md).
Copyright(C) 2016 Engineering Department, University of Cambridge, UK.
Licensed under Apache License 2.0; see LICENSE-PML-SIGPROC.txt.
Modified 2026-10-15: Python3/NumPy normal-path port, explicit RNG/diagnostics.
No waveform synthesis; no AM/FM demodulation or optional envelope removal.
"""

import numpy as np
from scipy import signal as sig


def wrap(x):
    return np.angle(np.exp(1j * x))


def pitchsync(f0s, nbperperiod=4):
    f = f0s.copy()
    f[:, 1] = np.interp(f[:, 0], f[f[:, 1] > 0, 0], f[f[:, 1] > 0, 1])
    f[:, 1] = np.clip(f[:, 1], 20.0, 5000.0)
    ts = [0.0]
    while ts[-1] < f[-1, 0]:
        cf0 = np.interp(ts[-1], f[:, 0], f[:, 1])
        ts.append(ts[-1] + (1.0 / nbperperiod) / cf0)
    ts = np.asarray(ts)
    return np.column_stack((ts, np.interp(ts, f[:, 0], f[:, 1])))


def ceiling_resample(ts, x, nts):
    # Upstream says nearest, but actually chooses first ts >= target.
    idx = np.searchsorted(ts, nts, side="left")
    return x[np.clip(idx, 0, len(x) - 1)].copy()


def extract_peaks(s, fs, f0, winlen, dftlen):
    freqs = f0 * np.arange(int(np.floor((fs / 2.0 - f0 / 2.0) / f0)) + 1)
    sa = np.abs(s)
    sa[sa == 0.0] = np.finfo(sa[0]).eps
    sa = np.log(sa)
    sf = (float(fs) / dftlen) * np.arange(dftlen // 2 + 1)
    issins = np.ones(len(freqs), dtype=bool)
    amps = np.zeros(len(freqs), dtype=np.float64)
    half = int(np.floor((f0 * dftlen / fs) / 2))
    offsets = np.arange(-half, half + 1, dtype=np.int64)
    for fi, f in enumerate(freqs):
        if fi == 0:
            amps[0] = sa[0]
            issins[0] = sa[1] < sa[0]
            continue
        center = int(f * dftlen / fs + 0.5)
        bins = center + offsets
        if bins.min() < 0 or bins.max() >= len(sa):
            raise ValueError("Peak search exceeds source spectrum support")
        peaks = np.where(np.diff(np.sign(np.diff(sa[bins]))) < 0)[0]
        if not len(peaks):
            issins[fi] = False
            continue
        # Deliberately preserve signed argmin (NO abs): upstream behavior.
        choice = np.argmin((peaks + 1) - half)
        imax = center + offsets[peaks[choice] + 1]
        ca, la, ra = sa[imax], sa[imax - 1], sa[imax + 1]
        a = (ra - ca + la - ca) / 2.0
        b = -la + ca + a
        c = la - a + b
        if a == 0.0:
            raise ValueError("Degenerate quadratic peak, no silent regularization")
        dx = -b / (2.0 * a)
        freqs[fi] = (imax + dx) * fs / dftlen
        amps[fi] = a * dx * dx + b * dx + c
    amps[~issins] = np.interp(freqs[~issins], sf, sa)
    amps = np.exp(amps)
    phase = np.angle(s)
    phase += (((winlen - 1) / 2) * 2 * np.pi / float(dftlen)) * np.arange(
        dftlen // 2 + 1
    )
    phase = wrap(np.interp(freqs, sf, np.unwrap(phase)))
    return np.vstack((freqs, amps, phase, issins))


def sinusoidal_params(wav, fs, f0s, rng, nbper=2.5):
    f = f0s.copy()
    f[:, 1] = np.interp(f[:, 0], f[f[:, 1] > 0, 0], f[f[:, 1] > 0, 1])
    sins = []
    diag = dict(empty_windows=0, random_uniform_draws=0, padded_windows=0)
    for t, f0 in f:
        winlen = int(0.5 + (nbper * fs / f0) / 2) * 2 + 1
        idx = np.arange(
            -int((winlen - 1) / 2), int((winlen - 1) / 2 + 1), dtype=np.int64
        )
        idx += int(0.5 + fs * t)
        if idx[0] < 0 or idx[-1] >= len(wav):
            diag["padded_windows"] += 1
            x = np.zeros(winlen)
            valid = (idx >= 0) & (idx < len(wav))
            x[valid] = wav[idx[valid]]
        else:
            x = wav[idx]
        freqs = f0 * np.arange(int(np.floor((fs / 2.0 - f0 / 2.0) / f0)) + 1)
        if np.linalg.norm(x) < np.finfo(float).eps:
            diag["empty_windows"] += 1
            diag["random_uniform_draws"] += len(freqs)
            sins.append(
                np.vstack(
                    (
                        freqs,
                        np.finfo(float).eps * np.ones(freqs.shape),
                        wrap(2 * np.pi * rng.rand(len(freqs))),
                        np.zeros(freqs.shape, dtype=bool),
                    )
                )
            )
            continue
        win = np.blackman(winlen)
        win = win / sum(win)
        dftlen = 2 ** (int(np.log2(winlen) + 1) + 1)
        s = np.fft.rfft(win * x, dftlen)
        sins.append(extract_peaks(s, fs, f0, winlen, dftlen))
    observations = sum(s.shape[1] for s in sins)
    amplitude_sum = float(sum(np.sum(s[1]) for s in sins))
    fallback_amplitude = diag["random_uniform_draws"] * np.finfo(float).eps
    diag.update(
        phase_observations_including_dc=int(observations),
        fallback_phase_observations=int(diag["random_uniform_draws"]),
        fallback_observation_fraction=float(
            diag["random_uniform_draws"] / observations
        ),
        fallback_amplitude_sum=float(fallback_amplitude),
        all_observation_amplitude_sum=amplitude_sum,
        fallback_amplitude_fraction=float(fallback_amplitude / amplitude_sum)
        if amplitude_sum
        else None,
        weighting="PDD is not amplitude weighted; amplitude fraction is descriptive only",
    )
    return sins, f, diag


def estimate_pdd(sins, f0s, fs, dftlen=4096, nbperperiod=4):
    """Pinned defaults A=None, rmPDtrend/outFscale/extrapDC=True."""
    if len(sins) != len(f0s):
        raise ValueError("Sinusoidal parameters and F0 sizes differ")
    h = max(s.shape[1] for s in sins)
    pd = np.zeros((len(sins), h), dtype=np.float64)
    freq = (float(fs) / dftlen) * np.arange(dftlen // 2 + 1)
    out = np.zeros((len(sins), dftlen // 2 + 1), dtype=np.float64)
    f = f0s.copy()
    f[:, 1] = np.interp(f[:, 0], f[f[:, 1] > 0, 0], f[f[:, 1] > 0, 1])
    for n, s in enumerate(sins):
        if s.shape[1] < 3:
            raise ValueError("PDD requires DC and at least two harmonics")
        p = s[2, :]  # Preserve upstream mutation of DC phase.
        p[0] = 0
        rp = p - np.arange(s.shape[1]) * p[1]
        pdh = np.diff(np.unwrap(rp))
        pd[n, : len(pdh)] = np.unwrap(pdh)
    b = np.hamming(2 * nbperperiod + 1)
    b = b / sum(b)
    pc = sig.medfilt(np.cos(pd), (nbperperiod * 2 + 1, 1))
    ps = sig.medfilt(np.sin(pd), (nbperperiod * 2 + 1, 1))
    smoothc = sig.filtfilt(b, [1], pc, axis=0)
    smooths = sig.filtfilt(b, [1], ps, axis=0)
    residual = pd - np.arctan2(smooths, smoothc)
    b = np.ones(2 * nbperperiod + 1)
    b = b / sum(b)
    pc = sig.filtfilt(b, [1], np.cos(residual), axis=0)
    ps = sig.filtfilt(b, [1], np.sin(residual), axis=0)
    v = pc * pc + ps * ps
    pdd = np.zeros_like(v)
    selected = v < 1
    with np.errstate(divide="ignore", invalid="ignore"):
        pdd[selected] = np.sqrt(-np.log(v[selected]))
    for n, s in enumerate(sins):
        out[n] = np.interp(freq, 0.5 * f[n, 1] + s[0, 1:], pdd[n, : len(s[0, 1:])])
        edge = int(dftlen * s[0, 2] / fs)
        out[n, :edge] = out[n, edge]
    if not np.isfinite(out).all():
        raise ValueError("Nonfinite original PDD; no silent clipping")
    return out


def analyze_pdd(wav, fs, f0s, dftlen=4096, seed=123):
    rng = np.random.RandomState(seed)
    ps = pitchsync(f0s, 4)
    sins, ps, diag = sinusoidal_params(wav, fs, ps, rng)
    pdd = estimate_pdd(sins, ps, fs, dftlen)
    diag.update(
        seed=int(seed),
        rng="numpy.random.RandomState MT19937; local per analyze",
        pitchsync_frames=len(ps),
        feature_resampling="first timestamp >= target",
    )
    return ceiling_resample(ps[:, 0], pdd, f0s[:, 0]), diag
