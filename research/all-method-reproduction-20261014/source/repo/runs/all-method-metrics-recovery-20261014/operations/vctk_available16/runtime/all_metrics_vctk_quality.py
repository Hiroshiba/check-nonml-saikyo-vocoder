"""VCTK availability16の全8同一48 kHz区間を派生し、公式ViSQOL Audioを正式計測する。"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import logging
import math
from pathlib import Path
import time
import traceback

import numpy as np
import scipy
from scipy.signal import resample_poly

from all_metrics_common import METHODS, ROOT, freeze, now, read
from all_metrics_vctk_inputs import VCTK_RUN, pcm_hash
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, measure_repeated, sha256, write_json
from vocoderbench.quality_visqol import VisqolAudio


def wave_record(wave):
    return {'samples': len(wave), 'sample_rate': 48000, 'seconds': len(wave) / 48000,
            'float64_sha256': pcm_hash(wave),
            'float32_sha256': hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest(),
            'peak': float(np.max(np.abs(wave))), 'over_one_fraction': float(np.mean(np.abs(wave) > 1))}


def amplitude_issue(wave, native_peak=None):
    rounded = np.rint(wave * 32768)
    limits = {'minimum': float(rounded.min()), 'maximum': float(rounded.max()),
              'below_minimum_count': int(np.sum(rounded < -32768)),
              'above_maximum_count': int(np.sum(rounded > 32767))}
    invalid = ((native_peak is not None and native_peak > 1) or np.max(np.abs(wave)) > 1
               or limits['minimum'] < -32768 or limits['maximum'] > 32767)
    return invalid, limits


def derive_case(spec, signature):
    """Keep full native files, reproduce derived arrays in memory, save their exact PCM hashes."""
    row = {'case': spec['id'], 'speaker': spec['speaker'], 'status': 'pending',
           'contract_sha256': signature, 'started_at_utc': now(), 'outputs': {},
           'sample_rate': 48000, 'reference_original_seconds': spec['samples'] / 48000}
    if sha256(spec['path']) != spec['sha256']:
        raise ValueError('原音NPYの固定hash不一致')
    original = np.load(spec['path'], allow_pickle=False)
    if pcm_hash(original) != spec['metadata']['excerpt_float64_sha256']:
        raise ValueError('原音PCM64の固定hash不一致')
    waves, missing, failed = {}, [], {}
    for method in METHODS:
        folder = VCTK_RUN / 'native' / method / spec['id']
        path = folder / 'unedited.json'
        if not path.exists():
            progress = folder / 'case-progress.json'
            if progress.exists() and read(progress).get('status') == 'failed':
                failed[method] = {'path': str(progress), 'sha256': sha256(progress), 'record': read(progress)}
            else:
                missing.append(method)
            continue
        native = read(path)
        if native['status'] != 'measured':
            failed[method] = {'path': str(path), 'sha256': sha256(path), 'record': native}
            continue
        source = path.with_suffix('.npy')
        if sha256(source) != native['audio']['file_sha256']:
            raise ValueError(f'native出力hash不一致: {spec["id"]} {method}')
        synthesis_contract = VCTK_RUN / 'synthesis-contracts' / f'{method}.json'
        if sha256(synthesis_contract) != native['contract_sha256']:
            raise ValueError('native合成契約hash不一致')
        wave = np.load(source, allow_pickle=False)
        rate = native['audio']['sample_rate']
        divisor = math.gcd(rate, 48000)
        start = time.perf_counter()
        derived = (resample_poly(wave, 48000 // divisor, rate // divisor,
                                window=('kaiser', 5.0), padtype='constant') if rate != 48000 else wave)
        if derived.ndim != 1 or not len(derived) or not np.isfinite(derived).all():
            raise ValueError('48 kHz派生が空・非有限です')
        waves[method] = derived
        row['outputs'][method] = {
            'native': native['audio'], 'native_record_sha256': sha256(path),
            'synthesis_contract_sha256': native['contract_sha256'],
            'full_analysis48': wave_record(derived),
            'resampling': {'applied': rate != 48000, 'up': 48000 // divisor,
                           'down': rate // divisor, 'wall_seconds': time.perf_counter() - start},
            'native_duration_delta_seconds': native['audio']['seconds'] - len(original) / 48000}
    if missing or failed:
        row.update(status='pending' if missing else 'upstream_failed', missing_methods=missing,
                   upstream_failures=failed, reason='全8成功native出力が揃わないため共通区間を決定しない')
        return row, None, {}
    n = min(len(original), *(len(w) for w in waves.values()))
    coverage = {'identity': n / len(original), **{m: n / len(w) for m, w in waves.items()}}
    row.update(common_samples=n, common_seconds=n / 48000, coverages=coverage,
               removed_reference_tail_samples=len(original) - n,
               reference_full=wave_record(original), finished_at_utc=now())
    for method, wave in waves.items():
        row['outputs'][method].update(removed_analysis48_tail_samples=len(wave) - n,
                                     native_time_coverage=(n / 48000) / row['outputs'][method]['native']['seconds'])
    if n < 3 * 48000 or min(coverage.values()) < .95:
        row.update(status='not_applicable', reason='共通3秒以上かつ全9波形coverage95%以上の事前条件を満たさない')
        return row, None, {}
    reference, outputs = original[:n], {m: w[:n] for m, w in waves.items()}
    row['reference_common'] = wave_record(reference)
    row['reference_pcm16_invalid'], row['reference_pcm16_rounding'] = amplitude_issue(reference)
    for method, wave in outputs.items():
        item = row['outputs'][method]
        item['common_analysis48'] = wave_record(wave)
        item['pcm16_invalid'], item['pcm16_rounding'] = amplitude_issue(wave, item['native']['peak'])
    row.update(status='measured', derivative_storage='in-memory only; full/common PCM hashes retained; native preserved')
    return row, reference, outputs


def evaluate_case(spec, backend, signature, args):
    start = time.perf_counter()
    directory = VCTK_RUN / 'quality' / spec['id']
    derivation_path = VCTK_RUN / 'analysis48' / spec['id'] / 'derivation.json'
    try:
        derived, reference, outputs = derive_case(spec, signature)
    except Exception:
        logging.exception('VCTK48派生失敗: %s', spec['id'])
        derived = {'case': spec['id'], 'speaker': spec['speaker'], 'status': 'failed',
                   'contract_sha256': signature, 'reason': '派生処理例外', 'error': traceback.format_exc()}
        reference, outputs = None, {}
    if derivation_path.exists():
        previous = read(derivation_path)
        if previous['contract_sha256'] != signature:
            raise ValueError('既存派生契約が不一致です')
        if previous['status'] not in ('pending', 'measured') and args.retry_failed:
            write_json(derivation_path.parent / 'failure_history' / f'{time.time_ns()}.json', previous)
    write_json(derivation_path, derived)
    for method in METHODS:
        path = directory / f'{method}.json'
        if path.exists():
            previous = read(path)
            if previous['contract_sha256'] != signature:
                raise ValueError('既存品質評価契約が不一致です')
            if previous['status'] == 'measured':
                if (derived['status'] != 'measured'
                        or previous['input_pcm64_sha256'] != derived['outputs'][method]['common_analysis48']['float64_sha256']
                        or previous['reference_pcm64_sha256'] != derived['reference_common']['float64_sha256']):
                    raise ValueError('既存品質成功行の入力PCM hash不一致')
                continue
            if previous['status'] != 'pending' and not args.retry_failed:
                continue
            write_json(directory / 'failure_history' / f'{method}-{time.time_ns()}.json', previous)
        row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
               'metric': 'visqol_audio', 'unit': 'MOS-LQO', 'direction': 'higher',
               'status': derived['status'], 'value': None, 'contract_sha256': signature,
               'source_manifest_sha256': read(VCTK_RUN / 'input-contract.json')['source_manifest_sha256'],
               'source_original_seconds': spec['samples'] / 48000, 'started_at_utc': now(),
               'derivation_path': str(derivation_path)}
        if derived['status'] != 'measured':
            row['reason'] = derived.get('reason', '全8同一区間の派生不成立')
        else:
            info = derived['outputs'][method]
            row.update(common_samples=derived['common_samples'], common_seconds=derived['common_seconds'],
                       native_sample_rate=info['native']['sample_rate'], native_peak=info['native']['peak'],
                       analysis48_peak=info['common_analysis48']['peak'], coverages=derived['coverages'],
                       input_pcm64_sha256=info['common_analysis48']['float64_sha256'],
                       reference_pcm64_sha256=derived['reference_common']['float64_sha256'],
                       native_audio_sha256=info['native']['file_sha256'],
                       pcm16_rounding=info['pcm16_rounding'])
            if derived['reference_pcm16_invalid'] or info['pcm16_invalid']:
                row.update(status='pcm16_range_exceeded',
                           reason='生成は成功。native/派生peak>1またはPCM16丸め範囲外。clip・音量補正せず品質値null。')
            else:
                measurement = measure_repeated(lambda: backend.score(reference, outputs[method], 48000), 1)
                row.update(status=measurement['status'], value=measurement['value'], measurement=measurement)
        row['finished_at_utc'] = now()
        write_json(path, row)
        logging.info('VCTK正式品質: %s %s %s value=%s', spec['id'], method, row['status'], row['value'])
    return {'case': spec['id'], 'derivation_status': derived['status'],
            'wall_seconds': time.perf_counter() - start,
            'statuses': {m: read(directory / f'{m}.json')['status'] for m in METHODS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True, type=int)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.batch < 2:
        raise ValueError('正式16録音の2バッチのみが対象です')
    assets = read(args.assets)
    start = time.perf_counter()
    backend = VisqolAudio(assets['metrics']['visqol_audio'], args.assets.parent,
                         VCTK_RUN / 'visqol-work', threads=2)
    initialization = time.perf_counter() - start
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_common.py', Path(__file__).parent / 'all_metrics_vctk_inputs.py',
             ROOT / 'vocoderbench/quality_core.py', ROOT / 'vocoderbench/quality_visqol.py']
    contract = {
        'schema_version': 1, 'metric': 'visqol_audio', 'planned_methods': list(METHODS),
        'planned_recordings': 16, 'planned_speakers': 4,
        'input_contract_sha256': sha256(VCTK_RUN / 'input-contract.json'),
        'inputs_sha256': sha256(VCTK_RUN / 'inputs.json'),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        'assets_path': str(args.assets.resolve()), 'assets_sha256': sha256(args.assets),
        'backend_provenance': backend.provenance, 'environment': environment(),
        'sample_rate': 48000, 'use_speech_mode': False, 'use_lattice_model': False,
        'minimum_common_seconds': 3, 'minimum_coverage_each_waveform': .95,
        'native_amplitude_rule': 'native peak>1 excludes only that method quality value; synthesis status retained',
        'pcm16_rule': 'round(32768*x), reject outside [-32768,32767], never clip or normalize',
        'resampling': {'function': 'scipy.signal.resample_poly', 'scipy_version': scipy.__version__,
                       'source_sha256': hashlib.sha256(inspect.getsource(resample_poly).encode()).hexdigest(),
                       'window': ['kaiser', 5.0], 'padtype': 'constant'},
        'comparison_samples': 'min(original and all eight successful full derived 48k lengths)',
        'alignment': False, 'gain_normalization': False, 'time_warp': False,
        'repetitions_after_first': 1, 'score_selection': 'first result only; repetitions are not independent ratings',
        'threads': 2, 'derivative_storage': 'in memory with full/common PCM64 and PCM32 hashes; native files retained',
        'ranking': 'all8-common finite measured case subset, mean within speaker then equal-weight speakers',
        'interval': 'speaker-cluster percentile bootstrap 2000 iterations seed20261014; descriptive, only4 speakers',
        'recommended_duration_stratum': 'original>=8s candidates counted from actual frozen inputs; require common>=8s for recommended interval summary'}
    contract_path = VCTK_RUN / 'quality-contract.json'
    freeze(contract_path, contract)
    signature = sha256(contract_path)
    write_json(VCTK_RUN / 'quality-initializations' / f'{time.time_ns()}.json',
               {'batch': args.batch, 'seconds': initialization, 'contract_sha256': signature,
                'started_at_utc': now()})
    rows = [evaluate_case(s, backend, signature, args)
            for s in read(VCTK_RUN / 'input-batches' / f'{args.batch:02d}.json')]
    write_json(VCTK_RUN / 'quality-batches' / f'{args.batch:02d}.json',
               {'rows': rows, 'finished_at_utc': now(), 'contract_sha256': signature})
    return int(any(s not in ('measured', 'not_applicable', 'pcm16_range_exceeded')
                   for row in rows for s in row['statuses'].values()))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-vctk-quality'))
