"""任意方式の音声一覧と、既存固定比較の保存波形を読み込む。"""
from __future__ import annotations

from pathlib import Path

from .quality_core import read_json, resolve_path, sha256


def _identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('ケース・方式IDは空でない文字列にしてください')
    return value


def load_manifest(path):
    path = Path(path).resolve()
    data = read_json(path)
    if data.get('schema_version') != 1:
        raise ValueError('音声一覧のschema_versionは1です')
    baseline = _identifier(data['baseline'])
    cases = data['cases']
    if not isinstance(cases, list) or not cases:
        raise ValueError('音声一覧に1件以上のcasesが必要です')
    ids = set()
    for case in cases:
        identifier = _identifier(case['id'])
        if identifier in ids:
            raise ValueError(f'ケースIDが重複しています: {identifier}')
        ids.add(identifier)
        if case.get('kind') not in ('natural_speech', 'synthetic_speech', 'artificial_probe'):
            raise ValueError('各caseにnatural_speech / synthetic_speech / artificial_probeのkindを明示してください')
        outputs = case['outputs']
        if not isinstance(outputs, dict) or not outputs or baseline not in outputs or 'identity' in outputs:
            raise ValueError('outputsにはbaselineの音声を含め、予約ID identityは含めないでください')
        case['reference'] = str(resolve_path(path.parent, case['reference']))
        case['outputs'] = {_identifier(method): str(resolve_path(path.parent, filename))
                           for method, filename in outputs.items()}
    return {'baseline': baseline, 'cases': cases, 'source': str(path),
            'source_sha256': sha256(path), 'formal_base': data.get('formal_base'),
            'interpretation': '指定した無編集再合成の追加評価。方式の選定・採否は行わない。'}


def load_benchmark(directory):
    directory = Path(directory).resolve()
    path = directory / 'results.json'
    report = read_json(path)
    baseline = report['formal_base']['method']
    if baseline not in report['method_labels']:
        raise ValueError('保存されたベース方式がmethod_labelsにありません')
    cases = []
    statuses = {(r['case'], r['method']): r['status'] for r in report['resynthesis']}
    for metadata in report['cases']:
        identifier = metadata['id']
        folder = directory / 'waveforms' / identifier
        case = {key: metadata.get(key) for key in ('language', 'style', 'speaker')}
        case.update(id=identifier, kind='natural_speech', sample_rate=metadata.get('sr'),
                    reference=str(folder / 'identity.npy'),
                    outputs={method: str(folder / f'{method}.npy')
                             for method in report['method_labels'] if method != 'identity'},
                    upstream_status={method: statuses.get((identifier, method), 'pending')
                                     for method in report['method_labels'] if method != 'identity'})
        cases.append(case)
    if not cases:
        raise ValueError('固定比較レポートに音声がありません')
    return {'baseline': baseline, 'formal_base': report['formal_base'], 'cases': cases,
            'source': str(path), 'source_sha256': sha256(path),
            'original_report': str(directory / 'index.html'),
            'interpretation': '保存されたseed 0波形への追加測定。元の結果・採否は変更しない。'}
