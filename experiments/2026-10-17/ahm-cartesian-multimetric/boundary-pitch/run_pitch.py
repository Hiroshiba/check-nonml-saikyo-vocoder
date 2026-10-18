"""Additional fixed pitch-control observations on previously saved waves only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import traceback

MANIFEST_SHA = '8528307f71e77cbe27861f5457c36622216ad0f20f60d3d6529f820c5d0094cf'
METHODS = ('boundary_hold', 'original_candidate', 'pml')
CONDITIONS = (-3, 3)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    with Path(path).open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


class Pair:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def pair(self, job, same_length=True):
        return self.x, self.y, 16000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    authorization = json.loads(args.authorization.read_text())
    if (sha(args.manifest) != MANIFEST_SHA or authorization['manifest_sha256'] != MANIFEST_SHA
            or authorization['approved'] is not True or authorization['runner_sha256'] != sha(__file__)
            or authorization['methods'] != list(METHODS) or authorization['semitones'] != list(CONDITIONS)):
        raise RuntimeError('Fixed source/input authorization mismatch')
    if (manifest['schema'] != 'boundary-quality-matched-host-v1'
            or Path(sys.prefix).resolve() != Path(manifest['python_prefix']).resolve()):
        raise RuntimeError('Wrong existing runtime or input schema')
    if any(os.environ.get(k) != '2' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')):
        raise RuntimeError('Fixed two-thread environment required')
    cases = manifest['cases']
    if len(cases) != 120 or len({c['case'] for c in cases}) != 120:
        raise RuntimeError('Fixed 120-case set changed')
    sys.path.insert(0, manifest['integrity_directory'])
    from integrity import FrozenClosure, ScientificLock
    lock = ScientificLock(manifest['lock_path'])
    closure = FrozenClosure(args.manifest.parent, manifest['files'] + [
        {'path': str(args.manifest.resolve()), 'sha256': MANIFEST_SHA},
        {'path': str(args.authorization.resolve()), 'sha256': sha(args.authorization)},
        {'path': str(Path(__file__).resolve()), 'sha256': sha(__file__)},
    ])
    output = Path(authorization['output_directory'])
    output.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(output).free < 6 * 1024**3:
        raise RuntimeError('Insufficient free-space floor')
    started = {'manifest_sha256': MANIFEST_SHA, 'runner_sha256': sha(__file__),
               'authorization_sha256': sha(args.authorization), 'utc': datetime.now(timezone.utc).isoformat(),
               'planned_recordings': 120, 'planned_rows': 720,
               'reference': 'same method native output, full length; not original F0 truth'}
    save(output/'started.json', started)
    sys.path.insert(0, manifest['repository'])
    import numpy as np
    from vocoderbench.assessment.controls import pitch
    from vocoderbench.assessment.common import NotApplicable
    rows = []
    for case in cases:
        lock.verify()
        closure.checkpoint()
        for method in METHODS:
            for semitone in CONDITIONS:
                native = case['outputs'][method]['0']
                edited = case['outputs'][method][str(semitone)]
                row = {'case': case['case'], 'speaker': case['speaker'], 'method': method,
                       'candidate_id': manifest['method_ids'][method], 'semitones': semitone,
                       'metric': 'pitch_tracking', 'status': 'pending', 'value': None}
                unavailable = [r for r in (native, edited) if r['status'] != 'measured']
                if unavailable:
                    if method != 'original_candidate' or any(r['status'] != 'upstream_failed' for r in unavailable):
                        raise RuntimeError('Unexpected missing wave state')
                    row.update(status='upstream_failed', reason='native_or_edited_generation_failed')
                else:
                    for desc in (native, edited):
                        if sha(desc['path']) != desc['sha256']:
                            raise RuntimeError('Saved wave identity changed')
                    x, y = [np.load(r['path'], allow_pickle=False) for r in (native, edited)]
                    if any(z.dtype != np.float64 or z.shape != (case['samples'],) or not np.isfinite(z).all() for z in (x,y)):
                        raise RuntimeError('Saved wave dtype/shape/nonfinite mismatch')
                    row.update(reference_sha256=native['sha256'], output_sha256=edited['sha256'])
                    try:
                        detail = pitch({'target_cents': semitone*100}, Pair(x,y))
                        row.update(status='measured' if detail['status']=='ok' else detail['status'],
                                   value=detail['value'], detail=detail)
                    except NotApplicable as e:
                        logging.exception('Pitch support unavailable: %s %s %s', case['case'], method, semitone)
                        row.update(status='not_applicable', reason=str(e), traceback=traceback.format_exc())
                    except (ValueError, FloatingPointError) as e:
                        logging.exception('Pitch measurement failure: %s %s %s', case['case'], method, semitone)
                        row.update(status='failed', reason=str(e), traceback=traceback.format_exc())
                save(output/f"{case['case']}-{method}-{semitone:+d}.json",row)
                rows.append(row)
        if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > 25*1024**2:
            raise RuntimeError('Output budget exceeded before terminal summary')
        logging.info('Saved %d/720 planned pitch rows',len(rows))
    closure.verify_full()
    lock.verify()
    save(output/'summary.json',{'validation_state':'validated_end', **started,
         'completed_utc':datetime.now(timezone.utc).isoformat(), 'planned_conditions':720,
         'status_counts':{s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})},
         'rows':rows, 'limits':'Existing YIN 65-700Hz, 80ms/10ms. No synthesis, no quality inference, no adoption.'})
    logging.info('Terminal pitch evaluation saved')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.captureWarnings(True)
    try:
        main()
    except BaseException:
        logging.exception('Saved-wave pitch evaluation interrupted; preserve partial results')
        raise
