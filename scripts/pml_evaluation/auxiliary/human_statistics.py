"""固定された人間評定対のweighted rankと話者node集計。"""
from __future__ import annotations

from collections import defaultdict
import math

import numpy as np

METRICS = ('rating_spearman', 'rated_neighbor_top1')


def tied(values, reference):
    return np.isclose(values, reference, atol=1e-12, rtol=1e-9)


def midranks(values, weights):
    """昇順の各群の最小値とのtieを使い、群の質量中央を順位にする。"""
    order = np.argsort(values, kind='stable')
    answer = np.empty(len(values), dtype=float)
    start, previous_mass = 0, 0.0
    while start < len(order):
        end = start + 1
        while end < len(order) and tied(values[order[end]], values[order[start]]):
            end += 1
        group = order[start:end]
        mass = weights[group].sum()
        answer[group] = previous_mass + mass/2
        previous_mass += mass
        start = end
    return answer


def spearman(ratings, similarities, weights):
    support = weights > 0
    if support.sum() < 3:
        return float('nan')
    weights = weights[support]
    x = midranks(ratings[support], weights)
    y = midranks(similarities[support], weights)
    x -= np.average(x, weights=weights)
    y -= np.average(y, weights=weights)
    covariance = np.sum(weights*x*y)
    denominator = np.sqrt(np.sum(weights*x*x)*np.sum(weights*y*y))
    return float(covariance/denominator) if denominator > 0 else float('nan')


def neighbors(pairs, ratings, distances, multiplicities, lookup, detailed=False):
    anchors = defaultdict(list)
    for index, row in enumerate(pairs):
        anchors[row['sample_b']].append(index)
    by_speaker, chance_by_speaker, rows = defaultdict(list), defaultdict(list), []
    for anchor, columns in sorted(anchors.items()):
        speaker = pairs[columns[0]]['b_speaker']
        if multiplicities[lookup[speaker]] == 0:
            continue
        weights = np.asarray([1 if pairs[i]['a_speaker'] == speaker
                              else multiplicities[lookup[pairs[i]['a_speaker']]] for i in columns], dtype=float)
        support = weights > 0
        columns = np.asarray(columns)[support]
        weights = weights[support]
        if len({pairs[i]['sample_a'] for i in columns}) < 2:
            continue
        best_human = tied(ratings[columns], ratings[columns].max())
        nearest = tied(distances[columns], distances[columns].min())
        value = float(np.average(best_human[nearest], weights=weights[nearest]))
        chance = float(np.average(best_human, weights=weights))
        by_speaker[speaker].append(value)
        chance_by_speaker[speaker].append(chance)
        if detailed:
            rows.append({'sample_b': anchor, 'b_speaker': speaker, 'value': value,
                'random_candidate_expectation': chance, 'candidate_count': len(columns),
                'nearest_samples_a': [pairs[i]['sample_a'] for i in columns[nearest]],
                'highest_rated_samples_a': [pairs[i]['sample_a'] for i in columns[best_human]]})
    speakers = sorted(by_speaker)
    if speakers:
        weights = [multiplicities[lookup[s]] for s in speakers]
        value = float(np.average([np.mean(by_speaker[s]) for s in speakers], weights=weights))
        chance = float(np.average([np.mean(chance_by_speaker[s]) for s in speakers], weights=weights))
    else:
        value = chance = float('nan')
    return value, chance, {'anchors': sum(map(len, by_speaker.values())),
                           'b_speakers': len(speakers)}, rows


def estimate(pairs, distance_matrix, multiplicities, speakers, detailed=False):
    lookup = {speaker: index for index, speaker in enumerate(speakers)}
    a = np.asarray([lookup[row['a_speaker']] for row in pairs])
    b = np.asarray([lookup[row['b_speaker']] for row in pairs])
    weights = multiplicities[a]*np.where(a == b, 1, multiplicities[b])
    ratings = np.asarray([row['human_rating'] for row in pairs])
    scores, anchor_rows, chance_values = [], [], []
    top_support = None
    for distances in distance_matrix.T:
        rho = spearman(ratings, -distances, weights)
        top1, chance, support, rows = neighbors(pairs, ratings, distances, multiplicities, lookup, detailed)
        if top_support is not None and top_support != support:
            raise ValueError('方式間の近傍候補支持が不一致')
        top_support = support
        scores.append((rho, top1))
        anchor_rows.append(rows)
        chance_values.append(chance)
    positive = weights > 0
    used = {row[f'{role}_speaker'] for row, ok in zip(pairs, positive) if ok for role in ('a', 'b')}
    support = {'pairs': int(positive.sum()), 'speakers': len(used), **top_support}
    return np.asarray(scores), support, anchor_rows, chance_values


def bootstrap(pairs, distances):
    speakers = sorted({row[f'{role}_speaker'] for row in pairs for role in ('a', 'b')})
    size = len(speakers)
    rng = np.random.default_rng(20261014)
    draws = rng.integers(0, size, size=(2000, size))
    multiplicities = np.stack([np.bincount(row, minlength=size) for row in draws])
    point, support, anchors, chance = estimate(pairs, distances, np.ones(size, dtype=int), speakers, True)
    replicates, supports = [], []
    for draw in multiplicities:
        values, used, _, _ = estimate(pairs, distances, draw, speakers)
        replicates.append(values)
        supports.append([used[key] for key in ('pairs', 'speakers', 'anchors', 'b_speakers')])
    arrays = {'speaker_multiplicities': multiplicities, 'values': np.asarray(replicates),
              'support': np.asarray(supports)}
    return point, arrays, {'speakers': speakers, 'point_support': support,
        'support_columns': ['pairs', 'speakers', 'anchors', 'b_speakers'],
        'metric_columns': list(METRICS)}, anchors, chance


def ci(values):
    finite = values[np.isfinite(values)]
    return {'ci95': np.quantile(finite, [.025, .975]).tolist() if len(finite) else None,
        'valid_replicates': len(finite), 'undefined_replicates': len(values)-len(finite)}


def ranks(points, methods):
    result = {method: None for method in methods}
    previous, rank = None, None
    available = [method for method in methods if np.isfinite(points[method])]
    for index, method in enumerate(sorted(available, key=lambda name: -points[name]), 1):
        value = points[method]
        if previous is None or not math.isclose(value, previous, abs_tol=1e-12, rel_tol=1e-9):
            previous, rank = value, index
        result[method] = rank
    return result
