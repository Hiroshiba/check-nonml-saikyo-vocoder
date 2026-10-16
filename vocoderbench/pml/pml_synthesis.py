"""Measured lowband-extension PML compatibility port.
The first unprotected NM bin is extended to the low-frequency region.
Only the adopted synthesis configuration is exposed.
Copyright(C)2016 Engineering Department, University of Cambridge, UK.
Original author: Gilles Degottex. Apache-2.0; see LICENSE-PML-SIGPROC.txt.
Modified2026-10-15: Python3 print/integer-index syntax; explicit scipy.signal import;
minimal pinned helpers imported as pml_helpers. Default core retained; explicit lowband-rule alternative added.
Modified 2026-10-16: local RandomState replaces global RNG with identical MT19937
sequence; package imports; remove plotting/debugger; select measured lowband extension.
Source: gillesdegottex/pulsemodel@f1d0fbb397368e019efa4dfc96bde09482cd734b.
No file-output convenience wrapper or its peak normalization is included.
"""

import numpy as np
import scipy
import scipy.signal
from . import pml_helpers as sp


def getwinlen(f0, fs, nbper):
    return int(np.max((0.050 * fs, nbper * fs / f0)) / 2) * 2 + 1  # Has to be odd


def synthesize(
    fs, f0s, SPEC, NM, wavlen, *, ener_multT0=True, verbose=0, trace=None, seed=20261015
):
    """固定の既測定設定。外部呼出しには codec.decode を使う。"""
    nm_lowpasswinlen = 9
    hp_f0coef = 0.5
    antipreechohwindur = 0.001

    rng = np.random.RandomState(seed)
    winnbper = 4  # Number of periods in a synthesis windows. It still contains only one single pulse, but leaves space for the VTF to decay without being cut abruptly.

    # Copy the inputs to avoid modifying them
    f0s = f0s.copy()
    SPEC = SPEC.copy()
    if NM is not None:
        NM = NM.copy()
    else:
        NM = np.zeros(SPEC.shape)

    NM = np.clip(NM, 0.0, 1.0)  # The noise mask is supposed to be in [0,1]

    # Check the size of the inputs
    if f0s.shape[0] != SPEC.shape[0]:
        raise ValueError(
            "F0 size {} and spectrogram size {} do not match".format(
                f0s.shape[0], SPEC.shape[0]
            )
        )  # pragma: no cover
    if NM is not None:
        if SPEC.shape != NM.shape:
            raise ValueError(
                "spectrogram size {} and NM size {} do not match.".format(
                    SPEC.shape, NM.shape
                )
            )  # pragma: no cover

    if wavlen is None:
        wavlen = int(np.round(f0s[-1, 0] * fs))
    dftlen = (SPEC.shape[1] - 1) * 2
    shift = np.median(np.diff(f0s[:, 0]))
    if verbose > 0:
        print(
            "PML Synthesis (dur={}s, fs={}Hz, f0 in [{:.0f},{:.0f}]Hz, shift={}s, dftlen={})".format(
                wavlen / float(fs),
                fs,
                np.min(f0s[:, 1]),
                np.max(f0s[:, 1]),
                shift,
                dftlen,
            )
        )

    # Prepare the features

    # Enforce continuous f0
    f0s[:, 1] = np.interp(f0s[:, 0], f0s[f0s[:, 1] > 0, 0], f0s[f0s[:, 1] > 0, 1])
    winlenmax = getwinlen(np.min(f0s[:, 1]), fs, winnbper)
    if winlenmax > dftlen:
        raise ValueError("合成窓が FFT 長を超えています。F0 を黙って補正しません")

    if NM is not None:
        # Extend the first unprotected (2 F0) mask value toward DC.
        cuts = np.array(
            [int((float(dftlen) / fs) * 2 * v) for v in f0s[:, 1]], dtype=int
        )
        if np.any(cuts < 0) or np.any(cuts >= NM.shape[1]):
            raise ValueError("Cut outside saved mask bins")
        replacement = NM[np.arange(len(NM)), cuts].copy()
        for n, k in enumerate(cuts):
            NM[n, :k] = replacement[n]
        if trace is not None:
            trace.update(
                lowband_cut_indices=cuts.copy(),
                lowband_first_unprotected_values=replacement.copy(),
            )

    NM[NM <= 0.5] = 0.0
    NM[NM > 0.5] = 1.0

    # Generate the pulse positions [1](2) (i.e. the synthesis instants, the GCIs in voiced segments)
    ts = [0.0]
    while ts[-1] < float(wavlen) / fs:
        cf0 = np.interp(ts[-1], f0s[:, 0], f0s[:, 1])
        if cf0 < 50.0:
            cf0 = 50
        ts.append(ts[-1] + (1.0 / cf0))
    ts = np.array(ts)
    f0s = np.vstack((ts, np.interp(ts, f0s[:, 0], f0s[:, 1]))).T

    # Resample the features to the pulse positions

    # Spectral envelope uses the nearest, to avoid over-smoothing
    SPECR = np.zeros((f0s.shape[0], dftlen // 2 + 1))
    for n, t in enumerate(f0s[:, 0]):  # Nearest: Way better for plosives
        idx = int(np.round(t / shift))
        idx = np.clip(idx, 0, SPEC.shape[0] - 1)
        SPECR[n, :] = SPEC[idx, :]

    # Resample the noise feature to the pulse positions
    # Smooth the frequency response of the mask in order to avoid Gibbs
    # (poor Gibbs nobody want to see him)
    nm_lowpasswin = np.hanning(nm_lowpasswinlen)
    nm_lowpasswin /= np.sum(nm_lowpasswin)
    NMR = np.zeros((f0s.shape[0], dftlen // 2 + 1))
    for n, t in enumerate(f0s[:, 0]):
        idx = int(np.round(t / shift))  # Nearest is better for plosives
        idx = np.clip(idx, 0, NM.shape[0] - 1)
        NMR[n, :] = NM[idx, :]
        if nm_lowpasswinlen > 1:
            NMR[n, :] = scipy.signal.filtfilt(nm_lowpasswin, [1.0], NMR[n, :])

    NMR = np.clip(NMR, 0.0, 1.0)

    if trace is not None:
        trace.update(
            pulse_times=f0s[:, 0].copy(),
            pulse_f0=f0s[:, 1].copy(),
            effective_mask=NMR[0].copy(),
            effective_masks=NMR.copy(),
            gaussian=[],
        )

    # The complete waveform that we will fill with the pulses
    wav = np.zeros(wavlen)
    # Half window on the left of the synthesized segment to avoid pre-echo
    dampinhwin = np.hanning(
        1 + 2 * int(np.round(antipreechohwindur * fs))
    )  # 1ms forced dampingwindow
    dampinhwin = dampinhwin[: (len(dampinhwin) - 1) // 2 + 1]

    for n, t in enumerate(f0s[:, 0]):
        f0 = f0s[n, 1]

        if verbose > 1:
            print(
                "\rPM Synthesis (python) t={:4.3f}s f0={:3.3f}Hz               ".format(
                    t, f0
                ),
                end=" ",
            )

        # Window's length
        # TODO It should be ensured that the beggining and end of the
        #      noise is within the window. Nothing is doing this currently!
        winlen = getwinlen(f0, fs, winnbper)
        # TODO We also assume that the VTF's decay is shorter
        #      than winnbper-1 periods (dangerous with high pitched and tense voice).
        if winlen > dftlen:
            raise ValueError(
                "The window length ({}) is bigger than the DFT length ({}). Please, increase the dftlen of your spectral features or check if the f0 curve has extremly low values and try to clip them to higher values (at least higher than 50[Hz])".format(
                    winlen, dftlen
                )
            )  # pragma: no cover

        # Set the rough position of the pulse in the window (the closest sample)
        # We keep a third of the window (1 period) on the left because the
        # pulse signal is minimum phase. And 2/3rd (remaining 2 periods)
        # on the right to let the VTF decay.
        pulseposinwin = int((1.0 / winnbper) * winlen)

        # The sample indices of the current pulse wrt. the final waveform
        winidx = int(round(fs * t)) + np.arange(winlen) - pulseposinwin

        # Build the pulse spectrum

        # Let start with a Dirac
        S = np.ones(dftlen // 2 + 1, dtype=np.complex64)

        # Add the delay to place the Dirac at the "GCI": exp(-j*2*pi*t_i)
        delay = -pulseposinwin - fs * (t - int(round(fs * t)) / float(fs))
        S *= np.exp((delay * 2j * np.pi / dftlen) * np.arange(dftlen // 2 + 1))

        # Add the spectral envelope
        # Both amplitude and phase
        E = SPECR[n, :]  # Take the amplitude from the given one
        if hp_f0coef is not None:
            # High-pass it to avoid any residual DC component.
            fcut = hp_f0coef * f0
            HP = sp.butter2hspec(fcut, 4, fs, dftlen, high=True)
            E *= HP
            # Not necessarily good as it is non-causal, so make it causal...
            # ... together with the VTF response below.
        # Build the phase of the envelope from the amplitude
        E = sp.hspec2minphasehspec(E, replacezero=True)  # We spend 2 FFT here!
        S *= E  # Add it to the current pulse

        # Add energy correction wrt f0.
        # STRAIGHT and AHOCODER vocoders do it.
        # (why ? to equalize the energy when changing the pulse's duration ?)
        if ener_multT0:
            S *= np.sqrt(fs / f0)

        # Generate the segment of Gaussian noise
        # Use mid-points before/after pulse position
        if n > 0:
            leftbnd = int(np.round(fs * 0.5 * (f0s[n - 1, 0] + t)))
        else:
            leftbnd = int(np.round(fs * (t - 0.5 / f0s[n, 1])))  # int(0)
        if n < f0s.shape[0] - 1:
            rightbnd = int(np.round(fs * 0.5 * (t + f0s[n + 1, 0]))) - 1
        else:
            rightbnd = int(
                np.round(fs * (t + 0.5 / f0s[n, 1]))
            )  # rightbnd=int(wavlen-1)
        gausswinlen = rightbnd - leftbnd  # The length of the noise segment
        gaussnoise4win = rng.normal(size=(gausswinlen))  # The noise

        GN = np.fft.rfft(gaussnoise4win, dftlen)  # Move the noise to freq domain
        # Normalize it by its energy (@Yannis, That's your answer at SSW9!)
        if trace is not None:
            q = float(np.mean(np.abs(GN) ** 2))
            energy = float(gaussnoise4win @ gaussnoise4win)
            endpoint = float(abs(GN[0]) ** 2 + abs(GN[-1]) ** 2)
            trace["gaussian"].append(
                dict(
                    time=float(t),
                    length=int(gausswinlen),
                    q=q,
                    energy=energy,
                    normalized_energy=energy / q,
                    endpoint=endpoint,
                    parseval_error=q - (dftlen * energy + endpoint) / (dftlen + 2),
                )
            )
        GN /= np.sqrt(np.mean(np.abs(GN) ** 2))
        # Place the noise within the pulse's window
        delay = pulseposinwin - (leftbnd - winidx[0])
        GN *= np.exp((delay * 2j * np.pi / dftlen) * np.arange(dftlen // 2 + 1))

        # Add it to the pulse spectrum, under the condition of the mask
        S *= GN ** NMR[n, :]

        # That's it! the pulse spectrum is ready!

        # Move it to time domain
        deter = np.fft.irfft(S)[0:winlen]

        # Add half window on the left of the synthesized segment
        # to avoid any possible pre-echo
        deter[: leftbnd - winidx[0] - len(dampinhwin)] = 0.0
        deter[leftbnd - winidx[0] - len(dampinhwin) : leftbnd - winidx[0]] *= dampinhwin

        # Add half window on the right
        # to avoid cutting the VTF response abruptly
        deter[-len(dampinhwin) :] *= dampinhwin[::-1]

        if trace is not None and "pulse" not in trace and t >= 0.25:
            trace["pulse"] = dict(
                samples=deter.copy(),
                positions=winidx - fs * t,
                envelope=E.copy() * (np.sqrt(fs / f0) if ener_multT0 else 1.0),
                highpass=HP.copy(),
                time=float(t),
                f0=float(f0),
            )

        # Write the synthesized segment in the final waveform
        if winidx[0] < 0 or winidx[-1] >= wavlen:
            # The window is partly outside of the waveform ...
            # ... thus copy only the existing part
            itouse = np.logical_and(winidx >= 0, winidx < wavlen)
            wav[winidx[itouse]] += deter[itouse]
        else:
            wav[winidx] += deter

    if verbose > 1:
        print(
            "\r                                                               \r",
            end=" ",
        )

    return wav
