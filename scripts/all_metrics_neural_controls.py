"""公開比較方式の復号入力に定義されているパラメータだけを操作する。"""
from __future__ import annotations

import json
import math

import numpy as np
import torch

from scripts.all_metrics_representation import copy_tree, to_numpy, validate_features


def pitch_conditions(description, **extra):
    return {f'pitch_{name}3': {'control': 'pitch', 'amount': amount,
                             'unit': 'semitone', 'target_cents': amount * 100,
                             'description': description, **extra}
            for name, amount in [('minus', -3), ('plus', 3)]}


def gain_conditions(description, **extra):
    return {f'gain_{name}6': {'control': 'gain', 'amount': amount,
                            'unit': 'dB', 'target_gain_db': amount,
                            'description': description, **extra}
            for name, amount in [('minus', -6), ('plus', 6)]}


def _facodec(adapter):
    def features(z):
        latent, speaker = map(to_numpy, z)
        frames = latent[0].T
        speaker = speaker.reshape(1, -1)
        return validate_features(np.concatenate((frames, np.repeat(speaker, len(frames), axis=0)), axis=1), {
            'representation': 'FACodec decoder-input continuous quantized embedding + speaker embedding',
            'frame_hop_samples': 200, 'sample_rate': 16000,
            'columns': [{'field': 'z', 'width': frames.shape[1]},
                        {'field': 'spk', 'width': speaker.shape[1], 'projection': 'broadcast'}],
            'note': 'RVQ code indices are not treated as Euclidean coordinates',
        })
    adapter.readout_features = features
    adapter.info['representation_contract']['missing_native_controls'] = [
        'pitch: no Hz-valued decoder input', 'gain: no dB-valued decoder input',
        'time: no declared duration edit', 'slope: no calibrated dB/octave input',
        'pitch-endpoint interpolation: native +3 semitone endpoint undefined']


def _hifiglot(adapter, src):
    from neural_formant_synthesis.feature_extraction import Normaliser
    norm = Normaliser()
    config = json.loads((src / 'hifiglot/configs/hifiglot/config_hifigan.json').read_text())
    adapter.capabilities = pitch_conditions('normalized pitch and linear pitch updated together')
    adapter.capabilities.update(gain_conditions(
        'represented energy in dB + delta, lower-clamped at the official -40 dB floor',
        limitation='original sub-floor energy is absent; acoustic gain response is measured'))

    def regenerate(z):
        feat, pitch = z
        feat[:, 0, :] = norm._scale(torch.log2(pitch), norm.f3_upper, norm.pitch_lower)
        return feat, pitch
    adapter.regenerate_derived = regenerate

    def edit(z, condition):
        point = adapter.capabilities[condition]
        feat, pitch = copy_tree(z)
        if point['control'] == 'pitch':
            pitch *= 2 ** (point['amount'] / 12)
            # Preserve the pinned upstream f3_upper choice, not pitch_upper.
            feat[:, 0, :] = norm._scale(torch.log2(pitch), norm.f3_upper, norm.pitch_lower)
        else:
            energy = (feat[:, -2, :] + 1) * (norm.energy_upper - norm.energy_lower) / 2 + norm.energy_lower
            feat[:, -2, :] = norm._scale(
                torch.clamp(energy + point['amount'], min=norm.energy_lower),
                norm.energy_upper, norm.energy_lower)
        return feat, pitch

    def features(z):
        feat, pitch = map(to_numpy, z)
        matrix = np.concatenate((feat[0].T, pitch.reshape(-1, 1)), axis=1)
        return validate_features(matrix, {
            'representation': 'HiFi-Glot normalized conditioning + linear pitch',
            'frame_hop_samples': config['hop_size'], 'sample_rate': adapter.sr,
            'columns': ['pitch_normalized', 'formants_as_extracted', 'tilt_normalized',
                        'centroid_normalized', 'energy_normalized', 'voicing', 'pitch_Hz'],
            'source_feature_channels': feat.shape[1],
        })
    adapter.edit, adapter.readout_features = edit, features
    adapter.info['representation_contract']['missing_native_controls'] = [
        'time: no declared duration edit', 'slope: reflection/tilt coefficient is not dB/octave']


