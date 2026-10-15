"""既存HNM/WORLDを同じ評価APIへ接続する。元の復号・編集実装は変更しない。"""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from vocoderbench import hnm, methods, world
from vocoderbench.references.common import digest
from scripts.all_metrics_interpolation import InterpolationNotApplicable, attach_interpolation
from scripts.all_metrics_neural_controls import gain_conditions, pitch_conditions
from scripts.all_metrics_representation import export_tree, import_tree, validate_features
from scripts.all_metrics_storage_policy import attach_storage_policy


ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    'hnm': ['f0', 'frame_times', 'frequency_grid', 'harmonic_envelope',
            'noise_psd', 'relative_phase', 'periodicity'],
    'world_harvest': ['f0', 'time', 'spectral_envelope', 'aperiodicity'],
}


def build_base_control_adapter(method, src, models, out):
    del src, models
    out.mkdir(parents=True, exist_ok=True)
    module = hnm if method == 'hnm' else world
    parameter_type = hnm.HNMParameters if method == 'hnm' else world.WorldParameters
    sources = sorted((ROOT / 'vocoderbench').glob('hnm*.py')) if method == 'hnm' else [
        ROOT / 'vocoderbench/world.py', ROOT / 'vocoderbench/control.py']
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    if method == 'world_harvest':
        path = world.library_path()
        if not path.is_file():
            raise FileNotFoundError(f'固定WORLD共有ライブラリがありません: {path}')
        source_hashes['native_world_library'] = digest(path)
    adapter = SimpleNamespace(
        sr=16000, encode=lambda x, path: methods.encode(method, x, 16000),
        decode=lambda z: methods.decode(method, z), load_native=module.load, load=module.load,
        capabilities=pitch_conditions('existing methods.edit pitch_semitones parameter'),
        info={'variant': 'current HNM-v3' if method == 'hnm' else 'fixed WORLD Harvest',
              'noise_seed': 0, 'source_hashes': source_hashes,
              'representation_contract': {
                  'version': 1, 'method': method,
                  'serialization': 'numeric NPZ arrays + JSON metadata; native dataclass restored',
                  'decoder_input': True, 'external_decoder_assets_required': True,
                  'payload_alone_is_self_contained_bitrate': False,
                  'shared_decoder_assets': source_hashes,
                  'missing_native_controls': ['slope: no native calibrated dB/octave parameter'],
              }})
    adapter.capabilities.update(gain_conditions('existing methods.edit gain_db parameter'))

    def export(z):
        module.validate(z)
        arrays, structure = export_tree({field: getattr(z, field) for field in FIELDS[method]})
        structure['parameter_class'] = parameter_type.__name__
        structure['parameter_metadata'] = copy.deepcopy({
            key: value for key, value in vars(z).items() if key not in FIELDS[method]})
        return arrays, structure

    def restore(arrays, structure):
        if structure['parameter_class'] != parameter_type.__name__:
            raise ValueError('保存表現の方式が一致しません')
        z = parameter_type(**import_tree(arrays, structure), **copy.deepcopy(structure['parameter_metadata']))
        module.validate(z)
        return z

    def edit(z, condition):
        point = adapter.capabilities[condition]
        kwargs = {'pitch_semitones' if point['control'] == 'pitch' else 'gain_db': point['amount']}
        return methods.edit(method, z, **kwargs)

    def features(z):
        parts = [z.f0[:, None]]
        columns = [{'field': 'f0_Hz', 'width': 1}]
        if method == 'hnm':
            parts += [z.harmonic_envelope, z.noise_psd, z.periodicity[:, None]]
            columns += [{'field': name, 'width': value.shape[1]} for name, value in
                        [('harmonic_envelope', z.harmonic_envelope), ('noise_psd', z.noise_psd)]]
            columns.append({'field': 'periodicity', 'width': 1})
            if z.relative_phase is not None:
                harmonics = np.arange(1, z.max_harmonics + 1)
                present = (z.f0[:, None] > 0) & (harmonics <= np.floor(z.sample_rate * .48 / np.maximum(z.f0[:, None], 1e-12)))
                parts += [np.sin(z.relative_phase) * present, np.cos(z.relative_phase) * present,
                          present.astype(float)]
                columns += [{'field': name, 'width': z.max_harmonics}
                            for name in ['relative_phase_sin', 'relative_phase_cos', 'harmonic_present']]
            times = z.frame_times
        else:
            parts += [z.spectral_envelope, z.aperiodicity]
            columns += [{'field': name, 'width': value.shape[1]} for name, value in
                        [('spectral_envelope', z.spectral_envelope), ('aperiodicity', z.aperiodicity)]]
            times = z.time
        return validate_features(np.concatenate(parts, axis=1), {
            'representation': method + ' native acoustic parameters, time/frequency-grid metadata excluded',
            'sample_rate': z.sample_rate, 'frame_times_seconds': times.tolist(),
            'columns': columns, 'phase_rule': 'sin/cos with physical harmonic-support mask for HNM',
            'projection': 'native fixed frame grid, no regridding or per-utterance normalization',
        })

    adapter.export_arrays, adapter.import_arrays = export, restore
    adapter.edit, adapter.readout_features = edit, features
    adapter.edit_time = lambda z, scale: methods.edit(method, z, time_scale=scale)
    adapter.extra_controls = {'time_scale': {'unit': 'output/input duration ratio', 'minimum': .25,
                                           'maximum': 4, 'native_api': 'methods.edit(time_scale=...)'}}
    attach_storage_policy(adapter, method)
    attach_interpolation(adapter, method)
    original_interpolate = adapter.interpolate

    def interpolate(z0, z1, alpha, endpoint_kind='input_gain_reencode'):
        immutable = ['sample_rate', 'n_samples', 'schema_version', 'method']
        immutable += ['max_harmonics'] if method == 'hnm' else ['frame_period', 'source_revision']
        if any(getattr(z0, field) != getattr(z1, field) for field in immutable):
            raise InterpolationNotApplicable('HNM/WORLD補間端点の復号設定が一致しません')
        value = original_interpolate(z0, z1, alpha, endpoint_kind=endpoint_kind)
        if method == 'hnm' and z0.relative_phase is not None and 0 < alpha < 1:
            # HNM stores an unwrapped phase trajectory; retain the left winding branch.
            delta = np.arctan2(np.sin(z1.relative_phase - z0.relative_phase),
                               np.cos(z1.relative_phase - z0.relative_phase))
            value.relative_phase = z0.relative_phase + alpha * delta
            module.validate(value)
        return value

    adapter.interpolate = interpolate
    adapter.info['representation_contract']['interpolation_metadata_rule'] = (
        'immutable decoder settings must match; descriptive analysis metadata retained from first endpoint; '
        'HNM residual phase circular arc retains the unwrapped left-endpoint branch')
    return adapter
