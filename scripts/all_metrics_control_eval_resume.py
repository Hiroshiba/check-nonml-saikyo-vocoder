"""凍結済みcontrol測定を保存層等価性照合の下で再開する運用入口。"""
from __future__ import annotations

import argparse
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_control_eval import CONDITIONS, applicable, contract, evaluate, source_names
from all_metrics_control_eval_equivalence import verified_record
from all_metrics_resources import shared_stage
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def source_finalized(spec, method, condition):
    if method in METHODS[:2] or method == 'facodec' or not applicable(method, condition):
        return True
    folder = RUN / 'native' / method / spec['id']
    progress = folder / 'case-progress.json'
    if not progress.exists() or not read(progress).get('finished_at_utc'):
        return False
    names = source_names(condition)
    for name in names:
        path = folder / f'{name}.json'
        if path.exists() and path.stat().st_size >= 1024 * 1024:
            value = read(path)
            if 'storage_compaction' not in value and ('arrays' in value.get('feature_artifact', {})
                                                     or 'structure' in value.get('feature_artifact', {})):
                return False
    return True


@shared_stage('control-evaluation-resume')
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True, choices=range(12))
    args = parser.parse_args()
    path = RUN / 'controls/contract.json'
    freeze(path, contract())
    signature = sha256(path)
    rows, deferred, checked = [], [], set()
    for spec in read(RUN / 'inputs.json')[args.batch * 10:(args.batch + 1) * 10]:
        for method in METHODS:
            for condition in CONDITIONS:
                saved = RUN / 'controls/measurements' / f'{spec["id"]}__{method}__{condition}.json'
                previous = read(saved) if saved.exists() else None
                if previous and previous['status'] in ('measured', 'not_applicable', 'unsupported'):
                    if previous['contract_sha256'] != signature:
                        raise ValueError('正式control測定の科学契約が変わりました')
                    for source in previous.get('input_records', []):
                        key = source['path'], source['sha256']
                        if key not in checked:
                            verified_record(*key, RUN / 'controls/storage-equivalence')
                            checked.add(key)
                    rows.append(previous)
                elif source_finalized(spec, method, condition):
                    rows.append(evaluate(spec, method, condition, signature, True))
                else:
                    if previous:
                        rows.append(previous)
                    deferred.append({'case': spec['id'], 'method': method, 'condition': condition,
                                     'reason': 'native case finished/metadata compaction completion pending'})
        write_json(RUN / f'controls/resume-batch-{args.batch:02d}.json', {'updated_at_utc': now(), 'rows': rows,
            'deferred': deferred, 'operational_source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in
                [Path(__file__), ROOT / 'scripts/all_metrics_control_eval_equivalence.py']}})
    return int(bool(deferred) or any(row['status'] in ('failed', 'upstream_failed') or row['status'].startswith('pending') for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-control-resume'))
