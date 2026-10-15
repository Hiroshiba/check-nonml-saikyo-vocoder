"""native全長と固定原音全長のECAPA。共通prefix話者指標と混合しない。"""
from __future__ import annotations

import argparse
import hashlib
import logging
import math
from pathlib import Path
import random
import time
import traceback

import numpy as np
from scipy.signal import resample_poly

from all_metrics_common import METHODS, ROOT, RUN, audio_info, freeze, now, read
from all_metrics_resources import shared_stage
from all_metrics_control_eval import native_conditions, original
from all_metrics_control_eval_equivalence import verified_record
from all_metrics_controls import checked_audio
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_backends import EcapaSimilarity
from vocoderbench.quality_core import NotApplicable, check_output, environment, offline_environment, sha256, write_json

LATENT = ('quantized_float16', 'quantized_float32', 'interpolation_input_gain_alpha0',
          'interpolation_input_gain_alpha0p5', 'interpolation_input_gain_alpha1')


def configuration(model):
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_controls.py', ROOT / 'scripts/all_metrics_control_eval.py',
             ROOT / 'vocoderbench/quality_backends.py', ROOT / 'vocoderbench/quality_core.py']
    return {'schema_version': 2, 'evaluator': 'ECAPA-TDNN raw embedding cosine',
        'embedding_model': str(model), 'embedding_model_sha256': sha256(model),
        'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        'environment': environment(), 'seed': 20261014, 'threads': 2, 'repetitions': 1,
        'reference': 'same fixed original excerpt full length; not entire original corpus utterance',
        'output': 'full native waveform, independently resampled to16k; no common-prefix crop',
        'resampling': {'function': 'scipy.signal.resample_poly', 'window': ['kaiser', 5.0], 'padtype': 'constant'},
        'normalization': 'backend official per-sentence mean normalization; no waveform level normalization',
        'alignment': 'none', 'full_length_distinct_from_primary_common16_ecapa': True}


def to16(wave, rate):
    divisor = math.gcd(rate, 16000)
    converted = resample_poly(wave, 16000 // divisor, rate // divisor, window=('kaiser', 5.0), padtype='constant')
    evidence = {'input_rate': rate, 'input_samples': len(wave), 'output_rate': 16000,
                'output_samples': len(converted), 'up': 16000 // divisor, 'down': rate // divisor,
                'float64_sha256': hashlib.sha256(converted.astype('<f8').tobytes()).hexdigest(),
                'float32_sha256': hashlib.sha256(converted.astype('<f4').tobytes()).hexdigest()}
    return converted, evidence


def evaluate(spec, method, condition, folder, signature, backend, retry_failed):
    path = RUN / folder / 'measurements' / f'{spec["id"]}__{method}__{condition}.json'
    source = RUN / 'native' / method / spec['id'] / f'{condition}.json'
    previous = read(path) if path.exists() else None
    if previous:
        if previous['configuration_sha256'] != signature:
            raise ValueError('全長ECAPA評価器条件が変わりました')
        if sha256(spec['path']) != spec['sha256']:
            raise ValueError('ECAPA再読時に固定原音fileのhashが変わりました')
        if previous['status'] == 'measured' or (not previous['status'].startswith('pending') and not retry_failed):
            if previous.get('source_record_sha256'):
                verified_record(source, previous['source_record_sha256'], RUN / folder / 'storage-equivalence')
            return previous
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', previous)
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'condition': condition,
           'status': 'pending_audio', 'value': None, 'unit': 'cosine', 'direction': 'higher',
           'configuration_sha256': signature, 'started_at_utc': now(), 'source_record': str(source),
           'original_audio_sha256': spec['sha256'], 'full_native_length': True}
    start, cpu = time.perf_counter(), time.process_time()
    try:
        if source.exists():
            native = read(source)
            row['source_record_sha256'] = sha256(source)
            if any(native.get(key) != value for key, value in [('case', spec['id']), ('method', method), ('condition', condition)]):
                raise ValueError('全長ECAPA対象のcase/method/conditionが不一致です')
            row['audio_sha256'] = native.get('audio', {}).get('file_sha256')
            if native['status'] != 'measured':
                row.update(status='pending_audio' if native['status'].startswith('pending') else 'upstream_failed',
                           upstream_status=native['status'], reason='native正式波形が非成功')
            else:
                x, reference_rate = original(spec)
                y, output_rate = checked_audio(native)
                x, reference = to16(x, reference_rate)
                y, output = to16(y, output_rate)
                check_output(x, 16000)
                check_output(y, 16000)
                evaluator = backend()
                random.seed(20261014)
                np.random.seed(20261014)
                evaluator.torch.manual_seed(20261014)
                value, details = evaluator.score(x, y, 16000)
                if not np.isfinite(value):
                    raise ValueError('ECAPA類似度が非有限値です')
                row.update(status='measured', value=float(value), details=details,
                           preprocessing={'reference': reference, 'output': output},
                           native_audio=native['audio'], evaluator_provenance=evaluator.provenance,
                           measurement={'value': float(value), 'status': 'measured',
                               'output_derivation': {'source': native['audio'], 'derived_16k': output},
                               'reference_derivation': {'source': audio_info(spec['path'], spec['sample_rate']),
                                                        'derived_16k': reference}})
    except NotApplicable as error:
        logging.warning('全長ECAPA適用外: %s %s %s: %s', spec['id'], method, condition, error)
        row.update(status='not_applicable', reason=str(error))
    except Exception:
        logging.exception('全長ECAPA正式測定失敗: %s %s %s', spec['id'], method, condition)
        row.update(status='failed', error=traceback.format_exc())
    row.update(finished_at_utc=now(), wall_seconds=time.perf_counter() - start,
               process_cpu_seconds=time.process_time() - cpu, terminal=not row['status'].startswith('pending'))
    write_json(path, row)
    return row


