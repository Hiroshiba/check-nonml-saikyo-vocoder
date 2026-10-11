"""自然音声の無加工再合成に対する追加診断。総合点や採否判定は作らない。"""
from __future__ import annotations

from importlib import metadata
import logging
import threading
import warnings

import numpy as np

from .metrics import estimate_f0_yin
from .temporal_metrics import measure_temporal

SCHEMA = "extended-diagnostics-v1"
ESTOI_SEED = 0
_ESTOI_LOCK = threading.Lock()


def _unavailable(reason):
    return {"status": "not_applicable", "value": None, "reason": reason}


def _estoi(x, y, sr, is_speech):
    result = {"value": None, "library": "pystoi", "version": None, "extended": True,
              "reference_required": True, "internal_sample_rate": 10000, "evaluation_seed": ESTOI_SEED,
              "internal_silence_removal_db": 40, "warnings": [], "normalization": "公式実装の行・列正規化",
              "scope": "明瞭性の推定。MOS・自然性・話者類似度ではない"}
    if not is_speech:
        return {**result, **_unavailable("音声以外の人工信号は明瞭性推定の対象外"), "status": "not_speech"}
    if float(np.std(x)) <= 1e-12:
        return {**result, **_unavailable("参照が無音または定数波形"), "status": "reference_no_ac_energy"}
    if float(np.std(y)) <= 1e-12:
        return {**result, **_unavailable("出力が無音または定数波形。出力エネルギーも参照すること"),
                "status": "output_no_ac_energy"}
    if len(x) / sr <= 0.026:
        return {**result, **_unavailable("eSTOIの最初の解析窓より短い")}
    try:
        from pystoi import stoi
        result["version"] = metadata.version("pystoi")
        # pystoiのepsilon摂動を再現可能にする。合成器のGeneratorとは独立。
        with _ESTOI_LOCK:
            rng_state = np.random.get_state()
            try:
                np.random.seed(ESTOI_SEED)
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter("always")
                    value = float(stoi(x, y, sr, extended=True))
            finally:
                np.random.set_state(rng_state)
        for item in captured:
            message = str(item.message)
            result["warnings"].append({"category": item.category.__name__, "message": message})
            logging.warning("eSTOI: %s: %s", item.category.__name__, message)
        if any("Not enough STFT frames" in row["message"] for row in result["warnings"]):
            return {**result, "status": "insufficient_active_frames", "library_raw_value": value,
                    "reason": "参照基準の無音除去後に30フレーム未満。ライブラリの代替値を採点しない"}
        if not np.isfinite(value) or any(row["category"] == "RuntimeWarning" for row in result["warnings"]):
            return {**result, "status": "numerically_unreliable",
                    "library_raw_value": value if np.isfinite(value) else None,
                    "reason": "非有限値または数値計算警告"}
        return {**result, "status": "measured", "value": value}
    except Exception as error:
        logging.exception("eSTOIの測定に失敗しました")
        return {**result, "status": "failed", "error": f"{type(error).__name__}: {error}"}


def _level(x):
    power = float(np.mean(x * x))
    peak = float(np.max(np.abs(x)))
    return {"rms": float(np.sqrt(power)), "rms_dbfs": float(10 * np.log10(power)) if power > 0 else None,
            "peak": peak, "peak_dbfs": float(20 * np.log10(peak)) if peak > 0 else None,
            "crest_factor_db": float(20 * np.log10(peak / np.sqrt(power))) if power > 0 else None,
            "mean": float(np.mean(x)), "zero_energy": power == 0}


def _full_scale(x):
    absolute = np.abs(x)
    exceeded = absolute >= 1.0
    starts = np.diff(np.r_[False, exceeded, False].astype(np.int8))
    lengths = np.flatnonzero(starts == -1) - np.flatnonzero(starts == 1)
    return {"sample_count": len(x), "full_scale_amplitude": 1.0,
            "at_or_above_full_scale_samples": int(np.sum(exceeded)),
            "at_or_above_full_scale_fraction": float(np.mean(exceeded)),
            "near_full_scale_amplitude": 0.999,
            "near_full_scale_fraction": float(np.mean(absolute >= 0.999)),
            "longest_full_scale_run_samples": int(np.max(lengths)) if len(lengths) else 0,
            "meaning": "固定振幅尺度の閾値超過。録音時のクリッピング発生の証明ではない"}


