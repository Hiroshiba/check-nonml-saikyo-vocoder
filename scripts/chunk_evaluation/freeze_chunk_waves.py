"""生成済み区間receiptから品質用波形manifestを凍結する。合成・推論はしない。"""
from pathlib import Path

from .axis_registry import validate_registry
from .chunk_checkpoint import checked
from .chunk_contracts import CONDITIONS, ContractError, freeze, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli


def main():
    parser = LoggedArgumentParser(description=__doc__)
    for name in ('plan', 'inputs', 'input-root', 'receipts', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--chunk', required=True)
    args = parser.parse_args()
    signature = sha(args.plan)
    plan = validate_plan(read(args.plan))
    validate_registry(plan)
    chunk = {r['id']: r for r in plan['chunks']}[args.chunk]
    inputs = read(args.inputs)
    if list(inputs) != [row['case'] for row in plan['cases']]:
        raise ContractError('固定入力の全120順序が違います')
    rows = {r['case']: {'case': r['case'], 'speaker': r['speaker'],
                       'common_samples': r['common_samples'], 'outputs': {}}
            for r in plan['cases'] if r['case'] in chunk['case_ids']}
    expected = {r['case']: r for r in plan['cases']}
    audited = [(args.plan, signature), (args.inputs, sha(args.inputs)), (args.receipts, sha(args.receipts))]
    for case, row in rows.items():
        source, fixed = inputs[case], expected[case]
        if (source['expected_npy_sha256'] != fixed['input_sha256'] or source['samples'] != fixed['samples']
                or source['sample_rate'] != fixed['sample_rate'] or source['speaker'] != fixed['speaker']):
            raise ContractError('固定入力のSHA/N/SR/話者が違います')
        path = checked(args.input_root/source['path'], fixed['input_sha256'])
        audited.append((path, fixed['input_sha256']))
        row['reference'] = {'status': 'measured', 'path': str(path.resolve()), 'sha256': fixed['input_sha256'],
                            'samples': fixed['samples'], 'sample_rate': 16000}
    mapping = read(args.receipts)
    required = {plan['candidate']: 'candidate-generation', 'pml': 'pml-generation', 'world_harvest': 'world-generation'}
    if set(mapping) != set(plan['methods']) or set(mapping) != set(required):
        raise ContractError('候補・現PML・WORLDの生成receiptが必要です')
    receipts = []
    import numpy as np
    for method, item in mapping.items():
        path = checked(args.receipts.parent/item['path'], item['sha256'])
        audited.append((path, item['sha256']))
        receipt = read(path)
        if (receipt.get('schema_version') != 2 or receipt.get('stage_id') != required[method]
                or receipt.get('method') != method or receipt.get('validation_state') != 'validated_end'
                or receipt.get('run_plan_sha256') != signature or receipt.get('chunk_id') != args.chunk
                or receipt.get('case_ids') != chunk['case_ids']
                or receipt.get('frozen_digests') != plan['frozen_digests']):
            raise ContractError('生成receiptの凍結条件が違います')
        if method == plan['candidate'] and receipt.get('primary_native') != 'Cartesian q=0':
            raise ContractError('候補nativeはCartesian q0出力でなければなりません')
        for artifact in receipt['artifacts']:
            artifact_path = checked(path.parent/artifact['path'], artifact['sha256'])
            audited.append((artifact_path, artifact['sha256']))
        seen = set()
        wanted = ('native',) if method == 'world_harvest' else CONDITIONS
        for source in receipt['rows']:
            case, condition = source['case'], source['condition']
            key = case, condition
            if case not in rows or condition not in wanted or key in seen:
                raise ContractError('生成行の重複または予定外条件です')
            seen.add(key)
            if source['status'] in ('measured', 'ok'):
                value = dict(source['wave'])
                wave = checked(path.parent/value['path'], value['sha256'])
                audited.append((wave, value['sha256']))
                audio = np.load(wave, allow_pickle=False, mmap_mode='r')
                if (audio.ndim != 1 or audio.dtype != np.dtype('float64') or not np.isfinite(audio).all()
                        or len(audio) != expected[case]['samples'] or value['samples'] != len(audio)
                        or value['sample_rate'] != 16000):
                    raise ContractError('生成波形のN/SR/dtype/有限性が違います')
                value.update(status='measured', path=str(wave.resolve()))
            elif source['status'] in ('failed', 'failed_or_not_generated', 'failed_q1_observation'):
                value = {'status': 'failed', 'reason_code': 'generation_failed',
                         'source_status': source['status'], 'source_reason_code': source.get('reason_code'),
                         'failed_stages': source.get('failed_stages', [])}
            else:
                raise ContractError('生成行が終端状態ではありません')
            value['generation_receipt_sha256'] = item['sha256']
            value['generation_case'] = case
            row = rows[case]
            row['outputs'].setdefault(method, {})[condition] = value
        required_keys = {(c, condition) for c in chunk['case_ids'] for condition in wanted}
        if seen != required_keys:
            raise ContractError('生成条件の全予定行が不足しています')
        if method == 'world_harvest':
            for row in rows.values():
                for condition in CONDITIONS[1:]:
                    row['outputs'][method][condition] = {'status': 'unsupported', 'reason_code': 'unsupported_operation'}
        receipts.append({'path': str(path.resolve()), 'sha256': item['sha256'], 'stage_id': required[method]})
    for path, digest in audited:
        checked(path, digest)
    freeze(args.output, {'schema_version': 2, 'run_plan_sha256': signature, 'chunk_id': args.chunk,
                        'generation_receipts': receipts, 'cases': [rows[c] for c in chunk['case_ids']]})


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'freeze-chunk-waves'))
