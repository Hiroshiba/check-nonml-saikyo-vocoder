"""全8方式の既存人間評定との一致を共通録音対で正式集計する。"""
from __future__ import annotations

from collections import Counter
import logging
from pathlib import Path
import sys

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_features_common import TRAIN, prepare_input_contract, save_npz, schema_digest
from all_metrics_features_support import calibration_cohort, load_train
from all_metrics_human_data import OUT as HUMAN, PLAN, PUBLIC
from all_metrics_human_statistics import METRICS, bootstrap, ci, ranks
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

OUT = RUN / 'feature-assessment/human-rankings'
DEFINITIONS = {
    'rating_spearman': '録音対等重みの人間対平均評定と負Euclidean距離のSpearman相関',
    'rated_neighbor_top1': 'Bごとの評定済みA候補限定の最短距離と最高評定の一致率、B話者macro'}
UNCERTAINTY = ('固定された人間対平均と観測話者グラフに条件付きの記述的node bootstrap。'
               '評定者不確実性・公式CI・厳密なnominal coverageは保証せず、多重比較未補正。')


def load_features(methods=METHODS):
    selection = read(HUMAN / 'selection.json')
    states, data, records, exclusions = {}, {}, {}, []
    pending = False
    for method in methods:
        features, source_rows, counts = {}, {}, Counter()
        schema = read(TRAIN / 'schemas' / f'{method}.json')
        contract_path = HUMAN / 'feature-contracts' / f'{method}.json'
        for sample in selection['identities']:
            identifier = 'asvspoof2019_'+Path(sample).stem
            folder = HUMAN / 'features' / method / identifier
            path = folder / 'features.json'
            if not path.exists():
                counts['pending'] += 1
                pending = True
                continue
            record = read(path)
            counts[record['status']] += 1
            if record['status'] != 'measured':
                exclusions.append({'method': method, 'sample': sample,
                                   'status': record['status'], 'error': record.get('error')})
                continue
            if record['contract_sha256'] != sha256(contract_path):
                raise ValueError('#13特徴契約hash不一致')
            mean = folder / 'mean.npy'
            if sha256(mean) != record['mean_sha256'] or schema_digest(schema) != record['projected_schema_sha256']:
                raise ValueError('#13平均特徴hash/schema不一致')
            vector = np.load(mean, allow_pickle=False)
            if vector.ndim != 1 or vector.dtype != np.float64 or not np.isfinite(vector).all():
                raise ValueError('#13平均特徴shape/float64/有限性不一致')
            features[sample] = vector
            source_rows[sample] = {'mean_sha256': record['mean_sha256'],
                'record_sha256': sha256(path), 'frame_npy_sha256': record['frame_npy_sha256'],
                'frame_canonical_sha256': record['frame_canonical_sha256'],
                'contract_sha256': record['contract_sha256']}
        states[method] = dict(counts)
        data[method], records[method] = features, source_rows
    if pending:
        write_json(OUT / 'status.json', {'status': 'pending', 'states': states, 'updated_at_utc': now()})
        return None
    common = [row for row in selection['pairs'] if all(
        row['sample_a'] in data[method] and row['sample_b'] in data[method] for method in methods)]
    return selection, states, data, records, exclusions, common


def train_source_index(methods=METHODS):
    specs, _ = prepare_input_contract()
    sources = {}
    for method in methods:
        calibration, issues = load_train(method, specs)
        if issues:
            raise ValueError('固定120独立trainの全成功校正がありません')
        sources[method] = calibration['sources']
    return sources


def scale(method):
    specs, _ = prepare_input_contract()
    calibration, issues = load_train(method, specs)
    if issues:
        raise ValueError('固定120独立train母統計が未成功です')
    path = OUT / 'calibration' / f'{method}.npz'
    save_npz(path, center=calibration['center'], scale=calibration['scale'])
    metadata = {'sources': calibration['sources'], 'sha256': sha256(path),
        'schema_sha256': calibration['schema_sha256'],
        'definition': 'train utterance-equal; within utterance frame-equal population moments',
        'independent_training_recordings': len(specs), 'evaluation_fit': False,
        'input_contract_sha256': sha256(TRAIN / 'input-contract.json')}
    write_json(path.with_suffix('.json'), metadata)
    return calibration['scale'], metadata


