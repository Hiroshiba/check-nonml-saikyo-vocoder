"""#16–18の独立集約。解放済みpayloadの永久実IO証拠と保存waveを評価する。"""
from __future__ import annotations

import argparse
from collections import Counter
import logging
from pathlib import Path
import time
import traceback

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_controls import evaluate_control_pair
from all_metrics_latent_evaluation_common import (
    POINTS, TOLERANCES, artifact_evidence, attributes_cached, auditory_pair, exact_identity,
    fixed_quality_configuration, quality, read_point, source_fingerprint,
)
from vocoderbench.assessment.common import NotApplicable, error_summary
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, sha256, write_json


def contract():
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_latent_evaluation_common.py',
        ROOT / 'scripts/all_metrics_latent_provenance.py', ROOT / 'scripts/all_metrics_controls.py',
        ROOT / 'vocoderbench/assessment/acoustics.py', ROOT / 'vocoderbench/assessment/controls.py',
        ROOT / 'vocoderbench/assessment/common.py', ROOT / 'vocoderbench/assessment/curves.py',
        ROOT / 'vocoderbench/metrics.py']
    return {'schema_version': 1, 'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths}, 'environment': environment(),
        'protocol': 'independent_saved_wave_and_permanent_actual_IO_evidence_v1',
        'not_the_existing_curves_CLI': True,
        'representation_points': ['native', 'float16', 'float32'], 'interpolation_alpha': [0., .5, 1.],
        'auditory': {'reference': 'same_method_native_unedited', 'rate': 16000,
            'resampling': 'scipy.resample_poly, Kaiser5, constant; no crop/pad/align/gain/silence processing',
            'different_lengths': 'not_applicable for auditory; full-length attributes/duration retained',
            'definition': 'existing assessment.acoustics.auditory: 32 ERB triangles,40ms Hann,5ms hop'},
        'attributes': {'scope': 'native full length', 'slope_band_hz': [300., 5000.],
            'tolerances': TOLERANCES, 'perceptual_JND': False, 'absolute_F0_truth': False},
        'interpolation': {'meaning': 'same utterance 0/-6dB input reencode endpoints',
            'diagnostics': 'finite-point slopes/reversals/endpoint-linear deviations, not a proof of continuity or required perceptual linearity'},
        'controls': 'each quantized point unedited waveform is its own pitch/gain reference; native-rate shared control API',
        'magphase_time_map': 'Only stored corresponding native epochs; no waveform endpoint insertion, renormalization or extrapolation. Recovery-run synthesis metadata uses the same definition.',
        'quality': {'mos': 'existing fixed UTMOSv2 full-length evidence',
            'ecapa': 'same fixed original excerpt reference, independent full-length 16k protocol',
            'scope': 'native + two quantized unedited + three interpolation points; no quantized control MOS/ECAPA'},
        'analytic_identity': 'only exact canonical decoder inputs AND PCM alias; no self-comparison computation; undefined attributes stay null; distinct from measured',
        'bytes': 'actual measured NPZ bytes/SHA from immutable IO proof, including structure/header; shared assets separately; denominator original input seconds',
        'pending_quality': 'saved as pending and retried; never replace missing values by zero',
        'overall_score_or_aggregate_rank': False}


def control_values(spec, method, baseline, signature):
    results = []
    if method == 'facodec':
        return [{'status': 'unsupported', 'value': None, 'reason': '意味を固定したnative pitch/gain操作がありません'}]
    for name in ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6'):
        output = read_point(spec, method, baseline['condition'] + '__' + name)
        result = {'condition': output['condition'], 'control_reference': baseline['condition'],
                  'status': output['status'], 'value': None}
        if output['status'] == 'measured':
            key = source_fingerprint([signature, baseline['audio']['sample_rate'], baseline['audio']['float64_sha256'],
                output['audio']['float64_sha256'], name, output.get('parameter_frame_times')])
            cache = RUN / 'latent-evaluation/controls-cache' / f'{key}.json'
            try:
                value = read(cache) if cache.exists() else evaluate_control_pair(baseline, output)
                if not cache.exists():
                    write_json(cache, value)
                result.update(value, status='measured' if value['measurement']['status'] == 'ok' else value['measurement']['status'],
                              value=value['measurement']['value'])
            except NotApplicable as error:
                result.update(status='not_applicable', reason=str(error))
        results.append(result)
    return results


