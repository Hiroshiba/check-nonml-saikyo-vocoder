"""全8方式の正式研究で使う保存・照合処理。予行や自己検査は行わない。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.quality_core import environment, sha256, write_json  # noqa: E402
from vocoderbench import corpus  # noqa: E402

RUN = ROOT / 'runs/all-method-metrics-recovery-20261014'
METHODS = ('hnm', 'world_harvest', 'facodec', 'hifiglot', 'golf', 'sifigan', 'llsm2', 'magphase')
RATES = dict(zip(METHODS, (16000, 16000, 16000, 44100, 24000, 24000, 24000, 48000)))


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def entries():
    return read(ROOT / 'data/clean_speech_v1.json')['entries']


def freeze(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ValueError(f'保存済みの研究条件と不一致です: {path}')
    else:
        write_json(path, value)


def source_hashes():
    paths = [*sorted((ROOT / 'scripts').glob('all_metrics_*.py')),
             *sorted((ROOT / 'vocoderbench').rglob('*.py')),
             ROOT / 'BASELINE.json', ROOT / 'vocoderbench/references/sources.lock.json',
             ROOT / 'vocoderbench/references/requirements.txt']
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths if '.cache' not in p.parts}


def audio_info(path, sample_rate):
    wave = np.load(path, allow_pickle=False)
    if wave.ndim != 1 or wave.dtype.kind != 'f' or not len(wave) or not np.isfinite(wave).all():
        raise ValueError(f'有限な1次元浮動小数点波形が必要です: {path}')
    return {'path': str(Path(path).resolve()), 'file_sha256': sha256(path),
            'samples': len(wave), 'sample_rate': sample_rate, 'seconds': len(wave) / sample_rate,
            'float64_sha256': hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest(),
            'float32_sha256': hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest(),
            'peak': float(np.max(np.abs(wave))), 'over_one_fraction': float(np.mean(np.abs(wave) > 1))}


def save_audio(path, wave, sample_rate, exact_float32=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    wave = np.asarray(wave, dtype=np.float64).reshape(-1)
    exact = False
    stored = wave
    if exact_float32:
        with np.errstate(over='ignore', invalid='ignore'):
            candidate = wave.astype(np.float32)
        exact = np.array_equal(wave, candidate.astype(np.float64))
        if exact:
            stored = candidate
    with temporary.open('wb') as stream:
        np.save(stream, stored, allow_pickle=False)
    temporary.replace(path)
    info = audio_info(path, sample_rate)
    source_hash = hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()
    if info['float64_sha256'] != source_hash:
        raise ValueError('保存前後のPCM hashが一致しません')
    info.update(stored_dtype=str(stored.dtype), exact_float32_storage_requested=exact_float32,
                float32_roundtrip_exact=exact if exact_float32 else None,
                storage_source_float64_sha256=source_hash,
                storage_rule='float32 only if every float64 value is exactly preserved; otherwise float64'
                    if exact_float32 else 'float64; original input representation retained')
    return info


def link_existing(source, target, expected):
    source, target = Path(source).resolve(), Path(target)
    if sha256(source) != expected:
        raise ValueError(f'既存資産hash不一致: {source}')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) != expected:
            raise ValueError(f'既存の再利用リンクとhash不一致: {target}')
    else:
        target.symlink_to(source)


def make_inputs():
    """公式固定120録音を新runへ保存する。喪失した旧出力は輸入しない。"""
    dataset = entries()
    if len(dataset) != 120 or len({e['speaker'] for e in dataset}) != 40:
        raise ValueError('固定120録音40話者が必要です')
    RUN.mkdir(parents=True, exist_ok=True)
    contract = {'schema_version': 2, 'source_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dataset_sha256': sha256(ROOT / 'data/clean_speech_v1.json'),
        'input_preparation_source_sha256': sha256(Path(__file__)),
        'methods': list(METHODS), 'native_sample_rates': RATES, 'seed': 0,
        'scope': '凍結済みLibriSpeech120録音40話者、全8方式を新規実行。',
        'formal_base': read(ROOT / 'BASELINE.json'),
        'plan_sha256': sha256(ROOT / 'research/all-method-recovery-plan-2026-10-14.md'),
        'recovery_boundary': '旧途中runのrawは復元不能。会話中の集約を測定値へ転記しない。',
        'reuse': '公開済み旧評価値は別の全科学条件/実入力hash照合に合格した場合だけ後段で引用。',
        'original_storage': 'float64 NPY; no new trimming, normalization or resampling'}
    freeze(RUN / 'input-contract.json', contract)
    fixed = {case['id']: case for case in corpus.load_cases()}
    if set(fixed) != {entry['id'] for entry in dataset}:
        raise ValueError('固定manifestと原音case集合が不一致')
    inputs = []
    for entry in dataset:
        identifier = entry['id']
        wave = np.asarray(fixed[identifier]['x'], dtype=np.float64)
        if wave.ndim != 1 or len(wave) != entry['excerpt_samples'] or not np.isfinite(wave).all():
            raise ValueError(f'固定原音PCMの長さ/形式が不一致: {identifier}')
        target = RUN / 'inputs' / f'{identifier}.npy'
        expected = hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()
        if target.exists():
            if audio_info(target, 16000)['float64_sha256'] != expected:
                raise ValueError(f'保存済み固定原音PCMのhash不一致: {identifier}')
        else:
            save_audio(target, wave, 16000)
        inputs.append({'id': identifier, 'path': str(target), 'sha256': sha256(target),
                       'sample_rate': 16000, 'samples': len(wave), 'speaker': entry['speaker'],
                       'metadata': entry})
    freeze(RUN / 'inputs.json', inputs)
    for offset in range(0, 120, 10):
        freeze(RUN / 'input-batches' / f'{offset // 10:02d}.json', inputs[offset:offset + 10])
    write_json(RUN / 'input-preparation.json', {'completed_at_utc': now(),
        'originals': len(inputs), 'imported_previous_native_outputs': 0,
        'environment': environment(), 'platform': platform.platform(),
        'inputs_sha256': sha256(RUN / 'inputs.json')})


if __name__ == '__main__':
    make_inputs()
