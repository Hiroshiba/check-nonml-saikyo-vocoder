"""固定ファイルの照合と、途中失敗でも追跡できる保存形式。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def check(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f'固定ファイルのSHA-256が一致しません: {path}: {actual} != {expected}')


def implementation_hashes():
    paths = [*HERE.glob('*.py'), *(ROOT / 'vocoderbench').glob('*.py'), *(ROOT / 'vocoderbench/pml').glob('*.py'),
             HERE / 'sources.lock.json', HERE / 'requirements.txt',
             ROOT / 'vocoderbench/world.lock.json', ROOT / 'uv.lock', ROOT / 'BASELINE.json']
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}



def verify_prepared(cache, method):
    record = read(cache / 'prepared' / f'{method}.json')
    check(HERE / 'sources.lock.json', record['lock_sha256'])
    check(HERE / 'requirements.txt', record['requirements_sha256'])
    for relative, expected in record['files'].items():
        check(cache / relative, expected)
    return record
