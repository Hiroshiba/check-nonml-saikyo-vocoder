"""公開済み固定集合と事前設定から、新しい区間実行計画を凍結する。"""
from pathlib import Path

from .chunk_contracts import freeze, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--settings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cohort = read(args.cohort)
    settings = read(args.settings)
    cases = [{'case': row['id'], 'speaker': row['speaker'],
              'input_sha256': row['input']['sha256'],
              'samples': row['input']['excerpt_samples'],
              'sample_rate': row['input']['sample_rate'],
              'common_samples': row['common_samples']} for row in cohort['cases']]
    ids = [row['case'] for row in cases]
    axes = [{key: axis[key] for key in ('id', 'condition', 'direction', 'methods')}
            for axis in settings['axes']]
    names = ('cohort', 'evaluator', 'generation', 'runtime', 'assets', 'preprocessing')
    frozen = {name: settings['frozen_digests'][name] for name in names}
    if frozen['cohort'] != sha(args.cohort):
        raise ValueError('事前設定と固定集合のSHAが一致しません')
    plan = {'schema_version': 2, 'scope': 'fixed120-chunked-evaluation', 'cases': cases,
            'chunks': [{'id': f'chunk-{i+1:02d}', 'case_ids': ids[i*12:(i+1)*12]} for i in range(10)],
            'methods': settings['methods'], 'formal_base': settings['formal_base'],
            'formal_base_version': settings['formal_base_version'], 'candidate': settings['candidate'],
            'axes': axes, 'frozen_digests': frozen,
            'required_stage_receipts': settings['required_stage_receipts'],
            'execution': {'chunk_size': 12, 'scientific_parallelism': 1,
                          'rank_before_all_chunks': False, 'generation_before_quality': True}}
    validate_plan(plan)
    freeze(args.output, plan)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'freeze-chunk-plan'))
