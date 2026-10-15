"""全8主群と固定成功方式補助群を混ぜずにABXの値・区間を保存する。"""
from __future__ import annotations

import numpy as np

from all_metrics_common import METHODS
from all_metrics_features_common import save_npz
from all_metrics_features_support import number, ranked
from all_metrics_features_abx_statistics import (
    CONDITIONS, ESTIMANDS, REPLICATES, SEED, bootstrap, make_strata,
)
from vocoderbench.quality_core import sha256, write_json


def cohort(triplets, items):
    used = {row[role] for row in triplets for role in ('a', 'b', 'x')}
    return {'triplets': len(triplets), 'tokens': len(used),
            'recordings': len({items[i]['recording_id'] for i in used}),
            'speakers': len({items[i]['speaker'] for i in used})}


def summarize(folder, planned, errors, items, methods=METHODS, ranking=True):
    indices = [METHODS.index(method) for method in methods]
    keep = np.isfinite(errors[:, indices]).all(axis=1)
    common = [row for row, valid in zip(planned, keep) if valid]
    if common:
        keys, values, counts = make_strata(common, errors[keep], items)
        point, arrays, support = bootstrap(keys, values, counts)
    else:
        keys, values, counts = [], np.empty((0, len(METHODS))), np.empty(0, dtype=int)
        point = np.full((len(CONDITIONS), len(ESTIMANDS), len(METHODS)), np.nan)
        arrays = {'values': np.empty((0, *point.shape))}
        support = {'by_condition': {}, 'reason': 'no_common_triplets'}
    save_npz(folder / 'speaker-bootstrap.npz', **arrays)
    write_json(folder / 'strata.json', [{'stratum': list(key), 'triplets': int(count),
        'methods': {method: number(row[METHODS.index(method)]) for method in methods}}
        for key, row, count in zip(keys, values, counts)])
    write_json(folder / 'common-triplets.json', common)
    estimands, cohorts = {}, {}
    for c, condition in enumerate(CONDITIONS):
        expected = [row for row in planned if row['condition'] == condition]
        selected = [row for row in common if row['condition'] == condition]
        cohorts[condition] = {'planned': cohort(expected, items), 'common': cohort(selected, items),
                              'planned_complete': len(expected) == len(selected)}
        for e, estimand in enumerate(ESTIMANDS):
            rows = ranked(point[c, e], arrays['values'][:, c, e])
            if not ranking:
                rows = {method: {**rows[method], 'rank': None} for method in methods}
            estimands[f'{condition}/{estimand}'] = {'unit': 'error_fraction', 'higher_is_better': False,
                'methods': rows, 'cohort': cohorts[condition]}
    return {'status': 'measured' if common else 'no_common_triplets', 'method_set': list(methods),
        'ranking': ranking, 'estimands': estimands, 'cohorts': cohorts,
        'bootstrap': {**support, 'sha256': sha256(folder / 'speaker-bootstrap.npz'),
                      'path': str(folder / 'speaker-bootstrap.npz'), 'method_axis': list(METHODS),
                      'replicates': len(arrays['values']), 'requested_replicates': REPLICATES, 'seed': SEED},
        'strata_sha256': sha256(folder / 'strata.json'),
        'common_triplets_sha256': sha256(folder / 'common-triplets.json'),
        'exclusion_counts_by_method': {method: int((~np.isfinite(errors[:, METHODS.index(method)])).sum())
                                       for method in methods}, 'exclusion_counts_can_overlap': True,
        'excluded_triplets': [{'triplet': row, 'failed_methods': [method for method in methods
            if not np.isfinite(errors[i, METHODS.index(method)])]} for i, row in enumerate(planned) if not keep[i]],
        'triplet_micro_auxiliary': {condition: {
            method: float(errors[keep, METHODS.index(method)][[row['condition'] == condition for row in common]].mean())
                    if any(row['condition'] == condition for row in common) else None
            for method in methods} for condition in CONDITIONS}}
