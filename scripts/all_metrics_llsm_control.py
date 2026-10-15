"""LLSM2 Layer 0の実パラメータ操作と固定次元の評価用読み出し。"""
import ctypes as ct

import numpy as np

from scripts.all_metrics_llsm_storage import CHP, Layer0Storage
from scripts.all_metrics_neural_controls import gain_conditions, pitch_conditions
from scripts.all_metrics_representation import export_tree, import_tree, validate_features


def _harmonic_features(harmonic, maximum):
    count = len(harmonic['ampl'])
    if count > maximum:
        raise ValueError('LLSMの調波数が固定config上限を超えています')
    result = np.zeros((4, maximum), dtype=np.float32)
    result[0, :count] = harmonic['ampl']
    result[1, :count] = np.sin(harmonic['phse'])
    result[2, :count] = np.cos(harmonic['phse'])
    result[3, :count] = 1
    return result.reshape(-1)


def augment_llsm(adapter, src):
    storage = Layer0Storage(src.parent / 'native/libllsm_speed.so')

    def export(z):
        arrays, structure = export_tree(storage.export(z))
        structure['llsm_layer'] = 0
        structure['native_float_type'] = 'float32'
        structure['fields'] = 'config + every frame F0/HM/NM/PSDRES, including ragged harmonics'
        return arrays, structure

    def restore(arrays, structure):
        if structure.get('llsm_layer') != 0:
            raise ValueError('LLSM Layer 0保存表現ではありません')
        return storage.restore(import_tree(arrays, structure))

    adapter.export_arrays, adapter.import_arrays = export, restore

    def export_residual(z):
        copied = storage.lib.llsm_copy_chunk(ct.cast(z, CHP))
        if not copied:
            raise ValueError('LLSM chunk copyに失敗しました')
        try:
            storage.lib.llsm_chunk_phasepropagate(copied, -1)
            return adapter.export_arrays(copied)
        finally:
            storage.lib.llsm_delete_chunk(copied)

    def integrate_phase(z):
        storage.lib.llsm_chunk_phasepropagate(ct.cast(z, CHP), 1)
        return z

    adapter.export_residual_arrays = export_residual
    adapter.integrate_phase = integrate_phase
    adapter.capabilities = pitch_conditions(
        'native FRAME_F0 scaling with phasepropagate(-1/+1); harmonic-index spectrum retained',
        limitation='Layer 0 pitch changes harmonic spacing and can move formants; no Layer 1 conversion')
    adapter.capabilities.update(gain_conditions(
        'HM amplitude * g, noise envelope power * g^2, noise target PSD + dB; PSDRES unchanged',
        limitation='upstream noise floors and regularization can deviate from exact linearity'))

    def edit(z, condition):
        point = adapter.capabilities[condition]
        result = storage.lib.llsm_copy_chunk(ct.cast(z, CHP))
        if not result:
            raise ValueError('LLSM chunk copyに失敗しました')
        try:
            if point['control'] == 'pitch':
                storage.lib.llsm_chunk_phasepropagate(result, -1)
            values = storage.export(result)
            for frame in values['frames']:
                if point['control'] == 'pitch':
                    frame['0'] *= 2 ** (point['amount'] / 12)
                else:
                    gain = 10 ** (point['amount'] / 20)
                    frame['1']['ampl'] *= gain
                    frame['2']['edc'] *= gain ** 2
                    frame['2']['psd'] += point['amount']
                    for harmonic in frame['2']['eenv']:
                        harmonic['ampl'] *= gain ** 2
            edited = storage.restore(values)
        finally:
            storage.lib.llsm_delete_chunk(result)
        if point['control'] == 'pitch':
            storage.lib.llsm_chunk_phasepropagate(ct.cast(edited, CHP), 1)
        return edited

    def features(z):
        values = storage.export(z)
        conf = values['config']
        max_harmonic, max_envelope = int(conf['2'][0]), int(conf['3'][0])
        npsd, channels = int(conf['4'][0]), int(conf['7'][0])
        rows = []
        for frame in values['frames']:
            noise = frame['2']
            if len(noise['psd']) != npsd or len(frame['3']) != npsd or len(noise['eenv']) != channels:
                raise ValueError('LLSMのframe次元が固定configと違います')
            rows.append(np.concatenate([
                frame['0'], _harmonic_features(frame['1'], max_harmonic),
                noise['psd'], noise['edc'], frame['3'],
                *[_harmonic_features(h, max_envelope) for h in noise['eenv']],
            ]))
        return validate_features(rows, {
            'representation': 'LLSM2 Layer 0 with native amplitudes, phase sin/cos and padding masks',
            'sample_rate': adapter.sr, 'frame_hop_seconds': float(conf['1'][0]),
            'max_harmonics': max_harmonic, 'max_noise_envelope_harmonics': max_envelope,
            'noise_channels': channels, 'noise_psd_dimensions': npsd,
            'columns': ['F0', 'HM[amplitude,sin_phase,cos_phase,present_mask]',
                        'NM.psd_dB', 'NM.edc_power', 'PSDRES',
                        'each_NM.eenv[amplitude,sin_phase,cos_phase,present_mask]'],
            'projection': 'native 5 ms grid; zero padded only absent harmonics, mask is explicit',
        })

    adapter.edit, adapter.readout_features = edit, features
    adapter.info['representation_contract']['missing_native_controls'] = [
        'time: official duration demo converts to Layer 1; current Layer 0 is kept',
        'slope: no calibrated dB/octave field']
