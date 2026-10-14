"""同一原音と-6 dB再解析端点の正式補間、および既存時間操作。"""
from __future__ import annotations

import hashlib
import logging
import math
import time

import numpy as np
import torch

from all_metrics_common import freeze, now, read, save_audio
from all_metrics_latent_io import (
    array_hashes, base_row, decode_result, failure, pending, read_payload, release, save_payload,
)
from all_metrics_synthesis import native_input, seed_all
from all_metrics_latent_provenance import evidence as keep_evidence, release_payload
from scripts.all_metrics_interpolation import InterpolationNotApplicable
from vocoderbench.quality_core import sha256, write_json


def attenuation_input(spec, args):
    directory = args.output_root / 'latent-inputs' / 'gain_minus6'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{spec["id"]}.npy'
    if sha256(spec['path']) != spec['sha256']:
        raise ValueError('固定原音hash不一致')
    wave = np.load(spec['path'], allow_pickle=False).astype(np.float64) * 10 ** (-6 / 20)
    expected = hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest()
    if target.exists():
        saved = np.load(target, allow_pickle=False)
        if hashlib.sha256(saved.astype('<f8').tobytes()).hexdigest() != expected:
            raise ValueError('保存済み-6 dB入力のPCM hash不一致')
        info = read(target.with_suffix('.json'))['audio']
        if sha256(target) != info['file_sha256']:
            raise ValueError('保存済み-6 dB入力のファイルhash不一致')
    else:
        info = save_audio(target, wave, spec['sample_rate'])
    row = {'case': spec['id'], 'source_sha256': spec['sha256'], 'gain_db': -6.0,
           'linear_gain': 10 ** (-6 / 20), 'audio': info,
           'scope': '物理的入力摂動。nativeボコーダーのgain control性能とは呼ばない。'}
    freeze(target.with_suffix('.json'), row)
    return {**spec, 'path': str(target), 'sha256': info['file_sha256']}, row


def attenuated_endpoint(adapter, spec, args, signature, folder):
    path = folder / 'interpolation_gain_minus6_endpoint.npz'
    metadata = path.with_suffix('.json')
    prior = read(metadata) if metadata.exists() else None
    if prior:
        if prior['contract_sha256'] != signature:
            raise ValueError('保存済み再解析端点の契約不一致')
        if path.exists():
            if sha256(path) != prior['payload']['sha256']:
                raise ValueError('保存済み再解析端点のhash不一致')
            value = adapter.import_arrays(*read_payload(path))
            if array_hashes(adapter, value) != prior['decoder_arrays']:
                release(adapter, value)
                raise ValueError('再解析端点の永久canonical hash不一致')
            return value, prior
    modified, input_manifest = attenuation_input(spec, args)
    input_folder = args.output_root / 'latent-adapter-work' / args.method / spec['id'] / 'gain_minus6'
    input_folder.mkdir(parents=True, exist_ok=True)
    wave, wav, input_info = native_input(modified, adapter, args.method, input_folder)
    seed_all(args.seed)
    start, cpu = time.perf_counter(), time.process_time()
    with torch.inference_mode():
        endpoint = adapter.encode(wave, wav)
    row = {'case': spec['id'], 'method': args.method, 'contract_sha256': signature,
           'analysis_seconds': time.perf_counter() - start,
           'analysis_process_cpu_seconds': time.process_time() - cpu,
           'input': input_info, 'input_manifest': input_manifest, 'seed': args.seed,
           'finished_at_utc': now(), 'origin': 'new_analysis_of_known_input_gain_minus6'}
    restored = None
    try:
        canonical = array_hashes(adapter, endpoint)
        if prior and canonical != prior['decoder_arrays']:
            raise ValueError('再生成した端点のcanonical hashが不一致。過去証跡を上書きしません')
        payload = save_payload(*adapter.export_arrays(endpoint), path)
        payload['retained'] = False
        if prior and payload['sha256'] != prior['payload']['sha256']:
            raise ValueError('再生成端点の実保存容器hashが不一致。過去証跡を上書きしません')
        restored = adapter.import_arrays(*read_payload(path))
        if array_hashes(adapter, restored) != canonical:
            raise ValueError('実ファイルから復元した端点のcanonical hash不一致')
        row.update(payload=payload, decoder_arrays=canonical)
        row['provenance'] = keep_evidence(args, spec, 'interpolation_gain_minus6_endpoint', {
            'contract_sha256': signature, 'seed': args.seed, 'source_input_sha256': spec['sha256'],
            'input': input_info, 'payload': payload, 'decoder_arrays': canonical,
            'measurement_order': 'known input reencode, actual write-close-read-import, then official endpoint/midpoint decodes'})
        if prior:
            write_json(folder / 'regeneration_history' / f'gain-minus6-{time.time_ns()}.json', row)
            row = {**prior, 'payload': payload}
        write_json(metadata, row)
        return restored, row
    except Exception:
        release(adapter, restored)
        raise
    finally:
        release(adapter, endpoint)


