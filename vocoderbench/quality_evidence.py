"""追加品質の結果を、曲線が参照できる音声hash付きの証跡へ書き出す。"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from .quality_core import sha256, write_json

SCORES = {'utmosv2': 'predicted_mos', 'speaker_ecapa': 'speaker_similarity'}


def fingerprint(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def configuration(report, metric, evaluator, preparation):
    value = {'evaluator': evaluator, 'options': report['settings']['metrics'].get(metric),
             'model_provenance': preparation.get('provenance'),
             'source_sha256': report['source_sha256'], 'environment': report['environment'],
             'threads': report['threads'], 'repetitions': report['repetitions'],
             'score_selection': 'first_call_only_if_all_repetitions_measured',
             'input_protocol': ('native_full_length_nonreference-v1' if metric == 'utmosv2' else
                                'full_length_equal_rate_equal_length_no_alignment-v1')}
    preparation.update(evaluator=evaluator, configuration=value, configuration_sha256=fingerprint(value))


def export(report, output):
    output = Path(output)
    cases = {case['id']: case for case in report['input']['cases']}
    entries = {}
    for index, row in enumerate(report['rows']):
        metric = row['metric']
        if metric not in SCORES:
            continue
        key = (row['case'], row['method'])
        if key not in entries:
            case = cases[row['case']]
            path = case['reference'] if row['method'] == 'identity' else case['outputs'][row['method']]
            audio_hash = report['input_file_sha256'].get(path)
            audio_error = None
            if audio_hash is None:
                try:
                    audio_hash = sha256(path)
                except Exception as error:
                    logging.exception('品質証跡の音声hashを取得できません: %s', path)
                    audio_error = f'{type(error).__name__}: {error}'
            entries[key] = {'schema_version': 1, 'case': row['case'], 'method': row['method'],
                            'audio_path': path, 'audio_sha256': audio_hash, 'audio_error': audio_error,
                            'source': report['input']['source'], 'source_sha256': report['input']['source_sha256'],
                            'scores': {}}
        preparation = report['metrics'][metric]
        item = {'status': 'ok' if row['status'] == 'measured' else row['status'],
                'value': row['value'] if row['status'] == 'measured' else None,
                'evaluator': preparation['evaluator'], 'configuration_sha256': preparation['configuration_sha256'],
                'unit': row['unit'], 'direction': row['direction'], 'source_metric': metric,
                'configuration': preparation['configuration'],
                'source_result': 'results.json', 'source_row_index': index,
                'reason': row.get('reason'), 'upstream_status': row.get('upstream_status'),
                'initialization_seconds': preparation['seconds'], 'measurement': row.get('measurement')}
        entries[key]['scores'][SCORES[metric]] = item
    manifest = []
    for key, entry in entries.items():
        # case・methodをファイル名へ直接連結せず、区切りを含むJSON全体をhashにする。
        relative = Path(f'quality-evidence-{fingerprint(list(key))}.json')
        write_json(output / relative, entry)
        manifest.append({'case': key[0], 'method': key[1], 'quality_evidence': relative.as_posix(),
                         'audio_path': entry['audio_path'], 'audio_sha256': entry['audio_sha256'],
                         'scores': {name: item['status'] for name, item in entry['scores'].items()}})
    write_json(output / 'quality-evidence-index.json', {'schema_version': 1, 'points': manifest,
               'path_base': '追加評価の出力ディレクトリ（この一覧と同じ階層）。利用側manifestからの相対パスへ直して指定する。'})
