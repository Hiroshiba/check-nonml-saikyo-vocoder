"""低速包絡・既知イベントの研究測定。合否判定や知覚品質の予測は行わない。"""
from __future__ import annotations

import numpy as np
from scipy import signal

SCHEMA = "temporal-diagnostics-v2"
WINDOWS_MS = (10.0, 40.0)
HOP_MS = 5.0


def _array(value, name):
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 1 or not len(result) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name}は空でない有限のモノラル配列が必要です")
    return result


def _windows(x, sr, window_ms):
    size = max(1, round(sr * window_ms / 1000))
    hop = max(1, round(sr * HOP_MS / 1000))
    starts = np.arange(0, max(0, len(x) - size + 1), hop, dtype=int)
    cumulative = np.r_[0.0, np.cumsum(x * x)]
    power = np.maximum(0, (cumulative[starts + size] - cumulative[starts]) / size)
    centers = (starts + (size - 1) / 2) / sr
    return power, centers, starts, size, hop


def _db_ratio(numerator, denominator):
    if numerator <= 0 or denominator <= 0:
        return None
    return float(10 * np.log10(numerator / denominator))


def _correlation(a, b):
    if len(a) < 2:
        return None
    a, b = a - np.mean(a), b - np.mean(b)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator > 1e-20 else None


def _envelope_metrics(reference, output, floor):
    ref_rms, out_rms = np.sqrt(reference), np.sqrt(output)
    denominator = float(np.mean(reference)) if len(reference) else 0.0
    return {
        "frame_count": len(reference),
        "rms_floor": float(floor),
        "log_rms_mae_db": float(np.mean(np.abs(
            20 * np.log10(np.maximum(ref_rms, floor))
            - 20 * np.log10(np.maximum(out_rms, floor))))) if len(reference) else None,
        "rms_envelope_nrmse": float(np.sqrt(np.mean((out_rms - ref_rms) ** 2) / denominator))
        if denominator else None,
        "envelope_correlation": _correlation(ref_rms, out_rms),
        "rms_gain_error_db": _db_ratio(float(np.mean(output)), denominator)
        if len(output) else None,
        "reference_mean_power": denominator if len(reference) else None,
        "output_mean_power": float(np.mean(output)) if len(output) else None,
    }


def _modulation(power, centers, frequency_hz):
    columns = [np.ones(len(centers))]
    for multiple in (1, 2):
        angle = 2 * np.pi * frequency_hz * multiple * centers
        columns.extend((np.sin(angle), np.cos(angle)))
    design = np.column_stack(columns)
    if len(centers) < 5 or np.linalg.matrix_rank(design) < 5:
        return {"status": "insufficient_frames", "frame_count": len(centers)}
    coefficients, _, _, _ = np.linalg.lstsq(design, power, rcond=None)
    dc = float(coefficients[0])
    harmonics = []
    for i, multiple in enumerate((1, 2)):
        sine, cosine = coefficients[1 + 2 * i:3 + 2 * i]
        amplitude = float(np.hypot(sine, cosine))
        harmonics.append({
            "frequency_hz": float(frequency_hz * multiple),
            "relative_amplitude": amplitude / dc if dc > 0 else None,
            "phase_radians": float(np.arctan2(cosine, sine)) if amplitude > 1e-20 else None,
        })
    residual = power - design @ coefficients
    return {"status": "measured", "dc_power": dc, "frame_count": len(centers),
            "power_fit_nrmse": float(np.sqrt(np.mean(residual ** 2)) / dc) if dc > 0 else None,
            "harmonics": harmonics}


def _modulation_difference(reference, output):
    if reference.get("status") != "measured" or output.get("status") != "measured":
        return {"status": "unavailable"}
    rows = []
    for left, right in zip(reference["harmonics"], output["harmonics"]):
        a, b = left["relative_amplitude"], right["relative_amplitude"]
        phase_a, phase_b = left["phase_radians"], right["phase_radians"]
        rows.append({
            "frequency_hz": left["frequency_hz"],
            "relative_amplitude_error": b - a if a is not None and b is not None else None,
            "phase_error_radians": float(np.angle(np.exp(1j * (phase_b - phase_a))))
            if phase_a is not None and phase_b is not None else None,
        })
    return {"status": "measured", "harmonics": rows}


