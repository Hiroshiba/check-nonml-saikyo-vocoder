"""WORLDのnativeスペクトル表現を±3dB/oct操作する独立正式stage。"""
from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import logging
from pathlib import Path
import random
import time
import traceback

import numpy as np

from all_metrics_common import ROOT, RUN, freeze, now, read, save_audio
from all_metrics_control_eval_equivalence import verified_record
from all_metrics_controls import checked_audio
from all_metrics_resources import shared_stage
from vocoderbench import world
from vocoderbench.assessment.acoustics import timbre
from vocoderbench.assessment.common import Inputs, NotApplicable
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, sha256, write_json

SOURCE_FILES = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', ROOT / 'vocoderbench/methods.py', ROOT / 'vocoderbench/world.py',
    ROOT / 'vocoderbench/assessment/acoustics.py', ROOT / 'vocoderbench/assessment/common.py',
    ROOT / 'scripts/all_metrics_controls.py', ROOT / 'scripts/all_metrics_control_eval_equivalence.py']


def arrays(params):
    return {key: {'shape': list(value.shape), 'dtype': value.dtype.str,
                  'c_order_sha256': hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()}
            for key, value in vars(params).items() if isinstance(value, np.ndarray)}


def edit_native(params, method, delta):
    if method != 'world_harvest':
        raise ValueError('旧HNM傾斜研究の再計算はbbab81fをcheckoutしてください')
    edited = copy.deepcopy(params)
    frequencies = np.linspace(
        0, params.sample_rate / 2, params.spectral_envelope.shape[1])
    amplitude = 10 ** (delta * np.log2(np.clip(frequencies, 300., 5000.) / 1000.) / 20)
    edited.spectral_envelope *= amplitude[None, :] ** 2
    world.validate(edited)
    permitted = {'spectral_envelope'}
    before, after = arrays(params), arrays(edited)
    if set(before) != set(after) or any(before[key] != after[key] for key in before if key not in permitted):
        raise ValueError('傾斜の操作対象外arrayが変化しました')
    if any(value != vars(edited)[key] for key, value in vars(params).items() if key not in before):
        raise ValueError('傾斜操作でnative metadataが変化しました')
    return edited


def evaluate_point(spec, method, condition, delta, signature, retry_failed):
    if method == 'hnm':
        raise ValueError('旧HNM傾斜研究の再計算はbbab81fをcheckoutしてください')
    folder = RUN / 'native' / method / spec['id']
    path = folder / f'{condition}.json'
    result_path = RUN / 'controls-slope/measurements' / f'{spec["id"]}__{method}__{condition}.json'
    if result_path.exists():
        previous = read(result_path)
        if previous['contract_sha256'] != signature:
            raise ValueError('slope正式評価の再開契約が変わりました')
        if previous['status'] in ('measured', 'not_applicable') or (not retry_failed and not previous['status'].startswith('pending')):
            for key in ('native_record', 'baseline_record'):
                if key in previous:
                    verified_record(previous[key], previous[key + '_sha256'], RUN / 'controls-slope/storage-equivalence')
            return previous
        write_json(result_path.parent.parent / 'history' / f'{result_path.stem}-{time.time_ns()}.json', previous)
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'condition': condition,
           'status': 'failed', 'value': None, 'contract_sha256': signature, 'started_at_utc': now(),
           'controls': {'control': 'native_spectral_slope', 'amount': delta, 'unit': 'dB/oct',
                        'description': '明示したnativeスペクトルfield操作。既存scalar APIではない。'}}
    start, cpu = time.perf_counter(), time.process_time()
    native = None
    try:
        inputs = [folder / 'representation.json', folder / 'unedited.json']
        if not all(source.exists() for source in inputs):
            row.update(status='pending_audio', reason='native元表現または無編集波形の正式記録待ち')
        else:
            representation, baseline_record = map(read, inputs)
            if representation.get('status') != 'measured' or baseline_record.get('status') != 'measured':
                states = [record.get('status', 'failed') for record in (representation, baseline_record)]
                row.update(status='pending_audio' if any(state.startswith('pending') for state in states) else 'upstream_failed',
                           upstream_statuses=states, reason='native元表現または無編集生成が非成功')
            else:
                source = folder / 'representation.npz'
                if sha256(source) != representation['sha256']:
                    raise ValueError('native元表現のhashが変わりました')
                checked_audio(baseline_record)
                if path.exists() and read(path).get('status') == 'measured':
                    native = read(path)
                    if native['contract_sha256'] != signature:
                        raise ValueError('成功済みnative傾斜波形の契約が変わりました')
                    checked_audio(native)
                else:
                    if path.exists():
                        write_json(folder / 'failure_history' / f'{condition}-{time.time_ns()}.json', read(path))
                    params = world.load(source)
                    edited = edit_native(params, method, delta)
                    native = {**row, 'origin': 'explicit_native_spectral_field_operation',
                        'native_representation': {'path': str(source), 'sha256': representation['sha256'],
                                                  'record_sha256': sha256(folder / 'representation.json')},
                        'original_arrays': arrays(params), 'edited_arrays': arrays(edited),
                        'edited_representation_storage': 'in_memory; canonical arrays hashes; no redundant NPZ', 'seed': 0}
                    random.seed(0)
                    np.random.seed(0)
                    ctypes.CDLL(None).srand(ctypes.c_uint(0))
                    inference_start, inference_cpu = time.perf_counter(), time.process_time()
                    wave = world.decode(edited)
                    native.update(synthesis_seconds=time.perf_counter() - inference_start,
                        synthesis_process_cpu_seconds=time.process_time() - inference_cpu,
                        audio=save_audio(folder / f'{condition}.npy', wave, params.sample_rate),
                        status='measured', finished_at_utc=now())
                    native['length_delta_native_samples'] = native['audio']['samples'] - params.n_samples
                    write_json(path, native)
                measurement = timbre({'reference': baseline_record['audio'], 'output': native['audio'],
                    'low_hz': 300., 'high_hz': 5000., 'target_delta_db_per_octave': delta}, Inputs(ROOT))
                x, _ = checked_audio(baseline_record)
                y, _ = checked_audio(native)
                measurement.update(direction='lower', control_reference='same_native_unedited_decoded',
                    reference_rms=float(np.sqrt(np.mean(x * x))), output_rms=float(np.sqrt(np.mean(y * y))),
                    reference_peak=float(np.max(abs(x))), output_peak=float(np.max(abs(y))),
                    over_one_fraction=float(np.mean(abs(y) > 1)), clipping_or_level_correction=False)
                row.update(status='measured', metric='native_spectral_slope_tracking', measurement=measurement,
                    native_record=str(path), native_record_sha256=sha256(path),
                    baseline_record=str(folder / 'unedited.json'), baseline_record_sha256=sha256(folder / 'unedited.json'))
    except NotApplicable as error:
        logging.warning('native傾斜適用外: %s %s %s: %s', spec['id'], method, condition, error)
        row.update(status='not_applicable', reason=str(error))
    except Exception:
        logging.exception('native傾斜正式評価失敗: %s %s %s', spec['id'], method, condition)
        row.update(status='failed', error=traceback.format_exc())
    row.update(finished_at_utc=now(), wall_seconds=time.perf_counter() - start,
               process_cpu_seconds=time.process_time() - cpu, terminal=not row['status'].startswith('pending'))
    if not path.exists() or read(path).get('status') != 'measured':
        if path.exists():
            write_json(folder / 'failure_history' / f'{condition}-{time.time_ns()}.json', read(path))
        write_json(path, {**row, 'failure_stage': 'slope_native_generation'})
    write_json(result_path, row)
    return row


