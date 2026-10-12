"""#4、#6、#10。ASR推論と誤り集計、聴覚帯域、音響的傾斜を区別する。"""
from __future__ import annotations

import unicodedata

import numpy as np
from scipy import signal

from .common import NotApplicable, error_summary, frames, number, ok


def edits(a: list, b: list) -> int:
    previous = list(range(len(b) + 1))
    for i, token in enumerate(a, 1):
        current = [i]
        for j, other in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (token != other)))
        previous = current
    return previous[-1]


def content(job, inputs):
    data = inputs.json(job["transcripts"])
    if data.get("evidence_kind") not in ("asr_output", "synthetic_token_fixture"):
        raise ValueError("ASR出力か、記号列の計算用プローブかを明示してください")
    required = ("recognizer", "recognizer_revision", "language", "normalization", "reference_audio_sha256", "output_audio_sha256")
    if any(not data.get(key) for key in required):
        raise ValueError("同一認識器・版・言語・正規化・対応音声のハッシュを指定してください")
    # 収録済みの認識出力を採点する。ASRを実行したと偽らない。
    for key in ("reference", "output"):
        spec = job[key]
        path = inputs.path(spec if isinstance(spec, str) else spec["path"])
        if inputs.hashes[str(path)] != data[f"{key}_audio_sha256"]:
            raise ValueError("書き起こしに対応する音声のハッシュが不一致です")
    def normalize(text):
        if not isinstance(text, str):
            raise ValueError("書き起こしは文字列が必要です")
        mode = data["normalization"]
        if mode == "identity":
            return text
        if mode == "nfkc_casefold_whitespace":
            return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        raise ValueError("未対応の正規化規則です")
    text = {key: normalize(data[key]) for key in ("truth", "reference_text", "output_text")}
    results = {}
    for name in ("cer", "wer"):
        if name == "cer":
            def tokenize(value):
                return list(value.replace(" ", ""))
        else:
            if data.get("word_tokenization") != "whitespace":
                results[name] = {"status": "not_configured", "reason": "空白で分かち書き済みの語列が必要です"}
                continue
            tokenize = str.split
        truth = tokenize(text["truth"])
        if not truth:
            results[name] = {"status": "not_applicable", "reason": "正解トークンがありません"}
            continue
        a, b = (edits(truth, tokenize(text[key])) for key in ("reference_text", "output_text"))
        results[name] = {"status": "ok", "reference_errors": a, "output_errors": b, "truth_tokens": len(truth),
                         "reference_rate": a / len(truth), "output_rate": b / len(truth), "delta": (b - a) / len(truth)}
    if results["cer"]["status"] != "ok":
        raise NotApplicable("CERの正解文字がありません")
    limit = number(job["maximum_reference_cer"], "maximum_reference_cer")
    if limit < 0:
        raise ValueError("原音CERの上限は非負で指定してください")
    result = ok(results["cer"]["delta"], "CER差", scores=results,
              reference_usable=results["cer"]["reference_rate"] <= limit, maximum_reference_cer=limit,
              normalization=data["normalization"], recognizer=data["recognizer"], evidence_kind=data["evidence_kind"],
              timing_scope="保存済み認識結果の読み込み・誤り集計。ASR推論時間は含まない")
    if not result["reference_usable"]:
        result.update(status="partial", value=None, reason="原音CERが事前上限を超えています。増分を品質根拠に使いません")
    return result


def erb_features(x, rate):
    n, hop = max(4, round(rate * .04)), max(1, round(rate * .005))
    if rate < 4000 or len(x) < n:
        raise NotApplicable("ERB診断は4 kHz以上・40 ms以上が必要です")
    f, t, spectrum = signal.stft(x, fs=rate, nperseg=n, noverlap=n-hop, window="hann",
                                 boundary=None, padded=False)
    def erb(hz):
        return 21.4 * np.log10(1 + .00437 * hz)
    edges = (10 ** (np.linspace(erb(40), erb(rate / 2), 34) / 21.4) - 1) / .00437
    bands = np.maximum(0, np.minimum((f[None, :] - edges[:-2, None]) / np.diff(edges)[:-1, None],
                                     (edges[2:, None] - f[None, :]) / np.diff(edges)[1:, None]))
    norm = bands.sum(axis=1)
    if np.any(norm <= 0):
        raise NotApplicable("FFT分解能に対して空のERB帯域があります")
    power = (bands / norm[:, None]) @ np.abs(spectrum)**2
    return power, t, edges[1:-1], int(len(x) - (n + (len(t) - 1) * hop))


def auditory(job, inputs):
    x, y, rate = inputs.pair(job)
    a, times, centers, tail = erb_features(x, rate)
    b = erb_features(y, rate)[0]
    if not np.any(a > 1e-14):
        raise NotApplicable("参照帯域に有効なエネルギーがありません")
    floor = max(1e-14, float(a.max()) * 1e-8)
    delta = 10 * np.log10(np.maximum(b, floor) / np.maximum(a, floor))
    local = np.sqrt(np.mean(delta**2, axis=0))
    intervals = []
    for interval in job.get("intervals", []):
        start, end = number(interval["start"]), number(interval["end"])
        if not 0 <= start < end <= len(x) / rate:
            raise ValueError("区間境界が波形外または逆順です")
        mask = (times >= start) & (times < end)
        intervals.append({"label": interval["label"], "start": start, "end": end,
                          "status": "ok" if mask.any() else "not_applicable", **error_summary(local[mask])})
    return ok(float(np.mean(np.abs(delta))), "dB", local_frame_rmse=error_summary(local),
              per_band_mae_db=np.abs(delta).mean(axis=1).tolist(), centers_hz=centers.tolist(),
              reference_active_cells=int((a > floor).sum()), total_band_frame_cells=int(a.size),
              active_policy="参照電力が共通床より大きい帯域×フレーム。主値には全帯域を含む",
              intervals=intervals, sample_rate=rate, frame_seconds=times.tolist(),
              local_frame_rmse_db=local.tolist(), power_floor=floor, uncovered_tail_samples=tail,
              definition="ERB間隔32三角帯域、40 ms Hann、5 ms間隔。聴覚モデル・MOS・JNDではない")


def spectral_slope(x, rate, low, high):
    if not 0 < low < high < rate / 2:
        raise NotApplicable("傾斜の測定帯域がNyquist内にありません")
    views, _, _ = frames(x, rate, 40, 10)
    power = np.mean(np.abs(np.fft.rfft(views * np.hanning(views.shape[1]), axis=1))**2, axis=0)
    frequencies = np.fft.rfftfreq(views.shape[1], 1 / rate)
    mask = (frequencies >= low) & (frequencies <= high)
    if mask.sum() < 3 or power[mask].max() <= 1e-20:
        raise NotApplicable("傾斜を測れる帯域エネルギーがありません")
    floor = max(1e-20, float(power[mask].max()) * 1e-8)
    return float(np.polyfit(np.log2(frequencies[mask]), 10 * np.log10(np.maximum(power[mask], floor)), 1)[0])


def timbre(job, inputs):
    x, y, rate = inputs.pair(job)
    low, high = number(job["low_hz"]), number(job["high_hz"])
    a, b = (spectral_slope(z, rate, low, high) for z in (x, y))
    target = number(job["target_delta_db_per_octave"])
    return ok(abs(b-a-target), "dB/oct", reference_slope=a, output_slope=b,
              achieved_delta=b-a, requested_delta=target, signed_error=b-a-target,
              scope="音響的スペクトル傾斜のみ。フォルマント・息っぽさの知覚制御は未校正")
