"""同一発話の既存ピッチ操作端点を、宣言した物理座標で補間する。"""
import numpy as np

from scripts.all_metrics_storage_policy import array_nodes


class InterpolationNotApplicable(ValueError):
    """Aligned endpoint correspondence is absent; do not silently align it."""


def _log_interpolate(left, right, alpha):
    if np.any((left > 0) != (right > 0)) or np.any(left < 0) or np.any(right < 0):
        raise InterpolationNotApplicable('logHz補間は同じ有声区間と非負F0が必要です')
    result = np.array(left, copy=True)
    voiced = left > 0
    result[voiced] = np.exp((1 - alpha) * np.log(left[voiced]) + alpha * np.log(right[voiced]))
    return result


def _positive_interpolate(left, right, alpha):
    if np.any(left < 0) or np.any(right < 0):
        raise ValueError('振幅・powerの補間は非負値に限定します')
    positive = (left > 0) & (right > 0)
    result = left * (1 - alpha) + right * alpha
    result[positive] = np.exp((1 - alpha) * np.log(left[positive]) + alpha * np.log(right[positive]))
    return result


def attach_interpolation(adapter, method):
    adapter.interpolation_rule = {
        'scope': 'same utterance reencoded at original and -6 dB input; existing +3 semitone endpoint is an optional separate condition',
        'primary_pitch': 'linear in log Hz with unchanged voicing mask',
        'derived_fields': 'HiFi-Glot normalized pitch and SiFiGAN dilation factors regenerated',
        'phase': 'LLSM removes endpoint F0 phase integration, interpolates residual phases by shortest arc, then integrates interpolated F0; GOLF phase is frequency increment',
        'fixed_fields': 'time grid, count, integer and configuration metadata remain unchanged',
        'magphase': 'logF0 interpolation changes pitch-synchronous duration; shifts regenerated',
        'positive_amplitude_power': 'log interpolation when both positive; linear at an exact zero boundary',
        'facodec': 'continuous decoder-input z and speaker embedding coordinates interpolated linearly',
        'alignment': 'no post-hoc alignment; unequal frame/field shapes or voicing masks are not applicable',
    }

    def interpolate(z0, z1, alpha, endpoint_kind='input_gain_reencode'):
        if endpoint_kind not in ('input_gain_reencode', 'native_pitch_plus3'):
            raise ValueError('未定義の補間端点条件です')
        if endpoint_kind == 'native_pitch_plus3' and 'pitch_plus3' not in adapter.capabilities:
            raise ValueError('既存+3 semitone端点がないためこの補間条件は適用外です')
        if not np.isfinite(alpha) or not 0 <= alpha <= 1:
            raise ValueError('alphaは0以上1以下に限定します')
        left, structure = adapter.export_arrays(z0)
        right, right_structure = adapter.export_arrays(z1)
        if left.keys() != right.keys():
            raise InterpolationNotApplicable('補間端点の表現fieldが一致しません')
        if structure['tree'] != right_structure['tree']:
            raise InterpolationNotApplicable('補間端点の構造・型・scalar metadataが一致しません')
        if method == 'magphase' and endpoint_kind == 'input_gain_reencode' and not np.array_equal(z0[4], z1[4]):
            raise InterpolationNotApplicable('再解析したMagPhaseのpitch mark対応時刻が一致しません')
        nodes = array_nodes(structure)
        if [(n['field_path'], n['shape']) for n in nodes] != [
                (n['field_path'], n['shape']) for n in array_nodes(right_structure)]:
            raise InterpolationNotApplicable('補間端点の表現shapeが一致しません')
        if alpha in (0, 1):
            return adapter.import_arrays(left if alpha == 0 else right, structure)
        if method == 'llsm2':
            left, structure = adapter.export_residual_arrays(z0)
            right, right_structure = adapter.export_residual_arrays(z1)
            nodes = array_nodes(structure)
        result = {}
        for node in nodes:
            key, path = node['key'], node['field_path']
            a, b = left[key], right[key]
            if a.shape != b.shape:
                raise InterpolationNotApplicable('補間端点の配列shapeが一致しません')
            fixed = a.dtype.kind != 'f' or (method == 'llsm2' and path[0] == 'config')
            fixed |= method in ('hnm', 'world_harvest') and path[0] in ('frame_times', 'frequency_grid', 'time')
            if fixed and not np.array_equal(a, b):
                raise InterpolationNotApplicable('時刻・config・整数構造が異なる端点は補間できません')
            if np.array_equal(a, b):
                value = a.copy()
            elif ((method == 'llsm2' and path[-1] == 'phse')
                  or (method == 'hnm' and path == ['relative_phase'])):
                delta = np.arctan2(np.sin(b - a), np.cos(b - a))
                value = np.arctan2(np.sin(a + alpha * delta), np.cos(a + alpha * delta))
            elif ((method == 'llsm2' and path[0] == 'frames' and path[-1] == '0')
                  or (method == 'hifiglot' and path == ['1'])
                  or (method == 'sifigan' and path == ['0'])
                  or (method == 'golf' and path == ['phase'])
                  or (method in ('hnm', 'world_harvest') and path == ['f0'])):
                value = _log_interpolate(a, b, alpha)
            elif ((method == 'llsm2' and path[-1] in ('ampl', 'edc'))
                  or (method == 'golf' and path == ['end_filter_params', '0'])
                  or (method == 'hnm' and path[0] in ('harmonic_envelope', 'noise_psd'))
                  or (method == 'world_harvest' and path == ['spectral_envelope'])):
                value = _positive_interpolate(a, b, alpha)
            elif method == 'magphase' and path == ['3']:
                if np.any((a <= -1e9) != (b <= -1e9)):
                    raise InterpolationNotApplicable('MagPhase補間端点のUV maskが一致しません')
                value = a * (1 - alpha) + b * alpha
            else:
                value = a * (1 - alpha) + b * alpha
            result[key] = value.astype(a.dtype)
        value = adapter.import_arrays(result, structure)
        if method == 'llsm2':
            value = adapter.integrate_phase(value)
        if hasattr(adapter, 'regenerate_derived'):
            value = adapter.regenerate_derived(value)
        if method == 'magphase':
            from src import magphase as mp
            value = list(value)
            value[4] = mp.f0_to_shift(np.exp(value[3]), value[5])
            value = tuple(value)
        return value

    adapter.interpolate = interpolate
    adapter.info['representation_contract']['interpolation_rule'] = adapter.interpolation_rule
