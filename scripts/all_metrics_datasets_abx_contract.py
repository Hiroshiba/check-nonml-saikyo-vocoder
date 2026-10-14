"""公式ABXラベルの取得前契約と、取得後の索引・原本hashを固定する。"""
from __future__ import annotations

import argparse

from all_metrics_common import ROOT, RUN, freeze, read
from all_metrics_datasets_remote import RemoteZip, URLS
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256

PLAN = RUN / 'corpora/selection-plans/abx.json'
ACQUISITION = RUN / 'corpora/abx-acquisition-contract.json'
LABEL = RUN / 'corpora/abx-label-source.json'
DOCUMENT = ROOT / 'research/all-method-abx-plan-recovery-2026-10-14.md'
LABEL_MEMBER = 'test-clean/triphone-test-clean.item'


def specification():
    paths = [__file__, ROOT / 'scripts/all_metrics_datasets_abx.py',
        ROOT / 'scripts/all_metrics_datasets_abx_sources.py',
        ROOT / 'scripts/all_metrics_datasets_remote.py', ROOT / 'scripts/all_metrics_common.py',
        ROOT / 'vocoderbench/quality_core.py', DOCUMENT,
        ROOT / 'research/all-method-features-plan-recovery-2026-10-14.md']
    from pathlib import Path
    return {'schema_version': 1, 'study': 'recovery-new-abx-selection',
        'implementation_origin': 'new_contract_not_old_manifest_reconstruction',
        'source_sha256': {str(Path(p).relative_to(ROOT)): sha256(p) for p in paths},
        'evaluation_manifest_sha256': sha256(ROOT / 'data/clean_speech_v1.json'),
        'rule': {'archive_url': URLS['abxls'], 'label_member': LABEL_MEMBER,
            'source_page': 'https://zerospeech.com/tasks/task_1/benchmarks_datasets/',
            'salt': 'all-method-metrics-abxls-20261014/',
            'recordings': 'fixed clean_speech_v1 120 IDs; no new recordings',
            'scope': 'full triphone interval inside each original frozen excerpt, at most 6s',
            'exclude': ['speaker differs from utterance prefix', 'not 0 <= onset < offset <= excerpt duration',
                'any center/left/right phone in SIL,SPN,SILENCE,SP,NSN,<eps>'],
            'triplets': 'A/B same speaker and left/right context, distinct center phones; X same phone as A and same context; all three token IDs distinct',
            'conditions': ['within_speaker', 'across_speaker'],
            'selection_order': 'ascending sha256((salt + a + "|" + b + "|" + x).encode()) per condition',
            'maximum_triplets_per_condition': 20000,
            'selection_uses_audio_features_or_scores': False,
            'source_identity': 'audit all 120 against official full WAV PCM; only recordings used by selected triplets are required for ABX',
            'license': 'verify archive README; expected CC BY 4.0',
            'normalization': False, 'silence_trimming': False, 'realignment': False}}


def require_plan():
    value = read(PLAN)
    if value != specification():
        raise ValueError('ABX取得前契約/sourceが不一致。別契約が必要です')
    return value


def bind_index(source):
    plan = require_plan()
    if source.url != plan['rule']['archive_url'] or read(source.index)['url'] != source.url:
        raise ValueError('公式ABXのZIP配布元不一致')
    value = {'selection_plan_sha256': sha256(PLAN), 'archive_url': source.url,
        'archive_bytes': source.size, 'archive_index_sha256': sha256(source.index)}
    freeze(ACQUISITION, value)
    return value


def labels():
    require_plan()
    source = RemoteZip('abxls')
    acquisition = bind_index(source)
    path, metadata = source.member(source.by_name[LABEL_MEMBER])
    freeze(LABEL, {'selection_plan_sha256': sha256(PLAN),
        'acquisition_contract_sha256': sha256(ACQUISITION), **metadata,
        'archive_index_sha256': acquisition['archive_index_sha256'],
        'label_sha256': sha256(path)})
    notices = [row for row in source.entries if row['member'].rsplit('/', 1)[-1].lower()
               in ('readme.md', 'readme.txt', 'license', 'license.txt', 'copying')]
    records = []
    for row in notices:
        notice, record = source.member(row)
        records.append({**record, 'bytes': notice.stat().st_size})
    freeze(RUN / 'corpora/abx-notices.json', records)


def require_label(path):
    require_plan()
    value = read(LABEL)
    if (value['selection_plan_sha256'] != sha256(PLAN)
            or value['acquisition_contract_sha256'] != sha256(ACQUISITION)
            or value['label_sha256'] != sha256(path)):
        raise ValueError('ABXラベル原本/hash/取得前契約が不一致')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('plan', 'labels'))
    args = parser.parse_args()
    if args.stage == 'plan':
        freeze(PLAN, specification())
    else:
        labels()
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-abx-contract'))
