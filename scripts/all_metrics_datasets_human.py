"""公式ASV CSVのラベルだけで対を固定し、その後に既存評定を結合する。"""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
from pathlib import Path
import re
import shutil

import numpy as np

from all_metrics_common import RUN, freeze, read
from all_metrics_datasets_contract import DOCUMENT, plan_path, require_plan
from vocoderbench.quality_core import sha256

OUT = RUN / 'human-similarity'


def select_ids(csv_path, salt):
    """score列を参照せず、元規則のカテゴリ/ID/話者/人数だけを使う。"""
    grouped = {}
    with csv_path.open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        next(reader)
        for row in reader:
            if len(row) < 8:
                raise ValueError('公式CSVの必要8列がありません')
            if row[0] != 'bonafide':
                continue
            if row[1] not in ('target', 'non-target') or not row[7]:
                raise ValueError('未知のカテゴリまたは空のlistener ID')
            key = row[3], row[5]
            metadata = {'sample_a': row[5], 'sample_b': row[3], 'type': row[1],
                        'a_speaker': row[4], 'b_speaker': row[2]}
            if key not in grouped:
                grouped[key] = {**metadata, 'listeners': set(), 'raw_rating_count': 0}
            if any(grouped[key][k] != value for k, value in metadata.items()):
                raise ValueError('同一録音対のカテゴリ/話者が一貫しません')
            grouped[key]['listeners'].add(row[7])
            grouped[key]['raw_rating_count'] += 1
    anchors = defaultdict(lambda: defaultdict(list))
    for row in grouped.values():
        if len(row['listeners']) >= 2:
            anchors[row['sample_b']][row['type']].append(row)
    speakers = defaultdict(list)
    for anchor, categories in anchors.items():
        if len(categories['target']) >= 2 and len(categories['non-target']) >= 2:
            labels = {r['b_speaker'] for rows in categories.values() for r in rows}
            if len(labels) != 1:
                raise ValueError('同じB anchorの話者が一貫しません')
            speakers[next(iter(labels))].append(anchor)
    def h(text):
        return hashlib.sha256((salt+'|'+text).encode('utf-8')).hexdigest()
    selected = []
    for speaker in sorted(speakers, key=lambda value: h('speaker:'+value)):
        anchor = min(speakers[speaker], key=lambda value: h('anchor:'+value))
        for category in ('target', 'non-target'):
            candidates = sorted(anchors[anchor][category],
                key=lambda row: h('candidate:'+anchor+':'+row['sample_a']))[:2]
            for row in candidates:
                selected.append({key: value for key, value in row.items() if key != 'listeners'}
                                | {'distinct_listener_count': len(row['listeners'])})
    return selected


def label_contract(csv_path, plan):
    selected = select_ids(csv_path, plan['rule']['salt'])
    identities = {}
    seen = set()
    for row in selected:
        pair = row['sample_a'], row['sample_b']
        if pair in seen or pair[0] == pair[1]:
            raise ValueError('重複対または同一録音のA/B対')
        seen.add(pair)
        if (row['a_speaker'] == row['b_speaker']) != (row['type'] == 'target'):
            raise ValueError('target/non-targetと話者ラベルが不一致')
        for role in ('a', 'b'):
            sample, speaker = row[f'sample_{role}'], row[f'{role}_speaker']
            if not re.fullmatch(r'LA_E_[A0-9]+\.wav', sample) or not speaker:
                raise ValueError('想定外の公式録音ID/空の話者')
            if sample in identities and identities[sample] != speaker:
                raise ValueError('同じ録音IDの話者が一貫しません')
            identities[sample] = speaker
    counts = {'pairs': len(selected), 'recordings': len(identities),
              'speakers': len(set(identities.values())),
              'anchors': len({r['sample_b'] for r in selected}),
              'anchor_speakers': len({r['b_speaker'] for r in selected})}
    for name, count in counts.items():
        if count != plan['rule']['expected_'+name]:
            raise ValueError(f'事前規則から得るASV分母が違います: {name}={count}。別集合で代用しません')
    contract = {'schema_version': 1, 'implementation_origin': 'new_label_selection_without_old_proposal',
        'selection_plan_sha256': sha256(plan_path('human')), 'source_csv_sha256': sha256(csv_path),
        'selection_rule': plan['rule'], 'counts': counts, 'pairs': selected, 'identities': identities,
        'scores_used_for_selection': False}
    freeze(OUT / 'label-selection.json', contract)
    return contract


