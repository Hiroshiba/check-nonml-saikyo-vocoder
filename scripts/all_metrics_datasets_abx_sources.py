"""ラベルと固定原音の時刻対応を保証する全120件の配布PCM出典照合。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging

import soundfile as sf

from all_metrics_datasets_remote import OUT, ROOT, RemoteZip, save_json, sha
from all_metrics_datasets_abx_contract import bind_index, require_plan


def main():
    require_plan()
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(OUT / 'abxls-source-audit.log')])
    source = RemoteZip('abxls')
    bind_index(source)
    entries = json.loads((ROOT / 'data/clean_speech_v1.json').read_text())['entries']
    def acquire(entry):
        try:
            member = f'test-clean/{entry["source_utterance_id"]}.wav'
            path, metadata = source.member(source.by_name[member])
            pcm, rate = sf.read(path, dtype='int16')
            pcm_hash = sha(pcm.astype('<i2').tobytes())
            equal = rate == entry['sample_rate'] and pcm_hash == entry['decoded_pcm_sha256']
            row = {'id': entry['id'], **metadata, 'sample_rate': rate, 'source_samples': len(pcm),
                   'abxls_pcm_sha256': pcm_hash, 'frozen_librispeech_pcm_sha256': entry['decoded_pcm_sha256'],
                   'identical_full_source_pcm': equal, 'status': 'ok' if equal else 'pcm_mismatch'}
            logging.info('%s identical=%s', entry['id'], equal)
            return row
        except Exception as error:
            logging.exception('Source audit acquisition failed for %s', entry['id'])
            return {'id': entry['id'], 'status': 'failed', 'error': str(error)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(acquire, entries))
    summary = {'recordings': len(rows), 'identical': sum(r.get('identical_full_source_pcm', False) for r in rows),
               'failed': sum(r['status'] != 'ok' for r in rows)}
    save_json(OUT / 'abxls120-source-identity.json', {'purpose': 'official timestamp audio and frozen source PCM identity',
                                                   'counts': summary, 'entries': rows})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
