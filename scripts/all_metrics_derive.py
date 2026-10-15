"""全8成功nativeの共通16k区間を別データとして固定。原nativeは保持する。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

import numpy as np
import scipy
from scipy.signal import resample_poly

from all_metrics_common import METHODS, ROOT, RUN, audio_info, freeze, now, read, save_audio
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def protocol():
    return {'schema_version': 1, 'target_sample_rate': 16000,
        'source_sha256': sha256(__file__), 'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'resampler': {'function': 'scipy.signal.resample_poly', 'scipy_version': scipy.__version__,
                      'window': ['kaiser', 5.0], 'padtype': 'constant', 'up_down': 'reduced integer ratio'},
        'common_length': 'minimum of original and all eight successful resampled full native waves',
        'minimum_seconds': 1., 'minimum_coverage_every_waveform': .95,
        'missing_method': 'exclude entire case from all-eight primary comparison',
        'alignment': 'none', 'normalization': 'none', 'silence_removal': 'none',
        'native_retained': True, 'status_only_revisions': 'new snapshot after an explicit native retry; prior snapshot retained'}


def sources(spec):
    records = {'original': {'status': 'measured', 'audio': audio_info(spec['path'], spec['sample_rate'])}}
    if records['original']['audio']['file_sha256'] != spec['sha256']:
        raise ValueError('固定原音hash不一致')
    for method in METHODS:
        path = RUN / 'native' / method / spec['id'] / 'unedited.json'
        row = read(path) if path.exists() else {'status': 'pending_native'}
        if path.exists():
            row = {**row, 'record_path': str(path), 'record_sha256': sha256(path)}
        if row['status'] == 'measured':
            actual = audio_info(row['audio']['path'], row['audio']['sample_rate'])
            if actual['file_sha256'] != row['audio']['file_sha256']:
                raise ValueError('native出力hash不一致')
        records[method] = row
    return records


def derive_one(spec, records, snapshot, signature):
    folder = RUN / 'derived16' / snapshot / spec['id']
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'contract_sha256': signature,
           'source_records': records, 'planned_methods': list(METHODS), 'status': 'upstream_failed'}
    if any(record['status'] != 'measured' for record in records.values()):
        row['reason'] = '全8成功nativeがないため共通区間を決めない'
        freeze(folder / 'derivation.json', row)
        return row
    full, waves = {}, {}
    for method, record in records.items():
        source = record['audio']
        wave = np.load(source['path'], allow_pickle=False).astype(np.float64)
        divisor = math.gcd(source['sample_rate'], 16000)
        if source['sample_rate'] != 16000:
            wave = resample_poly(wave, 16000 // divisor, source['sample_rate'] // divisor,
                                 window=('kaiser', 5.0), padtype='constant')
        path = folder / 'full' / f'{method}.npy'
        if path.exists():
            saved = audio_info(path, 16000)
            if saved['float64_sha256'] != hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest():
                raise ValueError('既存16k派生PCMが一致しません')
        else:
            saved = save_audio(path, wave, 16000)
        waves[method] = wave
        full[method] = {'source': source, 'derived': saved, 'up': 16000 // divisor,
                        'down': source['sample_rate'] // divisor}
    n = min(len(wave) for wave in waves.values())
    coverage = {method: n / len(wave) for method, wave in waves.items()}
    row.update(full_length_derivations=full, common_samples=n, common_seconds=n / 16000, coverage=coverage,
               omitted_tail_samples={method: len(wave) - n for method, wave in waves.items()})
    if n < 16000 or min(coverage.values()) < .95:
        row.update(status='not_applicable', reason='事前1秒/全波形95%coverage条件を満たさない')
    else:
        common = {}
        for method, wave in waves.items():
            path = folder / 'common' / f'{method}.npy'
            if path.exists():
                saved = audio_info(path, 16000)
                if saved['float64_sha256'] != hashlib.sha256(wave[:n].astype('<f8').tobytes()).hexdigest():
                    raise ValueError('既存共通区間PCMが一致しません')
            else:
                saved = save_audio(path, wave[:n], 16000)
            common[method] = saved
        row.update(status='measured', common=common)
    freeze(folder / 'derivation.json', row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--finalize-native-failures', action='store_true',
                        help='このbatchのnative再試行を確定し、失敗caseを全8主比較から除外してsnapshotを固定')
    args = parser.parse_args()
    specs = read(RUN / f'input-batches/{args.batch:02d}.json')
    all_sources = {spec['id']: sources(spec) for spec in specs}
    states = [record['status'] for records in all_sources.values() for record in records.values()]
    if any(state.startswith('pending') for state in states):
        write_json(RUN / f'derivation-progress/{args.batch:02d}.json', {'status': 'pending_native', 'updated_at_utc': now()})
        return 1
    if any(state != 'measured' for state in states) and not args.finalize_native_failures:
        raise ValueError('native失敗あり。再試行を終えてから明示--finalize-native-failuresで確定してください')
    contract = protocol()
    freeze(RUN / 'derived16/contract.json', contract)
    signature = sha256(RUN / 'derived16/contract.json')
    snapshot = hashlib.sha256(json.dumps([signature, all_sources], sort_keys=True).encode()).hexdigest()
    rows = [derive_one(spec, all_sources[spec['id']], snapshot, signature) for spec in specs]
    cases = [{'id': row['case'], 'speaker': row['speaker'], 'language': 'en', 'style': 'normal',
              'kind': 'natural_speech', 'sample_rate': 16000, 'reference': row['common']['original']['path'],
              'outputs': {method: row['common'][method]['path'] for method in METHODS}}
             for row in rows if row['status'] == 'measured']
    manifest = {'schema_version': 1, 'baseline': 'hnm', 'formal_base': read(ROOT / 'BASELINE.json'),
                'comparison_contract_sha256': signature, 'snapshot': snapshot, 'cases': cases}
    immutable = RUN / 'quality-inputs/snapshots' / snapshot / f'common-{args.batch:02d}.json'
    freeze(immutable, manifest)
    freeze(immutable.parent / 'derivation-rows.json', rows)
    active = RUN / f'quality-inputs/common-{args.batch:02d}.json'
    if active.exists() and read(active) != manifest:
        write_json(active.parent / 'history' / f'common-{args.batch:02d}-{time.time_ns()}.json', read(active))
    write_json(active, manifest)
    write_json(RUN / f'derivation-progress/{args.batch:02d}.json', {'status': 'finalized',
        'updated_at_utc': now(), 'snapshot': snapshot, 'manifest_path': str(immutable),
        'manifest_sha256': sha256(immutable), 'planned_cases': len(specs), 'common_cases': len(cases),
        'native_failures_explicitly_finalized': args.finalize_native_failures})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-derive'))
