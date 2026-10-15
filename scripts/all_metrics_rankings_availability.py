"""終端済み可用性別群の保存値だけを取り込む。推定・順位・区間は再計算しない。"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN
from all_metrics_rankings_core import pending, state_counts
from vocoderbench.quality_core import sha256

HUMAN_NOTES = [
    '取得可用性で事後追加した100録音80対27話者・B基準20録音20話者の別群。元105録音の未完を置換しません。',
    '原音の特徴距離と既存の同一人物らしさの評定との一致です。復号音のMOSや総合品質ではありません。',
    'Spearmanは録音対等重み。最近傍一致は評定済みA候補内でBごとに求め、B話者を等重みにします。',
    '全800抽出終端後に、学習校正成功かつ有効な予定対が1対以上ある方式を全て固定。共通数や一致値で再選別しません。',
    '条件付き規則は320特徴の抽出状態を確認した後、一致値の計算前に固定した事後規則です。事前登録とは呼びません。',
    'MagPhaseの既存resample後のPCM16入力範囲外は抽出処理の失敗です。特徴の品質劣位、0点、最下位とは解釈しません。',
    '全8主群の共通0と値・順位・区間のnullを保持し、成功方式条件付きの値だけを別表に示します。',
    '今回の両指標で、対応HNM差の95%区間は全方式で0を含みます。順位だけでHNMに対する優位性を確定しません。',
]


def required(sources, path, expected=None):
    value = sources.get(path)
    if value is None or expected is not None and sources.evidence[str(Path(path))] != expected:
        raise ValueError(f'別群の必須出典またはSHAが不一致: {path}')
    return value


def verify_files(sources, mapping):
    for name, expected in mapping.items():
        path = ROOT / name
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f'保存済み別群の固定source SHAが不一致: {name}')
        sources.evidence[str(path)] = actual


def null_if_empty(cohort, count):
    if count == 0:
        for cell in cohort['methods'].values():
            delta = cell.get('hnm_difference') or {}
            if any(v is not None for v in (cell.get('value'), cell.get('rank'), cell.get('ci95'),
                                           delta.get('value'), delta.get('ci95'))):
                raise ValueError('共通0の保存値・順位・区間・HNM差はnullでなければなりません')


def human_groups(sources):
    handoff = required(sources, RUN / 'operations/human-availability100-final-review-handoff.json',
        'c6161047db2c772d24e9755f9573f1af486cc33dc13a939ab217004a3f9ef73f')
    verify_files(sources, {item['path']: item['sha256'] for item in handoff['artifacts']})
    folder = RUN / 'human-availability100'
    inputs = required(sources, folder / 'inputs.json')
    selected = required(sources, folder / 'selection.json')
    input_contract = required(sources, folder / 'input-contract.json')
    if (len(inputs) != 100 or len({s['id'] for s in inputs}) != 100
            or len({s['speaker'] for s in inputs}) != 27 or len(selected['pairs']) != 80
            or input_contract['inputs_sha256'] != sources.evidence[str(folder / 'inputs.json')]
            or input_contract['selection_sha256'] != sources.evidence[str(folder / 'selection.json')]):
        raise ValueError('ASV可用性100の固定集合が不一致')
    completion = required(sources, folder / 'extraction-completion.json')
    membership = required(sources, folder / 'conditional-rankings/method-selection.json')
    freeze = required(sources, RUN / 'operations/human_available100_conditional/freeze.json',
                      membership['frozen_analysis_sha256'])
    if (freeze['selection_uses_agreement_metric_values'] is not False
            or freeze['agreement_values_computed_at_freeze'] is not False
            or membership['selection_uses_agreement_values'] is not False
            or membership['cohort_selection_sha256'] != input_contract['selection_sha256']
            or completion['planned_records'] != 800):
        raise ValueError('ASVの全予定終端または一致値によらない固定規則の証拠が不一致')
    verify_files(sources, freeze['source_sha256'])
    primary_raw = required(sources, folder / 'rankings/results.json')
    conditional_raw = required(sources, folder / 'conditional-rankings/results.json')
    primary = required(sources, folder / 'report/results.json')
    conditional = required(sources, folder / 'report/conditional/results.json')
    contracts, calibrations = [], []
    for name, raw, clean in [('rankings', primary_raw, primary),
                             ('conditional-rankings', conditional_raw, conditional)]:
        contract = required(sources, folder / name / 'contract.json', raw['contract_sha256'])
        contracts.append(contract)
        calibrations.append(required(sources, folder / name / 'calibration-cohort.json',
                                     contract['calibration_cohort_sha256']))
        if (raw.get('analysis_complete') is not True
                or clean['private_raw_result_sha256'] != sources.evidence[str(folder / name / 'results.json')]
                or clean['estimands'] != raw['estimands']
                or contract['inputs_sha256'] != input_contract['inputs_sha256']
                or contract['selection_sha256'] != input_contract['selection_sha256']):
            raise ValueError('ASVの表示用JSONと固定集約値・契約が不一致')
        for key in ('planned', 'common', 'extraction_states'):
            if clean['cohort'][key] != raw['cohort'][key]:
                raise ValueError('ASVの保存分母または抽出状態が不一致')
        verify_files(sources, contract['source_sha256'])
    if (primary_raw['methods'] != list(METHODS) or conditional_raw['methods'] != membership['methods']
            or contracts[1]['method_selection_sha256'] != sources.evidence[str(folder / 'conditional-rankings/method-selection.json')]
            or contracts[1]['pre_score_freeze_sha256'] != membership['frozen_analysis_sha256']
            or conditional_raw['all8_primary_sha256'] != sources.evidence[str(folder / 'rankings/results.json')]
            or conditional_raw['conditional_method_selection'] != membership):
        raise ValueError('ASVの全8主群・固定条件付き集合の連結が不一致')
    if calibrations[0] != calibrations[1] or calibrations[1]['selection_uses_metric_values'] is not False:
        raise ValueError('ASVの固定train校正集合が不一致')
    states, expected_members, valid_by_method = {}, [], {}
    for method in METHODS:
        proof = completion['terminal_feature_records'][method]
        indexed = {row['case']: row for row in proof}
        if len(proof) != 100 or set(indexed) != {s['id'] for s in inputs}:
            raise ValueError('ASVの終端証拠に予定録音の欠落・重複があります')
        records = []
        valid_samples = set()
        for spec in inputs:
            row = required(sources, folder / 'features' / method / spec['id'] / 'features.json',
                           indexed[spec['id']]['record_sha256'])
            if (row['case'] != spec['id'] or row['method'] != method or row['speaker'] != spec['speaker']
                    or row['status'] not in ('measured', 'failed') or row['status'] != indexed[spec['id']]['status']):
                raise ValueError('ASVの固定録音・方式・話者・終端状態が不一致')
            required(sources, folder / 'feature-contracts' / f'{method}.json', row['contract_sha256'])
            records.append({'status': row['status'], 'value': None})
            if row['status'] == 'measured':
                sample = spec['metadata']['official_rating_sample_id']
                valid_samples.add(sample)
                evidence = membership['feature_records'][method][sample]
                if (evidence['record_sha256'] != indexed[spec['id']]['record_sha256']
                        or evidence['mean_sha256'] != row['mean_sha256']):
                    raise ValueError('ASVの集合固定時と現在の特徴出典が不一致')
        counts = dict(Counter(row['status'] for row in records))
        if counts != completion['method_counts'][method] or counts != primary['cohort']['extraction_states'][method]:
            raise ValueError('ASVの全予定抽出件数が不一致')
        valid_pairs = sum(p['sample_a'] in valid_samples and p['sample_b'] in valid_samples for p in selected['pairs'])
        decision = membership['all_method_counts'][method]
        calibrated = method in calibrations[1]['methods']
        if decision['train_calibration_successful'] != calibrated:
            raise ValueError('ASVの選択に用いたtrain校正状態が不一致')
        eligible = calibrated and valid_pairs > 0
        valid_by_method[method] = valid_samples
        if (decision['planned_recordings'] != 100 or decision['planned_pairs'] != 80
                or decision['measured'] != counts.get('measured', 0) or decision['failed'] != counts.get('failed', 0)
                or decision['valid_pairs'] != valid_pairs or decision['selected'] != eligible
                or set(membership['feature_records'][method]) != valid_samples):
            raise ValueError('ASVの方式選択が全有効方式を固定する状態規則と一致しません')
        if eligible:
            expected_members.append(method)
        states[method] = state_counts(records) | {'finite_values': len(valid_samples),
            'direct_measured': len(valid_samples), 'observation_unit': 'input_feature_recording'}
    if (membership['methods'] != expected_members or contracts[0]['feature_records'] != membership['feature_records']
            or contracts[1]['feature_records'] != membership['feature_records']):
        raise ValueError('ASVの比較方式集合・特徴証拠が固定契約と不一致')
    for contract, data in zip(contracts, (primary, conditional)):
        common = [p for p in selected['pairs'] if contract['methods'] and all(
            p['sample_a'] in valid_by_method[m] and p['sample_b'] in valid_by_method[m] for m in contract['methods'])]
        if contract['common_pairs'] != [[p['sample_a'], p['sample_b']] for p in common]:
            raise ValueError('ASVの保存共通対と固定方式交差が不一致')
        common_counts = {'pairs': len(common),
            'recordings': len({p[k] for p in common for k in ('sample_a', 'sample_b')}),
            'speakers': len({p[k] for p in common for k in ('a_speaker', 'b_speaker')}),
            'b_anchors': len({p['sample_b'] for p in common}),
            'b_speakers': len({p['b_speaker'] for p in common})}
        if data['cohort']['common'] != common_counts:
            raise ValueError('ASVの保存共通分母が固定対と不一致')
    output = []
    for estimand, title, unit in [('rating_spearman', '声同一性評定とのSpearman相関', '相関係数'),
                                  ('rated_neighbor_top1', '評定済み候補内の最近傍一致', '割合')]:
        main = {'methods': deepcopy(primary['estimands'][estimand]['methods']),
                'cohort': {k: primary['cohort'][k] for k in ('planned', 'common')},
                'comparable_methods': list(METHODS), 'all_eight_methods': True}
        extra = {'methods': deepcopy(conditional['estimands'][estimand]['methods']),
                 'cohort': {k: conditional['cohort'][k] for k in ('planned', 'common')},
                 'comparable_methods': membership['methods'],
                 'excluded_methods': [m for m in METHODS if m not in membership['methods']],
                 'same_as_primary': membership['methods'] == list(METHODS),
                 'selection': HUMAN_NOTES[3] + HUMAN_NOTES[4]}
        null_if_empty(main, main['cohort']['common']['pairs'])
        null_if_empty(extra, extra['cohort']['common']['pairs'])
        output.append({'id': '13.availability100.' + estimand, 'family': 13,
            'label': '取得済み100録音の別群・' + title, 'unit': unit, 'direction': 'higher',
            'scope': primary['estimands'][estimand]['definition'], 'note': ' '.join(HUMAN_NOTES),
            'methods': list(METHODS), 'method_states': states, 'terminal': True,
            'primary': main, 'conditional': extra, 'supplementary': True, 'rows': [],
            'observation_unit': 'preaggregated_human_pairs', 'rankable': True,
            'planned_recordings_per_method': 100, 'planned_speakers_per_method': 27,
            'uncertainty': conditional['uncertainty'], 'limits': conditional.get('limits'),
            'bootstrap': {k: conditional['bootstrap'][k] for k in ('seed', 'replicates')},
            'group_terminal_evidence': {'all_planned_rows_terminal': True, 'planned_rows': 800,
                'status_only_selection_verified': True,
                'source_result_sha256': sources.evidence[str(folder / 'rankings/results.json')],
                'conditional_source_sha256': sources.evidence[str(folder / 'conditional-rankings/results.json')],
                'selection_sha256': sources.evidence[str(folder / 'conditional-rankings/method-selection.json')]}})
    return output


def public_cohort(cohort):
    if cohort is None:
        return None
    keys = ('label', 'comparable_methods', 'excluded_methods', 'selection', 'same_as_primary',
            'all_eight_methods', 'common_valid_recordings', 'common_valid_speakers',
            'valid_bootstrap_replicates', 'requested_bootstrap_replicates', 'interval_limitation')
    return {k: cohort[k] for k in keys if k in cohort} | {'methods': {
        m: {k: v for k, v in cell.items() if k != 'speaker_means'} for m, cell in cohort['methods'].items()}}


def vctk_available_groups(sources):
    from all_metrics_rankings_coverage import retain_group_conditional
    completion = required(sources, RUN / 'operations/vctk_available16/all16-completion.json',
        'c6474a470834de9ef417dfebdcba0fdd27e2e206ad1e2d20099db4f4edc1fcd3')
    if completion['terminal'] is not True or completion['planned_quality_rows'] != 128:
        raise ValueError('VCTK16の固定全128終端証拠が必要です')
    verify_files(sources, completion['immutable_evidence_sha256'])
    folder = RUN / 'vctk-availability16'
    summary = required(sources, folder / 'report/summary.json')
    private = required(sources, folder / 'rankings-private.json')
    raw = required(sources, folder / 'results.json', private['results_sha256'])
    contract = required(sources, folder / 'quality-contract.json', private['quality_contract_sha256'])
    inputs = required(sources, folder / 'inputs.json', contract['inputs_sha256'])
    required(sources, folder / 'input-contract.json', contract['input_contract_sha256'])
    selection = required(sources, RUN / 'operations/vctk_available16/selection-before-measurement.json',
                         'ce192ea183202f5714c8f25a6c87ed3cae5500439e4f992dbfcc61abe62da8ff')
    verify_files(sources, private['source_sha256'])
    cases = {s['id']: s for s in inputs}
    if (len(inputs) != 16 or len(cases) != 16 or len({s['speaker'] for s in inputs}) != 4
            or {s['id']: s['speaker'] for s in inputs} != {s['id']: s['speaker'] for s in selection['entries']}
            or contract['planned_methods'] != list(METHODS) or len(raw['rows']) != 128
            or raw['input_contract_sha256'] != contract['input_contract_sha256']
            or raw['quality_contract_sha256'] != private['quality_contract_sha256']
            or summary['formal126_status'] != 'incomplete_unmeasured' or summary['below100_recordings'] is not True):
        raise ValueError('VCTK16の固定集合・契約・正式126未完の区別が不一致')
    identities = [(r['case'], r['method']) for r in raw['rows']]
    if len(set(identities)) != 128 or set(identities) != {(c, m) for c in cases for m in METHODS}:
        raise ValueError('VCTK16の128予定状態が欠落または重複しています')
    for row in raw['rows']:
        if (pending(row['status']) or row['speaker'] != cases[row['case']]['speaker']
                or row != required(sources, folder / 'quality' / row['case'] / f'{row["method"]}.json')):
            raise ValueError('VCTK16の終端rawと品質出典が不一致')
    result = []
    for key, title in [('all16', '全16候補'), ('recommended_duration', '原音・共通区間8秒以上')]:
        group = deepcopy(private[key])
        expected_ids = {s['id'] for s in inputs if key == 'all16' or s['samples'] >= 8 * s['sample_rate']}
        if set(group['planned_case_ids']) != expected_ids:
            raise ValueError('VCTK16の保存済み層と固定入力の分母が不一致')
        for field in ('id', 'direction', 'terminal', 'method_states', 'planned_recordings_per_method',
                      'planned_speakers_per_method', 'bootstrap', 'aggregation'):
            if group[field] != summary[key][field]:
                raise ValueError('VCTK16の公開向け群定義が保存集約と不一致')
        for field in ('primary', 'conditional'):
            if public_cohort(group[field]) != summary[key][field]:
                raise ValueError('VCTK16の値・順位・区間・共通分母が保存集約と不一致')
        auxiliary = {m: {k: v for k, v in cell.items() if k != 'speaker_means'}
                     for m, cell in group['available_case_auxiliary'].items()}
        if auxiliary != summary[key]['available_case_auxiliary'] or any(c['rank'] is not None for c in auxiliary.values()):
            raise ValueError('VCTK16の全有効値補助が不一致または順位付きです')
        retain_group_conditional(group)
        null_if_empty(group['primary'], group['primary']['common_valid_recordings'])
        if group['conditional']:
            null_if_empty(group['conditional'], group['conditional']['common_valid_recordings'])
        result.append({**summary[key], 'id': '3.availability16.' + key, 'family': 3,
            'label': '取得済み16録音の別群・ViSQOL Audio・' + title, 'unit': 'MOS-LQO',
            'scope': '公式48kHz原音、4話者16録音の可用性による事後限定群。主120録音とは独立。',
            'note': ' '.join(summary['limitations']), 'methods': list(METHODS),
            'supplementary': True, 'rows': [], 'rankable': True,
            'group_terminal_evidence': group.get('group_terminal_evidence', {}) | {
                'all_planned_rows_terminal': True, 'planned_rows': 128,
                'source_result_sha256': private['results_sha256'],
                'summary_sha256': sources.evidence[str(folder / 'report/summary.json')]}})
    return result


def availability_groups(sources):
    return [*human_groups(sources), *vctk_available_groups(sources)]
