"""固定集合の比較で用いる版情報・中断再開・数値集約。"""
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'identity': '原音', 'pml': '自作PML（当時のベース）',
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
