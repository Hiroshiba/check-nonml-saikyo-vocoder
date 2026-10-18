"""Aggregate the completed fixed saved-wave pitch observations; no remeasurement."""
import hashlib
import json
from pathlib import Path
import numpy as np

SOURCE=Path('boundary-pitch-completion-20261018/unpacked/results/summary.json')
OUT=Path('boundary-pitch-report-20261018')
EXPECTED='704d04912445bbee893d5c365bf7208cf06d38e6c90ff4db5bf7050bd890d2ee'
METHODS=('boundary_hold','original_candidate','pml')
METRICS=('mae_cents','missing_voiced_fraction','false_voiced_fraction','out_of_range_fraction','gross_over600_fraction','near_octave_error_fraction')


def value(row, metric):
    if row['status']!='measured':
        return None
    d=row['detail']
    if metric=='mae_cents':
        return row['value']
    num,den={'missing_voiced_fraction':('missing_voiced_frames','expected_voiced_frames'),
             'false_voiced_fraction':('false_voiced_frames','expected_unvoiced_frames'),
             'out_of_range_fraction':('out_of_range_frames','total_frames'),
             'gross_over600_fraction':('gross_error_over_600_cents','matched'),
             'near_octave_error_fraction':('octave_error_frames','matched')}[metric]
    denominator=d['relative_error']['count'] if den=='matched' else d[den]
    return d[num]/denominator if denominator else None


def summarize(matrix):
    rng=np.random.default_rng(20261018)
    draw=rng.integers(0,len(matrix),(2000,len(matrix)))
    boot=matrix[draw].mean(axis=1)
    return matrix.mean(axis=0),np.quantile(boot,[.025,.975],axis=0),boot


raw=SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED:
    raise ValueError('Wrong terminal input summary')
d=json.loads(raw)
if d['validation_state']!='validated_end' or len(d['rows'])!=720:
    raise ValueError('Incomplete terminal input')
records={(r['case'],r['method'],r['semitones']):r for r in d['rows']}
if len(records)!=720:
    raise ValueError('Duplicate planned measurement')
cases=list(dict.fromkeys(r['case'] for r in d['rows']))
speaker={r['case']:r['speaker'] for r in d['rows']}
results=[]
for q in (-3,3):
    for metric in METRICS:
        mappings={m:{c:value(records[c,m,q],metric) for c in cases} for m in METHODS}
        row={'semitones':q,'metric':metric,'planned_recordings':120,'own_support':{},'comparisons':{}}
        for m in METHODS:
            usable=[c for c in cases if mappings[m][c] is not None]
            groups=sorted({speaker[c] for c in usable})
            matrix=np.array([[np.mean([mappings[m][c] for c in usable if speaker[c]==s])] for s in groups])
            point,ci,_=summarize(matrix)
            row['own_support'][m]={'recordings':len(usable),'speakers':len(groups),'value':float(point[0]),'ci95':ci[:,0].tolist(),
                'generation_failed':sum(records[c,m,q]['status']=='upstream_failed' for c in cases),
                'metric_unavailable':sum(records[c,m,q]['status']!='upstream_failed' and mappings[m][c] is None for c in cases)}
        for scope,methods in [('all_three',METHODS),('boundary_vs_pml',('boundary_hold','pml')),('boundary_vs_old',('boundary_hold','original_candidate'))]:
            usable=[c for c in cases if all(mappings[m][c] is not None for m in methods)]
            groups=sorted({speaker[c] for c in usable})
            matrix=np.array([[np.mean([mappings[m][c] for c in usable if speaker[c]==s]) for m in methods] for s in groups])
            point,ci,boot=summarize(matrix)
            result={'recordings':len(usable),'speakers':len(groups),'methods':{},'case_ids':usable,'speaker_ids':groups}
            for i,m in enumerate(methods):
                result['methods'][m]={'value':float(point[i]),'ci95':ci[:,i].tolist(),
                    'descriptive_rank':int(1+sum(v<point[i] for v in point)) if scope=='all_three' and metric in ('mae_cents','missing_voiced_fraction') else None}
            if len(methods)==2:
                result['first_minus_second']={'value':float(point[0]-point[1]),'ci95':np.quantile(boot[:,0]-boot[:,1],[.025,.975]).tolist()}
            row['comparisons'][scope]=result
        results.append(row)
report={'scope':'Same-host additional pitch tracking only; not all79 quality axes or absolute F0 truth',
    'source_summary_sha256':EXPECTED,'source_manifest_sha256':d['manifest_sha256'],
    'measurement_runner_sha256':d['runner_sha256'],'aggregation_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'measurement_started_utc':d['utc'],'measurement_completed_utc':d['completed_utc'],
    'planned_rows':720,'status_counts':d['status_counts'],'methods':list(METHODS),
    'bootstrap':{'seed':20261018,'replicates':2000,'unit':'speaker','point':'recording mean within speaker then speaker equal weight'},
    'results':results}
with (OUT/'statistics.json').open('x') as f:
    json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
for r in results:
    if r['metric'] in ('mae_cents','missing_voiced_fraction'):
        print(r['semitones'],r['metric'])
        for scope in ('all_three','boundary_vs_pml','boundary_vs_old'):
            x=r['comparisons'][scope];print(scope,x['recordings'],{m:y['value'] for m,y in x['methods'].items()},x.get('first_minus_second'))
