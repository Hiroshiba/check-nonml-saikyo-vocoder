"""WORLDと既存6方式の比較。DACは --include-dac でのみ追加する。"""
from __future__ import annotations

import importlib.metadata
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

from . import corpus
from .logging_utils import LoggedArgumentParser, run_cli
from .references import inputs
from .references.catalog import METHODS, add_arguments, selected
from .references.common import digest, implementation_hashes, now, read, write
from .references.evaluate import measure
from .references.report import render


def initialize(args, cases, names):
    versions = {}
    for method in names:
        if method == 'pml':
            from .references.current_base import record
            versions[method] = record()
            continue
        path = args.runtime_cache / 'prepared' / f'{method}.json'
        versions[method] = read(path) if path.exists() else {'status': 'not_prepared'}
        versions[method].pop('prepared_at', None)
    contract = {'schema_version': 1, 'methods': names, 'inputs': inputs.fingerprint(cases),
                'scope': 'fixed_corpus', 'seed': args.seed,
                'threads': args.threads, 'device': 'cpu', 'mos_requested': args.mos,
                'source_hashes': implementation_hashes(), 'prepared_methods': versions,
                'native_sample_rates': {m: METHODS[m].sample_rate for m in names},
                'evaluation': 'native-full-MOS + strict-length + original-rate-common-prefix-v1',
                'runtime_python': str(args.runtime_cache / 'env/bin/python'),
                'host_python': platform.python_version(),
                'host_environment': {'platform': platform.platform(), 'machine': platform.machine(),
                    'cpu_count': os.cpu_count(),
                    'cpu_model': next((line.split(':', 1)[1].strip() for line in
                        Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
                        platform.processor()) if Path('/proc/cpuinfo').exists() else platform.processor(),
                    'packages': {name: importlib.metadata.version(name) for name in
                        ('numpy', 'scipy', 'pystoi', 'torch', 'torchaudio', 'torchvision',
                         'transformers', 'timm', 'librosa', 'utmosv2')}},
                'manifest_sha256': digest(args.manifest),
                'current_base': versions.get('pml'),
                'synthesis_repetitions': 1, 'noise_seeds': [args.seed],
                'timing_protocol': 'single encode/decode; no warmup/repetitions; diagnostic only',
                'mos_protocol': {'fold': 0, 'extraction_seed': 20261012, 'repetitions': 1,
                                 'cpu_threads': 4, 'include_originals': True},
                'scope_limit': (f'合成seed {args.seed}。採用研究seed 20261015や過去HNM 8 seedとは別条件'
                                if args.include_current_base else '既存方式のみの単一seed比較')}
    path = args.output / 'contract.json'
    if path.exists() and read(path) != contract:
        raise ValueError('既存結果の条件が違います。別の出力先を指定してください')
    if not path.exists():
        if any(args.output.iterdir()):
            raise ValueError('条件記録のない非空フォルダには上書きしません')
        write(path, contract)
        write(args.output / 'execution.json', {'started_at': now(), 'repository_commit':
              subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()})
    inputs.save(cases, args.output)
    return contract


def run_workers(args, names):
    processes = []
    python = args.runtime_cache / 'env/bin/python'
    logs = args.output / 'logs'
    logs.mkdir(exist_ok=True)
    for name in names:
        command = [sys.executable if name == 'pml' else str(python), '-m', 'vocoderbench.references.worker', '--method', name,
                   '--runtime-cache', str(args.runtime_cache), '--inputs', str(args.output / 'inputs.json'),
                   '--output', str(args.output / 'native' / name), '--threads', str(args.threads),
                   '--seed', str(args.seed)]
        if args.retry_failed:
            command.append('--retry-failed')
        env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), MKL_NUM_THREADS=str(args.threads),
                   OPENBLAS_NUM_THREADS=str(args.threads), NUMBA_NUM_THREADS=str(args.threads),
                   MPLBACKEND='Agg', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   VOCODERBENCH_LOG_DIR=str(logs))
        path = logs / f'{name}-{__import__("time").time_ns()}.log'
        try:
            with path.open('w') as stream:
                process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                         env=env, timeout=args.timeout)
            processes.append({'method': name, 'returncode': process.returncode, 'log': str(path.relative_to(args.output))})
            if process.returncode:
                logging.error('方式の実行に失敗: %s。ログ: %s', name, path, stack_info=True)
        except Exception:
            logging.exception('方式の起動・実行に失敗: %s', name)
            processes.append({'method': name, 'error': traceback.format_exc(), 'log': str(path.relative_to(args.output))})
        write(args.output / 'processes.json', processes)
    return processes


