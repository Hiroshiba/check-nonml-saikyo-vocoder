"""全10区間の確定値を、軸別・話者等重み・対応した支持集合で集約する。"""
from collections import Counter, defaultdict
import math
from pathlib import Path

import numpy as np

from .chunk_checkpoint import assemble
from .chunk_contracts import ContractError, freeze, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli

SEED = 20261014
REPLICATES = 2000


def competition_ranks(values, direction):
    ranks = {method: None for method in values}
    if direction == 'diagnostic':
        return ranks
    ordered = sorted((m for m, value in values.items() if value is not None),
                     key=lambda m: values[m], reverse=direction == 'higher')
    anchor, rank = None, None
    for position, method in enumerate(ordered, 1):
        value = values[method]
        if anchor is None or not math.isclose(value, anchor, abs_tol=1e-12, rel_tol=1e-9):
            anchor, rank = value, position
        ranks[method] = rank
    return ranks


def summarize(indexed, members, cases, speakers, direction, base=None):
    """録音内差→話者内平均→話者等重み。全方式に同じ話者drawを使う。"""
    by_speaker = defaultdict(list)
    for case in sorted(cases):
        by_speaker[speakers[case]].append(case)
    ordered_speakers = sorted(by_speaker)
    matrix = np.array([[np.mean([indexed[m, c]['value'] for c in by_speaker[s]])
                        for m in members] for s in ordered_speakers], dtype=np.float64)
    values = matrix.mean(axis=0) if ordered_speakers else np.full(len(members), np.nan)
    bootstrap = None
    if len(ordered_speakers) >= 2:
        draws = np.random.default_rng(SEED).integers(
            0, len(ordered_speakers), (REPLICATES, len(ordered_speakers)))
        bootstrap = matrix[draws].mean(axis=1)
    means = {m: float(v) if np.isfinite(v) else None for m, v in zip(members, values, strict=True)}
    ranks = competition_ranks(means, direction)
    base_index = members.index(base) if base in members else None
    results = {}
    for i, method in enumerate(members):
        delta = None
        if base_index is not None:
            delta = {'value': float(values[i] - values[base_index]) if ordered_speakers else None,
                     'ci95': np.quantile(bootstrap[:, i] - bootstrap[:, base_index], [.025, .975]).tolist()
                     if bootstrap is not None else None,
                     'definition': '同じ録音の方式−現PML→話者内平均→話者等重み'}
        results[method] = {
            'value': means[method], 'rank': ranks[method],
            'ci95': np.quantile(bootstrap[:, i], [.025, .975]).tolist() if bootstrap is not None else None,
            'status': 'measured' if ordered_speakers else 'no_common_valid_recordings',
            'valid_recordings': len(cases), 'valid_speakers': len(ordered_speakers),
            'speaker_means': {s: float(matrix[j, i]) for j, s in enumerate(ordered_speakers)},
            'pml_difference': delta,
        }
    return {'methods': results, 'case_ids': sorted(cases), 'speaker_ids': ordered_speakers,
            'common_valid_recordings': len(cases), 'common_valid_speakers': len(ordered_speakers),
            'bootstrap_replicates': REPLICATES if bootstrap is not None else 0}


def aggregate(plan_path, checkpoint_paths):
    plan_sha = sha(plan_path)
    plan = validate_plan(read(plan_path))
    terminal = assemble(plan_path, checkpoint_paths)
    if terminal['run_plan_sha256'] != plan_sha:
        raise ContractError('集約中に計画が変更されました')
    cases = {r['case'] for r in plan['cases']}
    speakers = {r['case']: r['speaker'] for r in plan['cases']}
    grouped = defaultdict(list)
    for row in terminal['rows']:
        grouped[row['axis'], row['condition']].append(row)
    axes = []
    for axis in plan['axes']:
        rows = grouped[axis['id'], axis['condition']]
        indexed = {(r['method'], r['case']): r for r in rows}
        unsupported = [m for m in axis['methods'] if all(indexed[m, c]['status'] == 'unsupported' for c in cases)]
        members = [m for m in axis['methods'] if m != 'original' and m not in unsupported]
        valid = {m: {r['case'] for r in rows if r['method'] == m and r['status'] == 'measured'}
                 for m in axis['methods']}
        common = cases.intersection(*(valid[m] for m in members)) if members else set()
        states, own = {}, {}
        for method in axis['methods']:
            selected = [r for r in rows if r['method'] == method]
            states[method] = {'planned_recordings': len(cases), 'measured_recordings': len(valid[method]),
                              'status_counts': dict(Counter(r['status'] for r in selected)),
                              'reason_counts': dict(Counter(r['reason_code'] for r in selected))}
            own[method] = summarize(indexed, [method], valid[method], speakers, 'diagnostic')['methods'][method]
        paired = {}
        base = plan['formal_base']
        if base in members:
            for method in members:
                if method != base:
                    paired[method] = summarize(indexed, [base, method], valid[base] & valid[method],
                                               speakers, 'diagnostic', base)
        axes.append({**axis, 'method_states': states,
                     'comparison_methods': members, 'structurally_unsupported_methods': unsupported,
                     'common_support': summarize(indexed, members, common, speakers, axis['direction'], base),
                     'pairwise_pml': paired, 'own_support_unranked': own})
    if sha(plan_path) != plan_sha:
        raise ContractError('集約中に計画が変更されました')
    return {'schema_version': 2, 'validation_state': 'validated_end',
            'run_plan_sha256': plan_sha, 'chunk_sources': terminal['chunk_sources'],
            'formal_base': plan['formal_base'], 'formal_base_version': plan['formal_base_version'],
            'candidate': plan['candidate'], 'planned_recordings': 120, 'planned_speakers': 40,
            'bootstrap': {'seed': SEED, 'replicates': REPLICATES, 'unit': 'speaker',
                          'limitation': '話者構成の記述的95%区間。2話者未満は区間なし。多重比較未補正。'},
            'ranking_definition': '軸ごとの宣言方式の共通録音上で順位。全120件unsupportedの方式のみ除外し明示。失敗方式は除外しない。原音は参考値。総合点・平均順位なし。',
            'axes': axes, 'adoption_decision': None}


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze(args.output, aggregate(args.plan, args.checkpoints))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-aggregate'))
