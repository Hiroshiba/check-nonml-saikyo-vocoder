"""開発候補の既存比較にも、新しい公開方式を標準で追加する。"""
from copy import deepcopy
from pathlib import Path

from .catalog import DEFAULT_METHODS, METHODS
from .common import HERE, digest, implementation_hashes, read


EXTRA_METHODS = tuple(m for m in DEFAULT_METHODS if m != 'world_harvest')


def add_arguments(parser):
    from .catalog import DEFAULT_CACHE
    parser.add_argument('--include-dac', action='store_true')
    parser.add_argument('--reference-cache', type=Path, default=DEFAULT_CACHE)
    parser.add_argument('--legacy-three-methods', action='store_true',
                        help='旧3方式の実行経路のみを使う。標準の既存方式比較とは区別する')


def contract(args):
    names = [*EXTRA_METHODS, *(['dac'] if args.include_dac else [])]
    return {'methods': names, 'lock_sha256': digest(HERE / 'sources.lock.json'),
            'implementation_hashes': implementation_hashes()}


def execute(args):
    if args.legacy_three_methods:
        return
    from ..reference import main
    argv = ['--methods', *EXTRA_METHODS, '--manifest', str(args.manifest),
            '--corpus-cache', str(args.cache), '--runtime-cache', str(args.reference_cache),
            '--mos-cache', str(args.mos_cache), '--output', str(args.output / 'references'),
            '--stage', args.stage]
    if args.include_dac:
        argv.append('--include-dac')
    if args.retry_failed:
        argv.append('--retry-failed')
    # Failures are kept in the resulting report; parent main returns nonzero after collection.
    main(argv)


def append_results(args, report, samples):
    if args.legacy_three_methods:
        return
    from ..benchmark_io import seed_summary, temporal_scalars
    path = args.output / 'references/results.json'
    data = read(path)
    report['method_labels'] = dict(report['method_labels'])
    report['method_labels'].update({m: METHODS[m].label for m in data['selected_methods']})
    report['existing_reference_contract'] = data['contract']
    report['existing_reference_note'] = (
        '追加方式は公開ネイティブ帯域で合成。長さ不一致の全長指標を未測定として残し、'
        '共通先頭区間の補助値はcommon_prefixに分離。予測MOSはネイティブ全長出力。')
    groups = {c['id']: c.get('speaker_gender_as_distributed', 'unknown') for c in report['cases']}
    for original in data['resynthesis']:
        row = deepcopy(original)
        row['speaker_group'] = groups[row['case']]
        row['planned_noise_seeds'] = [0]
        row['seed_diagnostics'] = []
        values = {}
        if row.get('measurement', {}).get('status') == 'ok':
            row['extended'] = row['common_prefix']['extended']
            values = temporal_scalars(row['extended'].get('temporal') or {})
            basic = row['measurement']
            values.update(mr_stft_db=basic.get('mr_stft_log_magnitude_mae_db'),
                          band_mae_db=(basic.get('band_energy') or {}).get('active_band_mae_db'),
                          rms_gain_error_db=basic.get('rms_gain_error_db'), output_peak=basic.get('output_peak'))
        row['seed_diagnostics'].append({'seed': 0, 'status': row['status'], 'values': values})
        row['seed_summary'] = seed_summary(row['seed_diagnostics'])
        report['resynthesis'].append(row)
    audio = read(args.output / 'references/audio_samples.json')
    samples.extend(s for s in audio['samples'] if s['method'] != 'identity')
