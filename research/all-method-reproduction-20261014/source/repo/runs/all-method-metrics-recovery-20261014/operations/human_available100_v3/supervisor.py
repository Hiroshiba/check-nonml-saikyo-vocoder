"""可用性100録音別群の1方式・10録音運用入口。独立reviewと固定保存後のみ使用する。"""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import shutil
import time
import traceback

from settings import ROOT, OUT, PACKAGE
from release_proof import verify_release

from all_metrics_common import METHODS, RUN, now, read  # noqa: E402
from all_metrics_features_common import TRAIN, schema_digest  # noqa: E402
from all_metrics_features_receipts import completion_receipt  # noqa: E402
from all_metrics_process_receipts import command_files, source_receipt, verify_previous  # noqa: E402
from all_metrics_resources import resource_snapshot, stop_owned_child, study_gate  # noqa: E402
from vocoderbench.logging_utils import run_cli  # noqa: E402
from vocoderbench.quality_core import sha256, write_json  # noqa: E402

ENVIRONMENT = {
    'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
    'NONML_WORLD_CACHE': str(ROOT / '.cache/world'),
}


def check_hash(path, digest):
    if not Path(path).is_file() or sha256(path) != digest:
        raise ValueError(f'正式#13の固定入力/成果hash不一致または未復元: {path}')


def require_inputs(args):
    """独立100群の固定inventoryとreview/保全releaseを照合する。"""
    check_hash(OUT / 'preflight-freeze-v3.json', args.preflight_sha256)
    fixed = read(OUT / 'preflight-freeze-v3.json')
    for name, digest in fixed['fixed_files'].items():
        check_hash(name, digest)
    for name, digest in read(OUT / 'dependency-sha256-v3.json').items():
        check_hash(name, digest)
    for name, digest in read(OUT / 'source-sha256-v3.json').items():
        check_hash(ROOT / name, digest)
    verify_release(OUT / 'preflight-freeze-v3.json', args.batch)
    check_hash(OUT / 'inputs.json', args.inputs_sha256)
    check_hash(OUT / 'input-contract.json', args.input_contract_sha256)
    specs = read(OUT / 'inputs.json')
    if len(specs) != 100 or len({r['id'] for r in specs}) != 100:
        raise ValueError('100 distinct録音の固定manifestが必要です')
    if read(OUT / 'input-batches' / f'{args.batch:02d}.json') != specs[args.batch*10:(args.batch+1)*10]:
        raise ValueError('固定10録音batchの順序/内容不一致')
    if shutil.disk_usage(ROOT).free < 1_500_000_000:
        raise ValueError('既存stage容量下限1.5GB未満。資源解放まで起動しません')
    return fixed['fixed_files']


def inspect_records(method, specs, verify=False):
    result = []
    contract = OUT / 'feature-contracts' / f'{method}.json'
    schema = TRAIN / 'schemas' / f'{method}.json'
    for spec in specs:
        folder = OUT / 'features' / method / spec['id']
        path = folder / 'features.json'
        row = read(path) if path.exists() else {'status': 'missing'}
        if verify and path.exists():
            fixed = read(contract)
            if (row['method'] != method or row['case'] != spec['id']
                    or row['speaker'] != spec['speaker'] or row['contract_sha256'] != sha256(contract)
                    or fixed['input_contract_sha256'] != sha256(OUT / 'input-contract.json')
                    or fixed['train_feature_schema_sha256'] != sha256(schema)):
                raise ValueError('既存#13特徴のID/入力契約/schemaが不一致です')
            for relative, digest in fixed['source_sha256'].items():
                check_hash(ROOT / relative, digest)
            if row['status'] == 'measured':
                if (row['input']['source_sha256'] != spec['sha256']
                        or row['projected_schema_sha256'] != schema_digest(read(schema))):
                    raise ValueError('既存成功#13特徴の入力/schemaが不一致です')
                check_hash(folder / 'mean.npy', row['mean_sha256'])
            elif row['status'] != 'failed':
                raise ValueError('既存#13特徴に未知の状態があります')
        result.append({'case': spec['id'], 'status': row['status'],
            'record_sha256': sha256(path) if path.exists() else None,
            'mean_sha256': sha256(folder / 'mean.npy') if (folder / 'mean.npy').exists() else None})
    return result