def _modulation_bands(reference_power, output_power, envelope_rate):
    """RMS包絡の変動電力。周期内構造や変調の位相一致は評価しない。"""
    frames = len(reference_power)
    if frames < envelope_rate:
        return {"status": "less_than_one_second_of_envelope", "frames": frames,
                "envelope_rate_hz": float(envelope_rate), "bands": []}
    frequencies, reference = signal.periodogram(np.sqrt(reference_power), fs=envelope_rate,
                                               window="hann", detrend="constant", scaling="density")
    _, output = signal.periodogram(np.sqrt(output_power), fs=envelope_rate,
                                   window="hann", detrend="constant", scaling="density")
    step = float(frequencies[1] - frequencies[0])
    floor = max(1e-20, float(np.sum(reference) * step) * 1e-6)
    bands = []
    for low, high in ((2.0, 8.0), (8.0, 20.0), (20.0, 50.0)):
        selected = (frequencies >= low) & (frequencies < high)
        a, b = float(np.sum(reference[selected]) * step), float(np.sum(output[selected]) * step)
        bands.append({"low_hz": low, "high_hz": high, "reference_power": a, "output_power": b,
                      "reference_active": a > floor,
                      "delta_db": float(10 * np.log10(max(b, floor) / max(a, floor)))})
    active = [abs(row["delta_db"]) for row in bands if row["reference_active"]]
    return {"status": "measured", "envelope_rate_hz": float(envelope_rate), "frames": frames,
            "frequency_resolution_hz": step, "power_floor": floor, "window": "hann",
            "detrend": "constant", "gain_normalization": "none", "bands": bands,
            "active_band_count": len(active), "active_band_mae_db": float(np.mean(active)) if active else None}


def _event_energy(x, sr, event_time_s, margin_ms):
    energy = x * x
    total = float(np.sum(energy))
    row = {"total_energy": total, "expected_time_s": float(event_time_s),
           "margin_ms": float(margin_ms), "fraction_denominator": "この信号自身の全エネルギー"}
    if total <= 0:
        return {**row, "status": "no_output_energy", "width_90_ms": None,
                "median_error_ms": None, "pre_margin_fraction": None,
                "post_margin_fraction": None, "quantile_times_s": None}
    cumulative = np.cumsum(energy) / total
    times = [float(np.searchsorted(cumulative, q, side="left") / sr) for q in (0.05, 0.5, 0.95)]
    sample_times = np.arange(len(x)) / sr
    return {**row, "status": "measured", "quantile_times_s": times,
            "width_90_ms": 1000 * (times[2] - times[0]),
            "median_error_ms": 1000 * (times[1] - event_time_s),
            "pre_margin_fraction": float(energy[sample_times < event_time_s - margin_ms / 1000].sum() / total),
            "post_margin_fraction": float(energy[sample_times > event_time_s + margin_ms / 1000].sum() / total)}


def _silence_energy(x, sr, intervals):
    total = float(np.sum(x * x))
    times = np.arange(len(x)) / sr
    rows = []
    for start, end in intervals:
        if not np.isfinite([start, end]).all() or not 0 <= start < end <= len(x) / sr:
            raise ValueError("既知無音区間は入力長内の[start, end)で指定してください")
        selected = (times >= start) & (times < end)
        energy = float(np.sum(x[selected] ** 2))
        rows.append({"start_s": float(start), "end_s": float(end), "samples": int(selected.sum()),
                     "energy": energy, "energy_fraction": energy / total if total > 0 else None,
                     "fraction_denominator": "この信号自身の全エネルギー"})
    return rows


