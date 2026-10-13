"""既存方式比較の未調整・全長の保存出力を追加評価へ渡す。"""
from __future__ import annotations

import logging
from pathlib import Path

from .quality_core import read_json, resolve_path, sha256


def _name(value):
    if (not isinstance(value, str) or not value.strip() or value in ('.', '..')
            or '/' in value or '\\' in value):
        raise ValueError('既存方式比較のケース・方式IDは単純なファイル名にしてください')
    return value


def load_reference_run(directory):
    directory = Path(directory).resolve()
    source_paths = {name: directory / name for name in ('results.json', 'contract.json', 'inputs.json')}
    report, contract, saved = (read_json(source_paths[name]) for name in source_paths)
    source_hashes = {str(path): sha256(path) for path in source_paths.values()}
    if report.get('schema_version') != 5 or report.get('contract') != contract:
        raise ValueError('既存方式比較のschema_version=5と一致するcontract.jsonが必要です')
    methods = [_name(method) for method in report['selected_methods']]
    if not methods or len(set(methods)) != len(methods) or 'identity' in methods:
        raise ValueError('selected_methodsが空・重複・原音を含んでいます')
    if contract['methods'] != methods:
        raise ValueError('選択方式と元の契約が一致しません')
    baseline = report['comparison_reference']
    if baseline not in methods:
        raise ValueError('保存された比較基準がselected_methodsにありません')
    originals = {_name(item['id']): item for item in saved}
    if len(originals) != len(saved):
        raise ValueError('inputs.jsonのケースIDが重複しています')
    cases, ids = [], set()
    for metadata in contract['inputs']:
        identifier = _name(metadata['id'])
        if identifier in ids:
            raise ValueError('元の契約のケースIDが重複しています')
        ids.add(identifier)
        original = originals.get(identifier, {})
        # 保存先の移設は許すが、記録された入力hashは評価時に必ず照合する。
        local = directory / 'inputs' / f'{identifier}.npy'
        reference = local if local.exists() or not original.get('path') else resolve_path(directory, original['path'])
        case = {key: metadata.get(key) for key in ('language', 'style', 'speaker')}
        case.update(id=identifier, kind='natural_speech', reference=str(reference),
                    sample_rate=metadata['sample_rate'], reference_sha256=original.get('sha256'),
                    reference_source=metadata, original_record=original, outputs={},
                    output_sample_rates={}, output_sha256={}, upstream_status={}, upstream_records={})
        if not original or not original.get('sha256') or original.get('sample_rate') != metadata['sample_rate']:
            case['reference_error'] = 'inputs.jsonの入力hash・サンプルレートが欠落、または契約と不一致です'
        for method in methods:
            path = directory / 'native' / method / f'{identifier}.json'
            record = {'status': 'pending', 'reason': '元のネイティブ出力記録がありません'}
            if path.exists():
                source_hashes[str(path)] = None
                try:
                    source_hashes[str(path)] = sha256(path)
                    record = read_json(path)
                    if not isinstance(record.get('status'), str) or not record['status']:
                        raise ValueError('ネイティブ出力記録に状態がありません')
                    if record.get('case') != identifier or record.get('method') != method:
                        raise ValueError('ネイティブ出力記録のケース・方式IDが不一致です')
                    if record.get('status') == 'measured' and (
                            not record.get('output_sha256') or not record.get('native_sample_rate')):
                        raise ValueError('測定済みネイティブ出力にhash・サンプルレートがありません')
                except Exception as error:
                    logging.exception('保存出力記録を読み込めません: %s', path)
                    record = {'status': 'failed', 'reason': f'{type(error).__name__}: {error}'}
            case['outputs'][method] = str(path.with_suffix('.npy'))
            case['output_sample_rates'][method] = record.get('native_sample_rate')
            case['output_sha256'][method] = record.get('output_sha256')
            case['upstream_status'][method] = record['status']
            case['upstream_records'][method] = record
        cases.append(case)
    if not cases or set(originals) - ids:
        raise ValueError('元の契約とinputs.jsonのケース集合が不正です')
    return {'baseline': baseline, 'formal_base': report.get('formal_base'), 'cases': cases,
            'comparison_reference': baseline, 'study_role': report.get('study_role'),
            'source': str(source_paths['results.json']), 'source_sha256': source_hashes[str(source_paths['results.json'])],
            'source_files_sha256': source_hashes,
            'source_contract': contract, 'source_execution': report.get('execution'),
            'original_report': str(directory / 'index.html'),
            'interpretation': '保存されたネイティブ全長出力への追加評価。再標本化・切り詰め・整列なし。元の比較・採否は変更しない。'}