def _sifigan(adapter, src):
    import joblib
    from sifigan.utils.features import dilated_factor
    config = adapter.info['config']
    if config['aux_feats'] != ['mcep', 'bap'] or config['df_f0_type'] != 'cf0' or config['sine_f0_type'] != 'cf0':
        raise ValueError('固定SiFiGANのaux_feats/励振設定が変わっています')
    adapter.capabilities = pitch_conditions('official cf0 scaling, dilation factors recomputed, excitation regenerated')
    adapter.capabilities.update(gain_conditions('mel-cepstrum c0 += ln(amplitude gain), using the fixed training scaler'))
    scaler = joblib.load(next((src.parent / 'models').rglob('*.joblib')))

    def regenerate(z):
        cf0, c, _ = z
        frequency = to_numpy(cf0).reshape(-1, 1)
        dfs = [torch.tensor(np.repeat(dilated_factor(frequency.copy(), adapter.sr, df), us),
                            dtype=torch.float32).view(1, 1, -1)
               for df, us in zip(config['dense_factors'], np.cumprod(config['generator']['upsample_scales']))]
        return cf0, c, dfs
    adapter.regenerate_derived = regenerate

    def edit(z, condition):
        point = adapter.capabilities[condition]
        cf0, c, _ = copy_tree(z)
        if point['control'] == 'gain':
            c[:, 0, :] += point['amount'] * math.log(10) / 20 / scaler['mcep'].scale_[0]
            return cf0, c, copy_tree(z[2])
        cf0 *= 2 ** (point['amount'] / 12)
        return regenerate((cf0, c, None))

    def features(z):
        cf0, c, _ = z
        return validate_features(np.concatenate((to_numpy(cf0)[0].T, to_numpy(c)[0].T), axis=1), {
            'representation': 'SiFiGAN cf0 + standardized mcep/bap conditioning',
            'frame_hop_samples': int(adapter.sr * config['frame_period'] / 1000),
            'sample_rate': adapter.sr,
            'columns': [{'field': 'cf0_Hz', 'width': 1}, {'field': 'c', 'aux_feats': config['aux_feats']}],
            'excluded_redundant_fields': 'dfs are deterministic multirate transforms of cf0',
        })
    adapter.edit, adapter.readout_features = edit, features
    adapter.info['representation_contract']['missing_native_controls'] = [
        'time: no declared duration edit',
        'slope: no calibrated dB/octave input']


def _magphase(adapter):
    adapter.capabilities = gain_conditions('add dB * ln(10) / 20 to every compressed log-magnitude bin')
    adapter.capabilities.update(pitch_conditions(
        'add semitone * ln(2)/12 to voiced log-F0; pitch-synchronous timing also changes',
        changes_duration=True, time_map_required=True))

    def edit(z, condition):
        point = adapter.capabilities[condition]
        values = list(copy_tree(z))
        if point['control'] == 'gain':
            values[0] += point['amount'] * math.log(10) / 20
        else:
            from src import magphase as mp
            lf0 = values[3]
            # The upstream decoder uses its own UV sentinel convention.
            f0 = np.exp(lf0)
            voiced = f0 > 1
            lf0[voiced] += point['amount'] * math.log(2) / 12
            values[4] = mp.f0_to_shift(np.exp(lf0), values[5])
        return tuple(values)

    def features(z):
        matrix = np.concatenate([np.asarray(x).reshape(len(z[0]), -1) for x in z[:4]], axis=1)
        return validate_features(matrix, {
            'representation': 'MagPhase compressed magnitude/phase/log-F0',
            'native_frame_grid': 'pitch synchronous', 'sample_rate': adapter.sr,
            'frame_times_seconds': (np.cumsum(np.asarray(z[4]).reshape(-1)) / z[5]).tolist(),
            'frame_times_origin': 'native_analysis_shift_cumsum',
            'columns': [{'field': field, 'width': np.asarray(value).reshape(len(z[0]), -1).shape[1]}
                        for field, value in zip(['logmag', 'real', 'imag', 'lf0'], z[:4])],
        })
    adapter.edit, adapter.readout_features = edit, features
    def frame_times(z):
        from src import magphase as mp
        shifts = mp.f0_to_shift(np.exp(z[3]), z[5]).astype(int).reshape(-1)
        return np.cumsum(shifts) / z[5]
    adapter.frame_times = frame_times
    adapter.info['representation_contract']['missing_native_controls'] = [
        'time-only: pitch-synchronous shifts are not an independent duration control',
        'slope: no calibrated dB/octave input']


def augment(adapter, method, src):
    if method == 'facodec':
        _facodec(adapter)
    elif method == 'hifiglot':
        _hifiglot(adapter, src)
    elif method == 'sifigan':
        _sifigan(adapter, src)
    elif method == 'magphase':
        _magphase(adapter)
    elif method == 'golf':
        from scripts.all_metrics_golf_control import augment_golf
        augment_golf(adapter)
    if not hasattr(adapter, 'edit'):
        def unavailable(z, condition):
            raise ValueError(f'{method}にこの物理操作は定義されていません: {condition}')
        adapter.edit = unavailable
