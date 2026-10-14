"""正式manifestから全予定rowを作る。raw不在を0や実測済みへ変換しない。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, read
from all_metrics_rankings_core import finite
from vocoderbench.quality_core import sha256


class Sources:
    def __init__(self):
        self.cache = {}
        self.evidence = {}

    def get(self, path):
        path = Path(path)
        if path not in self.cache:
            self.cache[path] = read(path) if path.exists() else None
            self.evidence[str(path)] = sha256(path) if path.exists() else None
        return self.cache[path]

    def row(self, path, spec, method, condition=None, contract=None):
        path = Path(path)
        row = self.get(path)
        expected = {'case': spec['id'], 'method': method}
        if condition is not None:
            expected['condition'] = condition
        if row is not None and any(row.get(key) != value for key, value in expected.items()):
            raise ValueError(f'順位入力rawの対象が不一致: {path}')
        if row is not None and row.get('speaker', spec['speaker']) != spec['speaker']:
            raise ValueError(f'順位入力の話者が不一致: {path}')
        if row is not None and contract is not None:
            contract_path, key = contract
            if self.get(contract_path) is None or row.get(key) != self.evidence[str(Path(contract_path))]:
                raise ValueError(f'順位入力の固定科学契約が不一致: {path}')
        return {**(row or {'status': 'pending_record', 'value': None}), **expected,
                'speaker': spec['speaker'], 'raw_result': str(path),
                'raw_result_sha256': self.evidence[str(path)]}


def public_audio(manifest, output):
    """実WAV・固定2 ID・公開許諾を照合。保留を数値測定の状態へ混ぜない。"""
    import base64
    import hashlib
    import io
    import numpy as np
    from scipy.io import wavfile
    from all_metrics_audio_policy import (CREDITS_NAME, CREDITS_TEMPLATE, PUBLIC_METHODS, TERMS_SHA256,
                                          WITHHELD, public_ids)
    from all_metrics_common import ROOT
    dataset_path = ROOT / 'data/clean_speech_v1.json'
    dataset = read(dataset_path)
    allowed = set(public_ids(dataset))
    if (manifest.get('schema_version') != 2 or manifest.get('dataset_sha256') != sha256(dataset_path)
            or manifest.get('public_case_ids') != dataset['public_audio_example_ids']
            or manifest.get('publication_terms_sha256') != TERMS_SHA256):
        raise ValueError('音声例の固定dataset・公開条件・schemaが不一致')
    credits = manifest['credits']
    if (credits['src'] != CREDITS_NAME or credits['sha256'] != sha256(Path(output) / CREDITS_NAME)
            or credits['template_sha256'] != sha256(CREDITS_TEMPLATE)):
        raise ValueError('音声帰属・原文noticeの公開HTML hashが不一致')
    samples, identities = [], set()
    for source in manifest['samples']:
        key = source['case'], source['method']
        uri = source['data_uri']
        prefix = 'data:audio/wav;base64,'
        rate, count = source['sample_rate'], source['n_samples']
        if (key in identities or source['case'] not in allowed or source['method'] not in PUBLIC_METHODS
                or source['start_sample'] != 0 or type(rate) is not int or rate <= 0
                or type(count) is not int or not 0 < count <= 2 * rate or not uri.startswith(prefix)):
            raise ValueError('公開音声は許諾確認済み方式・固定2録音・先頭最大2秒の埋込WAVに限定します')
        wav = base64.b64decode(uri[len(prefix):], validate=True)
        if hashlib.sha256(wav).hexdigest() != source['wav_sha256']:
            raise ValueError('公開する短い音声ファイルのhash不一致')
        actual_rate, wave = wavfile.read(io.BytesIO(wav))
        if (actual_rate != rate or wave.ndim != 1 or len(wave) != count or str(wave.dtype) != 'float32'
                or not np.isfinite(wave).all()):
            raise ValueError('実WAVの長さ・標本化周波数・有限なモノラルfloat32形式とmanifestが不一致')
        identities.add(key)
        samples.append({**source, 'seconds': count / rate, 'start_seconds': 0,
                        'existing_public_excerpt': True, 'publication_status': 'available'})
    for source in manifest['excluded']:
        key = source['case'], source['method']
        method, status = source['method'], source['status']
        if (key in identities or source['case'] not in allowed or method not in METHODS
                or source.get('data_uri') or source.get('src')):
            raise ValueError('公開保留の対象が不一致または音声が混在しています')
        if method in WITHHELD:
            if status != 'withheld_license':
                raise ValueError('GOLF/SiFiGANの音声は重み固有許諾未確認のため公開保留です')
            reason = WITHHELD[method]
        elif (method in PUBLIC_METHODS and status == 'withheld_audio_unavailable'
              and source.get('native_status') and source['native_status'] != 'measured'):
            reason = '公開できる未編集native音声が未到着または利用不能。測定状態は数値表を参照。'
        else:
            raise ValueError('音声公開保留の理由がありません')
        identities.add(key)
        samples.append({**source, 'reason': reason, 'publication_status': 'withheld'})
    expected = {(identifier, method) for identifier in allowed for method in ('original', *METHODS)}
    if identities != expected:
        raise ValueError('固定2録音×原音・全8方式の公開または保留理由を全て記録してください')
    return sorted(samples, key=lambda row: (dataset['public_audio_example_ids'].index(row['case']),
                                           ('original', *METHODS).index(row['method'])))


def definition(identifier, label, family, unit, direction, specs, scope, **extra):
    return {'id': identifier, 'label': label, 'family': family, 'unit': unit,
        'direction': direction, 'methods': list(METHODS), 'planned_methods': list(METHODS),
        'planned_case_ids': [row['id'] for row in specs], 'rows': [],
        'observation_unit': 'utterance', 'speaker_bootstrap_eligible': True,
        'admissible_status': ['measured', 'ok'], 'scope': scope, **extra}


def value_row(raw, value, status=None, **extra):
    state = status or raw['status']
    if state in ('measured', 'ok') and value is None:
        state = 'not_applicable'
    return {'case': raw['case'], 'speaker': raw['speaker'], 'method': raw['method'],
        'status': state, 'origin_status': raw['status'], 'value': value,
        'raw_result': raw.get('raw_result'), 'raw_result_sha256': raw.get('raw_result_sha256'),
        'reason': raw.get('reason', raw.get('error')), **extra}


def mos_groups(specs, sources):
    group = definition('1.native_mos', 'native全長UTMOSv2予測MOS', 1, 'predicted MOS', 'higher', specs,
                       '各方式の実標本化周波数・無編集全長。原音は方式順位外。')
    original = []
    for spec in specs:
        for method in ('original', *METHODS):
            path = RUN / 'mos/measurements' / f'{spec["id"]}__{method}__unedited.json'
            row = sources.row(path, spec, method, 'unedited',
                              (RUN / 'mos/configuration.json', 'configuration_sha256'))
            cell = value_row(row, row.get('value'), origin=row.get('origin'),
                             new_inference_seconds=row.get('new_inference_seconds'))
            (original if method == 'original' else group['rows']).append(cell)
    group['reference_only_rows'] = original
    return [group]


def quality_groups(specs, sources):
    definitions = [('scoreq', '2.scoreq', 'SCOREQ参照あり距離', 2, 'distance', 'lower'),
                   ('speaker_ecapa', '5.ecapa', 'ECAPA話者類似度', 5, 'cosine', 'higher'),
                   ('erb', 'existing.erb20', '20ms ERB帯域距離', 0, 'dB', 'lower')]
    groups = {name: definition(identifier, label, family, unit, direction, specs,
                              '全8が同時に成立した固定16kHz共通先頭区間')
              for name, identifier, label, family, unit, direction in definitions}
    signatures = {name: set() for name in groups}
    for batch in range(12):
        selected = specs[batch * 10:(batch + 1) * 10]
        manifest_path = RUN / f'quality-inputs/common-{batch:02d}.json'
        manifest = sources.get(manifest_path)
        history = sources.get(RUN / 'processes' / f'quality-common16-{batch:02d}.json') or []
        candidates = []
        for attempt in history:
            if not attempt.get('output'):
                continue
            path = Path(attempt['output']) / 'results.json'
            result = sources.get(path)
            if result is None or manifest is None:
                continue
            if result.get('input', {}).get('source_sha256') != sources.evidence[str(manifest_path)]:
                continue
            for name in groups:
                preparation = result.get('metrics', {}).get(name, {})
                if preparation.get('status') == 'ready' and preparation.get('configuration_sha256'):
                    signatures[name].add(preparation['configuration_sha256'])
            candidates.append((attempt, path, result))
        chosen = candidates[-1] if candidates else None
        indexed = {}
        if chosen:
            _, path, result = chosen
            for row in result['rows']:
                key = row['metric'], row['case'], row['method']
                if key in indexed:
                    raise ValueError('品質attempt内に指標×録音×方式の重複')
                indexed[key] = {**row, 'raw_result': str(path),
                                'raw_result_sha256': sources.evidence[str(path)]}
        for spec in selected:
            derivation = (sources.get(RUN / 'derived16' / manifest['snapshot'] / spec['id'] / 'derivation.json')
                          if manifest else None)
            for method in METHODS:
                for name, group in groups.items():
                    row = indexed.get((name, spec['id'], method))
                    if row is None:
                        state = (derivation['status'] if derivation and derivation['status'] != 'measured'
                                 else 'pending_measurement')
                        row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
                               'status': state, 'value': None, 'reason': (derivation or {}).get('reason')}
                    if row.get('speaker') != spec['speaker']:
                        raise ValueError('品質rowとmanifestの話者が不一致')
                    group['rows'].append(value_row(row, row.get('value')))
    for name, values in signatures.items():
        if len(values) > 1:
            raise ValueError(f'共通品質のbatch/attempt間で科学設定が不一致: {name}')
        groups[name]['configuration_sha256'] = sorted(values)
    return list(groups.values())


def imported_groups(specs, sources):
    groups = []
    for filename in ('control-metric-groups.json', 'latent-metric-groups.json'):
        data = sources.get(RUN / filename)
        if data is None:
            continue
        if filename.startswith('latent') and data.get('schema_version') != 2:
            raise ValueError('latent群は共有資産を定数に分離したschema2が必要です')
        for source in data['groups']:
            for row in [*source.get('rows', []), *source.get('method_constants', [])]:
                path, expected_hash = row.get('raw_result'), row.get('raw_result_sha256')
                if path and expected_hash:
                    sources.get(path)
                    if sources.evidence[str(Path(path))] != expected_hash:
                        raise ValueError(f'群の元rawが集計後に変更または不在: {path}')
            group = {**source, 'family': int(source['id'].split('.')[0]),
                     'planned_case_ids': [spec['id'] for spec in specs],
                     'group_source': str(RUN / filename),
                     'group_source_sha256': sources.evidence[str(RUN / filename)]}
            groups.append(group)
    return groups


def native_groups(specs, sources):
    scope = ('全8とも各ライブラリのスレッド設定2・worker1の独立native工程。単回正式入力、初回を除外しない。'
             '解析/未編集復号の秒数を固定原入力秒で割る。初期化・前処理・保存読込を別記。')
    groups = [definition('speed.' + key, label, 0, 'RTF', 'lower', specs, scope,
                        note='区間は録音・話者構成だけの不確実性。実行時間反復や共有host負荷の区間ではない。')
              for key, label in [('analysis', '解析速度'), ('synthesis', '未編集復号速度'), ('total', '解析＋復号速度')]]
    lengths = []
    for index, spec in enumerate(specs):
        seconds = spec['samples'] / spec['sample_rate']
        batch = index // 10
        for method in METHODS:
            row = sources.row(RUN / 'native' / method / spec['id'] / 'unedited.json', spec, method, 'unedited',
                              (RUN / 'synthesis-contracts' / f'{method}.json', 'contract_sha256'))
            histories = sources.get(RUN / 'processes' / f'synthesis-{method}-{batch:02d}.json') or []
            eligible = [attempt for attempt in histories if attempt.get('native_phase_active') is True
                        and attempt.get('finished_at_utc') and attempt.get('method') == method
                        and attempt.get('worker_started_at_utc', '~') <= row.get('started_at_utc', '')
                        and row.get('finished_at_utc', '~') <= attempt['finished_at_utc']]
            audio = row.get('audio', {})
            lengths.append({'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
                'status': row['status'], 'source_seconds': seconds, 'native_seconds': audio.get('seconds'),
                'native_sample_rate': audio.get('sample_rate'), 'native_samples': audio.get('samples'),
                'initialization_included': False,
                'excluded_seconds': {key: row.get(key) for key in ('input_preprocessing_seconds',
                    'representation_save_seconds', 'representation_load_seconds', 'output_storage_seconds')}})
            times = [row.get('analysis_seconds'), row.get('synthesis_seconds')]
            values = [*times, sum(times) if all(finite(value) for value in times) else None]
            for group, value in zip(groups, values):
                state = row['status']
                if state == 'measured' and not eligible:
                    state = 'failed_timing_phase_evidence'
                group['rows'].append(value_row(row, value / seconds if finite(value) else None, state,
                                              denominator={'original_input_seconds': seconds},
                                              timing_phase_attempts=[a.get('attempt') for a in eligible]))
    return groups, lengths


def runtime_supplement(specs, sources, speed):
    """固定70録音を元の速度rowから選ぶ。再計時・値補正・結果による選別はしない。"""
    plan_path = RUN / 'operations/runtime-storage-isolated-supplement-plan.json'
    policy_path = RUN / 'operations/native-storage-io-policy-20261014T0856.json'
    start_path = RUN / 'operations/native-batch05-start.json'
    review_path = RUN / 'operations/native-storage-io-overlap-review.json'
    review_md_path = review_path.with_suffix('.md')
    plan, policy, start, review = [sources.get(path) for path in (plan_path, policy_path, start_path, review_path)]
    if any(not isinstance(value, dict) for value in (plan, policy, start, review)):
        raise ValueError('速度補助群の固定計画・保存方針・開始記録・重複レビューが必要です')
    selected = specs[50:120]
    records = [{'case': spec['id'], 'speaker': spec['speaker'], 'batch': index // 10,
                'input_sha256': spec['sha256'], 'input_samples': spec['samples'],
                'input_sample_rate': spec['sample_rate']} for index, spec in enumerate(selected, 50)]
    speaker_counts = dict(Counter(spec['speaker'] for spec in selected))
    if (plan['methods'] != list(METHODS) or plan['planned_recordings'] != 70 or plan['planned_speakers'] != 24
            or len({spec['id'] for spec in selected}) != 70 or len(speaker_counts) != 24
            or plan['records'] != records or plan['speaker_recording_counts'] != speaker_counts
            or plan['raw_values_changed'] is not False or plan['additional_inference'] is not False
            or policy['applies_from_native_batch'] != 5
            or plan['source_policy_path'] != str(policy_path.relative_to(RUN))):
        raise ValueError('速度補助群は保存方針で固定したbatch005–011の70録音24話者に限定します')
    for batch in range(5, 12):
        path = RUN / f'input-batches/{batch:02d}.json'
        batch_specs = sources.get(path)
        if (batch_specs != specs[batch * 10:(batch + 1) * 10]
                or sources.evidence[str(path)] != plan['input_batches_sha256'][str(path.relative_to(ROOT))]):
            raise ValueError(f'速度補助群の固定batch manifestが不一致: {path}')
    if not (datetime.fromisoformat(policy['created_at_utc']) < datetime.fromisoformat(start['started_at_utc'])
            < datetime.fromisoformat(plan['created_at_utc'])):
        raise ValueError('保存方針記録→batch005開始→補助分析計画採用の時系列が不一致')
    sources.evidence[str(review_md_path)] = sha256(review_md_path)
    full_note = ('全120録音40話者は保存I/O条件が混在した単回の参考値。batch000–004には時刻重複候補と'
                 '開始不明の保存工程がある。工程全体の交差から個別の解析/復号への干渉時間や大きさは特定できず、'
                 '元の測定値を保持し、差し引き・補正しない。')
    supplement_note = ('保存処理をnative工程間へ移す方針は08:56に告知、方針JSON作成は08:57:03、'
                       'batch005開始は09:04:29、補助分析計画採用は09:07:50（全て2026-10-14 UTC）。'
                       '全70録音の合成前に分析計画を事前登録したものではない。指標値・順位で対象を選んでいない。'
                       '後半の固定70録音24話者は100録音未満で無作為部分集団でもなく、主120録音を置換しない。'
                       '保存処理分離の運用方針を示すもので、無負荷・方式間で同一の背景負荷を保証しない。')
    interval_note = ('95%区間は録音・話者構成の記述。反復計時の安定性、保存I/O干渉の補正、'
                     '他機械・他環境での速さを表さない。')
    ids = {spec['id'] for spec in selected}
    supplement = []
    expected_ids = ['speed.analysis', 'speed.synthesis', 'speed.total']
    if [group['id'] for group in speed] != expected_ids:
        raise ValueError('元の解析・復号・合計速度の3群が必要です')
    for group in speed:
        original_label = group['label']
        group.update(label=original_label + '（全120録音・保存I/O混在の参考値）',
                     comparison_role='full120_mixed_storage_io_single_run_reference',
                     note=full_note + interval_note)
        supplement.append({**group, 'id': 'speed.storage_policy70.' + group['id'].split('.')[-1],
            'label': original_label + '（保存処理分離方針下の固定70録音・補助）',
            'comparison_role': 'fixed70_storage_policy_supplement',
            'planned_case_ids': [spec['id'] for spec in selected],
            'rows': [row for row in group['rows'] if row['case'] in ids],
            'note': supplement_note + interval_note,
            'selection_plan': str(plan_path), 'selection_plan_sha256': sources.evidence[str(plan_path)]})
    context = {
        'full120_group_ids': expected_ids,
        'supplement_group_ids': [group['id'] for group in supplement],
        'supplement_batches': list(range(5, 12)), 'planned_recordings': 70, 'planned_speakers': 24,
        'speaker_recording_counts': speaker_counts, 'selection_basis': plan['selection_basis'],
        'operational_boundary_announced_utc_minute': '2026-10-14T08:56Z',
        'policy_record_created_at_utc': policy['created_at_utc'],
        'batch005_started_at_utc': start['started_at_utc'],
        'supplement_analysis_adopted_at_utc': plan['created_at_utc'],
        'plan_wording_corrected_at_utc': plan['wording_correction_at_utc'],
        'preregistered_before_all70_syntheses': False, 'selection_used_metric_values_or_ranks': False,
        'raw_values_changed': False, 'additional_inference': False,
        'storage_interference_duration_seconds': None, 'storage_interference_effect_on_timing': None,
        'background_load_equivalence_established': False,
        'review_scope': review['scope'], 'review_counts': review['counts'],
        'review_counts_unit': 'method_process_windows_not_recordings_or_encode_decode_exposure',
        'later_batch_isolation_certified_by_review': False,
        'interval_scope': interval_note, 'full120_note': full_note, 'supplement_note': supplement_note,
        'review_note': review['rtf_note_ja'], 'review_limitations': review['limitations'],
        'source_sha256': {str(path): sources.evidence[str(path)]
                          for path in (plan_path, policy_path, start_path, review_path, review_md_path)},
    }
    return supplement, context
