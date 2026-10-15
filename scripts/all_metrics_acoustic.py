"""固定共通16k区間へ既存音響群と40ms局所ERBを適用し、全予定行を保存する。"""
from __future__ import annotations

import argparse
from pathlib import Path
import time
import traceback

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from vocoderbench.assessment.acoustics import auditory
from vocoderbench.assessment.common import NotApplicable
from vocoderbench.extended_metrics import measure_extended
from vocoderbench.logging_utils import run_cli
from vocoderbench.metrics import compare_waveforms
from vocoderbench.quality_core import environment, sha256, write_json


def contract():
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_derive.py',
             ROOT / 'vocoderbench/metrics.py', ROOT / 'vocoderbench/extended_metrics.py',
             ROOT / 'vocoderbench/temporal_metrics.py', ROOT / 'vocoderbench/assessment/acoustics.py',
             ROOT / 'vocoderbench/assessment/common.py']
    return {'schema_version': 1, 'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths},
            'environment': environment(), 'derivation_contract_sha256': sha256(RUN / 'derived16/contract.json'),
            'input_contract_sha256': sha256(RUN / 'input-contract.json'),
            'scope': 'all-eight common 16k prefix; no alignment or normalization; native length/coverage shown separately',
            'natural_f0_truth': None, 'estimated_pitch_consistency': True,
            'auditory_local': 'existing 40ms Hann / 5ms hop / 32 ERB triangles',
            'diagnostics_not_quality_ranks': ['signed RMS bias', 'quiet output energy fraction', 'quiet RMS/peak'],
            'raw_families_are_not_independent_votes': True}


class Pair:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def pair(self, job):
        return self.x, self.y, 16000


def evaluate_one(spec, method, snapshot, signature, retry):
    path = RUN / 'acoustic/measurements' / f'{spec["id"]}__{method}.json'
    derived = RUN / 'derived16' / snapshot / spec['id'] / 'derivation.json'
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'condition': 'unedited',
           'contract_sha256': signature, 'derivation_snapshot': snapshot, 'status': 'pending_derivation',
           'value': None, 'started_at_utc': now()}
    if path.exists():
        previous = read(path)
        if previous['contract_sha256'] != signature:
            raise ValueError('既存音響計測のsource/科学契約不一致')
        same = previous['derivation_snapshot'] == snapshot
        if same and previous['status'] == 'measured':
            if sha256(derived) != previous['derivation_record_sha256']:
                raise ValueError('保存済み共通派生証拠のhash不一致')
            for info in previous['inputs'].values():
                if sha256(info['path']) != info['file_sha256']:
                    raise ValueError('保存済み音響入力hash不一致')
            return previous
        if same and previous['status'] == 'failed' and not retry:
            return previous
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', previous)
    if derived.exists():
        derivation = read(derived)
        row.update(derivation_record=str(derived), derivation_record_sha256=sha256(derived),
                   coverage=derivation.get('coverage'), common_seconds=derivation.get('common_seconds'))
        if derivation['status'] != 'measured':
            row.update(status=derivation['status'], reason=derivation.get('reason'))
        else:
            try:
                inputs = {'reference': derivation['common']['original'], 'output': derivation['common'][method]}
                waves = {}
                for key, info in inputs.items():
                    if sha256(info['path']) != info['file_sha256']:
                        raise ValueError('共通区間音声hash不一致')
                    waves[key] = np.load(info['path'], allow_pickle=False).astype(np.float64)
                start, cpu = time.perf_counter(), time.process_time()
                x, y = waves['reference'], waves['output']
                comparison = compare_waveforms(x, y, 16000)
                extended = measure_extended(x, y, 16000, include_pitch=True, include_temporal=True, is_speech=True)
                try:
                    local = auditory({}, Pair(x, y))
                except NotApplicable as error:
                    local = {'status': 'not_applicable', 'value': None, 'reason': str(error)}
                row.update(status='measured', inputs=inputs, measurement=comparison,
                           extended=extended, auditory_local=local,
                           wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu)
            except Exception:
                row.update(status='failed', error=traceback.format_exc())
    row['finished_at_utc'] = now()
    write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    manifest = read(RUN / f'quality-inputs/common-{args.batch:02d}.json')
    snapshot = manifest['snapshot']
    freeze(RUN / 'acoustic/contract.json', contract())
    signature = sha256(RUN / 'acoustic/contract.json')
    specs = read(RUN / f'input-batches/{args.batch:02d}.json')
    rows = [evaluate_one(spec, method, snapshot, signature, args.retry_failed) for spec in specs for method in METHODS]
    write_json(RUN / f'acoustic/batch-{args.batch:02d}.json', {'snapshot': snapshot, 'rows': rows,
               'contract_sha256': signature, 'planned_cases': len(specs), 'planned_rows': len(specs) * len(METHODS)})
    return int(any(row['status'].startswith('pending') or row['status'] == 'failed' for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-acoustic'))
