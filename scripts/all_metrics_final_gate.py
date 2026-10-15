"""正式予定集合の終端を確認する。既存globだけで未到着の群やpointを見逃さない。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from all_metrics_common import METHODS, RUN
from all_metrics_rankings_core import finite, pending, special_terminal

LATENT = ('quantized_float16', 'quantized_float32', 'interpolation_input_gain_alpha0',
          'interpolation_input_gain_alpha0p5', 'interpolation_input_gain_alpha1')
EDITS = ('pitch_minus3', 'pitch_plus3', 'gain_minus6', 'gain_plus6')


def expected_main(specs):
    from all_metrics_control_eval_plan import expected_records
    yield from expected_records(specs)
    for spec in specs:
        base = {'case': spec['id'], 'speaker': spec['speaker']}
        metadata = spec['metadata']
        if metadata['source_samples'] == metadata['excerpt_samples'] and metadata['excerpt_start_sample'] == 0:
            for method in ('original', *METHODS):
                yield {**base, 'method': method, 'stage': 'asr-recognition',
                       'path': str(RUN / 'asr/recognitions' / f'{spec["id"]}__{method}.json')}
        yield {'case': spec['id'], 'stage': 'evaluation-target', 'identity_key': 'id',
               'path': str(RUN / 'feature-assessment/targets/evaluation' / f'{spec["id"]}.json')}
        yield {**base, 'method': 'original', 'condition': 'unedited', 'stage': 'mos',
               'path': str(RUN / 'mos/measurements' / f'{spec["id"]}__original__unedited.json')}
        for method in METHODS:
            row = {**base, 'method': method}
            for stage in ('acoustic', 'asr', 'latent-evaluation'):
                yield {**row, 'stage': stage,
                       'path': str(RUN / stage / 'measurements' / f'{spec["id"]}__{method}.json')}
            yield {**row, 'stage': 'features',
                   'path': str(RUN / 'native' / method / spec['id'] / 'features.json')}
            for condition in LATENT:
                yield {**row, 'stage': 'native', 'condition': condition,
                       'path': str(RUN / 'native' / method / spec['id'] / f'{condition}.json')}
                for stage in ('mos-latent', 'latent-speaker'):
                    yield {**row, 'stage': stage, 'condition': condition,
                           'path': str(RUN / stage / 'measurements' / f'{spec["id"]}__{method}__{condition}.json')}
            if method != 'facodec':
                for precision in LATENT[:2]:
                    for edit in EDITS:
                        condition = precision + '__' + edit
                        yield {**row, 'stage': 'native', 'condition': condition,
                               'path': str(RUN / 'native' / method / spec['id'] / f'{condition}.json')}


def unresolved_nested(value, path=''):
    if isinstance(value, dict):
        if 'status' in value and pending(value['status']):
            return path + '.status:' + str(value['status'])
        for key, item in value.items():
            if key not in ('history', 'failure_history', 'source_records'):
                reason = unresolved_nested(item, path + '.' + key)
                if reason:
                    return reason
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reason = unresolved_nested(item, f'{path}[{index}]')
            if reason:
                return reason
    return None


def inspect(expected, sources):
    from all_metrics_control_eval_plan import unresolved_record
    row = sources.get(expected['path'])
    reason = None
    if row is None:
        reason = 'planned_record_absent'
    else:
        for key in ('case', 'method', 'condition', 'control'):
            raw_key = expected.get('identity_key', key) if key == 'case' else key
            if key in expected and row.get(raw_key) != expected[key]:
                reason = 'record_identity_mismatch:' + key
                break
        state = row.get('status', 'missing_status')
        if expected['stage'] in ('evaluation-target', 'train-target'):
            target_states = row.get('target_status', {})
            state = ('measured' if set(target_states) == {'log_f0', 'rms_dbfs', 'spectral_slope'}
                     and all(value in ('measured', 'not_applicable') for value in target_states.values())
                     else 'missing_status')
        if reason is None and pending(state):
            reason = state
        if reason is None and expected['stage'] in ('controls', 'controls-slope', 'edit-quality', 'native', 'mos', 'speaker-full'):
            reason = unresolved_record(expected, row)
        if reason is None and state in ('measured', 'partial', 'ok'):
            reason = unresolved_nested(row)
        if reason is None and expected['stage'] in ('mos-latent', 'latent-speaker') and state == 'measured':
            if not finite(row.get('value')) or not row.get('configuration_sha256') or not row.get('audio_sha256'):
                reason = 'quality_success_evidence_missing'
        if reason is None and expected['stage'] == 'features' and state == 'measured':
            if not row.get('sha256') or not row.get('schema'):
                reason = 'feature_success_evidence_missing'
        if reason is None and state in ('measured', 'ok', 'partial'):
            required = {'acoustic': ('measurement', 'extended', 'auditory_local'),
                        'asr': ('measurement', 'configuration_sha256'),
                        'asr-recognition': ('text', 'audio', 'configuration_sha256'),
                        'latent-evaluation': ('metrics', 'contract_sha256'),
                        'train-features': ('moments_sha256', 'schema', 'contract_sha256'),
                        'human-features': ('mean_sha256', 'schema', 'contract_sha256'),
                        'vctk-quality': ('value',), 'vctk-native': ('audio',),
                        'evaluation-target': ('targets',), 'train-target': ('targets',)}
            if any(key not in row for key in required.get(expected['stage'], ())):
                reason = 'success_structure_evidence_missing'
    return {**expected, 'status': state if row is not None else 'pending_record',
            'terminal': reason is None, 'unresolved_reason': reason,
            'raw_result_sha256': sources.evidence[str(Path(expected['path']))]}


def supplementary(sources):
    rows = []
    paths = [('readout-train', RUN / 'corpora/readout-train/inputs.json', 120),
             ('vctk', RUN / 'vctk-audio/inputs.json', 126),
             ('human', RUN / 'human-similarity/inputs.json', 105)]
    for stage, path, count in paths:
        specs = sources.get(path)
        if specs is None:
            rows.append({'stage': stage, 'path': str(path), 'status': 'pending_manifest',
                         'terminal': False, 'unresolved_reason': 'planned_manifest_absent'})
            continue
        if not isinstance(specs, list) or len(specs) != count or len({s['id'] for s in specs}) != count:
            raise ValueError(f'補助群manifestの予定件数/IDが不一致: {stage}')
        for spec in specs:
            if stage == 'readout-train':
                target = RUN / 'feature-assessment/targets/train' / f'{spec["id"]}.json'
                rows.append(inspect({'case': spec['id'], 'identity_key': 'id',
                                     'stage': 'train-target', 'path': str(target)}, sources))
            for method in METHODS:
                if stage == 'readout-train':
                    target = RUN / 'readout-train/native' / method / spec['id'] / 'features.json'
                    targets = [('train-features', target)]
                elif stage == 'vctk':
                    targets = [('vctk-quality', RUN / 'vctk-audio/quality' / spec['id'] / f'{method}.json'),
                               ('vctk-native', RUN / 'vctk-audio/native' / method / spec['id'] / 'unedited.json')]
                else:
                    targets = [('human-features', RUN / 'human-similarity/features' / method / spec['id'] / 'features.json')]
                for name, target in targets:
                    rows.append(inspect({'case': spec['id'], 'method': method,
                                         'stage': name, 'path': str(target)}, sources))
    for name in ('human', 'abx', 'readout'):
        path = RUN / f'feature-assessment/{name}-rankings/results.json'
        data = sources.get(path)
        terminal = bool(data and special_terminal(data))
        reason = None if terminal else 'special_estimator_not_terminal'
        if terminal:
            reason = unresolved_nested(data)
            terminal = reason is None
        rows.append({'stage': name + '-rankings', 'path': str(path),
                     'status': (data or {}).get('status', 'pending_record'),
                     'terminal': terminal, 'unresolved_reason': reason})
    return rows


def inventory(specs, sources, groups):
    expected = list(expected_main(specs))
    paths = [row['path'] for row in expected]
    if len(paths) != len(set(paths)):
        raise ValueError('最終予定集合に重複recordがあります')
    rows = [inspect(row, sources) for row in expected]
    rows.extend(supplementary(sources))
    for filename in ('control-metric-groups.json', 'latent-metric-groups.json'):
        path = RUN / filename
        exists = sources.get(path) is not None
        rows.append({'stage': 'metric-groups', 'path': str(path), 'status': 'present' if exists else 'pending_record',
                     'terminal': exists, 'unresolved_reason': None if exists else 'planned_group_file_absent'})
    for group in groups:
        invalid = any(state['status_counts'].get(status, 0)
                      for state in group['method_states'].values()
                      for status in ('missing_metric_evidence', 'failed_nonfinite_value', 'failed_timing_phase_evidence'))
        terminal = group['terminal'] and not invalid
        rows.append({'stage': 'ranking-group', 'group': group['id'],
            'terminal': terminal, 'status': 'terminal' if terminal else 'pending_group',
            'unresolved_reason': 'group_evidence_invalid' if invalid else None if terminal else 'planned_group_cells_not_terminal'})
    unresolved = [row for row in rows if not row['terminal']]
    return {'terminal': not unresolved, 'planned_records': len(rows), 'unresolved_records': len(unresolved),
        'stage_counts': dict(Counter(row['stage'] for row in rows)),
        'status_counts': dict(Counter(row['status'] for row in rows)), 'rows': rows,
        'meaning': '予定集合の終端確認。失敗・適用外も終端であり、終端は全成功・測定品質合格を意味しない。'}
