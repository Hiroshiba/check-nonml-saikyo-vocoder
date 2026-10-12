"""固定入力の雑音seed・時間・帯域診断。採否や新しいMOS評価は行わない。"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import platform
import traceback

import numpy as np
import scipy
from scipy import signal

from . import corpus, hnm
from .benchmark_io import ROOT, external_candidate, now, read, sha, write
from .extended_metrics import _estoi, _full_scale
from .logging_utils import LoggedArgumentParser, run_cli, run_process
from .metrics import compare_waveforms
from .temporal_metrics import _envelope_metrics, _windows

BANDS = (("全帯域", None), ("0–300 Hz", (0, 300)),
         ("300–1000 Hz", (300, 1000)), ("1000–3000 Hz", (1000, 3000)),
         ("3000–6000 Hz", (3000, 6000)), ("6000–11000 Hz", (6000, 11000)))


def _hash_array(x):
    return hashlib.sha256(np.asarray(x, dtype='<f8').tobytes()).hexdigest()


def _filtered(x, sr, edges):
    if edges is None:
        return x, {"kind": "none"}
    cutoff = edges[1] if edges[0] == 0 else edges
    sos = signal.butter(4, cutoff, fs=sr, output='sos',
                        btype='lowpass' if edges[0] == 0 else 'bandpass')
    pad = min(len(x) - 1, 3 * (2 * len(sos) + 1))
    return signal.sosfiltfilt(sos, x, padtype='even', padlen=pad), {
        "kind": "butterworth-forward-backward", "prototype_order": 4,
        "edges_hz": list(edges), "pad_type": "even", "pad_samples": pad}


def local_envelopes(x, y, sr):
    """全録音をフィルタしてから窓中心時刻で非重複1秒区間へ割り当てる。"""
    rows = []
    seconds = len(x) / sr
    for name, edges in BANDS:
        band = {"name": name, "edges_hz": edges, "windows": []}
        rows.append(band)
        if edges and edges[1] >= sr / 2:
            band.update(status='outside_nyquist', reason='上端がNyquist周波数以上')
            continue
        a, spec = _filtered(x, sr, edges)
        b, _ = _filtered(y, sr, edges)
        band.update(status='measured', filter=spec)
        for window in (10, 40):
            pa, times, starts, size, hop = _windows(a, sr, window)
            pb, _, _, _, _ = _windows(b, sr, window)
            floor = max(1e-7, float(np.sqrt(pa.max())) * 1e-3) if len(pa) else 1e-7
            denominator = float(np.sum(pa))
            segments = []
            for start in range(int(np.ceil(seconds))):
                mask = (times >= start) & (times < start + 1)
                error = float(np.sum((np.sqrt(pb[mask]) - np.sqrt(pa[mask])) ** 2))
                segments.append({"start_s": start, "end_s": min(start + 1, seconds),
                                 "frames": int(mask.sum()),
                                 "status": 'measured' if mask.any() else 'no_complete_frames',
                                 "reference_energy_fraction_in_band":
                                 float(np.sum(pa[mask])) / denominator if denominator else None,
                                 "metrics": _envelope_metrics(pa[mask], pb[mask], floor),
                                 "squared_error_contribution_to_whole_band":
                                 error / denominator if denominator else None})
            band['windows'].append({"window_ms": window, "hop_ms": 5,
                                    "status": 'measured' if len(pa) else 'no_complete_frames',
                                    "uncovered_tail_samples": int(len(x) - starts[-1] - size)
                                    if len(starts) else len(x),
                                    "whole": _envelope_metrics(pa, pb, floor), "segments": segments})
    return rows


def _difference(a, b):
    return b - a if a is not None and b is not None else None


def paired(base, other):
    rows = []
    for a, b in zip(base['bands'], other['bands']):
        if a['status'] != 'measured' or b['status'] != 'measured':
            continue
        for u, v in zip(a['windows'], b['windows']):
            segments = []
            for p, q in zip(u['segments'], v['segments']):
                segments.append({"start_s": p['start_s'], "end_s": p['end_s'],
                                 "delta_nrmse": _difference(p['metrics']['rms_envelope_nrmse'],
                                                            q['metrics']['rms_envelope_nrmse']),
                                 "delta_squared_error_contribution": _difference(
                                     p['squared_error_contribution_to_whole_band'],
                                     q['squared_error_contribution_to_whole_band'])})
            rows.append({"band": a['name'], "window_ms": u['window_ms'],
                         "delta_nrmse": _difference(u['whole']['rms_envelope_nrmse'],
                                                    v['whole']['rms_envelope_nrmse']),
                         "segments": segments})
    return {"case": base['case'], "seed": base['seed'], "method": other['method'],
            "direction": 'other_minus_current_base', "bands": rows,
            "delta_estoi": _difference(base['estoi']['value'], other['estoi']['value'])}


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'data/jvs_available_v1.json')
    parser.add_argument('--cache', type=Path, default=corpus.CACHE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=list(range(8)))
    parser.add_argument('--style', default='whisper', help='発声名、またはall')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--candidate-label', default='外部診断比較器')
    parser.add_argument('--candidate-revision', help='外部比較器を復元したコミット等の識別子')
    parser.add_argument('--world', action='store_true')
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds) or min(args.seeds) < 0:
        parser.error('seedは重複しない非負整数を指定してください')
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError('既存結果へ継ぎ足さず、空の出力先を指定してください')
    modules = {'hnm': hnm}
    labels = {'hnm': read(ROOT / 'BASELINE.json')['version']}
    if args.candidate:
        modules['candidate'] = external_candidate(args.candidate)
        labels['candidate'] = args.candidate_label
    if args.world:
        from . import world
        modules['world_harvest'] = world
        labels['world_harvest'] = 'WORLD（Harvest）'
    manifest = read(args.manifest)
    selected = [e for e in manifest['entries'] if args.style == 'all' or e['style'] == args.style]
    if not selected:
        raise ValueError('指定した発声の固定入力がありません')
    names = ['noise_stability.py', 'corpus.py', 'benchmark_io.py', 'temporal_metrics.py',
             'extended_metrics.py', 'metrics.py', 'logging_utils.py', 'world.py', 'build_world.py']
    sources = {name: sha(ROOT / 'vocoderbench' / name) for name in names}
    sources.update({p.name: sha(p) for p in (ROOT / 'vocoderbench').glob('hnm*.py')})
    contract = {"schema": 'noise-stability-v1', "created_at": now(),
                "study_role": 'exploratory_seed_diagnosis_not_formal_adoption',
                "formal_base": read(ROOT / 'BASELINE.json'), "method_labels": labels,
                "manifest_sha256": sha(args.manifest), "selected_input_ids": [e['id'] for e in selected],
                "dependency_lock_sha256": sha(ROOT / 'uv.lock'), "resume_supported": False,
                "input_records": selected, "noise_seeds": args.seeds, "source_sha256": sources,
                "git_commit": run_process(['git', 'rev-parse', 'HEAD'], cwd=ROOT).stdout.strip(),
                "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                "scipy": scipy.__version__, "platform": platform.platform()},
                "normalization": 'none', "alignment": 'none', "public_audio": False,
                "filter_policy": '全録音にButterworth4次前後向き・even延長。区間ごとに再始動しない',
                "segment_policy": '1秒非重複、窓中心時刻で所属、末尾は実長',
                "mos": {"status": 'not_measured', "reason": '音響診断。既存MOSを再測定と扱わない'},
                "limitations": ['seedは独立話者ではない', '帯域間寄与は単純合計できない',
                                'eSTOI・MOS低下の因果は同定しない',
                                '正式120録音の採否評価とは別研究', 'Windows再計算は旧Linux実行と同一条件ではない']}
    if args.candidate:
        contract['candidate_revision'] = args.candidate_revision
        contract['candidate_source_sha256'] = {
            str(p.relative_to(args.candidate)): sha(p) for p in args.candidate.rglob('*.py')}
    if args.world:
        contract['world_binary_sha256'] = sha(world.library_path())
        contract['world_source_lock'] = read(ROOT / 'vocoderbench/world.lock.json')
    write(args.output / 'contract.json', contract)
    result = {"contract": contract, "started_at": now(), "status": 'running',
              "planned_syntheses": len(selected) * sum(1 if m == 'world_harvest' else len(args.seeds)
                                                      for m in modules),
              "rows": [], "pairs": [], "failures": []}
    write(args.output / 'results.json', result)
    selected_ids = {e['id'] for e in selected}
    try:
        for case in corpus.load_cases(args.manifest, args.cache):
            if case['id'] not in selected_ids:
                continue
            x, sr = case['x'], case['sr']
            current = {}
            for name, module in modules.items():
                seeds = [0] if name == 'world_harvest' else args.seeds
                try:
                    params = module.encode(x, sr)
                except Exception as error:
                    logging.exception('解析失敗: %s / %s', case['id'], name)
                    result['failures'].append({'case': case['id'], 'method': name,
                                               'stage': 'encode', 'error': str(error),
                                               'traceback': traceback.format_exc()})
                    result['rows'].extend({'case': case['id'], 'speaker': case['speaker'],
                                           'style': case['style'], 'method': name, 'seed': seed,
                                           'status': 'failed', 'stage': 'encode', 'error': str(error)}
                                          for seed in seeds)
                    write(args.output / 'results.json', result)
                    continue
                for seed in seeds:
                    row = {'case': case['id'], 'speaker': case['speaker'], 'style': case['style'],
                           'method': name, 'seed': seed, 'status': 'failed', 'sample_rate': sr,
                           'seconds': len(x) / sr, 'input_float64_sha256': _hash_array(x)}
                    try:
                        y = module.decode(params) if name == 'world_harvest' else module.decode(params, seed=seed)
                        if y.shape != x.shape or not np.isfinite(y).all():
                            raise ValueError('出力の長さまたは有限値が不正')
                        acoustic = compare_waveforms(x, y, sr)
                        if acoustic['status'] != 'ok':
                            raise ValueError(f"音響測定不能: {acoustic['status']}")
                        row.update(status='measured', output_float64_sha256=_hash_array(y),
                                   acoustic=acoustic, full_scale=_full_scale(y),
                                   estoi=_estoi(x, y, sr, True), bands=local_envelopes(x, y, sr))
                        current[name, seed] = row
                        if row['estoi']['status'] != 'measured':
                            result['failures'].append({'case': case['id'], 'method': name,
                                                       'seed': seed, 'stage': 'estoi',
                                                       'detail': row['estoi']})
                    except Exception as error:
                        logging.exception('診断失敗: %s / %s / %d', case['id'], name, seed)
                        row.update(error=str(error), traceback=traceback.format_exc())
                        result['failures'].append({'case': case['id'], 'method': name, 'seed': seed,
                                                   'stage': 'decode_or_measure', 'detail': row['error']})
                    result['rows'].append(row)
                    write(args.output / 'results.json', result)
                    logging.info('診断: %s / %s / seed=%d %s', case['id'], name, seed, row['status'])
            for (name, seed), row in current.items():
                if name != 'hnm' and ('hnm', seed) in current:
                    result['pairs'].append(paired(current['hnm', seed], row))
            write(args.output / 'results.json', result)
    except Exception as error:
        logging.exception('固定入力の診断を継続できません')
        result['failures'].append({'stage': 'input_or_execution', 'error': str(error),
                                   'traceback': traceback.format_exc()})
    result['completed_syntheses'] = sum(r['status'] == 'measured' for r in result['rows'])
    result['finished_at'] = now()
    complete = result['completed_syntheses'] == result['planned_syntheses']
    result['status'] = 'completed' if complete and not result['failures'] else 'partial_failure'
    write(args.output / 'results.json', result)
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'noise-stability'))
