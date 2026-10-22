"""固定入力、担当分割、保存済み試行の共通契約。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = '1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193'
PARTITION_SPEAKERS = (14, 13, 13)
CONDITIONS = ('apron_0', 'apron_minus3', 'apron_plus3', 'llsm2_0')
ASSET_SHA256 = {
    'mos/weights/fold0_s42_best_model.pth': 'c8149d988e4bbf3f347e6966b5d769de347a5f8c59ffca1dc4bd4bf5b8585e57',
    'mos/wav2vec2_config/config.json': '4937977e24d12d1bba70cdce8709c3c04807a8e4ae8ddac4229c48c436ae99ae',
    'mos/wav2vec2_config/preprocessor_config.json': 'b225d617c025463b9e157e06afea8b90dc7078fc70b013c533328423e0486b4a',
    'scoreq/fixed_nmr_telephone.onnx': '899c9959bf48b38d99fdd5227b31182ca9d8253b14b61edd2725eca779a55b49',
    'ecapa/embedding_model.ckpt': '0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2',
}
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')


def require_threads(count: int) -> None:
    wrong = {name: os.environ.get(name) for name in THREAD_ENV
             if os.environ.get(name) != str(count)}
    if wrong:
        raise ValueError(f'固定thread環境が{count}と違います: {wrong}')


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read(path: Path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n',
                         encoding='utf-8')
    temporary.replace(path)


def input_cases(manifest: Path, input_root: Path, owner: int):
    """120個すべてを照合してから、話者単位の担当だけを返す。"""
    if sha(manifest) != MANIFEST_SHA256:
        raise ValueError('固定入力manifestのSHA256が一致しません')
    data = read(manifest)
    cases = data['cases']
    speakers = list(dict.fromkeys(row['speaker'] for row in cases))
    if (len(cases) != 120 or len({row['id'] for row in cases}) != 120
            or len(speakers) != 40 or set(Counter(row['speaker'] for row in cases).values()) != {3}
            or data['sample_rate'] != 16000 or data['seed'] != 0):
        raise ValueError('固定120録音・40話者・seed0契約が一致しません')
    if owner not in (0, 1, 2):
        raise ValueError('担当は0、1、2だけです')
    checked = []
    for row in cases:
        item = row['input']
        name = item['path']
        if (not re.fullmatch(r'[A-Za-z0-9_-]+\.npy', name)
                or name != row['id'] + '.npy' or item['sample_rate'] != 16000
                or item['excerpt_start_sample'] != 0
                or item['excerpt_samples'] <= 0
                or not 0 < row['common_samples'] <= item['excerpt_samples']):
            raise ValueError('入力名・範囲・固定共通窓が不正です')
        path = input_root / name
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError(f'入力bytes/SHAが不一致または欠落: {row["id"]}')
        array = np.load(path, mmap_mode='r', allow_pickle=False)
        if array.ndim != 1 or array.dtype != np.dtype('<f8') or len(array) != item['excerpt_samples']:
            raise ValueError(f'入力NPYヘッダーが不一致: {row["id"]}')
        checked.append({**row, 'absolute_input': str(path.resolve())})
    first = sum(PARTITION_SPEAKERS[:owner])
    chosen = set(speakers[first:first + PARTITION_SPEAKERS[owner]])
    owned = [row for row in checked if row['speaker'] in chosen]
    if len(owned) != PARTITION_SPEAKERS[owner] * 3:
        raise ValueError('話者単位の担当録音数が不一致です')
    return owned


def source_hashes():
    files = [ROOT / 'BASELINE.json', ROOT / 'vocoderbench/references/current_base.py',
             ROOT / 'vocoderbench/references/adapters_dsp.py',
             ROOT / 'vocoderbench/references/native.py',
             ROOT / 'vocoderbench/references/common.py',
             ROOT / 'vocoderbench/references/worker.py',
             ROOT / 'vocoderbench/references/sources.lock.json',
             ROOT / 'vocoderbench/references/requirements.txt',
             ROOT / 'vocoderbench/quality_backends.py', ROOT / 'vocoderbench/extended_metrics.py',
             ROOT / 'vocoderbench/quality_core.py', ROOT / 'vocoderbench/mos.py',
             ROOT / 'vocoderbench/logging_utils.py', ROOT / 'uv.lock',
             *sorted((ROOT / 'vocoderbench/apron').glob('*.py')),
             *sorted((ROOT / 'scripts/apron_fixed120').glob('*.py'))]
    return {str(path.relative_to(ROOT)): sha(path) for path in files}


def versions():
    names = ('numpy', 'scipy', 'pyworld', 'torch', 'torchaudio', 'utmosv2',
             'onnxruntime', 'speechbrain', 'transformers', 'timm', 'librosa', 'pystoi')
    result = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def bind_run(output: Path, contract: dict) -> None:
    """既存の同一契約だけを再開し、別契約や未知の既存物を拒否する。"""
    output = Path(output)
    if output.exists():
        path = output / 'contract.json'
        if not path.is_file() or read(path) != contract:
            raise ValueError(f'既存出力の契約が違います: {output}')
    else:
        output.mkdir(parents=True, exist_ok=False)
        with (output / 'contract.json').open('x', encoding='utf-8') as stream:
            json.dump(contract, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write('\n')


def latest_attempt(output: Path, case_id: str):
    root = output / 'cases' / case_id
    attempts = sorted(root.glob('attempt-*'))
    if not attempts:
        return None, None
    last = attempts[-1]
    path = last / 'result.json'
    return last, read(path) if path.is_file() else None


def new_attempt(output: Path, case_id: str) -> Path:
    root = output / 'cases' / case_id
    root.mkdir(parents=True, exist_ok=True)
    index = len(list(root.glob('attempt-*'))) + 1
    path = root / f'attempt-{index:04d}'
    path.mkdir(exist_ok=False)
    return path


def save_wave(path: Path, wave) -> dict:
    wave = np.asarray(wave)
    if wave.ndim != 1 or not len(wave) or wave.dtype not in (np.dtype('float32'), np.dtype('float64')):
        raise ValueError('native出力のshape/dtypeが不正です')
    if not np.isfinite(wave).all():
        raise ValueError('native出力に非有限値があります')
    with path.open('xb') as stream:
        np.save(stream, wave, allow_pickle=False)
    return {'path': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path),
            'samples': len(wave), 'sample_rate': 24000, 'dtype': str(wave.dtype)}
