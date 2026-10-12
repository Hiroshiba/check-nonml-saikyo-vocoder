"""外部の雑音合成5候補を共通解析・固定入力で比較し、逐次保存する。"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
import importlib
import importlib.metadata
import importlib.util
import json
import logging
import multiprocessing
import os
from pathlib import Path
import platform
import sys
import traceback

import numpy as np

from . import corpus, hnm, hnm_synthesis
from .benchmark_io import ROOT, SEEDS, now, read, sha, seed_summary, temporal_scalars, write
from .extended_metrics import _estoi, _full_scale
from .logging_utils import LoggedArgumentParser, configure_logging, run_cli
from .metrics import compare_waveforms
from .temporal_metrics import measure_temporal

METHODS = ('hnm', 'A', 'B', 'C', 'D', 'E')
_modules = {}


def initialize_worker(candidate_root):
    configure_logging('noise-screen-worker')
    _modules['hnm'] = hnm_synthesis
    for key in METHODS[1:]:
        directory = Path(candidate_root) / key
        name = f'_noise_screen_{key}'
        spec = importlib.util.spec_from_file_location(
            name, directory / '__init__.py', submodule_search_locations=[str(directory)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _modules[key] = importlib.import_module(name + '.hnm_synthesis')


def contract_for(args):
    sources = {p.name: sha(p) for p in (ROOT / 'vocoderbench').glob('*.py')}
    versions = {}
    for name in ('numpy', 'scipy', 'pystoi', 'torch', 'torchaudio', 'torchvision',
                 'transformers', 'timm', 'librosa', 'utmosv2'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    candidates = {}
    for key in METHODS[1:]:
        directory = args.candidates / key
        if directory.is_relative_to(ROOT) or not (directory / 'hnm_synthesis.py').is_file():
            raise ValueError(f'候補はリポジトリ外のパッケージで指定してください: {directory}')
        candidates[key] = {p.relative_to(directory).as_posix(): sha(p)
                           for p in sorted(directory.rglob('*')) if p.is_file()
                           and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    return {'schema': 'noise-screen-v1', 'formal_base': read(ROOT / 'BASELINE.json'),
            'baseline_sha256': sha(ROOT / 'BASELINE.json'), 'sources': sources,
            'candidate_sources': candidates, 'manifest_sha256': sha(args.manifest),
            'input_records': read(args.manifest)['entries'], 'criteria_sha256': sha(args.criteria),
            'lock_sha256': sha(ROOT / 'uv.lock'), 'python': platform.python_version(),
            'platform': platform.platform(), 'dependencies': versions,
            'methods': list(METHODS), 'noise_seeds': list(SEEDS), 'mos_noise_seed': 0,
            'mos_extraction_seed': 20261012, 'mos_repetitions': 1, 'mos_threads': 1,
            'workers': 2, 'threads_per_worker': 1, 'alignment': 'none', 'normalization': 'none',
            'analysis': 'single_current_base_encode_per_recording',
            'world': 'not_run; historical_reference_only',
            'role': 'candidate_screening_not_automatic_adoption'}


def acoustic_case(task):
    case, output, retry = task
    output = Path(output)
    identifier, x, sr = case['id'], case['x'], case['sr']
    part = output / 'parts' / f'{identifier}.json'
    waves = output / 'waveforms' / identifier
    waves.mkdir(parents=True, exist_ok=True)
    if part.exists():
        data = read(part)
    else:
        data = {'case': {k: v for k, v in case.items() if k not in ('x', 'f0_truth')},
                'original': {'method': 'identity', 'mos': {'status': 'pending', 'value': None}},
                'rows': [{'case': identifier, 'method': method, 'status': 'pending',
                          'mos': {'status': 'pending', 'value': None},
                          'seed_diagnostics': [{'seed': s, 'status': 'pending'} for s in SEEDS]}
                         for method in METHODS]}
    np.save(waves / 'identity.npy', x)
    data['original']['waveform_sha256'] = sha(waves / 'identity.npy')
    write(part, data)
    selected = [(row, item) for row in data['rows'] for item in row['seed_diagnostics']
                if item['status'] == 'pending' or (retry and item['status'] == 'failed')]
    if not selected:
        return identifier
    for row, item in selected:
        if item['status'] == 'failed':
            row.setdefault('failure_history', []).append(dict(item))
    try:
        params = hnm.encode(x, sr)
        harmonic = hnm.decode(replace(params, noise_psd=np.zeros_like(params.noise_psd)))
    except Exception as error:
        logging.exception('共通解析失敗: %s', identifier)
        for row, item in selected:
            item.update(status='failed', error=str(error), traceback=traceback.format_exc())
            row['status'] = 'partial_failure'
        write(part, data)
        return identifier
    for row, item in selected:
        seed, method = item['seed'], row['method']
        if seed == 0:
            (waves / f'{method}.npy').unlink(missing_ok=True)
            row['mos'] = {'status': 'pending', 'value': None}
        item.clear()
        item.update(seed=seed, status='failed')
        try:
            y = harmonic + _modules[method]._noise(params, seed)
            if y.shape != x.shape or not np.isfinite(y).all():
                raise ValueError('出力の長さまたは有限性が不正')
            basic = compare_waveforms(x, y, sr)
            if basic['status'] != 'ok':
                raise ValueError(f'音響比較不能: {basic["status"]}')
            temporal = measure_temporal(x, y, sr)
            values = temporal_scalars(temporal)
            values.update(mr_stft_db=basic['mr_stft_log_magnitude_mae_db'],
                          band_mae_db=basic['band_energy']['active_band_mae_db'],
                          rms_gain_error_db=basic['rms_gain_error_db'], output_peak=basic['output_peak'])
            item.update(status='measured', values=values, full_scale=_full_scale(y))
            if seed == 0:
                row.update(measurement=basic, temporal=temporal, estoi=_estoi(x, y, sr, True))
                np.save(waves / f'{method}.npy', y)
                row['waveform_sha256'] = sha(waves / f'{method}.npy')
        except Exception as error:
            logging.exception('合成・測定失敗: %s / %s / %s', identifier, method, seed)
            item.update(status='failed', error=str(error), traceback=traceback.format_exc())
        row['status'] = ('measured' if all(v['status'] == 'measured' for v in row['seed_diagnostics'])
                         else 'partial_failure')
        row['seed_summary'] = seed_summary(row['seed_diagnostics'])
        write(part, data)
        logging.info('雑音比較: %s / %s / seed=%s %s', identifier, method, seed, item['status'])
    return identifier


def score_mos(args, cases):
    from .mos import MosEvaluator
    evaluator = MosEvaluator(args.mos_cache, repetitions=1, seed=20261012, threads=1)
    evaluator.prepare()
    write(args.output / 'mos_provenance.json', evaluator.provenance)
    for case in cases:
        path = args.output / 'parts' / f'{case["id"]}.json'
        if not path.exists():
            raise ValueError(f'音響測定が未実行です: {case["id"]}')
        data = read(path)
        for row in [data['original'], *data['rows']]:
            if row['mos']['status'] != 'pending' and not (
                    args.retry_failed and row['mos']['status'] == 'failed'):
                continue
            if row['mos']['status'] == 'failed':
                row.setdefault('mos_failure_history', []).append(row['mos'])
            wave = args.output / 'waveforms' / case['id'] / f'{row["method"]}.npy'
            valid = row['method'] == 'identity' or any(
                s['seed'] == 0 and s['status'] == 'measured' for s in row['seed_diagnostics'])
            if valid and wave.exists():
                if row.get('waveform_sha256') and sha(wave) != row['waveform_sha256']:
                    raise ValueError(f'保存波形のhashが変わりました: {wave}')
                row['mos'] = evaluator.predict(np.load(wave, allow_pickle=False), case['sr'],
                                               language=case['language'], style=case['style'])
            else:
                row['mos'] = {'status': 'failed', 'value': None, 'reason': '有効なseed 0波形なし'}
                logging.error('MOS入力欠落: %s', wave, stack_info=True)
            write(path, data)
            logging.info('MOS: %s / %s %s', case['id'], row['method'], row['mos']['status'])


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=corpus.MANIFEST)
    parser.add_argument('--cache', type=Path, default=corpus.CACHE)
    parser.add_argument('--candidates', type=Path, default=ROOT.parent / 'noise_candidates')
    parser.add_argument('--criteria', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mos-cache', type=Path, default=ROOT / '.cache/mos')
    parser.add_argument('--stage', choices=('acoustic', 'mos', 'all'), default='acoustic')
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    for key in ('manifest', 'cache', 'candidates', 'criteria', 'output', 'mos_cache'):
        setattr(args, key, getattr(args, key).resolve())
    contract = json.loads(json.dumps(contract_for(args)))
    path = args.output / 'contract.json'
    if path.exists() and read(path) != contract:
        raise ValueError('保存済み条件と不一致です。別の出力先を指定してください')
    if not path.exists():
        if args.output.exists() and any(args.output.iterdir()):
            raise ValueError('条件記録のない既存出力先へ書き込めません')
        write(path, contract)
    cases = list(corpus.load_cases(args.manifest, args.cache))
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('固定入力が空またはIDが重複しています')
    execution_path = args.output / 'execution.json'
    execution = read(execution_path) if execution_path.exists() else {'attempts': []}
    execution['attempts'].append({'started_at': now(), 'stage': args.stage,
                                  'retry_failed': args.retry_failed})
    write(execution_path, execution)
    if args.stage in ('all', 'acoustic'):
        for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                         'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
            os.environ[variable] = '1'
        with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'),
                                 initializer=initialize_worker, initargs=(args.candidates,)) as pool:
            futures = [pool.submit(acoustic_case, (case, args.output, args.retry_failed)) for case in cases]
            for index, future in enumerate(as_completed(futures), 1):
                logging.info('録音完了 %s/%s: %s', index, len(cases), future.result())
    if args.stage in ('all', 'mos'):
        score_mos(args, cases)
    parts = [read(args.output / 'parts' / f'{case["id"]}.json') for case in cases]
    failures = sum(row['status'] != 'measured' or row.get('estoi', {}).get('status') != 'measured'
                   for part in parts for row in part['rows'])
    if args.stage in ('all', 'mos'):
        failures += sum(row['mos']['status'] != 'measured'
                        for part in parts for row in [part['original'], *part['rows']])
    write(args.output / 'results.json', {'contract': contract, 'finished_at': now(), 'stage': args.stage,
          'status': 'completed' if not failures else 'partial_failure', 'parts': parts,
          'planned_recordings': len(cases), 'failures': failures})
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'noise-screen'))
