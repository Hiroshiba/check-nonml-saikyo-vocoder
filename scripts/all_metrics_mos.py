"""native全長UTMOSv2を正式測定し、完全同一条件の旧値/同一PCMだけを引用する。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, audio_info, freeze, now, read
from vocoderbench.logging_utils import run_cli
from vocoderbench.mos import MosEvaluator, CHECKPOINT_NAME, CHECKPOINT_SHA256, CONFIG_HASHES, SOURCE_COMMIT
from vocoderbench.quality_core import sha256, write_json

PRIOR = ROOT / 'experiments/2026-10-13/formal-hnm-v3-references/results/run-001/results.json'
PACKAGES = ('torch', 'torchaudio', 'torchvision', 'transformers', 'timm', 'librosa', 'numpy', 'utmosv2')
EDITS = ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6')
LATENT = ('quantized_float16', 'quantized_float32', 'interpolation_input_gain_alpha0',
          'interpolation_input_gain_alpha0p5', 'interpolation_input_gain_alpha1')


def configuration(evaluator):
    provenance = dict(evaluator.provenance)
    distribution = importlib.metadata.distribution('utmosv2')
    installed = json.loads(distribution.read_text('direct_url.json') or '{}')
    if installed.get('vcs_info', {}).get('commit_id') != SOURCE_COMMIT:
        raise ValueError('UTMOSv2の固定commitが不一致')
    checkpoint = ROOT / '.cache/mos/weights' / CHECKPOINT_NAME
    if sha256(checkpoint) != CHECKPOINT_SHA256:
        raise ValueError('UTMOSv2重みhashが不一致')
    actual = {name: sha256(ROOT / '.cache/mos/wav2vec2_config' / name) for name in CONFIG_HASHES}
    if actual != CONFIG_HASHES:
        raise ValueError('UTMOSv2前処理設定hashが不一致')
    provenance['packages'] = {name: importlib.metadata.version(name) for name in PACKAGES}
    return {'schema_version': 1, 'evaluator': 'vocoderbench.mos.MosEvaluator',
            'source_sha256': sha256(ROOT / 'vocoderbench/mos.py'), 'provenance': provenance,
            'checkpoint_sha256': CHECKPOINT_SHA256, 'feature_configuration_sha256': actual,
            'input': 'native full length float32; no external alignment/normalization/crop',
            'repetition_semantics': 'one official extraction; not five folds and not a new human rating'}


def old_candidates(config):
    if not PRIOR.exists():
        proof = {'prior_results': str(PRIOR), 'prior_results_sha256': None,
                 'scientific_conditions_match': False, 'status': 'prior_unavailable',
                 'mismatches': ['prior_report_absent'], 'new_measurements_permitted': True}
        freeze(RUN / 'mos/prior-scientific-equivalence.json', proof)
        return {}, proof
    old = read(PRIOR)
    reasons = []
    if old['contract']['source_hashes'].get('vocoderbench/mos.py') != config['source_sha256']:
        reasons.append('evaluator_source')
    for key, value in config['provenance'].items():
        if old['mos_provenance'].get(key) != value:
            reasons.append('provenance.' + key)
    if old['mos_provenance']['checkpoint']['sha256'] != config['checkpoint_sha256']:
        reasons.append('checkpoint')
    for key, value in CONFIG_HASHES.items():
        if old['mos_provenance']['feature_configuration'][key]['sha256'] != value:
            reasons.append('feature_configuration.' + key)
    proof = {'prior_results': str(PRIOR), 'prior_results_sha256': sha256(PRIOR),
             'scientific_conditions_match': not reasons, 'mismatches': reasons,
             'per_waveform_PCM_SR_samples_still_required': True}
    freeze(RUN / 'mos/prior-scientific-equivalence.json', proof)
    candidates = {}
    if not reasons:
        for row in [*old['resynthesis'], *old['calibration']]:
            measurement = row.get('mos', {})
            if measurement.get('status') == 'measured':
                candidates[(row['case'], 'original' if row['method'] == 'identity' else row['method'])] = measurement
    return candidates, proof


def same_input(measurement, audio):
    return (measurement.get('input_float32_sha256') == audio['float32_sha256']
            and measurement.get('input_sample_rate') == audio['sample_rate']
            and measurement.get('input_samples') == audio['samples'])


def planned_conditions(method, include_edits, latent):
    if latent:
        return LATENT
    names = ['unedited']
    if include_edits and method != 'facodec':
        names += EDITS
    if include_edits and method in METHODS[:2]:
        names += ['time_scale1p25', 'slope_minus3', 'slope_plus3']
    return names


def evaluate(spec, method, condition, evaluator, signature, candidates, proof, retry_failed=False, latent=False):
    folder = RUN / ('mos-latent' if latent else 'mos')
    path = folder / 'measurements' / f'{spec["id"]}__{method}__{condition}.json'
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'condition': condition,
           'configuration_sha256': signature, 'status': 'pending_audio', 'value': None,
           'unit': 'predicted MOS', 'direction': 'higher', 'started_at_utc': now()}
    source = RUN / 'native' / method / spec['id'] / f'{condition}.json'
    if method == 'original':
        audio = audio_info(spec['path'], spec['sample_rate'])
        if audio['file_sha256'] != spec['sha256']:
            raise ValueError('MOS原音hash不一致')
    elif source.exists():
        native = read(source)
        row.update(source_record=str(source), source_record_sha256=sha256(source))
        if native['status'] != 'measured':
            row.update(status='pending_audio' if native['status'].startswith('pending') else 'upstream_failed',
                       upstream_status=native['status'], reason=native.get('error', native.get('reason')))
            audio = None
        else:
            audio = audio_info(native['audio']['path'], native['audio']['sample_rate'])
            if audio['file_sha256'] != native['audio']['file_sha256']:
                raise ValueError('MOS入力native hash不一致')
    else:
        audio = None
    if path.exists():
        previous = read(path)
        if previous['configuration_sha256'] != signature:
            raise ValueError('保存MOSの科学契約が不一致')
        if previous['status'] == 'measured':
            if audio is None or previous['audio_sha256'] != audio['file_sha256']:
                raise ValueError('保存MOS入力が変化または不在')
            return previous
        if previous['status'] == 'failed' and not retry_failed:
            return previous
        write_json(folder / 'history' / f'{path.stem}-{time.time_ns()}.json', previous)
    if audio is not None:
        row.update(audio_sha256=audio['file_sha256'], audio=audio)
        key = hashlib.sha256(json.dumps([signature, audio['float32_sha256'], audio['sample_rate'],
                                        audio['samples']], separators=(',', ':')).encode()).hexdigest()
        cache = RUN / 'mos/value-cache' / f'{key}.json'
        previous = read(cache) if cache.exists() else None
        old = candidates.get((spec['id'], method)) if condition == 'unedited' else None
        if previous and previous['status'] == 'measured':
            if previous['configuration_sha256'] != signature or not same_input(previous['measurement'], audio):
                raise ValueError('同一PCM MOS cacheの契約不一致')
            measurement = previous['measurement']
            row.update(origin='same_PCM_and_protocol_cached', source_result=str(cache), source_result_sha256=sha256(cache))
        elif old and same_input(old, audio):
            measurement = old
            row.update(origin='prior_same_PCM_and_all_scientific_conditions', prior=proof)
        else:
            if not evaluator._attempted:
                tick = time.perf_counter()
                ready = evaluator.prepare()
                write_json(RUN / 'mos/initializations' / f'{time.time_ns()}.json', {
                    'started_at_utc': now(), 'ready': ready, 'seconds': time.perf_counter() - tick,
                    'configuration_sha256': signature, 'provenance': evaluator.provenance})
            measurement = evaluator.predict(np.load(audio['path'], allow_pickle=False), audio['sample_rate'],
                                             language=spec['metadata'].get('language', 'en'), style='normal')
            row['origin'] = 'new_inference'
        row.update(measurement=measurement, status=measurement['status'], value=measurement['value'])
        row['new_inference_seconds'] = measurement.get('seconds') if row['origin'] == 'new_inference' else 0.0
        if measurement['status'] == 'measured' and not cache.exists():
            write_json(cache, {'status': 'measured', 'configuration_sha256': signature,
                              'measurement': measurement, 'first_source': str(path), 'origin': row['origin']})
    row['finished_at_utc'] = now()
    write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--include-edits', action='store_true')
    parser.add_argument('--latent', action='store_true')
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    specs = read(RUN / f'input-batches/{args.batch:02d}.json')
    if not 1 <= len(specs) <= 10:
        raise ValueError('MOS正式工程は10録音以下')
    evaluator = MosEvaluator(ROOT / '.cache/mos', repetitions=1, seed=20261012, threads=4)
    config = configuration(evaluator)
    freeze(RUN / 'mos/configuration.json', config)
    signature = sha256(RUN / 'mos/configuration.json')
    freeze(RUN / 'mos/execution-contract.json', {'source_sha256': sha256(__file__),
           'input_contract_sha256': sha256(RUN / 'input-contract.json'), 'configuration_sha256': signature})
    candidates, proof = old_candidates(config)
    rows = []
    for spec in specs:
        methods = METHODS if args.latent else ('original', *METHODS)
        for method in methods:
            names = ['unedited'] if method == 'original' else planned_conditions(method, args.include_edits, args.latent)
            for condition in names:
                rows.append(evaluate(spec, method, condition, evaluator, signature, candidates, proof,
                                     args.retry_failed, args.latent))
    return int(any(row['status'].startswith('pending') or row['status'] == 'failed' for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-mos'))