def interpolation_result(points, signature):
    selected = [points[name] for name in POINTS[3:]]
    available = [{'alpha': alpha, 'status': p['status'],
        'audio': p.get('audio'), 'source_record': p.get('record_evidence'),
        'quality': p.get('quality'),
        'attributes': attributes_cached(p, signature) if p['status'] == 'measured' else None}
        for alpha, p in zip((0., .5, 1.), selected)]
    if any(p['status'] == 'not_applicable' for p in selected):
        return {'status': 'not_applicable', 'value': None,
                'reason': '端点構造/UV/pitchmark対応がないため中間表現は適用外。後付け整列しない。',
                'point_statuses': [p['status'] for p in selected], 'available_endpoint_evidence': available}
    if any(p['status'] != 'measured' for p in selected):
        return {'status': 'pending_audio' if any(p['status'] == 'pending_audio' for p in selected) else 'upstream_failed',
                'value': None, 'point_statuses': [p['status'] for p in selected], 'available_endpoint_evidence': available}
    rows = [{'alpha': alpha, 'attributes': attributes_cached(p, signature), 'quality': p['quality'],
             'audio': p['audio'], 'source_record': p['record_evidence'], 'provenance': p.get('provenance')}
            for alpha, p in zip((0., .5, 1.), selected)]
    fixed_quality_configuration(rows)
    diagnostics = {}
    for key, tolerance in TOLERANCES.items():
        values = [row['attributes'][key] for row in rows]
        if any(value is None for value in values):
            diagnostics[key] = {'status': 'not_applicable', 'value': None, 'values': values}
            continue
        values = np.asarray(values)
        slopes = np.diff(values) / .5
        linear = values[0] + np.array([0., .5, 1.]) * (values[-1] - values[0])
        sign = np.sign(values[-1] - values[0]) if abs(values[-1] - values[0]) > tolerance else 0
        diagnostics[key] = {'status': 'measured', 'values': values.tolist(),
            'max_abs_slope': float(abs(slopes).max()), 'max_abs_slope_change': float(abs(np.diff(slopes)).max()),
            'reversal_steps': int((sign * np.diff(values) < -tolerance).sum()) if sign else None,
            'monotonicity_tolerance': tolerance, 'endpoint_linear_deviation': error_summary(values - linear),
            'midpoint_absolute_linear_deviation': float(abs(values[1] - linear[1])),
            'interpretation': '有限3点の記述診断。線形応答の要求や知覚品質尺度ではない。'}
    dips = {}
    for name in ('predicted_mos', 'speaker_similarity'):
        values = [row['quality'][name]['value'] for row in rows]
        states = [row['quality'][name]['status'] for row in rows]
        dips[name] = {'status': 'measured' if all(v is not None for v in values) else
            'pending_quality' if any(state.startswith('pending') for state in states) else 'upstream_quality_failed',
            'quality_point_statuses': states,
            'value': max(0., min(values[0], values[-1]) - values[1]) if all(v is not None for v in values) else None,
            'direction': 'lower', 'definition': 'middle point deficit below both endpoint quality values'}
    return {'status': 'pending_quality' if any(d['status'] == 'pending_quality' for d in dips.values())
            else 'partial' if any(d['status'] != 'measured' for d in [*diagnostics.values(), *dips.values()]) else 'measured',
            'value': None, 'points': rows, 'attributes': diagnostics, 'quality_dips_below_both_endpoints': dips}


def representation_results(spec, method, points, signature):
    baseline = points['unedited']
    if baseline['status'] != 'measured':
        state = baseline['status']
        value = {'status': 'pending_audio' if state.startswith('pending') else
                 state if state in ('not_applicable', 'unsupported') else 'upstream_failed',
                 'value': None, 'native_reference_status': state,
                 'reason': baseline.get('error', baseline.get('reason')),
                 'source_record': baseline.get('record_evidence')}
        return value, value
    base_attributes = attributes_cached(baseline, signature)
    rate_points = [{'configuration': 'native', 'status': 'measured', 'quality': baseline['quality'],
                    'artifact': artifact_evidence(spec, method, baseline), 'audio': baseline['audio'],
                    'auditory': {'status': 'reference_not_scored', 'value': None}}]
    perturbations = []
    for condition in POINTS[1:3]:
        point = points[condition]
        row = {'configuration': condition, 'status': point['status'], 'value': None}
        if point['status'] == 'measured':
            values = attributes_cached(point, signature)
            identical = exact_identity(baseline, point)
            deltas = {}
            for key, value in values.items():
                base = base_attributes[key]
                deltas[key] = {'status': ('analytic_identity' if identical else 'measured')
                    if base is not None and value is not None else 'not_applicable',
                    'signed_delta': value - base if base is not None and value is not None else None,
                    'absolute_delta': abs(value - base) if base is not None and value is not None else None,
                    'native_reference': base, 'output': value}
            key = source_fingerprint([signature, baseline['audio']['float64_sha256'],
                point['audio']['float64_sha256'], point['audio']['sample_rate'], point.get('provenance')])
            cache = RUN / 'latent-evaluation/auditory-cache' / f'{key}.json'
            if cache.exists():
                heard = read(cache)
            else:
                try:
                    heard = auditory_pair(baseline, point)
                except NotApplicable as error:
                    heard = {'status': 'not_applicable', 'value': None, 'reason': str(error)}
                write_json(cache, heard)
            row.update(audio=point['audio'], source_record=point['record_evidence'],
                artifact=artifact_evidence(spec, method, point), attributes=values, attribute_deltas=deltas,
                auditory=heard, quality=point['quality'], controls=control_values(spec, method, point, signature),
                exact_identity=identical,
                quality_delta_from_native={name: {'value': point['quality'][name]['value'] - baseline['quality'][name]['value']
                    if point['quality'][name]['value'] is not None and baseline['quality'][name]['value'] is not None else None,
                    'status': ('analytic_identity' if identical else 'measured') if point['quality'][name]['value'] is not None and baseline['quality'][name]['value'] is not None else 'pending_quality' if any(p['quality'][name]['status'].startswith('pending') for p in (point, baseline)) else 'upstream_quality_failed'}
                    for name in ('predicted_mos', 'speaker_similarity')})
            rate_points.append(row)
        else:
            row['reason'] = point.get('error', point.get('reason', '正式復号が未完了'))
            row['failure_stage'] = point.get('failure_stage')
            row['attempted_artifact_not_a_successful_rate_point'] = point.get('feature_artifact')
        perturbations.append(row)
    fixed_quality_configuration(rate_points)
    pending = any(p['status'] == 'pending_audio' for p in perturbations)
    quality_pending = any(q['status'].startswith('pending') for p in rate_points for q in p.get('quality', {}).values())
    quality_incomplete = any(q['value'] is None for p in rate_points for q in p.get('quality', {}).values())
    control_states = Counter(c['status'] for p in perturbations for c in p.get('controls', []))
    pending_controls = any(key.startswith('pending') and count for key, count in control_states.items())
    incomplete_controls = any(key not in ('measured', 'unsupported') and count for key, count in control_states.items())
    incomplete = any(p['status'] != 'measured' for p in perturbations)
    status = ('pending_audio' if pending or pending_controls else 'pending_quality' if quality_pending
              else 'partial' if incomplete or incomplete_controls or quality_incomplete else 'measured')
    robustness = {'status': status, 'value': None, 'native_reference': baseline['audio'],
        'native_attributes': base_attributes, 'points': perturbations, 'control_status_counts': dict(control_states),
        'scope': '同方式の量子化保存精度摂動。入力gain再解析とは別。'}
    rate = {'status': status if len(rate_points) >= 2 else 'insufficient_valid_points', 'value': None,
        'points': sorted(rate_points, key=lambda p: p['artifact']['payload_bits_per_source_second']),
        'excluded_points': [p for p in perturbations if p['status'] != 'measured'],
        'self_contained_total_bitrate': False, 'overall_winner': None, 'control_status_counts': dict(control_states)}
    return robustness, rate


