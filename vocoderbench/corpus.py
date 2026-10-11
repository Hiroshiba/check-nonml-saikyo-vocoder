"""固定した英語120録音の取得、入力確認、読み込み。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import struct
import tarfile
import urllib.request
import zlib

from .logging_utils import LoggedArgumentParser, configure_logging, run_cli, run_process

if __name__ == '__main__':
    configure_logging('corpus')

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/clean_speech_v1.json'
CACHE = ROOT / 'data/cache/clean_speech_v1'
SALT = 'nonml-clean-speech-v1-20261011'
JVS_URL = ('https://drive.usercontent.google.com/download?'
           'id=19oAw8wWn3Y7z6CKChRdAyGOB9yupL_Xt&export=download&confirm=t')
JVS_SIZE = 3536595425
LIBRI_URL = 'https://www.openslr.org/resources/12/test-clean.tar.gz'
RULES = {'minimum_source_seconds': 1.0, 'excerpt_start_sample': 0,
         'maximum_excerpt_seconds': 6.0, 'maximum_full_scale_fraction': 0.001,
         'minimum_power': 0.0, 'selection_order': 'sha256(salt + speaker + source_member)',
         'normalization': 'none', 'silence_trimming': 'none', 'resampling': 'none',
         'selection_uses_mos_or_vocoder_output': False}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _rank(value):
    return sha256((SALT + value).encode())


def _range(url, start, length, size):
    if not length:
        return b''
    last = min(start + length, size) - 1
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{last}'})
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.headers.get('Content-Range') != f'bytes {start}-{last}/{size}':
                    raise RuntimeError('配布元の部分取得位置またはアーカイブ長が変わりました')
                data = response.read(last - start + 1)
            if len(data) != last - start + 1:
                raise RuntimeError('音声データの部分取得が途中で終了しました')
            return data
        except Exception:
            logging.exception('部分取得失敗 (%d/3): %s bytes=%d-%d', attempt + 1, url, start, last)
            if attempt == 2:
                raise


def _jvs_bytes(locator):
    # ローカルヘッダーの長さを読み、その位置から圧縮データを展開する。
    prefix = _range(JVS_URL, locator['header_offset'], 30, JVS_SIZE)
    fields = struct.unpack('<4s5H3L2H', prefix)
    if fields[0] != b'PK\x03\x04':
        raise RuntimeError('ZIP内の音声ヘッダーが一致しません')
    offset = locator['header_offset'] + 30 + fields[-2] + fields[-1]
    packed = _range(JVS_URL, offset, locator['compressed_bytes'], JVS_SIZE)
    data = zlib.decompress(packed, -15) if locator['compression'] == 8 else packed
    if locator['compression'] not in (0, 8) or zlib.crc32(data) != locator['crc32']:
        raise RuntimeError('ZIP内の音声CRCまたは圧縮方式が一致しません')
    return data


def _download_libri(cache, offline=False):
    path = cache / 'archives/test-clean.tar.gz'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if offline:
            raise FileNotFoundError('オフライン取得用のLibriSpeechアーカイブがありません')
        temporary = path.with_suffix('.part')
        with urllib.request.urlopen(LIBRI_URL, timeout=60) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(path)
    logging.info('LibriSpeechアーカイブ: %s (%d bytes)', path, path.stat().st_size)
    return path


def _audio_info(path):
    sr, raw = wavfile.read(path)
    if raw.ndim != 1 or raw.dtype.kind != 'i':
        raise ValueError('元音声は整数PCMのモノラルである必要があります')
    x = raw.astype(np.float64) / 2 ** (raw.dtype.itemsize * 8 - 1)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    clipping = float(np.mean(np.abs(x) >= 1 - 1 / 32768)) if len(x) else 0.0
    power = float(np.mean(x * x)) if len(x) else 0.0
    excerpt = x[:round(sr * 6)]
    excerpt_power = float(np.mean(excerpt * excerpt)) if len(excerpt) else 0.0
    excerpt_clipping = float(np.mean(np.abs(excerpt) >= 1 - 1 / 32768)) if len(excerpt) else 0.0
    reasons = []
    if len(x) / sr < RULES['minimum_source_seconds']:
        reasons.append('1秒未満')
    if not np.isfinite(x).all() or min(power, excerpt_power) <= RULES['minimum_power']:
        reasons.append('非有限値または全無音')
    if max(clipping, excerpt_clipping) > RULES['maximum_full_scale_fraction']:
        reasons.append('フルスケール付近の標本が0.1%を超える')
    return {'sample_rate': int(sr), 'source_samples': len(x), 'source_duration_seconds': len(x) / sr,
            'source_peak': peak, 'source_rms_dbfs': float(10 * np.log10(power)) if power > 0 else None,
            'full_scale_fraction': clipping, 'reasons': reasons,
            'excerpt_full_scale_fraction': excerpt_clipping,
            'excerpt_rms_dbfs': float(10 * np.log10(excerpt_power)) if excerpt_power > 0 else None,
            'decoded_pcm_sha256': sha256(raw.astype(raw.dtype.newbyteorder('<')).tobytes())}


def _entry(data, metadata, cache):
    directory = cache / 'audio'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / (metadata['id'] + Path(metadata['source']['member']).suffix)
    source.write_bytes(data)
    wav = source if source.suffix == '.wav' else source.with_suffix('.wav')
    if wav != source:
        run_process(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-acodec', 'pcm_s16le', str(wav)])
    info = _audio_info(wav)
    item = {**metadata, **info, 'source_sha256': sha256(data), 'wav_sha256': sha256(wav.read_bytes()),
            'local_source': str(source.relative_to(cache)), 'local_wav': str(wav.relative_to(cache)),
            'excerpt_start_sample': 0,
            'excerpt_samples': min(info['source_samples'], round(info['sample_rate'] * 6))}
    return item


def _prepare_libri(cache, offline=False):
    path = _download_libri(cache, offline=offline)
    with tarfile.open(path, 'r:gz') as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        lines = archive.extractfile(members['LibriSpeech/SPEAKERS.TXT']).read().decode().splitlines()
        rows = [[part.strip() for part in line.split('|')] for line in lines if line and not line.startswith(';')]
        chosen = [row for gender in ('F', 'M') for row in sorted(
            (row for row in rows if row[1] == gender and row[2] == 'test-clean'),
            key=lambda row: _rank('librispeech/' + row[0]))[:20]]
        entries, rejected = [], []
        for row in chosen:
            names = sorted((name for name in members if name.startswith(f'LibriSpeech/test-clean/{row[0]}/')
                            and name.endswith('.flac')), key=lambda name: _rank(row[0] + name))
            accepted = 0
            for name in names:
                utterance = Path(name).stem
                chapter = Path(name).parent.name
                text_name = str(Path(name).parent / f'{row[0]}-{chapter}.trans.txt')
                text = archive.extractfile(members[text_name]).read().decode()
                texts = dict(line.split(' ', 1) for line in text.splitlines() if ' ' in line)
                metadata = {'id': f'librispeech_{utterance}', 'corpus': 'librispeech_test_clean',
                            'speaker': f'librispeech_{row[0]}', 'language': 'en', 'style': 'normal',
                            'speaker_gender_as_distributed': row[1], 'source_utterance_id': utterance,
                            'transcript': texts.get(utterance), 'source': {'archive_url': LIBRI_URL, 'member': name}}
                item = _entry(archive.extractfile(members[name]).read(), metadata, cache)
                if item['reasons']:
                    rejected.append(item)
                    continue
                entries.append(item)
                accepted += 1
                logging.info('英語を選定: %s', item['id'])
                if accepted == 3:
                    break
            if accepted != 3:
                raise RuntimeError(f'入力条件を満たすLibriSpeech音声が不足: {row[0]}')
    return entries, rejected, {'bytes': path.stat().st_size, 'sha256': sha256(path.read_bytes())}


def prepare(manifest_path=MANIFEST, cache_root=CACHE, offline=False):
    manifest_path, cache_root = Path(manifest_path), Path(cache_root)
    if manifest_path.exists():
        raise FileExistsError('固定済みの音声一覧は上書きしません。新しい版を指定してください')
    cache_root.mkdir(parents=True, exist_ok=True)
    english, rejected_libri, archive = _prepare_libri(cache_root, offline=offline)
    entries = sorted(english, key=lambda item: item['id'])
    example_speakers = list(dict.fromkeys(e['speaker'] for e in entries if e['language'] == 'en'))[:2]
    manifest = {'id': 'clean_speech_v1', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
                'selection_salt': SALT, 'input_rules': RULES, 'entries': entries,
                'excluded_before_freeze': rejected_libri,
                'plan_revision': {'before_codec_or_mos_measurement': True,
                                  'initial_plan': '日本語60録音と英語60録音',
                                  'reason': 'JVS12録音取得後に環境の通信許可が停止したため、取得済み英語アーカイブで固定120録音を構成'},
                'counts': {'recordings': len(entries), 'speakers': len({e['speaker'] for e in entries}),
                           'unique_transcripts': len({e['transcript'] for e in entries if e['transcript']})},
                'librispeech_archive': archive,
                'public_audio_example_ids': [next(e['id'] for e in entries if e['speaker'] == speaker)
                                             for speaker in example_speakers]}
    if len(entries) != 120 or len({e['source_sha256'] for e in entries}) != 120:
        raise RuntimeError('独立した120録音が揃っていません')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    logging.info('120録音を固定しました: %s', manifest_path)
    return manifest


def read_manifest(path=MANIFEST):
    return json.loads(Path(path).read_text())


def fetch(manifest_path=MANIFEST, cache_root=CACHE, offline=False):
    manifest, cache_root = read_manifest(manifest_path), Path(cache_root)
    missing = [e for e in manifest['entries'] if not (cache_root / e['local_wav']).exists()]
    if missing:
        if offline:
            raise FileNotFoundError('固定入力のWAVが不足しています。オフライン指定中は通信しません')
        path = _download_libri(cache_root) if any(e['language'] == 'en' for e in missing) else None
        archive = tarfile.open(path, 'r:gz') if path else None
        try:
            for entry in missing:
                data = (_jvs_bytes(entry['source']) if entry['language'] == 'ja'
                        else archive.extractfile(entry['source']['member']).read())
                if sha256(data) != entry['source_sha256']:
                    raise RuntimeError(f"配布音声のハッシュが変わりました: {entry['id']}")
                _entry(data, entry, cache_root)
        finally:
            if archive:
                archive.close()
    # 欠落だけでなく既存ファイルの変化も検出し、別の録音へ置換しない。
    for _ in load_cases(manifest_path, cache_root):
        pass


def load_cases(manifest_path=MANIFEST, cache_root=CACHE):
    for entry in read_manifest(manifest_path)['entries']:
        path = Path(cache_root) / entry['local_wav']
        source = Path(cache_root) / entry['local_source']
        if source.exists() and sha256(source.read_bytes()) != entry['source_sha256']:
            raise RuntimeError(f"元ファイルが固定記録と一致しません: {entry['id']}")
        sr, raw = wavfile.read(path)
        if raw.ndim != 1 or raw.dtype.kind != 'i' or sr != entry['sample_rate']:
            raise RuntimeError(f"入力音声の形式が固定記録と一致しません: {entry['id']}")
        pcm_sha = sha256(raw.astype(raw.dtype.newbyteorder('<')).tobytes())
        if len(raw) != entry['source_samples'] or pcm_sha != entry['decoded_pcm_sha256']:
            raise RuntimeError(f"復号音声が固定記録と一致しません: {entry['id']}")
        wav_sha = sha256(path.read_bytes())
        if wav_sha != entry['wav_sha256']:
            logging.warning('PCMは一致しますがWAVコンテナが異なります: %s SHA-256=%s', entry['id'], wav_sha)
        x = raw.astype(np.float64) / 2 ** (raw.dtype.itemsize * 8 - 1)
        start, length = entry['excerpt_start_sample'], entry['excerpt_samples']
        yield {**{key: entry[key] for key in ('id', 'language', 'style', 'speaker', 'source_utterance_id',
                                             'speaker_gender_as_distributed',
                                             'excerpt_start_sample', 'excerpt_samples')},
               'kind': 'natural_speech', 'x': x[start:start + length], 'sr': int(sr), 'f0_truth': None,
               'source_file': entry['local_wav'], 'source_file_sha256': wav_sha,
               'decoded_pcm_sha256': pcm_sha,
               'original_source_sha256': entry['source_sha256'], 'corpus_entry_id': entry['id']}


def main():
    parser = LoggedArgumentParser(description='固定した英語120録音の準備')
    parser.add_argument('action', choices=('prepare', 'fetch'))
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--offline', action='store_true', help='通信せず取得済みの入力だけを使う')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.manifest, args.cache, offline=args.offline)
    else:
        fetch(args.manifest, args.cache, offline=args.offline)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'corpus'))
