"""新runの#16–18全予定行を列挙する。品質・容器量・記述診断を別の軸へ渡す。"""
from __future__ import annotations

from collections import Counter
import logging
import math
from pathlib import Path
import traceback

from all_metrics_common import METHODS, ROOT, RUN, freeze, now, read
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

UNITS = {'pitch_cents': 'cent', 'level_db': 'dB', 'slope_db_per_octave': 'dB/oct', 'duration_seconds': 's'}
LABELS = {'pitch_cents': '推定音高', 'level_db': 'RMS音量', 'slope_db_per_octave': 'スペクトル傾斜', 'duration_seconds': '全長'}
QUALITY = (('predicted_mos', '予測MOS', 'predicted MOS'), ('speaker_similarity', '話者類似度', 'cosine'))
CONTROLS = {'pitch_minus3': '音高−3半音', 'pitch_plus3': '音高＋3半音',
            'gain_minus6': '音量−6dB', 'gain_plus6': '音量＋6dB'}
METRIC_KEYS = {'16': '16_interpolation', '17': '17_representation_robustness', '18': '18_information_rate'}


def templates():
    groups = []
    def add(identifier, label, unit, direction, condition, scope, note, methods=METHODS, kind='metric_order'):
        shared = identifier == '18.shared_assets'
        groups.append({'id': identifier, 'label': label, 'unit': unit, 'direction': direction,
            'methods': list(methods), 'planned_methods': list(METHODS), 'condition': condition,
            'scope': scope, 'note': note, 'kind': kind, 'rankable': direction in ('lower', 'higher'),
            'observation_unit': 'method_fixed_assets' if shared else 'utterance',
            'speaker_bootstrap_eligible': not shared,
            'admissible_status': ['measured', 'ok', 'analytic_identity']
                if identifier.startswith('17.') and '.control.' not in identifier else ['measured', 'ok'],
            'rows': []})
    for name, label, unit in QUALITY:
        add(f'16.dip.{name}', f'補間中点の{label}落込み', unit, 'lower', 'input_gain_reencode_alpha0_0p5_1',
            '同じ発話の原音入力と−6dB入力の再解析端点、中間点が両端より低い量',
            '有限3点の予測品質診断。連続性や知覚的滑らかさの証明ではない。', kind='predicted_quality_diagnostic_order')
    for attribute, unit in UNITS.items():
        for diagnostic, label in [('midpoint_absolute_linear_deviation', '中点の端点線形値からの偏差'),
                                  ('max_abs_slope', '最大傾き'), ('max_abs_slope_change', '最大傾き変化'),
                                  ('reversal_steps', '反転区間数')]:
            add(f'16.{attribute}.{diagnostic}', f'補間の{LABELS[attribute]}・{label}',
                'count' if diagnostic == 'reversal_steps' else unit, 'descriptive', 'input_gain_reencode_alpha0_0p5_1',
                'native全長属性の有限3点差分', '線形応答を良さと仮定しない。順位対象外。', kind='descriptive_no_order')
    for precision in ('float16', 'float32'):
        condition = 'quantized_' + precision
        add(f'17.{precision}.erb', f'{precision}混合精度保存・聴覚帯域変化', 'dB', 'lower', condition,
            '同方式native無編集に対する共通16kHz同長全区間ERB32帯域MAE',
            '保存忠実性の機械指標。長さ不一致は適用外、切り詰め・整列なし。')
        for attribute, unit in UNITS.items():
            add(f'17.{precision}.{attribute}', f'{precision}混合精度保存・{LABELS[attribute]}絶対変化', unit,
                'lower', condition, '同方式native全長属性との差', '絶対音声真値や知覚JNDではない。')
        for name, label, unit in QUALITY:
            add(f'17.{precision}.delta.{name}', f'{precision}混合精度保存・{label}のnative比変化', unit,
                'higher', condition, '同じ評価器・固定原音参照での全長品質値差', '知覚的改善や原音忠実性の保証ではない。')
        for control, label in CONTROLS.items():
            add(f'17.{precision}.control.{control}', f'{precision}復元後の{label}追従誤差',
                'cent' if control.startswith('pitch') else 'dB', 'lower', condition + '__' + control,
                '同じ量子化点の無編集復号を基準とするnative操作',
                'MagPhaseは既存epoch対応内のみ。未知端点を挿入しない。', methods=[m for m in METHODS if m != 'facodec'])
    for configuration in ('native', 'quantized_float16', 'quantized_float32'):
        add(f'18.{configuration}.payload_bitrate', f'{configuration}発話payload量', 'bit/s', 'lower', configuration,
            '実測NPZ全bytes×8÷固定元入力秒。構造JSON・ヘッダー込み',
            '容器量のみの順序。固定共有資産は別途必要、自己完結総bitrateや品質の順位ではない。', kind='container_size_order')
        for name, label, unit in QUALITY:
            add(f'18.{configuration}.{name}', f'{configuration}表現量点の{label}', unit, 'higher', configuration,
                'native全長の非参照MOSまたは固定原音参照ECAPA', '容量と別軸。合成順位・総合勝者を作らない。')
    add('18.shared_assets', '固定共有資産の宣言ファイル量', 'bytes', 'descriptive', 'method_shared',
        '固定decoder/model/source/config資産の宣言ファイル合計',
        'OS/runtimeを全て含む自己完結bundle容量ではない。録音へ複写せず話者CIの入力にしない。', kind='descriptive_no_order')
    return groups


