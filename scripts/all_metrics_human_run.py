"""#13全8方式の正式特徴抽出を共有ML lockで直列化し、その後固定集計する。"""
from __future__ import annotations

import argparse
import fcntl
import logging
import os
import resource
import shutil
import subprocess
import time

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_feature_locked_run import ML_METHODS, cgroup
from all_metrics_human_data import OUT
from all_metrics_features_receipts import completion_receipt
from all_metrics_process_receipts import command_files, source_receipt, verify_previous
from all_metrics_resources import shared_stage, stop_owned_child
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


@shared_stage('human-features')
def extract(method, retry):
    for inputs in sorted((OUT / 'input-batches').glob('*.json')):
        ledger = OUT / 'processes' / f'{method}-{inputs.stem}.json'
        history = read(ledger) if ledger.exists() else []
        while shutil.disk_usage(ROOT).free < 1_500_000_000:
            logging.warning('#13次batchを容量待機: %s/%s', method, inputs.stem)
            time.sleep(60)
        python = ROOT / ('.venv/bin/python3.12' if method in ('hnm', 'world_harvest')
                         else '.cache/references/env/bin/python3.10')
        command = [str(python), str(ROOT / 'scripts/all_metrics_human_features.py'),
                   '--method', method, '--inputs', str(inputs)]
        if retry:
            command.append('--retry-failed')
        if history and history[-1].get('returncode') == 0:
            if not verify_previous(history[-1], command):
                raise ValueError('#13成功batchの完了receiptが未復元。終了0だけでは省略しません')
            completion_receipt(OUT, method, inputs, human=True)
            continue
        log = OUT / 'logs' / f'{method}-{inputs.stem}-attempt{len(history)+1:02d}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        env = {'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
            'NONML_WORLD_CACHE': str(ROOT / '.cache/world')}
        row = {'method': method, 'batch': inputs.stem, 'command': command, 'started_at_utc': now(),
            'source_receipt': source_receipt(), 'command_files': command_files(command),
            'log': str(log), 'environment': env, 'driver_sha256': sha256(__file__), 'cgroup_before': cgroup()}
        history.append(row)
        write_json(ledger, history)
        lock = None
        tick = time.perf_counter()
        if method in ML_METHODS:
            lock = (RUN / '.ml-worker.lock').open('a+')
            row['ml_lock_requested_at_utc'] = now()
            write_json(ledger, history)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            row.update(ml_lock_acquired_at_utc=now(), ml_lock_wait_seconds=time.perf_counter()-tick)
            write_json(ledger, history)
        try:
            with log.open('w') as stream:
                process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, **env},
                                           stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                row['pid'] = process.pid
                write_json(ledger, history)
                try:
                    row['returncode'] = process.wait()
                except KeyboardInterrupt:
                    row.update(stop_owned_child(process))
                    row['returncode'] = row['child_returncode']
                    row.update(interrupted_at_utc=now(), interrupted=True,
                               elapsed_seconds=time.perf_counter()-tick)
                    write_json(ledger, history)
                    raise
        finally:
            if lock is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                lock.close()
        row.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter()-tick,
            log_sha256=sha256(log), cgroup_after=cgroup(),
            children_cumulative_ru_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            resource_scope='wrapper cumulative children maxrss and shared cgroup peak; no OOM-cause inference')
        if row['returncode'] == 0:
            if row['source_receipt'] != source_receipt():
                raise ValueError('#13抽出中にsourceが変更されました')
            row['completion_receipt'] = completion_receipt(OUT, method, inputs, human=True)
            row['scientific_source_receipt'] = read(OUT / 'feature-contracts' / f'{method}.json')['source_sha256']
        write_json(ledger, history)
        logging.info('正式#13 batch完了: %s %s code=%s', method, inputs.stem, row['returncode'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('features', 'rankings', 'all'))
    parser.add_argument('--methods', nargs='+', default=list(METHODS))
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if args.stage in ('features', 'all'):
        if not (OUT / 'inputs.json').exists() or len(read(OUT / 'inputs.json')) != 105:
            raise ValueError('正式#13全105原音取得が未完了')
        for method in args.methods:
            extract(method, args.retry_failed)
    if args.stage in ('rankings', 'all'):
        from all_metrics_human_rankings import execute
        from all_metrics_resources import study_gate
        with study_gate('human-rankings'):
            execute()
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-human'))
