"""事後追加の量子化共通窓。保存済みwaveの正式測定専用。"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import logging
import traceback
from pathlib import Path
import sys

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from all_metrics_common import METHODS, RUN, read  # noqa: E402
from all_metrics_controls import checked_audio  # noqa: E402
from all_metrics_latent_evaluation_common import (  # noqa: E402
    artifact_evidence, exact_identity,
)
from all_metrics_latent_provenance import verify_native, verify_retained_evidence  # noqa: E402
from vocoderbench.assessment.acoustics import auditory  # noqa: E402
from vocoderbench.assessment.common import NotApplicable  # noqa: E402
from vocoderbench.quality_core import sha256  # noqa: E402

BASE = RUN / 'latent-common-window-supplement-v2'
SOURCE = Path(__file__).resolve().parent
CONDITIONS = ('quantized_float16', 'quantized_float32')
TERMINAL = ('measured', 'failed', 'not_applicable', 'unsupported', 'upstream_failed')


def pcm_hash(wave):
    return hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()


def evidence(path):
    return {'path': str(path), 'sha256': sha256(path), 'bytes': Path(path).stat().st_size}


def marker_time(path, field):
    text = path.read_text().strip()
    values = [line.split('=', 1)[1] for line in text.splitlines() if line.startswith(field + '=')]
    if len(values) != 1:
        raise ValueError(f'実時刻markerの{field}が一意にありません: {path}')
    return values[0]


def batch_gate(batch):
    path = RUN / f'operations/control-latent-batch{batch:02d}-completion.json'
    if not path.exists():
        return {'status': 'pending_batch_completion', 'path': str(path)}
    row = read(path)
    if row.get('batch') != batch or row.get('all_owned_scientific_sessions_exited') is not True:
        return {'status': 'pending_batch_completion', **evidence(path)}
    if batch != 0 and not (row.get('all_planned_records_terminal') is True and row.get('native_json_storage_frozen') is True):
        return {'status': 'pending_storage_completion', **evidence(path)}
    stage = 'storage-migration' if batch == 0 else 'latent-evaluation'
    matches = [x for x in row.get('stage_executions', []) if x.get('stage') == stage]
    if len(matches) != 1 or (batch == 0 and matches[0].get('exit_code') != 0):
        return {'status': 'pending_storage_completion', 'required_stage': stage, **evidence(path)}
    actual = []
    for entry in row.get('stage_executions', []):
        prefix = RUN / f"operations/control-latent-batch{batch:02d}-{entry['stage']}"
        exit_path = Path(str(prefix) + '.driver.exit')
        finish = Path(str(prefix) + '.finish.txt')
        start = Path(str(prefix) + '.start.txt')
        if any(not p.exists() for p in (exit_path, start, finish)):
            return {'status': 'pending_actual_stage_exit', 'required_stage': entry['stage'], **evidence(path)}
        if int(exit_path.read_text().strip()) != entry['exit_code']:
            raise ValueError(f'completionと実exit不一致: {exit_path}')
        if marker_time(start, 'started_at_utc') != entry['started_at_utc'] or marker_time(finish, 'finished_at_utc') != entry['finished_at_utc']:
            raise ValueError(f'completionと実開始/終了不一致: {prefix}')
        actual.append({'stage': entry['stage'], 'exit': evidence(exit_path), 'start': evidence(start), 'finish': evidence(finish)})
    return {'status': 'terminal', 'stage': stage, 'stage_execution': matches[0], 'actual_stage_receipts': actual, **evidence(path)}


@lru_cache(maxsize=16)
def scientific_contract(method, native):
    path = RUN / f'synthesis-contracts/{method}.json' if native else RUN / f'latent-contracts/{method}/quantization.json'
    value = read(path)
    if value['method'] != method or value['seed'] != 0 or value['input_contract_sha256'] != sha256(RUN / 'input-contract.json'):
        raise ValueError(f'元科学契約のmethod/seed/input不一致: {path}')
    for source, digest in value['source_sha256'].items():
        if sha256(ROOT / source) != digest:
            raise ValueError(f'元科学source hash不一致: {source}')
    return {**evidence(path), 'seed': value['seed'], 'input_contract_sha256': value['input_contract_sha256']}


def source_record(spec, method, condition):
    path = RUN / 'native' / method / spec['id'] / f'{condition}.json'
    if not path.exists():
        raise ValueError(f'終端batchに予定native JSONがありません: {path}')
    row = read(path)
    if (row.get('case'), row.get('method'), row.get('condition')) != (spec['id'], method, condition):
        raise ValueError(f'case/method/condition不一致: {path}')
    input_hash = row.get('input_source_sha256', row.get('input', {}).get('source_sha256'))
    if input_hash != spec['sha256']:
        raise ValueError(f'固定入力hash不一致: {path}')
    if row.get('status') not in TERMINAL:
        raise ValueError(f'終端batchに非終端のpointがあります: {path}')
    contract = scientific_contract(method, condition == 'unedited')
    if row.get('contract_sha256') != contract['sha256'] or row.get('seed') != contract['seed']:
        raise ValueError(f'元科学契約またはseedとの対応不一致: {path}')
    if row.get('speaker', spec['speaker']) != spec['speaker']:
        raise ValueError(f'予定話者不一致: {path}')
    if condition != 'unedited':
        expected = RUN / 'native' / method / spec['id'] / 'representation.npz'
        if row.get('native_representation', {}).get('path') != str(expected):
            raise ValueError(f'量子化点のnative表現対応先が不一致: {path}')
        verify_native(row)
    row['scientific_contract_evidence'] = contract
    row['record_evidence'] = evidence(path)
    return row


def compact_record(row):
    keys = ('case', 'speaker', 'method', 'condition', 'status', 'audio', 'record_evidence',
            'contract_sha256', 'input_source_sha256', 'input', 'origin', 'quantization', 'provenance',
            'native_representation', 'feature_artifact', 'error', 'reason', 'failure_stage',
            'reused_waveform_record', 'reused_waveform_record_sha256', 'length_delta_native_samples', 'scientific_contract_evidence')
    return {key: row[key] for key in keys if key in row}


def transform(record, cache):
    wave, rate = checked_audio(record)
    key = (record['audio']['float64_sha256'], rate)
    divisor = math.gcd(rate, 16000)
    if key not in cache:
        cache[key] = (resample_poly(wave, 16000 // divisor, rate // divisor,
                      window=('kaiser', 5.0), padtype='constant') if rate != 16000 else wave)
    transformed = cache[key]
    return transformed, {'source_audio': record['audio'], 'sample_rate': 16000,
        'up': 16000 // divisor, 'down': rate // divisor, 'samples': len(transformed),
        'seconds': len(transformed) / 16000, 'float64_sha256': pcm_hash(transformed),
        'window': ['kaiser', 5.0], 'padtype': 'constant', 'stored': False}


def original_record(spec):
    if sha256(spec['path']) != spec['sha256']:
        raise ValueError('固定原音file hash不一致')
    wave = np.load(spec['path'], allow_pickle=False)
    if len(wave) != spec['samples'] or spec['sample_rate'] != 16000:
        raise ValueError('固定主集合の原音長さ/16kHz条件不一致')
    return {'status': 'measured', 'audio': {'path': spec['path'], 'file_sha256': spec['sha256'],
        'sample_rate': spec['sample_rate'], 'samples': spec['samples'],
        'seconds': spec['samples'] / spec['sample_rate'], 'float64_sha256': pcm_hash(wave)}}


def length_delta(native, point, transformed):
    if native['status'] != 'measured' or point['status'] != 'measured':
        return {'status': 'not_applicable', 'reason': 'native/pointの成功waveが揃っていません'}
    a, b = native['audio'], point['audio']
    return {'status': 'measured_metadata', 'native_samples': a['samples'],
        'native_sample_rate': a['sample_rate'], 'native_seconds': a['seconds'],
        'point_samples': b['samples'], 'point_sample_rate': b['sample_rate'], 'point_seconds': b['seconds'],
        'signed_native_samples': b['samples'] - a['samples'] if a['sample_rate'] == b['sample_rate'] else None,
        'signed_seconds': b['seconds'] - a['seconds'],
        'signed_fraction_of_native': b['seconds'] / a['seconds'] - 1,
        'signed_16k_samples': transformed['point']['samples'] - transformed['native']['samples']}


def measure_pair(native, point, waves):
    if exact_identity(native, point):
        return {'status': 'analytic_identity', 'value': 0., 'unit': 'dB', 'direction': 'lower',
            'reason': '同一canonical復号入力と実PCMの証拠。共通窓にも同一性が継承され、自己比較計算なし。',
            'identity_evidence': point['quantization'],
            'native_record': native['record_evidence'], 'point_record': point['record_evidence'],
            'wave_float64_sha256': point['audio']['float64_sha256']}
    class Pair:
        def pair(self, job):
            return waves['native'], waves['point'], 16000
    return {**auditory({}, Pair()), 'status': 'measured', 'direction': 'lower'}


def case_group(spec, records, condition, members, group_id):
    """群の全成功waveから一度だけ窓を固定し、同じ窓で各方式を測る。"""
    selected = {m: records[m] for m in members}
    rows, transformed, waves, cache = [], {}, {}, {}
    raw_states = {m: {side: records[m][side]['status'] for side in ('native', 'point')} for m in METHODS}
    # 成功waveの全長変換は欠測群にも残す。聴覚自己比較は行わない。
    source_original = original_record(spec)
    original, original_info = transform(source_original, cache)
    for method, pair in selected.items():
        transformed[method], waves[method] = {}, {}
        for side, record in pair.items():
            if record['status'] == 'measured':
                if side == 'point':
                    verify_retained_evidence(record)
                waves[method][side], transformed[method][side] = transform(record, cache)
    all_success = bool(members) and all(s == 'measured' for p in selected.values() for s in (p['native']['status'], p['point']['status']))
    n = min([len(original)] + [len(w) for pair in waves.values() for w in pair.values()]) if all_success else None
    infos = {'original': original_info, **{f'{m}:{s}': info for m, pair in transformed.items() for s, info in pair.items()}}
    for info in infos.values():
        count = info['samples']
        info.update(common_samples=n, coverage=n / count if n is not None else None,
                    omitted_tail_samples=count - n if n is not None else None,
                    omitted_tail_seconds=(count - n) / 16000 if n is not None else None)
    common = {'start_sample': 0, 'end_sample_exclusive': n,
        'seconds': n / 16000 if n is not None else None, 'sample_rate': 16000,
        'members': list(members), 'all_sources': infos,
        'all_selected_native_and_point_successful': all_success}
    if not all_success:
        common.update(status='no_common_window_upstream', reason='固定集合のnative/point成功waveが揃わず、共通窓を定めません')
    elif n < 16000 or min(x['coverage'] for x in infos.values()) < .95:
        common.update(status='not_applicable', reason='共通窓が最低1秒または全波形95%coverageを満たしません')
    else:
        common['status'] = 'measured'
        for method, pair in waves.items():
            for side, wave in pair.items():
                transformed[method][side]['common_float64_sha256'] = pcm_hash(wave[:n])
        original_info['common_float64_sha256'] = pcm_hash(original[:n])
    for method in METHODS:
        pair = records[method]
        row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
            'condition': condition, 'group_id': group_id, 'value': None, 'unit': 'dB', 'direction': 'lower',
            'upstream_statuses': raw_states[method],
            'source_records': {s: compact_record(r) for s, r in pair.items()},
            'shared_window_status': common['status'], 'window_evidence_scope': 'shared case-level common_window'}
        if method not in members:
            row.update(status='excluded_method', reason='全予定point終端後にwave成功状態だけで固定した比較集合の対象外')
        elif any(r['status'] != 'measured' for r in pair.values()):
            statuses = [r['status'] for r in pair.values() if r['status'] != 'measured']
            row.update(status='upstream_failed' if any('failed' in s for s in statuses) else statuses[0],
                reason='同方式native/point上流終端状態を継承', upstream_reasons=[r.get('error', r.get('reason')) for r in pair.values() if r['status'] != 'measured'])
        elif common['status'] != 'measured':
            row.update(status='not_applicable', reason=common['reason'])
        else:
            try:
                row.update(measure_pair(pair['native'], pair['point'], {s: w[:n] for s, w in waves[method].items()}))
            except NotApplicable as error:
                row.update(status='not_applicable', reason=str(error))
            except Exception:
                logging.exception('補助聴覚測定失敗: %s %s %s', spec['id'], method, condition)
                row.update(status='failed', error=traceback.format_exc())
        if method in transformed:
            row['derivations'] = transformed[method]
            row['full_length_delta'] = length_delta(pair['native'], pair['point'], transformed[method])
        strict_path = RUN / 'latent-evaluation/measurements' / f"{spec['id']}__{method}.json"
        strict = read(strict_path)
        strict_contract = RUN / 'latent-evaluation/contract.json'
        if (strict.get('case'), strict.get('method'), strict.get('speaker'), strict.get('contract_sha256')) != (spec['id'], method, spec['speaker'], sha256(strict_contract)):
            raise ValueError('元strict評価のcase/method/speaker/科学契約SHA不一致')
        strict_points = strict['metrics']['17_representation_robustness'].get('points', [])
        prior = next((p for p in strict_points if p['configuration'] == condition), None)
        row['strict_primary_evidence'] = evidence(strict_path)
        row['strict_primary_contract_evidence'] = evidence(strict_contract)
        row['strict_primary_auditory'] = ({k: v for k, v in prior.get('auditory', {}).items() if k in ('status', 'value', 'unit', 'reason')} if prior else None)
        if pair['native']['status'] == 'measured':
            row['native_information_rate'] = artifact_evidence(spec, method, pair['native'])
        if pair['point']['status'] == 'measured':
            row['information_rate'] = artifact_evidence(spec, method, pair['point'])
            row['information_rate']['auditory_source'] = {'group_id': group_id, 'case': spec['id'], 'method': method, 'condition': condition}
        rows.append(row)
    return {'case': spec['id'], 'speaker': spec['speaker'], 'condition': condition,
            'group_id': group_id, 'members': list(members), 'common_window': common, 'rows': rows}
