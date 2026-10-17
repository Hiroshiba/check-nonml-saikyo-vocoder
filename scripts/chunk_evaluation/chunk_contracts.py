"""固定120録音の区間計画と数値保存契約。音声・モデルを実行しない。"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

CONDITIONS = ('native', 'pitch_minus3', 'pitch_plus3')
STATUSES = {'measured', 'failed', 'unsupported', 'not_applicable', 'upstream_failed',
            'reference_cer_gate_exceeded', 'insufficient_support'}
REASONS = {'none', 'generation_failed', 'metric_failed', 'model_initialization_failed',
           'unsupported_operation', 'outside_scope', 'full_transcript_unavailable',
           'reference_cer_gate_exceeded', 'insufficient_voiced_support',
           'no_low_energy_segment', 'length_mismatch', 'output_shorter_than_fixed_window',
           'invalid_f0', 'diagnostic_failed', 'other_classified_failure'}


class ContractError(ValueError):
    """科学処理失敗とは分けて全体を停止する契約不一致。"""


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ContractError('SHA256の形式が不正です')
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}', value):
        raise ContractError('公開識別子の形式が不正です')
    return value


def freeze(path, value):
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise ContractError('凍結済みファイルの上書きを拒否しました')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    with path.open('x', encoding='utf-8') as stream:
        stream.write(content)


def validate_plan(plan):
    if plan.get('schema_version') != 2 or plan.get('scope') != 'fixed120-chunked-evaluation':
        raise ContractError('新規区間実行の計画形式が必要です')
    cases = plan['cases']
    ids = [r['case'] for r in cases]
    speakers = Counter(r['speaker'] for r in cases)
    if len(ids) != 120 or len(set(ids)) != 120 or len(speakers) != 40 or set(speakers.values()) != {3}:
        raise ContractError('固定120録音・40話者・各3録音と一致しません')
    for row in cases:
        identifier(row['case'])
        identifier(row['speaker'])
        digest(row['input_sha256'])
        if row['sample_rate'] != 16000 or type(row['samples']) is not int or row['samples'] <= 0:
            raise ContractError('入力N/SRが不正です')
        if type(row['common_samples']) is not int or not 0 < row['common_samples'] <= row['samples']:
            raise ContractError('固定共通窓が不正です')
    chunks = plan['chunks']
    expected = [{'id': f'chunk-{i+1:02d}', 'case_ids': ids[i*12:(i+1)*12]} for i in range(10)]
    if chunks != expected:
        raise ContractError('元順序を維持した12件ずつの10区間が必要です')
    methods = plan['methods']
    if len(methods) != len(set(methods)) or not methods or 'original' in methods:
        raise ContractError('方式IDが空・重複、または原音を方式扱いしています')
    for method in methods:
        identifier(method)
    if plan['formal_base'] not in methods or plan['candidate'] not in methods:
        raise ContractError('現baseと候補を予定方式へ含めてください')
    if plan['formal_base'] != 'pml' or plan['formal_base_version'] != 'pml-lowband-fwcep60-v1':
        raise ContractError('今回の正式base版と一致しません')
    seen = set()
    for axis in plan['axes']:
        identifier(axis['id'])
        if axis['condition'] not in CONDITIONS or axis['direction'] not in ('lower', 'higher', 'diagnostic'):
            raise ContractError('軸の条件・方向が不正です')
        key = (axis['id'], axis['condition'])
        if key in seen:
            raise ContractError('予定軸が重複しています')
        seen.add(key)
        if not axis['methods'] or len(axis['methods']) != len(set(axis['methods'])):
            raise ContractError('軸の予定方式が空または重複です')
        if set(axis['methods']) - set(methods+['original']):
            raise ContractError('未知の予定方式です')
        if 'original' in axis['methods'] and (axis['id'] != '1.native_mos' or axis['condition'] != 'native'):
            raise ContractError('原音はnative MOSのみの別参照行です')
    if len([axis for axis in plan['axes'] if axis['condition'] == 'native']) != 71:
        raise ContractError('主品質の予定71軸が必要です')
    mos = [a for a in plan['axes'] if a['id'] == '1.native_mos' and a['condition'] == 'native']
    if len(mos) != 1 or 'original' not in mos[0]['methods']:
        raise ContractError('同じ新規実行の原音MOS120を予定してください')
    if not plan['required_stage_receipts'] or len(plan['required_stage_receipts']) != len(set(plan['required_stage_receipts'])):
        raise ContractError('必須stage一覧が空または重複です')
    for stage in plan['required_stage_receipts']:
        identifier(stage)
    for name in ('cohort', 'evaluator', 'generation', 'runtime', 'assets', 'preprocessing'):
        digest(plan['frozen_digests'][name])
    if plan['execution'] != {'chunk_size': 12, 'scientific_parallelism': 1,
                             'rank_before_all_chunks': False, 'generation_before_quality': True}:
        raise ContractError('区間順序・並列・順位の規則が一致しません')
    return plan


def planned_keys(plan, chunk):
    return {(case, axis['id'], axis['condition'], method)
            for case in chunk['case_ids'] for axis in plan['axes'] for method in axis['methods']}


def public_row(row, valid_keys):
    key = (row['case'], row['axis'], row['condition'], row['method'])
    if key not in valid_keys or row['status'] not in STATUSES or row['reason_code'] not in REASONS:
        raise ContractError('予定外または未終端の評価行です')
    value = row['value']
    if row['status'] == 'measured':
        if type(value) not in (int, float) or not math.isfinite(value) or row['reason_code'] != 'none':
            raise ContractError('測定成功は有限数値と理由noneが必要です')
    elif value is not None or row['reason_code'] == 'none':
        raise ContractError('欠測・失敗はnull値と具体的理由が必要です')
    # 自由文・path・private IDをコピーしない。公開列はこの固定集合だけ。
    result = dict(zip(('case', 'axis', 'condition', 'method'), key, strict=True))
    result.update(status=row['status'], reason_code=row['reason_code'], value=value)
    for name in ('support_numerator', 'support_denominator'):
        if name in row:
            if type(row[name]) is not int or row[name] < 0:
                raise ContractError('支持数は非負整数が必要です')
            result[name] = row[name]
    support = ('support_numerator', 'support_denominator')
    if any(name in row for name in support):
        if not all(name in row for name in support) or row[support[0]] > row[support[1]]:
            raise ContractError('支持数は分子・分母の両方と分子以下でない分母が必要です')
    return key, result
