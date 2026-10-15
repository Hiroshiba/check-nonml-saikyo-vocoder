"""取得済み公式dev-cleanから、新契約の40話者各3録音をmetadataのみで選ぶ。"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
from pathlib import Path
import re
import tarfile

import numpy as np
import soundfile as sf

from all_metrics_common import ROOT, RUN, audio_info, freeze, read, save_audio
from all_metrics_datasets_contract import plan_path, require_plan
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

OUT = RUN / 'corpora/readout-train'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def evaluation_sets():
    manifest = read(ROOT / 'data/clean_speech_v1.json')['entries']
    inputs = read(RUN / 'inputs.json')
    if (len(manifest) != 120 or len(inputs) != 120
            or {r['id'] for r in manifest} != {r['id'] for r in inputs}):
        raise ValueError('固定主120の評価manifest/inputsが揃っていません')
    groups = Counter(r['speaker'] for r in manifest)
    if len(groups) != 40 or set(groups.values()) != {3}:
        raise ValueError('評価群は40話者各3録音が必要です')
    lookup = {r['id']: r for r in manifest}
    hashes = set()
    for item in inputs:
        if item['speaker'] != lookup[item['id']]['speaker'] or sha256(item['path']) != item['sha256']:
            raise ValueError('主評価inputsの話者/hashがmanifestと不一致')
        hashes.add(audio_info(item['path'], item['sample_rate'])['float64_sha256'])
    return {'speaker': {r['speaker'] for r in manifest}, 'id': {r['id'] for r in manifest},
            'source_utterance_id': {r['source_utterance_id'] for r in manifest},
            'source_sha256': {r['source_sha256'] for r in manifest},
            'source_pcm_sha256': {r['decoded_pcm_sha256'] for r in manifest},
            'excerpt_pcm_sha256': hashes, 'input_npy_sha256': {r['sha256'] for r in inputs}}


def choose_metadata(archive, rule):
    files = [m for m in archive.getmembers() if m.isfile()]
    if len({m.name for m in files}) != len(files):
        raise ValueError('tar内の同名member重複')
    members = {m.name: m for m in files}
    labels = archive.extractfile(members['LibriSpeech/SPEAKERS.TXT']).read()
    speakers = {}
    for line in labels.decode().splitlines():
        if not line.strip() or line.startswith(';'):
            continue
        fields = [value.strip() for value in line.split('|')]
        if fields[2] == 'dev-clean':
            if fields[0] in speakers:
                raise ValueError('公式speaker labelの重複')
            speakers[fields[0]] = fields[1]
    if len(speakers) != 40:
        raise ValueError('公式dev-clean話者が40人でないため停止。縮小選択しません')
    listing = [{'member': m.name, 'bytes': m.size, 'offset_data': m.offset_data}
               for m in sorted(files, key=lambda m: m.name)]
    freeze(OUT / 'archive-file-index.json', listing)
    rows = []
    for speaker in sorted(speakers):
        names = [name for name in members if name.startswith(f'LibriSpeech/dev-clean/{speaker}/')
                 and name.endswith('.flac')]
        names.sort(key=lambda name: (digest((rule['salt']+'|'+speaker+'|'+name).encode()), name))
        if len(names) < 3:
            raise ValueError(f'話者{speaker}の元録音数が不足')
        for name in names[:3]:
            utterance = Path(name).stem
            if not re.fullmatch(r'[0-9]+-[0-9]+-[0-9]+', utterance) or utterance.split('-')[0] != speaker:
                raise ValueError('公式LibriSpeech元発話IDと話者の不一致')
            rows.append({'id': 'librispeech_'+utterance, 'speaker': 'librispeech_'+speaker,
                         'source_utterance_id': utterance, 'source_member': name,
                         'speaker_gender_as_distributed': speakers[speaker], 'split': 'dev-clean'})
    return sorted(rows, key=lambda r: r['id']), members, labels


def prepare(archive_path, expected_archive_sha):
    plan = require_plan('train')
    rule = plan['rule']
    if not re.fullmatch('[a-f0-9]{64}', expected_archive_sha):
        raise ValueError('取得時に記録したarchive SHA256が必要です')
    freeze(OUT / 'acquisition-contract.json', {'plan_sha256': sha256(plan_path('train')),
        'archive_sha256': expected_archive_sha, 'archive_path': str(archive_path.resolve()),
        'evaluation_inputs_sha256': sha256(RUN / 'inputs.json'),
        'source_url': rule['source_url']})
    if sha256(archive_path) != expected_archive_sha:
        raise ValueError('取得済みdev-clean archiveのhash不一致')
    evaluation = evaluation_sets()
    with tarfile.open(archive_path, 'r:gz') as archive:
        chosen, members, labels = choose_metadata(archive, rule)
        for field in ('speaker', 'id', 'source_utterance_id'):
            if {r[field] for r in chosen} & evaluation[field]:
                raise ValueError(f'train/evalのmetadata重複: {field}')
        selection_hashes = {'archive_sha256': expected_archive_sha,
            'archive_file_index_sha256': sha256(OUT / 'archive-file-index.json'),
            'speaker_labels_sha256': digest(labels), 'plan_sha256': sha256(plan_path('train'))}
        freeze(OUT / 'selected-metadata.json', {'schema_version': 1, 'selection_rule': rule,
            'selection_inputs_sha256': selection_hashes, 'entries': chosen})
        entries, inputs = [], []
        seen = {key: set() for key in ('source_sha256', 'source_pcm_sha256',
                                      'excerpt_pcm_sha256', 'input_npy_sha256')}
        for row in sorted(chosen, key=lambda item: members[item['source_member']].offset_data):
            raw = archive.extractfile(members[row['source_member']]).read()
            info = sf.info(io.BytesIO(raw))
            if info.samplerate != 16000 or info.channels != 1 or info.subtype != 'PCM_16':
                raise ValueError(f'選択済み原音format不適合。差替えなし: {row["id"]}')
            pcm, rate = sf.read(io.BytesIO(raw), dtype='int16')
            wave = pcm.astype(np.float64) / 32768
            excerpt = wave[:rate*6]
            if (len(wave) < rate or not np.isfinite(wave).all() or np.mean(wave**2) <= 0
                    or np.mean(excerpt**2) <= 0
                    or max(np.mean(np.abs(wave) >= 1-1/32768),
                           np.mean(np.abs(excerpt) >= 1-1/32768)) > .001):
                raise ValueError(f'選択済み原音の入力条件違反。差替えなし: {row["id"]}')
            hashes = {'source_sha256': digest(raw), 'source_pcm_sha256': digest(pcm.astype('<i2').tobytes()),
                      'excerpt_pcm_sha256': digest(excerpt.astype('<f8').tobytes())}
            for field, value in hashes.items():
                if value in evaluation[field] or value in seen[field]:
                    raise ValueError(f'元音声/抜粋のtrain内またはevalとの重複: {row["id"]}/{field}')
                seen[field].add(value)
            source = OUT / 'sources' / f'{row["id"]}.flac'
            source.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() and sha256(source) != hashes['source_sha256']:
                raise ValueError('既存train原FLACが選択入力と不一致')
            if not source.exists():
                source.write_bytes(raw)
            path = OUT / 'audio' / f'{row["id"]}.npy'
            audio = audio_info(path, rate) if path.exists() else save_audio(path, excerpt, rate)
            if audio['float64_sha256'] != hashes['excerpt_pcm_sha256']:
                raise ValueError('既存train NPYが選択抜粋と不一致')
            npy_sha = audio['file_sha256']
            if npy_sha in evaluation['input_npy_sha256'] or npy_sha in seen['input_npy_sha256']:
                raise ValueError('train/evalまたはtrain内のNPY hash重複')
            seen['input_npy_sha256'].add(npy_sha)
            entry = {**row, **hashes, 'sample_rate': rate, 'source_samples': len(wave),
                'source_duration_seconds': len(wave)/rate, 'excerpt_start_sample': 0,
                'excerpt_samples': len(excerpt), 'local_source': str(source.relative_to(ROOT)),
                'input_npy_sha256': npy_sha, 'source_archive_sha256': expected_archive_sha}
            entries.append(entry)
            inputs.append({'id': row['id'], 'speaker': row['speaker'], 'path': str(path),
                'sha256': npy_sha, 'samples': len(excerpt), 'sample_rate': rate, 'metadata': entry})
        entries.sort(key=lambda row: row['id'])
        inputs.sort(key=lambda row: row['id'])
        if len(entries) != 120 or len({r['source_sha256'] for r in entries}) != 120:
            raise ValueError('独立した120 train元録音が揃っていません')
        freeze(OUT / 'manifest.json', {'schema_version': 1, 'split': 'dev-clean',
            'selection_rule': rule, 'selection_inputs_sha256': selection_hashes,
            'implementation_origin': 'new_recovery_selection_not_assumed_equal_to_old',
            'entries': entries})
        freeze(OUT / 'inputs.json', inputs)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--archive-sha256', required=True)
    args = parser.parse_args()
    try:
        return prepare(args.archive, args.archive_sha256)
    except Exception:
        import traceback
        write_json(OUT / 'selection-failure.json', {'status': 'failed', 'traceback': traceback.format_exc(),
                   'replacement_selected': False})
        raise


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-train-selection'))
