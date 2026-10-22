"""固定120評価の科学子を一度だけ起動し、実終了と資源を記録する。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback


# 値は固定評価計画のまま。RLIMIT_ASは仮想アドレス空間でありRSSではない。
PHASES = {'native': {'wall_seconds': 1800, 'grace_seconds': 10,
                     'address_space_bytes': 8 * 1024**3, 'threads': 1},
          'quality': {'wall_seconds': 3600, 'grace_seconds': 10,
                      'address_space_bytes': 12 * 1024**3, 'threads': 2}}
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_record(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def free_disk_bytes(path):
    state = os.statvfs(path)
    return state.f_bavail * state.f_frsize


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def send_group(process, sig, actions):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, sig)
        actions.append({'signal': sig.name, 'sent_at_utc': utc_now(),
                        'process_group_id': process.pid})
    except ProcessLookupError:
        pass


def stop_child(process, grace, actions):
    send_group(process, signal.SIGTERM, actions)
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        send_group(process, signal.SIGKILL, actions)
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=PHASES, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('科学子のargvがありません')
    limits = PHASES[args.phase]
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    paths = {name: evidence / name for name in
             ('invocation-start.json', 'invocation.json', 'stdout.log', 'stderr.log')}
    if any(path.exists() for path in paths.values()):
        parser.error('同じ証拠領域の起動履歴を上書きできません')
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    record = {'schema_version': 1, 'kind': 'apron_fixed120_actual_invocation',
              'status': 'starting', 'phase': args.phase, 'argv': command,
              'cwd': str(args.cwd.resolve()), 'started_at_utc': utc_now(),
              'limits': limits, 'launcher_source': file_record(Path(__file__)),
              'thread_environment': {name: os.environ.get(name) for name in THREAD_ENV},
              'python_dont_write_bytecode': os.environ.get('PYTHONDONTWRITEBYTECODE'),
              'rusage_children_before_maxrss_kib': usage_before.ru_maxrss,
              'free_disk_bytes_before': free_disk_bytes(evidence),
              'rss_unit': 'Linux ru_maxrss KiB; RUSAGE_CHILDREN cumulative high-water',
              'reaped_by_launcher': False, 'timed_out': False, 'signals_sent': []}
    write_new(paths['invocation-start.json'], record)
    process = None
    exit_code = 1
    try:
        if sys.platform != 'linux':
            raise RuntimeError('ru_maxrssのKiB単位はLinux環境だけで固定しています')
        if any(os.environ.get(name) != str(limits['threads']) for name in THREAD_ENV):
            raise ValueError('固定thread環境が計画と一致しません')
        if os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
            raise ValueError('PYTHONDONTWRITEBYTECODE=1が必要です')
        if not args.cwd.is_dir():
            raise FileNotFoundError(f'実行directoryがありません: {args.cwd}')
        if not Path(command[0]).is_file() or not os.access(command[0], os.X_OK):
            raise FileNotFoundError(f'科学子の実行ファイルがありません: {command[0]}')

        def limit_address_space():
            maximum = limits['address_space_bytes']
            resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))

        with paths['stdout.log'].open('xb') as stdout, paths['stderr.log'].open('xb') as stderr:
            process = subprocess.Popen(command, cwd=args.cwd, env=os.environ.copy(),
                                       stdout=stdout, stderr=stderr, start_new_session=True,
                                       preexec_fn=limit_address_space)
            child_started = time.perf_counter()
            record.update(status='running', child_pid=process.pid,
                          child_started_at_utc=utc_now())
            try:
                process.wait(timeout=limits['wall_seconds'])
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                stop_child(process, limits['grace_seconds'], record['signals_sent'])
            record['reaped_by_launcher'] = True
            record['child_elapsed_seconds'] = time.perf_counter() - child_started
            record['actual_child_exit_code'] = process.returncode
            record['child_signal'] = -process.returncode if process.returncode < 0 else None
            if record['timed_out']:
                exit_code = 124
            elif process.returncode >= 0:
                exit_code = process.returncode
            else:
                exit_code = 128 - process.returncode
            record['status'] = 'finished'
    except BaseException:
        record['launcher_error'] = traceback.format_exc()
        print(record['launcher_error'], file=sys.stderr, end='')
        if process is not None:
            stop_child(process, limits['grace_seconds'], record['signals_sent'])
            record['reaped_by_launcher'] = True
            record['child_elapsed_seconds'] = time.perf_counter() - child_started
            record['actual_child_exit_code'] = process.returncode
            record['child_signal'] = -process.returncode if process.returncode < 0 else None
        record['status'] = 'launcher_failed'
    finally:
        usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(finished_at_utc=utc_now(), elapsed_seconds=time.perf_counter() - started,
                      launcher_exit_code=exit_code,
                      free_disk_bytes_after=free_disk_bytes(evidence),
                      rusage_children_after_maxrss_kib=usage_after.ru_maxrss,
                      max_rss_kib=(usage_after.ru_maxrss if process is not None
                                   and record['reaped_by_launcher'] and usage_before.ru_maxrss == 0
                                   else None),
                      stdout=file_record(paths['stdout.log']) if paths['stdout.log'].exists() else None,
                      stderr=file_record(paths['stderr.log']) if paths['stderr.log'].exists() else None)
        write_new(paths['invocation.json'], record)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
