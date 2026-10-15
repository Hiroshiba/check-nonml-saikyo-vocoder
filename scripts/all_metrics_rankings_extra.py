"""独立補助群と専用統計を取り込む。異なる観測単位の分母を合算しない。"""
from __future__ import annotations

from collections import Counter

from all_metrics_common import METHODS, RUN
from all_metrics_rankings_core import competition_ranks, finite, special_terminal, state_counts
from all_metrics_rankings_inputs import definition, value_row

SPECIAL = [
    ('human-rankings', 13, 'rating_spearman', '既存の声同一性評定・Spearman相関', 'correlation', 'higher'),
    ('human-rankings', 13, 'rated_neighbor_top1', '評定済み候補内・最近傍一致率', 'fraction', 'higher'),
    *[('abx-rankings', 14, f'{condition}/{estimand}', f'音素ABX・{label}・{text}', 'error_fraction', 'lower')
      for condition, label in [('within_speaker', '同話者'), ('across_speaker', '異話者')]
      for estimand, text in [('flat_stratum', '層等重み'), ('x_speaker_macro', 'X話者等重み'),
                             ('nested_phone_context', '音素対・文脈入れ子補助')]],
    *[('readout-rankings', 15, key, f'線形読み出し・{label}絶対誤差', unit, 'lower')
      for key, label, unit in [('log_f0', '推定対数F0', 'ln(Hz)'), ('rms_dbfs', 'RMS', 'dBFS'),
                               ('spectral_slope', 'スペクトル傾斜', 'dB/octave')]],
]


def asr_groups(specs, sources):
    groups = [definition('4.incremental_' + key, '増分' + key.upper(), 4, 'error rate delta', 'lower', specs,
        '全文正解55録音32話者、原音CER≤0.20。残65は正解不足の適用外。出力は16kHz派生全長。',
        expected_eligible_recordings=55, expected_eligible_speakers=32)
        for key in ('cer', 'wer')]
    for spec in specs:
        for method in METHODS:
            row = sources.row(RUN / 'asr/measurements' / f'{spec["id"]}__{method}.json', spec, method,
                              contract=(RUN / 'asr/configuration.json', 'configuration_sha256'))
            measured = row.get('measurement', {})
            for key, group in zip(('cer', 'wer'), groups):
                score = measured.get('scores', {}).get(key, {})
                state = row['status']
                if state in ('measured', 'partial'):
                    state = score.get('status', 'missing_metric_evidence')
                    if measured.get('reference_usable') is not True:
                        state = 'reference_cer_gate_exceeded'
                value = score.get('delta') if state in ('measured', 'ok') else None
                group['rows'].append(value_row(row, value, state,
                    denominator={field: score.get(field) for field in ('truth_tokens', 'reference_errors', 'output_errors')},
                    reference_rate=score.get('reference_rate'), output_rate=score.get('output_rate')))
    return groups


def vctk_groups(sources):
    specs = sources.get(RUN / 'vctk-audio/inputs.json')
    if specs is None:
        return []
    groups = []
    for recommended in (False, True):
        selected = [spec for spec in specs if not recommended or spec['samples'] / spec['sample_rate'] >= 8]
        group = definition('3.visqol' + ('.recommended8s' if recommended else ''),
            'ViSQOL Audio・' + ('原音/共通区間8秒以上の補助層' if recommended else 'VCTK126独立群'),
            3, 'MOS-LQO', 'higher', selected,
            'VCTK7話者126録音の真の48kHz原音。全8同一の48kHz共通先頭区間。主120群とは独立。',
            note='GOLF既知heldout7話者。HiFi-GlotのVCTK学習重複可能性。低帯域模型のupsampleを真の48kHz対応と呼ばない。')
        for spec in selected:
            for method in METHODS:
                row = sources.row(RUN / 'vctk-audio/quality' / spec['id'] / f'{method}.json', spec, method,
                                  contract=(RUN / 'vctk-audio/quality-contract.json', 'contract_sha256'))
                state, value = row['status'], row.get('value')
                if recommended and state == 'measured':
                    seconds = row.get('common_seconds')
                    if not finite(seconds):
                        state, value = 'missing_metric_evidence', None
                    elif seconds < 8:
                        state, value = 'not_applicable', None
                group['rows'].append(value_row(row, value, state,
                    common_seconds=row.get('common_seconds'), coverage=row.get('coverages')))
        groups.append(group)
    return groups


def method_state(data, method, cell, folder, sources, condition, estimand):
    calibration = data.get('calibration_cohort', {})
    calibration_failures = calibration.get('excluded_method_status_counts', {}).get(method)
    auxiliary = data.get('auxiliary_successful_methods', {})
    auxiliary_cell = auxiliary.get('estimands', {}).get(estimand, {}).get('methods', {}).get(method, {})
    if folder == 'human-rankings':
        states = (data.get('cohort', {}).get('extraction_states', {}).get(method)
                  or auxiliary.get('cohort', {}).get('extraction_states', {}).get(method, {}))
        unit = 'input_recording'
    elif folder == 'abx-rankings':
        raw_source = data.get('raw_sources', {}).get(method, {})
        raw = sources.get(raw_source['path']) if raw_source.get('path') else None
        if raw:
            if sources.evidence[raw_source['path']] != raw_source['sha256']:
                raise ValueError('ABX条件別状態の元raw hashが不一致')
            states = dict(Counter(row['status'] for row in raw['triplets'] if row['condition'] == condition))
            unit = condition + '_triplet'
        else:
            states, unit = {}, condition + '_estimand'
    else:
        states, unit = {}, 'estimand'
    if not states:
        states = {auxiliary_cell.get('status', cell['status']): 1}
    rows = [{'status': key, 'value': None} for key, count in states.items() for _ in range(count)]
    summary = state_counts(rows)
    summary.update(observation_unit=unit, source_status_counts=states,
                   finite_values=int(finite(cell.get('value')) or finite(auxiliary_cell.get('value'))),
                   direct_measured=int(finite(cell.get('value')) or finite(auxiliary_cell.get('value'))),
                   calibration_failure_counts=calibration_failures,
                   calibration_required_recordings=calibration.get('required_train_recordings'))
    return summary


