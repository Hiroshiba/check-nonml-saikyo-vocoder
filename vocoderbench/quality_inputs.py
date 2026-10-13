"""任意方式の音声一覧と、既存固定比較の保存波形を読み込む。"""
from __future__ import annotations

from pathlib import Path

from .quality_core import check_output, check_pair, load_audio, read_json, resolve_path, sha256


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
            'interpretation': '指定した保存音声の追加評価。編集点は非参照MOS・固定参照の話者類似度の適用条件内で使う。参照距離を編集罰則にせず、方式の選定・採否は行わない。'}


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


def evaluation_audio(case, method, filename, metric, row, hashes):
    def load(path, rate, key, expected):
        wave, sr, info = load_audio(path, rate)
        row[key] = info
        previous = hashes.setdefault(info['path'], info['file_sha256'])
        if previous != info['file_sha256']:
            raise ValueError('計測中に入力ファイルが変更されました')
        if expected is not None and info['file_sha256'] != expected:
            raise ValueError('保存元の音声hashと追加評価入力が一致しません')
        return wave, sr, info

    is_original = method == 'identity'
    if case.get('reference_error') and (is_original or metric != 'utmosv2'):
        raise ValueError(case['reference_error'])
    expected = case.get('reference_sha256') if is_original else case.get('output_sha256', {}).get(method)
    rate = case.get('output_sample_rates', {}).get(method, case.get('sample_rate'))
    y, output_sr, output_info = load(filename, rate, 'output', expected)
    if metric == 'utmosv2':
        # 非参照MOSは参照音を読まず、出力固有の全長・帯域で測る。自己差分ではない。
        if is_original:
            expected_pcm = case.get('reference_source', {}).get('pcm_sha256')
            if expected_pcm is not None and output_info['pcm_float64_sha256'] != expected_pcm:
                raise ValueError('原音PCMのhashが元の契約と一致しません')
        check_output(y, output_sr)
        row['reference_used'] = False
        return None, y, output_sr
    x, reference_sr, reference_info = load(case['reference'], case.get('sample_rate'),
                                           'reference', case.get('reference_sha256'))
    expected_pcm = case.get('reference_source', {}).get('pcm_sha256')
    if expected_pcm is not None and reference_info['pcm_float64_sha256'] != expected_pcm:
        raise ValueError('原音PCMのhashが元の契約と一致しません')
    if output_sr != reference_sr:
        raise ValueError('入出力のサンプルレートが一致しません')
    check_pair(x, y, reference_sr)
    row['reference_used'] = True
    return x, y, reference_sr
