"""新run専用: train-only Ridgeと全8共通録音による独立属性読み出し。"""
from __future__ import annotations

from collections import Counter
import logging
import sys

import numpy as np

from all_metrics_common import METHODS, freeze, now, read
from all_metrics_features_common import (
    OUT, TARGETS, prepare_input_contract, save_npz, source_contract,
)
from all_metrics_features_support import (
    calibration_cohort, checked_feature, evaluation_records, load_train, number, pending,
    publish_results, ranked, verify_result_artifacts,
)
from vocoderbench.quality_core import sha256, write_json

FOLDER = OUT / 'readout-rankings'
ALPHA = 1.0
SEED = 20261014
REPLICATES = 2000


def targets(split, specs):
    rows, sources, issues = [], [], []
    contract = OUT / 'targets/contract.json'
    for spec in specs:
        path = OUT / 'targets' / split / f'{spec["id"]}.json'
        if not path.exists():
            issues.append({'split': split, 'case': spec['id'], 'status': 'pending'})
            continue
        row = read(path)
        if (row['id'] != spec['id'] or row['speaker'] != spec['speaker']
                or row['source_sha256'] != spec['sha256']
                or row['contract_sha256'] != sha256(contract)):
            raise ValueError('独立原音targetの入力/契約が不一致')
        values = []
        for key in TARGETS:
            value = row['targets'][key]
            if value is not None and not np.isfinite(value):
                raise ValueError('独立targetの非有限値はnullで保存してください')
            values.append(np.nan if value is None else value)
        rows.append(values)
        sources.append({'case': spec['id'], 'record_sha256': sha256(path),
                        'missing_reasons': row.get('missing_reasons', {})})
    return np.asarray(rows, dtype=float), sources, issues


def fit(calibration, train_truth, evaluation, method):
    means = calibration['means']
    predictions = np.full((len(evaluation), len(TARGETS)), np.nan)
    metadata = {}
    for column, key in enumerate(TARGETS):
        valid = np.isfinite(train_truth[:, column])
        if valid.sum() < 2:
            metadata[key] = {'status': 'not_applicable', 'reason': 'fewer_than_two_valid_train_targets',
                             'train_valid': int(valid.sum()), 'train_total': len(valid)}
            continue
        x, y = means[valid], train_truth[valid, column]
        center, standard = x.mean(axis=0), x.std(axis=0)
        standard = np.where(standard > 1e-12, standard, 1)
        x = (x-center)/standard
        target_center = y.mean()
        u, singular, vt = np.linalg.svd(x, full_matrices=False)
        coefficients = (vt.T*(singular/(singular**2+ALPHA))) @ (u.T @ (y-target_center))
        predictions[:, column] = ((evaluation-center)/standard) @ coefficients+target_center
        path = FOLDER / 'models' / method / f'{key}.npz'
        save_npz(path, center=center, scale=standard, coefficients=coefficients,
                 target_center=np.array(target_center), train_valid=valid)
        metadata[key] = {'status': 'measured', 'train_valid': int(valid.sum()),
            'train_total': len(valid), 'train_indices': np.flatnonzero(valid).tolist(),
            'ridge_alpha': ALPHA, 'coefficients_sha256': sha256(path), 'path': str(path),
            'feature_dimensions': means.shape[1], 'constant_baseline': float(target_center),
            'scale_scope': 'target-valid train recording means only; population std; std<=1e-12 -> 1'}
    return predictions, metadata


