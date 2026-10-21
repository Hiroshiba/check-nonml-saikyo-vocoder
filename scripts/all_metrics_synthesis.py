"""全8方式研究のnative再合成・既存表現操作を10録音単位で逐次保存する。"""
from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import logging
import math
import os
from pathlib import Path
import platform
import random
import sys
import time
import traceback

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import torch

from all_metrics_common import ROOT, RUN, freeze, now, read, save_audio
from vocoderbench.quality_core import sha256, write_json
from vocoderbench.references.common import verify_prepared
from vocoderbench.logging_utils import run_cli

ADAPTER_SOURCES = ('all_metrics_control_adapters.py', 'all_metrics_representation.py',
    'all_metrics_neural_controls.py', 'all_metrics_golf_control.py', 'all_metrics_llsm_storage.py',
    'all_metrics_llsm_control.py', 'all_metrics_storage_policy.py', 'all_metrics_interpolation.py')


def conditions(adapter, args):
    names = [] if args.encode_only or args.edits_only else ['unedited']
    if not args.encode_only and not args.unedited_only:
        names += list(adapter.capabilities)
    return names


def completed(folder, names, signature, waveform_only=False):
    for name in names:
        path = folder / f'{name}.json'
        if not path.exists() or read(path).get('status') != 'measured':
            return False
        previous = read(path)
        if previous.get('contract_sha256') != signature or sha256(path.with_suffix('.npy')) != previous['audio']['file_sha256']:
            raise ValueError('成功済み合成の条件または波形hashが変わりました')
    if waveform_only:
        return True
    for name, suffix in (('representation', '.npz'), ('features', '.npy')):
        path = folder / f'{name}.json'
        if not path.exists() or read(path).get('status') != 'measured':
            return False
        previous = read(path)
        if previous.get('contract_sha256') != signature or sha256(folder / (name + suffix)) != previous['sha256']:
            raise ValueError('保存成功済みの表現または特徴hashが変わりました')
    return True


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    ctypes.CDLL(None).srand(ctypes.c_uint(seed))


def to_wave(value):
    if hasattr(value, 'as_tensor'):
        value = value.as_tensor()
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=np.float64).reshape(-1)


def save_representation(adapter, z, path):
    arrays, structure = adapter.export_arrays(z)
    if any(not isinstance(value, np.ndarray) or value.dtype.kind == 'O' for value in arrays.values()):
        raise ValueError('表現はpickleを必要としない明示数値配列が必要です')
    import json
    combined = dict(arrays)
    if '__structure_json__' in combined:
        raise ValueError('予約した表現キーが衝突しています')
    combined['__structure_json__'] = np.array(json.dumps(structure, ensure_ascii=False, sort_keys=True))
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **combined)
    temporary.replace(path)
    return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'array_count': len(arrays), 'uncompressed_array_bytes': sum(value.nbytes for value in arrays.values()),
            'structure_location': '__structure_json__ inside this actual retained NPZ',
            'array_schema_location': 'native dtype/shape metadata inside this actual retained NPZ',
            'storage_scope': '発話ごとの復号入力payload。NPZヘッダーと構造JSON込み。固定共有decoder/modelは別途必要。',
            'encoding': 'numpy.savez_compressed with structure metadata; no pickle'}


def restore_representation(adapter, path):
    import json
    with np.load(path, allow_pickle=False) as archive:
        structure = json.loads(str(archive['__structure_json__']))
        arrays = {key: archive[key] for key in archive if key != '__structure_json__'}
    return adapter.import_arrays(arrays, structure)


def save_native_representation(adapter, z, path, method):
    """HNM/WORLDは既存native容器、他方式は明示decoder-input容器へ保存する。"""
    if method not in ('hnm', 'world_harvest'):
        return save_representation(adapter, z, path)
    if method == 'hnm':
        raise ValueError('旧HNM再計算はbbab81fをcheckoutしてください')
    from vocoderbench import world
    module = world
    temporary = path.with_suffix('.part')
    module.save(z, temporary)
    temporary.replace(path)
    return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'encoding': f'vocoderbench.{"hnm" if method == "hnm" else "world"}.save native NPZ',
            'format': 'native_hnm_world_npz',
            'decoder_input_source': 'native NPZ; reloaded parameters supply subsequent formal operations',
            'storage_scope': '既存native発話容器の実量。構造metadata込み、共有decoder/runtimeは別。'}


