"""Post-hoc paired editing contrasts from immutable published scalar records."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path('vocoder-candidate-pr-20261017')
BASE = ROOT/'experiments/2026-10-17/ahm-cartesian-multimetric'
OUT = Path('editing-contrast-diagnostic-20261018')
CANDIDATE = 'ahm_cartesian_node_editor_v1'

def sha(b):
    return hashlib.sha256(b).hexdigest()

summary_bytes = gzip.decompress((BASE/'ordinary/ordinary-summary.json.gz').read_bytes())
if sha(summary_bytes) != '3f3dff136fba05860c3cb2ac965724b40e4528a17aaf71257afd717ac18eeda2':
    raise ValueError('Published summary identity changed')
summary = json.loads(summary_bytes)
cohort_bytes = (ROOT/'research/pml-package-evaluation-2026-10-16/input-manifest.json').read_bytes()
if sha(cohort_bytes) != '1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193':
    raise ValueError('Cohort changed')
cohort = json.loads(cohort_bytes)['cases']
records, cases, sources = {}, [], []
for item in summary['chunk_sources']:
    path = BASE/'checkpoints'/(item['chunk_id']+'.json.gz')
    raw = gzip.decompress(path.read_bytes())
    if sha(raw) != item['sha256']:
        raise ValueError('Checkpoint identity changed')
    d = json.loads(raw)
    if d['validation_state'] != 'chunk_validated_end' or d['run_plan_sha256'] != summary['run_plan_sha256']:
        raise ValueError('Checkpoint contract changed')
    cases.extend(d['case_ids'])
    sources.append({'chunk': item['chunk_id'], 'uncompressed_sha256': sha(raw)})
    for r in d['rows']:
        key = (r['case'],r['method'],r['condition'],r['axis'])
        if key in records:
            raise ValueError('Duplicate measurement')
        records[key] = r
if cases != [c['id'] for c in cohort] or len(set(cases)) != 120:
    raise ValueError('Case identity/order changed')
results=[]
for condition in ('pitch_minus3','pitch_plus3'):
    for metric in ('1.native_mos','5.ecapa'):
        rows,excluded=[],[]
        for case in cohort:
            keys=[(case['id'],m,c,metric if c=='native' else metric+'.'+c)
                  for m in (CANDIDATE,'pml') for c in ('native',condition)]
            values=[records[k] for k in keys]
            if not all(r['status']=='measured' for r in values):
                excluded.append({'case':case['id'],'states':[
                    {'method':r['method'],'condition':r['condition'],'status':r['status'],'reason':r['reason_code']}
                    for r in values if r['status']!='measured']})
                continue
            v=np.array([r['value'] for r in values],dtype=float)
            if not np.isfinite(v).all():
                raise ValueError('Nonfinite measured value')
            rows.append({'case':case['id'],'speaker':case['speaker'],'values':v.tolist(),
                         'candidate_edit_change':float(v[1]-v[0]),'pml_edit_change':float(v[3]-v[2]),
                         'difference_of_changes':float((v[1]-v[0])-(v[3]-v[2]))})
        speakers=sorted({r['speaker'] for r in rows})
        matrix=np.array([np.mean([r['values'] for r in rows if r['speaker']==s],axis=0) for s in speakers])
        changes=np.column_stack((matrix[:,1]-matrix[:,0],matrix[:,3]-matrix[:,2]))
        differences=changes[:,0]-changes[:,1]
        draws=np.random.default_rng(20261018).integers(0,len(speakers),(2000,len(speakers)))
        boot=differences[draws].mean(axis=1)
        results.append({'metric':metric,'condition':condition,'planned_recordings':120,
                        'paired_recordings':len(rows),'paired_speakers':len(speakers),
                        'value_order':['candidate_native','candidate_edited','pml_native','pml_edited'],
                        'speaker_equal_means':matrix.mean(axis=0).tolist(),
                        'candidate_edit_change':float(changes[:,0].mean()),
                        'pml_edit_change':float(changes[:,1].mean()),
                        'difference_of_changes':float(differences.mean()),
                        'difference_ci95':np.quantile(boot,[.025,.975]).tolist(),
                        'speaker_differences':[{'speaker':s,'difference':float(v)} for s,v in zip(speakers,differences)],
                        'excluded':excluded,'rows':rows})
out={'scope':'post-hoc same-support editing contrasts; not causal evidence or a new model evaluation',
     'source_summary_sha256':sha(summary_bytes),'cohort_sha256':sha(cohort_bytes),'sources':sources,
     'bootstrap':{'seed':20261018,'replicates':2000,'unit':'speaker','point':'recording mean within speaker, then speaker equal weight'},
     'plan_sha256':sha((OUT/'PLAN-ja.md').read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),
     'numpy_version':np.__version__,'results':results}
with (OUT/'results.json').open('x') as f:
    json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False)
for r in results:
    print({k:r[k] for k in ('metric','condition','paired_recordings','paired_speakers','speaker_equal_means','candidate_edit_change','pml_edit_change','difference_of_changes','difference_ci95')})
