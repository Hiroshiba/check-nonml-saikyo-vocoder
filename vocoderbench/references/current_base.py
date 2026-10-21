"""Apron（LLSM2 Layer1）を固定した現在の作業ベースとして併記する。"""
import importlib.metadata
import platform
from types import SimpleNamespace

from .common import ROOT, digest, read, verify_prepared


BASE_ID = 'apron'
LLSM_REVISION = 'd18cdf02b31819670e3bc23ead933ad9467da06d'
CIGLET_REVISION = '895ba9b1c0eabee83d3544208bbc82420efa3206'


def record(runtime_cache):
    baseline = read(ROOT / 'BASELINE.json')
    if baseline.get('status') != 'selected' or baseline.get('method') != BASE_ID:
        raise ValueError('現在の作業ベースは選定済みのApronだけです')
    prepared = verify_prepared(runtime_cache, 'llsm2')
    sources = prepared['sources']
    if (sources['llsm']['revision'] != LLSM_REVISION
            or sources['ciglet']['revision'] != CIGLET_REVISION):
        raise ValueError('固定 LLSM2 / ciglet revision が一致しません')
    native = runtime_cache / 'native/libllsm_speed.so'
    from ..apron.engine import NATIVE_SHA256
    if digest(native) != NATIVE_SHA256:
        raise ValueError('固定 Layer1 native library の SHA が一致しません')
    paths = [ROOT / 'BASELINE.json',
             *sorted((ROOT / 'vocoderbench/apron').glob('*.py'))]
    return {'baseline': baseline,
            'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths},
            'upstream_revision': LLSM_REVISION, 'ciglet_revision': CIGLET_REVISION,
            'native_sha256': NATIVE_SHA256,
            'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in
                         ('numpy', 'scipy', 'pyworld', 'torch')},
            'analysis_seed': 0, 'decoder_seed': 0,
            'role': 'current_development_base_not_new_candidate',
            'runtime': 'host_python_3_12_with_verified_native_cache'}


def build(seed, runtime_cache):
    from ..apron import Layer1Engine, SAMPLE_RATE
    baseline = record(runtime_cache)['baseline']
    engine = Layer1Engine(runtime_cache / 'native/libllsm_speed.so')

    def encode(x, path):
        destination = path.with_suffix('.layer1')
        engine.analyze_to_saved(x, SAMPLE_RATE, destination)
        return destination

    def decode(destination):
        y, sample_rate = engine.decode_from_saved(destination)
        if sample_rate != SAMPLE_RATE:
            raise ValueError('Layer1 の実出力レートが固定24 kHzと異なります')
        return y

    return SimpleNamespace(sr=SAMPLE_RATE, encode=encode, decode=decode,
                           release=lambda destination: None,
                           info={'variant': baseline['version'], 'formal_base': baseline,
                                 'analysis_seed': 0, 'noise_seed': 0,
                                 'requested_comparison_seed': seed,
                                 'runtime': 'host_python_3_12',
                                 'native_output': '24 kHz, actual sample count'})
