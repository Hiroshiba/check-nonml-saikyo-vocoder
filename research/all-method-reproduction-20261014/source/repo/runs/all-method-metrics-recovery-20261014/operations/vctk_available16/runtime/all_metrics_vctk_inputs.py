"""取得済み全16件の既定抜粋を復元する正式入力準備。新たな性能選択はしない。"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from all_metrics_common import METHODS, ROOT, RUN, audio_info, freeze, read, save_audio
from vocoderbench.quality_core import environment, sha256

VCTK_RUN = RUN / 'vctk-availability16'
OPERATIONS = RUN / 'operations/vctk_available16'
SELECTION = OPERATIONS / 'selection-before-measurement.json'
SELECTION_SHA256 = 'ce192ea183202f5714c8f25a6c87ed3cae5500439e4f992dbfcc61abe62da8ff'
NATIVE_RATES = dict(zip(METHODS, (48000, 48000, 16000, 44100, 24000, 24000, 24000, 48000)))


def pcm_hash(wave):
    return hashlib.sha256(np.asarray(wave, dtype='<f8').tobytes()).hexdigest()


def main():
    if sha256(SELECTION) != SELECTION_SHA256:
        raise ValueError('事前選択hash不一致')
    selection = read(SELECTION)
    entries = selection['entries']
    counts = Counter(e['speaker'] for e in entries)
    if (len(entries) != 16 or len({e['id'] for e in entries}) != 16
            or counts != {'p360': 4, 'p361': 4, 'p362': 4, 'p363': 4}
            or [e['id'] for e in entries] != sorted(e['id'] for e in entries)):
        raise ValueError('事前固定した取得済み全16件と不一致')
    contract = {
        'schema_version': 1, 'study': 'VCTK availability16 limited supplementary study',
        'source_manifest_path': str(SELECTION), 'source_manifest_sha256': SELECTION_SHA256,
        'selection_rule': selection['selection'], 'formal126_status': selection['formal126_status'],
        'below100_limitation': selection['below100_limitation'],
        'planned_recordings': 16, 'planned_speakers': 4, 'recordings_per_speaker': dict(counts),
        'methods': list(METHODS), 'native_sample_rates': NATIVE_RATES,
        'source_sample_rate': 48000, 'seed': 0, 'threads': 2,
        'source_preprocessing': selection['preprocessing'], 'gain_normalization': False,
        'comparison': selection['common_window'], 'training_overlap': selection['training_overlap'],
        'duration_layers': selection['duration_layers'], 'formal_base': read(ROOT / 'BASELINE.json'),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in
                          (Path(__file__), ROOT / 'scripts/all_metrics_common.py')},
        'publication': selection['publication'],
        'preparation': 'Decode unchanged preserved official FLAC; verify declared full/excerpt PCM64; save original excerpt float64 NPY. No inference.',
    }
    freeze(VCTK_RUN / 'input-contract.json', contract)
    inputs = []
    for selected in entries:
        record_path = ROOT / selected['reference_record']
        source = ROOT / selected['preserved_source_flac']
        if (sha256(record_path) != selected['reference_record_sha256']
                or sha256(source) != selected['source_sha256']):
            raise ValueError('事前固定した原音・metadata hash不一致')
        entry = read(record_path)
        original, sr = sf.read(source, dtype='float64')
        start, n = entry['excerpt_start_sample'], entry['excerpt_samples']
        wave = original[start:start + n]
        if (sr != 48000 or original.ndim != 1 or len(original) != entry['source_samples']
                or pcm_hash(original) != entry['source_float64_sha256']
                or pcm_hash(wave) != selected['excerpt_float64_sha256']
                or pcm_hash(wave) != entry['excerpt_float64_sha256']
                or start != 0 or n != min(len(original), 480000)
                or not 3 <= n / sr <= 10 or not np.isfinite(wave).all()):
            raise ValueError(f'固定原音・既定抜粋のPCM/寸法不一致: {entry["id"]}')
        path = VCTK_RUN / 'inputs' / f'{entry["id"]}.npy'
        info = audio_info(path, sr) if path.exists() else save_audio(path, wave, sr)
        if info['float64_sha256'] != entry['excerpt_float64_sha256']:
            raise ValueError('保存入力PCM64不一致')
        inputs.append({'id': entry['id'], 'speaker': entry['speaker'], 'path': str(path),
                       'sha256': info['file_sha256'], 'sample_rate': sr, 'samples': n,
                       'audio': info, 'source_flac_sha256': entry['source_sha256'],
                       'metadata': entry})
    freeze(VCTK_RUN / 'inputs.json', inputs)
    for offset in range(0, 16, 10):
        freeze(VCTK_RUN / 'input-batches' / f'{offset // 10:02d}.json', inputs[offset:offset + 10])
    freeze(VCTK_RUN / 'input-environment.json', environment())
    return 0


if __name__ == '__main__':
    from vocoderbench.logging_utils import run_cli
    raise SystemExit(run_cli(main, 'vctk-availability16-inputs'))
