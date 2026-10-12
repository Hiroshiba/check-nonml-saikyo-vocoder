"""固定100音声以上で再合成・雑音反復・自動MOSを比較し、中断時も結果を残す。"""
from __future__ import annotations

from pathlib import Path
import logging
import time

import numpy as np

from . import audio_samples, corpus, hnm, world
from .benchmark_io import (ROOT, LABELS, SEEDS, external_candidate, now, read, seed_summary,
                           sha, source_contract, temporal_scalars, write)
from .extended_metrics import measure_extended
from .logging_utils import LoggedArgumentParser, run_cli, run_process
from .metrics import compare_waveforms
from .temporal_metrics import measure_temporal


def initialize(args):
    args.output.mkdir(parents=True, exist_ok=True)
    contract = source_contract(args.manifest, args.candidate_package, args.criteria)
    if not args.legacy_three_methods:
        from .references.integration import contract as reference_contract
        contract['existing_references'] = reference_contract(args)
    # JSON往復でtupleを正規化し、再開時は科学的条件の完全一致を要求する。
    import json
    contract = json.loads(json.dumps(contract))
    path = args.output / 'contract.json'
    if path.exists():
        previous = read(path)
        # HEADは出典として初回値を保持する。文章だけのcommitを科学条件変更としない。
        contract['method_sources']['hnm']['repository_commit'] = previous['method_sources']['hnm']['repository_commit']
        if previous != contract:
            raise ValueError('保存済みの比較条件と一致しません。新しい出力先で別の実験にしてください')
    else:
        write(path, contract)
        write(args.output / 'execution.json', {'started_at': now(), 'parent_commit':
              run_process(['git', 'rev-parse', 'HEAD'], cwd=ROOT).stdout.strip()})
    return contract


def acoustic_case(case, candidate, output, retry_failed=False):
    identifier, x, sr = case['id'], case['x'], case['sr']
    part = output / 'parts' / f'{identifier}.json'
    if part.exists():
        previous = read(part)
        if not retry_failed or all(row['status'] == 'measured' for row in previous['rows']):
            return
        write(output / 'failure_history' / f'{identifier}-{time.time_ns()}.json', previous)
    rows = []
    original = dict(case=identifier, method='identity', status='measured',
                    measurement=compare_waveforms(x, x, sr),
                    extended=measure_extended(x, x, sr), mos={'status': 'pending', 'value': None})
    waves = output / 'waveforms' / identifier
    waves.mkdir(parents=True, exist_ok=True)
    for method in ('hnm', 'candidate', 'world_harvest'):
        # 前回のseed 0波形を、再試行失敗後のMOSへ流用しない。
        (waves / f'{method}.npy').unlink(missing_ok=True)
    np.save(waves / 'identity.npy', x)
    for method in ('hnm', 'candidate', 'world_harvest'):
        module = hnm if method == 'hnm' else candidate if method == 'candidate' else world
        row = {'case': identifier, 'kind': 'natural_speech', 'method': method,
               'language': case['language'], 'style': case['style'], 'speaker': case['speaker'], 'speaker_group': case['speaker_gender_as_distributed'],
               'status': 'failed', 'mos': {'status': 'pending', 'value': None}, 'seed_diagnostics': []}
        row['planned_noise_seeds'] = list(SEEDS) if method != 'world_harvest' else [0]
        begin = time.perf_counter()
        try:
            params = module.encode(x, sr)
            for seed in SEEDS if method != 'world_harvest' else (0,):
                repetition = {'seed': seed, 'status': 'failed'}
                try:
                    y = module.decode(params, seed=seed) if method != 'world_harvest' else module.decode(params)
                    basic = compare_waveforms(x, y, sr)
                    if basic['status'] != 'ok':
                        raise ValueError(f"音響比較不能: {basic['status']}")
                    if seed == 0:
                        extended = measure_extended(x, y, sr)
                        temporal = extended['temporal']
                        row.update(measurement=basic, extended=extended, output_samples=len(y),
                                   representation_scalars=sum(v.size for v in vars(params).values()
                                                              if isinstance(v, np.ndarray)))
                        np.save(waves / f'{method}.npy', y)
                    else:
                        temporal = measure_temporal(x, y, sr)
                    values = temporal_scalars(temporal)
                    values.update(mr_stft_db=basic['mr_stft_log_magnitude_mae_db'],
                                  band_mae_db=basic['band_energy']['active_band_mae_db'],
                                  rms_gain_error_db=basic['rms_gain_error_db'], output_peak=basic['output_peak'])
                    repetition.update(status='measured', values=values)
                except Exception as error:
                    logging.exception('反復測定に失敗: %s / %s / seed=%s', identifier, method, seed)
                    repetition['error'] = f'{type(error).__name__}: {error}'
                row['seed_diagnostics'].append(repetition)
            row['seed_summary'] = seed_summary(row['seed_diagnostics'])
            row['status'] = ('measured' if all(r['status'] == 'measured' for r in row['seed_diagnostics'])
                             else 'partial_failure')
        except Exception as error:
            logging.exception('解析に失敗: %s / %s', identifier, method)
            row['error'] = f'{type(error).__name__}: {error}'
        row['seconds'] = time.perf_counter() - begin
        row['rtf_including_measurement'] = row['seconds'] / (len(x) / sr)
        rows.append(row)
        logging.info('%s / %s: %s (%.1f秒)', identifier, method, row['status'], row['seconds'])
    meta = {k: v for k, v in case.items() if k not in ('x', 'f0_truth')}
    write(part, {'case': meta, 'original': original, 'rows': rows})


