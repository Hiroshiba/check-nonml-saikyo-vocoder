"""VCTK availability16補助研究を10録音・2スレッドのプロセス単位で逐次保存する。"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_vctk_inputs import VCTK_RUN
from all_metrics_resources import shared_stage, stop_owned_child
from vocoderbench.quality_core import sha256, write_json
from vctk16_evidence import verify_saved_process


def saved_subset(method, batch, command):
    """Read-only success verification does not need a model or the shared ML lock."""
    if '--case-start' not in command or '--case-count' not in command:
        return False
    start = int(command[command.index('--case-start') + 1])
    count = int(command[command.index('--case-count') + 1])
    contract_path = VCTK_RUN / 'synthesis-contracts' / f'{method}.json'
    if not contract_path.exists():
        return False
    contract = read(contract_path)
    signature = sha256(contract_path)
    for relative, expected in contract['source_sha256'].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f'保存済み科学sourceの不一致: {relative}')
    specs = read(VCTK_RUN / 'input-batches' / f'{batch:02d}.json')[start:start + count]
    for spec in specs:
        path = VCTK_RUN / 'native' / method / spec['id'] / 'unedited.json'
        if not path.exists() or read(path).get('status') != 'measured':
            return False
        row = read(path)
        if (row['contract_sha256'] != signature or sha256(path.with_suffix('.npy')) != row['audio']['file_sha256']
                or sha256(spec['path']) != spec['sha256']):
            raise ValueError('保存済みsubsetの契約・入力・出力hash不一致')
    return bool(specs)


@shared_stage('vctk-process')
def process(stage, method, batch, command):
    ledger = VCTK_RUN / 'processes' / f'{stage}-{method}-{batch:02d}.json'
    history = read(ledger) if ledger.exists() else []
    if history and history[-1].get('returncode') == 0:
        if [x for x in history[-1]['command'] if x != '--retry-failed'] != [x for x in command if x != '--retry-failed']:
            raise ValueError('成功済みプロセスの再開コマンドが不一致です')
        verify_saved_process(method, batch, command)
        print(f'保存済みhash照合: {stage} {method} batch={batch:02d}', flush=True)
        return 0
    if saved_subset(method, batch, command):
        verify_saved_process(method, batch, command)
        history.append({'stage': stage, 'method': method, 'batch': batch, 'command': command,
                        'returncode': 0, 'finished_at_utc': now(), 'reused_hash_verified_outputs': True,
                        'new_child_process': False, 'driver_source_sha256': sha256(Path(__file__))})
        write_json(ledger, history)
        print(f'subset hash照合・再利用: {stage} {method} batch={batch:02d}', flush=True)
        return 0
    def resources_ready():
        available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))
        needed = (4 if method in ('facodec', 'hifiglot', 'sifigan') else 2) * 1024 ** 3
        return (shutil.disk_usage(ROOT).free >= 2 * 1024 ** 3 and available >= needed
                and not (VCTK_RUN / 'pause-processes').exists())

    while not resources_ready():
        print(f'資源/停止指定の待機: {stage} {method} batch={batch:02d} at={now()}', flush=True)
        time.sleep(60)
    attempt = len(history) + 1
    log = VCTK_RUN / 'logs' / f'{stage}-{method}-{batch:02d}-attempt{attempt:02d}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    overrides = {'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
                 'NUMEXPR_NUM_THREADS': '2', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                 'NONML_WORLD_CACHE': str(ROOT / '.cache/world')}
    row = {'stage': stage, 'method': method, 'batch': batch, 'attempt': attempt,
           'started_at_utc': now(), 'command': command, 'cwd': str(ROOT),
           'driver_source_sha256': sha256(Path(__file__)), 'environment_overrides': overrides,
           'log': str(log)}
    history.append(row)
    write_json(ledger, history)
    needs_lock = method in ('facodec', 'hifiglot', 'golf', 'sifigan', 'all8')
    lock_path = RUN / ('.visqol-worker.lock' if method == 'all8' else '.ml-worker.lock')
    lock_context = lock_path.open('a') if needs_lock else nullcontext(None)
    with lock_context as lock:
        if lock is not None:
            row['shared_lock'] = {'path': str(lock_path), 'requested_at_utc': now()}
            write_json(ledger, history)
            while True:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                if resources_ready():
                    row['shared_lock']['acquired_at_utc'] = now()
                    break
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                print(f'排他を解放して資源待機: {stage} {method} batch={batch:02d} at={now()}', flush=True)
                time.sleep(60)
        while lock is None and not resources_ready():
            print(f'排他取得後の資源待機: {stage} {method} batch={batch:02d} at={now()}', flush=True)
            time.sleep(60)
        start = time.perf_counter()
        row['child_started_at_utc'] = now()
        write_json(ledger, history)
        with log.open('w') as stream:
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                     env={**os.environ, **overrides}, start_new_session=True)
            row['pid'] = child.pid
            write_json(ledger, history)
            try:
                _, status, usage = os.wait4(child.pid, 0)
            except BaseException:
                row.update(returncode=130, interruption='driver interrupted', **stop_owned_child(child))
                write_json(ledger, history)
                raise
            child.returncode = os.waitstatus_to_exitcode(status)
            row['returncode'] = child.returncode
            row['child_rusage'] = {'user_cpu_seconds': usage.ru_utime, 'system_cpu_seconds': usage.ru_stime,
                                   'maximum_resident_set_kib': usage.ru_maxrss,
                                   'scope': 'Linux wait4 rusage for this exact child process'}
        row.update(finished_at_utc=now(), wall_seconds=time.perf_counter() - start, log_sha256=sha256(log))
        if lock is not None:
            row['shared_lock']['released_at_utc'] = now()
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    write_json(ledger, history)
    print(f'VCTK正式研究: {stage} {method} batch={batch:02d} rc={row["returncode"]} seconds={row["wall_seconds"]:.1f}',
          flush=True)
    return row['returncode']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('synthesis', 'quality'))
    parser.add_argument('--methods', nargs='+', choices=METHODS, default=list(METHODS))
    parser.add_argument('--start-batch', type=int, default=0)
    parser.add_argument('--end-batch', type=int, default=2)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--heavy-case-count', type=int, choices=(1, 2, 5, 10), default=2)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.start_batch < args.end_batch <= 2:
        raise ValueError('正式16録音の2バッチを指定してください')
    if args.stage == 'quality' and args.assets is None:
        raise ValueError('正式ViSQOLの固定資産JSONが必要です')
    failures = []
    for batch in range(args.start_batch, args.end_batch):
        for method in args.methods if args.stage == 'synthesis' else ['all8']:
            python = ROOT / ('.venv/bin/python' if method in (*METHODS[:2], 'all8')
                             else '.cache/references/env/bin/python')
            split = args.stage == 'synthesis' and method in ('facodec', 'hifiglot', 'sifigan')
            size = args.heavy_case_count if split else 10
            count = len(read(VCTK_RUN / 'input-batches' / f'{batch:02d}.json'))
            for offset in range(0, count, size):
                entrypoint = 'resume' if split else args.stage
                command = [str(python), str(Path(__file__).parent / f'all_metrics_vctk_{entrypoint}.py'),
                           '--batch', str(batch)]
                if args.stage == 'synthesis':
                    command += ['--method', method]
                else:
                    command += ['--assets', str(args.assets.resolve())]
                if split:
                    command += ['--case-start', str(offset), '--case-count', str(size)]
                if args.retry_failed:
                    command += ['--retry-failed']
                stage = f'{args.stage}-chunk{offset:02d}-{size:02d}' if split else args.stage
                code = process(stage, method, batch, command)
                if code:
                    failures.append({'method': method, 'batch': batch, 'case_start': offset, 'returncode': code})
    write_json(VCTK_RUN / f'{args.stage}-execution-summary-{time.time_ns()}.json',
               {'stage': args.stage, 'methods': args.methods, 'failures': failures,
                'start_batch': args.start_batch, 'end_batch': args.end_batch, 'finished_at_utc': now()})
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
