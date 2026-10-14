"""表現関連の正式研究を10録音processに分け、停止・再開履歴を保存する。"""
from __future__ import annotations

import argparse
import resource
import shutil
import time
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_run import run_process
from vocoderbench.quality_core import sha256, write_json


def run_guarded(stage, batch, method, command):
    """科学条件と分離した容量gate・ML排他・process資源の運用記録。"""
    locked = stage == 'speaker' or method in ('facodec', 'hifiglot', 'golf', 'sifigan')
    path = RUN / 'latent-operations' / f'{stage}-{method}-{batch:02d}-{time.time_ns()}.json'
    record = {'stage': stage, 'method': method, 'batch': batch, 'started_at_utc': now(),
              'ml_exclusive': locked, 'lock_path': str(RUN / '.ml-worker.lock') if locked else None,
              'operational_source_sha256': sha256(__file__)}
    # 排他順序は共通run_processが study gate→ML lock として管理する。
    record['lock_owner'] = 'all_metrics_run.run_process'
    record['free_bytes_before'] = shutil.disk_usage(RUN).free
    if record['free_bytes_before'] < 2 * 1024**3:
        write_json(path, {**record, 'status': 'blocked_free_space', 'minimum_free_bytes': 2 * 1024**3})
        return 75
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        code = run_process('latent-' + stage, batch, method, command)
        record.update(status='finished', returncode=code)
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(finished_at_utc=now(), free_bytes_after=shutil.disk_usage(RUN).free,
            children_user_cpu_delta_seconds=after.ru_utime - before.ru_utime,
            children_system_cpu_delta_seconds=after.ru_stime - before.ru_stime,
            children_peak_rss_kib_cumulative_high_water=after.ru_maxrss,
            peak_rss_scope='high water of all completed children of this driver, not a subtractable per-case maximum')
        write_json(path, record)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('features', 'quantization', 'interpolation', 'time', 'speaker'))
    parser.add_argument('--methods', nargs='+', default=list(METHODS))
    parser.add_argument('--start-batch', type=int, default=0)
    parser.add_argument('--end-batch', type=int, default=12)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if args.stage == 'features':
        raise ValueError('新runのnative特徴はsynthesisが所有します。保存nativeからの再抽出はsynthesis --unedited-only --retry-failedを使ってください')
    failures, pending = [], []
    for batch in range(args.start_batch, args.end_batch):
        if args.stage == 'speaker':
            if args.methods != list(METHODS):
                raise ValueError('統合全長ECAPA入口は全8方式を1batchずつ処理します')
            command = [str(ROOT / '.venv/bin/python3.12'),
                       str(ROOT / 'scripts/all_metrics_control_eval_speaker.py'), '--scope', 'latent', '--batch', str(batch)]
            if args.retry_failed:
                command.append('--retry-failed')
            code = run_guarded('speaker', batch, 'all8', command)
            if code:
                failures.append([batch, 'all8', code])
            continue
        inputs = RUN / f'input-batches/{batch:02d}.json'
        for method in args.methods:
            if args.stage in ('features', 'time') and method not in METHODS[:2]:
                raise ValueError('既存特徴export・時間操作はHNM/WORLDのみ')
            if any(
                not (RUN / 'native' / method / case['id'] / 'unedited.json').exists() or
                read(RUN / 'native' / method / case['id'] / 'unedited.json').get('status', 'pending').startswith('pending')
                for case in read(inputs)):
                pending.append([batch, method, 'native waveform pending'])
                continue
            python = (ROOT / '.venv/bin/python3.12'
                      if method in METHODS[:2] else ROOT / '.cache/references/env/bin/python3.10')
            script = 'all_metrics_latent_features.py' if args.stage == 'features' else 'all_metrics_latent_worker.py'
            command = [str(python), str(ROOT / 'scripts' / script), '--method', method,
                '--inputs', str(inputs), '--output-root', str(RUN),
                '--runtime-cache', str(ROOT / '.cache/references')]
            if args.stage != 'features':
                command += ['--stage', args.stage, '--threads', '2', '--seed', '0']
            if args.retry_failed:
                command.append('--retry-failed')
            code = run_guarded(args.stage, batch, method, command)
            if code:
                failures.append([batch, method, code])
    output = RUN / f'latent-{args.stage}-execution-summary-{args.start_batch:02d}-{args.end_batch:02d}.json'
    write_json(Path(output), {'finished_at_utc': now(), 'failures': failures, 'pending': pending,
        'start_batch': args.start_batch, 'end_batch': args.end_batch, 'methods': args.methods})
    return int(bool(failures or pending))


if __name__ == '__main__':
    raise SystemExit(main())
