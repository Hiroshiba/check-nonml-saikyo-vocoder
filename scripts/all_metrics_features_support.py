"""新runの#14/#15に共通する入力証跡・固定尺度・順位・欠測の処理。"""
from __future__ import annotations

from collections import Counter
import math
import time

import numpy as np

from all_metrics_common import METHODS, RUN, freeze, now, read
from all_metrics_features_common import TRAIN, feature_path, load_feature, schema_digest
from vocoderbench.quality_core import sha256, write_json


def load_train(method, specs):
    means, seconds, sources, issues = [], [], [], []
    schema_path = TRAIN / 'schemas' / f'{method}.json'
    schema = read(schema_path) if schema_path.exists() else None
    contract = TRAIN / 'contracts' / f'{method}.json'
    for spec in specs:
        folder = feature_path(TRAIN, method, spec['id'])
        path = folder / 'features.json'
        if not path.exists():
            issues.append({'method': method, 'case': spec['id'], 'split': 'train', 'status': 'pending'})
            continue
        record = read(path)
        if record['status'] != 'measured':
            issues.append({'method': method, 'case': spec['id'], 'split': 'train', 'status': record['status'],
                           'error': record.get('error')})
            continue
        if (record['source_sha256'] != spec['sha256'] or schema is None
                or record['projected_schema_sha256'] != schema_digest(schema)
                or record['contract_sha256'] != sha256(contract)):
            raise ValueError(f'train入力/schema/契約不一致: {method}/{spec["id"]}')
        moments = folder / 'moments.npz'
        if sha256(moments) != record['moments_sha256']:
            raise ValueError('train母統計hash不一致')
        with np.load(moments, allow_pickle=False) as archive:
            mean, second = archive['mean'], archive['second_moment']
        if (mean.ndim != 1 or not len(mean) or second.shape != mean.shape
                or mean.dtype != np.float64 or second.dtype != np.float64
                or not np.isfinite(mean).all() or not np.isfinite(second).all()):
            raise ValueError('train母統計のshape/dtype/有限性が不一致')
        means.append(mean)
        seconds.append(second)
        sources.append({'case': spec['id'], 'record_sha256': sha256(path),
                        'moments_sha256': record['moments_sha256'],
                        'transient_frame_npy_sha256': record['sha256']})
    if issues:
        return None, issues
    means, seconds = np.stack(means), np.stack(seconds)
    center = means.mean(axis=0)
    scale = np.sqrt(np.maximum(seconds.mean(axis=0)-center**2, 0))
    scale = np.where(scale > 1e-12, scale, 1)
    return {'means': means, 'center': center, 'scale': scale, 'schema': schema,
            'sources': sources, 'schema_sha256': sha256(schema_path)}, []


def evaluation_records(specs, methods=METHODS):
    """未到着と失敗を分離する。失敗録音は全8共通群の候補から外れる。"""
    records, issues = {}, []
    for method in methods:
        records[method] = {}
        for spec in specs:
            path = feature_path(RUN, method, spec['id']) / 'features.json'
            if not path.exists():
                issues.append({'method': method, 'case': spec['id'], 'status': 'pending'})
                continue
            row = read(path)
            if row['status'] != 'measured':
                issues.append({'method': method, 'case': spec['id'], 'status': row['status'],
                               'error': row.get('error')})
                continue
            artifact = path.parent / ('features.npz' if row.get('storage') == 'lossless_npz' else 'features.npy')
            if sha256(artifact) != row['sha256']:
                raise ValueError(f'eval特徴配列hash不一致: {method}/{spec["id"]}')
            contract = (RUN / 'latent-contracts' / method / 'feature-export.json'
                        if row.get('origin') == 'existing_native_representation_export'
                        else RUN / 'synthesis-contracts' / f'{method}.json')
            if row['contract_sha256'] != sha256(contract):
                raise ValueError('eval特徴の抽出契約hash不一致')
            if read(contract)['input_contract_sha256'] != sha256(RUN / 'input-contract.json'):
                raise ValueError('eval特徴の原音入力契約が不一致')
            records[method][spec['id']] = {'record_sha256': sha256(path)}
    return records, issues


