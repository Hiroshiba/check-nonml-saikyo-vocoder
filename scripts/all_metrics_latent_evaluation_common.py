"""#16–18専用評価の音声・永久IO証跡・既存品質値を厳密に読む。"""
from __future__ import annotations

import hashlib
import json
import math

from scipy.signal import resample_poly

from all_metrics_common import RUN, read
from all_metrics_controls import checked_audio
from all_metrics_latent_provenance import verify_retained_evidence
from vocoderbench.assessment.acoustics import auditory
from vocoderbench.assessment.common import NotApplicable
from vocoderbench.assessment.controls import attributes
from vocoderbench.quality_core import sha256, write_json

POINTS = ('unedited', 'quantized_float16', 'quantized_float32',
          'interpolation_input_gain_alpha0', 'interpolation_input_gain_alpha0p5', 'interpolation_input_gain_alpha1')
TOLERANCES = {'pitch_cents': 100., 'level_db': 1., 'slope_db_per_octave': 1., 'duration_seconds': .1}


def read_point(spec, method, condition):
    path = RUN / 'native' / method / spec['id'] / f'{condition}.json'
    if not path.exists():
        return {'case': spec['id'], 'method': method, 'condition': condition, 'status': 'pending_audio'}
    row = read(path)
    row['record_evidence'] = {'path': str(path), 'sha256': sha256(path)}
    if row['status'] == 'measured':
        checked_audio(row)
        if row.get('feature_artifact'):
            verify_retained_evidence(row)
    return row


def quality(spec, method, record):
    results = {}
    condition = record['condition']
    for name, folders in [('predicted_mos', ['mos/measurements', 'mos-latent/measurements']),
                          ('speaker_similarity', ['latent-speaker/measurements', 'speaker-full/measurements'])]:
        found, failure_evidence = None, None
        for folder in folders:
            candidates = [RUN / folder / f'{spec["id"]}__{method}__{condition}.json']
            if condition != 'unedited':
                candidates.append(RUN / folder / f'{spec["id"]}__{method}__unedited.json')
            for path in candidates:
                if not path.exists():
                    continue
                row = read(path)
                if row.get('status') != 'measured':
                    if path.name.endswith(f'__{condition}.json') and row.get('audio_sha256') == record['audio']['file_sha256']:
                        failure_evidence = {'status': row.get('status', 'unavailable'), 'value': None,
                            'reason': row.get('error', row.get('reason', row.get('measurement', {}).get('reason'))),
                            'source_result': str(path), 'source_result_sha256': sha256(path)}
                    continue
                audio = record['audio']
                if name == 'predicted_mos':
                    measured = row['measurement']
                    same = (measured.get('input_float32_sha256') == audio['float32_sha256'] and
                        measured.get('input_sample_rate') == audio['sample_rate'] and
                        measured.get('input_samples') == audio['samples'])
                    unit = 'predicted MOS'
                else:
                    measured = row.get('measurement', row)
                    source = measured.get('output_derivation', {}).get('source', {})
                    reference = measured.get('reference_derivation', {}).get('source', {})
                    same = (source.get('float64_sha256') == audio['float64_sha256'] and
                        source.get('sample_rate') == audio['sample_rate'] and source.get('samples') == audio['samples'] and
                        reference.get('file_sha256') == spec['sha256'])
                    unit = 'cosine'
                if same:
                    found = {'status': 'measured', 'value': row['value'], 'unit': unit, 'direction': 'higher',
                        'configuration_sha256': row['configuration_sha256'],
                        'source_result': str(path), 'source_result_sha256': sha256(path),
                        'origin': 'existing_quality_evidence_same_PCM_and_protocol'}
                    break
            if found:
                break
        results[name] = found or failure_evidence or {'status': 'pending_quality', 'value': None}
    return results


def fixed_quality_configuration(points):
    for name in ('predicted_mos', 'speaker_similarity'):
        configurations = {point['quality'][name]['configuration_sha256'] for point in points
                          if point.get('quality', {}).get(name, {}).get('status') == 'measured'}
        if len(configurations) > 1:
            raise ValueError(f'曲線内の品質評価条件が一致しません: {name}')


def attributes_cached(record, signature):
    info = record['audio']
    key = hashlib.sha256(f"{signature}|{info['float64_sha256']}|{info['sample_rate']}".encode()).hexdigest()
    path = RUN / 'latent-evaluation' / 'attributes-cache' / f'{key}.json'
    if path.exists():
        return read(path)['attributes']
    wave, rate = checked_audio(record)
    values = attributes(wave, rate, 300., 5000.)
    write_json(path, {'attributes': values, 'audio': info, 'contract_sha256': signature,
                      'scope': 'native全長の独立推定属性。自然音声の絶対F0真値ではない。'})
    return values


