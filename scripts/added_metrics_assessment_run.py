"""正式な追加評価を10録音ずつ実行し、部分測定も全予定件数に残す。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'runs/added-metrics-20261014'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['acoustic', 'curves'])
    args = parser.parse_args()
    path = RUN/f'assessment-{args.stage}-processes.json'
    history = json.loads(path.read_text()) if path.exists() else []
    for batch in range(12):
        if any(row['batch'] == batch and row.get('finished_at_utc') for row in history):
            continue
        manifest = RUN/f'assessment-{args.stage}-inputs/manifest-{batch:02d}.json'
        output = RUN/f'assessment-{args.stage}-{batch:02d}'
        command = [sys.executable, '-m', 'vocoderbench.assessment', '--manifest', str(manifest),
                   '--output', str(output), '--repetitions', '1']
        logfile = RUN/f'assessment-{args.stage}-{batch:02d}.log'
        item = {'batch': batch, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'command': command, 'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                'log': str(logfile.relative_to(RUN))}
        history.append(item)
        path.write_text(json.dumps(history, indent=2))
        started = time.perf_counter()
        with logfile.open('w') as stream:
            item['returncode'] = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                env=dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4')).returncode
        item.update(finished_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter()-started)
        result = output/'results.json'
        if result.exists():
            data = json.loads(result.read_text())
            item.update(counts=data.get('counts'), saved_jobs=len(data['rows']),
                        planned_jobs=len(json.loads(manifest.read_text())['jobs']))
        path.write_text(json.dumps(history, indent=2))
        print(f'{args.stage} {batch+1}/12: {item}', flush=True)
    return int(any(r['returncode'] != 0 for r in history))


if __name__ == '__main__':
    raise SystemExit(main())