def native_input(spec, adapter, method, folder):
    if sha256(spec['path']) != spec['sha256']:
        raise ValueError('固定入力NPYのhashが一致しません')
    wave = np.load(spec['path'], allow_pickle=False).astype(np.float64)
    if wave.ndim != 1 or not np.isfinite(wave).all():
        raise ValueError('入力は有限なモノラル波形にしてください')
    divisor = math.gcd(spec['sample_rate'], adapter.sr)
    if spec['sample_rate'] != adapter.sr:
        wave = resample_poly(wave, adapter.sr // divisor, spec['sample_rate'] // divisor,
                             window=('kaiser', 5.0), padtype='constant')
    wav = folder / 'input.wav'
    quantization = 'none'
    if method == 'magphase':
        if np.max(np.abs(wave)) > 1:
            raise ValueError('MagPhase PCM16入力が範囲外です。clipしません')
        sf.write(wav, wave, adapter.sr, subtype='PCM_16')
        wave, actual_sr = sf.read(wav, dtype='float64')
        if actual_sr != adapter.sr:
            raise ValueError('MagPhase入力SR不一致')
        quantization = 'PCM16 (official file API)'
    import hashlib
    return wave, wav, {'source_sha256': spec['sha256'], 'source_samples': spec['samples'],
        'source_sample_rate': spec['sample_rate'], 'native_samples': len(wave), 'native_sample_rate': adapter.sr,
        'native_input_float64_sha256': hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest(),
        'resampling': {'up': adapter.sr // divisor, 'down': spec['sample_rate'] // divisor,
                       'function': 'scipy.signal.resample_poly', 'window': ['kaiser', 5.0], 'padtype': 'constant'},
        'input_quantization': quantization}


