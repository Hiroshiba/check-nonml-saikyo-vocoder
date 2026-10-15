"""事後条件付き解析のpre-score固定と全800終端をmetadataで照合する。"""
from types import SimpleNamespace

from conditional_settings import ROOT, OUT, PACKAGE, ANALYSIS
from all_metrics_common import METHODS, read, now
from release_proof import file_proof, read_proof
from supervisor import require_inputs, inspect_records
from vocoderbench.quality_core import sha256, write_json


def verify_conditional_start():
    frozen_path = PACKAGE / 'freeze.json'
    frozen = read(frozen_path)
    for relative, digest in frozen['source_sha256'].items():
        if sha256(ROOT / relative) != digest:
            raise ValueError('事後条件付き解析のpre-score sourceが不一致')
    release_path = ANALYSIS / 'execution-release.json'
    release = read(release_path)
    if (release.get('status') != 'approved_for_posthoc_conditional_analysis'
            or release.get('freeze_sha256') != sha256(frozen_path)):
        raise ValueError('別解析のpre-score review/固定releaseが未完')
    review = read_proof(release['independent_review'])
    if review.get('status') != 'approved' or review.get('errors') != [] or review.get('freeze_sha256') != sha256(frozen_path):
        raise ValueError('別解析review対象の固定SHAが不一致')
    receipt = read_proof(release['private_checkpoint_readback'])
    if (receipt.get('status') != 'fixed_version_readback_all_member_hashes_match'
            or not receipt.get('library_file_id') or not receipt.get('file_id')
            or not isinstance(receipt.get('version'), int)):
        raise ValueError('別解析の固定版読戻しが未成功')
    lookup = {row['path']: row for row in receipt['files']}
    if len(lookup) != len(receipt['files']) or len(lookup) != receipt['member_count']:
        raise ValueError('別解析固定receiptのmember計数不一致')
    required = [frozen_path, ROOT / release['independent_review']['path']]
    required.extend(ROOT / path for path in frozen['source_sha256'] if (ROOT / path).parent == PACKAGE)
    for path in required:
        proof = file_proof(path)
        if lookup.get(proof['path']) != proof:
            raise ValueError('別解析の必要小memberが正確path/SHA/bytesで固定保存されていません')
    primary_release = read(OUT / 'execution-release-v3.json')
    if set(primary_release.get('released_batches', [])) != set(range(10)):
        raise ValueError('全100×8の正式抽出予定が未終了')
    if primary_release['preflight_sha256'] != frozen['primary_preflight_sha256']:
        raise ValueError('元v3固定preflightとの接続不一致')
    args = SimpleNamespace(preflight_sha256=primary_release['preflight_sha256'], batch=0,
        inputs_sha256=sha256(OUT / 'inputs.json'), input_contract_sha256=sha256(OUT / 'input-contract.json'))
    require_inputs(args)
    primary_path = OUT / 'rankings/results.json'
    primary = read(primary_path)
    if not primary.get('analysis_complete') or primary.get('methods') != list(METHODS):
        raise ValueError('元全8primaryの正式集計を先に完了して保持してください')
    states = {}
    for method in METHODS:
        rows = inspect_records(method, read(OUT / 'inputs.json'), verify=True)
        if len(rows) != 100 or any(row['status'] not in ('measured', 'failed') for row in rows):
            raise ValueError('全800予定recordが未終端。別解析をまだ開始しません')
        states[method] = rows
    write_json(ANALYSIS / 'aggregation-start-gate.json', {'verified_at_utc': now(),
        'freeze_sha256': sha256(frozen_path), 'execution_release': file_proof(release_path),
        'release_content': release, 'primary_result_sha256': sha256(primary_path),
        'terminal_feature_records': states})
