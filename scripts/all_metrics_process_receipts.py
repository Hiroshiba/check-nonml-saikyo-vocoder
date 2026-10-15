"""終了コードだけで再開を省略せず、実在する正式成果とsourceを照合する。"""
from __future__ import annotations

from pathlib import Path

from all_metrics_common import ROOT, RUN, read
from vocoderbench.quality_core import sha256


def command_key(command):
    return [value for value in command if value != '--retry-failed']


def source_receipt():
    paths = sorted({*ROOT.glob('scripts/*.py'), *ROOT.glob('vocoderbench/**/*.py'),
                    *ROOT.glob('vocoderbench/**/*.json'), *ROOT.glob('research/all-method*.md'),
                    ROOT / 'BASELINE.json', ROOT / 'pyproject.toml', ROOT / 'uv.lock'})
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths if path.is_file()}


def command_files(command):
    return {str(Path(value).resolve()): sha256(value) for value in command
            if isinstance(value, str) and Path(value).is_file() and Path(value).suffix in ('.py', '.json')}


def verify_previous(previous, command):
    if command_key(previous.get('base_command', previous['command'])) != command_key(command):
        raise ValueError('成功した工程の再開commandが一致しません')
    if previous.get('command_files') != command_files(command):
        raise ValueError('成功した工程の明示entrypointまたは入力hashが一致しません')
    for relative, expected in previous.get('scientific_source_receipt', {}).items():
        if sha256(ROOT / relative) != expected:
            raise ValueError('成功した工程の測定sourceが一致しません: ' + relative)
    receipt = previous.get('completion_receipt')
    if not receipt:
        return False
    for filename, expected in receipt.items():
        if not Path(filename).is_file() or sha256(filename) != expected:
            raise ValueError(f'保存成功成果が存在しないかhash不一致: {filename}')
    return True


def scientific_sources(stage, method, output):
    if stage in ('synthesis', 'synthesis-edits'):
        return read(RUN / 'synthesis-contracts' / f'{method}.json')['source_sha256']
    if output and (Path(output) / 'results.json').exists():
        data = read(Path(output) / 'results.json')
        return {'vocoderbench/' + key: value for key, value in data.get('source_sha256', {}).items()
                if (ROOT / 'vocoderbench' / key).is_file()}
    return {}


def completed_artifacts(stage, batch, method, output=None):
    paths = []
    if stage in ('synthesis', 'synthesis-edits'):
        contract_path = RUN / 'synthesis-contracts' / f'{method}.json'
        contract = read(contract_path)
        names = ['unedited'] if stage == 'synthesis' else list(contract['capabilities'])
        paths += [contract_path, RUN / f'input-batches/{batch:02d}.json']
        for spec in read(RUN / f'input-batches/{batch:02d}.json'):
            folder = RUN / 'native' / method / spec['id']
            for name in names:
                record = folder / f'{name}.json'
                row = read(record)
                if row['status'] != 'measured':
                    raise ValueError('成功終了工程に未成功の予定条件があります')
                paths += [record, Path(row['audio']['path'])]
                if 'feature_artifact' in row:
                    paths.append(Path(row['feature_artifact']['path']))
            if stage == 'synthesis':
                paths += [folder / name for name in ('representation.json', 'representation.npz', 'features.json', 'features.npy')]
    elif output and (Path(output) / 'results.json').exists():
        paths += sorted(path for path in Path(output).rglob('*') if path.is_file())
        paths += [Path(name) for name in read(Path(output) / 'results.json').get('input_file_sha256', {})]
    # その他の評価入口は個々のresume/hash契約を実行する。processの0だけで省略しない。
    return {str(path): sha256(path) for path in paths} or None
