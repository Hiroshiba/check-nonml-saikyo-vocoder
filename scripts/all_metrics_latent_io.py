"""正式表現研究の実ファイル保存・hash照合・既存波形引用。"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import traceback

import numpy as np
import torch

from all_metrics_common import ROOT, audio_info, link_existing, now, read
from all_metrics_synthesis import restore_representation, seed_all, to_wave
from all_metrics_latent_provenance import verify_retained_evidence
from vocoderbench.quality_core import sha256, write_json


def array_hashes(adapter, z):
    arrays, structure = adapter.export_arrays(z)
    record = {'tree': structure['tree'], 'parameter_metadata': structure.get('parameter_metadata'),
              'arrays': {key: {'dtype': value.dtype.str, 'shape': list(value.shape),
                  'sha256': hashlib.sha256(value.tobytes(order='C')).hexdigest()}
                  for key, value in arrays.items()}}
    return {'sha256': hashlib.sha256(json.dumps(record, sort_keys=True,
                ensure_ascii=False).encode()).hexdigest(), 'array_count': len(arrays),
            'algorithm': 'SHA256(sorted JSON(tree, parameter_metadata, per-array dtype/shape/C-order SHA256))'}


def read_payload(path):
    with np.load(path, allow_pickle=False) as data:
        structure = json.loads(str(data['__structure_json__']))
        arrays = {key: data[key] for key in data if key != '__structure_json__'}
    return arrays, structure


def save_payload(arrays, structure, path):
    if '__structure_json__' in arrays or any(value.dtype.kind == 'O' for value in arrays.values()):
        raise ValueError('payloadは予約キーなし・pickle不要の数値配列に限定します')
    content = dict(arrays, __structure_json__=np.array(json.dumps(structure, ensure_ascii=False, sort_keys=True)))
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **content)
    temporary.replace(path)
    return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'array_count': len(arrays), 'uncompressed_array_bytes': sum(a.nbytes for a in arrays.values()),
            'structure_location': '__structure_json__ member inside the actual NPZ',
            'encoding': 'numpy.savez_compressed; numeric arrays + structure JSON',
            'storage_scope': '発話payload。構造JSON・NPZヘッダー込み。固定共有decoder/modelとruntimeは別。'}


def release(adapter, z):
    if z is not None and hasattr(adapter, 'release'):
        adapter.release(z)


def native_representation(adapter, folder, method):
    record = read(folder / 'representation.json')
    path = folder / 'representation.npz'
    if sha256(path) != record['sha256']:
        raise ValueError('既存native表現のhash不一致')
    if method in ('hnm', 'world_harvest'):
        z = adapter.load_native(path)
    else:
        z = restore_representation(adapter, path)
    return z, {'path': str(path), 'sha256': record['sha256'],
               'record_sha256': sha256(folder / 'representation.json')}


def pending(target, signature, retry=False):
    if not target.exists():
        return True
    row = read(target)
    if row['contract_sha256'] != signature:
        raise ValueError(f'既存表現研究の契約が不一致: {target}')
    if row['status'] in ('measured', 'not_applicable'):
        if row['status'] == 'measured':
            if sha256(target.with_suffix('.npy')) != row['audio']['file_sha256']:
                raise ValueError(f'保存済み波形hash不一致: {target}')
            verify_retained_evidence(row)
        return False
    if retry:
        write_json(target.parent / 'failure_history' / f'{target.stem}-{time.time_ns()}.json', row)
    return retry


def base_row(spec, args, signature, condition, source, controls=None):
    return {'case': spec['id'], 'speaker': spec['speaker'], 'method': args.method,
            'condition': condition, 'status': 'failed', 'started_at_utc': now(),
            'seed': args.seed, 'contract_sha256': signature,
            'input_source_sha256': spec['sha256'], 'native_representation': source,
            'controls': controls or {}, 'origin': 'new_representation_inference'}


def failure(target, row, status='failed', error=None):
    row.update(status=status, error=error or traceback.format_exc(), finished_at_utc=now())
    write_json(target, row)
    logging.error('正式表現条件: %s %s %s %s\n%s', row['method'], row['case'],
                  row['condition'], status, row['error'])


def save_exact_wave(path, wave, sample_rate):
    """元decoderの値を変えず、厳密に可逆な場合だけfloat32 NPYにする。"""
    source = np.asarray(wave, dtype=np.float64)
    with np.errstate(over='ignore', invalid='ignore'):
        candidate = source.astype(np.float32)
    exact = np.array_equal(source, candidate.astype(np.float64))
    stored = candidate if exact else source
    temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream:
        np.save(stream, stored, allow_pickle=False)
    temporary.replace(path)
    info = audio_info(path, sample_rate)
    source_hash = hashlib.sha256(source.astype('<f8').tobytes()).hexdigest()
    if info['float64_sha256'] != source_hash:
        raise ValueError('元decoder出力から可逆保存したPCM hashが変わりました')
    info.update(stored_dtype=str(stored.dtype), float32_roundtrip_exact=exact,
                decoder_output_float64_sha256=source_hash,
                storage_rule='float64→float32→float64が要素完全一致の場合だけfloat32保存。そうでなければfloat64維持。')
    return info


def decode_result(adapter, z, target, row, native_samples, reuse=None, finalize=None):
    if reuse is not None:
        source = read(reuse)
        source_path = reuse.with_suffix('.npy')
        if source.get('status') != 'measured' or source['audio']['sample_rate'] != adapter.sr:
            raise ValueError('引用元の波形は成功済みでなければなりません')
        link_existing(source_path, target.with_suffix('.npy'), source['audio']['file_sha256'])
        info = audio_info(target.with_suffix('.npy'), adapter.sr)
        info['stored_dtype'] = str(np.load(target.with_suffix('.npy'), mmap_mode='r', allow_pickle=False).dtype)
        info['storage_rule'] = 'unmodified existing waveform alias'
        row.update(origin='existing_verified_waveform_identical_decoder_input',
                   reused_waveform_record=str(reuse), reused_waveform_record_sha256=sha256(reuse),
                   new_inference_seconds=0.0, synthesis_seconds=0.0,
                   reuse_rule='復号入力配列・型・構造・設定のhashが同一。自己復号比較を実行していない。')
    else:
        seed_all(row['seed'])
        started, cpu = time.perf_counter(), time.process_time()
        with torch.inference_mode():
            wave = to_wave(adapter.decode(z))
        row.update(synthesis_seconds=time.perf_counter() - started,
                   synthesis_process_cpu_seconds=time.process_time() - cpu)
        if not len(wave) or not np.isfinite(wave).all() or np.max(np.abs(wave)) < 1e-10:
            raise ValueError('復号波形が空・非有限・無音です')
        info = save_exact_wave(target.with_suffix('.npy'), wave, adapter.sr)
    row.update(status='measured', audio=info, finished_at_utc=now(),
               length_delta_native_samples=info['samples'] - native_samples)
    if finalize is not None:
        finalize(row)
    write_json(target, row)
    logging.info('正式表現条件: %s %s %s measured', row['method'], row['case'], row['condition'])


def shared_assets(adapter, args):
    declared = adapter.info['representation_contract'].get('shared_decoder_assets', {})
    records = []
    for name, expected in declared.items():
        if name == 'native_world_library':
            from vocoderbench import world
            path = world.library_path()
        else:
            path = (ROOT if args.method in ('hnm', 'world_harvest') else args.runtime_cache) / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f'固定共有資産hash不一致: {name}')
        records.append({'name': name, 'sha256': expected, 'bytes': path.stat().st_size})
    return {'files': records, 'total_declared_file_bytes': sum(r['bytes'] for r in records),
            'scope': 'adapterが宣言した固定ソース・model・設定等の共有資産。OS/runtime依存の全bundle容量ではない。',
            'payload_alone_is_self_contained_bitrate': False}
