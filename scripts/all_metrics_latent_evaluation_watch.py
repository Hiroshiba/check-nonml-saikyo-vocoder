"""B/C完了とMOS/ECAPA到着に応じて保存済み正式指標を再集約する。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_latent_evaluation_common import POINTS
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def source_state(specs, method):
    sources = []
    ready = True
    for spec in specs:
        folder = RUN / 'native' / method / spec['id']
        for stage in ('quantization', 'interpolation'):
            progress = folder / f'latent-{stage}-progress.json'
            if not progress.exists() or not read(progress).get('conditions'):
                ready = False
        conditions = list(POINTS)
        if method != 'facodec':
            conditions += [p + '__' + edit for p in POINTS[1:3]
                           for edit in ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6')]
        for condition in conditions:
            source = folder / f'{condition}.json'
            if source.exists() and source.stat().st_size > 1024 * 1024:
                ready = False
                sources.append((str(source), 'awaiting_compact_native_metadata'))
            else:
                sources.append((str(source), sha256(source) if source.exists() else None))
        for condition in POINTS:
            for name in ('mos', 'mos-latent', 'speaker-full', 'latent-speaker'):
                source = RUN / name / 'measurements' / f'{spec["id"]}__{method}__{condition}.json'
                sources.append((str(source), sha256(source) if source.exists() else None))
    return ready, hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()


def execute(batch, method):
    command = [str(ROOT / '.venv/bin/python3.12'), 'scripts/all_metrics_latent_evaluation_storage.py',
               '--batch', str(batch), '--methods', method]
    target = RUN / 'latent-evaluation-watch/executions' / f'{method}-{batch:02d}-{time.time_ns()}.json'
    log = target.with_suffix('.log')
    row = {'command': command, 'batch': batch, 'method': method, 'at_utc': now(),
        'operational_source_sha256': sha256(__file__), 'log': str(log),
        'scope': 'No model inference; fixed attribute/auditory/control evaluation and joining existing quality evidence'}
    write_json(target, row)
    with log.open('w') as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
            env={**os.environ, 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2'})
        _, status, usage = os.wait4(process.pid, 0)
        process.returncode = os.waitstatus_to_exitcode(status)
    row.update(returncode=process.returncode, finished_at_utc=now(), log_sha256=sha256(log),
        rusage={'max_rss_kib': usage.ru_maxrss, 'user_cpu_seconds': usage.ru_utime,
                'system_cpu_seconds': usage.ru_stime})
    write_json(target, row)
    if process.returncode:
        raise RuntimeError(f'正式表現指標の集約失敗、ログを保持して停止: {log}')


def main():
    previous_path = RUN / 'latent-evaluation-watch/observed.json'
    previous = read(previous_path) if previous_path.exists() else {}
    while True:
        pending = []
        updated = False
        for batch in range(12):
            specs = read(RUN / f'input-batches/{batch:02d}.json')
            for method in METHODS:
                ready, signature = source_state(specs, method)
                key = f'{method}-{batch:02d}'
                if not ready:
                    pending.append({'batch': batch, 'method': method, 'reason': 'pending_BC_or_metadata'})
                    continue
                if previous.get(key) != signature:
                    execute(batch, method)
                    previous[key] = signature
                    write_json(previous_path, previous)
                    updated = True
                for spec in specs:
                    result = read(RUN / 'latent-evaluation/measurements' / f'{spec["id"]}__{method}.json')
                    if result['status'].startswith('pending'):
                        pending.append({'case': spec['id'], 'method': method, 'reason': 'pending_quality'})
        if updated:
            subprocess.run([str(ROOT / '.venv/bin/python3.12'), 'scripts/all_metrics_latent_groups.py'],
                           cwd=ROOT, check=True)
        write_json(RUN / 'latent-evaluation-watch/status.json', {
            'status': 'waiting_measurements' if pending else 'completed', 'at_utc': now(), 'pending': pending})
        if not pending:
            return 0
        time.sleep(60)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-evaluation-watch'))
