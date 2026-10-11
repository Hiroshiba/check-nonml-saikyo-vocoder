"""キャッシュを使って、手編集するソースファイルの行数を静的に確認する。"""
import hashlib
import json
from pathlib import Path
import sys
import logging

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import configure_logging, run_cli, run_process  # noqa: E402

configure_logging('source-size')


def main():
    cache_file = ROOT / '.cache/source-size.json'
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    updated, errors = {}, []
    names = run_process(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).stdout
    for name in sorted(set(names.split('\0')) - {''}):
        path = ROOT / name
        if not path.is_file() or path.suffix not in ('.py', '.c', '.h', '.cpp', '.hpp', '.ts', '.tsx', '.js', '.jsx', '.vue', '.css'):
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        previous = cache.get(name, {})
        lines = previous['lines'] if previous.get('sha256') == digest else len(raw.splitlines())
        updated[name] = {'sha256': digest, 'lines': lines}
        if lines > 1000:
            errors.append(f'{name}: {lines}行')
        elif lines > 400:
            logging.warning('ファイル分割を検討してください: %s (%d行)', name, lines)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(updated, ensure_ascii=False, indent=2)+'\n')
    if errors:
        raise ValueError('ソースファイルが1000行を超えています: '+', '.join(errors))
    logging.info('%dファイルの行数を確認しました', len(updated))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'source-size'))
