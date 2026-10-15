"""公式全文GT55録音の全8 native全長へ固定greedy CTCを適用する。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import math
import time
import traceback

import numpy as np
import scipy
from scipy.signal import resample_poly

from all_metrics_common import METHODS, ROOT, RUN, audio_info, entries, freeze, now, read, save_audio
from vocoderbench.assessment.acoustics import content
from vocoderbench.assessment.common import Inputs
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

MODEL = 'facebook/wav2vec2-base-960h'
REVISION = '22aad52d435eb6dbaf354bdad9b0da84ce7d6156'
ASSETS = ROOT / '.cache/asr' / REVISION
ASSET_FILES = ('config.json', 'preprocessor_config.json', 'tokenizer_config.json',
               'special_tokens_map.json', 'vocab.json', 'README.md', 'model.safetensors')


def has_full_truth(entry):
    return entry['source_samples'] == entry['excerpt_samples'] and entry['excerpt_start_sample'] == 0


def configuration():
    selected = [entry for entry in entries() if has_full_truth(entry)]
    if len(selected) != 55 or len({e['speaker'] for e in selected}) != 32:
        raise ValueError('既定の公式全文55録音32話者と不一致')
    return {'schema_version': 1, 'recognizer': MODEL, 'recognizer_revision': REVISION,
        'asset_sha256': {name: sha256(ASSETS / name) for name in ASSET_FILES},
        'source_sha256': {name: sha256(ROOT / name) for name in ('scripts/all_metrics_asr.py',
            'scripts/all_metrics_common.py', 'vocoderbench/assessment/acoustics.py', 'vocoderbench/assessment/common.py')},
        'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'selection': 'source_samples == excerpt_samples and excerpt_start_sample == 0',
        'selected_case_ids': [entry['id'] for entry in selected], 'planned_cases': 55, 'planned_speakers': 32,
        'planned_recognitions': 55 * 9, 'planned_assessments': 55 * 8, 'no_full_GT_cases': 65,
        'no_full_GT_reason': '先頭6秒切出しの公式部分転記が未整備。推測ラベルで補わない。',
        'decoding': 'argmax logits then CTC collapse; no language model; batch_size=1',
        'normalization': 'nfkc_casefold_whitespace', 'word_tokenization': 'whitespace',
        'maximum_reference_cer': .20, 'sample_rate': 16000,
        'full_native_preprocessing': {'resampling': 'scipy.signal.resample_poly', 'scipy_version': scipy.__version__,
            'window': ['kaiser', 5.0], 'padtype': 'constant', 'float32': 'cast after full length resampling',
            'trim': False, 'align': False, 'normalize': False, 'clip': False},
        'execution': {'torch_threads': 2, 'torch_interop_threads': 1, 'device': 'cpu', 'inference_mode': True,
                      'trust_remote_code': False, 'local_files_only': True, 'use_safetensors': True},
        'packages': {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'torch', 'transformers', 'safetensors', 'tokenizers')}}


def audio_source(spec, method):
    if method == 'original':
        source = audio_info(spec['path'], spec['sample_rate'])
        if source['file_sha256'] != spec['sha256']:
            raise ValueError('ASR原音hash不一致')
        return {'status': 'measured', 'audio': source}
    path = RUN / 'native' / method / spec['id'] / 'unedited.json'
    if not path.exists():
        return {'status': 'pending_audio'}
    native = read(path)
    result = {'status': native['status'], 'native_record': str(path), 'native_record_sha256': sha256(path)}
    if native['status'] == 'measured':
        source = audio_info(native['audio']['path'], native['audio']['sample_rate'])
        if source['file_sha256'] != native['audio']['file_sha256']:
            raise ValueError('ASR native hash不一致')
        result['audio'] = source
    return result


def recognize(spec, method, signature, model_state, retry):
    path = RUN / 'asr/recognitions' / f'{spec["id"]}__{method}.json'
    source = audio_source(spec, method)
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method, 'configuration_sha256': signature,
           'source': source, 'status': 'pending_audio', 'started_at_utc': now()}
    if path.exists():
        old = read(path)
        if old['configuration_sha256'] != signature:
            raise ValueError('ASR再開の科学条件不一致')
        if old['status'] == 'measured':
            if source.get('audio', {}).get('file_sha256') != old['source']['audio']['file_sha256']:
                raise ValueError('既存ASRのnative入力hash不一致')
            if sha256(old['audio']['path']) != old['audio']['file_sha256']:
                raise ValueError('既存ASRの16k派生入力hash不一致')
            return old
        if old['status'] == 'failed' and not retry:
            return old
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', old)
    if source['status'] != 'measured':
        row.update(status='pending_audio' if source['status'].startswith('pending') else 'upstream_failed',
                   upstream_status=source['status'])
    else:
        try:
            wave = np.load(source['audio']['path'], allow_pickle=False).astype(np.float64)
            sr = source['audio']['sample_rate']
            divisor = math.gcd(sr, 16000)
            if sr != 16000:
                wave = resample_poly(wave, 16000 // divisor, sr // divisor, window=('kaiser', 5.0), padtype='constant')
            if not len(wave) or not np.isfinite(wave).all():
                raise ValueError('ASR入力波形が空/非有限')
            derived = RUN / 'asr/audio' / spec['id'] / f'{method}.npy'
            expected = hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()
            info = audio_info(derived, 16000) if derived.exists() else save_audio(derived, wave, 16000)
            if info['float64_sha256'] != expected:
                raise ValueError('ASR全長派生PCM不一致')
            row.update(audio=info, resampling={'up': 16000 // divisor, 'down': sr // divisor})
            import torch
            if not model_state:
                from transformers import AutoModelForCTC, AutoProcessor
                tick = time.perf_counter()
                processor = AutoProcessor.from_pretrained(ASSETS, local_files_only=True, trust_remote_code=False)
                model = AutoModelForCTC.from_pretrained(ASSETS, local_files_only=True, trust_remote_code=False,
                                                       use_safetensors=True).eval()
                model_state.update(processor=processor, model=model)
                write_json(RUN / 'asr/initializations' / f'{time.time_ns()}.json', {
                    'configuration_sha256': signature, 'seconds': time.perf_counter() - tick, 'finished_at_utc': now()})
            tick, cpu = time.perf_counter(), time.process_time()
            prepared = model_state['processor'](wave.astype(np.float32), sampling_rate=16000,
                                                return_tensors='pt', padding=False)
            prepared_sha = hashlib.sha256(prepared.input_values.numpy().astype('<f4').tobytes()).hexdigest()
            with torch.inference_mode():
                logits = model_state['model'](**prepared).logits
                tokens = torch.argmax(logits, dim=-1)
            text = model_state['processor'].batch_decode(tokens)[0]
            row.update(status='measured', text=text, truth=spec['metadata']['transcript'],
                       preprocessed_float32_sha256=prepared_sha, input_float32_sha256=info['float32_sha256'],
                       logit_frames=int(logits.shape[1]), inference_wall_seconds=time.perf_counter() - tick,
                       inference_process_cpu_seconds=time.process_time() - cpu)
        except Exception:
            row.update(status='failed', error=traceback.format_exc())
    row['finished_at_utc'] = now()
    write_json(path, row)
    return row


def assess(spec, method, signature, reference=None, output=None):
    path = RUN / 'asr/measurements' / f'{spec["id"]}__{method}.json'
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
           'configuration_sha256': signature, 'status': 'not_applicable', 'value': None}
    if not has_full_truth(spec['metadata']):
        row['reason'] = '切出し65録音の公式部分GTは未整備'
    elif reference['status'] != 'measured' or output['status'] != 'measured':
        row.update(status='pending_recognition' if any(r['status'].startswith('pending') for r in (reference, output))
                   else 'upstream_failed', reference_status=reference['status'], output_status=output['status'])
    else:
        sidecar = RUN / 'asr/sidecars' / f'{spec["id"]}__{method}.json'
        data = {'truth': spec['metadata']['transcript'], 'reference_text': reference['text'], 'output_text': output['text'],
                'evidence_kind': 'asr_output', 'recognizer': MODEL, 'recognizer_revision': REVISION, 'language': 'en',
                'normalization': 'nfkc_casefold_whitespace', 'word_tokenization': 'whitespace',
                'reference_audio_sha256': reference['audio']['file_sha256'], 'output_audio_sha256': output['audio']['file_sha256'],
                'configuration_sha256': signature}
        freeze(sidecar, data)
        job = {'transcripts': str(sidecar), 'reference': reference['audio']['path'],
               'output': output['audio']['path'], 'maximum_reference_cer': .20}
        measurement = content(job, Inputs(ROOT))
        row.update(status='measured' if measurement['status'] == 'ok' else measurement['status'],
                   measurement=measurement, value=measurement['value'], sidecar_sha256=sha256(sidecar),
                   reference_recognition_sha256=sha256(RUN / 'asr/recognitions' / f'{spec["id"]}__original.json'),
                   output_recognition_sha256=sha256(RUN / 'asr/recognitions' / f'{spec["id"]}__{method}.json'))
    if path.exists() and read(path) != row:
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', read(path))
    write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    freeze(RUN / 'asr/configuration.json', configuration())
    signature = sha256(RUN / 'asr/configuration.json')
    rows, model_state = [], {}
    for spec in read(RUN / f'input-batches/{args.batch:02d}.json'):
        if not has_full_truth(spec['metadata']):
            rows += [assess(spec, method, signature) for method in METHODS]
            continue
        reference = recognize(spec, 'original', signature, model_state, args.retry_failed)
        for method in METHODS:
            output = recognize(spec, method, signature, model_state, args.retry_failed)
            rows.append(assess(spec, method, signature, reference, output))
    write_json(RUN / f'asr/batch-{args.batch:02d}.json', {'rows': rows, 'configuration_sha256': signature})
    return int(any(row['status'].startswith('pending') or row['status'] == 'failed' for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-asr'))
