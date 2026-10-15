"""許諾済み音声と別publisher成果だけを梱包。単体10MiBを実bytesで停止判定。"""
from __future__ import annotations

import gzip
from pathlib import Path

from export_render_constants import PUBLIC_IDS, PUBLIC_METHODS
from export_types import (MAX_BYTES, METHODS, digest, encoded, fail, file_entry,
                          loads, read, scan)

AUDIO_PINS = {
    'audio_samples.json': '50f8de84de080015094d557bc906a75be85c5bfec15f385fcd4c983c866bfd66',
    'audio_credits.html': 'ac98e746c0efc85ba170175003216fecc56c1482225921b5b3e55ea3327855b8',
}
PUBLISHER_SHA = 'cc37e923327e1c41faed36ebc365b74b196aa64e0d36a5ed587baf2bbb50a930'
CONTRACT_SHA = 'dd0a439858c3a6864346712cbd3dbed05a550fd4da8c10f49706f478d948db6f'


class Payload:
    def __init__(self):
        self.files = {}

    def add(self, name, data):
        if name in self.files or Path(name).is_absolute() or '..' in Path(name).parts:
            fail(name, '重複または不正な公開ファイル名')
        if len(data) > MAX_BYTES:
            fail(name, '単体10MiB超。数値や表を削らず、別レビューで保存値の分割ページ化が必要')
        plain = gzip.decompress(data) if name.endswith('.gz') else data
        scan(plain.decode('utf-8'), name)
        if name.endswith(('.json', '.json.gz')):
            # 展開後もJSONとして非有限値/重複keyを拒否する。
            loads(plain)
        self.files[name] = data

    def json(self, name, value):
        self.add(name, encoded(value))

    def entries(self):
        return [file_entry(name, self.files[name]) for name in sorted(self.files)]

    def write(self, output):
        for name, blob in self.files.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(blob)
            # 保存後の実bytesをmanifest候補と照合する。本番の保存契約。
            if path.read_bytes() != blob or path.stat().st_size > MAX_BYTES:
                fail(name, '保存した公開候補bytesが一致しない')


def raw_parts(payload, records):
    def pack(rows):
        return gzip.compress(encoded({'schema_version': 1, 'records': rows}), compresslevel=9, mtime=0)
    leaves = []
    def split(start, end):
        blob = pack(records[start:end])
        if len(blob) <= MAX_BYTES:
            leaves.append((start, end, blob))
        elif end - start <= 1:
            fail('raw values', '単一のscalar recordが圧縮後10MiB超')
        else:
            middle = (start + end) // 2
            split(start, middle)
            split(middle, end)
    split(0, len(records))
    parts = []
    for index, (start, end, blob) in enumerate(leaves, 1):
        name = 'raw-values.json.gz' if len(leaves) == 1 else f'raw-values.part-{index:04d}.json.gz'
        payload.add(name, blob)
        parts.append({**file_entry(name, blob), 'begin': start, 'end': end,
            'record_count': end - start, 'expanded_json_sha256': digest(gzip.decompress(blob))})
    return {'format': 'JSON records; gzip mtime=0; fixed order; deterministic midpoint splitting',
            'record_count': len(records), 'canonical_all_records_sha256': digest(encoded(records)), 'parts': parts}


def source_inventory(payload, inventory):
    """全出典・順序・metadataを保持し、実圧縮bytesだけで必要時に分割する。"""
    records = inventory['sources']
    complete = encoded(inventory)
    leaves = []
    def split(start, end):
        plain = complete if start == 0 and end == len(records) else encoded({**inventory, 'sources': records[start:end]})
        blob = gzip.compress(plain, compresslevel=9, mtime=0)
        if len(blob) <= MAX_BYTES:
            leaves.append((start, end, plain, blob))
        elif end - start <= 1:
            fail('source inventory', '単一の出典entryとmetadataが圧縮後10MiB超')
        else:
            middle = (start + end) // 2
            split(start, middle)
            split(middle, end)
    split(0, len(records))
    parts = []
    for index, (start, end, plain, blob) in enumerate(leaves, 1):
        name = 'source-inventory.json.gz' if len(leaves) == 1 else f'source-inventory.part-{index:04d}.json.gz'
        payload.add(name, blob)
        parts.append({**file_entry(name, blob), 'begin': start, 'end': end,
            'source_count': end - start, 'expanded_json_bytes': len(plain), 'expanded_json_sha256': digest(plain)})
    return {'format': 'JSON source inventory; gzip mtime=0; fixed order; deterministic midpoint splitting',
            'source_count': len(records), 'expanded_inventory_bytes': len(complete),
            'expanded_inventory_sha256': digest(complete), 'parts': parts,
            'reassembly': 'parts順にsourcesを連結し、各部で共通の残りのmetadataを保持すると元の出典一覧へ戻る。'}


