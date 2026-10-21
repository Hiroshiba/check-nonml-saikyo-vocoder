"""Apron（LLSM2 Layer1）を固定した現在の作業ベースとして併記する。"""
import importlib.metadata
import logging
import platform
from types import SimpleNamespace
from uuid import uuid4

from .common import ROOT, digest, read, verify_prepared
from .native import LLSM_WRAPPER_SOURCE, llsm_build_command


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
    cache = runtime_cache.resolve()
    native = cache / 'native/libllsm_speed.so'
    native_sha256 = prepared['files']['native/libllsm_speed.so']
    if digest(native) != native_sha256:
        raise ValueError('準備済み Layer1 native library の SHA が一致しません')
    wrapper = cache / 'native/wrapper.c'
    if wrapper.read_bytes() != LLSM_WRAPPER_SOURCE.encode('utf-8'):
        raise ValueError('Layer1 native wrapper が固定ビルドソースと一致しません')
    build = read(cache / 'native/build.json')
    if build.get('command') != llsm_build_command(cache) or not build.get('compiler'):
        raise ValueError('Layer1 native build recipe が準備記録と一致しません')
    paths = [ROOT / 'BASELINE.json', ROOT / 'vocoderbench/references/native.py',
             *sorted((ROOT / 'vocoderbench/apron').glob('*.py'))]
    return {'baseline': baseline,
            'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths},
            'upstream_revision': LLSM_REVISION, 'ciglet_revision': CIGLET_REVISION,
            'native_sha256': native_sha256,
            'native_wrapper_sha256': prepared['files']['native/wrapper.c'],
            'native_build_record_sha256': prepared['files']['native/build.json'],
            'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in
                         ('numpy', 'scipy', 'pyworld', 'torch')},
            'analysis_seed': 0, 'decoder_seed': 0,
            'role': 'current_development_base_not_new_candidate',
            'runtime': 'host_python_3_12_with_verified_native_cache'}


def build(seed, runtime_cache):
    from ..apron import Layer1Engine, SAMPLE_RATE
    identity = record(runtime_cache)
    baseline = identity['baseline']
    engine = Layer1Engine(runtime_cache / 'native/libllsm_speed.so', identity['native_sha256'])

    def encode(x, path):
        destination = path.with_name(f'{path.stem}.{uuid4().hex}.layer1')
        logging.info('Layer1保存先（試行ごと、失敗時も保持）: %s', destination)
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
