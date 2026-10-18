"""区間終端の数値を公開列へ射影。全区間完了前の順位は生成しない。"""
from pathlib import Path

from .chunk_contracts import ContractError, digest, freeze, planned_keys, public_row, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli


def checked(path, expected):
    if sha(path) != digest(expected):
        raise ContractError('保存データのSHAが一致しません')
    return path


def checkpoint(plan_path, receipt_path):
    signature = sha(plan_path)
    plan = validate_plan(read(plan_path))
    receipt_hash = sha(receipt_path)
    receipt = read(receipt_path)
    if (receipt.get('schema_version') != 2 or receipt.get('validation_state') != 'validated_end'
            or receipt.get('run_plan_sha256') != signature
            or receipt.get('frozen_digests') != plan['frozen_digests']):
        raise ContractError('区間終端または凍結条件が一致しません')
    chunks = {row['id']: row for row in plan['chunks']}
    chunk = chunks[receipt['chunk_id']]
    if receipt['case_ids'] != chunk['case_ids']:
        raise ContractError('区間の予定録音が一致しません')
    # reviewed adapterがまとめた全stage証跡を実ファイルへ照合する。
    required = set(plan['required_stage_receipts'])
    stages = receipt['stage_receipts']
    if set(stages) != required:
        raise ContractError('予定stageの終端証跡に欠落または追加があります')
    audited = [(plan_path, signature), (receipt_path, receipt_hash)]
    for stage_id, item in stages.items():
        path = checked(receipt_path.parent/item['path'], item['sha256'])
        audited.append((path, item['sha256']))
        stage = read(path)
        if (stage.get('schema_version') != 2 or stage.get('stage_id') != stage_id
                or stage.get('validation_state') != 'validated_end'
                or stage.get('run_plan_sha256') != signature
                or stage.get('chunk_id') != chunk['id']
                or stage.get('case_ids') != chunk['case_ids']
                or stage.get('frozen_digests') != plan['frozen_digests']):
            raise ContractError('stageの終端条件が一致しません')
        if not stage['artifacts']:
            raise ContractError('stageの実artifact証跡が空です')
        for artifact in stage['artifacts']:
            artifact_path = checked(path.parent/artifact['path'], artifact['sha256'])
            audited.append((artifact_path, artifact['sha256']))
    rows_path = checked(receipt_path.parent/receipt['rows_path'], receipt['rows_sha256'])
    raw = read(rows_path)
    expected = planned_keys(plan, chunk)
    rows, seen = [], set()
    for row in raw['rows']:
        key, projection = public_row(row, expected)
        if key in seen:
            raise ContractError('区間内の測定行が重複しています')
        seen.add(key)
        rows.append(projection)
    if seen != expected:
        raise ContractError('区間内の予定ケース×軸に欠落があります')
    # 射影中に参照が変わった場合も止める。
    if sha(plan_path) != signature:
        raise ContractError('射影中に計画が変更されました')
    checked(rows_path, receipt['rows_sha256'])
    for path, expected_sha in audited:
        checked(path, expected_sha)
    return {'schema_version': 2, 'run_plan_sha256': signature, 'chunk_id': chunk['id'],
            'case_ids': chunk['case_ids'], 'validation_state': 'chunk_validated_end',
            'overall_state': 'incomplete_until_all_chunks_verified',
            'planned_recordings': 120, 'chunk_recordings': 12,
            'frozen_digests': plan['frozen_digests'], 'rows': rows,
            'source_receipt_sha256': receipt_hash,
            'rankings': None, 'adoption_decision': None}


def assemble(plan_path, paths):
    signature = sha(plan_path)
    plan = validate_plan(read(plan_path))
    chunks = {c['id']: c for c in plan['chunks']}
    seen, rows, sources, audited = set(), [], [], [(plan_path, signature)]
    for path in paths:
        initial_sha = sha(path)
        data = read(path)
        audited.append((path, initial_sha))
        identifier = data['chunk_id']
        if identifier not in chunks or identifier in seen:
            raise ContractError('区間の重複または未知の区間です')
        if (data.get('schema_version') != 2
                or data.get('validation_state') != 'chunk_validated_end'
                or data.get('run_plan_sha256') != signature
                or data.get('frozen_digests') != plan['frozen_digests']
                or data['case_ids'] != chunks[identifier]['case_ids']):
            raise ContractError('保存区間の来歴が一致しません')
        expected = planned_keys(plan, chunks[identifier])
        keys = set()
        for row in data['rows']:
            key, projection = public_row(row, expected)
            if key in keys:
                raise ContractError('保存区間に重複行があります')
            keys.add(key)
            rows.append(projection)
        if keys != expected:
            raise ContractError('保存区間の予定行に欠落があります')
        seen.add(identifier)
        checked(path, initial_sha)
        sources.append({'chunk_id': identifier, 'sha256': initial_sha})
    if seen != set(chunks):
        raise ContractError('全10区間が終端になるまで最終集約へ渡せません')
    for path, expected_sha in audited:
        checked(path, expected_sha)
    return {'schema_version': 2, 'validation_state': 'validated_end',
            'run_plan_sha256': signature, 'planned_recordings': 120,
            'chunk_sources': sources, 'rows': rows,
            'ranking_state': 'not_computed; aggregate_full_rows_by_speaker_and_common_support'}


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--receipt', type=Path)
    group.add_argument('--checkpoints', type=Path, nargs='+')
    args = parser.parse_args()
    result = checkpoint(args.plan, args.receipt) if args.receipt else assemble(args.plan, args.checkpoints)
    freeze(args.output, result)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-checkpoint'))