def owned_group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def finish_child(process, row, ledger, history):
    """直接childと同じ専用groupの残存子孫が終了するまでlockを保持する。"""
    handlers = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        if process.poll() is None:
            row.update(stop_owned_child(process))
        row.update(returncode=process.wait(), child_exit_confirmed_at_utc=now())
        row['owned_group_stop_actions'] = []
        for sig, timeout in ((signal.SIGINT, 60), (signal.SIGTERM, 30), (signal.SIGKILL, None)):
            if not owned_group_exists(process.pid):
                break
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            row['owned_group_stop_actions'].append({'signal': sig.name, 'sent_at_utc': now()})
            logging.warning('専用groupの残存子孫を停止待機: pgid=%s signal=%s', process.pid, sig.name)
            write_json(ledger, history)
            deadline = None if timeout is None else time.monotonic()+timeout
            while owned_group_exists(process.pid):
                if deadline is not None and time.monotonic() >= deadline:
                    break
                time.sleep(1)
        row['owned_group_exit_confirmed_at_utc'] = now()
        write_json(ledger, history)
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


def execute(args):
    inputs = OUT / 'input-batches' / f'{args.batch:02d}.json'
    input_receipt = require_inputs(args)
    specs = read(inputs)
    expected_count = 10
    if len(specs) != expected_count:
        raise ValueError('別群batchは全て10件です')
    python = ROOT / ('.venv/bin/python3.12' if args.method in ('hnm', 'world_harvest')
                     else '.cache/references/env/bin/python3.10')
    command = [str(python), str(PACKAGE / 'features.py'),
               '--method', args.method, '--inputs', str(inputs)]
    if args.retry_failed:
        command.append('--retry-failed')
    ledger = OUT / 'processes' / f'{args.method}-{args.batch:02d}.json'
    history = read(ledger) if ledger.exists() else []
    before = inspect_records(args.method, specs, verify=True)
    if any(r['status'] == 'missing' and r['mean_sha256'] for r in before):
        raise ValueError('recordのない孤立meanを保存しています。復旧判断前の上書きはしません')
    if history and history[-1].get('returncode') == 0 and not history[-1].get('supervisor_error'):
        previous = history[-1]
        if previous.get('full_input_receipt') != input_receipt:
            raise ValueError('既存成功時の別群100入力receiptが不一致または未復元です')
        if (not previous.get('child_exit_confirmed_at_utc')
                or not previous.get('owned_group_exit_confirmed_at_utc')
                or not previous.get('scientific_source_receipt') or not verify_previous(previous, command)):
            raise ValueError('既存成功の実終了/source/成果receiptが未復元です')
        if completion_receipt(OUT, args.method, inputs, human=True) != previous['completion_receipt']:
            raise ValueError('既存成功batchの成果receiptが一致しません')
        print(json.dumps({'status': 'verified_existing', 'ledger': str(ledger), 'cases': expected_count}))
        return 0
    if (history or any(r['status'] != 'missing' or r['mean_sha256'] for r in before)) and not args.retry_failed:
        raise ValueError('既存attempt/成果を保存済み。続行は明示的な--retry-failedと理由が必要です')
    attempt = len(history)+1
    log = OUT / 'logs' / f'{args.method}-{args.batch:02d}-attempt{attempt:02d}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {'method': args.method, 'batch': f'{args.batch:02d}', 'attempt': attempt,
        'command': command, 'started_at_utc': now(), 'source_receipt': source_receipt(),
        'command_files': command_files(command), 'full_input_receipt': input_receipt,
        'execution_release_proof': verify_release(OUT / 'preflight-freeze-v3.json', args.batch),
        'supervisor_path': str(Path(__file__)), 'supervisor_sha256': sha256(__file__),
        'runtime_environment_file_sha256': sha256(RUN / 'preparation/runtime-env.sh'),
        'environment': ENVIRONMENT, 'expected_count': expected_count,
        'planned_cases': [spec['id'] for spec in specs], 'existing_case_records': before,
        'retry_failed': args.retry_failed, 'retry_reason': args.retry_reason,
        'checkpoint_policy': 'one batch only; wait for owner checkpoint/next instruction',
        'log': str(log), 'input_manifest_sha256': sha256(inputs), 'resource_before': resource_snapshot()}
    history.append(row)
    write_json(ledger, history)
    process = None
    tick = time.perf_counter()
    try:
        with study_gate(f'availability100-human-{args.method}-{args.batch:02d}') as gate:
            row['study_gate'] = gate
            with (RUN / '.ml-worker.lock').open('a+') as lock:
                row['ml_lock_requested_at_utc'] = now()
                write_json(ledger, history)
                lock_tick = time.perf_counter()
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                row.update(ml_lock_acquired_at_utc=now(), ml_lock_wait_seconds=time.perf_counter()-lock_tick)
                try:
                    if require_inputs(args) != input_receipt or source_receipt() != row['source_receipt']:
                        raise ValueError('待機中に正式入力または科学sourceが変わりました')
                    write_json(ledger, history)
                    with log.open('x') as stream:
                        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, **ENVIRONMENT},
                            stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                        row.update(pid=process.pid, owned_pgid=process.pid, child_started_at_utc=now())
                        write_json(ledger, history)
                        row['returncode'] = process.wait()
                        row['child_exit_confirmed_at_utc'] = now()
                finally:
                    if process is not None:
                        finish_child(process, row, ledger, history)
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                    row['ml_lock_released_at_utc'] = now()
                    write_json(ledger, history)
            contract = OUT / 'feature-contracts' / f'{args.method}.json'
            if contract.exists():
                row['scientific_source_receipt'] = read(contract)['source_sha256']
                row['contract_sha256'] = sha256(contract)
                for relative, digest in row['scientific_source_receipt'].items():
                    check_hash(ROOT / relative, digest)
            if source_receipt() != row['source_receipt'] or require_inputs(args) != input_receipt:
                raise ValueError('正式#13抽出中に科学sourceまたは別群100入力が変わりました')
            if row['returncode'] == 0:
                row['completion_receipt'] = completion_receipt(OUT, args.method, inputs, human=True)
            row['supervisor_returncode'] = row['returncode']
    except BaseException as error:
        row.update(supervisor_error=traceback.format_exc(),
            supervisor_returncode=130 if isinstance(error, KeyboardInterrupt) else 1,
            interrupted=isinstance(error, KeyboardInterrupt))
        raise
    finally:
        row.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter()-tick,
            log_sha256=sha256(log) if log.exists() else None, resource_after=resource_snapshot())
        try:
            row['case_records'] = inspect_records(args.method, specs)
            row['status_counts'] = dict(Counter(record['status'] for record in row['case_records']))
        except Exception:
            row['record_inventory_error'] = traceback.format_exc()
        write_json(ledger, history)
        print(json.dumps({'ledger': str(ledger), 'returncode': row.get('returncode'),
            'supervisor_returncode': row.get('supervisor_returncode'),
            'status_counts': row.get('status_counts'), 'elapsed_seconds': row['elapsed_seconds']}))
    return row['supervisor_returncode']


def on_termination(signum, frame):
    raise KeyboardInterrupt(f'正式#13 supervisor停止signal={signum}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=METHODS, required=True)
    parser.add_argument('--batch', type=int, choices=range(10), required=True)
    parser.add_argument('--preflight-sha256', required=True)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--input-contract-sha256', required=True)
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--retry-reason')
    args = parser.parse_args()
    if args.retry_failed != bool(args.retry_reason and args.retry_reason.strip()):
        parser.error('--retry-failedと空でない--retry-reasonは同時指定が必要です')
    signal.signal(signal.SIGTERM, on_termination)
    lock_path = OUT / 'operation-locks' / f'{args.method}-{args.batch:02d}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute(args)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'availability100-human-batch-supervisor'))
