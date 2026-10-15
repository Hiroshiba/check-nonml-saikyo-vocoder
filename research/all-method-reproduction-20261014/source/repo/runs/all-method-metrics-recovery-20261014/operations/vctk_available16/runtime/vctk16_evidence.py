"""成功した正式processの再利用前に保存済み証拠だけを照合する。推論しない。"""
from pathlib import Path

from all_metrics_common import METHODS, ROOT, read
from all_metrics_vctk_inputs import VCTK_RUN
from all_metrics_vctk_summary import validate_row
from vocoderbench.quality_core import sha256


def checked_contract(path):
    contract = read(path)
    if (contract['input_contract_sha256'] != sha256(VCTK_RUN / 'input-contract.json')
            or contract['inputs_sha256'] != sha256(VCTK_RUN / 'inputs.json')):
        raise ValueError('保存済みprocessの入力契約/manifest SHA不一致')
    for relative, expected in contract['source_sha256'].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f'保存済みprocessの科学source SHA不一致: {relative}')
    return contract, sha256(path)


def checked_native(method, specs):
    _, signature = checked_contract(VCTK_RUN / 'synthesis-contracts' / f'{method}.json')
    records = {}
    for spec in specs:
        if sha256(spec['path']) != spec['sha256']:
            raise ValueError('保存済み原音SHA不一致')
        path = VCTK_RUN / 'native' / method / spec['id'] / 'unedited.json'
        row = read(path)
        if (row.get('case') != spec['id'] or row.get('method') != method
                or row.get('condition') != 'unedited' or row.get('status') != 'measured'
                or row.get('contract_sha256') != signature
                or row['input']['source_sha256'] != spec['sha256']
                or sha256(path.with_suffix('.npy')) != row['audio']['file_sha256']):
            raise ValueError('保存済みnative成功行/波形SHA不一致')
        records[spec['id']] = (path, row)
    return records


def verify_saved_process(method, batch, command):
    all_inputs = read(VCTK_RUN / 'inputs.json')
    indexed = {spec['id']: spec for spec in all_inputs}
    specs = read(VCTK_RUN / 'input-batches' / f'{batch:02d}.json')
    if '--case-start' in command:
        start = int(command[command.index('--case-start') + 1])
        count = int(command[command.index('--case-count') + 1])
        specs = specs[start:start + count]
    if not specs or any(spec != indexed.get(spec['id']) for spec in specs):
        raise ValueError('保存済みbatch/subsetと固定manifest不一致')
    if method != 'all8':
        checked_native(method, specs)
        return
    contract, signature = checked_contract(VCTK_RUN / 'quality-contract.json')
    assets_path = Path(contract['assets_path'])
    if sha256(assets_path) != contract['assets_sha256']:
        raise ValueError('保存済みViSQOL資産manifest SHA不一致')
    assets = read(assets_path)['metrics']['visqol_audio']
    for key in ('binary', 'model'):
        if sha256(assets[key]) != assets[key + '_sha256']:
            raise ValueError('保存済みViSQOL資産実体SHA不一致')
    input_contract = read(VCTK_RUN / 'input-contract.json')
    for spec in specs:
        if sha256(spec['path']) != spec['sha256']:
            raise ValueError('品質入力原音SHA不一致')
        path = VCTK_RUN / 'analysis48' / spec['id'] / 'derivation.json'
        derived = read(path)
        if (derived['case'] != spec['id'] or derived['speaker'] != spec['speaker']
                or derived['contract_sha256'] != signature
                or derived['status'] not in ('measured', 'not_applicable')):
            raise ValueError('保存済み品質派生の識別子/契約/状態不一致')
        for member in METHODS:
            native_path, native = checked_native(member, [spec])[spec['id']]
            info = derived['outputs'][member]
            if (info['native_record_sha256'] != sha256(native_path)
                    or info['native']['file_sha256'] != native['audio']['file_sha256']
                    or info['synthesis_contract_sha256'] != native['contract_sha256']):
                raise ValueError('派生と保存native証拠の不一致')
            row = read(VCTK_RUN / 'quality' / spec['id'] / f'{member}.json')
            validate_row(row, spec, member, signature, input_contract)
            if row['status'] not in ('measured', 'not_applicable', 'pcm16_range_exceeded'):
                raise ValueError('成功processの保存品質状態不一致')
            if derived['status'] == 'measured' and (
                    row['common_samples'] != derived['common_samples']
                    or row['common_seconds'] != derived['common_seconds']
                    or row['native_audio_sha256'] != native['audio']['file_sha256']
                    or row['input_pcm64_sha256'] != info['common_analysis48']['float64_sha256']
                    or row['reference_pcm64_sha256'] != derived['reference_common']['float64_sha256']):
                raise ValueError('保存品質値のnative/共通区間/PCM出典不一致')
