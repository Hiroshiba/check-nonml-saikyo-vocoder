"""復旧後の補助集合は、データ取得より前に新しい選択規則を固定する。"""
from __future__ import annotations

import argparse
from pathlib import Path

from all_metrics_common import ROOT, RUN, freeze, read
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256

DOCUMENT = ROOT / 'research/all-method-corpora-plan-recovery-2026-10-14.md'
SPEAKERS = ('p360', 'p361', 'p362', 'p363', 'p364', 'p374', 'p376')
HUMAN_CSV_SHA = '63f173185694582e60610e35c66f58a63ccc85f02114bc8675cbadcc612d21d5'
RULES = {
    'train': {
        'split': 'dev-clean', 'salt': 'all-method-metrics-dev-clean-recovery-20261014',
        'source_url': 'https://www.openslr.org/resources/12/dev-clean.tar.gz',
        'speaker_selection': 'all 40 speakers labelled dev-clean in official SPEAKERS.TXT',
        'candidate_selection_order': 'ascending sha256((salt+"|"+speaker+"|"+member).encode("utf-8")), then member',
        'final_manifest_and_inputs_order': 'ascending source utterance id',
        'recordings_per_speaker': 3, 'recordings': 120, 'speakers': 40,
        'selection_uses_audio_or_scores': False,
        'audio_validation': 'after fixed IDs; mono PCM16 16000Hz, >=1s, finite, nonzero source/excerpt power, abs(x)>=1-1/32768 fraction<=0.001',
        'on_invalid_selected_audio': 'stop without replacement',
        'excerpt': 'start=0, samples=min(source_samples,16000*6)',
        'normalization': False, 'silence_trimming': False,
        'disjoint_from_evaluation': ['speaker', 'id', 'source_utterance_id', 'source_sha256',
                                     'source_pcm_sha256', 'excerpt_pcm_sha256', 'input_npy_sha256'],
    },
    'vctk': {
        'source_url': 'https://datashare.ed.ac.uk/handle/10283/3443',
        'archive_url': 'https://datashare.ed.ac.uk/server/api/core/bitstreams/535f4286-e54c-4038-838c-a02285e32cb2/content',
        'salt': 'all-method-metrics-vctk-20261014/', 'speakers': list(SPEAKERS),
        'microphone': 'mic1', 'sample_rate': 48000, 'recordings_per_speaker': 18, 'recordings': 126,
        'order': 'decreasing FLAC uncompressed byte count; ties sha256((salt+member).encode()); then member',
        'reference_conditions': 'mono PCM16 48000Hz, >=3s, finite, nonzero source/excerpt power, abs(x)>=1-1/32768 fraction<=0.001',
        'excerpt': 'start=0, samples=min(source_samples,48000*10)',
        'selection_uses_vocoder_or_scores': False, 'normalization': False, 'silence_trimming': False,
        'preserve_full_original': True,
        'training_scope': 'known GOLF train/validation excluded only; not held-out for all models',
    },
    'human': {
        'source_csv_url': 'https://raw.githubusercontent.com/nii-yamagishilab/ASVspoof2019-LA-human-assessment-data/master/score_similarity.csv',
        'source_csv_sha256': HUMAN_CSV_SHA,
        'audio_url': 'https://datashare.ed.ac.uk/server/api/core/bitstreams/a9f87c35-f055-4015-80e2-2fdff0d46269/content',
        'salt': 'asvspoof2019-bonafide-human-v2-multirater-20261014',
        'categories': ['target', 'non-target'], 'minimum_distinct_listeners': 2,
        'anchors': 'all B speakers with an anchor having >=2 target and >=2 non-target candidate recordings; one anchor per B speaker',
        'order': 'sha256((salt+"|"+text).encode()); speaker:ID, anchor:B.wav, candidate:B.wav:A.wav; category target then non-target',
        'candidates_per_category': 2, 'expected_pairs': 84, 'expected_recordings': 105,
        'expected_speakers': 28, 'expected_anchors': 21, 'expected_anchor_speakers': 21,
        'selection_uses_ratings_or_features': False,
        'rating_target': 'within-listener trial mean then equal distinct-listener mean, unshifted 0..9',
        'audio': 'full original 16kHz mono; no crop, normalization, or silence trimming',
        'privacy': 'full CSV and listener IDs remain private; do not publish raw listener records',
    },
}
SOURCES = {
    'train': ('all_metrics_datasets_train.py',),
    'vctk': ('all_metrics_datasets_vctk.py', 'all_metrics_vctk_inputs.py', 'all_metrics_datasets_remote.py'),
    'human': ('all_metrics_datasets_human.py', 'all_metrics_human_data.py', 'all_metrics_datasets_remote.py'),
}


def plan_path(kind):
    return RUN / 'corpora/selection-plans' / f'{kind}.json'


def specification(kind):
    paths = [Path(__file__), DOCUMENT, ROOT / 'scripts/all_metrics_common.py',
             ROOT / 'vocoderbench/quality_core.py', *(ROOT / 'scripts' / p for p in SOURCES[kind])]
    if kind in ('train', 'human'):
        paths.append(ROOT / 'research/all-method-features-plan-recovery-2026-10-14.md')
    value = {'schema_version': 1, 'study': f'recovery-new-{kind}-selection',
             'implementation_origin': 'new_contract_not_old_manifest_reconstruction',
             'rule': RULES[kind], 'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths}}
    if kind == 'train':
        value['evaluation_manifest_sha256'] = sha256(ROOT / 'data/clean_speech_v1.json')
    return value


def require_plan(kind):
    path = plan_path(kind)
    value = read(path)
    if value != specification(kind):
        raise ValueError(f'{kind}: 取得前に固定した選択規則/ソース/計画が不一致。別契約が必要です')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=tuple(RULES))
    args = parser.parse_args()
    freeze(plan_path(args.kind), specification(args.kind))
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-corpus-plan'))
