"""科学契約を変えず、正式VCTK batch内の明示部分を同じ入口で再開する。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
import traceback

from all_metrics_common import METHODS, ROOT, freeze, now, read
from all_metrics_vctk_inputs import VCTK_RUN
from vocoderbench.quality_core import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=METHODS, required=True)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--case-start', type=int, required=True)
    parser.add_argument('--case-count', type=int, default=2)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.batch < 2 or not 0 <= args.case_start < 10 or not 1 <= args.case_count <= 10:
        raise ValueError('正式batch内の実行分割を指定してください')
    batch_path = VCTK_RUN / 'input-batches' / f'{args.batch:02d}.json'
    batch = read(batch_path)
    subset = batch[args.case_start:args.case_start + args.case_count]
    if not subset:
        raise ValueError('空の実行部分は処理しません')
    operation = {'schema_version': 1, 'scope': '固定した正式部分集合のprocess分割のみ。科学設定・入力・seed不変。',
                 'wrapper_source_sha256': sha256(Path(__file__)),
                 'original_entrypoint_sha256': sha256(Path(__file__).parent / 'all_metrics_vctk_synthesis.py'),
                 'input_contract_sha256': sha256(VCTK_RUN / 'input-contract.json'),
                 'routing': 'Only the original module-local batch-manifest read is sliced; all other reads and case_run unchanged.',
                 'model_initialization': 'One initialization per declared subset; timings include concurrent workloads.'}
    freeze(VCTK_RUN / 'resume-operation-contract.json', operation)
    path = VCTK_RUN / 'resume-executions' / f'{args.method}-{args.batch:02d}-{args.case_start:02d}-{time.time_ns()}.json'
    row = {'method': args.method, 'batch': args.batch, 'case_start': args.case_start,
           'case_count': len(subset), 'case_ids': [s['id'] for s in subset],
           'batch_manifest_path': str(batch_path), 'batch_manifest_sha256': sha256(batch_path),
           'subset_input_sha256': {s['id']: s['sha256'] for s in subset},
           'operation_contract_sha256': sha256(VCTK_RUN / 'resume-operation-contract.json'),
           'started_at_utc': now(), 'completed': False}
    write_json(path, row)
    import all_metrics_vctk_synthesis as original
    from all_metrics_synthesis import completed
    scientific_path = VCTK_RUN / 'synthesis-contracts' / f'{args.method}.json'
    if scientific_path.exists():
        scientific = read(scientific_path)
        for relative, expected in scientific['source_sha256'].items():
            if sha256(ROOT / relative) != expected:
                raise ValueError(f'科学契約の凍結source不一致: {relative}')
        signature = sha256(scientific_path)
        if all(completed(VCTK_RUN / 'native' / args.method / s['id'], ['unedited'], signature, True)
               for s in subset):
            row.update(completed=True, returncode=0, finished_at_utc=now(),
                       scientific_contract_sha256=signature, already_complete=True)
            write_json(path, row)
            return 0
    original_read, original_argv = original.read, sys.argv

    def selected_read(source):
        if Path(source).resolve() == batch_path.resolve():
            return subset
        return original_read(source)

    original.read = selected_read
    sys.argv = [str(Path(__file__).parent / 'all_metrics_vctk_synthesis.py'), '--method', args.method,
                '--batch', str(args.batch)] + (['--retry-failed'] if args.retry_failed else [])
    try:
        from vocoderbench.logging_utils import run_cli
        row['returncode'] = run_cli(original.main, 'all-metrics-vctk-resume')
        row['completed'] = True
        return row['returncode']
    except BaseException:
        row['error'] = traceback.format_exc()
        raise
    finally:
        original.read, sys.argv = original_read, original_argv
        row['finished_at_utc'] = now()
        if scientific_path.exists():
            row['scientific_contract_sha256'] = sha256(scientific_path)
        write_json(path, row)


if __name__ == '__main__':
    raise SystemExit(main())