def prepare_selection(csv_path):
    plan = require_plan('human')
    csv_path = Path(csv_path)
    if sha256(csv_path) != plan['rule']['source_csv_sha256']:
        raise ValueError('公式CSVが事前固定版と不一致。評定値を見る前に停止します')
    labels = label_contract(csv_path, plan)
    wanted = {(r['sample_a'], r['sample_b']): r for r in labels['pairs']}
    ratings = {key: defaultdict(list) for key in wanted}
    with csv_path.open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        next(reader)
        for row in reader:
            if len(row) < 8:
                raise ValueError('公式CSV列不足')
            key = row[5], row[3]
            if key not in wanted:
                continue
            selected = wanted[key]
            if (row[0], row[1], row[4], row[2]) != (
                    'bonafide', selected['type'], selected['a_speaker'], selected['b_speaker']):
                raise ValueError('選択対のカテゴリ/話者が不一致')
            score = float(row[6])
            if not np.isfinite(score) or not 0 <= score <= 9:
                raise ValueError('公開評定の0–9範囲外')
            ratings[key][row[7]].append(score)
    pairs = []
    for key, selected in wanted.items():
        raters = ratings[key]
        if (len(raters) != selected['distinct_listener_count']
                or sum(map(len, raters.values())) != selected['raw_rating_count']):
            raise ValueError('ラベル固定前後のlistener数/評定数が不一致')
        means = [float(np.mean(values)) for values in raters.values()]
        pairs.append({**selected, 'human_rating': float(np.mean(means)),
            'human_mean_all_trials': float(np.mean([v for values in raters.values() for v in values]))})
    if sha256(csv_path) != labels['source_csv_sha256']:
        raise ValueError('選択/評定読込中にCSVが変わりました')
    private = RUN / 'corpora/asvhuman-private/score_similarity.csv'
    private.parent.mkdir(parents=True, exist_ok=True)
    if private.exists() and sha256(private) != labels['source_csv_sha256']:
        raise ValueError('保存済みprivate CSVと入力が不一致')
    if not private.exists():
        shutil.copyfile(csv_path, private)
    counts = labels['counts']
    contract = {'id': 'asvspoof2019-bonafide-multirater105-recovery-v1', 'schema_version': 1,
        'selection_plan_sha256': sha256(plan_path('human')),
        'selection_label_manifest_sha256': sha256(OUT / 'label-selection.json'),
        'source_csv_sha256': labels['source_csv_sha256'], 'salt': plan['rule']['salt'],
        'selection': plan['rule'], 'plan_sha256': sha256(DOCUMENT),
        'pair_count': counts['pairs'], 'recording_count': counts['recordings'],
        'speaker_count': counts['speakers'], 'b_anchor_count': counts['anchors'],
        'pairs': pairs, 'identities': labels['identities'],
        'target': plan['rule']['rating_target'], 'privacy': plan['rule']['privacy'],
        'audio_license': 'ODC-By per official corpus README; not applied to ratings CSV',
        'ratings_terms': 'official author research release; no separate license verified; no full redistribution',
        'citations': ['https://doi.org/10.1016/j.csl.2020.101114',
                      'https://doi.org/10.21437/Interspeech.2019-2249']}
    freeze(OUT / 'selection.json', contract)
    freeze(OUT / 'public-evidence/cohort-and-ratings.json', contract)
    return contract


def require_selection():
    require_plan('human')
    value = read(OUT / 'selection.json')
    if (value['selection_plan_sha256'] != sha256(plan_path('human'))
            or value['selection_label_manifest_sha256'] != sha256(OUT / 'label-selection.json')):
        raise ValueError('ASV選択契約とラベル先行固定のhash不一致')
    return value