def artifact_evidence(spec, method, record):
    folder = RUN / 'native' / method / spec['id']
    if record['condition'] == 'unedited':
        path = folder / 'representation.json'
        value = read(path)
        actual = path.with_suffix('.npz')
        if (value.get('status') != 'measured' or sha256(actual) != value['sha256']
                or actual.stat().st_size != value['bytes']):
            raise ValueError('native基準payloadの成功状態・hash・bytes不一致')
        if method in ('hnm', 'world_harvest') and value.get('format') != 'native_hnm_world_npz':
            raise ValueError('新run HNM/WORLDの基準点は実native容器に限定します')
        proof = {'source_record': str(path), 'source_record_sha256': sha256(path),
                 'path': str(actual), 'sha256': value['sha256'], 'bytes': value['bytes'], 'retained': True,
                 'encoding': value['encoding'],
                 'container_format': value.get('format', 'numeric_arrays_and_structure_json_npz'),
                 'scope': '新runで実保存したfull precision native復号入力の容器。HNM/WORLDはnative NPZ、他6は構造JSON付きNPZ。読み出し用再export容器や旧値へ差し替えず、自己復号はしない。'}
    else:
        reference = record['provenance']
        if sha256(reference['path']) != reference['sha256']:
            raise ValueError('量子化の永久IO証跡hash不一致')
        data = read(reference['path'])
        proof = record['feature_artifact']
        if data['actual_payload']['sha256'] != proof['sha256'] or data['actual_payload']['bytes'] != proof['bytes']:
            raise ValueError('実容器と永久測定証跡のbytes/SHA不一致')
        if data['quantization'] != record['quantization']:
            raise ValueError('永久IO証跡と復号waveの量子化条件が不一致')
        proof = {**proof, 'permanent_provenance': reference,
                 'canonical_decoder_arrays': data['quantization']['restored_decoder_arrays'],
                 'native_representation_sha256': data['native_representation_sha256'],
                 'decode_wave_file_sha256': record['audio']['file_sha256'],
                 'scope': '正式write-close-read-import後のdecodeに対応した実容器測定値。派生payload解放後の永久証跡。'}
    duration = spec['samples'] / spec['sample_rate']
    assets = RUN / 'latent-contracts' / method / 'shared-assets.json'
    shared = read(assets) if assets.exists() else None
    return {**proof, 'payload_bits_per_source_second': proof['bytes'] * 8 / duration,
            'rate_denominator_seconds': duration,
            'shared_assets': str(assets),
            'shared_asset_manifest_sha256': sha256(assets) if shared else None,
            'fixed_shared_asset_bytes': shared['total_declared_file_bytes'] if shared else None,
            'shared_asset_scope': shared['scope'] if shared else 'pending asset manifest',
            'payload_alone_is_self_contained_bitrate': False}


def exact_identity(reference, output):
    q = output.get('quantization', {})
    a, b = reference['audio'], output['audio']
    return bool(q.get('restored_decoder_input_identical') and
                q.get('native_decoder_arrays') == q.get('restored_decoder_arrays') and
                a['float64_sha256'] == b['float64_sha256'] and a['sample_rate'] == b['sample_rate'] and
                a['samples'] == b['samples'] and output.get('origin') == 'existing_verified_waveform_identical_decoder_input')


def auditory_pair(reference, output):
    if exact_identity(reference, output):
        return {'status': 'analytic_identity', 'value': 0., 'unit': 'dB', 'direction': 'lower',
                'reason': '同一復号入力とPCMのhash証拠による定義上の差0。再測定・自己比較計算は行っていない。',
                'identity_evidence': output['quantization'], 'wave_file_sha256': output['audio']['file_sha256']}
    waves, derivations = [], []
    for record in (reference, output):
        wave, rate = checked_audio(record)
        divisor = math.gcd(rate, 16000)
        transformed = (resample_poly(wave, 16000 // divisor, rate // divisor,
                       window=('kaiser', 5.0), padtype='constant') if rate != 16000 else wave)
        waves.append(transformed)
        derivations.append({'source_audio': record['audio'], 'sample_rate': 16000,
            'up': 16000 // divisor, 'down': rate // divisor, 'samples': len(transformed),
            'float64_sha256': hashlib.sha256(transformed.astype('<f8').tobytes()).hexdigest(),
            'window': ['kaiser', 5.0], 'padtype': 'constant', 'stored': False})
    if len(waves[0]) != len(waves[1]):
        raise NotApplicable('共通16kHz派生の全長が不一致。自動crop/alignせず聴覚距離は適用外。')
    class Pair:
        def pair(self, job):
            return waves[0], waves[1], 16000
    result = auditory({}, Pair())
    result.update(status='measured', direction='lower', derivations=derivations,
                  scope='同方式native無編集対量子化。共通16kHzの同長全区間。')
    return result


def source_fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
