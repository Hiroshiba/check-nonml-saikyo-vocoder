"""JVS著者研究室の独立公開評定を、既存話者評定として保存する。"""
from __future__ import annotations

import csv
import json
import subprocess

from all_metrics_datasets_remote import CACHE, OUT, ROOT, save_json, sha


def main():
    repo = CACHE / 'jvs/ratings-repo'
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    rows, sources, counts = [], [], {}
    speakers = set()
    for gender in ('male', 'female'):
        path = repo / f'jvs_{gender}_raw_similarity_data.json'
        data = json.loads(path.read_text())
        group_speakers, self_pairs = set(), 0
        for pair, values in data.items():
            a, b = pair.split('-')
            if len(values) != 10 or any(not isinstance(v, int) or not -3 <= v <= 3 for v in values):
                raise ValueError(f'Unexpected rating record {pair}')
            group_speakers.update((a, b))
            speakers.update((a, b))
            if a == b:
                self_pairs += 1
                continue
            rows.append({'speaker_a': a, 'speaker_b': b, 'group': gender,
                         'rating': sum(values) / len(values), 'rating_count': len(values),
                         'raw_ratings': values})
        counts[gender] = {'speakers': len(group_speakers), 'pairs': len(data) - self_pairs,
                          'self_pairs_excluded': self_pairs}
        sources.append({'url': f'https://github.com/sarulab-speech/jvs_similarity_score/blob/{revision}/{path.name}',
                        'local_path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())})
    output = OUT / 'jvs-speaker-ratings.csv'
    with output.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['speaker_a', 'speaker_b', 'group', 'rating'])
        writer.writeheader()
        writer.writerows({k: row[k] for k in writer.fieldnames} for row in rows)
    availability = json.loads((ROOT / 'data/jvs_available_v1.json').read_text())
    existing = sorted({entry['speaker'] for entry in availability['entries']})
    manifest = {'id': 'jvs-official-existing-speaker-ratings-v1',
                'repository': 'https://github.com/sarulab-speech/jvs_similarity_score', 'revision': revision,
                'source_files': sources, 'speaker_count': len(speakers), 'counts': counts, 'ratings': rows,
                'csv_path': str(output.relative_to(ROOT)), 'csv_sha256': sha(output.read_bytes()),
                'tags_license': 'CC BY-SA 4.0, JVS official corpus terms',
                'terms_url': 'https://sites.google.com/site/shinnosuketakamichi/research-topics/jvs_corpus',
                'exact_original_rating_stimulus_recording_ids': None,
                'rating_scope': 'Existing perceptual similarity of original JVS speakers; not reconstructed-audio MOS',
                'planned_audio': '100 speakers, one common parallel100 normal recording each, selection fixed before extraction',
                'audio_acquisition_status': 'blocked_official_google_drive_quota_exceeded',
                'blocker_evidence': {'http_status': 200, 'content_type': 'text/html; charset=utf-8',
                                     'html_title': 'Google Drive - Quota exceeded',
                                     'observed_at_utc': '2026-10-13T20:25:09Z',
                                     'url': 'https://drive.usercontent.google.com/download?id=19oAw8wWn3Y7z6CKChRdAyGOB9yupL_Xt&export=download&confirm=t',
                                     'subsequent_retry': False},
                'previously_available_audio_speakers': existing,
                'previously_available_audio_recordings': len(availability['entries']),
                'audio_redistribution': False,
                'measurement_ready': False}
    save_json(OUT / 'jvs-speaker-ratings.json', manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'ratings'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
