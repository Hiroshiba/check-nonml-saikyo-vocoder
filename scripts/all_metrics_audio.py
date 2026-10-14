"""既存公開許諾2 IDのnative先頭最大2秒だけを最終レポート用に保存する。"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from all_metrics_common import METHODS, ROOT, RUN, read
from all_metrics_audio_policy import (CREDITS_NAME, CREDITS_TEMPLATE, PUBLIC_METHODS, TERMS_SHA256,
                                      WITHHELD, credits_html, public_ids)
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='最終HTMLと同じ保存先。音声JSONと帰属HTMLを新設する')
    args = parser.parse_args()
    dataset_path = ROOT / 'data/clean_speech_v1.json'
    dataset = read(dataset_path)
    selected = public_ids(dataset)
    entries = {entry['id']: entry for entry in dataset['entries']}
    specs = {spec['id']: spec for spec in read(RUN / 'inputs.json')}
    if any((args.output / name).exists() for name in ('audio', 'audio_samples.json', CREDITS_NAME)):
        raise FileExistsError('音声例を上書きしません')
    args.output.mkdir(parents=True, exist_ok=True)
    samples, excluded = [], []
    for identifier in selected:
        spec = specs[identifier]
        entry = entries[identifier]
        if entry['excerpt_start_sample'] != 0 or spec['metadata'] != entry:
            raise ValueError('公開例の原入力と固定datasetの先頭区間が不一致')
        for method in ('original', *METHODS):
            if method not in PUBLIC_METHODS:
                excluded.append({'case': identifier, 'method': method, 'status': 'withheld_license',
                    'reason': WITHHELD.get(method, 'この方式の音声公開許諾は未確認のため保留。')})
                continue
            provenance = {'kind': 'original', 'version': 'LibriSpeech test-clean'}
            if method == 'original':
                source, rate, expected = Path(spec['path']), spec['sample_rate'], spec['sha256']
            else:
                record = RUN / 'native' / method / identifier / 'unedited.json'
                native = read(record) if record.exists() else {'status': 'pending_audio'}
                if native['status'] != 'measured':
                    excluded.append({'case': identifier, 'method': method, 'status': 'withheld_audio_unavailable',
                        'native_status': native['status'],
                        'reason': '公開できる未編集native音声が未到着または利用不能。測定状態は数値表を参照。'})
                    continue
                if (native['case'] != identifier or native['method'] != method or native['condition'] != 'unedited'
                        or native['input']['source_sha256'] != spec['sha256']):
                    raise ValueError('公開例のnative recordと固定原入力が不一致')
                contract_path = RUN / 'synthesis-contracts' / f'{method}.json'
                if sha256(contract_path) != native['contract_sha256']:
                    raise ValueError('公開例の固定合成契約hash不一致')
                contract = read(contract_path)
                provenance = {'kind': 'vocoder_analysis_resynthesis',
                    'version': contract['adapter_info']['variant'],
                    'synthesis_contract_sha256': native['contract_sha256'],
                    'native_record_sha256': sha256(record),
                    'source_revisions': contract['prepared'].get('sources', {}),
                    'world_lock_sha256': contract['prepared'].get('world_lock_sha256'),
                    'checkpoint_sha256': contract['adapter_info'].get('checkpoint_sha256'),
                    'implementation_sha256': contract['source_sha256']}
                source, rate, expected = (Path(native['audio']['path']), native['audio']['sample_rate'],
                                          native['audio']['file_sha256'])
            if sha256(source) != expected:
                raise ValueError('公開例の元native音声hash不一致')
            wave = np.load(source, allow_pickle=False)
            if wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all():
                raise ValueError('公開例は有限なモノラル音声が必要です')
            excerpt = np.asarray(wave[:min(len(wave), 2 * rate)], dtype=np.float32)
            if not np.isfinite(excerpt).all():
                raise ValueError('float32形式への変換後に非有限の公開音声は保存しません')
            buffer = io.BytesIO()
            wavfile.write(buffer, rate, excerpt)
            wav = buffer.getvalue()
            samples.append({'case': identifier, 'method': method,
                'data_uri': 'data:audio/wav;base64,' + base64.b64encode(wav).decode('ascii'),
                'label': 'LibriSpeech test-clean・固定先頭最大2秒',
                'wav_sha256': hashlib.sha256(wav).hexdigest(),
                'sample_rate': rate, 'n_samples': len(excerpt), 'start_sample': 0,
                'native_source_sha256': expected, 'peak_amplitude': float(np.max(np.abs(excerpt))),
                'source_utterance_id': entry['source_utterance_id'],
                'source': entry['source'], 'source_file_sha256': entry['source_sha256'],
                'source_decoded_pcm_sha256': entry['decoded_pcm_sha256'],
                'original_input_sha256': spec['sha256'], 'source_sample_rate': entry['sample_rate'],
                'source_excerpt_start_sample': entry['excerpt_start_sample'],
                'source_excerpt_samples': entry['excerpt_samples'], 'source_public_start_sample': 0,
                'source_public_n_samples': min(spec['samples'], 2 * spec['sample_rate']),
                'method_provenance': provenance,
                'modifications': ['先頭最大2秒を切出し', 'WAV IEEE float32形式に変換']
                    + ([] if method == 'original' else ['固定版ボコーダーによる解析再合成（方式native標本化周波数）']),
                'format': 'WAV IEEE float32; fixed first <=2s, no normalization, clipping or resampling'})
    credits = args.output / CREDITS_NAME
    credits.write_text(credits_html(samples, excluded), encoding='utf-8')
    write_json(args.output / 'audio_samples.json', {'schema_version': 2,
        'dataset_sha256': sha256(dataset_path), 'public_case_ids': selected, 'samples': samples, 'excluded': excluded,
        'publication_terms_sha256': TERMS_SHA256,
        'exporter_source_sha256': {name: sha256(ROOT / 'scripts' / name)
            for name in ('all_metrics_audio.py', 'all_metrics_audio_policy.py')},
        'credits': {'src': CREDITS_NAME, 'sha256': sha256(credits), 'template_sha256': sha256(CREDITS_TEMPLATE)},
        'selection_note': '既存許諾2録音の固定先頭最大2秒。原音と許諾確認済み6方式のみ。公開保留は測定失敗を意味しません。',
        'scope': '既存許諾2録音の固定先頭区間、各方式native無編集。小さな再生音量から調整し、例だけで全体品質を判断しない。'})
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-audio'))