def evaluate(spec, method, signature):
    path = RUN / 'latent-evaluation/measurements' / f'{spec["id"]}__{method}.json'
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
           'contract_sha256': signature, 'started_at_utc': now()}
    try:
        points = {name: read_point(spec, method, name) for name in POINTS}
        for point in points.values():
            if point['status'] == 'measured':
                point['quality'] = quality(spec, method, point)
        controls = {}
        if method != 'facodec':
            for precision in POINTS[1:3]:
                for name in ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6'):
                    control = read_point(spec, method, precision + '__' + name)
                    controls[control['condition']] = {'status': control['status'],
                        'source': control.get('record_evidence'),
                        'audio_sha256': control.get('audio', {}).get('file_sha256')}
        inputs = source_fingerprint({'points': {name: {'status': p['status'],
            'source': p.get('record_evidence'), 'quality': p.get('quality')} for name, p in points.items()},
            'control_inputs': controls})
        if path.exists():
            old = read(path)
            if old['contract_sha256'] != signature:
                raise ValueError('専用評価の科学契約が不一致です')
            if old.get('input_fingerprint') == inputs and old.get('status') != 'failed':
                return old
            write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', old)
        row['input_fingerprint'] = inputs
        robustness, rate = representation_results(spec, method, points, signature)
        if points['unedited']['status'] != 'measured' and not points['unedited']['status'].startswith('pending'):
            interpolation = {**robustness,
                'point_statuses': [points[name]['status'] for name in POINTS[3:]],
                'dependency_scope': 'native端点失敗時に未着の依存補間点を永続pendingへしない。native成功後は再評価。'}
        else:
            interpolation = interpolation_result(points, signature)
        row.update(metrics={'16_interpolation': interpolation, '17_representation_robustness': robustness,
                            '18_information_rate': rate},
            status='pending' if any(r['status'].startswith('pending') for r in (interpolation, robustness, rate))
                else 'partial' if any(r['status'] not in ('measured', 'not_applicable') for r in (interpolation, robustness, rate)) else 'measured')
    except Exception:
        logging.exception('専用表現指標の正式計測失敗: %s %s', spec['id'], method)
        row.update(status='failed', error=traceback.format_exc())
    row['finished_at_utc'] = now()
    write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--methods', nargs='+', choices=METHODS, default=list(METHODS))
    args = parser.parse_args()
    target = RUN / 'latent-evaluation/contract.json'
    freeze(target, contract())
    signature = sha256(target)
    rows = []
    for spec in read(RUN / f'input-batches/{args.batch:02d}.json'):
        for method in args.methods:
            rows.append(evaluate(spec, method, signature))
        write_json(RUN / 'latent-evaluation' / f'batch-{args.batch:02d}-{"-".join(args.methods)}.json',
                   {'updated_at_utc': now(), 'rows': rows})
    return int(any(row['status'] == 'failed' for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-evaluation'))
