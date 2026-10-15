"""専用観測単位の既保存scalarだけを明示入力から転記する。評定値は含めない。"""
from pathlib import Path

from export_binding import bind_special
from export_science_schema import TARGETS
from export_types import (METHODS, N, PATH, boolean, digest, enum, fail, fields,
                          identifier, integer, loads, mapping, obj, private, reason,
                          sequence, sha)

# 入力manifest自体は私有。owner SHAだけでなく最終snapshot由来の出典へ結合する。
ENTRY = obj({'kind': enum('vctk16', 'abx', 'readout', 'asv_distances'),
    'path': lambda x, p: x if type(x) is str else fail(p, 'path文字列が必要'),
    'anchor_results': lambda x, p: x if type(x) is str else fail(p, 'anchor経路文字列が必要'),
    'sha256': sha, 'method': enum(*METHODS), 'expected_records': integer},
    ('kind', 'path', 'sha256', 'expected_records'))
TRIPLET_FIELDS = {**fields('a b x condition status', identifier),
    'distance_ax': N, 'distance_bx': N, 'tie': boolean, 'error': N, 'reason': reason}
ASV_PAIR = obj({**fields('sample_a sample_b type a_speaker b_speaker', identifier),
    'distances': mapping(N, METHODS),
    # 明示的に元評定平均・評定者数を公開成果から除外。再算出もしない。
    **fields('raw_rating_count distinct_listener_count human_rating human_mean_all_trials', private((int, float))),
}, ('sample_a', 'sample_b', 'a_speaker', 'b_speaker', 'distances'))
READOUT = obj({'case': identifier, 'speaker': identifier,
    'truth': obj(fields('log_f0 rms_dbfs spectral_slope', N), TARGETS),
    'predictions': mapping(obj(fields('log_f0 rms_dbfs spectral_slope', N), TARGETS), METHODS)},
    ('case', 'speaker', 'truth', 'predictions'))


def extra_records(manifest_path, manifest_sha, sources, row_schema):
    if manifest_path is None:
        return [], [], ['専用scalar入力manifest未指定: VCTK128、ABX三つ組、読み出し予測、ASV派生距離は未添付。']
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes) != manifest_sha:
        fail('special sources', 'owner固定manifest SHA不一致')
    entries = sequence(ENTRY)(loads(manifest_bytes), 'special sources')
    records, receipts, kinds, seen = [], [], set(), set()
    for entry in entries:
        path = Path(entry['path'])
        raw = path.read_bytes()
        if digest(raw) != entry['sha256']:
            fail(entry['kind'], '保存source SHAが不一致')
        data = loads(raw)
        kind = entry['kind']
        identity = kind, entry.get('method')
        if identity in seen or ('method' in entry and kind != 'abx'):
            fail(kind, '専用入力の重複または不要なmethod指定')
        seen.add(identity)
        expected_counts = {'vctk16': 128, 'abx': 4960, 'readout': 120, 'asv_distances': 80}
        if entry['expected_records'] != expected_counts[kind]:
            fail(kind, '固定済み観測件数に不一致。別群は新schemaのreviewが必要')
        local = []
        if kind == 'vctk16':
            if type(data) is not dict or set(data) != {'all16', 'recommended_duration', 'generated_at_utc',
                                                     'quality_contract_sha256', 'results_sha256', 'source_sha256'}:
                fail(kind, '未知のrankings-private schema')
            # all16だけを転記。8秒層の所属は別に保持し重複値を捏造しない。
            layer = data['recommended_duration']['planned_case_ids']
            sequence(identifier)(layer, 'VCTK recommended IDs')
            for item in data['all16']['rows']:
                local.append({'kind': 'vctk_recording', 'row': row_schema(item, kind),
                              'recommended_duration_member': item['case'] in layer})
        elif kind == 'abx':
            if 'method' not in entry:
                fail(kind, 'method明示が必要')
            schema = obj({'triplets': sequence(sources.bind(obj(TRIPLET_FIELDS,
                ('a', 'b', 'x', 'condition', 'status', 'error')))),
                'distances': sequence(sources.bind(obj({'tokens': sequence(identifier), 'status': identifier,
                    'value': N, 'exception': PATH}, ('tokens', 'status', 'value')))),
                'token_exclusions': sequence(sources.bind(obj({'method': identifier, 'token': identifier,
                    'reason': reason}, ('method', 'token', 'reason'))))},
                ('triplets', 'distances', 'token_exclusions'))
            clean = schema(data, kind)
            for key, unit in [('triplets', 'abx_triplet'), ('distances', 'abx_token_pair'),
                              ('token_exclusions', 'abx_token_exclusion')]:
                local.extend({'kind': unit, 'method': entry['method'], 'row': item} for item in clean[key])
        elif kind == 'readout':
            clean = sequence(READOUT)(data, kind)
            if any(set(item['predictions']) != set(METHODS) for item in clean):
                fail(kind, '全8方式の保存予測が必要')
            local = [{'kind': 'readout_recording_predictions', 'row': item} for item in clean]
        else:
            clean = sequence(ASV_PAIR)(data, kind)
            local = [{'kind': 'asv_derived_pair_distances', 'row': item} for item in clean]
        # 件数検証は転記対象だけ。再測定・相関・誤差・順位の計算ではない。
        observed = len(data['triplets']) if kind == 'abx' else len(local)
        if observed != entry['expected_records']:
            fail(kind, 'owner固定の観測件数が不一致')
        binding_sources = bind_special(entry, path, data, sources)
        source_id = sources.add(str(path), entry['sha256'], kind + '_scalars')
        start = len(records)
        records.extend({**item, 'source_id': source_id, 'raw_result_sha256': entry['sha256']} for item in local)
        receipts.append({'source_id': source_id, 'kind': kind, 'source_observation_count': observed,
            'exported_records': len(local), 'begin': start, 'end': len(records), 'sha256': entry['sha256'],
            'binding_source_ids': binding_sources})
        kinds.add(kind)
    missing = [kind + ': 専用scalar入力なし' for kind in ('vctk16', 'abx', 'readout', 'asv_distances') if kind not in kinds]
    missing.extend('ABX: ' + method + ' の4960三つ組source未指定'
                   for method in METHODS if ('abx', method) not in seen)
    missing.extend([
        '読み出しの録音別誤差はraw-recordings.jsonにもpredictions.npzにも保存されていないため、予測とtargetのみ転記。差・絶対誤差は再計算しない。',
        'ASVは派生距離だけ。元評定平均・評定者行・評定CSVは非公開。相関の完全再現には別途許諾された公式評定sourceが必要。',
        '専用scalarは録音・三つ組・token対・評定候補対を区別し、全18の独立録音数へ合算しない。',
    ])
    return records, receipts, missing
