"""新選択契約で公式ASV評定105録音を固定し、承認後に必要原音だけを取得する。"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging
from pathlib import Path
import traceback

import numpy as np
import soundfile as sf

from all_metrics_common import ROOT, RUN, freeze, now, read
from all_metrics_datasets_contract import DOCUMENT as PLAN, RULES, plan_path
from all_metrics_datasets_human import prepare_selection as selection, require_selection
from all_metrics_datasets_remote import CACHE, RemoteZip, URLS
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

OUT = RUN / 'human-similarity'
PUBLIC = OUT / 'public-evidence'
AUDIO_URL = RULES['human']['audio_url']


def acquire(sample, speaker, archive):
    record_path = OUT / 'audio-records' / f'{Path(sample).stem}.json'
    if record_path.exists() and read(record_path)['status'] == 'measured':
        record = read(record_path)
        if sha256(record['input']['path']) != record['input']['sha256']:
            raise ValueError('保存済み#13原音NPY hash不一致')
        return record
    try:
        stem = Path(sample).stem
        matches = [row for row in archive.entries if Path(row['member']).name == stem+'.flac']
        if len(matches) != 1:
            raise ValueError(f'公式LA.zipで録音IDのFLACを一意に結合できない: {sample}: {len(matches)}')
        source, metadata = archive.member(matches[0], CACHE / 'asvhuman/audio' / (stem+'.flac'))
        wave, rate = sf.read(source, dtype='float64')
        if rate != 16000 or wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all() or not np.any(wave):
            raise ValueError('公式原音が有限な16 kHz mono自然音声の入力条件外')
        identifier = 'asvspoof2019_'+stem
        path = OUT / 'audio-inputs' / f'{identifier}.npy'
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, wave, allow_pickle=False)
        spec = {'id': identifier, 'path': str(path), 'sha256': sha256(path), 'sample_rate': rate,
                'samples': len(wave), 'speaker': speaker,
                'metadata': {'corpus': 'ASVspoof2019_LA_bonafide', 'source_utterance_id': stem,
                             'official_rating_sample_id': sample, 'role': 'human_ratings_only'}}
        record = {'status': 'measured', 'sample': sample, 'speaker': speaker, 'input': spec, **metadata,
            'sample_rate': rate, 'samples': len(wave), 'full_duration_seconds': len(wave)/rate,
            'full_source_float64_sha256': hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest(),
            'pcm_identity_scope': 'official rating filename stem joined to official lossless FLAC member; '
                                  'web listening-player PCM was not separately distributed/audited',
            'excerpt': False, 'finished_at_utc': now()}
    except Exception:
        logging.exception('正式#13原音取得失敗: %s', sample)
        record = {'status': 'failed', 'sample': sample, 'speaker': speaker, 'error': traceback.format_exc()}
    write_json(record_path, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('selection', 'audio'))
    parser.add_argument('--csv', type=Path)
    args = parser.parse_args()
    if args.stage == 'selection':
        if args.csv is None:
            parser.error('selection stage requires --csv (already acquired official CSV)')
        selection(args.csv)
        return 0
    chosen = require_selection()
    URLS['asvhuman'] = AUDIO_URL
    archive = RemoteZip('asvhuman')
    if read(archive.index)['url'] != AUDIO_URL:
        raise ValueError('公式ASV archive索引の配布元不一致')
    freeze(OUT / 'audio-acquisition-contract.json', {'selection_sha256': sha256(OUT / 'selection.json'),
        'selection_plan_sha256': sha256(plan_path('human')), 'archive_index_sha256': sha256(archive.index),
        'archive_url': AUDIO_URL, 'archive_bytes': archive.size})
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda pair: acquire(*pair, archive), sorted(chosen['identities'].items())))
    if any(row['status'] != 'measured' for row in records):
        write_json(OUT / 'acquisition-status.json', {'status': 'failed', 'rows': records})
        return 1
    inputs = [row['input'] for row in records]
    freeze(OUT / 'inputs.json', inputs)
    for offset in range(0, len(inputs), 10):
        freeze(OUT / 'input-batches' / f'{offset//10:02d}.json', inputs[offset:offset+10])
    freeze(OUT / 'input-contract.json', {'role': 'human_ratings_only', 'recordings': len(inputs),
        'speakers': len({r['speaker'] for r in inputs}),
        'selection_sha256': sha256(OUT / 'selection.json'), 'inputs_sha256': sha256(OUT / 'inputs.json'),
        'plan_sha256': sha256(PLAN), 'full_length': True,
        'data_source_sha256': sha256(Path(__file__)),
        'remote_zip_source_sha256': sha256(ROOT / 'scripts/all_metrics_datasets_remote.py')})
    write_json(PUBLIC / 'audio-provenance.json', {'records': [
        {k: v for k, v in row.items() if k not in ('input', 'local_source')} for row in records],
        'input_contract_sha256': sha256(OUT / 'input-contract.json')})
    write_json(OUT / 'acquisition-status.json', {'status': 'measured', 'recordings': len(inputs),
        'total_seconds': sum(row['samples']/row['sample_rate'] for row in inputs), 'finished_at_utc': now()})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-human-data'))