def measure_temporal(reference, output, sample_rate, *, modulation_hz=None,
                     known_amplitude_envelope=None, event_time_s=None,
                     event_margin_ms=5.0, silent_intervals_s=(), include_trajectories=False):
    """同じ時刻・長さの2信号を測定する。整列・音量補正は行わない。

    known_amplitude_envelopeは雑音へ掛ける既知の非負振幅配列。絶対電力を
    仮定せず、同じ窓で二乗平均した理論包絡の相対変調だけを比較する。
    時間編集時は呼出し側で正解配列・変調周波数・イベント時刻を変換する。
    低速包絡と単一イベント用で、声帯周期内の変動や自然性は評価しない。
    """
    x, y = _array(reference, "参照"), _array(output, "出力")
    if len(x) != len(y):
        raise ValueError("時間診断の参照と出力は同じ長さが必要です")
    if isinstance(sample_rate, (bool, np.bool_)) or not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise ValueError("サンプルレートは正の整数が必要です")
    if modulation_hz is not None and (not np.isfinite(modulation_hz) or not 0 < modulation_hz < 1 / (4 * HOP_MS / 1000)):
        raise ValueError("変調周波数とその2倍成分は包絡のNyquist周波数未満で指定してください")
    truth = None if known_amplitude_envelope is None else _array(known_amplitude_envelope, "既知振幅包絡")
    if truth is not None and (truth.shape != x.shape or np.any(truth < 0)):
        raise ValueError("既知振幅包絡は波形と同じ長さの非負配列が必要です")
    if event_time_s is not None and (not np.isfinite(event_time_s) or not 0 <= event_time_s < len(x) / sample_rate):
        raise ValueError("既知イベント時刻は入力長内に指定してください")
    if not np.isfinite(event_margin_ms) or event_margin_ms < 0:
        raise ValueError("イベントの許容窓幅は非負の有限値が必要です")
    result = {"schema": SCHEMA, "status": "measured", "sample_rate": int(sample_rate),
              "samples": len(x), "alignment": "none", "normalization": "none",
              "bands": [], "event": None, "silent_intervals": None,
              "limitations": ["有限長雑音の包絡差は独立seedでもゼロにならない",
                              "帯域フィルタの端点過渡は測定に含むがイベント測定には使わない",
                              "RMS包絡は有声・無声や知覚品質の正解測定ではない"]}
    bands = [("全帯域", None), ("300–1000 Hz", (300.0, 1000.0)),
             ("1000–3000 Hz", (1000.0, 3000.0)), ("3000–6000 Hz", (3000.0, 6000.0))]
    for name, edges in bands:
        if edges is not None and edges[1] >= sample_rate / 2:
            result["bands"].append({"name": name, "status": "outside_nyquist", "windows": []})
            continue
        if edges is None:
            a, b = x, y
            filter_spec = {"kind": "none"}
        else:
            sos = signal.butter(4, edges, fs=sample_rate, btype="bandpass", output="sos")
            padlen = min(len(x) - 1, 3 * (2 * len(sos) + 1))
            a = signal.sosfiltfilt(sos, x, padtype="even", padlen=padlen)
            b = signal.sosfiltfilt(sos, y, padtype="even", padlen=padlen)
            filter_spec = {"kind": "butterworth-forward-backward", "prototype_order": 4,
                           "edges_hz": list(edges), "pad_type": "even", "pad_samples": padlen}
        band = {"name": name, "status": "measured", "filter": filter_spec, "windows": []}
        for window_ms in WINDOWS_MS:
            pa, times, starts, size, hop = _windows(a, sample_rate, window_ms)
            pb, _, _, _, _ = _windows(b, sample_rate, window_ms)
            floor = max(1e-7, float(np.sqrt(pa.max())) * 1e-3) if len(pa) else 1e-7
            row = {"window_ms": window_ms, "window_samples": size, "hop_samples": hop,
                   "hop_ms": HOP_MS, "status": "measured" if len(pa) else "no_complete_frames",
                   "covered_start_sample": 0 if len(pa) else None,
                   "covered_end_sample": int(starts[-1] + size) if len(pa) else None,
                   "uncovered_tail_samples": int(len(x) - starts[-1] - size) if len(pa) else len(x),
                   "metrics": _envelope_metrics(pa, pb, floor),
                   "modulation_bands": _modulation_bands(pa, pb, sample_rate / hop)}
            if include_trajectories:
                row["trajectory"] = {"center_times_s": times.tolist(), "reference_rms": np.sqrt(pa).tolist(),
                                     "output_rms": np.sqrt(pb).tolist()}
            if modulation_hz is not None:
                ref_mod = _modulation(pa, times, modulation_hz)
                out_mod = _modulation(pb, times, modulation_hz)
                row["modulation"] = {"reference": ref_mod, "output": out_mod,
                                     "difference_from_reference": _modulation_difference(ref_mod, out_mod)}
                if truth is not None:
                    pt, _, _, _, _ = _windows(truth, sample_rate, window_ms)
                    ideal = _modulation(pt, times, modulation_hz)
                    row["modulation"]["known_amplitude_model"] = ideal
                    row["modulation"]["difference_from_amplitude_model"] = _modulation_difference(ideal, out_mod)
                    row["modulation"]["amplitude_model_scope"] = "帯域フィルタ前の既知振幅二乗。帯域選択後の厳密な期待電力ではない"
            band["windows"].append(row)
        result["bands"].append(band)
    if event_time_s is not None:
        ref = _event_energy(x, sample_rate, event_time_s, event_margin_ms)
        out = _event_energy(y, sample_rate, event_time_s, event_margin_ms)
        result["event"] = {"filter": "none", "reference": ref, "output": out,
                           "energy_ratio": out["total_energy"] / ref["total_energy"] if ref["total_energy"] else None,
                           "scope": "既知の単一イベント。複数イベントの境界時刻推定ではない"}
    if silent_intervals_s:
        result["silent_intervals"] = {"filter": "none", "interval_convention": "[start, end)",
                                      "reference": _silence_energy(x, sample_rate, silent_intervals_s),
                                      "output": _silence_energy(y, sample_rate, silent_intervals_s)}
    return result