def evaluate(spec, method, signature, retry_failed):
    return [evaluate_point(spec, method, f'slope_{name}3', delta, signature, retry_failed)
            for name, delta in (('minus', -3.), ('plus', 3.))]


@shared_stage('native-slope')
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True, choices=range(12))
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    contract = {'schema_version': 2, 'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'methods': ['hnm', 'world_harvest'], 'planned_cases': 120, 'planned_speakers': 40,
        'control_amounts_db_per_octave': [-3., 3.], 'pivot_hz': 1000., 'low_hz': 300., 'high_hz': 5000.,
        'amplitude_rule': '10 ** (delta * log2(clip(f,300,5000)/1000) / 20)',
        'hnm_fields': {'harmonic_envelope': 'amplitude*g(f)', 'noise_psd': 'power*g(f)^2'},
        'world_fields': {'spectral_envelope': 'power*g(f)^2'},
        'frequency_grid': 'HNM native frequency_grid; WORLD linear0..sr/2 matching envelope bins',
        'unchanged': 'F0,time,aperiodicity,phase,periodicity,output_samples,all remaining fields',
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in SOURCE_FILES},
        'world_library_sha256': sha256(world.library_path()), 'environment': environment(),
        'seed': 0, 'threads': 2, 'repetitions': 1,
        'measurement': '40ms Hann/10ms hop average spectrum regression in300..5000Hz; output-baseline-target',
        'reference': 'same_method native unedited decoded full length',
        'scope': 'Explicit native spectral-field operation, not a previously implemented scalar-control API; not perceptual timbre',
        'external_waveform_dsp': False, 'original_representation_modified': False,
        'failure_policy': 'explicit native and measurement terminal rows; pending upstream reread; immutable failure history'}
    path = RUN / 'controls-slope/contract.json'
    freeze(path, contract)
    rows = []
    for spec in read(RUN / 'inputs.json')[args.batch * 10:(args.batch + 1) * 10]:
        for method in ('hnm', 'world_harvest'):
            rows += evaluate(spec, method, sha256(path), args.retry_failed)
        write_json(RUN / f'controls-slope/batch-{args.batch:02d}.json', {'rows': rows, 'updated_at_utc': now()})
    return int(any(row['status'] in ('failed', 'upstream_failed') or not row.get('terminal', True) for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-control-eval-slope'))
