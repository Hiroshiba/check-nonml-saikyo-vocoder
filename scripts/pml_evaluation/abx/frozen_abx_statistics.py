"""新runのABX層平均・X話者macro・明示nestedと話者node bootstrap。"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

CONDITIONS = ('within_speaker', 'across_speaker')
ESTIMANDS = ('flat_stratum', 'x_speaker_macro', 'nested_phone_context')
SEED, REPLICATES = 20261014, 2000


def make_strata(triplets, errors, items):
    groups = defaultdict(list)
    for index, row in enumerate(triplets):
        a, b, x = (items[row[role]] for role in ('a', 'b', 'x'))
        key = (row['condition'], a['phone'], b['phone'], a['context'], a['speaker'], x['speaker'])
        groups[key].append(index)
    keys = sorted(groups)
    values = np.stack([errors[groups[key]].mean(axis=0) for key in keys])
    counts = np.asarray([len(groups[key]) for key in keys])
    return keys, values, counts


def estimate(keys, values, counts, speakers, multiplicities):
    lookup = dict(zip(speakers, multiplicities))
    output = np.full((len(CONDITIONS), len(ESTIMANDS), values.shape[1]), np.nan)
    support = np.zeros((len(CONDITIONS), 4), dtype=int)
    for condition_index, condition in enumerate(CONDITIONS):
        indices = [i for i, key in enumerate(keys)
                   if key[0] == condition and lookup[key[4]] > 0 and lookup[key[5]] > 0]
        if not indices:
            continue
        weights = np.asarray([lookup[keys[i][4]] * (1 if keys[i][4] == keys[i][5]
                                                   else lookup[keys[i][5]]) for i in indices])
        output[condition_index, 0] = np.average(values[indices], axis=0, weights=weights)
        by_x, by_context = defaultdict(list), defaultdict(list)
        for index in indices:
            key = keys[index]
            by_x[key[5]].append(index)
            by_context[key[1:4]].append(index)
        x_values, x_weights = [], []
        for speaker, group in sorted(by_x.items()):
            # 内側のA multiplicityと外側のX multiplicityを分離する。
            inner = [1 if keys[i][4] == speaker else lookup[keys[i][4]] for i in group]
            x_values.append(np.average(values[group], axis=0, weights=inner))
            x_weights.append(lookup[speaker])
        output[condition_index, 1] = np.average(x_values, axis=0, weights=x_weights)
        by_phone = defaultdict(list)
        for key, group in sorted(by_context.items()):
            weights = [lookup[keys[i][4]] * (1 if keys[i][4] == keys[i][5]
                                            else lookup[keys[i][5]]) for i in group]
            by_phone[key[:2]].append(np.average(values[group], axis=0, weights=weights))
        output[condition_index, 2] = np.mean([np.mean(rows, axis=0) for rows in by_phone.values()], axis=0)
        used = {keys[i][role] for i in indices for role in (4, 5)}
        support[condition_index] = [len(indices), int(counts[indices].sum()), len(used), len(by_x)]
    return output, support


def bootstrap(keys, values, counts):
    point = np.full((len(CONDITIONS), len(ESTIMANDS), values.shape[1]), np.nan)
    arrays = {'values': np.full((REPLICATES, *point.shape), np.nan),
              'support': np.zeros((REPLICATES, len(CONDITIONS), 4), dtype=int)}
    metadata = {}
    for c, condition in enumerate(CONDITIONS):
        indices = [i for i, key in enumerate(keys) if key[0] == condition]
        selected = [keys[i] for i in indices]
        speakers = sorted({key[role] for key in selected for role in (4, 5)})
        size = len(speakers)
        if not size:
            metadata[condition] = {'speakers': [], 'point_support': [0, 0, 0, 0], 'drawn_replicates': 0}
            arrays[f'{condition}_speaker_multiplicities'] = np.empty((REPLICATES, 0), dtype=int)
            continue
        fitted, support = estimate(selected, values[indices], counts[indices], speakers, np.ones(size, dtype=int))
        point[c] = fitted[c]
        draws = np.random.default_rng(SEED).integers(0, size, size=(REPLICATES, size))
        multiplicities = np.stack([np.bincount(row, minlength=size) for row in draws])
        arrays[f'{condition}_speaker_multiplicities'] = multiplicities
        for r, draw in enumerate(multiplicities):
            result, used = estimate(selected, values[indices], counts[indices], speakers, draw)
            arrays['values'][r, c], arrays['support'][r, c] = result[c], used[c]
        metadata[condition] = {'speakers': speakers, 'point_support': support[c].tolist(), 'drawn_replicates': REPLICATES}
    return point, arrays, {
        'by_condition': metadata,
        'support_columns': ['strata', 'triplets', 'speakers', 'x_speakers'],
        'conditions': list(CONDITIONS), 'estimands': list(ESTIMANDS),
        'array_axes': ['replicate', 'condition', 'estimand', 'method']}