def specialized_auxiliary(data, estimand, condition):
    auxiliary = data.get('auxiliary_successful_methods')
    if not auxiliary:
        return None
    result = auxiliary.get('estimands', {}).get(estimand)
    if result is None:
        return None
    methods = auxiliary['method_set']
    if len(methods) != len(set(methods)) or set(methods) - set(METHODS):
        raise ValueError('専用補助群の固定方式集合が不正')
    if set(result['methods']) != set(methods):
        raise ValueError('専用補助群の方式集合と指標セルが不一致')
    if any(cell.get('rank') is not None for cell in result['methods'].values()):
        raise ValueError('固定train校正成功群の専用補助は無順位です')
    cohort = result.get('cohort') or auxiliary.get('cohorts', {}).get(condition) or auxiliary.get('cohort') or {}
    return {'label': '固定train校正が成功した方式の専用補助・無順位',
        'methods': result['methods'], 'comparable_methods': methods, 'cohort': cohort,
        'ranking': False, 'selection': '全120train校正の成功状態だけで方式集合を固定。指標値・共通数で再選別しない。',
        'calibration_cohort': data.get('calibration_cohort'),
        'excluded_methods': auxiliary.get('excluded_methods'),
        'exclusion_counts_by_method': auxiliary.get('exclusion_counts_by_method'),
        'excluded_triplets': auxiliary.get('excluded_triplets'),
        'selection_sha256': auxiliary.get('selection_sha256')}


def readout_train_evidence(data, path, sources):
    """表示用の欠測理由を、結果が参照する固定契約からそのまま引き継ぐ。"""
    if not data.get('contract_sha256'):
        return None
    contract_path = path.parent / 'contract.json'
    contract = sources.get(contract_path)
    if contract is None or sources.evidence[str(contract_path)] != data['contract_sha256']:
        raise ValueError('読み出し学習対象の表示用契約hashが不一致')
    return {'source_result': str(contract_path), 'source_sha256': data['contract_sha256'],
            'records': contract['train_targets']}


def special_groups(sources):
    output = []
    for folder, family, estimand, label, unit, direction in SPECIAL:
        path = RUN / 'feature-assessment' / folder / 'results.json'
        data = sources.get(path)
        status_data = sources.get(path.parent / 'status.json') if data is None else None
        data = data or status_data or {'status': 'pending_record'}
        result = data.get('estimands', {}).get(estimand)
        condition = estimand.split('/')[0]
        cohort = ((result or {}).get('cohort') or data.get('cohorts', {}).get(condition)
                  or data.get('cohort') or {})
        cells = {}
        for method in METHODS:
            cell = dict((result or {}).get('methods', {}).get(method) or {})
            if not cell:
                cell = {'value': None, 'ci95': None, 'rank': None,
                        'status': data['status'], 'reason': data.get('reason'),
                        'hnm_difference': {'value': None, 'ci95': None}}
            if cell.get('value') is not None and not finite(cell['value']):
                raise ValueError('専用集約に非有限値')
            cells[method] = cell
        values = {method: cell.get('value') for method, cell in cells.items()}
        expected_ranks = competition_ranks(values, direction)
        if any(cell.get('rank') != expected_ranks[method] for method, cell in cells.items()):
            raise ValueError('専用集約の同点順位規約が不一致')
        output.append({'id': f'{family}.{estimand}', 'family': family, 'label': label,
            'unit': unit, 'direction': direction, 'rankable': True, 'methods': list(METHODS),
            'rows': [], 'observation_unit': 'preaggregated_special_estimand',
            'scope': (result or {}).get('definition', label),
            'source_result': str(path), 'source_sha256': sources.evidence[str(path)],
            'terminal': special_terminal(data),
            'primary': {'methods': cells, 'cohort': cohort, 'comparable_methods': list(METHODS),
                        'label': '全8共通群・専用集計', 'all_eight_methods': True},
            'conditional': None, 'conditional_scope': '専用推定対象は元の全8共通集計を維持。方式選別しない。',
            'specialized_auxiliary': specialized_auxiliary(data, estimand, condition),
            'method_states': {method: method_state(data, method, cell, folder, sources, condition, estimand)
                              for method, cell in cells.items()},
            'uncertainty': data.get('uncertainty', data.get('limits')),
            'limits': data.get('limits'),
            'definitions': data.get('definitions'),
            'train_target_support': data.get('train_target_support'),
            'train_target_evidence': (readout_train_evidence(data, path, sources)
                                      if folder == 'readout-rankings' else None),
            'bootstrap': (result or {}).get('bootstrap', data.get('bootstrap')),
            'extraction_exclusions': data.get('extraction_exclusions'),
            'train_failures_by_method': data.get('train_failures_by_method'),
            'calibration_cohort': data.get('calibration_cohort'),
            'source_status': data['status']})
    return output
