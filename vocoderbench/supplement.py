"""正式120件の完了・版一致を確認し、JVS12録音だけの補助診断を実行する。"""
import logging
import os
from pathlib import Path

from . import corpus
from .benchmark import acoustic_case
from .benchmark_io import ROOT, LABELS, external_candidate, now, read, write
from .benchmark_pipeline import execute
from .logging_utils import LoggedArgumentParser, run_cli
from .mos_batch import score
from .supplement_contract import MANIFEST, build, initialize
from .supplement_report import render


def collect(args, cases, contract):
    report = {'schema_version': 4, 'study_role': 'supplement_to_completed_fixed_120',
              'formal_base': contract['shared_conditions']['formal_base'], 'comparison_reference': 'hnm',
              'method_labels': LABELS, 'contract': contract, 'execution': read(args.output / 'execution.json'),
              'generated_at': now(), 'planned_cases': 12, 'cases': [], 'resynthesis': [], 'calibration': [],
              'data_manifest': 'data/jvs_available_v1.json', 'corpus_counts': {'recordings': 12, 'speakers': 4},
              'alignment': 'none', 'normalization': 'none', 'public_audio': False}
    for case in cases:
        path = args.output / 'parts' / f"{case['id']}.json"
        if path.exists():
            part = read(path)
            report['cases'].append(part['case'])
            report['resynthesis'].extend(part['rows'])
            report['calibration'].append(part['original'])
        else:
            report['cases'].append({k: v for k, v in case.items() if k not in ('x', 'f0_truth')})
            for method in ('hnm', 'candidate', 'world_harvest'):
                report['resynthesis'].append({'case': case['id'], 'method': method, 'status': 'pending',
                    'style': case['style'], 'speaker': case['speaker'], 'speaker_group': None,
                    'mos': {'status': 'pending', 'value': None}})
            report['calibration'].append({'case': case['id'], 'method': 'identity', 'status': 'pending',
                                          'mos': {'status': 'pending', 'value': None}})
    provenance = args.output / 'mos_provenance.json'
    if provenance.exists():
        report['mos_provenance'] = read(provenance)
    write(args.output / 'results.json', report)
    render(report, args.output)
    return report


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=corpus.CACHE)
    parser.add_argument('--mos-cache', type=Path, required=True)
    parser.add_argument('--candidate-package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=('all', 'acoustic', 'mos', 'report'), default='all')
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(ROOT / 'runs'):
        raise ValueError('非公開音声を含む作業出力はGit管理外のruns配下へ置いてください')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    # load_casesは取得処理を呼ばず、固定PCM・ファイルの一致だけを確認する。
    cases = list(corpus.load_cases(MANIFEST, args.cache))
    contract = initialize(args, cases)
    execution = read(args.output / 'execution.json')
    execution.update(status='running', last_stage=args.stage)
    write(args.output / 'execution.json', execution)
    try:
        if args.stage == 'all':
            execute(args, cases)
        elif args.stage == 'acoustic':
            candidate = external_candidate(args.candidate_package)
            for case in cases:
                acoustic_case(case, candidate, args.output, args.retry_failed)
        elif args.stage == 'mos':
            score(args, cases)
        if build(args, cases) != contract:
            raise RuntimeError('実行中に測定条件が変わりました')
        report = collect(args, cases, contract)
        failures = sum(r['status'] != 'measured' for r in report['resynthesis'])
        if args.stage in ('all', 'mos'):
            failures += sum(r['mos']['status'] != 'measured' for r in report['resynthesis'] + report['calibration'])
        execution.update(status='completed' if not failures else 'completed_with_failures', completed_at=now())
        write(args.output / 'execution.json', execution)
        collect(args, cases, contract)
        logging.info('JVS補助比較終了: 12録音、予定204合成・48MOS。未完了または失敗=%s', failures)
        return int(bool(failures))
    except Exception as error:
        execution.update(status='interrupted', interrupted_at=now(), error=f'{type(error).__name__}: {error}')
        write(args.output / 'execution.json', execution)
        collect(args, cases, contract)
        raise


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'jvs-supplement'))