def main(argv=None):
    parser = LoggedArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--include-current-base', action='store_true',
                        help='現在のPMLを同じ入力・seedで正式に併記する。新候補や採用判断ではない')
    parser.add_argument('--manifest', type=Path, default=corpus.MANIFEST)
    parser.add_argument('--corpus-cache', type=Path, default=corpus.CACHE)
    parser.add_argument('--mos-cache', type=Path, default=Path('.cache/mos'))
    parser.add_argument('--stage', choices=('all', 'acoustic', 'mos', 'report'), default='all')
    parser.set_defaults(mos=True)
    parser.add_argument('--list-methods', action='store_true')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--seed', type=int, default=20261015)
    parser.add_argument('--timeout', type=int, default=3600, help='方式ごとの上限秒数。失敗を記録し次方式へ進む')
    args = parser.parse_args(argv)
    names = selected(args)
    if args.include_current_base:
        names.insert(0, 'pml')
    if args.list_methods:
        for name, spec in METHODS.items():
            print(f'{name}: {spec.label} / {spec.variant} / {"明示併記" if name == "pml" else "任意" if spec.optional else "標準"}')
        return 0
    if args.output is None:
        parser.error('--output が必要です')
    if args.threads < 1 or args.timeout < 1 or not 0 <= args.seed < 2**32:
        parser.error('threads/timeoutは正の整数、seedは0以上2**32未満にしてください')
    args.output, args.runtime_cache = args.output.resolve(), args.runtime_cache.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.stage == 'report':
        data = read(args.output / 'results.json')
        render(data, args.output)
        return int(bool(data.get('failure_count', sum(r['status'] != 'measured' for r in data['resynthesis']))))
    cases, public = inputs.load(args)
    if args.include_current_base and any(case['sr'] != 16000 for case in cases):
        parser.error('現ベース併記は16 kHzの固定入力専用です')
    contract = initialize(args, cases, names)
    if args.stage in ('all', 'acoustic'):
        run_workers(args, names)
    # Acoustic-only preserves the intended MOS setting in the contract but reports pending MOS.
    requested_mos = args.mos
    if args.stage == 'acoustic':
        args.mos = False
    rows, originals = measure(args, cases, names, public)
    args.mos = requested_mos
    processes_path = args.output / 'processes.json'
    processes = read(processes_path) if processes_path.exists() else []
    process_failures = sum(p.get('returncode') != 0 or bool(p.get('error')) for p in processes)
    failures = process_failures + sum(row['status'] != 'measured' for row in rows)
    if args.mos and args.stage in ('all', 'mos'):
        failures += sum(row['mos']['status'] != 'measured' for row in rows + originals)
    formal_base = (contract['current_base']['baseline'] if args.include_current_base else
                   {'method': None, 'reason': '既存方式の比較。現自作ベースを測定・選定基準にしない'})
    data = {'schema_version': 5,
            'study_role': 'current_base_and_references' if args.include_current_base else 'existing_references',
            'formal_base': formal_base,
            'comparison_reference': 'pml' if args.include_current_base else
                'world_harvest' if 'world_harvest' in names else names[0],
            'selected_methods': names, 'optional_omissions': [] if args.include_dac else ['dac'],
            'method_labels': {'identity': '原音', **{m: METHODS[m].label for m in names}},
            'native_sample_rates': {m: METHODS[m].sample_rate for m in names},
            'index_methods': ['identity', *names], 'generated_at': now(),
            'scope': '固定100音声以上の現ベース・既存方式比較' if args.include_current_base else
                     '固定100音声以上の既存方式比較',
            'planned_cases': len(cases), 'contract': contract, 'execution': read(args.output / 'execution.json'),
            'resynthesis': rows, 'calibration': originals, 'processes': processes,
            'failure_count': failures, 'process_failure_count': process_failures,
            'operation_evaluation': {'status': 'not_implemented', 'reason': '本PRは再合成比較の追加。属性操作・下流学習は未評価'}}
    if args.include_current_base:
        data['method_labels']['pml'] = f"PML（現ベース: {formal_base['version']}）"
    if (args.output / 'mos_provenance.json').exists():
        data['mos_provenance'] = read(args.output / 'mos_provenance.json')
    write(args.output / 'results.json', data)
    render(data, args.output)
    logging.info('既存方式比較: %s。%d方式・%d音声。失敗=%d', args.output, len(names), len(cases), failures)
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'references'))
