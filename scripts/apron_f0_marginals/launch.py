"""固定pYIN周辺支持診断の科学子を一度だけ起動し、実終了と資源を記録する。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
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
PHASES = {'extract': {'wall_seconds': 1800, 'grace_seconds': 10,
                      'address_space_bytes': 8 * 1024**3, 'threads': 1},
          'analyze': {'wall_seconds': 3600, 'grace_seconds': 10,
                      'address_space_bytes': 8 * 1024**3, 'threads': 1},
          'summarize': {'wall_seconds': 3600, 'grace_seconds': 10,
                        'address_space_bytes': 8 * 1024**3, 'threads': 1}}
MIN_FREE_BYTES = 4 * 1024**3
NEW_RUN_CAP_BYTES = 2 * 1024**3

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


def retained_bytes(path):
    return sum(item.stat().st_size for item in path.rglob('*') if item.is_file())


def available_memory_bytes():
    host = None
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            host = int(line.split()[1]) * 1024
            break
    if host is None:
        raise RuntimeError('/proc/meminfoにMemAvailableがありません')
    maximum = Path('/sys/fs/cgroup/memory.max')
    current = Path('/sys/fs/cgroup/memory.current')
    if maximum.is_file() and current.is_file():
        limit = maximum.read_text().strip()
        if limit != 'max':
            host = min(host, int(limit) - int(current.read_text().strip()))
    return host


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def send_group(process_group_id, sig, actions):
    action = {'signal': sig.name, 'sent_at_utc': utc_now(),
              'process_group_id': process_group_id}
    try:
        os.killpg(process_group_id, sig)
        action['delivered'] = True
    except ProcessLookupError:
        action['delivered'] = False
    actions.append(action)


def stop_child(process, grace, actions):
    """親のwaitまでleaderをreapせず、同じprocess groupへのKILLを保証する。"""
    if process.returncode is not None:
        return
    send_group(process.pid, signal.SIGTERM, actions)
    time.sleep(grace)
    send_group(process.pid, signal.SIGKILL, actions)
    process.wait()


def wait_child(process, wall_seconds, grace_seconds, record, signals, run_root):
    deadline = time.monotonic() + wall_seconds
    next_size_check = time.monotonic()
    while True:
        if signals['first'] is not None:
            stop_child(process, grace_seconds, record['signals_sent'])
            record['status'] = 'interrupted'
            record['interruption_reason'] = signal.Signals(signals['first']).name
            return 128 + signals['first']
        # WNOWAIT leaves the leader's PID reserved until group cleanup or normal wait.
        ended = os.waitid(os.P_PID, process.pid,
                          os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if ended is not None:
            if signals['first'] is not None:
                continue
            process.wait()
            if signals['first'] is not None:
                record['status'] = 'interrupted_after_child_exit'
                record['interruption_reason'] = signal.Signals(signals['first']).name
                return 128 + signals['first']
            record['status'] = 'finished'
            return (process.returncode if process.returncode >= 0
                    else 128 - process.returncode)
        if time.monotonic() >= next_size_check:
            used = retained_bytes(run_root)
            record['last_observed_new_run_bytes'] = used
            next_size_check = time.monotonic() + 2.0
            if used > NEW_RUN_CAP_BYTES:
                record['retained_budget_exceeded'] = True
                record['retained_budget_exceeded_observed_at_utc'] = utc_now()
                record['status'] = 'retained_budget_exceeded'
                stop_child(process, grace_seconds, record['signals_sent'])
                return 125
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            record['timed_out'] = True
            stop_child(process, grace_seconds, record['signals_sent'])
            record['status'] = 'timed_out'
            return 124
        time.sleep(min(remaining, 0.25))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=PHASES, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--run-root', type=Path, required=True)
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
    record = {'schema_version': 1, 'kind': 'apron_f0_marginals_actual_invocation',
              'status': 'starting', 'phase': args.phase, 'argv': command,
              'cwd': str(args.cwd.resolve()), 'started_at_utc': utc_now(),
              'run_root': str(args.run_root.resolve()),
              'limits': limits, 'launcher_source': file_record(Path(__file__)),
              'thread_environment': {name: os.environ.get(name) for name in THREAD_ENV},
              'python_dont_write_bytecode': os.environ.get('PYTHONDONTWRITEBYTECODE'),
              'rusage_children_before_maxrss_kib': usage_before.ru_maxrss,
              'free_disk_bytes_before': free_disk_bytes(evidence),
              'memory_available_bytes_before': available_memory_bytes(),
              'rss_unit': 'Linux ru_maxrss KiB; RUSAGE_CHILDREN cumulative high-water',
              'reaped_by_launcher': False, 'timed_out': False, 'signals_sent': []}
    signals = {'first': None, 'count': 0, 'last': None}
    record['termination_signals_received'] = signals

    def request_termination(signum, _frame):
        signals['count'] += 1
        signals['last'] = signal.Signals(signum).name
        if signals['first'] is None:
            signals['first'] = signum

    signal.signal(signal.SIGTERM, request_termination)
    signal.signal(signal.SIGHUP, request_termination)
    write_new(paths['invocation-start.json'], record)
    process = None
    slot_stream = None
    exit_code = 1
    try:
        if sys.platform != 'linux':
            raise RuntimeError('ru_maxrssのKiB単位はLinux環境だけで固定しています')
        if any(os.environ.get(name) != str(limits['threads']) for name in THREAD_ENV):
            raise ValueError('固定thread環境が計画と一致しません')
        if os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
            raise ValueError('PYTHONDONTWRITEBYTECODE=1が必要です')
        if free_disk_bytes(evidence) < MIN_FREE_BYTES:
            raise RuntimeError('開始前の空き容量が4GiB未満です')
        if available_memory_bytes() < MIN_FREE_BYTES:
            raise RuntimeError('開始前のMemAvailableが4GiB未満です')
        if not args.run_root.is_dir() or not evidence.is_relative_to(args.run_root.resolve()):
            raise RuntimeError('証拠directoryが固定新run内にありません')
        for slot in range(2):
            candidate = (args.run_root / f'concurrency-slot-{slot}.lock').open('a+')
            try:
                fcntl.flock(candidate.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                candidate.close()
                continue
            slot_stream = candidate
            record['concurrency_slot'] = slot
            break
        if slot_stream is None:
            raise RuntimeError('固定上限の同時2科学子がすでに稼働中です')
        if not args.cwd.is_dir():
            raise FileNotFoundError(f'実行directoryがありません: {args.cwd}')
        if not Path(command[0]).is_file() or not os.access(command[0], os.X_OK):
            raise FileNotFoundError(f'科学子の実行ファイルがありません: {command[0]}')
        if signals['first'] is not None:
            raise RuntimeError(f'科学子起動前に{signals["last"]}を受信しました')

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
            exit_code = wait_child(process, limits['wall_seconds'],
                                   limits['grace_seconds'], record, signals,
                                   args.run_root)
            record['reaped_by_launcher'] = True
            record['child_elapsed_seconds'] = time.perf_counter() - child_started
            record['actual_child_exit_code'] = process.returncode
            record['child_signal'] = -process.returncode if process.returncode < 0 else None
    except BaseException:
        record['launcher_error'] = traceback.format_exc()
        print(record['launcher_error'], file=sys.stderr, end='')
        if process is not None and process.returncode is None:
            stop_child(process, limits['grace_seconds'], record['signals_sent'])
            record['reaped_by_launcher'] = True
            record['child_elapsed_seconds'] = time.perf_counter() - child_started
            record['actual_child_exit_code'] = process.returncode
            record['child_signal'] = -process.returncode if process.returncode < 0 else None
        if signals['first'] is not None:
            exit_code = 128 + signals['first']
            record['status'] = 'interrupted'
            record['interruption_reason'] = signal.Signals(signals['first']).name
        else:
            record['status'] = 'launcher_failed'
    finally:
        # 直接子の処理後は証拠の閉鎖を優先し、追加信号で書込みを中断させない。
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        if slot_stream is not None:
            fcntl.flock(slot_stream.fileno(), fcntl.LOCK_UN)
            slot_stream.close()
        if signals['first'] is not None and record['status'] == 'finished':
            record['status'] = 'interrupted_after_child_exit'
            record['interruption_reason'] = signal.Signals(signals['first']).name
            exit_code = 128 + signals['first']
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
        record['retained_new_run_bytes_before_final_receipt'] = retained_bytes(args.run_root)
        if record['retained_new_run_bytes_before_final_receipt'] > NEW_RUN_CAP_BYTES:
            record['retained_budget_exceeded'] = True
            if exit_code == 0:
                exit_code = 2
                record['launcher_exit_code'] = exit_code
                record['status'] = 'retained_budget_exceeded'
        write_new(paths['invocation.json'], record)
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