def find_point(metric, configuration):
    return next((p for p in metric.get('points', []) if p.get('configuration') == configuration), None)


def fallback(metric, result):
    status = metric.get('status', result.get('status', 'pending_measurement'))
    if status in ('measured', 'ok', 'analytic_identity'):
        status = 'missing_metric_evidence'
    return {'status': status, 'value': None, 'reason': metric.get('reason', result.get('error'))}


def extract(group, result):
    parts = group['id'].split('.')
    metric = result.get('metrics', {}).get(METRIC_KEYS[parts[0]], {})
    absent = fallback(metric, result)
    if parts[0] == '16':
        if parts[1] == 'dip':
            return metric.get('quality_dips_below_both_endpoints', {}).get(parts[2], absent)
        cell = metric.get('attributes', {}).get(parts[1])
        if not cell:
            return absent
        answer = {'status': cell['status'], 'value': cell.get(parts[2]),
                  'denominator': {'decoded_alpha_points': 3}}
        if parts[2] == 'reversal_steps' and cell['status'] == 'measured' and answer['value'] is None:
            answer.update(status='not_applicable', reason='端点差が宣言許容幅内で方向が未定義のため、反転数を0へしない。')
        return answer
    if parts[0] == '17':
        point = find_point(metric, 'quantized_' + parts[1])
        if not point:
            return absent
        if point['status'] != 'measured':
            return {'status': point['status'], 'value': None, 'reason': point.get('reason')}
        if parts[2] == 'erb':
            cell = point['auditory']
            answer = {**cell, 'denominator': {key: cell.get(key) for key in
                      ('total_band_frame_cells', 'reference_active_cells')}}
        elif parts[2] in UNITS:
            cell = point['attribute_deltas'][parts[2]]
            answer = {**cell, 'value': cell['absolute_delta'], 'denominator': {'native_full_length_attributes': 1}}
        elif parts[2] == 'delta':
            answer = point['quality_delta_from_native'][parts[3]]
        else:
            cell = next((c for c in point.get('controls', [])
                         if c.get('condition', '').endswith('__' + parts[3])), None)
            if not cell:
                return {'status': 'pending_control', 'value': None}
            measurement = cell.get('measurement', {})
            return {**cell, 'denominator': {key: measurement.get(key) for key in
                ('total_frames', 'valid_voiced_frames', 'expected_voiced_frames', 'reference_silent_frames')}}
        if answer.get('status') == 'analytic_identity' and not point.get('exact_identity'):
            raise ValueError('analytic_identityを裏付ける評価済みcanonical入力・PCM同一性がありません')
        return answer
    point = find_point(metric, parts[1])
    if not point:
        excluded = next((p for p in metric.get('excluded_points', []) if p.get('configuration') == parts[1]), None)
        return {'status': excluded['status'], 'value': None, 'reason': excluded.get('reason')} if excluded else absent
    if parts[2] == 'payload_bitrate':
        artifact = point['artifact']
        return {'status': 'measured', 'value': artifact['payload_bits_per_source_second'],
            'denominator': {'seconds': artifact['rate_denominator_seconds'], 'serialized_bytes': artifact['bytes'],
                'actual_file_sha256': artifact['sha256'], 'retained': artifact['retained']}}
    return point.get('quality', {}).get(parts[2], absent)


def shared_constants(group):
    constants = []
    for method in METHODS:
        path = RUN / 'latent-contracts' / method / 'shared-assets.json'
        row = {'method': method, 'status': 'pending_asset_manifest', 'value': None,
               'raw_result': str(path), 'raw_result_sha256': None}
        if path.exists():
            try:
                record = read(path)
                total = record['total_declared_file_bytes']
                if not isinstance(total, int) or total < 0 or total != sum(item['bytes'] for item in record['files']):
                    raise ValueError('共有資産の宣言合計bytesがファイル一覧と不一致')
                row.update(status='measured', value=total, raw_result_sha256=sha256(path),
                           scope=record['scope'], payload_alone_is_self_contained_bitrate=False)
            except Exception:
                logging.exception('共有資産記録の読取失敗: %s', method)
                row.update(status='failed_evidence', error=traceback.format_exc())
        constants.append(row)
    group.update(method_constants=constants, planned_method_constants=len(METHODS),
                 planned_recordings_per_method=None, planned_speakers_per_method=None,
                 aggregation='one method-level declaration; no utterance duplication, mean or speaker CI')


