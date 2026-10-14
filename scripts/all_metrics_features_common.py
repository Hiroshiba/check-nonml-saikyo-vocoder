"""#14/#15の固定特徴派生、原音target、読み出し用統計。"""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import json

import numpy as np

from all_metrics_common import ROOT, RUN, freeze, read
from vocoderbench.quality_core import sha256, write_json

PLAN = ROOT / 'research/all-method-features-plan-recovery-2026-10-14.md'
TRAIN = RUN / 'readout-train'
OUT = RUN / 'feature-assessment'
TARGETS = {'log_f0': 'ln(Hz)', 'rms_dbfs': 'dBFS', 'spectral_slope': 'dB/octave'}


def npy_hash(array):
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def semantic_schema(schema):
    if isinstance(schema, dict):
        return {key: semantic_schema(value) for key, value in schema.items()
                if key not in ('frame_count', 'frame_times_seconds', 'source_frames')}
    if isinstance(schema, list):
        return [semantic_schema(value) for value in schema]
    return schema


def project(matrix, schema, method):
    matrix = np.asarray(matrix, dtype=np.float64)
    result_schema = semantic_schema(schema)
    if method == 'magphase':
        if schema['columns'][-1] != {'field': 'lf0', 'width': 1}:
            raise ValueError('MagPhase lf0列が既知のschemaと不一致')
        voiced = matrix[:, -1] > 0
        if np.any((~voiced) & (matrix[:, -1] != -1e10)):
            raise ValueError('未知のMagPhase無声sentinel')
        matrix = matrix.copy()
        matrix[~voiced, -1] = 0
        matrix = np.column_stack((matrix, voiced.astype(float)))
        result_schema['columns'][-1:] = [
            {'field': 'voiced_lf0_else_zero', 'width': 1}, {'field': 'voiced_mask', 'width': 1}]
        result_schema['dimension_count'] = matrix.shape[1]
        result_schema['categorical_sentinel_projection'] = 'lf0 -1e10 -> value 0 and voiced_mask 0'
    if matrix.ndim != 2 or not all(matrix.shape) or not np.isfinite(matrix).all():
        raise ValueError('特徴配列のshape/有限性が不正')
    return matrix, result_schema


def feature_path(root, method, identifier):
    return root / 'native' / method / identifier


def load_feature(root, method, identifier):
    folder = feature_path(root, method, identifier)
    record = read(folder / 'features.json')
    if record['status'] != 'measured':
        raise ValueError(f'特徴抽出未成功: {method}/{identifier}')
    path = folder / ('features.npz' if record.get('storage') == 'lossless_npz' else 'features.npy')
    if sha256(path) != record['sha256']:
        raise ValueError(f'特徴hash不一致: {path}')
    if path.suffix == '.npz':
        with np.load(path, allow_pickle=False) as archive:
            matrix = archive['features']
        if npy_hash(matrix) != record['uncompressed_npy_sha256']:
            raise ValueError('復元NPY hash不一致')
    else:
        matrix = np.load(path, allow_pickle=False)
    projected, schema = project(matrix, record['schema'], method)
    return projected, schema, record


