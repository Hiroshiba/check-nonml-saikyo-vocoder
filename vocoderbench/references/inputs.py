"""正式コーパスと、CI用の小規模実行を明確に分離する。"""
import hashlib
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .. import corpus
from .common import digest, write


def load(args):
    if not args.smoke:
        cases = list(corpus.load_cases(args.manifest, args.corpus_cache))
        if len(cases) < 100:
            raise ValueError('正式比較には100音声以上が必要です。動作確認には --smoke を指定してください')
        public = set(corpus.read_manifest(args.manifest)['public_audio_example_ids'])
    else:
        root = args.runtime_cache / 'src/llsm/test'
        cases = []
        for ident, name in [('arctic', 'arctic_a0001.wav'), ('ready', 'are-you-ready.wav')]:
            file = root / name
            sr, raw = wavfile.read(file)
            x = raw.astype(np.float64)
            if raw.dtype.kind == 'i':
                x /= 2 ** (raw.dtype.itemsize * 8 - 1)
            if x.ndim == 2:
                x = x.mean(axis=1)
            x = x[:5*sr]
            cases.append({'id': 'smoke_' + ident, 'x': x, 'sr': int(sr), 'kind': 'natural_speech',
                          'language': 'en', 'style': 'normal', 'speaker': ident,
                          'source_file': name, 'source_file_sha256': digest(file)})
        public = {c['id'] for c in cases}
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
