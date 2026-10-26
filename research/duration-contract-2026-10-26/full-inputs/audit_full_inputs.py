"""Read-only independent audit of returned public full-utterance input bytes."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import wave
import zipfile
from pathlib import Path

LIMIT = 45 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-bytes', type=int, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / 'source'
    blob = args.archive.read_bytes()
    require(len(blob) == args.expected_bytes and len(blob) <= LIMIT, 'Archive size differs')
    require(sha(blob) == args.expected_sha256, 'Archive SHA-256 differs')
    contract = json.loads((source / 'original-input-contract.json').read_text())
    prefixes = json.loads((source / 'retained-prefix-contract.json').read_text())
    expected = {entry['id']: entry for entry in contract['entries']}
    prefix_map = {entry['id']: entry for entry in prefixes['cases']}
    require(len(expected) == len(contract['entries']) == 120, 'Parent source count differs')
    require(set(prefix_map) == set(expected), 'Parent prefix identities differ')
    source_names = {p.name for p in source.iterdir() if p.is_file()}
    require(len(source_names) == 6, 'Parent frozen source set differs')
    logs = {'logs/preparation.log'}
    for tool in ('ffmpeg', 'ffprobe'):
        logs.update({f'logs/{tool}-version.txt', f'logs/{tool}-version.stderr'})
    for case in expected:
        logs.update({f'logs/{case}-probe.stderr', f'logs/{case}-decode.stderr'})
    wanted = (source_names | logs | {f'audio/{case}.wav' for case in expected}
              | {'full-input-index.json', 'artifact-manifest.json'})
    observed = []
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)) and set(names) == wanted,
                'Returned member set differs from explicit parent allowlist')
        require(all(info.compress_type == zipfile.ZIP_STORED for info in infos),
                'Archive did not retain its declared stored representation')
        require(sum(info.file_size for info in infos) <= LIMIT, 'Expanded size exceeds limit')
        manifest = json.loads(archive.read('artifact-manifest.json'))
        descriptors = {row['path']: row for row in manifest['files']}
        require(len(descriptors) == len(manifest['files'])
                and set(descriptors) == wanted - {'artifact-manifest.json'},
                'Artifact manifest membership differs')
        for name, row in descriptors.items():
            data = archive.read(name)
            require(len(data) == row['bytes'] and sha(data) == row['sha256'],
                    f'Returned member identity differs: {name}')
        for name in source_names:
            require(archive.read(name) == (source / name).read_bytes(),
                    f'Frozen parent source differs: {name}')
        index = json.loads(archive.read('full-input-index.json'))
        require(index['kind'] == 'same_120_sources_full_utterances_not_previous_6s_protocol'
                and index['sample_rate'] == 16000
                and index['sample_format'] == 'signed PCM16 little-endian',
                'Returned full-input contract differs')
        require(index['source_contract_sha256'] == sha((source / 'original-input-contract.json').read_bytes()),
                'Returned source-contract identity differs')
        require(index['source_archive_sha256'] == contract['librispeech_archive']['sha256']
                and index['all_full_transcripts_verified'] is True
                and index['all_prior_pcm_prefixes_verified'] is True
                and index['vocoder_asr_quality_executions'] == 0,
                'Returned preparation declarations differ')
        records = {row['id']: row for row in index['records']}
        require(len(records) == len(index['records']) == 120 and set(records) == set(expected),
                'Returned recording identities differ')
        for case, original in expected.items():
            row = records[case]
            name = f'audio/{case}.wav'
            data = archive.read(name)
            with wave.open(io.BytesIO(data), 'rb') as wav:
                require(wav.getnchannels() == 1 and wav.getsampwidth() == 2
                        and wav.getframerate() == original['sample_rate'] == 16000
                        and wav.getnframes() == original['source_samples']
                        and wav.getcomptype() == 'NONE', f'WAV contract differs: {case}')
                raw = wav.readframes(wav.getnframes())
                require(not wav.readframes(1), f'Unexpected trailing frames: {case}')
            require(len(data) == len(raw) + 44 and len(raw) == original['source_samples'] * 2,
                    f'Canonical WAV byte count differs: {case}')
            canonical_header = struct.pack(
                '<4sI4s4sIHHIIHH4sI', b'RIFF', len(raw) + 36, b'WAVE', b'fmt ',
                16, 1, 1, 16000, 32000, 2, 16, b'data', len(raw))
            require(data == canonical_header + raw, f'Canonical WAV header differs: {case}')
            require(sha(raw) == original['decoded_pcm_sha256'], f'Full PCM differs: {case}')
            prefix = prefix_map[case]
            require(prefix['samples'] == original['excerpt_samples']
                    and sha(raw[:prefix['samples'] * 2]) == prefix['pcm16_sha256'],
                    f'Existing retained excerpt differs: {case}')
            require(row['speaker'] == original['speaker']
                    and row['source_samples'] == original['source_samples']
                    and row['source_flac_sha256'] == original['source_sha256']
                    and row['pcm16_sha256'] == original['decoded_pcm_sha256']
                    and row['prior_excerpt_samples'] == prefix['samples']
                    and row['prior_excerpt_pcm16_sha256'] == prefix['pcm16_sha256']
                    and row['wav_path'] == name and row['wav_bytes'] == len(data)
                    and row['wav_sha256'] == sha(data), f'Index differs from actual bytes: {case}')
            observed.append({'id': case, 'samples': original['source_samples'],
                             'pcm16_sha256': sha(raw), 'prior_prefix_equal': True})
        warning_logs = {name: len(archive.read(name)) for name in sorted(logs)
                        if name.endswith('.stderr') and archive.read(name)}
    result = {
        'kind': 'parent_actual_full_input_audit_v1', 'archive_sha256': sha(blob),
        'archive_bytes': len(blob), 'all_members_verified': len(wanted),
        'full_pcm_recordings_verified': len(observed),
        'total_samples': sum(row['samples'] for row in observed),
        'prior_excerpt_pcm_prefixes_verified': len(observed),
        'full_transcripts': 'Exact copy of frozen distributed transcript metadata; Cloud reports archive text match',
        'limits': 'Parent did not independently decode original FLAC or reread original archive transcripts; WAV PCM matches fixed original PCM hashes',
        'vocoder_asr_quality_execution_requested': False,
        'nonempty_stderr_log_bytes': warning_logs, 'records': observed,
    }
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