def interpolation_case(adapter, z, source, spec, args, signature, folder):
    names = ['interpolation_input_gain_alpha0', 'interpolation_input_gain_alpha0p5',
             'interpolation_input_gain_alpha1']
    targets = [folder / f'{name}.json' for name in names]
    todo = [pending(path, signature, args.retry_failed) for path in targets]
    if not any(todo):
        endpoint_meta = folder / 'interpolation_gain_minus6_endpoint.json'
        if endpoint_meta.exists():
            release_payload(read(endpoint_meta)['payload'], [endpoint_meta, *targets], args, spec,
                '中断再開時、補間の全alpha条件が既にterminal保存済みであるため端点payloadを解放。')
        midpoint = read(targets[1]).get('feature_artifact')
        if midpoint:
            release_payload(midpoint, [targets[1]], args, spec, '全alpha条件のterminal保存後に中間payloadを解放。')
        return
    count = (spec['samples'] * adapter.sr + spec['sample_rate'] - 1) // spec['sample_rate']
    evidence = {'endpoint_kind': 'input_gain_reencode', 'input_gain_db': [0.0, -6.0],
                'rule': adapter.interpolation_rule,
                'scope': '同一原音の別解析端点。波形DSPをnative制御とは扱わず、後付け整列しない。'}
    if todo[0]:
        row = base_row(spec, args, signature, names[0], source)
        row.update(interpolation={**evidence, 'alpha': 0.0},
                   endpoint_decoder_arrays=array_hashes(adapter, z))
        try:
            decode_result(adapter, z, targets[0], row, count, reuse=folder / 'unedited.json')
        except Exception:
            logging.exception('補間の既存端点引用失敗')
            failure(targets[0], row)
    if not any(todo[1:]):
        return
    endpoint, endpoint_info, midpoint = None, None, None
    try:
        endpoint, endpoint_info = attenuated_endpoint(adapter, spec, args, signature, folder)
        for i, alpha in ((2, 1.0), (1, 0.5)):
            if not todo[i]:
                continue
            row = base_row(spec, args, signature, names[i], source)
            row.update(interpolation={**evidence, 'alpha': alpha},
                       reencoded_endpoint=endpoint_info)
            value = None
            try:
                if alpha == 1:
                    value, payload = endpoint, endpoint_info['payload']
                else:
                    interpolated = adapter.interpolate(z, endpoint, alpha, endpoint_kind='input_gain_reencode')
                    try:
                        canonical = array_hashes(adapter, interpolated)
                        midpoint = save_payload(*adapter.export_arrays(interpolated), folder / f'{names[i]}.npz')
                        midpoint['retained'] = False
                    finally:
                        release(adapter, interpolated)
                    value = adapter.import_arrays(*read_payload(midpoint['path']))
                    if array_hashes(adapter, value) != canonical:
                        raise ValueError('実ファイルから復元した中間点のcanonical hash不一致')
                    payload = midpoint
                row['feature_artifact'] = payload
                row['provenance'] = keep_evidence(args, spec, names[i], {
                    'contract_sha256': signature, 'seed': args.seed, 'native_representation_sha256': source['sha256'],
                    'reencoded_endpoint_provenance': endpoint_info['provenance'],
                    'alpha': alpha, 'actual_payload': payload, 'decoder_arrays': array_hashes(adapter, value)})
                row['endpoint_role'] = 'independent_physical_endpoint' if alpha == 1 else 'interpolated_midpoint'
                decode_result(adapter, value, targets[i], row, count)
            except InterpolationNotApplicable:
                failure(targets[i], row, status='not_applicable')
            except Exception:
                logging.exception('正式入力端点補間失敗')
                failure(targets[i], row)
            finally:
                if value is not endpoint:
                    release(adapter, value)
    except Exception:
        logging.exception('正式-6 dB入力再解析失敗')
        for i in (1, 2):
            if todo[i]:
                row = base_row(spec, args, signature, names[i], source)
                row.update(interpolation=evidence, failure_stage='input_gain_reencode')
                failure(targets[i], row)
    finally:
        release(adapter, endpoint)
        if all(target.exists() for target in targets):
            if endpoint_info is not None:
                release_payload(endpoint_info['payload'],
                    [folder / 'interpolation_gain_minus6_endpoint.json', *targets], args, spec,
                    'alpha0/0.5/1の正式波形または適用外/失敗が全て保存済み。永久端点hashと入力を保持。')
            if midpoint is not None:
                release_payload(midpoint, [targets[1]], args, spec,
                    '実保存中間payloadの読戻し・復元・正式復号を完了し、永久証跡と波形を保持。')


def time_case(adapter, z, source, spec, args, signature, folder):
    target = folder / 'time_scale1p25.json'
    if not pending(target, signature, args.retry_failed):
        return
    row = base_row(spec, args, signature, target.stem, source,
        {'control': 'time_scale', 'amount': 1.25, 'unit': 'output/input duration ratio',
         'native_api': 'existing adapter.edit_time / methods.edit(time_scale=...)'})
    edited = None
    try:
        reference = read(folder / 'unedited.json')['audio']
        edited = adapter.edit_time(z, 1.25)
        expected = math.floor(z.n_samples * 1.25 + 0.5)
        row.update(expected_samples=expected, expected_seconds=expected / adapter.sr,
                   length_rounding='positive round half up',
                   feature_artifact=save_payload(*adapter.export_arrays(edited), folder / 'time_scale1p25.npz'))
        def finalize(result):
            result['time_map'] = {'reference_seconds': [0.0, reference['seconds']],
                'output_seconds': [0.0, result['audio']['seconds']],
                'known_requested_map': {'reference_seconds': [0.0, spec['samples'] / spec['sample_rate']],
                    'output_seconds': [0.0, expected / adapter.sr]},
                'scope': '既存表現時間操作の両端。局所音素境界の正解とは呼ばない。'}
            result['length_error_samples'] = result['audio']['samples'] - expected
        decode_result(adapter, edited, target, row, reference['samples'], finalize=finalize)
    except Exception:
        logging.exception('正式既存時間操作失敗')
        failure(target, row)
    finally:
        release(adapter, edited)
