"""GOLF-ffの公開source/filterパラメータと時間単位を保持する。"""
import numpy as np

from scripts.all_metrics_neural_controls import gain_conditions, pitch_conditions
from scripts.all_metrics_representation import copy_tree, project_frames, to_numpy, validate_features


def augment_golf(adapter):
    adapter.capabilities = pitch_conditions(
        'scale oscillator phase increment (cycles/sample), retaining all filter parameters',
        limitation='the original adapter replaces unvoiced F0 by 150 Hz; that increment is also scaled')
    adapter.capabilities.update(gain_conditions(
        'multiply native end_filter_params[0] linear gain, before LPC and room filters'))

    def edit(z, condition):
        point = adapter.capabilities[condition]
        result = copy_tree(z)
        if point['control'] == 'pitch':
            result['phase'] = result['phase'] * 2 ** (point['amount'] / 12)
        else:
            params = result['end_filter_params']
            result['end_filter_params'] = (params[0] * 10 ** (point['amount'] / 20), *params[1:])
        return result

    def features(z):
        leaves = []

        def visit(value, path):
            if isinstance(value, dict):
                for key in sorted(value):
                    visit(value[key], path + [key])
            elif isinstance(value, (list, tuple)):
                for k, child in enumerate(value):
                    visit(child, path + [str(k)])
            else:
                if not hasattr(value, 'hop_length'):
                    raise ValueError(f'GOLF時間刻みが未定義です: {path}')
                array = to_numpy(value)
                if array.ndim not in (2, 3) or array.shape[0] != 1:
                    raise ValueError(f'GOLFのbatch/time/feature軸が未対応です: {path}')
                leaves.append(('/'.join(path), array[0].reshape(array.shape[1], -1), int(value.hop_length)))

        visit(z, [])
        target_hop = 240
        # The fixed encoder's native 10 ms grid; shorter tracks use held endpoints.
        duration_samples = max((len(array) - 1) * hop for _, array, hop in leaves)
        target_times = np.arange(int(duration_samples // target_hop) + 1) * target_hop / adapter.sr
        matrix = np.concatenate([
            project_frames(array, np.arange(len(array)) * hop / adapter.sr, target_times)
            for _, array, hop in leaves], axis=1)
        return validate_features(matrix, {
            'representation': 'GOLF-ff decoder input parameters after native control transforms',
            'sample_rate': adapter.sr, 'frame_hop_samples': target_hop,
            'projection': 'linear in time, held endpoints, native time axis 1',
            'columns': [{'field': name, 'width': array.shape[1], 'source_hop_samples': hop,
                         'source_frames': len(array)} for name, array, hop in leaves],
        })

    adapter.edit, adapter.readout_features = edit, features
    adapter.info['representation_contract']['missing_native_controls'] = [
        'time: no declared duration edit', 'slope: no calibrated dB/octave input']
