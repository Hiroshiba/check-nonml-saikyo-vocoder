"""保存した120録音だけから公開用の小さな記述台帳を作る。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import traceback

import numpy as np

from .common import (PITCH_BINS, ROOT, budget, check_environment, checked_cases,
                     file_manifest, identity, now, prepare_root, read, seal_owner, write_new)
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
        for owner in (0, 1, 2):
            owner_cases = partition[owner]
            if len(owner_cases) != (42, 39, 39)[owner]:
                raise ValueError(f'owner{owner}の入力対応が異なります')
            analysis = args.analysis_parent / f'owner-{owner}'
            factors = args.factor_parent / f'owner-{owner}'
            contract_path = analysis / 'contract.json'
            contract_problem = None
            try:
                contract = read(contract_path)
                if (contract['owner'] != owner
                        or contract['case_ids'] != [case['id'] for case in owner_cases]
                        or contract['input_manifest'] != identity(args.input_manifest)
                        or contract['environment'] != environment
                        or contract['factor_contract'] != identity(
                            args.factor_parent / f'owner-{owner}' / 'contract.json')
                        or contract['source_files'] != file_manifest(
                            ROOT, sorted(Path(__file__).parent.glob('*.py')))):
                    raise ValueError('owner契約が固定入力分割と一致しません')
            except Exception as exc:
                contract_problem = f'{type(exc).__name__}: {exc}'
            for case in owner_cases:
                case_id = case['id']
                result_path = analysis / 'cases' / case_id / 'result.json'
                try:
                    if contract_problem is not None:
                        raise ValueError(f'owner契約利用不可: {contract_problem}')
                    result = read(result_path)
                    if result['status'] != 'analyzed' or result['input_sha256'] != case['input']['sha256']:
                        raise ValueError('録音の解析結果・入力SHAが一致しません')
                    base = result_path.parent
                    files = {entry['path']: checked_file(base, entry)
                             for entry in result['files']}
                    for required in ('voiced_bin_log_marginal.npy', 'uv_log_mass.npy',
                                     'voiced_log_mass.npy', 'offset_log_mean.npy'):
                        if required not in files:
                            raise ValueError(f'保存配列がありません: {required}')
                    loguv = np.load(files['uv_log_mass.npy'], allow_pickle=False)
                    logv = np.load(files['voiced_log_mass.npy'], allow_pickle=False)
                    loghist = np.load(files['offset_log_mean.npy'], allow_pickle=False)
                    frow_path = factors / 'cases' / case_id / 'result.json'
                    frow = read(frow_path)
                    ffiles = {entry['path']: checked_file(frow_path.parent, entry)
                              for entry in frow['files']}
                    source_prob = np.load(ffiles['voiced_prob.npy'], allow_pickle=False)
                    if (len(loguv) != result['frames'] or len(logv) != result['frames']
                            or len(source_prob) != result['frames']
                            or loghist.shape != (2 * PITCH_BINS - 1,)
                            or not np.isfinite(loguv).all() or not np.isfinite(logv).all()
                            or np.isnan(loghist).any()):
                        raise ValueError('公開用保存配列のshape/有限性が不正です')
                    overlay = dict(result['apron_overlay'])
                    overlay.pop('source_result', None)  # 公開JSONへ絶対ローカルpathを出さない。
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
                                 'normalization_max_abs_log':
                                 result['frame_log_normalization_max_abs'],
                                 'normalization_max_abs_mass':
                                 result['frame_mass_drift_max_abs'],
                                 'apron_overlay': overlay})
                    histograms.append(loghist)
                except Exception as exc:
                    rows.append({'case': case_id, 'speaker': case['speaker'],
                                 'status': 'unavailable', 'reason': type(exc).__name__,
                                 'input_sha256': case['input']['sha256']})
        rows.sort(key=lambda row: row['case'])
        total_frames = sum(row['frames'] for row in rows if row['status'] == 'analyzed')
        complete = len(histograms) == 120 and total_frames == 123307
        aggregate = None
        if complete:
            stacked = np.stack(histograms)
            values = np.logaddexp.reduce(stacked, axis=0) - math.log(120)
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
