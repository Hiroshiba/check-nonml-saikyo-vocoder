"""全方式の正式研究用: 既存復号器への表現保存・既存パラメータ操作入口。"""
from __future__ import annotations

import importlib
import json
import sys

from vocoderbench.references.common import digest
from vocoderbench.references.worker import BUILDERS

from scripts.all_metrics_representation import export_tree, import_tree


def _golf_with_key_audit(src, models, out):
    """The pinned upstream ignores strict=True; inspect its returned key lists."""
    sys.path.insert(0, str(src / 'golf'))
    from ltng.ae import VoiceAutoEncoder
    from vocoderbench.references.adapters_source import build_golf
    original = VoiceAutoEncoder.load_state_dict
    records = []

    def load_checked(self, state_dict, **kwargs):
        result = original(self, state_dict, **kwargs)
        record = {'missing_keys': list(result.missing_keys),
                  'unexpected_keys': list(result.unexpected_keys)}
        records.append(record)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'golf-checkpoint-key-audit.json').write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        if record['missing_keys'] or record['unexpected_keys']:
            raise ValueError(f'GOLF固定重みのキーが一致しません: {record}')
        return result

    VoiceAutoEncoder.load_state_dict = load_checked
    try:
        adapter = build_golf(src, models, out)
    finally:
        VoiceAutoEncoder.load_state_dict = original
    adapter.info['checkpoint_key_audit'] = records
    return adapter


def build_control_adapter(method, src, models, out):
    """Return the original adapter, augmented with the documented research API."""
    if method in ('hnm', 'world_harvest'):
        from scripts.all_metrics_base_controls import build_base_control_adapter
        return build_base_control_adapter(method, src, models, out)
    if method not in {'facodec', 'hifiglot', 'golf', 'sifigan', 'llsm2', 'magphase'}:
        raise ValueError(f'この入口は公開比較6方式専用です: {method}')
    out.mkdir(parents=True, exist_ok=True)
    if method == 'golf':
        adapter = _golf_with_key_audit(src, models, out)
    else:
        module, builder = BUILDERS[method]
        adapter = getattr(importlib.import_module('vocoderbench.references.' + module), builder)(
            src, models, out)
    adapter.export_arrays = export_tree
    adapter.import_arrays = import_tree
    adapter.capabilities = {}
    adapter.info['representation_contract'] = {
        'version': 1, 'method': method, 'serialization': 'numeric NPZ arrays + JSON structure',
        'decoder_input': True, 'external_decoder_assets_required': True,
        'payload_alone_is_self_contained_bitrate': False,
        'floating_storage_rounding': 'explicit float16/float32 storage, original dtype restored',
        'integer_fields_are_not_rounded': True,
        'missing_native_controls': [],
    }
    prepared = src.parent / 'prepared' / f'{method}.json'
    if prepared.exists():
        record = json.loads(prepared.read_text())
        adapter.info['representation_contract'].update(
            prepared_record_sha256=digest(prepared),
            shared_decoder_assets=record['files'], sources=record['sources'])
    if method == 'llsm2':
        from scripts.all_metrics_llsm_control import augment_llsm
        augment_llsm(adapter, src)
    else:
        from scripts.all_metrics_neural_controls import augment
        augment(adapter, method, src)
    from scripts.all_metrics_storage_policy import attach_storage_policy
    attach_storage_policy(adapter, method)
    from scripts.all_metrics_interpolation import attach_interpolation
    attach_interpolation(adapter, method)
    return adapter


build = build_control_adapter
