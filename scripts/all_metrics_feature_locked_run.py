"""凍結features driverを無変更で動かし、重いML子processだけ共有flockで直列化。"""
from __future__ import annotations

import fcntl
import logging
from pathlib import Path
import resource
import subprocess
import time
import traceback

from all_metrics_common import RUN, now
from vocoderbench.quality_core import sha256, write_json

ML_METHODS = {'facodec', 'hifiglot', 'golf', 'sifigan'}
ORIGINAL_POPEN = subprocess.Popen


def cgroup():
    result = {}
    for name in ('memory.current', 'memory.peak', 'memory.events'):
        path = Path('/sys/fs/cgroup') / name
        try:
            result[name] = path.read_text().strip()
        except OSError:
            result[name] = None
    return result


class LockedPopen(ORIGINAL_POPEN):
    def __init__(self, args, *positional, **kwargs):
        self.ml_lock = None
        self.lock_record = None
        if isinstance(args, (list, tuple)) and '--method' in args:
            method = args[args.index('--method')+1]
            if method in ML_METHODS:
                started = time.perf_counter()
                self.lock_record = {'method': method, 'command': args,
                    'requested_at_utc': now(), 'lock': str(RUN / '.ml-worker.lock'),
                    'wrapper_sha256': sha256(Path(__file__)),
                    'cgroup_before': cgroup(),
                    'resource_scope': 'RUSAGE_CHILDREN maxrss is cumulative for this wrapper; '
                                      'cgroup peak/events include all processes in the cgroup; no OOM-cause claim'}
                self.lock_path = RUN / 'readout-train/lock-ledger' / f'{method}-{time.time_ns()}.json'
                write_json(self.lock_path, self.lock_record)
                self.ml_lock = (RUN / '.ml-worker.lock').open('a+')
                logging.info('共有ML lockを待機: %s', method)
                fcntl.flock(self.ml_lock.fileno(), fcntl.LOCK_EX)
                self.lock_record.update(acquired_at_utc=now(), wait_seconds=time.perf_counter()-started)
                write_json(self.lock_path, self.lock_record)
        try:
            super().__init__(args, *positional, **kwargs)
        except Exception:
            if self.lock_record is not None:
                self.lock_record['start_error'] = traceback.format_exc()
            self.release_lock()
            raise

    def release_lock(self):
        if self.ml_lock is not None:
            self.lock_record.update(released_at_utc=now(), returncode=getattr(self, 'returncode', None),
                children_cumulative_ru_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                cgroup_after=cgroup())
            write_json(self.lock_path, self.lock_record)
            fcntl.flock(self.ml_lock.fileno(), fcntl.LOCK_UN)
            self.ml_lock.close()
            self.ml_lock = None

    def wait(self, timeout=None):
        result = super().wait(timeout=timeout)
        self.release_lock()
        return result


def main():
    import all_metrics_features_run
    subprocess.Popen = LockedPopen
    try:
        return all_metrics_features_run.main()
    finally:
        subprocess.Popen = ORIGINAL_POPEN


if __name__ == '__main__':
    from vocoderbench.logging_utils import run_cli
    raise SystemExit(run_cli(main, 'all-metrics-feature-locked'))
