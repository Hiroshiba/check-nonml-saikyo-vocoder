"""nominal正値区間と厳密補集合を分ける、epsilon付き対数演算。"""
from __future__ import annotations

import math

from numba import njit
import numpy as np

from .common import PITCH_BINS, STATES


@njit
def logadd(a: float, b: float) -> float:
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    if a < b:
        a, b = b, a
    return a + math.log1p(math.exp(b - a))


@njit
def logsum(values: np.ndarray) -> float:
    total = -math.inf
    for value in values:
        total = logadd(total, value)
    return total


def support_operator(matrix: np.ndarray, epsilon: float) -> tuple:
    """各行先ではなく各列先で、両voicingの同一区間を実因子から検証する。"""
    if (matrix.shape != (STATES, STATES) or matrix.dtype != np.float64
            or not np.isfinite(matrix).all() or np.any(matrix < 0)):
        raise ValueError('実遷移因子のshape/dtype/有限性が不正です')
    left = np.empty(STATES, dtype=np.int32)
    right = np.empty(STATES, dtype=np.int32)
    offsets = np.zeros(STATES + 1, dtype=np.int32)
    indices = []
    weights = []
    for dest in range(STATES):
        block0 = np.flatnonzero(matrix[:PITCH_BINS, dest] > 0)
        block1 = np.flatnonzero(matrix[PITCH_BINS:, dest] > 0)
        if (not len(block0) or not np.array_equal(block0, block1)
                or block0[-1] - block0[0] + 1 != len(block0)):
            raise ValueError(f'forward/backward共通区間仮定が実因子で不成立: {dest}')
        left[dest] = int(block0[0])
        right[dest] = int(block0[-1]) + 1
        source = np.concatenate((block0, block1 + PITCH_BINS))
        indices.extend(source.tolist())
        weights.extend(np.log(matrix[source, dest] + epsilon).tolist())
        offsets[dest + 1] = len(indices)
    return (left, right, offsets, np.asarray(indices, dtype=np.int32),
            np.asarray(weights, dtype=np.float64))


@njit
def step(values: np.ndarray, left: np.ndarray, right: np.ndarray,
         offsets: np.ndarray, indices: np.ndarray, weights: np.ndarray,
         logepsilon: float) -> np.ndarray:
    """F_j: nominal正値辺のLSEと厳密補集合のlogepsilon項。"""
    combined = np.empty(PITCH_BINS, dtype=np.float64)
    prefix = np.empty(PITCH_BINS + 1, dtype=np.float64)
    suffix = np.empty(PITCH_BINS + 1, dtype=np.float64)
    for pitch in range(PITCH_BINS):
        combined[pitch] = logadd(values[pitch], values[pitch + PITCH_BINS])
    prefix[0] = -math.inf
    for pitch in range(PITCH_BINS):
        prefix[pitch + 1] = logadd(prefix[pitch], combined[pitch])
    suffix[PITCH_BINS] = -math.inf
    for pitch in range(PITCH_BINS - 1, -1, -1):
        suffix[pitch] = logadd(combined[pitch], suffix[pitch + 1])
    result = np.empty(STATES, dtype=np.float64)
    for dest in range(STATES):
        positive = -math.inf
        for pos in range(offsets[dest], offsets[dest + 1]):
            positive = logadd(positive, values[indices[pos]] + weights[pos])
        complement = logadd(prefix[left[dest]], suffix[right[dest]])
        result[dest] = logadd(positive, logepsilon + complement)
    return result


