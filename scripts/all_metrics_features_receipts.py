"""正式抽出batchの成功をsource契約と実在するmean/momentsで照合する。"""
from __future__ import annotations

from all_metrics_common import read
from all_metrics_features_common import TRAIN, schema_digest
from vocoderbench.quality_core import sha256


def completion_receipt(root, method, inputs, human=False):
    contract = root / ('feature-contracts' if human else 'contracts') / f'{method}.json'
    schema = TRAIN / 'schemas' / f'{method}.json'
    input_contract = root / 'input-contract.json'
    if read(contract)['input_contract_sha256'] != sha256(input_contract):
        raise ValueError('正式抽出の原音入力契約が不一致')
    paths = [inputs, contract, schema, input_contract]
    for spec in read(inputs):
        folder = root / ('features' if human else 'native') / method / spec['id']
        path = folder / 'features.json'
        record = read(path)
        if record['status'] != 'measured' or record['contract_sha256'] != sha256(contract):
            raise ValueError('成功終了batchの特徴記録が未成功または契約不一致')
        if record['projected_schema_sha256'] != schema_digest(read(schema)):
            raise ValueError('成功終了batchの投影schemaが不一致')
        if record['input']['source_sha256'] != spec['sha256']:
            raise ValueError('成功終了batchの原音入力SHAが不一致')
        artifact = folder / ('mean.npy' if human else 'moments.npz')
        if sha256(artifact) != record['mean_sha256' if human else 'moments_sha256']:
            raise ValueError('成功終了batchの特徴成果が未復元またはhash不一致')
        paths.extend([path, artifact])
    return {str(path): sha256(path) for path in paths}