def aggregate_seeds(records):
    """{seed, measurement}の各行を保持して集約。発話母集団の信頼区間ではない。"""
    scalar_keys = {"log_rms_mae_db", "rms_envelope_nrmse", "envelope_correlation",
                   "rms_gain_error_db", "relative_amplitude", "relative_amplitude_error",
                   "phase_radians", "phase_error_radians", "power_fit_nrmse", "energy_ratio",
                   "width_90_ms", "median_error_ms", "pre_margin_fraction", "post_margin_fraction",
                   "energy_fraction"}
    flattened = []

    def visit(value, path, result):
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else key
                if key in scalar_keys:
                    result[item_path] = item
                elif isinstance(item, (dict, list)):
                    visit(item, item_path, result)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", result)

    for record in records:
        values = {}
        visit(record["measurement"], "", values)
        flattened.append(values)
    statistics = {}
    for path in sorted({path for values in flattened for path in values}):
        values = [row.get(path) for row in flattened]
        valid = np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=float)
        row = {"values": values, "valid_count": len(valid), "total_count": len(records)}
        if path.endswith(("phase_radians", "phase_error_radians")):
            vector = np.mean(np.exp(1j * valid)) if len(valid) else None
            row.update(circular_mean_radians=float(np.angle(vector)) if vector is not None else None,
                       resultant_length=float(abs(vector)) if vector is not None else None)
        else:
            row.update(mean=float(np.mean(valid)) if len(valid) else None,
                       standard_deviation=float(np.std(valid, ddof=1)) if len(valid) > 1 else None,
                       minimum=float(np.min(valid)) if len(valid) else None,
                       maximum=float(np.max(valid)) if len(valid) else None)
        statistics[path] = row
    return {"schema": SCHEMA, "seed_count": len(records), "seeds": [row["seed"] for row in records],
            "interpretation": "固定入力に対する乱数実現のばらつき。独立発話や話者の信頼区間ではない",
            "records": records, "statistics": statistics}
