"""#7–11の正式control評価。全予定条件を列挙し、未着・失敗・適用外を区別。"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import time
import traceback

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_control_eval_equivalence import verified_record
from all_metrics_control_eval_time import EVENT_RULE, evaluate_time, original_events
from all_metrics_controls import checked_audio, evaluate_control_pair
from all_metrics_resources import shared_stage
from vocoderbench.assessment.acoustics import spectral_slope
from vocoderbench.assessment.common import Inputs, NotApplicable, ok
from vocoderbench.assessment.controls import interference
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, sha256, write_json

CONDITIONS = ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6',
              'gain_interference', 'time_scale1p25', 'time_preservation', 'slope_preservation')
ATTRIBUTE_SCALES = {'pitch_cents': 100., 'level_db': 1., 'slope_db_per_octave': 1., 'duration_seconds': .1}
GAIN_EXPECTED = {'pitch_cents': 0., 'level_db': 1., 'slope_db_per_octave': 0., 'duration_seconds': 0.}
TERMINAL = {'measured', 'failed', 'upstream_failed', 'not_applicable', 'unsupported'}


def applicable(method, condition):
    if condition in ('time_preservation', 'slope_preservation'):
        return True
    if condition == 'time_scale1p25':
        return method in METHODS[:2]
    return method != 'facodec'


def native_conditions(method):
    names = ['unedited']
    if method != 'facodec':
        names += list(CONDITIONS[:4])
    if method in METHODS[:2]:
        names += ['time_scale1p25', 'slope_minus3', 'slope_plus3']
    return names


def contract():
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_controls.py',
        ROOT / 'scripts/all_metrics_control_eval_time.py', ROOT / 'scripts/all_metrics_control_eval_equivalence.py',
        ROOT / 'vocoderbench/assessment/controls.py', ROOT / 'vocoderbench/assessment/acoustics.py',
        ROOT / 'vocoderbench/assessment/common.py', ROOT / 'vocoderbench/metrics.py']
    return {'schema_version': 2, 'implementation_origin': 'new source implementation after old raw/source loss',
        'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'inputs_sha256': sha256(RUN / 'inputs.json'), 'methods': list(METHODS), 'conditions': list(CONDITIONS),
        'planned_cases': 120, 'planned_speakers': 40,
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in paths}, 'environment': environment(),
        'pitch': {'semitones': [-3., 3.], 'reference': 'same native unedited decoded',
            'estimator': 'existing independent YIN; natural absolute truth not available',
            'magphase_mapping': 'saved native epoch pairs only; no endpoint insertion, renormalization or extrapolation'},
        'gain': {'db': [-6., 6.], 'reference': 'same native unedited decoded', 'waveform_gain_postprocessing': False},
        'time': {'methods': list(METHODS[:2]), 'requested_scale': 1.25,
            'event_rule': EVENT_RULE, 'expected_time': '1.25 * detected unedited event time',
            'endpoint_renormalization': False, 'main_comparison': 'HNM/WORLD common successful original event IDs'},
        'preservation': {'methods': list(METHODS), 'reference': 'fixed original excerpt full length',
            'audio_scope': 'original and output at their actual sample rates, full length; no resample/crop/align',
            'slope': 'independent 40ms Hann,10ms hop regressions 300..5000 Hz; native grid discretization differs',
            'time': 'original-only events, identity requested map; length error saved independently'},
        'interference': {'gain_delta_db': 6., 'gain_control_scale': 1., 'attribute_scales': ATTRIBUTE_SCALES,
            'expected_response': GAIN_EXPECTED, 'pitch_off_diagonal_expected_response': 'unknown; not scored'},
        'missing_policy': 'null and explicit status; all-missing events/F0 do not erase independent denominators or duration',
        'threads': 2, 'seed': 20261014, 'repetitions': 1}


def source_names(condition):
    if condition == 'gain_interference':
        return ['gain_minus6', 'gain_plus6']
    if condition in ('time_preservation', 'slope_preservation'):
        return ['unedited']
    return ['unedited', condition]


def read_sources(spec, method, condition, row):
    records = {}
    for name in source_names(condition):
        path = RUN / 'native' / method / spec['id'] / f'{name}.json'
        if not path.exists():
            records[name] = {'status': 'pending_audio', 'source_record': str(path)}
        else:
            records[name] = read(path)
            if any(records[name].get(key) != value for key, value in
                   [('case', spec['id']), ('method', method), ('condition', name)]):
                raise ValueError('native元記録のcase/method/conditionが不一致です')
            row['input_records'].append({'path': str(path), 'sha256': sha256(path)})
            if records[name]['status'] == 'measured':
                checked_audio(records[name])
    states = [value['status'] for value in records.values()]
    if any(state.startswith('pending') for state in states):
        row.update(status='pending_audio', reason='予定native元記録の到着待ち', upstream_statuses=states)
    elif any(state != 'measured' for state in states):
        row.update(status='upstream_failed', reason='正式native生成が非成功', upstream_statuses=states)
    return records


def original(spec):
    if sha256(spec['path']) != spec['sha256']:
        raise ValueError('固定原音のfile SHA256が不一致です')
    wave = np.load(spec['path'], allow_pickle=False)
    if wave.ndim != 1 or wave.dtype.kind != 'f' or len(wave) != spec['samples'] or not np.isfinite(wave).all():
        raise ValueError('固定原音のPCM/標本数が不正です')
    return wave.astype(float), spec['sample_rate']


def events_for(spec, signature, row):
    x, rate = original(spec)
    path = RUN / 'controls/original-events' / f'{spec["id"]}.json'
    identity = {'case': spec['id'], 'source_sha256': spec['sha256'], 'sample_rate': rate,
                'contract_sha256': signature, 'selection': EVENT_RULE}
    if path.exists():
        value = read(path)
        if any(value.get(key) != expected for key, expected in identity.items()):
            raise ValueError('固定原音eventの生成条件が変わりました')
    else:
        value = {**identity, 'events': original_events(x, rate)}
        freeze(path, value)
    row['input_records'].append({'path': str(path), 'sha256': sha256(path)})
    return x, rate, value['events']


def measure(spec, method, condition, records, signature, row):
    if condition in CONDITIONS[:4]:
        return evaluate_control_pair(records['unedited'], records[condition])
    if condition == 'gain_interference':
        job = {'low_hz': 300., 'high_hz': 5000., 'attribute_scales': ATTRIBUTE_SCALES,
            'sweeps': [{'control': 'gain', 'control_unit': 'dB', 'delta': 6., 'control_scale': 1.,
                'minus': records['gain_minus6']['audio'], 'plus': records['gain_plus6']['audio'],
                'expected_response': GAIN_EXPECTED}]}
        measurement = interference(job, Inputs(ROOT))
        for cell in measurement['matrix']:
            cell['absolute_normalized_error'] = abs(cell['normalized_error']) if cell['normalized_error'] is not None else None
        measurement['pitch_off_diagonal_expected_response'] = 'unknown; not scored'
        return {'metric': 'native_gain_interference', 'measurement': measurement}
    baseline, rate = checked_audio(records['unedited'])
    if condition == 'slope_preservation':
        x, original_rate = original(spec)
        a, b = spectral_slope(x, original_rate, 300., 5000.), spectral_slope(baseline, rate, 300., 5000.)
        return {'metric': 'native_full_length_slope_preservation', 'measurement': ok(abs(b - a), 'dB/oct',
            reference_slope=a, output_slope=b, signed_error=b - a, source_sample_rate=original_rate,
            output_sample_rate=rate, source_samples=len(x), output_samples=len(baseline),
            scope='各実SR・全長の音響傾斜保存診断。共通prefix品質群とは別。')}
    x, original_rate, events = events_for(spec, signature, row)
    preservation = condition == 'time_preservation'
    output, output_rate = (baseline, rate) if preservation else checked_audio(records[condition])
    measurement = evaluate_time(events, x, original_rate, baseline, rate, output, output_rate,
                                scale=1. if preservation else 1.25, preservation=preservation)
    return {'metric': 'native_local_time_preservation' if preservation else 'native_local_time_tracking',
            'measurement': measurement}


def evaluate(spec, method, condition, signature, retry_failed=False):
    path = RUN / 'controls/measurements' / f'{spec["id"]}__{method}__{condition}.json'
    previous = read(path) if path.exists() else None
    if previous:
        if previous['contract_sha256'] != signature:
            raise ValueError('control評価の凍結契約が変わりました')
        if sha256(spec['path']) != spec['sha256']:
            raise ValueError('control再読時に固定原音fileのhashが変わりました')
        if previous['status'] in ('measured', 'not_applicable', 'unsupported') or (
                previous['status'] in TERMINAL and not retry_failed):
            for source in previous.get('input_records', []):
                verified_record(source['path'], source['sha256'], RUN / 'controls/storage-equivalence')
            return previous
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', previous)
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'condition': condition,
           'contract_sha256': signature, 'started_at_utc': now(), 'status': 'failed', 'value': None,
           'input_records': [], 'original_input': spec, 'terminal': False}
    start, cpu = time.perf_counter(), time.process_time()
    try:
        if not applicable(method, condition):
            row.update(status='unsupported', reason='意味を固定した真のnative表現操作がありません')
        else:
            records = read_sources(spec, method, condition, row)
            if row['status'] not in ('pending_audio', 'upstream_failed'):
                row.update(measure(spec, method, condition, records, signature, row), status='measured')
    except NotApplicable as error:
        logging.warning('control適用外: %s %s %s: %s', spec['id'], method, condition, error)
        row.update(status='not_applicable', reason=str(error))
    except Exception:
        logging.exception('control正式評価失敗: %s %s %s', spec['id'], method, condition)
        row.update(status='failed', error=traceback.format_exc())
    row.update(terminal=row['status'] in TERMINAL, finished_at_utc=now(),
               wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu)
    write_json(path, row)
    return row


@shared_stage('control-evaluation')
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True, type=int, choices=range(12))
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    path = RUN / 'controls/contract.json'
    freeze(path, contract())
    rows = []
    for spec in read(RUN / 'inputs.json')[args.batch * 10:(args.batch + 1) * 10]:
        for method in METHODS:
            for condition in CONDITIONS:
                rows.append(evaluate(spec, method, condition, sha256(path), args.retry_failed))
        write_json(RUN / f'controls/batch-{args.batch:02d}.json', {'updated_at_utc': now(), 'rows': rows})
    return int(any(row['status'] in ('failed', 'upstream_failed') or not row['terminal'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-control-eval'))
