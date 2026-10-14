"""正式manifestから全予定rowを作る。raw不在を0や実測済みへ変換しない。"""
from __future__ import annotations

from pathlib import Path

from all_metrics_common import METHODS, RUN, read
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
    """公開許可は元datasetの2 IDから読む。生成側の自己申告flagだけに依存しない。"""
    from all_metrics_common import ROOT
    from urllib.parse import urlparse
    dataset_path = ROOT / 'data/clean_speech_v1.json'
    dataset = read(dataset_path)
    if manifest.get('dataset_sha256') != sha256(dataset_path):
        raise ValueError('音声例の元dataset hashが不一致')
    allowed = set(dataset['public_audio_example_ids'])
    if len(allowed) != 2:
        raise ValueError('既存公開許諾は固定2録音です')
    samples, identities = [], set()
    for source in manifest['samples']:
        key = source['case'], source['method']
        src = source['src']
        parsed = urlparse(src)
        rate, count = source['sample_rate'], source['n_samples']
        if (key in identities or source['case'] not in allowed or source['method'] not in ('original', *METHODS)
                or source['start_sample'] != 0 or not isinstance(rate, int) or rate <= 0
                or not isinstance(count, int) or not 0 < count <= 2 * rate
                or parsed.scheme or parsed.netloc or Path(src).is_absolute() or '..' in Path(src).parts):
            raise ValueError('公開音声は許可された2録音の先頭最大2秒に限定します')
        target = Path(output) / src
        if sha256(target) != source['wav_sha256']:
            raise ValueError('公開する短い音声ファイルのhash不一致')
        identities.add(key)
        samples.append({**source, 'seconds': count / rate, 'start_seconds': 0,
                        'existing_public_excerpt': True})
    return samples


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
    scope = ('全8各worker1・CPU上限2の独立native工程。単回正式入力、初回を除外しない。'
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