@njit
def summarize(alpha: np.ndarray, beta: np.ndarray, logz: float,
              histogram: np.ndarray, counts: np.ndarray,
              logvoiced: np.ndarray, loguv: np.ndarray, logv: np.ndarray,
              lognorm: np.ndarray, modes: np.ndarray) -> None:
    for frame in range(alpha.shape[0] - 1, -1, -1):
        maximum = -math.inf
        mode = 0
        mass_v = -math.inf
        mass_uv = -math.inf
        for pitch in range(PITCH_BINS):
            value = alpha[frame, pitch] + beta[pitch] - logz
            logvoiced[frame, pitch] = value
            mass_v = logadd(mass_v, value)
            if value > maximum:  # first index wins ties
                maximum = value
                mode = pitch
            mass_uv = logadd(mass_uv,
                             alpha[frame, pitch + PITCH_BINS]
                             + beta[pitch + PITCH_BINS] - logz)
        modes[frame] = mode
        logv[frame] = mass_v
        loguv[frame] = mass_uv
        lognorm[frame] = logadd(mass_v, mass_uv)
        for pitch in range(PITCH_BINS):
            offset = pitch - mode + PITCH_BINS - 1
            histogram[offset] = logadd(histogram[offset], logvoiced[frame, pitch])
            counts[offset] += 1


def marginals(observation: np.ndarray, transition: np.ndarray,
              initial: np.ndarray, epsilon: float) -> dict:
    if (observation.ndim != 2 or observation.shape[0] != STATES
            or observation.dtype != np.float64 or initial.shape != (STATES,)
            or initial.dtype != np.float64 or not np.isfinite(observation).all()
            or np.any(observation < 0) or not np.isfinite(initial).all()
            or np.any(initial < 0)):
        raise ValueError('保存観測・初期因子のshape/dtype/有限性が不正です')
    if not np.isfinite(epsilon) or epsilon <= 0:
        raise ValueError('librosa.util.tiny(O)が正の有限値ではありません')
    forward = support_operator(transition, epsilon)
    reverse = support_operator(transition.T.copy(), epsilon)
    logeps = math.log(epsilon)
    u = np.log(observation + epsilon)
    r = np.log(initial + epsilon)
    frames = observation.shape[1]
    alpha = np.empty((frames, STATES), dtype=np.float64)
    alpha[0] = r + u[:, 0]
    for frame in range(1, frames):
        alpha[frame] = u[:, frame] + step(alpha[frame - 1], *forward, logeps)
    logz = float(logsum(alpha[-1]))
    if not np.isfinite(logz):
        raise FloatingPointError('forward logZが非有限です')
    logvoiced = np.empty((frames, PITCH_BINS), dtype=np.float64)
    loguv = np.empty(frames, dtype=np.float64)
    logv = np.empty(frames, dtype=np.float64)
    lognorm = np.empty(frames, dtype=np.float64)
    modes = np.empty(frames, dtype=np.int16)
    histogram = np.full(2 * PITCH_BINS - 1, -np.inf, dtype=np.float64)
    counts = np.zeros(2 * PITCH_BINS - 1, dtype=np.int32)
    beta = np.zeros(STATES, dtype=np.float64)
    # Backward recursion uses transposed STORED weights, not row-normalized T.T.
    for frame in range(frames - 1, -1, -1):
        summarize(alpha[frame:frame + 1], beta, logz, histogram, counts,
                  logvoiced[frame:frame + 1], loguv[frame:frame + 1],
                  logv[frame:frame + 1], lognorm[frame:frame + 1],
                  modes[frame:frame + 1])
        if frame:
            beta = step(u[:, frame] + beta, *reverse, logeps)
    if (not np.isfinite(logvoiced).all() or not np.isfinite(loguv).all()
            or not np.isfinite(logv).all() or not np.isfinite(lognorm).all()
            or not np.isfinite(beta).all()):
        raise FloatingPointError('周辺支持またはbackward値が非有限です')
    log_hist_mean = histogram - math.log(frames)
    return {'logz': logz, 'logvoiced': logvoiced, 'loguv': loguv, 'logv': logv,
            'lognorm': lognorm, 'mode': modes, 'histogram_log_mean': log_hist_mean,
            'histogram_count': counts, 'initial_backward': beta,
            'forward_intervals': np.stack(forward[:2], axis=1),
            'backward_intervals': np.stack(reverse[:2], axis=1),
            'epsilon': epsilon}
