"""全予定curve点へnative全長MOS/固定原音全長ECAPAを結ぶ。欠落点も列挙。"""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import numpy as np

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from all_metrics_control_eval_equivalence import verified_record
from all_metrics_controls import checked_audio
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

CURVES = {
    'pitch': [['pitch_minus3', -3.], ['unedited', 0.], ['pitch_plus3', 3.]],
    'gain': [['gain_minus6', -6.], ['unedited', 0.], ['gain_plus6', 6.]],
    'time': [['unedited', 1.], ['time_scale1p25', 1.25]],
    'slope': [['slope_minus3', -3.], ['unedited', 0.], ['slope_plus3', 3.]],
}
UNITS = {'pitch': 'semitone', 'gain': 'dB', 'time': 'output/input duration ratio', 'slope': 'dB/oct'}
QUALITY_METRICS = ('predicted_mos', 'speaker_similarity')


def applicable(method, control):
    return method != 'facodec' and (control in ('pitch', 'gain') or method in METHODS[:2])


def quality(spec, method, condition, native, metric):
    folder = 'mos' if metric == 'predicted_mos' else 'speaker-full'
    path = RUN / folder / 'measurements' / f'{spec["id"]}__{method}__{condition}.json'
    if not path.exists():
        return {'status': 'pending_quality', 'value': None, 'source_result': str(path),
                'reason': '固定評価器の正式結果が未到着。後から再読する。'}
    row = read(path)
    if any(row.get(key) != expected for key, expected in [('case', spec['id']), ('method', method), ('condition', condition)]):
        raise ValueError('品質curve点のcase/method/conditionが不一致です')
    result = {key: row.get(key) for key in ('value', 'unit', 'direction', 'configuration_sha256')}
    result.update(status='ok' if row['status'] == 'measured' else row['status'],
                  source_result=str(path), source_result_sha256=sha256(path))
    if row.get('audio_sha256') is not None and row['audio_sha256'] != native['audio']['file_sha256']:
        raise ValueError('native全長音声と品質証跡のhashが不一致です')
    if row['status'] == 'measured':
        if row.get('audio_sha256') != native['audio']['file_sha256'] or not row.get('configuration_sha256'):
            raise ValueError('成功品質値の対象音声/評価器証跡が不足しています')
        if row['value'] is None or not np.isfinite(row['value']):
            raise ValueError('成功品質値は有限値が必要です')
        result['audio_sha256'] = row['audio_sha256']
    else:
        result['value'] = None
        if row.get('source_record') and row.get('source_record_sha256'):
            proof = verified_record(row['source_record'], row['source_record_sha256'])
            if read(row['source_record']).get('audio', {}).get('file_sha256') != native['audio']['file_sha256']:
                raise ValueError('失敗品質証跡の対象波形が不一致です')
            result['source_identity'] = proof
        elif row.get('audio_sha256') != native['audio']['file_sha256']:
            result.update(status='quality_failure_evidence_insufficient', reason='失敗時の対象波形証拠がありません')
    return result


def evaluate(spec, method, control, signature):
    path = RUN / 'edit-quality/measurements' / f'{spec["id"]}__{method}__{control}.json'
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
           'control': control, 'control_unit': UNITS[control], 'contract_sha256': signature,
           'status': 'unsupported', 'points': []}
    supported = applicable(method, control)
    if not supported:
        row['reason'] = '該当する真のnative表現操作がありません'
    for condition, amount in CURVES[control]:
        source = RUN / 'native' / method / spec['id'] / f'{condition}.json'
        state = 'pending_audio' if supported else 'unsupported'
        point = {'condition': condition, 'amount': amount, 'native_record': str(source),
                 'quality': {metric: {'status': state, 'value': None} for metric in QUALITY_METRICS}, 'status': state}
        if supported and source.exists():
            native = read(source)
            if any(native.get(key) != expected for key, expected in [('case', spec['id']), ('method', method), ('condition', condition)]):
                raise ValueError('curve点のnative identityが不一致です')
            point.update(native_record_sha256=sha256(source), status=native['status'])
            if native['status'] == 'measured':
                checked_audio(native)
                point.update(audio=native['audio'], duration_seconds=native['audio']['seconds'], output_peak=native['audio']['peak'])
                point['quality'] = {metric: quality(spec, method, condition, native, metric) for metric in QUALITY_METRICS}
            else:
                state = 'pending_audio' if native['status'].startswith('pending') else 'upstream_failed'
                point['quality'] = {metric: {'status': state, 'value': None, 'upstream_status': native['status']}
                                    for metric in QUALITY_METRICS}
        row['points'].append(point)
    baseline = next(point for point in row['points'] if point['condition'] == 'unedited')
    for point in row['points']:
        point['delta_from_unedited'], point['delta_status'] = {}, {}
        for metric, current in point['quality'].items():
            base = baseline['quality'][metric]
            valid = current['status'] == base['status'] == 'ok'
            if valid and current['configuration_sha256'] != base['configuration_sha256']:
                raise ValueError('品質curve途中で評価器設定が変わりました')
            point['delta_from_unedited'][metric] = current['value'] - base['value'] if valid else None
            point['delta_status'][metric] = ('measured' if valid else 'unsupported' if not supported else
                'pending_quality' if any(item['status'].startswith('pending') for item in (current, base)) else 'upstream_quality_failed')
    states = [item['status'] for point in row['points'] for item in point['quality'].values()]
    measured = states.count('ok')
    pending = any(state.startswith('pending') for state in states)
    row.update(status='unsupported' if not supported else 'pending' if pending else 'measured' if measured == len(states) else 'partial',
               terminal=not pending, quality_values_measured=measured, quality_values_planned=len(states),
               quality_values_applicable=len(states) if supported else 0)
    previous = read(path) if path.exists() else None
    if previous:
        if previous['contract_sha256'] != signature:
            raise ValueError('品質curveの再読契約が変わりました')
        if {key: value for key, value in previous.items() if key != 'updated_at_utc'} == row:
            return previous
        write_json(path.parent.parent / 'history' / f'{path.stem}-{time.time_ns()}.json', previous)
    row['updated_at_utc'] = now()
    write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True, choices=range(12))
    args = parser.parse_args()
    sources = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', ROOT / 'scripts/all_metrics_controls.py', ROOT / 'scripts/all_metrics_control_eval_equivalence.py']
    contract = {'schema_version': 2, 'source_sha256': {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        'input_contract_sha256': sha256(RUN / 'input-contract.json'), 'curves': CURVES,
        'quality': ['native_full_length_utmosv2', 'independent_full_length_ecapa_fixed_original_excerpt_reference'],
        'source_reference': 'fixed original excerpt full length, not entire corpus utterance',
        'control_reference': 'unedited decoded output for point deltas',
        'content_metric': 'not measured for native edits in this contract',
        'pending_policy': 'every planned point explicit; reread when upstream quality arrives',
        'no_composite_curve_quality_scalar': True, 'edited_audio_reference_distance_penalty': False}
    path = RUN / 'edit-quality/contract.json'
    freeze(path, contract)
    rows = []
    for spec in read(RUN / 'inputs.json')[args.batch * 10:(args.batch + 1) * 10]:
        for method in METHODS:
            for control in CURVES:
                rows.append(evaluate(spec, method, control, sha256(path)))
        write_json(RUN / f'edit-quality/batch-{args.batch:02d}.json', {'updated_at_utc': now(), 'rows': rows})
    return int(any(not row['terminal'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-control-eval-curves'))
