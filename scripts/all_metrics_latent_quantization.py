"""混合精度payloadの実保存・復元と対応する無編集/操作波形の正式測定。"""
from __future__ import annotations

import logging

from all_metrics_common import read
from all_metrics_latent_io import (
    array_hashes, base_row, decode_result, failure, pending, read_payload, release, save_payload,
)
from all_metrics_latent_provenance import evidence as keep_evidence, release_payload, structure_hash
from vocoderbench.quality_core import sha256


def quantize_case(adapter, z, source, spec, args, signature, folder):
    native = read(folder / 'unedited.json')
    native_samples = (spec['samples'] * adapter.sr + spec['sample_rate'] - 1) // spec['sample_rate']
    native_hashes = array_hashes(adapter, z)
    arrays, structure = adapter.export_arrays(z)
    for dtype in ('float16', 'float32'):
        condition = 'quantized_' + dtype
        names = [condition] + [condition + '__' + name for name in adapter.capabilities]
        targets = [folder / f'{name}.json' for name in names]
        todo = [pending(path, signature, args.retry_failed) for path in targets]
        if not any(todo):
            old = read(targets[0])
            if old.get('feature_artifact'):
                release_payload(old['feature_artifact'], targets, args, spec,
                    '中断再開時、量子化点の全条件が既にterminal保存済みであるため一時payloadを解放。')
            continue
        restored, payload = None, None
        row = base_row(spec, args, signature, condition, source)
        try:
            q_arrays, q_structure = adapter.quantize_arrays(arrays, structure, dtype)
            path = folder / f'{condition}.npz'
            if path.exists() and targets[0].exists() and read(targets[0]).get('feature_artifact'):
                payload = read(targets[0])['feature_artifact']
                if sha256(path) != payload['sha256']:
                    raise ValueError('保存済み量子化payloadのhashが不一致')
            else:
                payload = save_payload(q_arrays, q_structure, path)
            stored_arrays, stored_structure = read_payload(path)
            restored = adapter.import_arrays(stored_arrays, stored_structure)
            payload = {key: value for key, value in payload.items()
                       if key not in ('released_at_utc', 'release_reason', 'release_record_path')}
            payload['retained'] = False
            restored_hashes = array_hashes(adapter, restored)
            equal = native_hashes == restored_hashes
            evidence = {'nominal_storage_dtype': dtype, 'mixed_precision': True,
                'native_decoder_arrays': native_hashes, 'restored_decoder_arrays': restored_hashes,
                'restored_decoder_input_identical': equal,
                'payload_file_bytes': payload['bytes'],
                'payload_bits_per_source_second': payload['bytes'] * 8 / (spec['samples'] / spec['sample_rate']),
                'payload_bits_per_native_output_second': payload['bytes'] * 8 / native['audio']['seconds'],
                'shared_asset_manifest': str(args.output_root / 'latent-contracts' / args.method / 'shared-assets.json'),
                'shared_asset_manifest_sha256': sha256(args.output_root / 'latent-contracts' / args.method / 'shared-assets.json'),
                'scope': '指定fieldの保存精度摂動。全配列16bitではない。発話payloadと固定共有資産を分離。'}
            provenance = keep_evidence(args, spec, condition, {
                'contract_sha256': signature, 'seed': args.seed, 'native_representation_sha256': source['sha256'],
                'quantization': evidence, 'actual_payload': payload,
                'stored_structure_sha256': structure_hash(stored_structure),
                'measurement_order': 'actual NPZ write, close, read, import, canonical hash, then official decodes',
                'retention_policy': 'temporary payload, released after all point conditions reach a terminal saved outcome'})
            for edit_name, target, active in zip(['unedited', *adapter.capabilities], targets, todo):
                if not active:
                    continue
                edited = None
                row = base_row(spec, args, signature, target.stem, source,
                    adapter.capabilities.get(edit_name, {}))
                row.update(feature_artifact=payload, quantization=evidence, provenance=provenance,
                    representation_operation={'payload': str(path), 'control_after_import': edit_name})
                try:
                    edited = restored if edit_name == 'unedited' else adapter.edit(restored, edit_name)
                    reuse = folder / f'{edit_name}.json' if equal else None
                    if reuse is not None and (not reuse.exists() or read(reuse).get('status') != 'measured'):
                        reuse = None
                    if hasattr(adapter, 'frame_times'):
                        row['parameter_frame_times'] = {
                            'reference_seconds': adapter.frame_times(restored).tolist(),
                            'output_seconds': adapter.frame_times(edited).tolist(),
                            'scope': '量子化後の基準と操作後の対応native epoch間のみ。波形両端の挿入・外挿・全長への再正規化なし。'}
                    decode_result(adapter, edited, target, row, native_samples, reuse=reuse)
                except Exception:
                    logging.exception('量子化条件の正式復号失敗')
                    failure(target, row)
                finally:
                    if edited is not restored:
                        release(adapter, edited)
        except Exception:
            logging.exception('正式量子化payload保存・復元失敗: %s %s %s', args.method, spec['id'], dtype)
            for target, active in zip(targets, todo):
                if active:
                    edit_name = target.stem.split('__', 1)[-1]
                    row = base_row(spec, args, signature, target.stem, source,
                        adapter.capabilities.get(edit_name, {}))
                    row.update(nominal_storage_dtype=dtype, mixed_precision=True,
                               failure_stage='quantize_save_restore', feature_artifact=payload)
                    failure(target, row)
        finally:
            release(adapter, restored)
            if payload is not None and all(target.exists() for target in targets):
                release_payload(payload, targets, args, spec,
                    '量子化点の実保存・読戻し・復元と全対応復号条件がterminal保存済み。元表現と永久測定証跡を保持。')
