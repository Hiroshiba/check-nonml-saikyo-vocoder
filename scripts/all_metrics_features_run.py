"""全8方式×独立train120および#14/#15の正式研究を再開可能に進める。"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import time
import traceback

from all_metrics_common import METHODS, ROOT, now, read
from all_metrics_features_common import OUT, TRAIN, prepare_input_contract, target_measurements
from all_metrics_features_receipts import completion_receipt
from all_metrics_process_receipts import command_files, source_receipt, verify_previous
from all_metrics_resources import stop_owned_child, study_gate
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def train(method, retry_failed):
    for batch in range(12):
        ledger = TRAIN / 'processes' / f'{method}-{batch:02d}.json'
        history = read(ledger) if ledger.exists() else []
        while shutil.disk_usage(ROOT).free < 1_500_000_000:
            logging.warning('容量待機、次train batchを保留: %s %s free=%s', method, batch,
                            shutil.disk_usage(ROOT).free)
            time.sleep(60)
        python = (ROOT / '.venv/bin/python3.12' if method in ('hnm', 'world_harvest')
                  else ROOT / '.cache/references/env/bin/python3.10')
        command = [str(python), str(ROOT / 'scripts/all_metrics_features_train.py'), '--method', method,
                    '--inputs', str(TRAIN / 'input-batches' / f'{batch:02d}.json')]
        if retry_failed:
            command.append('--retry-failed')
        inputs = TRAIN / 'input-batches' / f'{batch:02d}.json'
        if history and history[-1].get('returncode') == 0:
            if not verify_previous(history[-1], command):
                raise ValueError('独立train成功batchの完了receiptが未復元。終了0だけでは省略しません')
            completion_receipt(TRAIN, method, inputs)
            continue
        attempt = len(history)+1
        log = TRAIN / 'logs' / f'{method}-{batch:02d}-attempt{attempt:02d}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        env = {'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
            'NONML_WORLD_CACHE': str(ROOT / '.cache/world')}
        row = {'method': method, 'batch': batch, 'command': command, 'attempt': attempt,
               'source_receipt': source_receipt(), 'command_files': command_files(command),
               'environment_overrides': env, 'started_at_utc': now(), 'log': str(log)}
        history.append(row)
        write_json(ledger, history)
        tick = time.perf_counter()
        with study_gate(f'features-train-{method}-{batch:02d}'), log.open('w') as stream:
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
        row.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter()-tick,
                   log_sha256=sha256(log), free_disk_bytes=shutil.disk_usage(ROOT).free)
        if row['returncode'] == 0:
            if row['source_receipt'] != source_receipt():
                raise ValueError('独立train抽出中にsourceが変更されました')
            row['completion_receipt'] = completion_receipt(TRAIN, method, inputs)
            row['scientific_source_receipt'] = read(TRAIN / 'contracts' / f'{method}.json')['sources_sha256']
        write_json(ledger, history)
        logging.info('正式train batch完了: %s %02d returncode=%s %.1fs',
                     method, batch, row['returncode'], row['elapsed_seconds'])


def assess(method, retry_failed=False):
    from all_metrics_features_readout import measure as readout
    from all_metrics_features_abx import measure as measure_abx
    states = []
    for name, function in (('readout', readout), ('abx', measure_abx)):
        result_file = OUT / method / name / 'results.json'
        # 成功済みも評価入口で契約と保存artifactのSHAを照合する。
        if result_file.exists() and read(result_file).get('status') == 'failed' and not retry_failed:
            states.append('failed')
            continue
        try:
            with study_gate(f'features-assess-{name}'):
                result = function(method)
            states.append(result['status'])
            logging.info('正式特徴評価: %s %s %s', method, name, result['status'])
        except Exception:
            logging.exception('正式特徴評価失敗: %s %s', method, name)
            error = {'status': 'failed', 'method': method, 'stage': name,
                     'error': traceback.format_exc(), 'finished_at_utc': now()}
            write_json(OUT / method / name / 'failure_history' / f'{time.time_ns()}.json', error)
            write_json(result_file, error)
            states.append('failed')
    return states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('targets', 'train', 'assess', 'all'))
    parser.add_argument('--methods', nargs='+', default=list(METHODS))
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    prepare_input_contract()
    if args.stage in ('targets', 'all'):
        with study_gate('features-targets'):
            target_measurements()
    if args.stage in ('train', 'all'):
        for method in args.methods:
            train(method, args.retry_failed)
    if args.stage in ('assess', 'all'):
        while True:
            states = {method: assess(method, args.retry_failed) for method in args.methods}
            write_json(OUT / 'execution-summary.json', {'states': states, 'updated_at_utc': now()})
            if not args.watch or not any('pending' in value for value in states.values()):
                break
            logging.info('全方式の固定eval120特徴を待機中: %s', states)
            time.sleep(60)
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-features'))
