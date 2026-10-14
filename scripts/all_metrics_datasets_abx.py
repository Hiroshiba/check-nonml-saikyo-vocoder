"""公式abxLSラベルを固定LibriSpeech120区間へ結合し、ABX三つ組を固定。"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import logging

from all_metrics_common import freeze, read
from all_metrics_datasets_remote import CACHE, OUT, ROOT, sha
from all_metrics_datasets_abx_contract import PLAN, require_label

SALT = 'all-method-metrics-abxls-20261014/'
SILENCE = {'SIL', 'SPN', 'SILENCE', 'SP', 'NSN', '<eps>'}


def main():
    source = CACHE / 'abxls/members/test-clean/triphone-test-clean.item'
    require_label(source)
    frozen_path = ROOT / 'data/clean_speech_v1.json'
    entries = json.loads(frozen_path.read_text())['entries']
    by_utterance = {e['source_utterance_id']: e for e in entries}
    items, excluded, matched = [], [], set()
    for line_number, line in enumerate(source.read_text().splitlines()[1:], 2):
        utterance, onset, offset, phone, left, right, speaker = line.split()
        if utterance not in by_utterance:
            continue
        matched.add(utterance)
        entry = by_utterance[utterance]
        start, end = float(onset), float(offset)
        seconds = entry['excerpt_samples'] / entry['sample_rate']
        item = {'id': f'abxls_{utterance}_{line_number}', 'utterance_id': utterance,
                'recording_id': entry['id'], 'speaker': entry['speaker'], 'phone': phone,
                'left_phone': left, 'right_phone': right, 'context': f'{left}|{right}',
                'onset_seconds': start, 'offset_seconds': end, 'source_line': line_number,
                'official_speaker': speaker, 'sample_rate': entry['sample_rate'],
                'start_sample': round(start * entry['sample_rate']),
                'end_sample': round(end * entry['sample_rate'])}
        reasons = []
        if speaker != utterance.split('-')[0]:
            reasons.append('speaker_id_mismatch')
        if not 0 <= start < end <= seconds:
            reasons.append('not_fully_within_frozen_excerpt')
        if SILENCE & {phone, left, right}:
            reasons.append('silence_or_noise_phone')
        if reasons:
            excluded.append({**item, 'reasons': reasons})
        else:
            items.append(item)
    items.sort(key=lambda x: x['id'])
    contexts = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for item in items:
        contexts[item['context']][item['speaker']][item['phone']].append(item['id'])
    triples = {'within_speaker': [], 'across_speaker': []}
    for context, speakers in sorted(contexts.items()):
        for speaker, phones in sorted(speakers.items()):
            for phone_a, aa in sorted(phones.items()):
                for phone_b, bb in sorted(phones.items()):
                    if phone_a == phone_b:
                        continue
                    for x_speaker, x_phones in sorted(speakers.items()):
                        condition = 'within_speaker' if x_speaker == speaker else 'across_speaker'
                        for a in aa:
                            for b in bb:
                                for x in x_phones.get(phone_a, []):
                                    if len({a, b, x}) != 3:
                                        continue
                                    triples[condition].append({'a': a, 'b': b, 'x': x, 'condition': condition})
    eligible = {key: len(rows) for key, rows in triples.items()}
    selected = []
    for condition, rows in triples.items():
        rows.sort(key=lambda row: sha((SALT + '|'.join(row[key] for key in ('a', 'b', 'x'))).encode()))
        selected.extend(rows[:20000])
    used = {row[key] for row in selected for key in ('a', 'b', 'x')}
    used_items = [item for item in items if item['id'] in used]
    lookup = {e['id']: e for e in used_items}
    condition_counts = {}
    for condition in triples:
        ids = {row[key] for row in selected if row['condition'] == condition for key in ('a', 'b', 'x')}
        condition_counts[condition] = {'triplets': sum(r['condition'] == condition for r in selected),
            'used_tokens': len(ids), 'used_recordings': len({lookup[i]['recording_id'] for i in ids}),
            'used_speakers': len({lookup[i]['speaker'] for i in ids})}
    manifest = {'id': 'abxls-clean-speech-v1-clip-triphones',
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'selection_plan_sha256': sha(PLAN.read_bytes()),
                'frozen_audio_manifest_sha256': sha(frozen_path.read_bytes()),
                'label_file': str(source.relative_to(ROOT)), 'label_sha256': sha(source.read_bytes()),
                'license': 'CC BY 4.0 (archive README.md)',
                'source_url': 'https://zerospeech.com/tasks/task_1/benchmarks_datasets/',
                'all_items': items, 'items': used_items, 'triplets': selected,
                'excluded': excluded, 'unmatched_utterances': sorted(set(by_utterance) - matched),
                'counts': {'source_recordings': len(entries), 'matched_recordings': len(matched),
                           'eligible_tokens': len(items), 'used_tokens': len(used_items),
                           'used_recordings': len({e['recording_id'] for e in used_items}),
                           'used_speakers': len({e['speaker'] for e in used_items}),
                           'eligible_triplets': eligible, 'by_condition': condition_counts,
                           'selected_triplets': dict(Counter(t['condition'] for t in selected))},
                'label_scope': 'Official abxLS v1.1 full-triphone spans, all three phones inside frozen excerpt',
                'scope_limit': 'subset ABX, not full official abxLS leaderboard; no new ASR alignment'}
    target = OUT / 'abxls120-triphones.json'
    if target.exists():
        manifest['created_at_utc'] = read(target)['created_at_utc']
    freeze(target, manifest)
    print(json.dumps(manifest['counts'], indent=2))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(OUT / 'abxls-join.log')])
    try:
        main()
    except Exception:
        logging.exception('ABX official label join failed')
        raise