def _quiet_regions(x, y, sr):
    size = max(1, round(0.010 * sr))
    count = len(x) // size
    result = {"block_ms": 10.0, "block_samples": size, "total_blocks": count,
              "uncovered_tail_samples": len(x) - count * size,
              "meaning": "参照低エネルギー区間。人が付けた無音・無声ラベルではない"}
    if not count:
        return {**result, "status": "no_complete_blocks", "quiet_blocks": 0,
                "output_rms_dbfs": None, "output_peak": None, "output_energy_fraction": None}
    a = x[:count * size].reshape(count, size)
    b = y[:count * size].reshape(count, size)
    power = np.mean(a * a, axis=1)
    threshold = max(1e-6, float(np.max(power)) * 1e-4)
    quiet = power <= threshold
    selected = int(quiet.sum())
    output_power = float(np.mean(b[quiet] ** 2)) if selected else None
    reference_power = float(np.mean(a[quiet] ** 2)) if selected else None
    total_energy = float(np.sum(y * y))
    quiet_energy = float(np.sum(b[quiet] ** 2)) if selected else None
    return {**result, "status": "measured" if selected else "no_reference_quiet_blocks",
            "threshold_power": threshold, "threshold_dbfs": float(10 * np.log10(threshold)),
            "threshold_policy": "max(-60 dBFS, 最大参照ブロック電力より40 dB下)",
            "quiet_blocks": selected, "quiet_samples": selected * size,
            "reference_mean_power": reference_power, "output_mean_power": output_power,
            "output_rms_dbfs": float(10 * np.log10(output_power)) if output_power else None,
            "output_zero_energy": output_power == 0 if output_power is not None else None,
            "output_peak": float(np.max(np.abs(b[quiet]))) if selected else None,
            "output_energy_fraction": quiet_energy / total_energy if selected and total_energy > 0 else None,
            "energy_fraction_denominator": "出力波形全体のエネルギー"}


def _pitch_consistency(x, y, sr):
    reference, output = estimate_f0_yin(x, sr), estimate_f0_yin(y, sr)
    a, b = reference["f0_hz"], output["f0_hz"]
    both = (a > 0) & (b > 0)
    cents = 1200 * np.log2(b[both] / a[both])
    reference_voiced = int(np.sum(a > 0))
    n = reference["frame_samples"]
    starts = reference["start_samples"]
    return {"status": "estimated_consistency_not_ground_truth", "estimator": reference["method"],
            "fmin_hz": 65.0, "fmax_hz": 700.0, "frame_ms": 80.0, "hop_ms": 10.0,
            "prefilter": reference["prefilter"], "total_frames": len(a),
            "reference_estimated_voiced_frames": reference_voiced,
            "output_estimated_voiced_frames": int(np.sum(b > 0)),
            "both_estimated_voiced_frames": int(np.sum(both)),
            "reference_voiced_output_unvoiced_frames": int(np.sum((a > 0) & (b <= 0))),
            "reference_unvoiced_output_voiced_frames": int(np.sum((a <= 0) & (b > 0))),
            "paired_voiced_fraction": float(np.sum(both) / reference_voiced) if reference_voiced else None,
            "absolute_difference_cents_median": float(np.median(np.abs(cents))) if len(cents) else None,
            "absolute_difference_cents_p95": float(np.percentile(np.abs(cents), 95)) if len(cents) else None,
            "difference_over_600_cents_frames": int(np.sum(np.abs(cents) > 600)),
            "uncovered_tail_samples": int(len(x) - starts[-1] - n) if len(starts) else len(x),
            "scope": "自然音声の参照F0は未知。同じ独立測定器の入出力推定値の整合性のみ"}


def _guard(name, function):
    try:
        return function()
    except Exception as error:
        logging.exception("追加指標の測定に失敗しました: %s", name)
        return {"status": "failed", "error": f"{type(error).__name__}: {error}"}


def measure_extended(reference, output, sample_rate, *, include_pitch=True,
                     include_temporal=True, is_speech=True):
    """整列済み清潔参照と未加工再合成を測る。編集後の知覚品質には転用しない。"""
    x, y = np.asarray(reference, dtype=np.float64), np.asarray(output, dtype=np.float64)
    result = {"schema": SCHEMA, "status": "measured", "alignment": "none",
              "gain_normalization": "none", "sample_rate": int(sample_rate),
              "reference_samples": int(x.size), "output_samples": int(y.size),
              "intelligibility": None, "level": None, "full_scale": None, "quiet_regions": None,
              "pitch_consistency": None, "temporal": None}
    if isinstance(sample_rate, (bool, np.bool_)) or not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise ValueError("サンプルレートは正の整数が必要です")
    reason = None
    if x.ndim != 1 or y.ndim != 1:
        reason = "not_mono"
    elif len(x) != len(y):
        reason = "length_mismatch"
    elif not len(x):
        reason = "empty_waveform"
    elif not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        reason = "nonfinite_waveform"
    if reason:
        logging.error("追加指標の入力が測定条件を満たしません: %s", reason, stack_info=True)
        return {**result, "status": reason}
    result["intelligibility"] = {"estoi": _estoi(x, y, sample_rate, is_speech)}
    ref_level, out_level = _level(x), _level(y)
    result["level"] = {"reference": ref_level, "output": out_level,
                       "rms_difference_db": out_level["rms_dbfs"] - ref_level["rms_dbfs"]
                       if out_level["rms_dbfs"] is not None and ref_level["rms_dbfs"] is not None else None}
    result["full_scale"] = {"reference": _full_scale(x), "output": _full_scale(y)}
    result["quiet_regions"] = _guard("低エネルギー区間", lambda: _quiet_regions(x, y, sample_rate))
    result["pitch_consistency"] = (_guard("F0推定の整合性", lambda: _pitch_consistency(x, y, sample_rate))
                                   if include_pitch else {"status": "not_requested"})
    result["temporal"] = (_guard("時間包絡", lambda: measure_temporal(x, y, sample_rate))
                          if include_temporal else {"status": "not_requested"})
    return result
