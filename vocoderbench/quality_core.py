"""追加評価の共通処理。欠測、初期化、初回、反復を分離する。"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import time

import numpy as np
from scipy.io import wavfile


class Unavailable(RuntimeError):
    """必要なローカル資産・追加依存が存在しない。"""


class NotApplicable(ValueError):
    """定義した適用範囲に入らない。品質が良いという意味ではない。"""


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    def invalid(value):
        raise ValueError(f'JSON内の非有限値: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=invalid)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def resolve_path(base, value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else Path(base) / path).resolve()


def file_asset(options, key, base, provenance, expected=None):
    value = options.get(key)
    if not value:
        raise Unavailable(f'資産の設定がありません: {key}')
    path = resolve_path(base, value)
    if not path.is_file():
        raise Unavailable(f'ローカル資産がありません: {path}')
    actual = sha256(path)
    expected = expected or options.get(key + '_sha256')
    if expected is not None and actual != expected:
        raise ValueError(f'SHA256が一致しません: {path}')
    provenance.setdefault('assets', {})[key] = {
        'path': str(path), 'bytes': path.stat().st_size, 'sha256': actual,
        'expected_sha256': expected,
    }
    return path


def package_versions(names):
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def environment():
    return {
        'python': platform.python_version(), 'platform': platform.platform(),
        'cpu': platform.processor(), 'logical_cpu_count': os.cpu_count(),
        'packages': package_versions(('numpy', 'scipy', 'torch', 'torchaudio',
                                     'onnxruntime', 'speechbrain', 'utmosv2',
                                     'transformers', 'timm', 'librosa')),
    }


@contextmanager
def offline_environment():
    """ローカル経路に限定し、HF系列の暗黙のネットワーク取得も無効にする。"""
    keys = ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')
    previous = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ[key] = '1'
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def load_audio(path, sample_rate=None):
    path = Path(path)
    if path.suffix.lower() == '.npy':
        x = np.load(path, allow_pickle=False)
        sr = sample_rate
        if x.dtype.kind != 'f':
            raise ValueError('NPYは固定振幅尺度の浮動小数点PCMにしてください')
    elif path.suffix.lower() == '.wav':
        sr, x = wavfile.read(path)
        if sample_rate is not None and sr != sample_rate:
            raise ValueError(f'指定サンプルレートとWAVが不一致: {path}')
        if x.dtype.kind == 'i':
            x = x.astype(np.float64) / (2 ** (8 * x.dtype.itemsize - 1))
        elif x.dtype == np.uint8:
            x = (x.astype(np.float64) - 128) / 128
        elif x.dtype.kind != 'f':
            raise ValueError(f'未対応のWAV数値型: {x.dtype}')
    else:
        raise ValueError('入力はWAVまたは浮動小数点NPYにしてください')
    if isinstance(sr, bool) or not isinstance(sr, (int, np.integer)) or sr <= 0:
        raise ValueError('正の整数サンプルレートが必要です')
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all():
        raise ValueError('空でない有限値のモノラル波形が必要です')
    return x, int(sr), {
        'path': str(path), 'file_sha256': sha256(path), 'samples': len(x),
        'sample_rate': int(sr), 'seconds': len(x) / sr,
        'pcm_float64_sha256': hashlib.sha256(x.astype('<f8').tobytes()).hexdigest(),
    }


def check_output(output, sample_rate):
    """非参照評価の対象条件。原音との比較や自己差分は行わない。"""
    if len(output) / sample_rate < 1.0:
        raise NotApplicable('この追加評価の自然音声プロトコルは1秒以上を対象にします')
    if not np.any(output - np.mean(output)):
        raise ValueError('出力が無音または定数です。通常の欠測と区別します')


def check_pair(reference, output, sample_rate):
    if reference.shape != output.shape:
        raise ValueError('参照型の追加評価には同一長の音声が必要です。自動整列しません')
    if len(reference) / sample_rate < 1.0:
        raise NotApplicable('この追加評価の自然音声プロトコルは1秒以上を対象にします')
    if not np.any(reference - np.mean(reference)):
        raise NotApplicable('参照が無音または定数です')
    if not np.any(output - np.mean(output)):
        raise ValueError('出力が無音または定数です。通常の欠測と区別します')


def summarize(values):
    return {'count': len(values), 'median': float(np.median(values)) if values else None,
            'minimum': min(values) if values else None, 'maximum': max(values) if values else None}


def timed_call(function):
    start, cpu = time.perf_counter(), time.process_time()
    record = {'status': 'failed', 'value': None}
    try:
        value, details = function()
        value = float(value)
        if not np.isfinite(value):
            raise ValueError('評価器が非有限値を返しました')
        record.update(status='measured', value=value, details=details)
    except NotApplicable as error:
        logging.warning('追加評価の対象外: %s', error)
        record.update(status='not_applicable', reason=str(error))
    except Unavailable as error:
        logging.exception('追加評価の資産不足')
        record.update(status='unavailable', reason=str(error))
    except Exception as error:
        logging.exception('追加評価に失敗')
        record['reason'] = f'{type(error).__name__}: {error}'
    record.update(wall_seconds=time.perf_counter() - start,
                  process_cpu_seconds=time.process_time() - cpu)
    return record


def measure_repeated(function, repetitions):
    """初回値を採点値とする。反復平均でMOSの抽出回数を暗黙に増やさない。"""
    first = timed_call(function)
    repeats = [timed_call(function) for _ in range(repetitions)] if first['status'] == 'measured' else []
    complete = first['status'] == 'measured' and all(r['status'] == 'measured' for r in repeats)
    status = 'measured' if complete else ('partial_failure' if first['status'] == 'measured' else first['status'])
    valid = [r for r in repeats if r['status'] == 'measured']
    return {
        'status': status, 'value': first['value'] if complete else None,
        'first': first, 'repetitions': repeats, 'planned_repetitions': repetitions,
        'warm_wall_seconds': summarize([r['wall_seconds'] for r in valid]),
        'warm_cpu_seconds': summarize([r['process_cpu_seconds'] for r in valid]),
        'warm_value_range': summarize([r['value'] for r in valid]),
        'timing_scope': 'モデル初期化・入力ファイル読込・入力hashを除く。指標固有の前処理と両波形の推論を含む。',
    }
