"""正式native表現の到着を待ち、方式ごと10件のB/Cを一度ずつ逐次処理する。"""
from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import subprocess
import time

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_latent_provenance import verify_retained_evidence
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

TERMINAL = ('measured', 'failed', 'not_applicable', 'upstream_failed')


def stage_complete(method, specs, stage):
    contract = RUN / 'latent-contracts' / method / f'{stage}.json'
    if not contract.exists():
        return False
    signature = sha256(contract)
    for source, expected in read(contract)['source_sha256'].items():
        if sha256(ROOT / source) != expected:
            raise ValueError(f'凍結B/C source hash不一致: {source}')
    if stage == 'quantization':
        edits = [] if method == 'facodec' else ['pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6']
        names = [point + suffix for point in ('quantized_float16', 'quantized_float32')
                 for suffix in ['', *('__' + edit for edit in edits)]]
    else:
        names = ['interpolation_input_gain_alpha' + alpha for alpha in ('0', '0p5', '1')]
    for spec in specs:
        folder = RUN / 'native' / method / spec['id']
        progress = folder / f'latent-{stage}-progress.json'
        if not progress.exists() or not read(progress).get('conditions'):
            return False
        for name in names:
            path = folder / f'{name}.json'
            if not path.exists():
                return False
            row = read(path)
            if row.get('contract_sha256') != signature:
                raise ValueError(f'保存条件のB/C contract不一致: {path}')
            if row['status'] not in TERMINAL:
                return False
            if row['status'] == 'measured':
                if sha256(row['audio']['path']) != row['audio']['file_sha256']:
                    raise ValueError(f'保存成功wave hash不一致: {path}')
                verify_retained_evidence(row)
    return True


def ready(method, specs):
    for spec in specs:
        folder = RUN / 'native' / method / spec['id']
        path = folder / 'unedited.json'
        if not path.exists():
            return False
        if read(path).get('status', 'pending').startswith('pending'):
            return False
    return True


def execute(method, batch, stage, queue_root):
    free = shutil.disk_usage(RUN).free
    if free < 2 * 1024**3:
        return 75
    command = [str(ROOT / '.venv/bin/python3.12'), 'scripts/all_metrics_latent_run.py', stage,
               '--methods', method, '--start-batch', str(batch), '--end-batch', str(batch + 1)]
    target = queue_root / 'executions' / f'{stage}-{method}-{batch:02d}-{time.time_ns()}.json'
    row = {'method': method, 'batch': batch, 'stage': stage, 'started_at_utc': now(),
        'command': command, 'free_bytes_before': free, 'source_sha256': sha256(__file__),
        'ml_exclusive_scope': 'all_metrics_latent_run holds the shared lock for each complete ML process'}
    write_json(target, row)
    result = subprocess.run(command, cwd=ROOT, check=False, env={**os.environ,
        'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2'})
    row.update(returncode=result.returncode, finished_at_utc=now(), free_bytes_after=shutil.disk_usage(RUN).free)
    write_json(target, row)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--methods', nargs='+', choices=METHODS,
                        default=['llsm2', 'magphase', 'facodec', 'hifiglot', 'golf', 'sifigan'])
    parser.add_argument('--queue-name', choices=('all', 'classical', 'ml'), default='all')
    args = parser.parse_args()
    scopes = {'classical': {'llsm2', 'magphase'}, 'ml': {'facodec', 'hifiglot', 'golf', 'sifigan'}}
    if args.queue_name in scopes and set(args.methods) != scopes[args.queue_name]:
        raise ValueError('分割queueの方式集合を混ぜません')
    queue_root = RUN / 'latent-queue' / args.queue_name
    queue_root.mkdir(parents=True, exist_ok=True)
    lock = (queue_root / '.queue.lock').open('a')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    complete = set()
    while True:
        pending = []
        for batch in range(12):
            specs = read(RUN / f'input-batches/{batch:02d}.json')
            for method in args.methods:
                key = (batch, method)
                if key in complete:
                    continue
                if not ready(method, specs):
                    pending.append({'batch': batch, 'method': method, 'status': 'pending_native'})
                    continue
                for stage in ('quantization', 'interpolation'):
                    if stage_complete(method, specs, stage):
                        continue
                    if shutil.disk_usage(RUN).free < 2 * 1024**3:
                        write_json(queue_root / 'status.json', {'status': 'blocked_free_space',
                            'at_utc': now(), 'batch': batch, 'method': method, 'stage': stage,
                            'free_bytes': shutil.disk_usage(RUN).free, 'minimum_free_bytes': 2 * 1024**3})
                        return 75
                    write_json(queue_root / 'status.json', {'status': 'executing_or_waiting_shared_lock',
                        'at_utc': now(), 'batch': batch, 'method': method, 'stage': stage,
                        'completed_method_batches': sorted(complete), 'methods': args.methods})
                    code = execute(method, batch, stage, queue_root)
                    if not stage_complete(method, specs, stage):
                        write_json(queue_root / 'status.json', {'status': 'incomplete_process',
                            'at_utc': now(), 'batch': batch, 'method': method, 'stage': stage, 'returncode': code})
                        return code or 1
                complete.add(key)
                write_json(queue_root / 'status.json', {'status': 'running', 'at_utc': now(),
                    'completed_method_batches': sorted(complete), 'pending': pending})
        if not pending:
            write_json(queue_root / 'status.json', {'status': 'completed', 'at_utc': now(),
                'completed_method_batches': sorted(complete)})
            return 0
        write_json(queue_root / 'status.json', {'status': 'waiting_native', 'at_utc': now(),
            'completed_method_batches': sorted(complete), 'pending': pending})
        time.sleep(60)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-queue'))
