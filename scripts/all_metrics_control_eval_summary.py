"""全予定control群の録音値・分母・欠測を列挙し、話者macro順位側へ渡す。"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_control_eval import CONDITIONS, applicable
from all_metrics_control_eval_curves import CURVES, QUALITY_METRICS, applicable as curve_applicable
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def planned_row(spec, method, condition, stage='controls', supported=True):
    path = RUN / stage / 'measurements' / f'{spec["id"]}__{method}__{condition}.json'
    expected = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method}
    if path.exists():
        row = read(path)
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError('集約予定rowのcase/speaker/methodが不一致です')
        key = 'control' if stage == 'edit-quality' else 'condition'
        if row.get(key) != condition:
            raise ValueError('集約予定rowの条件が不一致です')
        contract_path = RUN / stage / 'contract.json'
        if not contract_path.exists() or row.get('contract_sha256') != sha256(contract_path):
            raise ValueError('control集約対象の科学契約が不一致です')
        row = {**row, 'raw_result_sha256': sha256(path)}
    else:
        row = {**expected, 'condition': condition, 'control': condition,
               'status': 'pending_measurement' if supported else 'unsupported', 'value': None,
               'reason': '予定正式rowが未到着' if supported else '真のnative操作なし'}
    row['raw_result'] = str(path)
    return row


def main():
    groups, by_time = {}, defaultdict(dict)
    specs = read(RUN / 'inputs.json')
    if len(specs) != 120 or len({s['id'] for s in specs}) != 120 or len({s['speaker'] for s in specs}) != 40:
        raise ValueError('固定120録音40話者の完全予定manifestが必要です')

    def emit(group, row, value, unit, direction='lower', status=None, denominator=None, methods=METHODS, **extra):
        definition = groups.setdefault(group, {'id': group, 'label': group, 'unit': unit, 'direction': direction,
            'methods': list(methods), 'planned_methods': list(METHODS), 'admissible_status': ['measured'],
            'rankable': direction in ('lower', 'higher'), 'observation_unit': 'utterance',
            'planned_recordings_per_method': len(specs), 'planned_speakers_per_method': len({s['speaker'] for s in specs}),
            'aggregation': 'common successful cases within declared methods; utterance -> speaker -> equal speaker weight',
            'rows': []})
        if value is not None and not np.isfinite(value):
            raise ValueError('順位入力に非有限値があります')
        state = status or ('measured' if value is not None else row['status'])
        if value is None and state in ('measured', 'ok', 'partial'):
            state = 'not_applicable' if row['status'] == 'measured' else 'missing_metric_evidence'
        definition['rows'].append({'case': row['case'], 'speaker': row['speaker'], 'method': row['method'],
            'value': value, 'status': state, 'denominator': denominator, 'raw_result': row['raw_result'],
            'raw_result_sha256': row.get('raw_result_sha256'), **extra})

    for spec in specs:
        for method in METHODS:
            for condition in CONDITIONS:
                row = planned_row(spec, method, condition, supported=applicable(method, condition))
                measure = row.get('measurement', {})
                outer = row['status'] == 'measured'
                valid = outer and measure.get('status') in ('ok', 'partial')
                state = measure.get('status', 'missing_metric_evidence') if outer else row['status']
                if condition.startswith('pitch_'):
                    emit('7.' + condition + '.relative_f0_mae', row, measure.get('value') if valid else None, 'cent',
                         denominator=measure.get('valid_voiced_frames'), methods=[m for m in METHODS if m != 'facodec'],
                         total_frames=measure.get('total_frames'), expected_voiced_frames=measure.get('expected_voiced_frames'),
                         unmapped_frames=measure.get('unmapped_frames'), status='measured' if valid and measure.get('value') is not None else state)
                    count, missing = measure.get('expected_voiced_frames'), measure.get('missing_voiced_frames')
                    rate_valid = outer and count is not None and count > 0 and missing is not None
                    emit('7.' + condition + '.missing_voiced_fraction', row, missing / count if rate_valid else None,
                         'fraction', denominator=count, methods=[m for m in METHODS if m != 'facodec'],
                         status='measured' if rate_valid else state)
                elif condition.startswith('gain_') and condition != 'gain_interference':
                    emit('8.' + condition + '.rms_frame_mae', row, measure.get('value') if valid else None,
                         'dB', denominator=measure.get('errors', {}).get('count'), methods=[m for m in METHODS if m != 'facodec'],
                         status='measured' if valid else state)
                elif condition == 'gain_interference':
                    cells = {cell['attribute']: cell for cell in measure.get('matrix', [])}
                    for attribute in ('pitch_cents', 'level_db', 'slope_db_per_octave', 'duration_seconds'):
                        cell = cells.get(attribute, {})
                        value = cell.get('absolute_normalized_error') if valid else None
                        emit('11.gain.' + attribute + '.absolute_normalized_response_error', row, value, 'normalized',
                             denominator=1 if value is not None else 0, methods=[m for m in METHODS if m != 'facodec'],
                             status='measured' if value is not None else cell.get('status', state),
                             control_scale=cell.get('control_scale'), attribute_scale=cell.get('attribute_scale'),
                             expected_response=cell.get('expected_response'))
                elif condition in ('time_scale1p25', 'time_preservation'):
                    by_time[(spec['id'], condition)][method] = row
                    members = METHODS[:2] if condition == 'time_scale1p25' else METHODS
                    duration = measure.get('absolute_duration_error_seconds') if outer else None
                    emit('9.' + condition + '.absolute_duration_error', row, duration, 's',
                         denominator=1 if duration is not None else 0, methods=members,
                         status='measured' if duration is not None else state)
                    count, missing = measure.get('event_count'), measure.get('missing_events')
                    rate_valid = outer and count is not None and count > 0 and missing is not None
                    emit('9.' + condition + '.missing_event_fraction', row, missing / count if rate_valid else None,
                         'fraction', denominator=count, methods=members, status='measured' if rate_valid else state,
                         event_status_counts=dict(Counter(event['status'] for event in measure.get('events', []))),
                         interpretation='未検出・比較不能event率。窓外・重複除外も含む。')
                elif condition == 'slope_preservation':
                    emit('10.slope_preservation.native_slope_error', row, measure.get('value') if outer else None,
                         'dB/oct', denominator=1 if outer else 0,
                         scope='各実SR・全長の傾斜保存。共通prefix品質とは別。')
            for condition in ('slope_minus3', 'slope_plus3'):
                row = planned_row(spec, method, condition, 'controls-slope', supported=method in METHODS[:2])
                measure = row.get('measurement', {})
                emit('10.' + condition + '.native_slope_error', row,
                     measure.get('value') if row['status'] == 'measured' else None, 'dB/oct', denominator=1,
                     methods=METHODS[:2], reference='same native unedited decoded',
                     scope='newly defined existing native spectral-field operation')
            for control, points in CURVES.items():
                row = planned_row(spec, method, control, 'edit-quality', supported=curve_applicable(method, control))
                observed = {point['condition']: point for point in row.get('points', [])}
                for condition, amount in points:
                    fallback = ('missing_metric_evidence' if row['status'] in ('measured', 'partial') else row['status'])
                    point = observed.get(condition, {'quality': {}, 'status': fallback, 'delta_from_unedited': {}})
                    for metric in QUALITY_METRICS:
                        quality = point['quality'].get(metric, {})
                        value = quality.get('value') if quality.get('status') == 'ok' else None
                        missing = 'missing_metric_evidence' if point['status'] == 'measured' else point['status']
                        status = 'measured' if value is not None else quality.get('status', missing)
                        prefix = '12.' + control + '.' + condition + '.' + metric
                        unit = 'predicted MOS' if metric == 'predicted_mos' else 'cosine'
                        members = [m for m in METHODS if curve_applicable(m, control)]
                        emit(prefix, row, value, unit, 'higher', status=status, denominator=1 if value is not None else 0,
                             methods=members, full_native_length=True, control_amount=amount)
                        if condition != 'unedited':
                            delta = point['delta_from_unedited'].get(metric)
                            emit(prefix + '.delta_from_unedited', row, delta, unit, 'higher', methods=members,
                                 status='measured' if delta is not None else point.get('delta_status', {}).get(metric, status),
                                 denominator=1 if delta is not None else 0)
    for (_, condition), methods in by_time.items():
        members = METHODS[:2] if condition == 'time_scale1p25' else METHODS
        successful = [{event['event_id'] for event in methods[method].get('measurement', {}).get('events', [])
                       if event['status'] == 'ok' and methods[method]['status'] == 'measured'} for method in members]
        common = set.intersection(*successful)
        for row in methods.values():
            events = [event for event in row.get('measurement', {}).get('events', [])
                      if event['status'] == 'ok' and event['event_id'] in common]
            value = float(np.mean([abs(event['error_ms']) for event in events])) if events else None
            emit('9.' + condition + '.common_event_mae', row, value, 'ms', methods=members,
                 status='measured' if value is not None else row['status'] if row['status'] != 'measured' else 'not_applicable',
                 denominator=len(events), common_event_ids=sorted(common),
                 method_specific_all_detected_mae=row.get('measurement', {}).get('value'))
    for group in groups.values():
        group['by_method'] = {}
        for method in METHODS:
            rows = [row for row in group['rows'] if row['method'] == method]
            values = [row['value'] for row in rows if row['value'] is not None and row['status'] == 'measured']
            group['by_method'][method] = {'rows_present': len(rows), 'valid_recordings': len(values),
                'status_counts': dict(Counter(row['status'] for row in rows)),
                'available_case_arithmetic_mean_auxiliary_only': float(np.mean(values)) if values else None}
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_control_eval.py', ROOT / 'scripts/all_metrics_control_eval_curves.py']
    contract_path = RUN / 'control-groups-contract.json'
    freeze(contract_path, {'schema_version': 2, 'input_contract_sha256': sha256(RUN / 'input-contract.json'),
        'inputs_sha256': sha256(RUN / 'inputs.json'),
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        'group_definitions': [{key: value for key, value in group.items() if key not in ('rows', 'by_method')}
                              for group in groups.values()]})
    write_json(RUN / 'control-metric-groups.json', {'created_at_utc': now(), 'contract_sha256': sha256(contract_path),
        'script_sha256': sha256(Path(__file__)), 'groups': list(groups.values()),
        'planned_row_policy': 'Every frozen case/method/condition enumerated, including absent records and unsupported points',
        'ranking_scope': 'point conditions separate; no composite winner; common event IDs before utterance aggregation',
        'pending_is_not_zero_or_last_rank': True})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-control-summary'))
