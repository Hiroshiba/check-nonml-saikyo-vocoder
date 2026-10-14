"""測定の直接入力は変えず、exact JSON圧縮だけの等価性を別台帳へ残す。"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path

from all_metrics_common import RUN, now, read
from vocoderbench.quality_core import sha256, write_json


def verified_record(path, expected_sha256, output=None):
    """旧記録を上書きせず、現JSONか可逆保存された旧原本との完全一致を要求。"""
    path = Path(path)
    current_hash = sha256(path)
    current = read(path)
    evidence = {'path': str(path), 'expected_sha256': expected_sha256, 'current_sha256': current_hash,
                'verified_at_utc': now(), 'status': 'identity'}
    if current_hash != expected_sha256:
        relative = path.relative_to(RUN)
        ledger_path = RUN / 'storage-compaction-ledger' / relative
        ledger = read(ledger_path)
        archive = RUN / ledger['archive_path']
        if ledger['compact_sha256'] != current_hash or ledger['original_sha256'] != expected_sha256:
            raise ValueError('保存層台帳と新旧JSONのhashが一致しません')
        if sha256(archive) != ledger['archive_sha256']:
            raise ValueError('exact metadata gzipのhashが一致しません')
        raw = gzip.decompress(archive.read_bytes())
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError('展開した旧JSON原本のhashが一致しません')
        original = json.loads(raw)
        restored = copy.deepcopy(current)
        storage = restored.pop('storage_compaction')
        if storage['original_sha256'] != expected_sha256 or storage['archive_sha256'] != ledger['archive_sha256']:
            raise ValueError('compact内保存証跡が台帳と不一致です')
        locations = [(restored, original)]
        if isinstance(restored.get('feature_artifact'), dict):
            locations.append((restored['feature_artifact'], original['feature_artifact']))
        for node, prior in locations:
            external = node.pop('external_schema', None)
            if external is None:
                continue
            if external['original_sha256'] != expected_sha256 or external['archive_path'] != ledger['archive_path']:
                raise ValueError('外部schemaの原本参照が一致しません')
            if not set(external['omitted_keys']) <= {'arrays', 'structure'}:
                raise ValueError('許可されない科学fieldが保存層で省略されています')
            for key in external['omitted_keys']:
                node[key] = prior[key]
        if restored != original:
            raise ValueError('許可した保存層fieldだけ戻したJSONが旧原本と完全一致しません')
        evidence.update(status='lossless_storage_equivalent', archive=str(archive),
            archive_sha256=ledger['archive_sha256'], decompressed_sha256=expected_sha256,
            compaction_ledger=str(ledger_path), compaction_ledger_sha256=sha256(ledger_path),
            restored_json_exactly_equal=True)
    if 'audio' in current:
        audio = current['audio']
        if sha256(audio['path']) != audio['file_sha256']:
            raise ValueError('実際に評価したnative波形のhashが変わりました')
        evidence['direct_waveform_sha256'] = audio['file_sha256']
    for key in ('feature_artifact', 'native_representation'):
        artifact = current.get(key)
        if not artifact or not artifact.get('path') or not artifact.get('sha256'):
            continue
        payload = Path(artifact['path'])
        if payload.exists():
            if sha256(payload) != artifact['sha256']:
                raise ValueError('保存表現payloadのhashが変わりました')
            state = 'local_file_sha256_verified'
        else:
            state = 'not_local_not_a_direct_input_to_this_waveform_metric'
        evidence[key] = {'sha256': artifact['sha256'], 'verification': state}
    if output and evidence['status'] != 'identity':
        identifier = hashlib.sha256((str(path) + expected_sha256 + current_hash).encode()).hexdigest()
        write_json(Path(output) / f'{identifier}.json', evidence)
    return evidence
