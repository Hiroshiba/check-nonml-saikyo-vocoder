"""#7〜9、#11。無編集出力と編集出力を比較し、指定以外の整列をしない。"""
from __future__ import annotations

import numpy as np
from scipy import signal

from ..metrics import estimate_f0_yin
from .acoustics import spectral_slope
from .common import NotApplicable, error_summary, finite, frames, number, ok, trajectory


def mapped_reference_times(job, output_times, reference_duration, output_duration, rate):
    mapping = job.get("time_map")
    if mapping is None:
        if abs(reference_duration-output_duration) > .5 / rate:
            raise ValueError("異なる長さには明示的な時間写像が必要です")
        return output_times
    a, b = finite(mapping["reference_seconds"]), finite(mapping["output_seconds"])
    if a.ndim != 1 or a.shape != b.shape or len(a) < 2 or np.any(np.diff(a) <= 0) or np.any(np.diff(b) <= 0):
        raise ValueError("時間写像の両軸は狭義単調増加である必要があります")
    if max(abs(a[0]), abs(b[0]), abs(a[-1]-reference_duration), abs(b[-1]-output_duration)) > .5/rate:
        raise ValueError("時間写像は両波形の開始・終了を覆う必要があります")
    return np.interp(output_times, b, a)


def pitch(job, inputs):
    x, y, rate = inputs.pair(job, same_length=False)
    if rate <= 4000:
        raise NotApplicable("既存YINの2 kHz前処理に対して標本化周波数が不足しています")
    a, b = (estimate_f0_yin(z, rate) for z in (x, y))
    ta, tb = a["center_samples"]/rate, b["center_samples"]/rate
    if not len(ta) or not len(tb):
        raise NotApplicable("80 msの完全なF0解析窓がありません")
    source_times = mapped_reference_times(job, tb, len(x)/rate, len(y)/rate, rate)
    # 有声・無声をまたいでF0を補間しない。未評価の端は別に数える。
    indices = np.searchsorted(ta, source_times)
    indices = np.clip(indices, 0, len(ta)-1)
    left = np.maximum(indices-1, 0)
    indices = np.where(abs(ta[left]-source_times) <= abs(ta[indices]-source_times), left, indices)
    covered = (source_times >= ta[0]) & (source_times <= ta[-1])
    cents = trajectory(job["target_cents"], tb, "target_cents")
    expected = a["f0_hz"][indices] * np.exp2(cents/1200)
    if not np.isfinite(expected).all():
        raise ValueError("ピッチ操作量が大きすぎます")
    in_range = (expected == 0) | ((expected >= 65) & (expected <= 700))
    selected = covered & in_range
    voiced, output_voiced = expected > 0, b["f0_hz"] > 0
    both = selected & voiced & output_voiced
    errors = 1200*np.log2(b["f0_hz"][both]/expected[both])
    summary = error_summary(errors)
    absolute = None
    if "target_f0_hz" in job:
        truth = trajectory(job["target_f0_hz"], tb, "target_f0_hz")
        if np.any(truth < 0):
            raise ValueError("指定F0は非負である必要があります")
        valid = (truth >= 65) & (truth <= 700) & output_voiced
        absolute = {**error_summary(1200*np.log2(b["f0_hz"][valid]/truth[valid])),
                    "missing_voiced_frames": int(((truth > 0) & ~output_voiced).sum()),
                    "false_voiced_frames": int(((truth == 0) & output_voiced).sum()),
                    "out_of_range_frames": int(((truth > 0) & ((truth < 65) | (truth > 700))).sum())}
    result = ok(summary["mae"], "cent", relative_error=summary, absolute_target_error=absolute,
                total_frames=len(tb), expected_voiced_frames=int((selected & voiced).sum()),
                expected_unvoiced_frames=int((selected & ~voiced).sum()),
                missing_voiced_frames=int((selected & voiced & ~output_voiced).sum()),
                false_voiced_frames=int((selected & ~voiced & output_voiced).sum()),
                unmapped_frames=int((~covered).sum()), out_of_range_frames=int((covered & ~in_range).sum()),
                gross_error_over_600_cents=int((abs(errors) > 600).sum()),
                octave_error_frames=int((abs(abs(errors)-1200) <= 100).sum()),
                frame_seconds=tb.tolist(), estimated_output_f0_hz=b["f0_hz"].tolist(),
                expected_relative_f0_hz=expected.tolist(), estimator=a["method"],
                limits="65〜700 Hz、80 ms窓・10 ms間隔。自然音声の絶対F0真値ではない")
    if not len(errors):
        result.update(status="not_applicable", reason="比較可能な両有声フレームがありません")
    return result


def gain(job, inputs):
    x, y, rate = inputs.pair(job)
    db = trajectory(job["target_gain_db"], np.arange(len(x))/rate, "target_gain_db")
    target = x * 10 ** (db/20)
    if not np.isfinite(target).all():
        raise ValueError("ゲイン指定から非有限値が生じました")
    a, times, tail = frames(target, rate)
    b = frames(y, rate)[0]
    ra, rb = np.sqrt(np.mean(a*a, axis=1)), np.sqrt(np.mean(b*b, axis=1))
    valid = ra > 1e-7
    errors = 20*np.log10(np.maximum(rb[valid], 1e-12)/ra[valid])
    summary = error_summary(errors)
    result = ok(summary["mae"], "dB", errors=summary, total_frames=len(ra),
                reference_silent_frames=int((~valid).sum()), silent_output_frames=int((valid & (rb <= 1e-12)).sum()),
                silent_region_output_rms_max=float(rb[~valid].max()) if (~valid).any() else None,
                output_peak=float(abs(y).max()), over_one_fraction=float(np.mean(abs(y) > 1)),
                frame_seconds=times.tolist(), uncovered_tail_samples=tail,
                definition="指定ゲインをサンプルごとに適用した期待RMS。知覚ラウドネスではない")
    if not len(errors):
        result.update(status="not_applicable", reason="参照に有効な振幅がありません")
    return result


