"""選択した既存方式だけを取得し、PR #24の成功環境を隔離して構築する。"""
import argparse
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib.request

from ..logging_utils import run_cli, run_process
from .catalog import METHODS, add_arguments, selected
from .common import HERE, check, digest, now, read, write


def checkout(spec, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        with tempfile.TemporaryDirectory(dir=path.parent, prefix=path.name + '-') as directory:
            temporary = Path(directory) / 'source'
            run_process(['git', 'init', str(temporary)])
            run_process(['git', 'remote', 'add', 'origin', spec['repository']], cwd=temporary)
            run_process(['git', 'fetch', '--depth', '1', 'origin', spec['revision']], cwd=temporary)
            run_process(['git', 'checkout', '--detach', 'FETCH_HEAD'], cwd=temporary)
            temporary.rename(path)
    actual = run_process(['git', 'rev-parse', 'HEAD'], cwd=path).stdout.strip()
    if actual != spec['revision']:
        raise ValueError(f'取得済みソースの版が違います: {path}: {actual}')


def download_weight(spec, cache):
    target = cache / spec['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        if 'hf_repo' in spec:
            from huggingface_hub import hf_hub_download
            file = hf_hub_download(spec['hf_repo'], spec['filename'], revision=spec['revision'])
            shutil.copyfile(file, target)
        elif 'gdrive_id' in spec:
            import gdown
            temporary = target.with_suffix('.download')
            if gdown.download(id=spec['gdrive_id'], output=str(temporary), quiet=False) is None:
                raise RuntimeError('SiFi-GANの重みを取得できません')
            check(temporary, spec['sha256'])
            temporary.replace(target)
        elif 'url' in spec:
            temporary = target.with_suffix('.download')
            with urllib.request.urlopen(spec['url'], timeout=120) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            check(temporary, spec['sha256'])
            temporary.replace(target)
        else:
            raise FileNotFoundError(f'固定チェックポイントがありません: {target}')
    check(target, spec['sha256'])
    if 'gdrive_id' in spec:
        with tarfile.open(target) as archive:
            archive.extractall(cache / 'models', filter='data')
    return target


def prepare_method(method, cache, lock, environment):
    from .native import build_llsm, build_magphase
    for source in METHODS[method].sources:
        checkout(lock['sources'][source], cache / 'src' / source)
    if method == 'golf':
        root = cache / 'src/golf'
        run_process(['git', '-c', 'url.https://github.com/.insteadOf=git@github.com:',
                     'submodule', 'update', '--init', '--recursive'], cwd=root)
        path = root / 'models/lru/recurrence.py'
        original = run_process(['git', 'show', 'HEAD:recurrence.py'], cwd=path.parent).stdout
        text = 'from typing import Any\n' + original.replace('torch.Any', 'Any')
        path.write_text(text)
        (cache / 'golf-submodules.txt').write_text(run_process(['git', 'submodule', 'status', '--recursive'], cwd=root).stdout)
    files = {}
    for spec in lock['weights'].get(method, []):
        path = download_weight(spec, cache)
        files[str(path.relative_to(cache))] = digest(path)
    if method == 'world_harvest':
        from ..build_world import build
        path = build()
        files[os.path.relpath(path, cache)] = digest(path)
    if method == 'llsm2':
        build_llsm(cache)
    if method == 'magphase':
        build_magphase(cache)
    roots = [cache / 'src' / name for name in METHODS[method].sources]
    roots += [cache / 'native'] if method == 'llsm2' else []
    roots += [cache / 'magphase-port'] if method == 'magphase' else []
    roots += [cache / 'models/model+stats'] if method == 'sifigan' else []
    extensions = {'.py', '.json', '.yaml', '.yml', '.so', '.c', '.h', '.joblib', '.pkl'}
    for root in roots:
        for path in sorted(root.rglob('*')):
            if path.is_file() and '.git' not in path.parts and (
                    path.suffix in extensions or root.name == 'magphase-port' and path.parent.name == 'bin'):
                files[str(path.relative_to(cache))] = digest(path)
    write(cache / 'prepared' / f'{method}.json', {
        'schema_version': 1, 'method': method, 'prepared_at': now(), 'environment': environment,
        'lock_sha256': digest(HERE / 'sources.lock.json'),
        'requirements_sha256': digest(HERE / 'requirements.txt'), 'files': files,
        'sources': {name: lock['sources'][name] for name in METHODS[method].sources},
        'note': '上流コードと重みをキャッシュへ取得。第三者コードを本リポジトリに複製しない。',
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    cache = args.runtime_cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    names = selected(args)
    if not args.inside:
        python = cache / 'env/bin/python'
        if not python.exists():
            run_process(['uv', 'venv', '--python', '3.10', str(cache / 'env')])
        run_process(['uv', 'pip', 'install', '--python', str(python), '--index-strategy', 'unsafe-best-match',
                     '--extra-index-url', 'https://download.pytorch.org/whl/cpu', '-r', str(HERE / 'requirements.txt')])
        command = [str(python), '-m', 'vocoderbench.references.prepare', *sys.argv[1:], '--inside']
        return subprocess.call(command)
    lock = read(HERE / 'sources.lock.json')
    freeze = run_process(['uv', 'pip', 'freeze', '--python', sys.executable]).stdout
    environment = {'python': sys.version, 'platform': platform.platform(), 'dependencies': freeze}
    failures = []
    for method in names:
        try:
            prepare_method(method, cache, lock, environment)
        except Exception:
            logging.exception('既存方式の準備に失敗しました: %s', method)
            failures.append({'method': method, 'error': traceback.format_exc()})
    write(cache / 'preparation.json', {'selected_methods': names, 'failures': failures, 'completed_at': now()})
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'reference-prepare'))
