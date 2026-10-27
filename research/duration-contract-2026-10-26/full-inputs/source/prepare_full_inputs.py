"""Recover fixed public full utterances; no vocoder, ASR, or quality execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import subprocess
import tarfile
import wave
import zipfile
from pathlib import Path

ARCHIVE_BYTES = 346663984
ARCHIVE_SHA = '39fde525e59672dc6d1551919b1478f724438a95aa55f874b576be21967e6c23'
CONTRACT_SHA = '644f4d57483366bb20d8dbcfdaa254e354aed4af8318a6a2984bb2e8b3ddc9c1'
LIMIT = 45 * 1024 * 1024
LOGGER = logging.getLogger(__name__)
SOURCE_FILES = (
    'prepare_full_inputs.py', 'original-input-contract.json',
    'retained-prefix-contract.json', 'PREPARATION.md', 'LICENSE-NOTICE.txt',
    'source-lock.json',
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + '\n', encoding='utf-8')


def command(args, stderr_path):
    try:
        result = subprocess.run(args, capture_output=True, check=False, timeout=120)
    except subprocess.TimeoutExpired as error:
        stderr_path.write_bytes(error.stderr or b'')
        LOGGER.exception('Command timed out: %r', args)
        raise
    stderr_path.write_bytes(result.stderr)
    if result.stderr:
        LOGGER.warning('%s: %s', args[0], result.stderr.decode('utf-8', 'replace'))
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {args!r}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    lock = json.loads((source / 'source-lock.json').read_text())
    if {row['path'] for row in lock['files']} != set(SOURCE_FILES) - {'source-lock.json'}:
        raise ValueError('Source lock file set differs')
    for row in lock['files']:
        path = source / row['path']
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError(f'Frozen source identity differs: {path.name}')
    contract_path = source / 'original-input-contract.json'
    if digest(contract_path) != CONTRACT_SHA:
        raise ValueError('Original public input contract identity differs')
    contract = json.loads(contract_path.read_text())
    prefixes = json.loads((source / 'retained-prefix-contract.json').read_text())
    entries = {entry['id']: entry for entry in contract['entries']}
    prefix_map = {entry['id']: entry for entry in prefixes['cases']}
    if (len(contract['entries']) != 120 or len(prefixes['cases']) != 120
            or len(entries) != 120 or len(prefix_map) != 120
            or set(entries) != set(prefix_map)):
        raise ValueError('Exactly the same 120 source utterances are required')
    if (args.archive.stat().st_size != ARCHIVE_BYTES
            or digest(args.archive) != ARCHIVE_SHA):
        raise ValueError('Public LibriSpeech archive identity differs')
    for entry in entries.values():
        if (not re.fullmatch(r'librispeech_\d+-\d+-\d+', entry['id'])
                or entry['sample_rate'] != 16000 or entry['excerpt_start_sample'] != 0
                or not 0 < entry['excerpt_samples'] <= entry['source_samples']):
            raise ValueError('Unexpected fixed source metadata')
    expected_audio_bytes = sum(44 + 2 * e['source_samples'] for e in entries.values())
    if expected_audio_bytes + 5 * 1024 * 1024 > LIMIT:
        raise ValueError('Predeclared raw audio plus metadata budget exceeds limit')
    for program in ('ffmpeg', 'ffprobe'):
        if shutil.which(program) is None:
            raise RuntimeError(f'Required existing decoder not found: {program}')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    payload = out / 'payload'
    payload.mkdir()
    audio = payload / 'audio'
    audio.mkdir()
    logs = payload / 'logs'
    logs.mkdir()
    scratch = out / 'sources'
    scratch.mkdir()
    logging.basicConfig(filename=logs / 'preparation.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    try:
        for program in ('ffmpeg', 'ffprobe'):
            version = command([program, '-version'], logs / f'{program}-version.stderr')
            (logs / f'{program}-version.txt').write_bytes(version)
        wanted = {entry['source']['member']: entry for entry in entries.values()}
        transcripts = {}
        records = []
        seen = set()
        with tarfile.open(args.archive, 'r:gz') as archive:
            for member in archive:
                if not member.isfile():
                    continue
                if member.name.endswith('.trans.txt'):
                    if member.size > 1024 * 1024:
                        raise ValueError('Transcript member exceeds declared bound')
                    for line in archive.extractfile(member).read().decode('utf-8').splitlines():
                        utterance, text = line.split(' ', 1)
                        case = 'librispeech_' + utterance
                        if case in entries:
                            if case in transcripts:
                                raise ValueError(f'Duplicate transcript: {case}')
                            transcripts[case] = text.strip()
                    continue
                if member.name not in wanted:
                    continue
                entry = wanted[member.name]
                case = entry['id']
                if case in seen or member.size > 10 * 1024 * 1024:
                    raise ValueError('Duplicate or oversized selected source member')
                seen.add(case)
                data = archive.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != entry['source_sha256']:
                    raise ValueError(f'Source FLAC identity differs: {case}')
                flac = scratch / (case + '.flac')
                flac.write_bytes(data)
                probe = command(['ffprobe', '-v', 'warning', '-select_streams', 'a',
                                 '-show_entries', 'stream=sample_rate,channels',
                                 '-of', 'json', str(flac)], logs / f'{case}-probe.stderr')
                streams = json.loads(probe)['streams']
                if (len(streams) != 1 or streams[0]['sample_rate'] != '16000'
                        or streams[0]['channels'] != 1):
                    raise ValueError(f'Actual source stream differs: {case}')
                raw = command(['ffmpeg', '-nostdin', '-v', 'warning', '-i', str(flac),
                               '-map', '0:a:0', '-vn', '-acodec', 'pcm_s16le',
                               '-f', 's16le', '-'], logs / f'{case}-decode.stderr')
                if (len(raw) != entry['source_samples'] * 2
                        or hashlib.sha256(raw).hexdigest() != entry['decoded_pcm_sha256']):
                    raise ValueError(f'Full decoded integer PCM differs: {case}')
                prefix = prefix_map[case]
                if (prefix['samples'] != entry['excerpt_samples']
                        or hashlib.sha256(raw[:prefix['samples'] * 2]).hexdigest()
                        != prefix['pcm16_sha256']):
                    raise ValueError(f'Existing retained excerpt differs: {case}')
                wav = audio / (case + '.wav')
                with wave.open(str(wav), 'wb') as writer:
                    writer.setnchannels(1)
                    writer.setsampwidth(2)
                    writer.setframerate(16000)
                    writer.writeframes(raw)
                if wav.stat().st_size != 44 + len(raw):
                    raise ValueError('Canonical PCM16 WAV size differs')
                records.append({'id': case, 'speaker': entry['speaker'],
                                'source_samples': entry['source_samples'],
                                'source_flac_sha256': entry['source_sha256'],
                                'pcm16_sha256': entry['decoded_pcm_sha256'],
                                'prior_excerpt_samples': prefix['samples'],
                                'prior_excerpt_pcm16_sha256': prefix['pcm16_sha256'],
                                'wav_path': wav.relative_to(payload).as_posix(),
                                'wav_bytes': wav.stat().st_size, 'wav_sha256': digest(wav)})
        if seen != set(entries) or set(transcripts) != set(entries):
            raise ValueError('Missing full source or transcript')
        for case, entry in entries.items():
            if transcripts[case] != entry['transcript']:
                raise ValueError(f'Full transcript differs: {case}')
        for name in SOURCE_FILES:
            shutil.copyfile(source / name, payload / name)
        dump(payload / 'full-input-index.json', {
            'kind': 'same_120_sources_full_utterances_not_previous_6s_protocol',
            'sample_rate': 16000, 'sample_format': 'signed PCM16 little-endian',
            'source_archive_sha256': ARCHIVE_SHA, 'source_contract_sha256': CONTRACT_SHA,
            'all_full_transcripts_verified': True, 'all_prior_pcm_prefixes_verified': True,
            'vocoder_asr_quality_executions': 0, 'records': sorted(records, key=lambda r: r['id'])})
        LOGGER.info('All 120 source files, full PCM, transcripts, and prior prefixes verified')
        logging.shutdown()
        files = sorted(p for p in payload.rglob('*') if p.is_file())
        manifest = {'files': [{'path': p.relative_to(payload).as_posix(),
                              'bytes': p.stat().st_size, 'sha256': digest(p)} for p in files]}
        dump(payload / 'artifact-manifest.json', manifest)
        files.append(payload / 'artifact-manifest.json')
        if sum(p.stat().st_size for p in files) + 1024 * len(files) > LIMIT:
            raise ValueError('Original payload exceeds predeclared ZIP size budget')
        result = out / 'fixed120-full-utterance-pcm16-20261026.zip'
        with zipfile.ZipFile(result, 'x', compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(files):
                archive.write(path, path.relative_to(payload))
        if result.stat().st_size > LIMIT:
            raise ValueError('Original result exceeded predeclared archive bound')
        print(json.dumps({'archive': str(result), 'bytes': result.stat().st_size,
                          'sha256': digest(result), 'recordings': len(records)}))
    except BaseException:
        LOGGER.exception('Full input preparation failed; no replacement or scientific retry')
        logging.shutdown()
        raise


if __name__ == '__main__':
    main()
