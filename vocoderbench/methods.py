"""現在の自作ベースと既存比較対象の共通呼出し。"""
import numpy as np

from . import world, hnm
from .control import edit_parameters as edit_world

METHODS = ('hnm', 'world_harvest')


def encode(method, x, sr):
    return hnm.encode(x, sr) if method == 'hnm' else world.encode(x, sr)


def decode(method, params):
    return hnm.decode(params, seed=0) if method == 'hnm' else world.decode(params)


def edit(method, params, **kwargs):
    return hnm.edit_parameters(params, **kwargs) if method == 'hnm' else edit_world(params, **kwargs)


def scalars(params):
    return sum(value.size for value in vars(params).values() if isinstance(value, np.ndarray))


def metadata(method, params):
    return {'feature_scalars': scalars(params),
            'feature_f0_voiced_fraction': float(np.mean(params.f0 > 0)),
            'analysis_metadata': getattr(params, 'analysis_metadata', {}),
            'representation': 'F0・固定Hz調波振幅包絡・相対位相・雑音帯域パワー' if method == 'hnm' else 'WORLDのF0・スペクトル包絡・非周期性'}
