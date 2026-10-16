"""現在の自作ベースと既存比較対象の共通呼出し。"""
import numpy as np
from . import pml, world
from .control import edit_parameters as edit_world

METHODS = ('pml', 'world_harvest')


def implementation(method):
    if method not in METHODS:
        raise ValueError(f'未対応の方式です: {method}')
    return pml if method == 'pml' else world


def encode(method, x, sr):
    return implementation(method).encode(x, sr)


def decode(method, params):
    return implementation(method).decode(params)


def edit(method, params, **kwargs):
    implementation(method)
    return pml.edit_parameters(params, **kwargs) if method == 'pml' else edit_world(params, **kwargs)


def scalars(params):
    return sum(value.size for value in vars(params).values() if isinstance(value, np.ndarray))


def metadata(method, params):
    result = {'feature_scalars': scalars(params), 'analysis_metadata': getattr(params, 'analysis_metadata', {}),
              'representation': '連続F0・60 FWCEP係数・二値雑音マスク' if method == 'pml' else 'WORLDのF0・スペクトル包絡・非周期性'}
    if method == 'pml':
        result['feature_f0_voiced_fraction'] = None
        result['f0_note'] = '連続F0はパルス時計であり有声判定ではありません'
    else:
        result['feature_f0_voiced_fraction'] = float(np.mean(params.f0 > 0))
    return result