def case_run(adapter, spec, args, signature):
    folder = args.output_root / 'native' / args.method / spec['id']
    folder.mkdir(parents=True, exist_ok=True)
    condition_names = conditions(adapter, args)
    if completed(folder, condition_names, signature, args.waveform_only or args.edits_only):
        logging.info('保存済み全条件を再利用: %s %s', args.method, spec['id'])
        return
    if not args.retry_failed and any((folder / f'{name}.json').exists()
            and read(folder / f'{name}.json').get('status') == 'failed' for name in condition_names):
        logging.info('既存失敗を保持（明示retryなし）: %s %s', args.method, spec['id'])
        return
    feature_record = folder / 'features.json'
    if not args.edits_only and feature_record.exists() and read(feature_record).get('status') != 'measured':
        if not args.retry_failed:
            return
        write_json(folder / 'failure_history' / f'features-{time.time_ns()}.json', read(feature_record))
    z = None
    row = {'case': spec['id'], 'method': args.method, 'started_at_utc': now(), 'contract_sha256': signature}
    try:
        native_record, payload_record = folder / 'unedited.json', folder / 'representation.json'
        saved_native = (native_record.exists() and read(native_record).get('status') == 'measured')
        if args.edits_only or saved_native:
            native, representation = read(native_record), read(payload_record)
            if not completed(folder, ['unedited'], signature, True):
                raise ValueError('編集は成功した同一契約のnative波形を必要とします')
            if (representation.get('status') != 'measured' or representation['contract_sha256'] != signature
                    or sha256(folder / 'representation.npz') != representation['sha256']):
                raise ValueError('編集元native表現の保存契約/hashが一致しません')
            load_started = time.perf_counter()
            z = (adapter.load_native(folder / 'representation.npz') if args.method in ('hnm', 'world_harvest')
                 else restore_representation(adapter, folder / 'representation.npz'))
            row.update(representation_load_seconds=time.perf_counter() - load_started, input=native['input'],
                       analysis_origin='saved native; no new encode',
                       native_record_sha256=sha256(native_record), representation_record_sha256=sha256(payload_record))
            input_info = native['input']
        else:
            seed_all(args.seed)
            input_started = time.perf_counter()
            wave, wav, input_info = native_input(spec, adapter, args.method, folder)
            row['input_preprocessing_seconds'] = time.perf_counter() - input_started
            start, cpu = time.perf_counter(), time.process_time()
            with torch.inference_mode():
                z = adapter.encode(wave, wav)
            row.update(analysis_seconds=time.perf_counter() - start,
                       analysis_process_cpu_seconds=time.process_time() - cpu, input=input_info)
        if not args.waveform_only and not args.edits_only and not saved_native:
            storage_started = time.perf_counter()
            representation = save_native_representation(adapter, z, folder / 'representation.npz', args.method)
            row['representation_save_seconds'] = time.perf_counter() - storage_started
            load_started = time.perf_counter()
            loaded = (adapter.load_native(folder / 'representation.npz') if args.method in ('hnm', 'world_harvest')
                      else restore_representation(adapter, folder / 'representation.npz'))
            original, z = z, loaded
            if original is not z and hasattr(adapter, 'release'):
                adapter.release(original)
            row['representation_load_seconds'] = time.perf_counter() - load_started
            representation['decoder_input_source'] = 'actual saved-and-reloaded NPZ supplies the sole formal decode'
            write_json(folder / 'representation.json', {**representation, **row, 'status': 'measured',
                                                         'adapter_info': adapter.info})
        try:
            if args.waveform_only or args.edits_only:
                raise StopIteration
            features, schema = adapter.readout_features(z)
            features = np.asarray(features, dtype=np.float32)
            if features.ndim != 2 or not np.isfinite(features).all():
                raise ValueError('読み出し特徴は有限なframe×dimension行列が必要です')
            np.save(folder / 'features.npy', features, allow_pickle=False)
            write_json(folder / 'features.json', {'case': spec['id'], 'method': args.method, 'schema': schema,
                'status': 'measured', 'sha256': sha256(folder / 'features.npy'), 'shape': list(features.shape),
                'representation_sha256': representation['sha256'], 'contract_sha256': signature})
        except StopIteration:
            pass
        except Exception:
            logging.exception('読み出し特徴の保存失敗、正式native表現からの再合成は続行: %s %s', args.method, spec['id'])
            write_json(folder / 'features.json', {**row, 'status': 'failed', 'error': traceback.format_exc()})
        for condition in condition_names:
            target = folder / f'{condition}.json'
            if target.exists():
                previous = read(target)
                if previous.get('status') == 'measured':
                    if previous.get('contract_sha256') != signature or sha256(target.with_suffix('.npy')) != previous['audio']['file_sha256']:
                        raise ValueError('保存済み成功の再開条件が変わりました')
                    continue
                if not args.retry_failed:
                    continue
                write_json(folder / 'failure_history' / f'{condition}-{time.time_ns()}.json', previous)
            result = {**row, 'condition': condition, 'status': 'failed', 'seed': args.seed,
                      'controls': adapter.capabilities.get(condition, {}), 'origin': 'new_inference'}
            edited = None
            try:
                if condition == 'unedited':
                    edited = z
                else:
                    edit_started = time.perf_counter()
                    edited = adapter.edit(z, condition)
                    result['edit_seconds'] = time.perf_counter() - edit_started
                    storage_started = time.perf_counter()
                    result['feature_artifact'] = save_representation(adapter, edited, folder / f'{condition}.npz')
                    result['edited_representation_save_seconds'] = time.perf_counter() - storage_started
                seed_all(args.seed)
                start, cpu = time.perf_counter(), time.process_time()
                with torch.inference_mode():
                    output = to_wave(adapter.decode(edited))
                result.update(synthesis_seconds=time.perf_counter() - start,
                              synthesis_process_cpu_seconds=time.process_time() - cpu)
                if not len(output) or not np.isfinite(output).all() or np.max(np.abs(output)) < 1e-10:
                    raise ValueError('合成音声が空・非有限・無音です')
                save_started = time.perf_counter()
                audio = save_audio(folder / f'{condition}.npy', output, adapter.sr, exact_float32=True)
                result['output_storage_seconds'] = time.perf_counter() - save_started
                result.update(status='measured', audio=audio,
                              length_delta_native_samples=len(output) - input_info['native_samples'], finished_at_utc=now())
                if hasattr(adapter, 'frame_times'):
                    result['parameter_frame_times'] = {
                        'reference_seconds': np.asarray(adapter.frame_times(z), dtype=float).tolist(),
                        'output_seconds': np.asarray(adapter.frame_times(edited), dtype=float).tolist(),
                        'scope': '対応するnative epoch間だけの写像。実波形両端の挿入・外挿・全長への再正規化はしない。'}
            except Exception:
                logging.exception('正式条件の合成失敗: %s %s %s', args.method, spec['id'], condition)
                result.update(error=traceback.format_exc(), finished_at_utc=now())
            finally:
                if edited is not None and edited is not z and hasattr(adapter, 'release'):
                    adapter.release(edited)
            write_json(target, result)
            logging.info('正式合成: %s %s %s %s', args.method, spec['id'], condition, result['status'])
        write_json(folder / 'case-progress.json', {**row, 'finished_at_utc': now(),
            'execution_mode': 'edits_only' if args.edits_only else 'encode_only' if args.encode_only
                              else 'unedited_only' if args.unedited_only else 'all_conditions',
            'conditions': {name: read(folder / f'{name}.json')['status'] for name in condition_names}})
    except Exception:
        logging.exception('正式解析・表現保存失敗: %s %s', args.method, spec['id'])
        failure = {**row, 'status': 'failed', 'error': traceback.format_exc(), 'finished_at_utc': now()}
        write_json(folder / 'case-progress.json', failure)
        if not args.waveform_only and not args.edits_only:
            for name in ('representation', 'features'):
                target = folder / f'{name}.json'
                previous = read(target) if target.exists() else None
                if previous and (previous.get('status') == 'measured' or not args.retry_failed):
                    continue
                if previous:
                    write_json(folder / 'failure_history' / f'{name}-{time.time_ns()}.json', previous)
                write_json(target, {**failure, 'failure_stage': 'native_input_or_representation'})
        for condition in condition_names:
            target = folder / f'{condition}.json'
            previous = read(target) if target.exists() else None
            if previous and (previous.get('status') == 'measured' or not args.retry_failed):
                continue
            if previous:
                write_json(folder / 'failure_history' / f'{condition}-{time.time_ns()}.json', previous)
            write_json(target, {**failure, 'condition': condition, 'failure_stage': 'native_input_or_representation'})
    finally:
        if z is not None and hasattr(adapter, 'release'):
            adapter.release(z)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--runtime-cache', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, default=RUN)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--retry-failed', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--encode-only', action='store_true', help='独立学習群の表現抽出だけを保存')
    mode.add_argument('--unedited-only', action='store_true', help='無編集native再合成を編集と分けて保存')
    mode.add_argument('--edits-only', action='store_true', help='保存したnative表現から編集のみ復号、再解析しない')
    parser.add_argument('--waveform-only', action='store_true', help='品質専用補助集合では表現・特徴ファイルを省く')
    args = parser.parse_args()
    if args.edits_only and args.waveform_only:
        parser.error('--edits-only requires a retained native representation')
    inputs = read(args.inputs)
    if not 1 <= len(inputs) <= 10:
        raise ValueError('正式処理は1〜10録音の固定小batchに限定します')
    sys.path.insert(0, str(ROOT))
    from scripts.all_metrics_control_adapters import build_control_adapter
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    prepared = (verify_prepared(args.runtime_cache, args.method) if args.method not in ('hnm', 'world_harvest')
                else {'method': args.method, 'formal_base': read(ROOT / 'BASELINE.json'),
                      'world_lock_sha256': sha256(ROOT / 'vocoderbench/world.lock.json')})
    seed_all(args.seed)
    start = time.perf_counter()
    adapter = build_control_adapter(args.method, args.runtime_cache / 'src',
                                    args.runtime_cache / 'models', args.output_root / 'adapter-work' / args.method)
    initialization = time.perf_counter() - start
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py',
             *(ROOT / 'scripts' / name for name in ADAPTER_SOURCES),
             *sorted((ROOT / 'vocoderbench/references').glob('adapters_*.py'))]
    if args.method in ('hnm', 'world_harvest'):
        paths += [ROOT / 'scripts/all_metrics_base_controls.py', ROOT / 'vocoderbench/world.py',
                  *sorted((ROOT / 'vocoderbench').glob('hnm*.py'))]
    contract = {'schema_version': 1, 'method': args.method, 'prepared': prepared,
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        'input_contract_sha256': sha256(args.output_root / 'input-contract.json'),
        'threads': args.threads, 'seed': args.seed, 'capabilities': adapter.capabilities,
        'encode_only': args.encode_only, 'waveform_only': args.waveform_only,
        'available_conditions': [] if args.encode_only else ['unedited', *adapter.capabilities],
        'native_sample_rate': adapter.sr, 'adapter_info': adapter.info,
        'runtime': {'python': sys.version, 'platform': platform.platform(),
                    'packages': {p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'torch', 'soundfile')}},
        'waveform_postprocessing': 'none', 'analysis_reuse': 'one encode, then independent parameter edits',
        'waveform_storage': 'float32 NPY only when float64→float32→float64 is elementwise exact; else float64. PCM is unchanged.',
        'native_payload_storage': 'HNM/WORLD existing module.save container; other six numeric tree NPZ. All eight formal decodes use actual saved-and-reloaded inputs. Derived payloads use numeric tree NPZ.',
        'timing_definition': {'analysis': 'adapter.encode only', 'synthesis': 'one condition adapter.decode plus tensor-to-NumPy conversion',
            'codec_rtf_denominator': 'original input samples / original input sample rate',
            'separate': ['initialization', 'input preprocessing', 'representation save/load', 'output storage', 'edited decodes'],
            'native_comparison': 'Only the predeclared single-worker native phase; shared-host timing remains descriptive.'},
        'randomness': 'seed before encode; reset to the same explicit seed immediately before every unedited/edited decode'}
    contract_path = args.output_root / 'synthesis-contracts' / f'{args.method}.json'
    freeze(contract_path, contract)
    signature = sha256(contract_path)
    write_json(args.output_root / 'synthesis-initializations' / f'{args.method}-{time.time_ns()}.json',
               {'started_at_utc': now(), 'seconds': initialization, 'inputs': str(args.inputs),
                'input_manifest_sha256': sha256(args.inputs), 'contract_sha256': signature,
                'requested_conditions': conditions(adapter, args), 'edits_only': args.edits_only})
    for spec in inputs:
        case_run(adapter, spec, args, signature)
    return int(any(not completed(args.output_root / 'native' / args.method / spec['id'],
                                 conditions(adapter, args), signature, args.waveform_only or args.edits_only)
                   for spec in inputs))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-synthesis'))