def audio(payload, folder):
    for name, expected in AUDIO_PINS.items():
        blob = (folder / name).read_bytes()
        if digest(blob) != expected:
            fail(name, '既レビュー済み14clip成果SHAが不一致。再exportは禁止')
        payload.add(name, blob)
    manifest = read(folder / 'audio_samples.json')
    if len(manifest['samples']) != 14 or len(manifest['excluded']) != 4:
        fail('audio', '14公開・4保留を維持する必要')
    samples = []
    identities = set()
    for item in manifest['samples']:
        key = item['case'], item['method']
        if key in identities or item['case'] not in PUBLIC_IDS or item['method'] not in PUBLIC_METHODS:
            fail('audio', '既存2ID×許諾7種の範囲外')
        identities.add(key)
        # URIのbytesは既成manifestから変更しない。切出しや再encodeはしない。
        samples.append({**item, 'seconds': item['n_samples'] / item['sample_rate'],
                        'start_seconds': 0, 'existing_public_excerpt': True, 'publication_status': 'available'})
    for item in manifest['excluded']:
        if item['method'] not in ('golf', 'sifigan') or item['status'] != 'withheld_license':
            fail('audio', 'GOLF/SiFiの保留状態が不一致')
        samples.append({**item, 'publication_status': 'withheld'})
    return samples


def quantization(payload, folder, saved):
    if saved.get('status') != 'available':
        if folder is not None:
            fail('quantization', '元privateにリンク未収載。最終private snapshotへ正式接続してから梱包する')
        return ['量子化共通窓の別publisher成果がprivate最終snapshotで未添付。#17/#18の元NAは保持。']
    if folder is None:
        fail('quantization', 'availableの保存リンクには別publisher成果の入力が必要')
    manifest = read(folder / 'artifact-manifest.json')
    if (manifest.get('renderer_sha256') != PUBLISHER_SHA
            or manifest.get('contract_sha256') != CONTRACT_SHA
            or manifest.get('scientific_values_recomputed') is not False
            or manifest.get('whole_18_study_completion_claim') is not False
            or {x['name'] for x in manifest['files']} != {'index.html', 'results.json'}):
        fail('quantization', 'レビュー済みpublisher/allowlistの証跡不一致')
    expected_links = {'href': 'quantization-common-window/index.html',
                      'results_href': 'quantization-common-window/results.json'}
    if any(saved.get(k) != v for k, v in expected_links.items()):
        fail('quantization', '同一別HTML/JSONへの保存リンクが不一致')
    for item in manifest['files']:
        blob = (folder / item['name']).read_bytes()
        if digest(blob) != item['sha256'] or len(blob) != item['bytes']:
            fail('quantization', '保存bytes/SHAが不一致')
        key = 'html_sha256' if item['name'] == 'index.html' else 'results_sha256'
        if digest(blob) != saved[key]:
            fail('quantization', 'private最終snapshotの参照SHAが不一致')
        payload.add('quantization-common-window/' + item['name'], blob)
    data = read(folder / 'results.json')
    if (data.get('post_hoc') is not True or data.get('replaces_primary') is not False
            or data.get('counts_as_additional_independent_metric') is not False
            or data.get('contract_sha256') != CONTRACT_SHA or len(data['groups']) != 2):
        fail('quantization', '元primaryと独立補助の意味が不一致')
    for group in data['groups']:
        if (group['primary']['terminal'] is not True
                or group['primary']['planned_recordings_per_method'] != 120
                or group['primary']['comparable_methods'] != list(METHODS)):
            fail('quantization', '全120×8の保存終端証拠が不足')
    payload.add('quantization-common-window/artifact-manifest.json', (folder / 'artifact-manifest.json').read_bytes())
    return []
