"""Execute comparison fixtures and preserve all outcomes, including failures."""
from __future__ import annotations

from .logging_utils import LoggedArgumentParser, configure_logging, run_cli, run_process
import logging

if __name__ == '__main__':
    configure_logging('run')

import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.io import wavfile

from .fixtures import make_synthetic_cases
from .metrics import compare_waveforms, pitch_metrics, estimate_f0_yin, _band_metrics
from . import world, audio_samples, methods, hnm_diagnostics

ROOT = Path(__file__).resolve().parents[1]


def digest(x):
    return hashlib.sha256(np.asarray(x, dtype='<f8').tobytes()).hexdigest()


def read_mono(path):
    sr, x = wavfile.read(path)
    if x.ndim != 1:
        raise ValueError('stereo is not silently downmixed')
    if x.dtype.kind == 'i':
        x = x.astype(float) / (2 ** (x.dtype.itemsize * 8 - 1))
    elif x.dtype.kind == 'u':
        x = (x.astype(float) - 128) / 128
    else:
        x = x.astype(float)
    return sr, x


def natural_cases(data_root):
    for speaker in ('5142-36586', '7021-79759'):
        path = data_root / f'librispeech_{speaker}.wav'
        sr, x = read_mono(path)
        # Fixed predeclared excerpt; never choose the easiest section per method.
        x = x[:6*sr]
        yield dict(id=f'librispeech_{speaker}_first6s', kind='natural_speech',
                   x=x, sr=sr, f0_truth=None, speaker=speaker.split('-')[0],
                   source_file=path.name, source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   excerpt_start_sample=0, excerpt_samples=len(x))


def relative_pitch(base, edited, sr, requested_cents):
    a, b = estimate_f0_yin(base, sr), estimate_f0_yin(edited, sr)
    if len(a['f0_hz']) != len(b['f0_hz']):
        return {'status': 'different_time_grids', 'valid_pairs': 0}
    fa, fb = a['f0_hz'], b['f0_hz']
    ok = (fa > 0) & (fb > 0)
    err = abs(1200*np.log2(fb[ok]/fa[ok])-requested_cents)
    return dict(status='estimated_relative_change_not_ground_truth', total_frames=len(fa),
                valid_pairs=int(ok.sum()), voiced_in_base=int((fa>0).sum()),
                voiced_in_edit=int((fb>0).sum()),
                p95_error_cents=float(np.percentile(err,95)) if len(err) else None)


def level_delta(a, b):
    ra, rb = np.sqrt(np.mean(a*a)), np.sqrt(np.mean(b*b))
    return float(20*np.log10(rb/ra)) if ra > 0 and rb > 0 else None


def event_diagnostic(y, sr, expected_time):
    energy = np.convolve(y*y, np.ones(max(1, round(sr*.005))), mode='same')
    if float(energy.max()) <= 1e-14:
        return {'status':'no_detectable_event','expected_s':expected_time,'error_ms':None}
    center = int(np.argmax(energy)) / sr
    return {'status':'peak_energy_diagnostic','expected_s':expected_time,'detected_s':center,
            'error_ms':1000*(center-expected_time)}


