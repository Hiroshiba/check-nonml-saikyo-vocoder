"""既存復号入力を数値配列と型情報へ分離する。pickleは使用しない。"""
from __future__ import annotations

import numpy as np
import torch


def export_tree(value):
    """Return (arrays, structure); all tensor/array buffers are independent copies."""
    arrays = {}

    def visit(item, path=()):
        if hasattr(item, 'as_tensor') and hasattr(item, 'hop_length'):
            node = visit(item.as_tensor(), path)
            node.update(kind='audio_tensor', hop_length=int(item.hop_length))
            return node
        if isinstance(item, (np.ndarray, torch.Tensor)):
            tensor = isinstance(item, torch.Tensor)
            array = item.detach().cpu().numpy() if tensor else item
            if array.dtype.kind not in 'biufc' or not np.isfinite(array).all():
                raise ValueError('表現は有限な数値配列である必要があります')
            key = f'array_{len(arrays):04d}'
            arrays[key] = np.array(array, copy=True)
            return {'kind': 'tensor' if tensor else 'ndarray', 'key': key,
                    'dtype': array.dtype.str, 'shape': list(array.shape), 'field_path': list(path)}
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValueError('表現辞書のキーは文字列に限定します')
            return {'kind': 'dict', 'items': {k: visit(item[k], (*path, k)) for k in sorted(item)}}
        if isinstance(item, (list, tuple)):
            return {'kind': 'tuple' if isinstance(item, tuple) else 'list',
                    'items': [visit(v, (*path, str(k))) for k, v in enumerate(item)]}
        if isinstance(item, (int, float, bool, np.number)):
            raw = item.item() if isinstance(item, np.number) else item
            if not np.isfinite(raw):
                raise ValueError('表現scalarは有限値に限定します')
            return {'kind': 'scalar', 'value': raw}
        if item is None:
            return {'kind': 'none'}
        raise TypeError(f'未対応の表現型です: {type(item)}')

    return arrays, {'schema_version': 1, 'tree': visit(value)}


def import_tree(arrays, structure):
    """Restore the original decoder dtype after explicit storage perturbation."""
    def visit(node):
        kind = node['kind']
        if kind == 'tensor_columns':
            return torch.cat([visit(child) for child in node['items']], dim=node['axis'])
        if kind in ('tensor', 'ndarray', 'audio_tensor'):
            value = np.asarray(arrays[node['key']])
            if list(value.shape) != node['shape'] or not np.isfinite(value).all():
                raise ValueError('保存表現のshapeまたは有限性が一致しません')
            value = np.array(value, dtype=np.dtype(node['dtype']), copy=True)
            if 'restore_sentinel_mask' in node:
                mask = np.asarray(arrays[node['restore_sentinel_mask']], dtype=bool)
                if mask.shape != value.shape:
                    raise ValueError('カテゴリsentinelのmask shapeが一致しません')
                value[mask] = node['categorical_sentinel']
            if kind == 'ndarray':
                return value
            value = torch.from_numpy(value)
            if kind == 'audio_tensor':
                from models.audiotensor import AudioTensor
                value = AudioTensor(value, node['hop_length'])
            return value
        if kind == 'dict':
            return {key: visit(child) for key, child in node['items'].items()}
        if kind in ('list', 'tuple'):
            values = [visit(child) for child in node['items']]
            return tuple(values) if kind == 'tuple' else values
        if kind == 'scalar':
            return node['value']
        if kind == 'none':
            return None
        raise ValueError(f'未対応の保存表現型です: {kind}')
    return visit(structure['tree'])


def copy_tree(value):
    return import_tree(*export_tree(value))


def to_numpy(value):
    if hasattr(value, 'as_tensor'):
        value = value.as_tensor()
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def validate_features(features, schema):
    features = np.asarray(features, dtype=np.float32)
    if features.ndim != 2 or not all(features.shape) or not np.isfinite(features).all():
        raise ValueError('読み出し用特徴は有限なframe×dimension配列に限定します')
    return features, dict(schema, frame_count=features.shape[0],
                          dimension_count=features.shape[1], dtype='float32',
                          codebook_index_as_continuous=False)


def project_frames(matrix, source_times, target_times):
    """Fixed linear projection of continuous coordinates, with held endpoints."""
    matrix = np.asarray(matrix)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    if len(matrix) != len(source_times):
        raise ValueError('特徴のフレーム数と時刻数が一致しません')
    return np.column_stack([np.interp(target_times, source_times, matrix[:, k])
                            for k in range(matrix.shape[1])])