def normalize_row(spec, method, group, cell, source, source_hash):
    origin_status = cell.get('status', 'pending_measurement')
    status, value, reason = origin_status, cell.get('value'), cell.get('reason')
    admissible = group['admissible_status']
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
        status, value, reason = 'failed_evidence', None, '指標値が有限な数値ではありません'
    elif value is None and status in admissible:
        status, reason = 'missing_metric_evidence', reason or '成功状態ですが対応する数値の証跡がありません'
    elif status not in admissible:
        value = None
    return {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
        'status': status, 'origin_status': origin_status, 'value': value, 'reason': reason,
        'raw_result': str(source) if source_hash else None, 'raw_result_sha256': source_hash,
        'denominator': cell.get('denominator', {'original_seconds': spec['samples'] / spec['sample_rate']})}


def main():
    groups = templates()
    specs = read(RUN / 'inputs.json')
    if len(specs) != 120 or len({s['id'] for s in specs}) != 120 or len({s['speaker'] for s in specs}) != 40:
        raise ValueError('全予定行の入力は固定120録音40話者に限定します')
    contract = {'schema_version': 1, 'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha256(__file__)},
        'input_contract_sha256': sha256(RUN / 'input-contract.json'), 'input_manifest_sha256': sha256(RUN / 'inputs.json'),
        'group_definitions': [{key: value for key, value in group.items() if key != 'rows'} for group in groups],
        'complete_grid': 'every planned utterance × every method; unsupported native controls remain explicit',
        'shared_assets': 'one method constant only; rows empty; never speaker bootstrap input',
        'identity': 'preserve proven analytic_identity separately from measured; never compute synthetic zero',
        'ranking': 'direction/kind/condition/scope-specific axes; no composite rank'}
    contract_path = RUN / 'latent-groups-contract.json'
    freeze(contract_path, contract)
    evaluation_contract = RUN / 'latent-evaluation/contract.json'
    signature = sha256(evaluation_contract) if evaluation_contract.exists() else None
    for spec in specs:
        for method in METHODS:
            path = RUN / 'latent-evaluation/measurements' / f'{spec["id"]}__{method}.json'
            result, raw_hash = {'status': 'pending_measurement'}, None
            if path.exists():
                try:
                    raw_hash, result = sha256(path), read(path)
                    if (result.get('case'), result.get('method'), result.get('speaker')) != (spec['id'], method, spec['speaker']):
                        raise ValueError('評価結果のcase/method/speakerが予定行と不一致')
                    if not signature or result.get('contract_sha256') != signature:
                        raise ValueError('評価結果の科学契約が新runと不一致')
                except Exception:
                    logging.exception('正式表現指標の保存証跡読取失敗: %s', path)
                    result = {'status': 'failed_evidence', 'error': traceback.format_exc()}
            for group in groups:
                if group['observation_unit'] != 'utterance':
                    continue
                try:
                    cell = extract(group, result) if method in group['methods'] else {
                        'status': 'unsupported', 'value': None, 'reason': '物理量を定義したnative pitch/gain操作がありません'}
                except Exception:
                    logging.exception('指標groupの保存値抽出失敗: %s %s', path, group['id'])
                    cell = {'status': 'failed_evidence', 'value': None, 'reason': traceback.format_exc()}
                group['rows'].append(normalize_row(spec, method, group, cell, path, raw_hash))
    for group in groups:
        if group['observation_unit'] == 'method_fixed_assets':
            shared_constants(group)
            continue
        group.update(planned_recordings_per_method=len(specs), planned_speakers_per_method=40,
            planned_rows=len(specs) * len(METHODS), status_counts=dict(Counter(r['status'] for r in group['rows'])),
            direct_measured_rows=sum(r['status'] in ('measured', 'ok') and r['value'] is not None for r in group['rows']),
            analytic_identity_rows=sum(r['status'] == 'analytic_identity' and r['value'] is not None for r in group['rows']),
            aggregation='common valid cases within declared comparable methods; utterance → speaker → equal speaker weight')
    write_json(RUN / 'latent-metric-groups.json', {'schema_version': 2, 'updated_at_utc': now(), 'groups': groups,
        'contract_sha256': sha256(contract_path), 'generator_sha256': sha256(__file__),
        'interpretation': '18項目内の軸別派生値。独立した評価項目数や総合順位ではない。',
        'pending_failed_and_not_applicable_are_distinct': True})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-groups'))