def run(args):
    cases = [c for sr in args.sample_rates for c in make_synthetic_cases(sr)]
    data_status = []
    if not args.no_natural:
        try:
            cases += list(natural_cases(args.data_root))
            data_status.append({'status':'loaded','speakers':2,'excerpts':2,'seconds_per_excerpt':6})
        except Exception as e:
            logging.exception('自然音声の取得・読み込みに失敗')
            data_status.append({'status':'blocked','error':str(e)})
    selected_methods = methods.METHODS
    base = json.loads((ROOT/'BASELINE.json').read_text())
    comparison_reference=base['method'] or base['comparison_reference']
    if comparison_reference not in selected_methods:
        raise ValueError(f'Current comparison/base method is unavailable: {comparison_reference}')
    try:
        head = run_process(['git','rev-parse','HEAD'],cwd=ROOT).stdout.strip()
    except (OSError,subprocess.CalledProcessError):
        logging.exception('実行版の取得に失敗')
        head = None
    report = dict(schema_version=2, formal_base=base,
                  environment={'python':platform.python_version(),'numpy':np.__version__,
                               'scipy':scipy.__version__,'platform':platform.platform()},
                  parent_commit=head, source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((ROOT/'vocoderbench').glob('*.py'))},
                  alignment='none', normalization='none', data_status=data_status,
                  fixture_seed=20261011, comparison_reference=comparison_reference,
                  cases=[], resynthesis=[], operations=[], decoder_only=[], calibration=[], diagnostics=[])
    saved_audio = []
    for case in cases:
        x, sr = case['x'], case['sr']
        report['cases'].append({**{k:v for k,v in case.items() if k not in ('x','f0_truth')},
                                'n_samples':len(x),'input_float64_sha256':digest(x)})
        measured_input = compare_waveforms(x,x,sr,case['f0_truth'])
        report['calibration'].append({'case':case['id'],'measurement':measured_input})
        audio_samples.collect(saved_audio, case, 'identity', x)
        for method in selected_methods:
            row = dict(case=case['id'],kind=case['kind'],method=method,base_method=base['method'],
                       decoder_family='自作HNM' if method == 'hnm' else 'WORLD',
                       f0_source='正規化自己相関' if method == 'hnm' else 'WORLD Harvest')
            begin = time.perf_counter()
            try:
                params = methods.encode(method, x, sr)
                y = methods.decode(method, params)
                elapsed = time.perf_counter()-begin
                repeated = methods.decode(method, params)
                row.update(methods.metadata(method, params))
                row['analysis_pitch_against_truth'] = hnm_diagnostics.feature_pitch(params, case['f0_truth'], sr)
                if method == 'hnm':
                    report['diagnostics'].extend(hnm_diagnostics.inspect(case, params, y))
                audio_samples.collect(saved_audio, case, method, y)
                row.update(status='measured',seconds=elapsed,rtf=elapsed/(len(x)/sr),
                           output_sha256=digest(y),repeat_max_abs_diff=float(np.max(abs(y-repeated))),
                           measurement=compare_waveforms(x,y,sr,case['f0_truth']))
                if case['kind']=='transient_diagnostic':
                    row['event']=event_diagnostic(y,sr,.3)
                if params is not None and sr==16000 and (case['id'].startswith(('harmonic_110_','impulse_','voiced_unvoiced_')) or case['kind']=='natural_speech'):
                    for name, kwargs in [('pitch_up3',dict(pitch_semitones=3)),('pitch_down3',dict(pitch_semitones=-3)),
                                         ('gain_up6',dict(gain_db=6)),('gain_down6',dict(gain_db=-6)),('time_1p25',dict(time_scale=1.25))]:
                        op = dict(case=case['id'],method=method,operation=name,request=kwargs)
                        try:
                            edited = methods.edit(method, params,**kwargs)
                            ey = methods.decode(method, edited)
                            op.update(status='measured',requested_samples=edited.n_samples,output_samples=len(ey),
                                      length_error_samples=len(ey)-edited.n_samples,finite=bool(np.isfinite(ey).all()),
                                      peak=float(np.max(abs(ey))),level_delta_db=level_delta(y,ey))
                            if 'pitch_semitones' in kwargs:
                                op['band_change_after_pitch'] = _band_metrics(y, ey, sr)
                            if 'gain_db' in kwargs:
                                op['gain_tracking_error_db'] = None if op['level_delta_db'] is None else op['level_delta_db']-kwargs['gain_db']
                            if 'time_scale' not in kwargs:
                                op['relative_pitch']=relative_pitch(y,ey,sr,kwargs.get('pitch_semitones',0)*100)
                                if case['f0_truth'] is not None:
                                    op['pitch_against_known_truth']=pitch_metrics(ey,sr,case['f0_truth']*2**(kwargs.get('pitch_semitones',0)/12))
                            if case['kind']=='transient_diagnostic':
                                op['event']=event_diagnostic(ey,sr,.3*kwargs.get('time_scale',1))
                        except Exception as e:
                            logging.exception('操作に失敗: %s / %s / %s', case['id'], method, name)
                            op.update(status='failed',error=f'{type(e).__name__}: {e}')
                        report['operations'].append(op)
            except Exception as e:
                logging.exception('解析・再合成に失敗: %s / %s', case['id'], method)
                row.update(status='failed',error=f'{type(e).__name__}: {e}')
            if row.get('measurement', {}).get('status', 'ok') != 'ok':
                logging.error('測定が完了しませんでした: %s / %s / %s', case['id'], method, row['measurement']['status'], stack_info=True)
            report['resynthesis'].append(row)
            print(f"{case['id']} {method}: {row['status']}",flush=True)
    for method in selected_methods:
        for f0 in (0., 140.):
            row = {'method': method, 'f0_hz': f0, 'sample_rate': 16000}
            try:
                params = methods.handmade(method, f0)
                y = methods.decode(method, params)
                row.update(status='measured', output_samples=len(y), finite=bool(np.isfinite(y).all()),
                           pitch=pitch_metrics(y,16000,np.full(len(y),f0)))
            except Exception as e:
                logging.exception('デコーダー単体の合成に失敗: %s / %s Hz', method, f0)
                row.update(status='failed', error=str(e))
            report['decoder_only'].append(row)
    report['unsupported_operations'] = []
    report['native_builds']={}
    for name, p in [('world', world.library_path().parent/'build.json')]:
        if p.exists():
            meta=json.loads(p.read_text())
            report['native_builds'][name]={k:v for k,v in meta.items() if k!='command'}
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/'results.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    audio_samples.save(saved_audio, args.output)
    from .report import render
    render(report,args.output/'index.html')
    failures=sum(r['status']=='failed' or r.get('measurement',{}).get('status')!='ok' for r in report['resynthesis'])
    failures+=sum(r['status']=='failed' for r in report['operations']+report['decoder_only'])
    failures+=sum(r['status']=='blocked' for r in data_status)
    print(f'Report: {args.output}/index.html; failed cases: {failures}',flush=True)
    return failures


def main():
    parser=LoggedArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs'/'latest')
    parser.add_argument('--data-root',type=Path,default=ROOT/'data'/'cache')
    parser.add_argument('--sample-rates',nargs='+',type=int,default=[16000,24000,48000])
    parser.add_argument('--no-natural',action='store_true')
    args=parser.parse_args()
    failures=run(args)
    if failures:
        raise SystemExit(1)


if __name__=='__main__':
    raise SystemExit(run_cli(main, 'run'))
