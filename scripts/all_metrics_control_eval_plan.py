"""control/curve終端gateの予定集合。既存ファイルglobから予定を推測しない。"""
from __future__ import annotations

import math

from all_metrics_common import METHODS, RUN, read
from all_metrics_control_eval import CONDITIONS, native_conditions
from all_metrics_control_eval_curves import CURVES, QUALITY_METRICS


def expected_records(specs):
    for spec in specs:
        for method in METHODS:
            base = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method}
            for condition in CONDITIONS:
                yield {**base, 'stage': 'controls', 'condition': condition,
                       'path': str(RUN / 'controls/measurements' / f'{spec["id"]}__{method}__{condition}.json')}
            if method in METHODS[:2]:
                for condition in ('slope_minus3', 'slope_plus3'):
                    yield {**base, 'stage': 'controls-slope', 'condition': condition,
                           'path': str(RUN / 'controls-slope/measurements' / f'{spec["id"]}__{method}__{condition}.json')}
            for condition in native_conditions(method):
                yield {**base, 'stage': 'native', 'condition': condition,
                       'path': str(RUN / 'native' / method / spec['id'] / f'{condition}.json')}
                for stage in ('mos', 'speaker-full'):
                    yield {**base, 'stage': stage, 'condition': condition,
                           'path': str(RUN / stage / 'measurements' / f'{spec["id"]}__{method}__{condition}.json')}
            for control in CURVES:
                yield {**base, 'stage': 'edit-quality', 'control': control,
                       'path': str(RUN / 'edit-quality/measurements' / f'{spec["id"]}__{method}__{control}.json')}


def unresolved_record(expected, row):
    """失敗は終端でも成功ではない。Noneは構造上終端、strは未到着/証拠不足。"""
    for key in ('case', 'method', 'condition', 'control'):
        if key in expected and row.get(key) != expected[key]:
            return 'record_identity_mismatch'
    state = row.get('status', 'missing_status')
    if state.startswith('pending') or state in ('running', 'missing_status'):
        return state
    if state not in ('measured', 'failed', 'unsupported', 'not_applicable', 'upstream_failed', 'partial', 'unavailable'):
        return 'unrecognized_status:' + state
    if state == 'measured':
        if expected['stage'] in ('controls', 'controls-slope') and not isinstance(row.get('measurement'), dict):
            return 'control_measurement_evidence_missing'
        if expected['stage'] == 'native' and not all(key in row.get('audio', {}) for key in
                ('path', 'file_sha256', 'float64_sha256', 'sample_rate', 'samples')):
            return 'native_audio_evidence_missing'
        if expected['stage'] in ('mos', 'speaker-full'):
            value = row.get('value')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return 'quality_success_value_missing'
            if not row.get('audio_sha256') or not row.get('configuration_sha256'):
                return 'quality_success_identity_missing'
    if expected['stage'] == 'edit-quality':
        points = row.get('points', [])
        if [p.get('condition') for p in points] != [p[0] for p in CURVES[expected['control']]]:
            return 'curve_planned_points_missing_or_reordered'
        if row.get('terminal') is not True:
            return 'curve_not_terminal'
        for point in points:
            for metric in QUALITY_METRICS:
                quality = point.get('quality', {}).get(metric)
                if not quality:
                    return 'curve_quality_missing'
                status = quality.get('status', 'pending_quality')
                if status.startswith('pending') or status == 'quality_failure_evidence_insufficient':
                    return status
                if status == 'ok':
                    value = quality.get('value')
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                        return 'curve_success_value_missing'
                    if not quality.get('audio_sha256') or not quality.get('configuration_sha256'):
                        return 'curve_success_identity_missing'
    return None


def terminal_inventory(specs):
    from pathlib import Path
    rows = []
    for expected in expected_records(specs):
        path = Path(expected['path'])
        if path.exists():
            value = read(path)
            reason = unresolved_record(expected, value)
            rows.append({**expected, 'status': value.get('status'), 'terminal': reason is None, 'unresolved_reason': reason})
        else:
            rows.append({**expected, 'status': 'pending_record', 'terminal': False, 'unresolved_reason': 'planned_record_absent'})
    return rows