def checked_feature(method, spec, calibration):
    matrix, schema, record = load_feature(RUN, method, spec['id'])
    if schema != calibration['schema']:
        raise ValueError(f'evalとtrainの特徴schema不一致: {method}/{spec["id"]}')
    return matrix, record


def calibration_cohort(folder, calibrations, issues):
    """全train終端後、値を見ずに120件校正成功方式を一度固定する。"""
    if any(row['status'] == 'pending' for row in issues):
        return None
    methods = [method for method in METHODS if calibrations[method] is not None]
    selection = {'methods': methods, 'selection_uses_metric_values': False,
        'required_train_recordings': 120, 'required_train_speakers': 40,
        'rule': 'all 120 native-feature moment records measured; never reduced-train fitting',
        'excluded_methods': {method: [row for row in issues if row.get('method') == method]
                             for method in METHODS if method not in methods},
        'excluded_method_status_counts': {method: dict(Counter(row['status'] for row in issues
            if row.get('method') == method)) for method in METHODS if method not in methods},
        'reselection': 'forbidden in this run; start a separate run to change the method set'}
    freeze(TRAIN / 'calibration-cohort.json', selection)
    freeze(folder / 'calibration-cohort.json', selection)
    return methods


def pending(folder, stage, issues):
    result = {'status': 'pending' if any(row['status'] == 'pending' for row in issues)
              else 'incomplete', 'stage': stage, 'value': None, 'rank': None,
              'issues': issues, 'status_counts': dict(Counter(row['status'] for row in issues)),
              'updated_at_utc': now()}
    write_json(folder / 'status.json', result)
    if result['status'] == 'incomplete':
        result.update(terminal=True, analysis_complete=True, methods=list(METHODS), formal_base='hnm', artifacts=[],
            reason='fixed_train_calibration_unavailable_no_reduced_train_fit',
            estimands={}, planned_train_recordings_per_method=120,
            planned_train_speakers_per_method=40,
            train_failures_by_method={method: [row for row in issues
                if row.get('method') == method and row.get('split') == 'train'] for method in METHODS})
        publish_results(folder, stage, result)
    return result


def number(value):
    return float(value) if np.isfinite(value) else None


def ci(values):
    valid = values[np.isfinite(values)]
    return {'ci95': np.quantile(valid, [.025, .975]).tolist() if len(valid) else None,
            'valid_replicates': len(valid), 'undefined_replicates': len(values)-len(valid)}


def ranked(points, replicates):
    order = sorted((i for i, value in enumerate(points) if np.isfinite(value)), key=lambda i: points[i])
    ranks, anchor, rank = {}, None, None
    for position, index in enumerate(order, 1):
        value = points[index]
        if anchor is None or not math.isclose(value, anchor, abs_tol=1e-12, rel_tol=1e-9):
            anchor, rank = value, position
        ranks[index] = rank
    base = METHODS.index('hnm')
    return {method: {'status': 'measured' if np.isfinite(points[index]) else 'undefined',
        'value': number(points[index]), 'rank': ranks.get(index), **ci(replicates[:, index]),
        'hnm_difference': {'value': number(points[index]-points[base]),
                           **ci(replicates[:, index]-replicates[:, base])}}
        for index, method in enumerate(METHODS)}


def publish_results(folder, stage, result):
    previous = folder / 'results.json'
    if previous.exists() and read(previous) != result:
        write_json(folder / 'failure_history' / f'{time.time_ns()}.json', read(previous))
    write_json(folder / 'results.json', result)
    for method in METHODS:
        write_json(folder.parent / method / stage / 'results.json',
                   {**result, 'method': method, 'shared_results': str(folder / 'results.json')})


def verify_result_artifacts(result):
    for item in result['artifacts']:
        if sha256(item['path']) != item['sha256']:
            raise ValueError(f'保存済み評価artifact hash不一致: {item["path"]}')
    return result
