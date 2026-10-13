"""100音声以上の正式コーパスを読み込み、比較入力を固定する。"""
import hashlib
from pathlib import Path

import numpy as np

from .. import corpus
from .common import digest, write


def load(args):
    cases = list(corpus.load_cases(args.manifest, args.corpus_cache))
    if len(cases) < 100:
        raise ValueError('正式比較には100音声以上が必要です')
    public = set(corpus.read_manifest(args.manifest)['public_audio_example_ids'])
    if len({case['id'] for case in cases}) != len(cases):
        raise ValueError('入力IDが重複しています')
    for case in cases:
        if not case['id'] or Path(case['id']).name != case['id'] or case['id'] in {'.', '..'}:
            raise ValueError('入力IDには単純なファイル名だけを使ってください')
    return cases, public


def save(cases, output):
    records = []
    for case in cases:
        path = output / 'inputs' / f'{case["id"]}.npy'
        path.parent.mkdir(exist_ok=True, parents=True)
        np.save(path, case['x'], allow_pickle=False)
        records.append({'id': case['id'], 'path': str(path.resolve()), 'sha256': digest(path),
                        'sample_rate': case['sr']})
    write(output / 'inputs.json', records)


def fingerprint(cases):
    return [{'id': case['id'], 'sample_rate': case['sr'], 'samples': len(case['x']),
             'pcm_sha256': hashlib.sha256(case['x'].astype('<f8').tobytes()).hexdigest()}
            for case in cases]
