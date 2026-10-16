"""現在のPMLを候補や外部方式に偽装せず、同じ固定入力で併記する。"""
import importlib.metadata
import platform
from types import SimpleNamespace

from .common import ROOT, digest, read


def record():
    baseline = read(ROOT / 'BASELINE.json')
    if baseline.get('status') != 'selected' or baseline.get('method') != 'pml':
        raise ValueError('この入口が併記できる現在のベースは選定済みPMLです')
    paths = [ROOT / 'BASELINE.json', *sorted((ROOT / 'vocoderbench').glob('pml/**/*.py'))]
    return {'baseline': baseline,
            'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths},
            'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'pyworld', 'pyreaper')},
            'analysis_seed': 20261015, 'role': 'current_development_base_not_new_candidate'}


def build(seed):
    from .. import pml
    baseline = record()['baseline']
    return SimpleNamespace(sr=16000, encode=lambda x, path: pml.encode(x, 16000),
                           decode=lambda parameters: pml.decode(parameters, seed=seed),
                           info={'variant': baseline['version'], 'formal_base': baseline,
                                 'noise_seed': seed, 'runtime': 'host_python'})