def train_readiness():
    specs, _ = prepare_input_contract()
    issues, sources, calibrations = [], {}, {}
    for method in METHODS:
        calibration, missing = load_train(method, specs)
        issues.extend(missing)
        calibrations[method] = calibration
        sources[method] = calibration['sources'] if calibration is not None else None
    successful = calibration_cohort(OUT, calibrations, issues)
    if not issues:
        return successful
    if any(row['status'] == 'pending' for row in issues):
        write_json(OUT / 'status.json', {'status': 'pending', 'stage': 'train_calibration',
                                       'issues': issues, 'updated_at_utc': now()})
        return False
    result = {'status': 'incomplete', 'terminal': not successful, 'analysis_complete': not successful, 'methods': list(METHODS), 'formal_base': 'hnm',
        'reason': 'fixed_all_eight_train_calibration_unavailable',
        'planned_train_recordings_per_method': 120, 'planned_train_speakers_per_method': 40,
        'train_failure_counts': {method: sum(row['method'] == method for row in issues) for method in METHODS},
        'train_failures': issues, 'successful_train_sources': sources,
        'calibration_cohort': read(OUT / 'calibration-cohort.json'),
        'input_contract_sha256': sha256(TRAIN / 'input-contract.json'),
        'estimands': {metric: {'definition': DEFINITIONS[metric], 'higher_is_better': True,
            'unit': 'correlation' if metric == 'rating_spearman' else 'fraction',
            'methods': {method: {'status': 'not_applicable',
                'reason': 'fixed_all_eight_train_calibration_unavailable',
                'value': None, 'rank': None, 'ci95': None,
                'valid_replicates': 0, 'undefined_replicates': 0,
                'hnm_difference': {'value': None, 'ci95': None, 'valid_replicates': 0,
                                   'undefined_replicates': 0}} for method in METHODS}}
            for metric in METRICS}, 'finished_at_utc': now()}
    if not (OUT / 'results.json').exists() or not read(OUT / 'results.json').get('analysis_complete'):
        write_json(OUT / 'results.json', result)
        write_json(PUBLIC / 'results.json', result)
    return successful


def cohort(pairs):
    recordings = {row[f'sample_{role}'] for row in pairs for role in ('a', 'b')}
    speakers = {row[f'{role}_speaker'] for row in pairs for role in ('a', 'b')}
    return {'pairs': len(pairs), 'recordings': len(recordings), 'speakers': len(speakers),
            'b_anchors': len({row['sample_b'] for row in pairs}),
            'b_speakers': len({row['b_speaker'] for row in pairs})}


def store_result(result, methods):
    result['analysis_complete'] = True
    result['calibration_cohort_sha256'] = sha256(OUT / 'calibration-cohort.json')
    if len(methods) != len(METHODS):
        result.update(ranking=False, method_set=methods,
                      comparison_scope='fixed_successful_calibration_subset_auxiliary')
        for estimand in result['estimands'].values():
            for row in estimand['methods'].values():
                row['rank'] = None
        primary = read(OUT / 'results.json')
        if primary['status'] != 'incomplete':
            raise ValueError('全8欠測の主群と補助群の境界が不一致')
        primary.update(auxiliary_successful_methods=result, analysis_complete=True,
                       terminal=True, finished_at_utc=now(),
                       cohort={'planned': result['cohort']['planned'],
                               'common': cohort([]), 'planned_complete': False,
                               'reason': 'one_or_more_fixed_train_calibrations_failed'})
        result = primary
    write_json(PUBLIC / 'results.json', result)
    write_json(OUT / 'results.json', result)