def aggregate(specs, truth, predicted, models, column, key, methods=METHODS, ranked_primary=True):
    indices = [METHODS.index(method) for method in methods]
    valid = np.isfinite(truth[:, column]) & np.isfinite(predicted[:, indices, column]).all(axis=1)
    selected = [row for row, keep in zip(specs, valid) if keep]
    speakers = sorted({row['speaker'] for row in selected})
    values = np.full(len(METHODS), np.nan)
    boot = np.empty((0, len(METHODS)))
    errors = predicted[valid, :, column]-truth[valid, column, None]
    speaker_rows, baseline = [], {}
    if speakers:
        speaker_mae = np.stack([np.abs(errors)[[row['speaker'] == speaker for row in selected]].mean(axis=0)
                                for speaker in speakers])
        values = speaker_mae.mean(axis=0)
        draws = np.random.default_rng(SEED).integers(0, len(speakers), size=(REPLICATES, len(speakers)))
        boot = speaker_mae[draws].mean(axis=1)
        for speaker, mae in zip(speakers, speaker_mae):
            mask = np.array([row['speaker'] == speaker for row in selected])
            speaker_rows.append({'speaker': speaker, 'recordings': int(mask.sum()),
                                 'mae': {method: number(mae[METHODS.index(method)]) for method in methods}})
        for method in methods:
            constant = models[method][key].get('constant_baseline')
            if constant is not None:
                absolute = np.abs(constant-truth[valid, column])
                baseline[method] = float(np.mean([absolute[[row['speaker'] == s for row in selected]].mean()
                                                  for s in speakers]))
    else:
        draws = np.empty((0, 0), dtype=int)
    suffix = '' if ranked_primary else '-auxiliary'
    path = FOLDER / 'bootstrap' / f'{key}{suffix}.npz'
    save_npz(path, values=boot, draws=draws)
    counts = Counter(row['speaker'] for row in selected)
    result = {'unit': TARGETS[key], 'higher_is_better': False,
        'definition': '各録音絶対誤差→話者内平均→話者等重みMAE',
        'methods': ranked(values, boot), 'constant_train_mean_speaker_macro_mae': baseline,
        'cohort': {'planned_recordings': len(specs), 'planned_speakers': len({s['speaker'] for s in specs}),
            'common_recordings': len(selected), 'common_speakers': len(speakers),
            'ids': [row['id'] for row in selected], 'speaker_counts': dict(counts),
            'planned_complete': bool(valid.all()),
            'exclusion_counts': {'target_unavailable': int((~np.isfinite(truth[:, column])).sum()),
                'prediction_unavailable_by_method': {method: int((~np.isfinite(predicted[:, METHODS.index(method), column])).sum())
                                                     for method in methods},
                'counts_can_overlap': True},
            'exclusions': [{'case': row['id'], 'target_available': bool(np.isfinite(truth[i, column])),
                'feature_prediction_methods': [method for j, method in enumerate(METHODS)
                    if np.isfinite(predicted[i, j, column])]}
                for i, row in enumerate(specs) if not valid[i]]},
        'by_speaker': speaker_rows,
        'bootstrap': {'sha256': sha256(path), 'path': str(path), 'speakers': speakers,
                      'replicates': len(boot), 'requested_replicates': REPLICATES,
                      'seed': SEED, 'axes': ['replicate', 'method']}}
    for index, method in enumerate(METHODS):
        result['methods'][method]['recording_equal_mae'] = number(np.abs(errors[:, index]).mean()) if len(errors) else None
        result['methods'][method]['recording_equal_rmse'] = number(np.sqrt(np.mean(errors[:, index]**2))) if len(errors) else None
    if not ranked_primary:
        result['methods'] = {method: {**result['methods'][method], 'rank': None} for method in methods}
        result.update(comparison_scope='fixed_successful_calibration_subset_auxiliary', ranking=False,
                      method_set=list(methods))
    return result


