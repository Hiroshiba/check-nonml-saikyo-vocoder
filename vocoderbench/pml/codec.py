"""既測定の PML + 低域マスク拡張 + 60 FWCEP の公開 API。"""

import logging

import numpy as np

from . import fwcep
from .parameters import BINS, DEFAULT_SEED, FS, NFFT, PMLParameters

_LOG = logging.getLogger(__name__)


def encode(x, sr=FS, *, seed=DEFAULT_SEED, trace=None):
    """有限・mono・[-1,1] の 16 kHz 音声を解析する（最低 0.2 秒）。

    pyreaper/pyworld はここでのみ読み込む。trace 辞書を指定すると解析中の
    SPEC/PDD/NM/F0 と診断値、reaper に未加工の5戻り配列の独立コピーを
    保存する。保存用パラメーターには PDD や REAPER 観測配列は不要。
    入力の正規化・クリップ・再標本化は行わない。
    """
    if type(sr) is not int or sr != FS:
        raise ValueError("PML は現在 16000 Hz のみ対応しています")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed は 0 以上 2**32 未満の整数で指定してください")
    if np.asarray(x).dtype.kind not in "fiu":
        raise ValueError("入力は実数の音声配列で指定してください")
    x = np.ascontiguousarray(x, dtype=np.float64)
    if x.ndim != 1 or len(x) < int(0.2 * FS):
        raise ValueError("PML 解析には 0.2 秒以上の mono 音声が必要です")
    if not np.isfinite(x).all() or np.max(np.abs(x)) > 1:
        raise ValueError("入力は有限かつ [-1, 1] の範囲で指定してください")
    if not np.any(x):
        raise ValueError("完全なゼロ信号は PML 解析の対応対象外です")
    import pyreaper

    from .pml_analysis import analyze

    pcm = np.rint(x * 32767).astype(np.int16)
    pm_times, pm, times, f0, corr = pyreaper.reaper(
        pcm,
        FS,
        minf0=65.0,
        maxf0=700.0,
        do_high_pass=True,
        do_hilbert_transform=False,
        inter_pulse=0.01,
        frame_period=0.005,
        unvoiced_cost=0.9,
    )
    if trace is not None:
        reaper_trace = dict(
            pm_times=pm_times.copy(),
            pm=pm.copy(),
            f0_times=times.copy(),
            f0=f0.copy(),
            corr=corr.copy(),
        )
    del pm_times, pm, corr
    raw_f0 = np.column_stack((times, f0)).astype(np.float64)
    raw_f0[raw_f0[:, 1] < 0, 1] = 0.0
    if len(raw_f0) < 3:
        raise ValueError("REAPER が十分な F0 フレームを返しませんでした")
    if not np.any(raw_f0[:, 1] > 0):
        _LOG.warning("正の F0 が未検出です。上流仕様の 65 Hz 合成クロックを使用します")
    features, diagnostics = analyze(x, FS, raw_f0, seed=seed)
    spec = features["SPEC"]
    if (
        spec.shape != (len(features["f0s"]), BINS)
        or not np.isfinite(spec).all()
        or np.any(spec <= 0)
    ):
        raise ValueError("解析したスペクトル包絡が有限の正値ではありません")
    expected_times = np.arange(len(features["f0s"]), dtype=np.float64) * np.float64(
        0.005
    )
    if not np.array_equal(
        features["f0s"][:, 0].view(np.uint64), expected_times.view(np.uint64)
    ):
        raise ValueError("保存形式の 5 ms 時間グリッドに一致しません")
    params = PMLParameters(
        fwcep=fwcep.encode_log(np.log(spec), FS, 59).astype(np.float32),
        noise_mask=features["NM"],
        f0=features["f0s"][:, 1],
        n_samples=len(x),
        seed=seed,
    )
    if trace is not None:
        trace.update(
            features=features, diagnostics=diagnostics, raw_f0=raw_f0,
            reaper=reaper_trace,
        )
    return params


def decode(params, *, seed=None, trace=None):
    """保存特徴量のみから float64 音声を生成する。必要依存は NumPy/SciPy。

    seed の省略時は保存値を使用。正規化・クリップは行わない。
    trace['pulse'] は 0.25 秒以後のパルスがある場合のみ存在する。
    """
    from .pml_synthesis import synthesize

    selected_seed = params.seed if seed is None else seed
    if type(selected_seed) is not int or not 0 <= selected_seed < 2**32:
        raise ValueError("seed は 0 以上 2**32 未満の整数で指定してください")
    with np.errstate(over="raise", invalid="raise"):
        spec = np.exp(fwcep.decode_log(params.fwcep, FS, NFFT))
    if not np.isfinite(spec).all() or np.any(spec <= 0):
        raise ValueError("復号したスペクトル包絡が有限の正値ではありません")
    y = synthesize(
        FS,
        np.column_stack((params.times, params.f0)),
        spec,
        NM=params.noise_mask.astype(np.float64),
        wavlen=params.n_samples,
        ener_multT0=True,
        verbose=0,
        trace=trace,
        seed=selected_seed,
    )
    if not np.isfinite(y).all():
        raise ValueError("PML 合成出力に非有限値があります")
    if np.max(np.abs(y)) > 1:
        _LOG.warning("PML 出力が ±1 を超えています。自動クリップは行いません")
    return y