def source_contract(extra=()):
    paths = [PLAN, *sorted((ROOT / 'scripts').glob('all_metrics_features*.py')),
             ROOT / 'vocoderbench/assessment/representation.py',
             ROOT / 'vocoderbench/assessment/common.py', ROOT / 'vocoderbench/assessment/acoustics.py',
             ROOT / 'vocoderbench/metrics.py', *extra]
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def prepare_input_contract():
    inputs = RUN / 'corpora/readout-train/inputs.json'
    manifest = RUN / 'corpora/readout-train/manifest.json'
    selection = read(manifest)
    train, evaluation = read(inputs), read(RUN / 'inputs.json')
    if (selection.get('schema_version') != 1 or selection.get('split') != 'dev-clean'
            or not selection.get('selection_rule') or not selection.get('selection_inputs_sha256')):
        raise ValueError('新runのdev-clean選択規則/出典を先に固定してください')
    entries = selection['entries']
    if [(r['id'], r['speaker']) for r in entries] != [(r['id'], r['speaker']) for r in train]:
        raise ValueError('train manifestと入力の順序/ID/話者が不一致')
    for rows in (train, evaluation):
        counts = Counter(row['speaker'] for row in rows)
        if len(rows) != 120 or len(counts) != 40 or set(counts.values()) != {3}:
            raise ValueError('固定120録音/40話者/各3録音を必要とします')
        if len({row['id'] for row in rows}) != 120:
            raise ValueError('固定入力の録音IDが重複')
    source_ids = [row['source_utterance_id'] for row in entries]
    eval_manifest = read(ROOT / 'data/clean_speech_v1.json')['entries']
    if (len(set(source_ids)) != 120 or set(source_ids) & {r['source_utterance_id'] for r in eval_manifest}
            or {r['id'] for r in evaluation} != {r['id'] for r in eval_manifest}):
        raise ValueError('train/evalの元発話重複または評価群変更')
    for field in ('speaker', 'id', 'sha256'):
        if {row[field] for row in train} & {row[field] for row in evaluation}:
            raise ValueError(f'train/evalが重複: {field}')
    freeze(TRAIN / 'input-contract.json', {'schema_version': 2, 'role': 'train_only',
        'inputs_sha256': sha256(inputs), 'manifest_sha256': sha256(manifest),
        'evaluation_inputs_sha256': sha256(RUN / 'inputs.json'), 'plan_sha256': sha256(PLAN),
        'selection_rule': selection['selection_rule'],
        'selection_inputs_sha256': selection['selection_inputs_sha256'],
        'implementation_origin': 'new_recovery_run_selection_not_assumed_identical_to_old_manifest',
        'scope': 'fixed dev-clean120/40; encode/readout only; no decoder payload or audio'})
    for index in range(0, len(train), 10):
        freeze(TRAIN / 'input-batches' / f'{index // 10:02d}.json', train[index:index+10])
    return train, evaluation


def target_measurements():
    from vocoderbench.assessment.acoustics import spectral_slope
    from vocoderbench.assessment.common import NotApplicable
    from vocoderbench.metrics import estimate_f0_yin
    train, evaluation = prepare_input_contract()
    config = {'frame_ms': 80.0, 'hop_ms': 10.0, 'fmin': 65.0, 'fmax': 700.0,
              'threshold': .15, 'rms_threshold': 1e-5, 'prefilter_hz': 2000.0}
    contract = {'source_sha256': source_contract(), 'yin': config, 'slope_band_hz': [300, 5000],
                'units': TARGETS, 'input_contract_sha256': sha256(TRAIN / 'input-contract.json')}
    freeze(OUT / 'targets/contract.json', contract)
    for split, specs in (('train', train), ('evaluation', evaluation)):
        for spec in specs:
            path = OUT / 'targets' / split / f'{spec["id"]}.json'
            if path.exists():
                previous = read(path)
                if (previous['contract_sha256'] != sha256(OUT / 'targets/contract.json')
                        or previous['source_sha256'] != spec['sha256']):
                    raise ValueError('保存済み原音targetの契約/入力が不一致')
                continue
            if sha256(spec['path']) != spec['sha256']:
                raise ValueError('原音target入力hash不一致')
            wave = np.load(spec['path'], allow_pickle=False).astype(np.float64)
            f0 = estimate_f0_yin(wave, spec['sample_rate'], **config)
            voiced = f0['f0_hz'] > 0
            power = float(np.mean(wave**2))
            reasons = {}
            try:
                slope = spectral_slope(wave, spec['sample_rate'], 300, 5000)
            except NotApplicable as error:
                import logging
                logging.warning('原音傾斜target適用外: %s %s', spec['id'], error, exc_info=True)
                slope = None
                reasons['spectral_slope'] = str(error)
            targets = {'log_f0': float(np.log(f0['f0_hz'][voiced]).mean()) if voiced.any() else None,
                       'rms_dbfs': float(10*np.log10(power)) if power > 0 else None,
                       'spectral_slope': slope}
            if not voiced.any():
                reasons['log_f0'] = 'no positive voiced YIN estimates'
            if power <= 0:
                reasons['rms_dbfs'] = 'zero power'
            write_json(path, {'id': spec['id'], 'speaker': spec['speaker'], 'split': split,
                'source_sha256': spec['sha256'], 'targets': targets,
                'target_status': {key: 'measured' if value is not None else 'not_applicable'
                                  for key, value in targets.items()},
                'missing_reasons': reasons,
                'yin_total_frames': len(voiced), 'yin_voiced_frames': int(voiced.sum()),
                'yin_f0_hz': f0['f0_hz'].tolist(), 'yin_min_cmnd': f0['min_cmnd'].tolist(),
                'yin_start_samples': f0['start_samples'].tolist(), 'power': power,
                'contract_sha256': sha256(OUT / 'targets/contract.json')})


def save_npz(path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **arrays)
    temporary.replace(path)


def schema_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


if __name__ == '__main__':
    target_measurements()
