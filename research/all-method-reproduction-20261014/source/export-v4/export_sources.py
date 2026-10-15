"""公開IDと内容hashだけを公開する。私有経路は別directoryの逆引き表へ。"""
from export_types import H, digest, fail, loads, obj, sha, string, with_reasons


class Sources:
    def __init__(self, private_report, private_digest, reviewed):
        self.records = []
        self.lookup = {}
        self.by_path = {}
        self.reviewed = reviewed
        self.private_digest = private_digest
        for kind, mapping in [('raw_record', private_report['raw_source_inventory']),
                              ('analysis_source', private_report['source_sha256']),
                              ('timing_source', private_report['timing_interpretation']['source_sha256'])]:
            if type(mapping) is not dict:
                fail(kind, '出典一覧はobjectが必要')
            for path, value in sorted(mapping.items()):
                self.add(path, value, kind)
        self.original_paths = dict(self.by_path)

    def add(self, path, value, kind):
        if path is not None and type(path) is not str:
            fail(kind, '私有出典経路の型不一致')
        H(value, kind)
        if path in self.by_path and self.by_path[path] != value:
            fail(kind, '同じ出典経路のhashが不一致')
        if path:
            self.by_path[path] = value
        key = (path, value, kind)
        if key not in self.lookup:
            source_id = f'source-{len(self.records) + 1:07d}'
            self.lookup[key] = source_id
            self.records.append({'source_id': source_id, 'kind': kind, 'sha256': value,
                                 'private_path': path})
        return self.lookup[key]

    def bind(self, schema):
        copy = with_reasons(schema, self.reviewed)
        def project(value, where):
            result = copy(value, where)
            for path_key, hash_key, kind in (
                    ('raw_result', 'raw_result_sha256', 'measurement_record'),
                    ('source_result', 'source_sha256', 'group_source'),
                    ('group_source', 'group_source_sha256', 'group_definition'),
                    ('selection_plan', 'selection_plan_sha256', 'selection_plan'),
                    ('inputs', 'input_manifest_sha256', 'input_manifest'),
                    ('path', 'raw_result_sha256', 'gate_record')):
                path = value.get(path_key)
                if path is not None:
                    if path_key == 'path' and 'record' in value:
                        kind = 'initialization_record'
                    elif path_key == 'path' and 'sha256' in value:
                        kind = 'bootstrap_artifact'
                    content_hash = value.get(hash_key, value.get('sha256', self.by_path.get(path)))
                    result[path_key + '_source_id'] = self.add(path, content_hash, kind)
            return result
        return project

    def public(self):
        return {'private_results_sha256': self.private_digest,
                'sources': [{k: r[k] for k in ('source_id', 'kind', 'sha256')} for r in self.records],
                'hash_semantics': 'sha256=nullは元snapshotで未到着またはhash未保存。現在のファイルから補完しない。'}

    def private(self):
        return {'private_results_sha256': self.private_digest, 'sources': self.records}


def reviewed_reasons(path, expected):
    if path is None:
        return {}
    blob = path.read_bytes()
    if digest(blob) != expected:
        fail('reviewed reasons', '独立レビュー済みSHAが不一致')
    data = loads(blob)
    if type(data) is not dict:
        fail('reviewed reasons', 'reason本文SHA→公開説明objectが必要')
    check = obj({'text': string, 'review_reference': string}, ('text', 'review_reference'))
    return {sha(key, 'reason SHA'): check(value, 'reason explanation') for key, value in data.items()}
