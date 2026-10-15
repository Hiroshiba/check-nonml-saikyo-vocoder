"""固定ViSQOL科学入口を一つの正式caseごとのprocessへ分割する運用wrapper。"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
import traceback

from all_metrics_common import freeze, now, read
from all_metrics_vctk_inputs import VCTK_RUN
from vocoderbench.quality_core import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--case-start', type=int, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    args = parser.parse_args()
    batch_path = VCTK_RUN / 'input-batches' / f'{args.batch:02d}.json'
    batch = read(batch_path)
    if not 0 <= args.case_start < len(batch):
        raise ValueError('正式batch内のcase番号が必要です')
    subset = batch[args.case_start:args.case_start + 1]
    operation = {'schema_version': 1, 'scope': '同じ品質科学契約のcase単位process分割。初回+1反復/threads2は不変。',
                 'wrapper_source_sha256': sha256(Path(__file__)),
                 'original_entrypoint_sha256': sha256(Path(__file__).parent / 'all_metrics_vctk_quality.py'),
                 'input_contract_sha256': sha256(VCTK_RUN / 'input-contract.json'),
                 'routing': 'Only the original module-local batch-manifest read is sliced; scientific evaluation unchanged.',
                 'batch_footer': 'Per-case footer saved separately; raw per-case/method paths unchanged.'}
    freeze(VCTK_RUN / 'quality-resume-operation-contract.json', operation)
    path = VCTK_RUN / 'quality-resume-executions' / f'{args.batch:02d}-{args.case_start:02d}-{time.time_ns()}.json'
    row = {'batch': args.batch, 'case_index': args.case_start, 'case': subset[0]['id'],
           'batch_manifest_sha256': sha256(batch_path), 'started_at_utc': now(),
           'operation_contract_sha256': sha256(VCTK_RUN / 'quality-resume-operation-contract.json')}
    write_json(path, row)
    import all_metrics_vctk_quality as original
    original_read, original_write, original_argv = original.read, original.write_json, sys.argv

    def selected_read(source):
        return subset if Path(source).resolve() == batch_path.resolve() else original_read(source)

    def routed_write(destination, value):
        if Path(destination).resolve() == (VCTK_RUN / 'quality-batches' / f'{args.batch:02d}.json').resolve():
            destination = VCTK_RUN / 'quality-case-batches' / f'{args.batch:02d}-{args.case_start:02d}.json'
        return original_write(destination, value)

    original.read, original.write_json = selected_read, routed_write
    sys.argv = [str(Path(__file__).parent / 'all_metrics_vctk_quality.py'), '--batch', str(args.batch),
                '--assets', str(args.assets.resolve())]
    try:
        from vocoderbench.logging_utils import run_cli
        row['returncode'] = run_cli(original.main, 'all-metrics-vctk-quality-resume')
        return row['returncode']
    except BaseException:
        row['error'] = traceback.format_exc()
        raise
    finally:
        original.read, original.write_json, sys.argv = original_read, original_write, original_argv
        row['finished_at_utc'] = now()
        write_json(path, row)


if __name__ == '__main__':
    raise SystemExit(main())