def score_mos(args, cases):
    from .mos_batch import score
    score(args, cases)


def collect(args, cases, contract):
    base = contract['formal_base']
    report = {'schema_version': 3, 'formal_base': base, 'comparison_reference': base['method'],
              'method_labels': LABELS, 'contract': contract, 'execution': read(args.output / 'execution.json'),
              'generated_at': now(), 'planned_cases': len(cases), 'cases': [], 'resynthesis': [],
              'calibration': [], 'operations': [], 'decoder_only': [], 'diagnostics': [],
              'corpus_counts': corpus.read_manifest(args.manifest)['counts'],
              'data_manifest': str(args.manifest.relative_to(ROOT)) if args.manifest.is_relative_to(ROOT)
                               else args.manifest.name,
              'alignment': 'none', 'normalization': 'none'}
    if (args.output / 'mos_provenance.json').exists():
        report['mos_provenance'] = read(args.output / 'mos_provenance.json')
    # 固定集合の英語2話者を音声例に使う。JVS原音の再配布は行わない。
    audio_cases = set(corpus.read_manifest(args.manifest)['public_audio_example_ids'])
    samples = []
    for case in cases:
        part = args.output / 'parts' / f"{case['id']}.json"
        if not part.exists():
            report['cases'].append({'id': case['id'], 'status': 'pending'})
            for method in ('hnm', 'candidate', 'world_harvest'):
                report['resynthesis'].append({'case': case['id'], 'kind': 'natural_speech',
                    'method': method, 'status': 'pending', 'language': case['language'],
                    'style': case['style'], 'speaker': case['speaker'],
                    'speaker_group': case['speaker_gender_as_distributed'], 'mos': {'status': 'pending', 'value': None},
                    'planned_noise_seeds': list(SEEDS) if method != 'world_harvest' else [0]})
            report['calibration'].append({'case': case['id'], 'method': 'identity', 'status': 'pending',
                                          'mos': {'status': 'pending', 'value': None}})
            continue
        data = read(part)
        report['cases'].append(data['case'])
        report['calibration'].append(data['original'])
        report['resynthesis'].extend(data['rows'])
        if case['id'] in audio_cases:
            for method in LABELS:
                path = args.output / 'waveforms' / case['id'] / f'{method}.npy'
                if path.exists():
                    audio_samples.collect(samples, case, method, np.load(path, allow_pickle=False))
    from .references.integration import append_results
    append_results(args, report, samples)
    write(args.output / 'results.json', report)
    write(args.output / 'audio_samples.json', {'schema_version': 1, 'samples': samples,
          'selection_note': '固定集合の英語2話者、各先頭最大2秒。原音・候補・当時のベース・既存方式で同一区間。音量補正なし。'})
    from .benchmark_report import render
    render(report, args.output / 'index.html')
    return report


def main():
    import sys
    # With no development candidate, compare the standard public methods without a self-made base.
    if not any(arg == '--candidate-package' or arg.startswith('--candidate-package=') for arg in sys.argv[1:]):
        from .reference import main as references_main
        return references_main()
    parser = LoggedArgumentParser(description=__doc__)
    from .references.integration import add_arguments, execute as execute_references
    add_arguments(parser)
    parser.add_argument('--manifest', type=Path, default=corpus.MANIFEST)
    parser.add_argument('--cache', type=Path, default=corpus.CACHE)
    parser.add_argument('--mos-cache', type=Path, default=ROOT / '.cache/mos')
    parser.add_argument('--candidate-package', type=Path, required=True)
    parser.add_argument('--criteria', type=Path, required=True,
                        help='今回の判断条件を記した文書。過去候補の条件を暗黙に流用しない')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=('all', 'acoustic', 'mos', 'report'), default='all')
    parser.add_argument('--retry-failed', action='store_true', help='元の失敗記録を保存して、失敗行だけ再実行する')
    args = parser.parse_args()
    args.manifest, args.output = args.manifest.resolve(), args.output.resolve()
    cases = list(corpus.load_cases(args.manifest, args.cache))
    if len(cases) < 100 or len({case['id'] for case in cases}) != len(cases):
        raise ValueError('比較には固定された100以上の独立音声が必要です')
    contract = initialize(args)
    if args.stage == 'all':
        from .benchmark_pipeline import execute
        execute(args, cases)
    if args.stage == 'acoustic':
        candidate = external_candidate(args.candidate_package)
        for case in cases:
            acoustic_case(case, candidate, args.output, args.retry_failed)
    if args.stage == 'mos':
        score_mos(args, cases)
    execute_references(args)
    report = collect(args, cases, contract)
    failures = sum(r['status'] != 'measured' for r in report['resynthesis'])
    failures += bool(getattr(args, 'reference_exit_status', 0) or report.get('existing_reference_failures'))
    if args.stage in ('all', 'mos'):
        failures += sum(r['mos']['status'] != 'measured' for r in report['resynthesis'] + report['calibration'])
    logging.info('比較結果: %s / 音声数=%s / 失敗=%s / 条件SHA=%s',
                 args.output, len(cases), failures, sha(args.output / 'contract.json'))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'fixed-benchmark'))
