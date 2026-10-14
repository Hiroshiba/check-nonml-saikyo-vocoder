"""既存公開許諾2 IDのnative先頭最大2秒だけを最終レポート用に保存する。"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from all_metrics_common import METHODS, ROOT, RUN, read
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='最終HTMLと同じ保存先。音声folderを新設する')
    args = parser.parse_args()
    dataset_path = ROOT / 'data/clean_speech_v1.json'
    dataset = read(dataset_path)
    selected = dataset['public_audio_example_ids']
    if len(selected) != 2 or len(set(selected)) != 2:
        raise ValueError('既存公開許諾の2 IDだけが必要です')
    specs = {spec['id']: spec for spec in read(RUN / 'inputs.json')}
    folder = args.output / 'audio'
    if folder.exists():
        raise FileExistsError('音声例を上書きしません')
    folder.mkdir(parents=True)
    samples, excluded = [], []
    for identifier in selected:
        spec = specs[identifier]
        for method in ('original', *METHODS):
            if method == 'original':
                source, rate, expected = Path(spec['path']), spec['sample_rate'], spec['sha256']
            else:
                record = RUN / 'native' / method / identifier / 'unedited.json'
                native = read(record) if record.exists() else {'status': 'pending_audio'}
                if native['status'] != 'measured':
                    excluded.append({'case': identifier, 'method': method, 'status': native['status']})
                    continue
                source, rate, expected = (Path(native['audio']['path']), native['audio']['sample_rate'],
                                          native['audio']['file_sha256'])
            if sha256(source) != expected:
                raise ValueError('公開例の元native音声hash不一致')
            wave = np.load(source, allow_pickle=False)
            if wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all():
                raise ValueError('公開例は有限なモノラル音声が必要です')
            excerpt = np.asarray(wave[:min(len(wave), 2 * rate)], dtype=np.float32)
            target = folder / f'{identifier}__{method}.wav'
            wavfile.write(target, rate, excerpt)
            samples.append({'case': identifier, 'method': method, 'src': str(target.relative_to(args.output)),
                'wav_sha256': sha256(target), 'sample_rate': rate, 'n_samples': len(excerpt), 'start_sample': 0,
                'native_source_sha256': expected, 'peak_amplitude': float(np.max(np.abs(excerpt))),
                'format': 'WAV IEEE float32; fixed first <=2s, no normalization, clipping or resampling'})
    write_json(args.output / 'audio_samples.json', {'schema_version': 1,
        'dataset_sha256': sha256(dataset_path), 'public_case_ids': selected, 'samples': samples, 'excluded': excluded,
        'scope': '既存許諾2録音の固定先頭区間、各方式native無編集。小さな再生音量から調整し、例だけで全体品質を判断しない。'})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-audio'))
