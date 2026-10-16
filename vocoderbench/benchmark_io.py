"""固定集合の比較で用いる版情報・中断再開・数値集約。"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = json.loads((ROOT / 'BASELINE.json').read_text(encoding='utf-8'))['version']
LABELS = {'identity': '原音', 'pml': f'自作PML {BASE_VERSION.removeprefix("pml-")}（当時のベース）',
          'candidate': 'Git管理外の開発候補', 'world_harvest': 'WORLD（Harvest）'}
SEEDS = tuple(range(8))


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    for attempt in range(5):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            logging.warning('結果の置換が一時的に拒否されました。再試行します: %s', path, exc_info=True)
            time.sleep(0.05 * (attempt + 1))


def external_candidate(path):
    """採否未定のコードはGit管理外から明示的に読み込む。"""
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('採否未定の候補パッケージはリポジトリ外へ置いてください')
    name = '_vocoder_candidate'
    spec = importlib.util.spec_from_file_location(name, path / '__init__.py',
                                               submodule_search_locations=[str(path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return importlib.import_module(name + '.pml')


def source_contract(manifest, candidate, criteria=None):
    import scipy
    from . import world
    from .logging_utils import run_process
    library = world.library_path()
    head = run_process(['git', 'rev-parse', 'HEAD'], cwd=ROOT).stdout.strip()
    selected = ['benchmark.py', 'benchmark_io.py', 'benchmark_pipeline.py', 'metrics.py', 'extended_metrics.py',
                'temporal_metrics.py', 'corpus.py', 'mos.py', 'mos_batch.py', 'world.py', 'control.py']
    selected += [str(p.relative_to(ROOT / 'vocoderbench')) for p in (ROOT / 'vocoderbench/pml').glob('*.py')]
    return {'schema_version': 1, 'manifest_sha256': sha(manifest),
            'formal_base': read(ROOT / 'BASELINE.json'), 'baseline_sha256': sha(ROOT / 'BASELINE.json'),
            'method_sources': {'pml': {'repository_commit': head, 'path': 'vocoderbench/pml/*.py'},
                               'candidate': {'path': 'Git外の候補。棄却時はコードを公開せず完全再実行はできない'},
                               'world_harvest': read(ROOT / 'vocoderbench/world.lock.json')},
            'world_binary_sha256': sha(library), 'world_build': read(library.parent / 'build.json'),
            'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                            'scipy': scipy.__version__, 'platform': platform.platform()},
            'source_sha256': {name: sha(ROOT / 'vocoderbench' / name) for name in sorted(set(selected))},
            'dependency_lock_sha256': sha(ROOT / 'uv.lock'),
            'decision_criteria_sha256': sha(criteria if criteria is not None else
                ROOT / 'experiments/2026-10-12/noise-envelope/reviews/criteria.md'),
            'candidate_source_sha256': {str(p.relative_to(candidate)): sha(p) for p in sorted(Path(candidate).rglob('*.py'))},
            'noise_seeds': SEEDS, 'mos_noise_seed': 0, 'mos_extraction_seed': 20261012,
            'mos_repetitions': 1, 'mos_domain': 'bvcc', 'alignment': 'none', 'normalization': 'none',
            'interpretation': '固定した開発・比較集合。未使用の最終評価集合ではない'}


def temporal_scalars(measurement):
    values = {}
    for band in measurement.get('bands', []):
        if band.get('status') != 'measured':
            continue
        for window in band['windows']:
            key = f"{band['name']}_{window['window_ms']:g}ms"
            for metric in ('log_rms_mae_db', 'rms_envelope_nrmse', 'envelope_correlation'):
                values[key + '_' + metric] = window['metrics'].get(metric)
            values[key + '_modulation_mae_db'] = window['modulation_bands'].get('active_band_mae_db')
    return values


def seed_summary(records):
    keys = sorted({key for record in records for key in record.get('values', {})})
    result = {}
    for key in keys:
        values = [r.get('values', {}).get(key) for r in records]
        valid = [v for v in values if v is not None and np.isfinite(v)]
        result[key] = {'mean': float(np.mean(valid)) if valid else None,
                       'standard_deviation': float(np.std(valid, ddof=1)) if len(valid) > 1 else None,
                       'minimum': min(valid) if valid else None, 'maximum': max(valid) if valid else None,
                       'valid_count': len(valid), 'planned_count': len(records)}
    return result