def measure(method):
    if method not in METHODS:
        raise ValueError('未知の方式')
    train_specs, eval_specs = prepare_input_contract()
    calibration, train_issues = {}, []
    for name in METHODS:
        calibration[name], missing = load_train(name, train_specs)
        train_issues.extend(missing)
    successful = calibration_cohort(FOLDER, calibration, train_issues)
    if not successful:
        return pending(FOLDER, 'readout', train_issues)
    issues = []
    records, missing = evaluation_records(eval_specs, successful)
    issues.extend(row for row in missing if row['status'] == 'pending')
    train_truth, train_targets, target_issues = targets('train', train_specs)
    eval_truth, eval_targets, missing_targets = targets('evaluation', eval_specs)
    issues.extend(target_issues+missing_targets)
    if issues:
        return pending(FOLDER, 'readout', issues)
    contract = {'schema_version': 1, 'implementation_origin': 'new_recovery_run_source',
        'sources_sha256': source_contract(), 'methods': list(METHODS), 'alpha': ALPHA,
        'runtime': {'python': sys.version, 'numpy': np.__version__},
        'train_records': {name: calibration[name]['sources'] for name in successful},
        'calibration_cohort_sha256': sha256(FOLDER / 'calibration-cohort.json'),
        'train_exclusions': train_issues,
        'eval_records': records, 'train_targets': train_targets, 'eval_targets': eval_targets,
        'scaling': 'target-valid train recording mean population std; no evaluation fitting',
        'aggregation': 'common evaluation recordings per target; speaker-macro MAE',
        'seed': SEED, 'bootstrap_replicates': REPLICATES}
    freeze(FOLDER / 'contract.json', contract)
    if (FOLDER / 'results.json').exists() and read(FOLDER / 'results.json').get('analysis_complete'):
        return verify_result_artifacts(read(FOLDER / 'results.json'))
    predicted = np.full((len(eval_specs), len(METHODS), len(TARGETS)), np.nan)
    models = {}
    for column, name in enumerate(METHODS):
        if name not in successful:
            continue
        indices, means = [], []
        for i, spec in enumerate(eval_specs):
            if spec['id'] in records[name]:
                matrix, _ = checked_feature(name, spec, calibration[name])
                indices.append(i)
                means.append(matrix.mean(axis=0))
        evaluation = np.stack(means) if means else np.empty((0, calibration[name]['means'].shape[1]))
        estimates, models[name] = fit(calibration[name], train_truth, evaluation, name)
        predicted[indices, column] = estimates
    save_npz(FOLDER / 'predictions.npz', predictions=predicted, truth=eval_truth)
    raw = [{'case': row['id'], 'speaker': row['speaker'],
            'truth': {key: number(eval_truth[i, j]) for j, key in enumerate(TARGETS)},
            'predictions': {name: {key: number(predicted[i, m, j]) for j, key in enumerate(TARGETS)}
                            for m, name in enumerate(METHODS)}} for i, row in enumerate(eval_specs)]
    write_json(FOLDER / 'raw-recordings.json', raw)
    write_json(FOLDER / 'models.json', models)
    result = {'status': 'measured' if len(successful) == len(METHODS) else 'incomplete',
        'analysis_complete': True, 'methods': list(METHODS), 'formal_base': 'hnm',
        'estimands': {key: aggregate(eval_specs, eval_truth, predicted, models, j, key)
                      for j, key in enumerate(TARGETS)},
        'train_target_support': {key: {'valid_recordings': int(np.isfinite(train_truth[:, j]).sum()),
             'valid_ids': [row['id'] for row, valid in zip(train_specs, np.isfinite(train_truth[:, j])) if valid],
             'valid_speakers': len({row['speaker'] for row, valid in zip(train_specs, np.isfinite(train_truth[:, j])) if valid})}
             for j, key in enumerate(TARGETS)},
        'extraction_exclusions': missing, 'contract_sha256': sha256(FOLDER / 'contract.json'),
        'predictions_sha256': sha256(FOLDER / 'predictions.npz'),
        'raw_recordings_sha256': sha256(FOLDER / 'raw-recordings.json'),
        'models_sha256': sha256(FOLDER / 'models.json'), 'finished_at_utc': now(),
        'limits': ['独立推定した原音属性の読み出しであり人間評定・因果制御・復号品質ではない',
                   '話者bootstrapの記述的95%区間。trainは固定し多重比較は補正しない']}
    result['calibration_cohort'] = read(FOLDER / 'calibration-cohort.json')
    if len(successful) < len(METHODS):
        result['auxiliary_successful_methods'] = {
            'method_set': successful, 'selection_sha256': sha256(FOLDER / 'calibration-cohort.json'),
            'excluded_methods': result['calibration_cohort']['excluded_methods'],
            'ranking': False, 'primary_all_eight_available': False,
            'estimands': {key: aggregate(eval_specs, eval_truth, predicted, models, j, key, successful, False)
                         for j, key in enumerate(TARGETS)}}
    artifacts = [FOLDER / 'predictions.npz', FOLDER / 'raw-recordings.json', FOLDER / 'models.json',
                 *sorted((FOLDER / 'models').glob('*/*.npz')), *sorted((FOLDER / 'bootstrap').glob('*.npz'))]
    result['artifacts'] = [{'path': str(path), 'sha256': sha256(path)} for path in artifacts]
    publish_results(FOLDER, 'readout', result)
    logging.info('新runの全8読み出し集計完了')
    return result
