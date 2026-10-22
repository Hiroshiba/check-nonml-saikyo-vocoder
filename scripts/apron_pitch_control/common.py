"""補助比較の固定契約、原結果参照、追記専用の証拠。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.apron_fixed120.common import (MANIFEST_SHA256, ROOT, latest_attempt,
                                           read, sha, source_hashes, versions)
from scripts.apron_fixed120.quality import native_rows


CONDITIONS = ('llsm2_minus3', 'llsm2_plus3')
SEMITONES = {'llsm2_minus3': -3, 'llsm2_plus3': 3}
CONTROL = {'llsm2_minus3': 'pitch_minus3', 'llsm2_plus3': 'pitch_plus3'}
FULL_ECAPA = ('apron_0', 'llsm2_0', *CONDITIONS)


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def file_record(path: Path) -> dict:
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def driver_hashes(phase: str) -> dict:
    paths = [ROOT / 'scripts/apron_pitch_control/common.py',
             ROOT / f'scripts/apron_pitch_control/{phase}.py']
    if phase == 'native':
        paths += [ROOT / f'scripts/{name}.py' for name in
                  ('all_metrics_control_adapters', 'all_metrics_llsm_control',
                   'all_metrics_llsm_storage',
                   'all_metrics_neural_controls', 'all_metrics_representation')]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def separate_output(output: Path, *inputs: Path) -> Path:
    output = output.resolve()
    for path in inputs:
        source = path.resolve()
        if output == source or output in source.parents or source in output.parents:
            raise ValueError(f'補助出力と既存原本・入力の経路が重なります: {source}')
    return output


def original_native(root: Path, cases: list, owner: int):
    """元の全4条件を検品する。元chunkは保存されていない。"""
    contract_path, rows = native_rows(root, cases, owner)
    contract = read(contract_path)
    if (contract['source_hashes'] != source_hashes()
            or contract['runtime_versions'] != versions()
            or contract['input_manifest_sha256'] != MANIFEST_SHA256
            or contract['native_sample_rate'] != 24000):
        raise ValueError('元nativeのsource/runtime/入力が凍結契約と違います')
    references = {}
    for case in cases:
        row_path, row = latest_attempt(root, case['id'])
        if row.get('status') != 'measured' or row.get('speaker') != case['speaker']:
            raise ValueError(f'元nativeが完了していません: {case["id"]}')
        branches = row['branches']
        if set(branches) != {'apron_0', 'apron_minus3', 'apron_plus3', 'llsm2_0'}:
            raise ValueError(f'元nativeの枝が不一致です: {case["id"]}')
        references[case['id']] = {
            'result': file_record(row_path / 'result.json'),
            'native_input': row['native_input'],
            'waves': {name: item['output']['sha256'] for name, item in branches.items()},
        }
    return contract_path, contract, rows, references


def supplemental_native(root: Path, cases: list, owner: int,
                        original_contract_sha: str):
    contract_path = root / 'contract.json'
    contract = read(contract_path)
    summary = read(root / 'summary.json')
    if (contract.get('kind') != 'apron_pitch_control_native'
            or contract.get('owner') != owner
            or contract.get('case_ids') != [case['id'] for case in cases]
            or contract.get('conditions') != list(CONDITIONS)
            or contract.get('original_native_contract_sha256') != original_contract_sha
            or contract.get('source_hashes') != source_hashes()
            or contract.get('driver_hashes') != driver_hashes('native')
            or contract.get('runtime_versions') != versions()
            or summary.get('planned_outputs') != len(cases) * 2):
        raise ValueError('補助nativeの固定契約または予定分母が違います')
    rows = {}
    references = {}
    for case in cases:
        attempt, row = latest_attempt(root, case['id'])
        if attempt is None or row is None:
            raise ValueError(f'補助native個票が未完了です: {case["id"]}')
        if (row['case'] != case['id'] or row['input_sha256'] != case['input']['sha256']
                or row.get('status') not in ('measured', 'failed')
                or set(row.get('branches', {})) != set(CONDITIONS)):
            raise ValueError(f'補助nativeの入力が不一致です: {case["id"]}')
        branch_refs = {}
        for name in CONDITIONS:
            item = row['branches'][name]
            branch_path = attempt / f'{name}.json'
            if not branch_path.is_file() or read(branch_path) != item:
                raise ValueError(f'補助native枝の記録が不一致です: {branch_path}')
            if item.get('status') == 'measured':
                descriptor = item['output']
                path = root / 'cases' / case['id'] / descriptor['path']
                if (not path.is_file() or path.stat().st_size != descriptor['bytes']
                        or sha(path) != descriptor['sha256']):
                    raise ValueError(f'補助波形が不一致です: {path}')
                wave = np.load(path, mmap_mode='r', allow_pickle=False)
                if (wave.ndim != 1 or len(wave) != descriptor['samples']
                        or descriptor['sample_rate'] != 24000
                        or wave.dtype not in (np.dtype('float32'), np.dtype('float64'))):
                    raise ValueError(f'補助波形の形式が不一致です: {path}')
            branch_refs[name] = {
                'record': file_record(branch_path), 'status': item.get('status'),
                'wave_sha256': item['output']['sha256']
                if item.get('status') == 'measured' else None,
            }
        rows[case['id']] = row
        references[case['id']] = {
            'attempt': str(attempt.relative_to(root)),
            'result': file_record(attempt / 'result.json'),
            'branches': branch_refs,
        }
    return contract_path, rows, references
