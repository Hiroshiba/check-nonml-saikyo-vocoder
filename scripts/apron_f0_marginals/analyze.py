"""保存済みpYIN因子だけからframewise周辺支持を記述する。"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import traceback
import warnings

import librosa
import numpy as np

from .common import (HOP, ROOT, SR, STATES, budget, check_environment,
                     checked_cases, file_manifest, identity, now, prepare_root,
                     read, save_array, seal_owner, write_current, write_new)
from .operator import marginals


def checked_file(base: Path, entry: dict) -> Path:
    path = base / entry['path']
    if identity(path) != {key: entry[key] for key in ('bytes', 'sha256')}:
        raise RuntimeError(f'保存原本のbytes/SHA不一致: {path}')
    return path


def apron_context(case: dict, owner: int, original_run: Path,
                  native_input: dict, frames: int) -> tuple[np.ndarray | None, dict]:
    """任意の既存重ね描き。失敗は主たるpYIN結果へ波及させない。"""
    case_id = case['id']
    path = (original_run / 'native' / f'owner-{owner}' / 'cases' / case_id
            / 'attempt-0001' / 'result.json')
    stage = 'saved_result'
    try:
        row = read(path)
        stage = 'input_identity'
        if row['status'] != 'measured' or row['case'] != case_id:
            raise ValueError('元case/statusが一致しません')
        if row['input_sha256'] != case['input']['sha256']:
            raise ValueError('元16kHz入力SHAが一致しません')
        native = row['native_input']
        if (native['sample_rate'] != SR or native['samples'] != native_input['samples']
                or native['float64_sha256'] != native_input['float64_sha256']):
            raise ValueError('元24kHz float64入力SHA/長さが一致しません')
        case_base = path.parent.parent
        stage = 'representation_hash'
        metadata_path = checked_file(case_base, row['representation']['metadata.json'])
        arrays_path = checked_file(case_base, row['representation']['arrays.npz'])
        meta = read(metadata_path)
        if (meta['sample_rate'] != SR or meta['native_input_samples'] != native['samples']
                or meta['arrays_sha256'] != identity(arrays_path)['sha256']):
            raise ValueError('Layer1 metadataと元入力/配列SHAが一致しません')
        tree = meta['tree']['items']
        stage = 'frame_clock_and_f0'
        descriptions = tree['frames']['items']
        if len(descriptions) != frames:
            raise ValueError('Layer1 frame数がpYINと異なります')
        with np.load(arrays_path, allow_pickle=False) as arrays:
            config = tree['config']['items']
            count = arrays[config['0']['key']]
            hop = arrays[config['1']['key']]
            if (count.shape != (1,) or int(count[0]) != frames or hop.shape != (1,)
                    or hop.dtype != np.float32
                    or hop[0] != np.float32(HOP / SR)):
                raise ValueError('Layer1保存frame数またはfloat32 hopが一致しません')
            trace = np.empty(frames, dtype=np.float32)
            for index, descriptor in enumerate(descriptions):
                value = arrays[descriptor['items']['0']['key']]
                if value.shape != (1,) or value.dtype != np.float32:
                    raise ValueError(f'Layer1 F0形状/dtype不一致: {index}')
                trace[index] = value[0]
        if not np.isfinite(trace).all() or np.any(trace < 0):
            raise ValueError('Layer1 F0に非有限または負値があります')
        return trace, {'status': 'available', 'source_result': str(path),
                       'representation': row['representation'], 'frames': frames,
                       'hop_serialized_float32_seconds': float(hop[0]),
                       'clock': 'integer frame index × 120 samples at 24000 Hz',
                       'post_llsm_refinement': True,
                       'positive_outside_pyin_range_count': int(np.count_nonzero(
                           (trace > 0) & ((trace < 60) | (trace > 1000))))}
    except Exception as exc:
        return None, {'status': 'unavailable',
                      'reason': f'{stage}:{type(exc).__name__}',
                      'source_result': str(path)}


def analyze_case(case: dict, owner: int, factors: Path, output: Path,
                 original_run: Path, transition: np.ndarray, initial: np.ndarray,
                 shared_identity: dict) -> dict:
    case_dir = output / 'cases' / case['id']
    case_dir.mkdir()
    row = {'case': case['id'], 'speaker': case['speaker'], 'status': 'running',
           'started_at_utc': now()}
    write_new(case_dir / 'start.json', row)
    captured = []
    try:
        factor_dir = factors / 'cases' / case['id']
        factor = read(factor_dir / 'result.json')
        if (factor['status'] != 'factors_saved' or factor['case'] != case['id']
                or factor['input_sha256'] != case['input']['sha256']
                or factor['shared_factors'] != shared_identity):
            raise ValueError('保存因子・入力・共有因子の来歴が一致しません')
        paths = {item['path']: checked_file(factor_dir, item) for item in factor['files']}
        if set(paths) != {'observation.npy', 'states.npy', 'f0.npy',
                          'voiced_flag.npy', 'voiced_prob.npy'}:
            raise ValueError('保存因子のfile集合が固定契約と異なります')
        observation = np.load(paths['observation.npy'], allow_pickle=False)
        frames = factor['frames']
        if observation.shape != (STATES, frames) or not 414 <= frames <= 1201:
            raise ValueError('保存観測のframe/state形状が異なります')
        epsilon = float(librosa.util.tiny(observation))
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            result = marginals(observation, transition, initial, epsilon)
        trace, overlay = apron_context(case, owner, original_run,
                                       factor['native_input'], frames)
        files = []
        arrays = {'voiced_bin_log_marginal.npy': result['logvoiced'],
                  'uv_log_mass.npy': result['loguv'],
                  'voiced_log_mass.npy': result['logv'],
                  'frame_log_normalization.npy': result['lognorm'],
                  'frame_mass_drift.npy': np.expm1(result['lognorm']),
                  'voiced_mode_bin.npy': result['mode'],
                  'offset_log_mean.npy': result['histogram_log_mean'],
                  'offset_mean.npy': np.exp(result['histogram_log_mean']),
                  'offset_contributing_frames.npy': result['histogram_count'],
                  'forward_support_intervals.npy': result['forward_intervals'],
                  'backward_support_intervals.npy': result['backward_intervals']}
        if trace is not None:
            arrays['apron_post_refinement_f0.npy'] = trace
        for name, array in arrays.items():
            path = case_dir / name
            save_array(output.parent.parent, path, array)
            files.append(path)
        row.update(status='analyzed', finished_at_utc=now(), frames=frames,
                   input_sha256=case['input']['sha256'],
                   factor_result=identity(factor_dir / 'result.json'),
                   factor_files=factor['files'], shared_factors=shared_identity,
                   log_evidence=result['logz'], epsilon=epsilon,
                   effective_log_convention='log(O+epsilon), log(T+epsilon), log(pi+epsilon)',
                   nominal_zero_transition_log_weight=math.log(epsilon),
                   frame_log_normalization_max_abs=float(np.max(np.abs(result['lognorm']))),
                   frame_mass_drift_max_abs=float(np.max(np.abs(arrays['frame_mass_drift.npy']))),
                   apron_overlay=overlay, files=file_manifest(case_dir, files),
                   warnings=[{'category': w.category.__name__, 'message': str(w.message),
                              'filename': w.filename, 'line': w.lineno} for w in captured])
    except Exception:
        row.update(status='failed', finished_at_utc=now(), traceback=traceback.format_exc(),
                   warnings=[{'category': w.category.__name__, 'message': str(w.message),
                              'filename': w.filename, 'line': w.lineno} for w in captured])
    write_new(case_dir / 'result.json', row)
    budget(output.parent.parent)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', required=True, type=Path)
    parser.add_argument('--input-root', required=True, type=Path)
    parser.add_argument('--original-run', required=True, type=Path)
    parser.add_argument('--factor-root', required=True, type=Path)
    parser.add_argument('--owner', required=True, type=int, choices=(0, 1, 2))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare_root(args.output)
    try:
        environment = check_environment()
        cases = checked_cases(args.input_manifest, args.input_root, args.owner)
        contract = read(args.factor_root / 'contract.json')
        if (contract['owner'] != args.owner or contract['planned_cases'] != len(cases)
                or contract['case_ids'] != [case['id'] for case in cases]
                or contract['input_manifest'] != identity(args.input_manifest)
                or contract['environment'] != environment
                or contract['source_files'] != file_manifest(
                    ROOT, sorted(Path(__file__).parent.glob('*.py')))):
            raise ValueError('抽出時と解析時の固定入力/owner契約が一致しません')
        shared = args.factor_root / 'common' / 'factor-manifest.json'
        shared_identity = identity(shared)
        shared_files = read(shared)['files']
        if {item['path'] for item in shared_files} != {'transition.npy', 'initial.npy'}:
            raise ValueError('共有因子のfile集合が不正です')
        arrays = {item['path']: np.load(checked_file(shared.parent, item), allow_pickle=False)
                  for item in shared_files}
        write_new(args.output / 'contract.json',
                  {'kind': 'fixed120_pyin_saved_factor_analysis', 'owner': args.owner,
                   'started_at_utc': now(), 'environment': environment,
                   'input_manifest': identity(args.input_manifest),
                   'factor_contract': identity(args.factor_root / 'contract.json'),
                   'shared_factors': shared_identity,
                   'planned_cases': len(cases), 'case_ids': [case['id'] for case in cases],
                   'source_files': file_manifest(ROOT, sorted(Path(__file__).parent.glob('*.py'))),
                   'summary_scope': 'model-internal unconditional voiced and UV support'})
        (args.output / 'cases').mkdir()
        for index, case in enumerate(cases, 1):
            row = analyze_case(case, args.owner, args.factor_root, args.output,
                               args.original_run, arrays['transition.npy'],
                               arrays['initial.npy'], shared_identity)
            saved = sum(read(p)['status'] == 'analyzed'
                        for p in (args.output / 'cases').glob('*/result.json'))
            write_current(args.output / 'summary.json',
                          {'kind': 'saved_factor_analysis_status', 'owner': args.owner,
                           'planned': len(cases), 'visited': index,
                           'unattempted': len(cases) - index, 'analyzed': saved,
                           'failed': index - saved, 'last_case': row['case'],
                           'last_status': row['status'],
                           'complete_owner_aggregate_available': saved == len(cases)})
        complete = read(args.output / 'summary.json')['analyzed'] == len(cases)
        seal_owner(args.output)
        return 0 if complete else 2
    except Exception:
        write_new(args.output / 'owner-failure.json',
                  {'status': 'failed_before_or_during_owner',
                   'traceback': traceback.format_exc(), 'recorded_at_utc': now()})
        seal_owner(args.output)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
