"""保存した120録音だけから公開用の小さな記述台帳を作る。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import traceback

import numpy as np

from .common import (PITCH_BINS, ROOT, budget, check_environment, checked_cases,
                     file_manifest, identity, now, prepare_root, read, seal_owner,
                     verified_seal, write_new)
from .analyze import checked_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--factor-parent', type=Path, required=True)
    parser.add_argument('--analysis-parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare_root(args.output)
    try:
        environment = check_environment()
        partition = [checked_cases(args.input_manifest, args.input_root, owner)
                     for owner in (0, 1, 2)]
        cases = [case for group in partition for case in group]
        if len(cases) != 120 or len({case['speaker'] for case in cases}) != 40:
            raise ValueError('固定120録音・40話者が揃いません')
        rows = []
        histograms = []
        local_failures = []
        for owner in (0, 1, 2):
            owner_cases = partition[owner]
            if len(owner_cases) != (42, 39, 39)[owner]:
                raise ValueError(f'owner{owner}の入力対応が異なります')
            analysis = args.analysis_parent / f'owner-{owner}'
            factors = args.factor_parent / f'owner-{owner}'
            contract_path = analysis / 'contract.json'
            owner_problem = None
            try:
                contract = read(contract_path)
                terminal = read(analysis / 'summary.json')
                if (contract['owner'] != owner
                        or contract['case_ids'] != [case['id'] for case in owner_cases]
                        or contract['input_manifest'] != identity(args.input_manifest)
                        or contract['environment'] != environment
                        or contract['factor_contract'] != identity(
                            args.factor_parent / f'owner-{owner}' / 'contract.json')
                        or contract['factor_owner_seal'] != verified_seal(factors)
                        or contract['factor_terminal_summary']
                        != identity(factors / 'summary.json')
                        or contract['source_files'] != file_manifest(
                            ROOT, sorted(Path(__file__).parent.glob('*.py')))
                        or terminal.get('terminal') is not True
                        or terminal.get('visited') != len(owner_cases)
                        or terminal.get('planned') != len(owner_cases)
                        or terminal.get('unattempted') != 0
                        or (analysis / 'owner-failure.json').exists()):
                    raise ValueError('owner契約が固定入力分割と一致しません')
                analysis_seal = verified_seal(analysis)
            except Exception as exc:
                owner_problem = f'{type(exc).__name__}: {exc}'
                local_failures.append({'owner': owner, 'stage': 'owner_seal_or_contract',
                                       'reason': owner_problem, 'traceback': traceback.format_exc()})
            for case in owner_cases:
                case_id = case['id']
                result_path = analysis / 'cases' / case_id / 'result.json'
                stage = 'owner_seal_or_contract'
                result = None
                frow = None
                try:
                    if owner_problem is not None:
                        raise ValueError('ownerの終端・閉鎖済み契約が利用できません')
                    stage = 'analysis_result'
                    result = read(result_path)
                    if (result['status'] != 'analyzed' or result['case'] != case_id
                            or result['input_sha256'] != case['input']['sha256']
                            or result['shared_factors'] != contract['shared_factors']):
                        raise ValueError('録音の解析結果・入力SHAが一致しません')
                    base = result_path.parent
                    stage = 'analysis_array_identity'
                    files = {entry['path']: checked_file(base, entry)
                             for entry in result['files']}
                    required_files = {'voiced_bin_log_marginal.npy', 'uv_log_mass.npy',
                                      'voiced_log_mass.npy', 'frame_log_normalization.npy',
                                      'frame_mass_drift.npy', 'voiced_mode_bin.npy',
                                      'offset_log_mean.npy', 'offset_mean.npy',
                                      'offset_contributing_frames.npy',
                                      'forward_support_intervals.npy',
                                      'backward_support_intervals.npy'}
                    if (len(files) != len(result['files'])
                            or set(files) not in (required_files,
                                                  required_files | {'apron_post_refinement_f0.npy'})):
                        raise ValueError('解析配列の厳密集合に欠落/重複/余剰があります')
                    loguv = np.load(files['uv_log_mass.npy'], allow_pickle=False)
                    logv = np.load(files['voiced_log_mass.npy'], allow_pickle=False)
                    loghist = np.load(files['offset_log_mean.npy'], allow_pickle=False)
                    stage = 'factor_result_identity'
                    frow_path = factors / 'cases' / case_id / 'result.json'
                    frow = read(frow_path)
                    if (frow['case'] != case_id or frow['status'] != 'factors_saved'
                            or frow['input_sha256'] != case['input']['sha256']
                            or frow['frames'] != result['frames']
                            or frow['shared_factors'] != contract['shared_factors']
                            or result['factor_result'] != identity(frow_path)
                            or result['factor_files'] != frow['files']):
                        raise ValueError('解析・抽出結果のcase/状態/入力/共有因子/SHAが異なります')
                    stage = 'source_voiced_prob_identity'
                    ffiles = {entry['path']: checked_file(frow_path.parent, entry)
                              for entry in frow['files']}
                    if (len(ffiles) != len(frow['files'])
                            or set(ffiles) != {'observation.npy', 'states.npy', 'f0.npy',
                                               'voiced_flag.npy', 'voiced_prob.npy'}):
                        raise ValueError('抽出配列の厳密集合に欠落/重複/余剰があります')
                    source_prob = np.load(ffiles['voiced_prob.npy'], allow_pickle=False)
                    if (len(loguv) != result['frames'] or len(logv) != result['frames']
                            or len(source_prob) != result['frames']
                            or loghist.shape != (2 * PITCH_BINS - 1,)
                            or not np.isfinite(loguv).all() or not np.isfinite(logv).all()
                            or np.isnan(loghist).any() or np.isposinf(loghist).any()
                            or source_prob.dtype != np.float64
                            or not np.isfinite(source_prob).all()):
                        raise ValueError('公開用保存配列のshape/有限性が不正です')
                    overlay = dict(result['apron_overlay'])
                    overlay.pop('source_result', None)  # 公開JSONへ絶対ローカルpathを出さない。
                    overlay.pop('reason_detail', None)
                    rows.append({'case': case_id, 'speaker': case['speaker'],
                                 'status': 'analyzed', 'frames': result['frames'],
                                 'input_sha256': case['input']['sha256'],
                                 'framewise_uv_log_mass': loguv.tolist(),
                                 'framewise_voiced_log_mass': logv.tolist(),
                                 'source_pyin_framewise_voiced_prob': source_prob.tolist(),
                                 'signed_offset_bins_from_log_mode':
                                 list(range(-PITCH_BINS + 1, PITCH_BINS)),
                                 'offset_frame_mean_log_unconditional_mass': [
                                     float(x) if math.isfinite(float(x)) else '-Infinity'
                                     for x in loghist],
                                 'local_array_hashes': result['files'],
                                 'factor_result': identity(frow_path),
                                 'analysis_result': identity(result_path),
                                 'analysis_owner_seal': analysis_seal,
                                 'normalization_max_abs_log':
                                 result['frame_log_normalization_max_abs'],
                                 'normalization_max_abs_mass':
                                 result['frame_mass_drift_max_abs'],
                                 'apron_overlay': overlay})
                    histograms.append(loghist)
                except Exception as exc:
                    local_failures.append({'owner': owner, 'case': case_id,
                                           'stage': stage, 'reason': str(exc),
                                           'traceback': traceback.format_exc(),
                                           'original_analysis_traceback': (
                                               result.get('traceback') if isinstance(result, dict)
                                               and result.get('case') == case_id else None),
                                           'original_extraction_traceback': (
                                               frow.get('traceback') if isinstance(frow, dict)
                                               and frow.get('case') == case_id else None)})
                    rows.append({'case': case_id, 'speaker': case['speaker'],
                                 'status': 'unavailable',
                                 'reason': f'{stage}:{type(exc).__name__}',
                                 'input_sha256': case['input']['sha256']})
        rows.sort(key=lambda row: row['case'])
        total_frames = sum(row['frames'] for row in rows if row['status'] == 'analyzed')
        complete = len(histograms) == 120 and total_frames == 123307
        aggregate = None
        if complete:
            stacked = np.stack(histograms)
            values = np.logaddexp.reduce(stacked, axis=0) - math.log(120)
            if np.isnan(values).any() or np.isposinf(values).any():
                raise FloatingPointError('録音等重み集計に正の無限大またはNaNがあります')
            aggregate = [float(x) if math.isfinite(float(x)) else '-Infinity'
                         for x in values]
        public = {'kind': 'fixed120_pyin_model_internal_marginal_support',
                  'created_at_utc': now(), 'expected_recordings': 120,
                  'expected_speakers': 40, 'successful_recordings': len(histograms),
                  'expected_total_frames': 123307, 'saved_successful_frames': total_frames,
                  'failed_or_unavailable_recordings': 120 - len(histograms),
                  'complete_120_recording_aggregate_available': complete,
                  'recording_equal_offset_log_mean_all_120': aggregate,
                  'offset_unit': '10 cents per pYIN voiced bin',
                  'geometric_plot_guides_cents': [-1200, 1200],
                  'rows': rows,
                  'full_observation_and_voiced_log_marginal_arrays': 'local_only',
                  'environment': environment,
                  'source_files': file_manifest(ROOT, sorted(Path(__file__).parent.glob('*.py')))}
        write_new(args.output / 'local-failures.json',
                  {'kind': 'full_local_failure_evidence', 'records': local_failures})
        budget(args.output.parent.parent,
               len(json.dumps(public, ensure_ascii=False, allow_nan=False).encode('utf-8')) + 4096)
        write_new(args.output / 'compact-results.json', public)
        budget(args.output.parent.parent)
        seal_owner(args.output)
        return 0 if complete else 2
    except Exception:
        write_new(args.output / 'owner-failure.json',
                  {'status': 'failed', 'traceback': traceback.format_exc(),
                   'recorded_at_utc': now()})
        seal_owner(args.output)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
