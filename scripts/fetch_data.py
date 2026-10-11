"""Download pinned CC-BY fixtures and verify decoded PCM, independent of WAV headers."""
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import configure_logging, run_cli, run_process  # noqa: E402
configure_logging('fetch-data')

from scipy.io import wavfile  # noqa: E402

ROOT=Path(__file__).resolve().parents[1]


def verify(path,entry):
    sr,x=wavfile.read(path)
    if sr!=entry['sample_rate'] or x.ndim!=1 or len(x)!=entry['samples'] or x.dtype.str not in ('<i2','=i2'):
        raise RuntimeError(f'Unexpected audio format: {path}')
    if hashlib.sha256(x.astype('<i2').tobytes()).hexdigest()!=entry['pcm_s16le_sha256']:
        raise RuntimeError(f'Decoded PCM differs: {path}')


def main():
    cache=ROOT/'data/cache'
    cache.mkdir(parents=True,exist_ok=True)
    entries=json.loads((ROOT/'data/manifest.json').read_text())['files']
    for entry in entries:
        target=cache/entry['local_wav']
        if target.exists():
            verify(target,entry)
            print('Verified',target.name)
            continue
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            flac=Path(tmp)/'source.flac'
            with urllib.request.urlopen(entry['source_url'],timeout=60) as response:
                flac.write_bytes(response.read())
            if hashlib.sha256(flac.read_bytes()).hexdigest()!=entry['source_sha256']:
                raise RuntimeError('Source download hash mismatch')
            wav=Path(tmp)/'decoded.wav'
            run_process(['ffmpeg','-v','error','-i',str(flac),'-acodec','pcm_s16le',str(wav)],check=True)
            verify(wav,entry)
            wav.replace(target)
        print('Downloaded and verified',target.name)


if __name__=='__main__':
    raise SystemExit(run_cli(main, 'fetch-data'))
