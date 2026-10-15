"""全長ECAPAをnative速度phase・共有ML排他の順で実行する運用driver。"""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time

from all_metrics_common import ROOT, RUN, now, read
from all_metrics_resources import shared_stage, stop_owned_child
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


@shared_stage('full-length-speaker-driver')
def run_batch(batch, scope='native'):
    folder = RUN / 'speaker-full'
    ledger = folder / 'executions' / f'{scope}-{batch:02d}.json'
    history = read(ledger) if ledger.exists() else []
    attempt = len(history) + 1
    log = folder / 'logs' / f'{scope}-{batch:02d}-attempt{attempt:02d}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    lock_path = RUN / '.ml-worker.lock'
    command = [str(ROOT / '.venv/bin/python'), 'scripts/all_metrics_control_eval_speaker.py',
               '--batch', str(batch), '--scope', scope, '--retry-failed']
    env = {'OPENBLAS_NUM_THREADS': '2', 'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
           'NUMEXPR_NUM_THREADS': '2', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    row = {'batch': batch, 'scope': scope, 'attempt': attempt, 'command': command, 'environment_overrides': env,
           'driver_source_sha256': sha256(Path(__file__)), 'requested_at_utc': now(),
           'shared_lock': str(lock_path), 'log': str(log)}
    history.append(row)
    write_json(ledger, history)
    wait_start = time.perf_counter()
    with lock_path.open('a') as lock:
        while True:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            free = shutil.disk_usage(ROOT).free
            if free >= 2_000_000_000:
                row['disk_free_bytes_at_launch'] = free
                break
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            row.setdefault('disk_gate_waits', []).append({'at_utc': now(), 'free_bytes': free, 'required_bytes': 2_000_000_000})
            write_json(ledger, history)
            print(f'全長ECAPA 空き容量待機: batch={batch:02d} free={free}', flush=True)
            time.sleep(60)
        row.update(acquired_at_utc=now(), lock_wait_seconds=time.perf_counter() - wait_start)
        start = time.perf_counter()
        try:
            with log.open('w') as stream:
                child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                         env={**os.environ, **env}, start_new_session=True)
                row.update(pid=child.pid, child_started_at_utc=now())
                write_json(ledger, history)
                try:
                    _, status, usage = os.wait4(child.pid, 0)
                    child.returncode = os.waitstatus_to_exitcode(status)
                    row.update(returncode=child.returncode,
                        child_rusage={'user_cpu_seconds': usage.ru_utime, 'system_cpu_seconds': usage.ru_stime,
                                      'maximum_resident_set_kib': usage.ru_maxrss, 'scope': 'Linux wait4 exact child'})
                except BaseException:
                    row.update(returncode=130, interruption='driver interrupted', **stop_owned_child(child))
                    raise
        finally:
            row.update(finished_at_utc=now(), wall_seconds=time.perf_counter() - start,
                       log_sha256=sha256(log) if log.exists() else None)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            row['released_at_utc'] = now()
            write_json(ledger, history)
    print(f'全長ECAPA 正式batch={batch:02d} returncode={row["returncode"]} seconds={row["wall_seconds"]:.1f}', flush=True)
    return row['returncode']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-batch', type=int, default=0)
    parser.add_argument('--end-batch', type=int, default=12)
    parser.add_argument('--scope', choices=('native', 'latent', 'all'), default='native')
    args = parser.parse_args()
    if not 0 <= args.start_batch < args.end_batch <= 12:
        raise ValueError('固定120録音の12batch以内で指定してください')
    failures = []
    for batch in range(args.start_batch, args.end_batch):
        code = run_batch(batch, args.scope)
        if code:
            failures.append({'batch': batch, 'returncode': code})
    write_json(RUN / f'speaker-full/execution-summary-{args.scope}.json',
               {'finished_at_utc': now(), 'failures': failures, 'start_batch': args.start_batch, 'end_batch': args.end_batch})
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-speaker-driver'))
