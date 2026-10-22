"""pYINを各入力に一度だけ呼び、実際に渡した状態因子を先に保存する。"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import traceback
import warnings

import librosa
import numpy as np
from scipy.signal import resample_poly

from .common import (HOP, PITCH_BINS, ROOT, SR, STATES, budget, check_environment,
                     checked_cases, file_manifest, identity, now, prepare_root,
                     read, save_array, seal_owner, write_current, write_new)


PYIN_OPTIONS = {
    'sr': SR, 'fmin': 60, 'fmax': 1000, 'frame_length': 2048,
    'hop_length': HOP, 'center': True, 'pad_mode': 'constant', 'fill_na': 0,
    'n_thresholds': 100, 'beta_parameters': (2, 18),
    'boltzmann_parameter': 2, 'resolution': 0.1,
    'max_transition_rate': 35.92, 'switch_prob': 0.01,
    'no_trough_prob': 0.01,
}


def capture_once(x24: np.ndarray, expected_frames: int):
    """公開呼出しの内側にある単一Viterbi呼出しだけを捕捉する。"""
    original = librosa.sequence.viterbi
    captured = []

    def intercept(prob, transition, *, p_init=None, **kwargs):
        if captured or kwargs:
            raise RuntimeError('mono pYIN以外のViterbi呼出しです')
        if (not isinstance(prob, np.ndarray) or prob.shape != (1, STATES, expected_frames)
                or prob.dtype != np.float64 or not isinstance(transition, np.ndarray)
                or transition.shape != (STATES, STATES) or transition.dtype != np.float64
                or not isinstance(p_init, np.ndarray) or p_init.shape != (STATES,)
                or p_init.dtype != np.float64):
            raise RuntimeError('実Viterbi因子のmono shape/dtypeが固定契約と違います')
        if (not np.isfinite(prob).all() or not np.isfinite(transition).all()
                or not np.isfinite(p_init).all() or np.any(prob < 0)
                or np.any(transition < 0) or np.any(p_init < 0)):
            raise RuntimeError('実Viterbi因子が非有限または負です')
        snapshot = (prob.copy(), transition.copy(), p_init.copy())
        result = original(prob, transition, p_init=p_init)
        state = np.asarray(result)
        if state.shape != (1, expected_frames) or not np.issubdtype(state.dtype, np.integer):
            raise RuntimeError('実Viterbi経路のshape/dtypeが固定契約と違います')
        captured.append((*snapshot, state.copy()))
        return result

    try:
        librosa.sequence.viterbi = intercept
        f0, flag, voiced_prob = librosa.pyin(x24, **PYIN_OPTIONS)
    finally:
        librosa.sequence.viterbi = original
    if len(captured) != 1:
        raise RuntimeError(f'実Viterbi呼出し数が1と違います: {len(captured)}')
    if (f0.shape != (expected_frames,) or flag.shape != (expected_frames,)
            or voiced_prob.shape != (expected_frames,) or flag.dtype != np.bool_
            or not np.isfinite(f0).all() or not np.isfinite(voiced_prob).all()):
        raise RuntimeError('公開pYIN出力のshape/dtype/有限性が不正です')
    return (*captured[0], f0, flag, voiced_prob)


def _warning_records(found):
    return [{'category': item.category.__name__, 'message': str(item.message),
             'filename': item.filename, 'line': item.lineno} for item in found]


def extract_case(case: dict, output: Path, common_dir: Path) -> dict:
    case_dir = output / 'cases' / case['id']
    case_dir.mkdir()
    row = {'case': case['id'], 'speaker': case['speaker'], 'status': 'running',
           'started_at_utc': now(), 'input_sha256': case['input']['sha256']}
    write_new(case_dir / 'start.json', row)
    found = []
    try:
        x = np.load(case['absolute_input'], allow_pickle=False)
        if x.dtype != np.float64 or x.ndim != 1 or not np.isfinite(x).all():
            raise RuntimeError('固定入力がmono float64有限値ではありません')
        with warnings.catch_warnings(record=True) as resample_warnings:
            warnings.simplefilter('always')
            x24 = np.ascontiguousarray(resample_poly(x, 3, 2), dtype=np.float64)
        found.extend(resample_warnings)
        frames = len(x24) // HOP + 1
        if not 414 <= frames <= 1201 or len(x24) != (len(x) * 3 + 1) // 2:
            raise RuntimeError(f'24 kHz長と固定frame範囲が不一致: {len(x24)}, {frames}')
        row['native_input'] = {'sample_rate': SR, 'samples': len(x24),
                               'float64_sha256': hashlib.sha256(x24.tobytes()).hexdigest(),
                               'resampling': 'scipy.signal.resample_poly(x,3,2)'}
        with warnings.catch_warnings(record=True) as pyin_warnings:
            warnings.simplefilter('always')
            observation, transition, initial, states, f0, flag, voiced_prob = capture_once(x24, frames)
        found.extend(pyin_warnings)
        if observation.shape != (1, STATES, frames) or np.any(states >= STATES) or np.any(states < 0):
            raise RuntimeError('捕捉因子・経路のshape/値が不正です')
        row['actual_transition_array_sha256'] = hashlib.sha256(
            transition.tobytes(order='C')).hexdigest()
        row['actual_initial_array_sha256'] = hashlib.sha256(
            initial.tobytes(order='C')).hexdigest()
        files = []
        for name, array in (('observation.npy', observation[0]), ('states.npy', states[0]),
                            ('f0.npy', f0), ('voiced_flag.npy', flag),
                            ('voiced_prob.npy', voiced_prob)):
            path = case_dir / name
            save_array(output.parent.parent, path, array)
            files.append(path)
        row['captured_files'] = file_manifest(case_dir, files)
        if not (common_dir / 'factor-manifest.json').exists():
            files = []
            for name, array in (('transition.npy', transition), ('initial.npy', initial)):
                path = common_dir / name
                save_array(output.parent.parent, path, array)
                files.append(path)
            write_new(common_dir / 'factor-manifest.json',
                      {'kind': 'shared_actual_viterbi_factors', 'files': file_manifest(common_dir, files)})
        else:
            shared = read(common_dir / 'factor-manifest.json')
            for record in shared['files']:
                path = common_dir / record['path']
                if identity(path) != {k: record[k] for k in ('bytes', 'sha256')}:
                    raise RuntimeError('共有遷移・初期因子の原本SHAが不一致です')
            if (transition.tobytes(order='C') != np.load(
                    common_dir / 'transition.npy', allow_pickle=False).tobytes(order='C')
                    or initial.tobytes(order='C') != np.load(
                        common_dir / 'initial.npy', allow_pickle=False).tobytes(order='C')):
                row['unexpected_factor_files'] = {}
                for name, array in (('unexpected_transition.npy', transition),
                                    ('unexpected_initial.npy', initial)):
                    row['unexpected_factor_files'][name] = save_array(
                        output.parent.parent, case_dir / name, array)
                raise RuntimeError('録音間で実Viterbi遷移・初期因子が異なります')
        row.update(status='factors_saved', finished_at_utc=now(), frames=frames,
                   pitch_bins=PITCH_BINS, states=STATES,
                   warnings=_warning_records(found),
                   files=file_manifest(case_dir, files),
                   shared_factors=identity(common_dir / 'factor-manifest.json'),
                   candidate_bin_collision_counts='unmeasured',
                   candidate_bin_clipping_counts='unmeasured')
    except Exception:
        row.update(status='failed', finished_at_utc=now(), traceback=traceback.format_exc(),
                   warnings=_warning_records(found))
    write_new(case_dir / 'result.json', row)
    budget(output.parent.parent)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', required=True, type=Path)
    parser.add_argument('--input-root', required=True, type=Path)
    parser.add_argument('--owner', required=True, type=int, choices=(0, 1, 2))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare_root(args.output)
    try:
        environment = check_environment()
        cases = checked_cases(args.input_manifest, args.input_root, args.owner)
        contract = {'kind': 'fixed120_pyin_factor_extraction', 'owner': args.owner,
                    'started_at_utc': now(), 'environment': environment,
                    'input_manifest': identity(args.input_manifest),
                    'planned_cases': len(cases), 'case_ids': [c['id'] for c in cases],
                    'options': PYIN_OPTIONS, 'expected_pitch_bins': PITCH_BINS,
                    'expected_states': STATES, 'expected_total_frames_all_owners': 123307,
                    'source_files': file_manifest(ROOT, sorted(Path(__file__).parent.glob('*.py')))}
        write_new(args.output / 'contract.json', contract)
        common_dir = args.output / 'common'
        common_dir.mkdir()
        (args.output / 'cases').mkdir()
        for index, case in enumerate(cases, start=1):
            row = extract_case(case, args.output, common_dir)
            write_current(args.output / 'summary.json',
                          {'kind': 'factor_extraction_status', 'owner': args.owner,
                           'planned': len(cases), 'visited': index,
                           'unattempted': len(cases) - index,
                           'saved': sum(read(p)['status'] == 'factors_saved'
                                        for p in (args.output / 'cases').glob('*/result.json')),
                           'last_case': row['case'], 'last_status': row['status']})
        complete = read(args.output / 'summary.json')['saved'] == len(cases)
        seal_owner(args.output)
        return 0 if complete else 2
    except Exception:
        write_new(args.output / 'owner-failure.json',
                  {'status': 'failed_before_or_during_owner', 'traceback': traceback.format_exc(),
                   'recorded_at_utc': now()})
        seal_owner(args.output)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
