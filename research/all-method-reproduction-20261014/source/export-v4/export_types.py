"""閉じた型付きallowlist。未知欄を削除して続行せず、公開前に停止する。"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

METHODS = ('hnm', 'world_harvest', 'facodec', 'hifiglot', 'golf', 'sifigan', 'llsm2', 'magphase')
MAX_BYTES = 10 * 1024 * 1024
# 出力のみの小範囲検査。秘密を推定して置換するredactorではない。
# 絶対rootは経路の境界だけで照合し、公開相対名の内部segmentと区別する。
PRIVATE = re.compile(
    r'(?<![A-Za-z0-9_.-])/(?:workspace|home|Users|tmp|private|mnt|root|var|opt|etc)/|[A-Za-z]:\\\\|'
    r'(?:file|sediment|library)://|(?:library_file_|file-service:|file_[A-Za-z0-9]{12})|'
    r'Traceback \(most recent call last\)|(?i:traceback|source_records)|'
    r'(?i:Bearer\s+[A-Za-z0-9._-]+|-----BEGIN .*PRIVATE KEY-----)|'
    r'(?i:[?&](?:x-amz-signature|x-goog-signature|sig|access_token|token|api_key)=)|'
    r'(?i:(?:password|authorization|api_key|access_token)\s*[=:]\s*[^\s,}]+)')
ID = re.compile(r'[A-Za-z0-9_.:/+\-]+\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
DROP = object()


def fail(where, message):
    raise ValueError(f'{where}: {message}')


def scan(text, where):
    # JSON escape、HTML entity、URL encodingの明白な経路も検査する。
    from urllib.parse import unquote
    candidate = unquote(html.unescape(text)).replace('\\/', '/')
    if PRIVATE.search(candidate):
        fail(where, '公開候補に私有locator・traceback・credentialらしい文字列')


def string(value, where):
    if type(value) is not str:
        fail(where, '文字列が必要')
    scan(value, where)
    return value


def identifier(value, where):
    string(value, where)
    if not ID.fullmatch(value) or len(value) > 240:
        fail(where, '既知形式の論理IDが必要')
    return value


def number(value, where):
    if type(value) not in (int, float) or not math.isfinite(value):
        fail(where, '有限数が必要。nullと0を代替しない')
    return value


def integer(value, where):
    if type(value) is not int or value < 0:
        fail(where, '非負整数が必要')
    return value


def boolean(value, where):
    if type(value) is not bool:
        fail(where, 'boolが必要')
    return value


def sha(value, where):
    if type(value) is not str or not SHA.fullmatch(value):
        fail(where, '保存済みSHA-256が必要')
    return value


def nullable(check):
    return lambda value, where: None if value is None else check(value, where)


def sequence(check):
    def copy(value, where):
        if type(value) is not list:
            fail(where, '配列が必要')
        return [check(item, f'{where}[{i}]') for i, item in enumerate(value)]
    return copy


def interval(value, where):
    if value is None:
        return None
    if type(value) is not list or len(value) != 2:
        fail(where, '区間は保存された2値またはnull')
    return [number(item, where) for item in value]


def enum(*allowed):
    def copy(value, where):
        if value not in allowed or type(value) not in (str, type(None)):
            fail(where, '未定義の列挙値')
        return value
    return copy


def mapping(check, allowed=None):
    """動的keyはIDのラベルだけ。valueは常に明示schema。"""
    def copy(value, where):
        if type(value) is not dict:
            fail(where, '辞書が必要')
        result = {}
        for key, item in value.items():
            identifier(key, where)
            if allowed is not None and key not in allowed:
                fail(where, '未知のmap key: ' + key)
            result[key] = check(item, where + '.' + key)
        return result
    return copy


def private(types):
    def omit(value, where):
        if type(value) not in types:
            fail(where, '私有欄の予想外型')
        return DROP
    return omit


def obj(fields, required=()):
    def copy(value, where):
        if type(value) is not dict:
            fail(where, 'objectが必要')
        unknown = set(value) - fields.keys()
        if unknown or set(required) - value.keys():
            fail(where, '未知欄/必須欄不足: ' + repr(sorted(unknown or set(required) - value.keys())))
        result = {}
        for key, check in fields.items():
            if key in value:
                item = check(value[key], where + '.' + key)
                if item is not DROP:
                    result[key] = item
        return result
    return copy


def fields(names, check):
    return dict.fromkeys(names.split(), check)


N = nullable(number)
COUNT = nullable(integer)
S = nullable(string)
H = nullable(sha)
STRINGS = sequence(string)
IDS = sequence(identifier)
COUNTS = mapping(integer)
METHOD_NUMBERS = mapping(N, (*METHODS, 'original', 'identity'))
PATH = private((str, type(None)))
PRIVATE_OBJECT = private((dict, type(None)))
PRIVATE_LIST = private((list, type(None)))
SAFE_REASONS = frozenset((
    'no_common_pairs', 'no_common_triplets', 'no_valid_values',
    'no positive voiced YIN estimates', 'planned_record_absent', 'planned_manifest_absent',
    'planned_group_file_absent', 'special_estimator_not_terminal', 'group_evidence_invalid',
    'planned_group_cells_not_terminal', '指標値が有限な数値ではありません',
    '成功状態ですが対応する数値の証跡がありません', '物理量を定義したnative pitch/gain操作がありません',
    '端点差が宣言許容幅内で方向が未定義のため、反転数を0へしない。',
    'missing_token_features', 'distance_failed', 'no_native_frame_in_token',
    '生成は成功。native/派生peak>1またはPCM16丸め範囲外。clip・音量補正せず品質値null。',
))


def reason(value, where):
    if value is not None and type(value) is not str:
        fail(where, '理由は文字列またはnull')
    # 生理由は既知の短い科学的理由だけ。未レビュー本文は公開しない。
    return value if value is None or value in SAFE_REASONS else DROP


def with_reasons(schema, reviewed):
    def copy(value, where):
        result = schema(value, where)
        for key in ('reason', 'error', 'exception', 'unresolved_reason'):
            raw = value.get(key)
            if raw and (key not in result):
                result[key + '_private_available'] = True
                digest = hashlib.sha256(raw.encode()).hexdigest()
                explanation = reviewed.get(digest)
                if explanation:
                    result[key + '_reviewed_explanation'] = explanation
                else:
                    result[key + '_public_note'] = '理由本文は私有証跡に保存。公開要約は未レビュー。'
        return result
    return copy


def known_reason(value, where):
    result = reason(value, where)
    if result is DROP:
        fail(where, '表示必須の欠測理由が既知allowlistにない。個別reviewが必要')
    return result


def loads(content):
    def constant(value):
        fail('JSON', '非有限値 ' + value)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail('JSON', '重複key')
            result[key] = value
        return result
    return json.loads(content, parse_constant=constant, object_pairs_hook=pairs,
                      parse_float=lambda value: number(float(value), 'JSON number'))


def read(path):
    return loads(Path(path).read_bytes())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_entry(name, data):
    return {'name': name, 'bytes': len(data), 'sha256': digest(data),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}
