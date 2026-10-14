"""正式研究を小バッチで実行し、終了状態・失敗・再開履歴を保存する。"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_resources import stop_owned_child, study_gate
from all_metrics_process_receipts import command_files, completed_artifacts, scientific_sources, source_receipt, verify_previous
from vocoderbench.quality_core import sha256, write_json


def run_process(stage, batch, method, command, output=None, native_phase_active=False):
    ledger = RUN / 'processes' / f'{stage}-{method}-{batch:02d}.json'
    history = read(ledger) if ledger.exists() else []
    if history and history[-1].get('returncode') == 0 and verify_previous(history[-1], command):
        print(f'再開済み: {stage} {method} batch={batch}', flush=True)
        return 0
    attempt = len(history) + 1
    base_command = list(command)
    command = list(command)
    if output is not None:
        output = Path(str(output) + f'-attempt{attempt:02d}')
        command += ['--output', str(output)]
    log = RUN / 'logs' / f'{stage}-{method}-{batch:02d}-attempt{attempt:02d}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {'stage': stage, 'batch': batch, 'method': method, 'attempt': attempt,
           'started_at_utc': now(), 'command': command, 'cwd': str(ROOT), 'log': str(log),
           'output': str(output) if output else None, 'driver_source_sha256': sha256(Path(__file__)),
           'base_command': base_command, 'command_files': command_files(base_command),
           'source_receipt': source_receipt(),
           'environment_overrides': {'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2',
                                    'MKL_NUM_THREADS': '2', 'NUMEXPR_NUM_THREADS': '2',
                                    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                                    'NONML_WORLD_CACHE': str(ROOT / '.cache/world')},
           'native_phase_active': native_phase_active}
    history.append(row)
    write_json(ledger, history)
    required = stage in ('quality', 'asr') or stage.startswith('mos') or (
        stage in ('synthesis', 'synthesis-edits') and method in ('facodec', 'hifiglot', 'golf', 'sifigan')) or (
        stage.startswith('latent-') and (stage == 'latent-speaker' or method in ('facodec', 'hifiglot', 'golf', 'sifigan')))
    row['shared_ml_concurrency_limit'] = 1
    row['ml_lock_required'] = required
    resource_log = log.with_suffix('.resource.txt')
    if Path('/usr/bin/time').exists():
        command = ['/usr/bin/time', '-v', '-o', str(resource_log), *command]
        row['resource_wrapper_command'] = command
    wait_started = time.perf_counter()
    context = (RUN / '.ml-worker.lock').open('a+') if required else nullcontext(None)
    gate = nullcontext(None) if native_phase_active else study_gate(f'{stage}-{method}-{batch:02d}')
    with gate, context as lock:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
        row['ml_lock_wait_seconds'] = time.perf_counter()-wait_started
        row['worker_started_at_utc'] = now()
        write_json(ledger, history)
        start = time.perf_counter()
        with log.open('w') as stream:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                env={**os.environ, **row['environment_overrides']}, start_new_session=True)
            row['pid'] = process.pid
            write_json(ledger, history)
            try:
                row['returncode'] = process.wait()
            except KeyboardInterrupt:
                row.update(returncode=130, interruption='operator interruption; completed case files retained',
                           interruption_received_at_utc=now())
                row.update(stop_owned_child(process), finished_at_utc=now())
                write_json(ledger, history)
                raise
    if resource_log.exists():
        row['resource_log'] = str(resource_log)
        row['resource_log_sha256'] = sha256(resource_log)
        for line in resource_log.read_text().splitlines():
            if 'Maximum resident set size (kbytes):' in line:
                row['maximum_resident_set_size_kbytes'] = int(line.split(':')[-1])
    row.update(finished_at_utc=now(), wall_seconds=time.perf_counter() - start, log_sha256=sha256(log))
    if output and (output / 'results.json').exists():
        result = read(output / 'results.json')
        row['result_rows'] = len(result.get('rows', []))
        row['result_status_counts'] = {status: sum(r['status'] == status for r in result.get('rows', []))
                                       for status in sorted({r['status'] for r in result.get('rows', [])})}
    if row['returncode'] == 0:
        row['completion_receipt'] = completed_artifacts(stage, batch, method, output)
        row['scientific_source_receipt'] = scientific_sources(stage, method, output)
    write_json(ledger, history)
    print(f'正式研究: {stage} {method} batch={batch} returncode={row["returncode"]} seconds={row["wall_seconds"]:.1f}', flush=True)
    return row['returncode']


def assets():
    path = RUN / 'quality-inputs/assets.json'
    metrics = {'erb': {},
        'scoreq': {'model': str(ROOT / '.cache/quality/fixed_nmr_telephone.onnx'), 'domain': 'natural'},
        'speaker_ecapa': {'embedding_model': str(ROOT / '.cache/ecapa/embedding_model.ckpt')}}
    for metric, key in (('scoreq', 'model'), ('speaker_ecapa', 'embedding_model')):
        metrics[metric][key + '_sha256'] = sha256(metrics[metric][key])
    freeze(path, {'schema_version': 1, 'metrics': metrics})
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('synthesis', 'synthesis-edits', 'quality', 'mos', 'mos-edits', 'mos-latent', 'acoustic', 'asr', 'controls'))
    parser.add_argument('--start-batch', type=int, default=0)
    parser.add_argument('--end-batch', type=int, default=12)
    parser.add_argument('--methods', nargs='+', default=list(METHODS))
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--finalize-native-failures', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.start_batch < args.end_batch <= 12:
        parser.error('batch range must satisfy 0 <= start < end <= 12')
    if args.stage == 'synthesis' and (args.methods != list(METHODS) or args.end_batch != args.start_batch + 1):
        parser.error('native timing phase requires all eight methods and exactly one fixed 10-record batch')
    failures = []
    for batch in range(args.start_batch, args.end_batch):
        if args.stage in ('synthesis', 'synthesis-edits'):
            order = list(METHODS[batch % len(METHODS):] + METHODS[:batch % len(METHODS)])
            selected = [method for method in order if method in args.methods]
            gate = study_gate(f'native-batch-{batch:02d}', native=True) if args.stage == 'synthesis' else nullcontext()
            with gate:
                for method in selected:
                    python = ROOT / ('.venv/bin/python' if method in METHODS[:2] else '.cache/references/env/bin/python')
                    command = [str(python), str(ROOT / 'scripts/all_metrics_synthesis.py'),
                        '--method', method, '--inputs', str(RUN / f'input-batches/{batch:02d}.json'),
                        '--runtime-cache', str(ROOT / '.cache/references'), '--threads', '2', '--seed', '0',
                        '--unedited-only' if args.stage == 'synthesis' else '--edits-only']
                    if args.retry_failed:
                        command.append('--retry-failed')
                    code = run_process(args.stage, batch, method, command, native_phase_active=args.stage == 'synthesis')
                    if code:
                        failures.append([batch, method, code])
        elif args.stage == 'quality':
            command = [sys.executable, str(ROOT / 'scripts/all_metrics_derive.py'), '--batch', str(batch)]
            if args.finalize_native_failures:
                command.append('--finalize-native-failures')
            code = run_process('derive', batch, 'all', command)
            if code:
                failures.append([batch, 'derive', code])
                continue
            if not read(RUN / f'quality-inputs/common-{batch:02d}.json')['cases']:
                write_json(RUN / f'quality/common-{batch:02d}-not-applicable.json', {
                    'status': 'not_applicable', 'reason': '全8共通の事前条件を満たす録音がこのbatchにない',
                    'manifest_sha256': sha256(RUN / f'quality-inputs/common-{batch:02d}.json')})
                continue
            command = [sys.executable, '-m', 'vocoderbench.quality', '--manifest',
                str(RUN / f'quality-inputs/common-{batch:02d}.json'), '--assets', str(assets()),
                '--metrics', 'scoreq', 'speaker_ecapa', 'erb', '--repetitions', '1', '--threads', '2']
            code = run_process('quality', batch, 'common16', command, RUN / f'quality/common-{batch:02d}')
            if code:
                failures.append([batch, 'quality', code])
        else:
            name = 'mos' if args.stage.startswith('mos') else 'control_eval' if args.stage == 'controls' else args.stage
            command = [sys.executable, str(ROOT / f'scripts/all_metrics_{name}.py'), '--batch', str(batch)]
            if args.stage == 'mos-edits':
                command += ['--include-edits']
            elif args.stage == 'mos-latent':
                command += ['--latent']
            if args.retry_failed:
                command.append('--retry-failed')
            code = run_process(args.stage, batch, 'all', command)
            if code:
                failures.append([batch, args.stage, code])
    write_json(RUN / f'{args.stage}-execution-summary.json', {'finished_at_utc': now(), 'failures': failures,
        'start_batch': args.start_batch, 'end_batch': args.end_batch, 'methods': args.methods})
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