@shared_stage('full-length-speaker')
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True, type=int, choices=range(12))
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--scope', choices=('native', 'latent', 'all'), default='native')
    parser.add_argument('--embedding-model', type=Path, default=ROOT / '.cache/ecapa/embedding_model.ckpt')
    args = parser.parse_args()
    config = configuration(args.embedding_model)
    path = RUN / 'speaker-full/configuration.json'
    freeze(path, config)
    signature = sha256(path)
    instance, initialization_error = None, None

    def backend():
        nonlocal instance, initialization_error
        if initialization_error:
            raise RuntimeError('同processのECAPA初期化が失敗済み: ' + initialization_error)
        if instance is None:
            start = time.perf_counter()
            try:
                instance = EcapaSimilarity({'embedding_model': config['embedding_model'],
                    'embedding_model_sha256': config['embedding_model_sha256']}, ROOT, RUN / 'speaker-full/work', 2)
                write_json(RUN / 'speaker-full/initializations' / f'{args.batch:02d}-{time.time_ns()}.json',
                    {'configuration_sha256': signature, 'seconds': time.perf_counter() - start,
                     'provenance': instance.provenance, 'at_utc': now()})
            except Exception:
                initialization_error = traceback.format_exc()
                raise
        return instance

    rows = []
    with offline_environment():
        for spec in read(RUN / 'inputs.json')[args.batch * 10:(args.batch + 1) * 10]:
            for method in METHODS:
                conditions = []
                if args.scope in ('native', 'all'):
                    conditions += [(name, 'speaker-full') for name in native_conditions(method)]
                if args.scope in ('latent', 'all'):
                    conditions += [(name, 'latent-speaker') for name in LATENT]
                for name, folder in conditions:
                    rows.append(evaluate(spec, method, name, folder, signature, backend, args.retry_failed))
            write_json(RUN / f'speaker-full/batch-{args.scope}-{args.batch:02d}.json', {'updated_at_utc': now(), 'rows': rows})
    return int(any(row['status'] in ('failed', 'upstream_failed') or not row.get('terminal', True) for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-full-speaker'))
