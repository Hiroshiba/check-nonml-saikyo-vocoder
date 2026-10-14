"""新run専用: 公式境界の部分群をnative特徴・固定距離で全8合同評価。"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
import logging
import sys
import traceback

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_features_common import (
    OUT, feature_path, npy_hash, prepare_input_contract, project, save_npz, source_contract,
)
from all_metrics_features_support import (
    calibration_cohort, evaluation_records, load_train, pending, publish_results,
    verify_result_artifacts,
)
from all_metrics_features_abx_statistics import (
    ESTIMANDS, REPLICATES, SEED,
)
from all_metrics_features_abx_results import summarize
from vocoderbench.assessment.representation import dtw
from vocoderbench.quality_core import sha256, write_json

FOLDER = OUT / 'abx-rankings'
MANIFEST = RUN / 'corpora/abxls120-triphones.json'
SOURCE_AUDIT = RUN / 'corpora/abxls120-source-identity.json'
MAX_CELLS = 2_000_000
TIE_ATOL = 1e-12


def native_times(record, length, method):
    schema = record['schema']
    if 'frame_times_seconds' in schema:
        if method == 'magphase' and schema.get('frame_times_origin') != 'native_analysis_shift_cumsum':
            raise ValueError('MagPhase token境界は元analysis shift累積の時刻が必要です')
        times = np.asarray(schema['frame_times_seconds'], dtype=float)
    elif 'frame_hop_seconds' in schema:
        times = np.arange(length)*float(schema['frame_hop_seconds'])
    elif 'frame_hop_samples' in schema:
        times = np.arange(length)*float(schema['frame_hop_samples'])/schema['sample_rate']
    else:
        raise ValueError('native特徴の時刻が不明。録音長から補間しません')
    if times.shape != (length,) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('native特徴時刻が有限な単調増加frame時刻ではありません')
    return times


def validate_manifest(data, specs):
    known = {row['id']: row for row in specs}
    items = {row['id']: row for row in data['items']}
    if len(items) != len(data['items']):
        raise ValueError('ABX token ID重複')
    if data['frozen_audio_manifest_sha256'] != sha256(ROOT / 'data/clean_speech_v1.json'):
        raise ValueError('ABXラベル対象の固定原音manifestが不一致')
    if sha256(ROOT / data['label_file']) != data['label_sha256']:
        raise ValueError('ABXの公式ラベルファイルhash不一致')
    for item in items.values():
        spec = known[item['recording_id']]
        if (item['speaker'] != spec['speaker'] or not 0 <= item['onset_seconds'] < item['offset_seconds']
                <= spec['samples']/spec['sample_rate']):
            raise ValueError('ABX tokenの話者/原音区間が不一致')
    seen = set()
    for row in data['triplets']:
        ids = tuple(row[role] for role in ('a', 'b', 'x'))
        if len(set(ids)) != 3 or ids in seen:
            raise ValueError('ABXの重複三つ組または同一token')
        seen.add(ids)
        a, b, x = (items[i] for i in ids)
        condition = 'within_speaker' if a['speaker'] == x['speaker'] else 'across_speaker'
        if (a['phone'] != x['phone'] or a['phone'] == b['phone']
                or len({p['context'] for p in (a, b, x)}) != 1
                or a['speaker'] != b['speaker'] or condition != row['condition']):
            raise ValueError('ABXのphone/context/話者条件が不一致')
    audit = read(SOURCE_AUDIT)['entries']
    sources = {row['id']: row for row in audit}
    used_tokens = {row[role] for row in data['triplets'] for role in ('a', 'b', 'x')}
    used_recordings = {items[token]['recording_id'] for token in used_tokens}
    if len(sources) != len(audit) or set(sources)-set(known) or used_recordings-set(sources):
        raise ValueError('ABX使用録音の公式PCM照合が未完了または照合IDが不正')
    if any(sources[key].get('status') != 'ok' or sources[key].get('identical_full_source_pcm') is not True
           or sources[key]['abxls_pcm_sha256'] != sources[key]['frozen_librispeech_pcm_sha256'] for key in used_recordings):
        raise ValueError('公式ABX配布PCMと原音PCMの同一性が未確認')
    original = read(ROOT / 'data/clean_speech_v1.json')['entries']
    if any(sources[row['id']]['frozen_librispeech_pcm_sha256'] != row['decoded_pcm_sha256']
           for row in original if row['id'] in used_recordings):
        raise ValueError('ABX PCM照合の参照hashが固定manifestと不一致')
    audit_scope = {'planned_source_recordings': len(specs), 'used_recordings': len(used_recordings),
        'verified_used_source_pcm': len(used_recordings),
        'label_unmatched_utterances': data.get('unmatched_utterances', []),
        'unused_recordings': [{'id': key, 'source_audit_status': sources.get(key, {}).get('status', 'not_present'),
                              'source_audit_error': sources.get(key, {}).get('error')}
                             for key in sorted(set(known)-used_recordings)]}
    return items, audit_scope


def distances(method, items, triplets, specs, calibration, records):
    by_recording = {}
    for item in items.values():
        by_recording.setdefault(item['recording_id'], []).append(item)
    tokens, exclusions = {}, []
    for spec in specs:
        if spec['id'] not in by_recording or spec['id'] not in records:
            continue
        record = read(feature_path(RUN, method, spec['id']) / 'features.json')
        times = native_times(record, record['shape'][0], method)
        for item in by_recording[spec['id']]:
            start, end = np.searchsorted(times, [item['onset_seconds'], item['offset_seconds']], side='left')
            if start == end:
                exclusions.append({'method': method, 'token': item['id'], 'reason': 'no_native_frame_in_token'})
            else:
                tokens[item['id']] = (spec['id'], int(start), int(end), record)
    @lru_cache(maxsize=4)
    def raw_features(identifier):
        folder = feature_path(RUN, method, identifier)
        record = read(folder / 'features.json')
        if record.get('storage') == 'lossless_npz':
            with np.load(folder / 'features.npz', allow_pickle=False) as archive:
                matrix = archive['features']
            if npy_hash(matrix) != record['uncompressed_npy_sha256']:
                raise ValueError('ABXの復元NPY hash不一致')
        else:
            matrix = np.load(folder / 'features.npy', allow_pickle=False, mmap_mode='r')
        if list(matrix.shape) != record['shape']:
            raise ValueError('ABX特徴shapeが記録と不一致')
        return matrix
    def token(identifier):
        recording, start, end, record = tokens[identifier]
        matrix, schema = project(raw_features(recording)[start:end], record['schema'], method)
        if schema != calibration['schema']:
            raise ValueError('ABXのeval/train特徴schema不一致')
        return matrix
    cache, raw, errors = {}, [], np.full(len(triplets), np.nan)
    weights = 1/calibration['scale']
    for index, row in enumerate(triplets):
        ids = [row[role] for role in ('a', 'b', 'x')]
        if not all(i in tokens for i in ids):
            raw.append({**row, 'status': 'not_applicable', 'reason': 'missing_token_features', 'error': None})
            continue
        pair_keys = [tuple(sorted((row[role], row['x']))) for role in ('a', 'b')]
        for key in pair_keys:
            if key not in cache:
                try:
                    value = dtw(token(key[0]), token(key[1]), 'euclidean', weights, MAX_CELLS)
                    if not np.isfinite(value):
                        raise ValueError('ABX DTW距離が非有限')
                    cache[key] = {'status': 'measured', 'value': value}
                except Exception:
                    logging.exception('ABX DTW距離失敗: %s %s', method, key)
                    cache[key] = {'status': 'failed', 'value': None, 'exception': traceback.format_exc()}
        da, db = [cache[key]['value'] for key in pair_keys]
        if da is None or db is None:
            raw.append({**row, 'status': 'failed', 'reason': 'distance_failed', 'error': None})
            continue
        tie = abs(da-db) <= TIE_ATOL
        errors[index] = .5 if tie else float(da > db)
        raw.append({**row, 'status': 'measured', 'distance_ax': da, 'distance_bx': db,
                    'tie': tie, 'error': float(errors[index])})
    path = FOLDER / 'raw' / f'{method}.json'
    write_json(path, {'triplets': raw, 'token_exclusions': exclusions,
        'distances': [{'tokens': list(key), **value} for key, value in sorted(cache.items())]})
    return errors, {'path': str(path), 'sha256': sha256(path),
                    'status_counts': dict(Counter(row['status'] for row in raw)),
                    'available_tokens': len(tokens)}


def measure(method):
    if method not in METHODS:
        raise ValueError('未知の方式')
    issues = [{'artifact': str(path), 'status': 'pending'} for path in (MANIFEST, SOURCE_AUDIT) if not path.exists()]
    if issues:
        return pending(FOLDER, 'abx', issues)
    train_specs, eval_specs = prepare_input_contract()
    data = read(MANIFEST)
    items, audit_scope = validate_manifest(data, eval_specs)
    calibrations, train_issues = {}, []
    for name in METHODS:
        calibrations[name], missing = load_train(name, train_specs)
        train_issues.extend(missing)
    successful = calibration_cohort(FOLDER, calibrations, train_issues)
    if not successful:
        return pending(FOLDER, 'abx', train_issues)
    records, exclusions = evaluation_records(eval_specs, successful)
    issues.extend(row for row in exclusions if row['status'] == 'pending')
    if issues:
        return pending(FOLDER, 'abx', issues)
    contract = {'schema_version': 1, 'implementation_origin': 'new_recovery_run_source',
        'sources_sha256': source_contract(), 'manifest_sha256': sha256(MANIFEST),
        'source_audit_sha256': sha256(SOURCE_AUDIT), 'methods': list(METHODS),
        'train_records': {name: calibrations[name]['sources'] for name in successful},
        'train_exclusions': train_issues, 'calibration_cohort_sha256': sha256(FOLDER / 'calibration-cohort.json'),
        'eval_records': records, 'distance': 'euclidean', 'max_dtw_cells': MAX_CELLS,
        'tie_atol': TIE_ATOL, 'tie_error': .5, 'downsampling': False,
        'scale': 'train utterance-equal native frame population std; std<=1e-12 -> 1',
        'token_window': 'onset <= actual native frame time < offset',
        'estimands': list(ESTIMANDS), 'bootstrap_seed': SEED, 'bootstrap_replicates': REPLICATES,
        'runtime': {'python': sys.version, 'numpy': np.__version__}}
    freeze(FOLDER / 'contract.json', contract)
    if (FOLDER / 'results.json').exists() and read(FOLDER / 'results.json').get('analysis_complete'):
        return verify_result_artifacts(read(FOLDER / 'results.json'))
    errors = np.full((len(data['triplets']), len(METHODS)), np.nan)
    raw_sources = {}
    for name in successful:
        error, raw_sources[name] = distances(name, items, data['triplets'], eval_specs, calibrations[name], records[name])
        errors[:, METHODS.index(name)] = error
        save_npz(FOLDER / 'calibration' / f'{name}.npz', center=calibrations[name]['center'], scale=calibrations[name]['scale'])
    result = summarize(FOLDER, data['triplets'], errors, items)
    if len(successful) < len(METHODS):
        result['status'] = 'incomplete'
        result['auxiliary_successful_methods'] = summarize(
            FOLDER / 'auxiliary', data['triplets'], errors, items, successful, ranking=False)
        result['auxiliary_successful_methods'].update(
            selection_sha256=sha256(FOLDER / 'calibration-cohort.json'),
            primary_all_eight_available=False,
            excluded_methods=read(FOLDER / 'calibration-cohort.json')['excluded_methods'])
    result.update({
        'analysis_complete': True, 'methods': list(METHODS), 'formal_base': 'hnm',
        'raw_sources': raw_sources, 'extraction_exclusions': exclusions,
        'official_source_audit_scope': audit_scope,
        'calibration_cohort': read(FOLDER / 'calibration-cohort.json'),
        'contract_sha256': sha256(FOLDER / 'contract.json'),
        'definitions': {'flat_stratum': '条件/有向音素対/文脈/A話者/X話者の層内三つ組平均→全層等重み',
            'x_speaker_macro': 'X話者内の層等重み平均→X話者等重み',
            'nested_phone_context': '有向音素対×文脈内の話者対平均→音素対内文脈平均→有向音素対平均'},
        'limits': ['公式6秒部分群でありabxLS全corpus順位ではない',
            'nestedは本研究の明示補助。公式ZeroSpeech集計との厳密同値性は未検証',
            '固定話者グラフに条件付きの記述的node bootstrap。多重比較未補正'],
        'finished_at_utc': now()})
    artifacts = [FOLDER / 'speaker-bootstrap.npz', FOLDER / 'strata.json', FOLDER / 'common-triplets.json',
                 *sorted((FOLDER / 'auxiliary').glob('*')), *sorted((FOLDER / 'raw').glob('*.json')), *sorted((FOLDER / 'calibration').glob('*.npz'))]
    result['artifacts'] = [{'path': str(path), 'sha256': sha256(path)} for path in artifacts]
    publish_results(FOLDER, 'abx', result)
    return result
