"""新runの速度phaseを他の正式研究processから分離し、資源設定を記録する。"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
from functools import wraps
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

from all_metrics_common import ROOT, RUN, now
from vocoderbench.quality_core import sha256, write_json


def resource_snapshot():
    limits = {}
    for name in ('cpu.max', 'cpuset.cpus.effective', 'memory.max', 'memory.current', 'memory.peak', 'memory.events'):
        path = Path('/sys/fs/cgroup') / name
        try:
            limits[name] = path.read_text().strip()
        except OSError:
            limits[name] = None
    cpu = Path('/proc/cpuinfo').read_text()
    return {'pid': os.getpid(), 'platform': platform.platform(), 'cpu_count': os.cpu_count(),
            'cpu_model_names': sorted({line.split(':', 1)[1].strip() for line in cpu.splitlines()
                                      if line.startswith('model name')}),
            'affinity': sorted(os.sched_getaffinity(0)), 'cgroup': limits,
            'scope': 'This task process/cgroup snapshot; shared-host outside load is not controlled.'}


@contextmanager
def study_gate(label, native=False):
    """native phaseはexclusive、他stageはshared。ML/ViSQOL排他より先に取得する。"""
    RUN.mkdir(parents=True, exist_ok=True)
    path = RUN / 'resource-gates' / f'{label}-{os.getpid()}-{time.time_ns()}.json'
    lock_path = RUN / '.native-timing-phase.lock'
    record = {'label': label, 'exclusive_native_phase': native, 'pid': os.getpid(),
              'requested_at_utc': now(), 'gate_path': str(lock_path),
              'source_sha256': sha256(Path(__file__)), 'cwd': str(ROOT)}
    write_json(path, record)
    tick = time.perf_counter()
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if native else fcntl.LOCK_SH)
        record.update(acquired_at_utc=now(), wait_seconds=time.perf_counter() - tick,
                      before=resource_snapshot())
        write_json(path, record)
        try:
            yield record
        finally:
            record.update(released_at_utc=now(), after=resource_snapshot())
            write_json(path, record)
            fcntl.flock(lock, fcntl.LOCK_UN)


def shared_stage(label):
    """native速度phase以外の正式計測入口に使う。"""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with study_gate(label):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def stop_owned_child(process):
    """start_new_session=Trueで起動した当該childだけを停止し終了を確認する。"""
    actions = []
    for sig, timeout in ((signal.SIGINT, 60), (signal.SIGTERM, 30), (signal.SIGKILL, None)):
        if process.poll() is not None:
            break
        try:
            os.killpg(process.pid, sig)
            actions.append({'signal': sig.name, 'sent_at_utc': now(), 'owned_pgid': process.pid})
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
    return {'child_returncode': process.wait(), 'child_exit_confirmed_at_utc': now(),
            'stop_actions': actions}
