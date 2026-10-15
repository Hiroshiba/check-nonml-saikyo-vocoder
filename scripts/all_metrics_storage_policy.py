"""浮動小数点の保存精度摂動。時刻・整数・UV sentinelを数値摂動しない。"""
import copy

import numpy as np


def array_nodes(structure):
    def visit(node):
        if 'key' in node:
            yield node
        items = node.get('items', [])
        for child in items.values() if isinstance(items, dict) else items:
            yield from visit(child)
    return list(visit(structure['tree']))


def attach_storage_policy(adapter, method):
    original_export = adapter.export_arrays

    def export(z):
        arrays, structure = original_export(z)
        fields = []
        for node in array_nodes(structure):
            path = node['field_path']
            eligible = arrays[node['key']].dtype.kind == 'f'
            if method == 'llsm2' and path[0] == 'config':
                eligible = False
            if method == 'magphase' and path[0] == '4':
                eligible = False
            if method == 'sifigan' and path[0] == '2':
                eligible = False
            if method in ('hnm', 'world_harvest') and path[0] in ('frame_times', 'frequency_grid', 'time'):
                eligible = False
            node['quantization_eligible'] = eligible
            if method == 'magphase' and path[0] == '3':
                node['categorical_sentinel'] = -1e10
            if eligible:
                fields.append({'key': node['key'], 'field_path': path,
                               'decoder_dtype': node['dtype'],
                               'categorical_sentinel': node.get('categorical_sentinel')})
        structure['quantization_fields'] = fields
        structure['quantization_rule'] = (
            'IEEE float16/float32 nearest rounding for listed fields only; integer/config/time retained; '
            'restore original decoder dtype; MagPhase UV sentinel stored losslessly as a mask')
        return arrays, structure

    def quantize(arrays, structure, dtype):
        dtype = np.dtype(dtype)
        if dtype not in (np.dtype('float16'), np.dtype('float32')):
            raise ValueError('保存精度はfloat16またはfloat32に固定します')
        structure = copy.deepcopy(structure)
        result = {key: np.array(value, copy=True) for key, value in arrays.items()}
        for node in array_nodes(structure):
            if not node['quantization_eligible']:
                continue
            key = node['key']
            values = result[key]
            sentinel = node.get('categorical_sentinel')
            if sentinel is not None:
                mask = values == sentinel
                mask_key = key + '_categorical_mask'
                result[mask_key] = mask.astype(np.uint8)
                values = np.where(mask, 0, values)
                node['restore_sentinel_mask'] = mask_key
            with np.errstate(over='raise', invalid='raise'):
                result[key] = values.astype(dtype)
            if not np.isfinite(result[key]).all():
                raise ValueError(f'指定保存精度の有限範囲外です: {node["field_path"]}')
        structure['storage_float_dtype'] = dtype.name
        if method in ('hifiglot', 'sifigan'):
            restored = adapter.import_arrays(result, structure)
            canonical = adapter.regenerate_derived(restored)
            derived_arrays, derived_structure = original_export(canonical)
            if method == 'sifigan':
                for node in array_nodes(derived_structure):
                    if node['field_path'][0] == '2':
                        result[node['key']] = derived_arrays[node['key']]
                structure['derived_regeneration'] = 'dfs recomputed from stored cf0 restored to float32'
            else:
                feature = structure['tree']['items'][0]
                key = feature['key']
                original = copy.deepcopy(feature)
                pitch_key, other_key = key + '_derived_pitch', key + '_other_columns'
                result[pitch_key] = derived_arrays[key][:, :1, :]
                result[other_key] = result.pop(key)[:, 1:, :]
                first = dict(original, key=pitch_key, shape=list(result[pitch_key].shape),
                             quantization_eligible=False, field_path=['0', 'pitch_derived'])
                other = dict(original, key=other_key, shape=list(result[other_key].shape),
                             field_path=['0', 'other_columns'])
                structure['tree']['items'][0] = {'kind': 'tensor_columns', 'axis': 1, 'items': [first, other]}
                structure['derived_regeneration'] = 'normalized pitch column recomputed from stored linear pitch; other columns stored separately'
        structure['quantization_fields'] = [
            {'key': node['key'], 'field_path': node['field_path'], 'decoder_dtype': node['dtype'],
             'storage_dtype': str(result[node['key']].dtype), 'categorical_sentinel': node.get('categorical_sentinel')}
            for node in array_nodes(structure) if node['quantization_eligible']]
        return result, structure

    adapter.export_arrays = export
    adapter.quantize_arrays = quantize
    adapter.info['representation_contract']['quantization_fields'] = 'per-artifact structure.quantization_fields'
    adapter.info['representation_contract']['quantization_exclusions'] = [
        'integer/scalar structural metadata', 'LLSM configuration including hop time',
        'MagPhase analysis frame shifts and categorical UV sentinel']