def execute():
    methods = train_readiness()
    if methods is False:
        return False
    if not methods:
        return True
    loaded = load_features(methods)
    if loaded is None:
        return False
    selection, states, data, records, exclusions, common = loaded
    sources = [Path(__file__), ROOT / 'scripts/all_metrics_human_statistics.py',
        ROOT / 'scripts/all_metrics_human_data.py', ROOT / 'scripts/all_metrics_features_common.py',
        ROOT / 'scripts/all_metrics_features_support.py',
        ROOT / 'scripts/all_metrics_common.py', PLAN]
    contract = {'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        'selection_sha256': sha256(HUMAN / 'selection.json'),
        'inputs_sha256': sha256(HUMAN / 'inputs.json'), 'feature_records': records,
        'train_moment_sources': train_source_index(methods),
        'calibration_cohort_sha256': sha256(OUT / 'calibration-cohort.json'),
        'methods': list(methods), 'seed': 20261014, 'replicates': 2000,
        'runtime': {'python': sys.version, 'numpy': np.__version__},
        'common_pairs': [[row['sample_a'], row['sample_b']] for row in common]}
    freeze(OUT / 'contract.json', contract)
    if (OUT / 'results.json').exists() and read(OUT / 'results.json').get('analysis_complete'):
        previous = read(OUT / 'results.json')
        previous = previous.get('auxiliary_successful_methods', previous)
        for method, expected in previous.get('calibration_artifacts', {}).items():
            path = OUT / 'calibration' / f'{method}.npz'
            if sha256(path) != expected['npz_sha256'] or sha256(path.with_suffix('.json')) != expected['metadata_sha256']:
                raise ValueError('再利用する固定尺度artifact hash不一致')
        return True
    if not common:
        result = {'status': 'no_common_pairs', 'methods': list(methods), 'formal_base': 'hnm',
            'cohort': {'id': selection['id'], 'planned': cohort(selection['pairs']), 'common': cohort(common),
                       'planned_complete': False, 'extraction_states': states, 'exclusions': exclusions},
            'estimands': {metric: {'definition': DEFINITIONS[metric], 'higher_is_better': True,
                'unit': 'correlation' if metric == 'rating_spearman' else 'fraction',
                'methods': {method: {'status': 'not_applicable', 'reason': 'no_common_pairs',
                    'value': None, 'rank': None, 'ci95': None, 'valid_replicates': 0,
                    'undefined_replicates': 0, 'hnm_difference': {'value': None, 'ci95': None,
                        'valid_replicates': 0, 'undefined_replicates': 0}}
                    for method in methods}} for metric in METRICS},
            'uncertainty': UNCERTAINTY,
            'contract_sha256': sha256(OUT / 'contract.json'), 'finished_at_utc': now()}
        store_result(result, methods)
        return True
    distances, calibrations = [], {}
    for method in methods:
        standard, calibrations[method] = scale(method)
        values = [float(np.linalg.norm((data[method][row['sample_a']]-data[method][row['sample_b']])/standard))
                  for row in common]
        if not np.isfinite(values).all():
            raise ValueError('#13距離が非有限')
        distances.append(values)
    distances = np.asarray(distances).T
    point, arrays, support, anchors, chance = bootstrap(common, distances)
    bootstrap_path = OUT / 'node-bootstrap.npz'
    save_npz(bootstrap_path, **arrays)
    raw = [{**row, 'distances': dict(zip(methods, values.tolist()))}
           for row, values in zip(common, distances)]
    write_json(OUT / 'raw-pairs.json', raw)
    write_json(OUT / 'raw-neighbors.json', dict(zip(methods, anchors)))
    result = {'status': 'measured', 'methods': list(methods), 'formal_base': 'hnm',
        'cohort': {'id': selection['id'], 'planned': cohort(selection['pairs']), 'common': cohort(common),
            'planned_complete': len(common) == len(selection['pairs']) and all(
                state.get('measured', 0) == selection['recording_count'] for state in states.values()),
            'extraction_states': states, 'exclusions': exclusions,
            'scope': 'ASVspoof2019 bonafide 105録音・84対・21anchorの固定複数評定者部分群'},
        'estimands': {}, 'contract_sha256': sha256(OUT / 'contract.json'),
        'calibration_artifacts': {method: {'npz_sha256': calibrations[method]['sha256'],
            'metadata_sha256': sha256(OUT / 'calibration' / f'{method}.json')} for method in methods},
        'bootstrap': {'path': str(bootstrap_path), 'sha256': sha256(bootstrap_path),
                      'seed': 20261014, 'replicates': 2000, 'support': support,
                      'array_axes': ['replicate', 'method', 'metric']},
        'uncertainty': UNCERTAINTY,
        'limits': ['原音の特徴距離と既存の声同一性評定との一致であり、再合成MOSや総合品質ではない',
                   '元corpusはVCTK由来。既存学習型vocoderの訓練音声/話者重複可能性を排除していない',
                   '音声は公式録音IDとlossless FLACを結合。Web試聴player PCMそのものの一致は別検証なし'],
        'citations': selection['citations'], 'finished_at_utc': now()}
    for metric_index, metric in enumerate(METRICS):
        points = dict(zip(methods, point[:, metric_index]))
        ranking = ranks(points, methods)
        method_rows = {}
        for index, method in enumerate(methods):
            value = points[method]
            boot = arrays['values'][:, index, metric_index]
            baseline = points.get('hnm', float('nan'))
            delta = (boot-arrays['values'][:, methods.index('hnm'), metric_index] if 'hnm' in methods
                     else np.full_like(boot, np.nan))
            method_rows[method] = {'status': 'measured' if np.isfinite(value) else 'undefined',
                'value': float(value) if np.isfinite(value) else None, 'rank': ranking[method], **ci(boot),
                'hnm_difference': {'value': float(value-baseline) if np.isfinite(value-baseline) else None,
                                   **ci(delta)}}
            if metric == 'rated_neighbor_top1':
                method_rows[method]['random_candidate_expectation'] = chance[index] if np.isfinite(chance[index]) else None
                if support['point_support']['anchors'] == 0:
                    method_rows[method].update(status='not_applicable', reason='no_anchor_with_two_distinct_a_recordings')
            elif not np.isfinite(value):
                method_rows[method]['reason'] = 'fewer_than_three_supported_pairs_or_constant_ranks'
        result['estimands'][metric] = {'definition': DEFINITIONS[metric], 'higher_is_better': True,
            'unit': 'correlation' if metric == 'rating_spearman' else 'fraction', 'methods': method_rows}
    provenance = {'input_contract': read(HUMAN / 'input-contract.json'),
        'feature_records': records, 'fixed_train_calibrations': calibrations,
        'feature_contracts': {method: read(HUMAN / 'feature-contracts' / f'{method}.json') for method in methods},
        'ranking_contract_sha256': sha256(OUT / 'contract.json')}
    write_json(PUBLIC / 'feature-and-scale-provenance.json', provenance)
    write_json(PUBLIC / 'pair-distances.json', raw)
    write_json(PUBLIC / 'neighbors.json', dict(zip(methods, anchors)))
    store_result(result, methods)
    logging.info('正式#13共通順位完了: %s', result['cohort']['common'])
    return True


if __name__ == '__main__':
    raise SystemExit(run_cli(lambda: 0 if execute() else 2, 'all-metrics-human-rankings'))
