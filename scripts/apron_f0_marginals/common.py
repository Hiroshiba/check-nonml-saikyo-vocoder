"""固定入力・実装版・原本保存の共通境界。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

import numpy as np

from scripts.apron_fixed120.common import input_cases


ROOT = Path(__file__).resolve().parents[2]
LIMIT_BYTES = 2 * 1024**3
MIN_FREE_BYTES = 4 * 1024**3
PITCH_BINS = 488
STATES = 976
HOP = 120
SR = 24000
SOURCE_PINS = {
    'scripts/apron_fixed120/common.py': '8acaadffec7f2ae07740b9eb44f8d08135c19d60da2c18ce9f6bdd6f38614801',
}
LIBROSA_PINS = {
    'core/pitch.py': 'f45cc429f9daa2276d750fa4f100641eae45991daf6e70050073088b86516b87',
    'sequence.py': '1253a1427630506928873c82d00ae0fdf1a6a35ba7653252d3bad8f2d37052e6',
}
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'numba': '0.68.0', 'librosa': '0.11.0'}
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def identity(path: Path) -> dict:
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_new(path: Path, data) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def write_current(path: Path, data) -> None:
    temp = path.with_name(path.name + '.tmp')
    with temp.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
    temp.replace(path)


def tree_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def budget(root: Path, next_bytes: int = 0) -> None:
    used = tree_bytes(root)
    if used + next_bytes > LIMIT_BYTES:
        raise RuntimeError(f'新runの2GiB保存上限: 既存{used}B・追加予定{next_bytes}B')


def save_array(root: Path, path: Path, array: np.ndarray) -> dict:
    array = np.asarray(array)
    budget(root, array.nbytes + 1024)
    with path.open('xb') as stream:
        np.save(stream, array, allow_pickle=False)
    return identity(path)


def check_environment() -> dict:
    if sys.version_info[:3] != (3, 12, 14):
        raise RuntimeError(f'固定Python版と不一致: {sys.version.split()[0]}')
    actual = {name: importlib.metadata.version(name) for name in VERSIONS}
    if actual != VERSIONS:
        raise RuntimeError(f'固定distribution版と不一致: {actual}')
    wrong = {name: os.environ.get(name) for name in THREAD_ENV
             if os.environ.get(name) != '1'}
    if wrong or os.environ.get('PYTHONDONTWRITEBYTECODE') != '1':
        raise RuntimeError(f'固定thread/bytecode環境と不一致: {wrong}')
    files = {}
    for name, expected in SOURCE_PINS.items():
        actual_sha = sha(ROOT / name)
        files[name] = actual_sha
        if actual_sha != expected:
            raise RuntimeError(f'固定入力helperのsource SHA不一致: {name}: {actual_sha}')
    site = Path(importlib.metadata.distribution('librosa').locate_file('librosa'))
    for name, expected in LIBROSA_PINS.items():
        actual_sha = sha(site / name)
        files['librosa/' + name] = actual_sha
        if actual_sha != expected:
            raise RuntimeError(f'固定librosa source SHA不一致: {name}: {actual_sha}')
    return {'python': sys.version.split()[0], 'distributions': actual,
            'source_sha256': files, 'librosa_release_commit_reference':
            'af8c839fb15317fa2712ea66e7a22da6a9267b32',
            'release_commit_verified_from_wheel_metadata': False}


def checked_cases(manifest: Path, input_root: Path, owner: int) -> list[dict]:
    return input_cases(manifest, input_root, owner)


def prepare_root(output: Path) -> None:
    if output.exists():
        raise FileExistsError(f'新しい実行先が既存です: {output}')
    if not output.parent.is_dir():
        raise FileNotFoundError(f'事前に作成するrun内の親directoryがありません: {output.parent}')
    free = os.statvfs(output.parent)
    available = free.f_bavail * free.f_frsize
    if available < MIN_FREE_BYTES:
        raise RuntimeError(f'開始時空き容量が4GiB未満です: {available}B')
    output.mkdir()


def file_manifest(root: Path, paths: list[Path]) -> list[dict]:
    return [{'path': p.relative_to(root).as_posix(), **identity(p)} for p in paths]


def seal_owner(output: Path) -> None:
    """自己参照なしの保存file一覧。失敗した部分原本もそのまま列挙する。"""
    paths = sorted(p for p in output.rglob('*') if p.is_file()
                   and p.name != 'ARTIFACT_MANIFEST.json')
    write_new(output / 'ARTIFACT_MANIFEST.json',
              {'kind': 'local_artifact_inventory', 'recorded_at_utc': now(),
               'files': file_manifest(output, paths)})