def local_time(job, inputs):
    if job.get("probe_kind") != "isolated_energy_events":
        raise NotApplicable("この検出器は既知の孤立イベント専用です。自然音声の音素境界は未対応です")
    x, y, rate = inputs.pair(job, same_length=False)
    mapping = job["time_map"]
    mapped_reference_times(job, np.asarray([0.0]), len(x)/rate, len(y)/rate, rate)
    source = finite(job["event_seconds"])
    half = number(job["search_half_width_seconds"])
    ratio = number(job["minimum_peak_ratio"])
    if source.ndim != 1 or half <= 0 or not 0 < ratio <= 1 or np.any(np.diff(source) <= 2*half):
        raise ValueError("イベントは重複しない探索区間と、0より大きく1以下の検出比が必要です")
    target = np.interp(source, mapping["reference_seconds"], mapping["output_seconds"])
    if np.any(np.diff(target) <= 2*half):
        raise ValueError("出力側のイベント探索区間が重複しています")
    window = max(1, round(.005*rate))
    def envelope(z):
        return signal.convolve(z*z, np.ones(window)/window, mode="same")
    a, b = envelope(x), envelope(y)
    rows, errors = [], []
    for start, expected in zip(source, target):
        if start-half < 0 or start+half > len(x)/rate or expected-half < 0 or expected+half > len(y)/rate:
            raise ValueError("イベント探索区間が波形外です")
        ia, ja = int(np.ceil((start-half)*rate)), int(np.floor((start+half)*rate))+1
        ib, jb = int(np.ceil((expected-half)*rate)), int(np.floor((expected+half)*rate))+1
        reference_peak = float(a[ia:ja].max())
        if reference_peak <= 1e-14:
            raise ValueError("既知イベントの参照エネルギーがありません")
        peak = float(b[ib:jb].max())
        detected = peak >= reference_peak*ratio
        observed = (ib+int(np.argmax(b[ib:jb])))/rate if detected else None
        error = (observed-expected)*1000 if detected else None
        if detected:
            errors.append(error)
        rows.append({"reference_seconds": float(start), "expected_seconds": float(expected),
                     "observed_seconds": observed, "error_ms": error, "status": "ok" if detected else "missing",
                     "output_peak_power": peak, "reference_peak_power": reference_peak})
    summary = error_summary(errors)
    result = ok(summary["mae"], "ms", errors=summary, events=rows, event_count=len(rows),
                missing_events=len(rows)-len(errors), duration_error_seconds=len(y)/rate-mapping["output_seconds"][-1],
                definition="5 ms移動電力のピーク。未検出を0 msへ置換しない")
    if len(errors) < len(rows):
        result.update(status="partial" if errors else "not_applicable", reason="未検出イベントがあります")
    return result


def attributes(x, rate, low, high):
    rms = float(np.sqrt(np.mean(x*x)))
    f0 = estimate_f0_yin(x, rate)["f0_hz"] if rate > 4000 else np.asarray([])
    voiced = f0[f0 > 0]
    try:
        slope = spectral_slope(x, rate, low, high)
    except NotApplicable:
        slope = None
    return {"pitch_cents": float(1200*np.log2(np.median(voiced))) if len(voiced) else None,
            "level_db": float(20*np.log10(rms)) if rms > 1e-12 else None,
            "slope_db_per_octave": slope, "duration_seconds": len(x)/rate}


def interference(job, inputs):
    rows = []
    for sweep in job["sweeps"]:
        delta = number(sweep["delta"])
        control_scale = number(sweep["control_scale"])
        if delta <= 0 or control_scale <= 0 or not sweep.get("control_unit"):
            raise ValueError("中央差分の正の操作量と単位が必要です")
        minus, sr = inputs.audio(sweep["minus"])
        plus, other_sr = inputs.audio(sweep["plus"])
        if sr != other_sr:
            raise ValueError("中央差分の標本化周波数が不一致です")
        a, b = (attributes(z, sr, number(job["low_hz"]), number(job["high_hz"])) for z in (minus, plus))
        if set(sweep["expected_response"]) != set(a) or set(job["attribute_scales"]) != set(a):
            raise ValueError("全属性の期待応答と正規化尺度を事前指定してください")
        for key in a:
            scale = number(job["attribute_scales"][key])
            expected = number(sweep["expected_response"][key])
            if scale <= 0:
                raise ValueError("属性尺度は正である必要があります")
            derivative = (b[key]-a[key])/(2*delta) if a[key] is not None and b[key] is not None else None
            rows.append({"control": sweep["control"], "control_unit": sweep["control_unit"], "attribute": key,
                         "minus": a[key], "plus": b[key], "response": derivative, "expected_response": expected,
                         "control_scale": control_scale, "attribute_scale": scale,
                         "normalized_error": (derivative-expected)*control_scale/scale if derivative is not None else None,
                         "status": "ok" if derivative is not None else "not_applicable"})
    if not rows:
        raise ValueError("中央差分の測定条件がありません")
    result = ok(None, "干渉行列", matrix=rows, missing_cells=sum(r["response"] is None for r in rows),
                definition="属性ごとの期待応答との差。異なる属性を一つの総合点にしない")
    if result["missing_cells"]:
        result.update(status="partial", reason="測定できない応答があります")
    return result
