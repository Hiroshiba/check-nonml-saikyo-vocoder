"""推論や指標計算をせず、可用性別群と既存入力・sourceの実SHAを固定する。"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from settings import ROOT, OUT, ORIGINAL, PLAN, PACKAGE
from all_metrics_common import METHODS, RUN, freeze, now, read
from all_metrics_features_common import TRAIN
from all_metrics_features_support import load_train
from all_metrics_process_receipts import source_receipt
from vocoderbench.quality_core import sha256

MISSING = 'LA_E_A9407859.wav'
AVAILABILITY = RUN / 'operations/human105-missing-recording-availability-review.json'
AVAILABILITY_SHA = 'df3181056e719719e4287d22ead139d730960feb8991070732b7b54799b19548'


def main():
    if sha256(AVAILABILITY) != AVAILABILITY_SHA:
        raise ValueError('独立可用性計数SHA不一致')
    labels = read(ORIGINAL / 'label-selection.json')
    kept = [row for row in labels['pairs'] if MISSING not in (row['sample_a'], row['sample_b'])]
    removed = [row for row in labels['pairs'] if row not in kept]
    if len(kept) != 80 or len(removed) != 4 or any(row['sample_b'] != MISSING for row in removed):
        raise ValueError('欠落anchorの接続4対だけの除外ではない')
    identities = {}
    by_anchor = defaultdict(Counter)
    for row in kept:
        for role in ('a', 'b'):
            sample, speaker = row[f'sample_{role}'], row[f'{role}_speaker']
            if sample in identities and identities[sample] != speaker:
                raise ValueError('録音と話者の結合不一致')
            identities[sample] = speaker
        by_anchor[row['sample_b']][row['type']] += 1
    counts = {'pairs': len(kept), 'recordings': len(identities), 'speakers': len(set(identities.values())),
              'anchors': len(by_anchor), 'anchor_speakers': len({r['b_speaker'] for r in kept})}
    if counts != {'pairs': 80, 'recordings': 100, 'speakers': 27, 'anchors': 20, 'anchor_speakers': 20}:
        raise ValueError('別群の予定計数不一致')
    if any(dict(value) != {'target': 2, 'non-target': 2} for value in by_anchor.values()):
        raise ValueError('同2異2の候補集合が崩れた')
    timing = {'adopted_at_utc': '2026-10-14T17:29:00+00:00', 'timing_precision': 'minute; parent adoption',
        'selection': 'post_acquisition_availability_before_feature_extraction_or_method_results',
        'rule': 'mechanically exclude only pairs incident to LA_E_A9407859.wav; preserve all other pairs',
        'uses_rating_values': False, 'uses_feature_or_metric_values': False,
        'original105_gate': 'unchanged_and_incomplete', 'replaces_original105': False,
        'missing_recording_treated_as_success': False, 'availability_review_sha256': AVAILABILITY_SHA}
    freeze(OUT / 'label-selection.json', {'id': 'asvspoof2019-availability100-20261014-v1',
        'counts': counts, 'pairs': kept, 'removed_pairs': removed, 'availability_selection': timing,
        'original_label_selection_sha256': sha256(ORIGINAL / 'label-selection.json')})
    original = read(ORIGINAL / 'selection.json')
    keys = {(r['sample_a'], r['sample_b']) for r in kept}
    pairs = [r for r in original['pairs'] if (r['sample_a'], r['sample_b']) in keys]
    if [{k: v for k, v in r.items() if k not in ('human_rating', 'human_mean_all_trials')} for r in pairs] != kept:
        raise ValueError('元評定と独立label選択の対応不一致')
    selection = {'id': 'asvspoof2019-availability100-20261014-v1', 'schema_version': 1,
        'pairs': pairs, 'identities': dict(sorted(identities.items())), 'pair_count': 80,
        'recording_count': 100, 'speaker_count': 27, 'b_anchor_count': 20,
        'selection_label_manifest_sha256': sha256(OUT / 'label-selection.json'),
        'original_selection_sha256': sha256(ORIGINAL / 'selection.json'),
        'source_csv_sha256': original['source_csv_sha256'], 'citations': original['citations'],
        'original_selection_rule': original['selection'], 'availability_selection': timing}
    freeze(OUT / 'selection.json', selection)
    specs, dependencies = [], [AVAILABILITY, ORIGINAL / 'selection.json', ORIGINAL / 'label-selection.json']
    for sample, speaker in sorted(identities.items()):
        path = ORIGINAL / 'audio-records' / (Path(sample).stem+'.json')
        row = read(path)
        spec = row['input']
        if (row['status'] != 'measured' or row['speaker'] != speaker or row['sample'] != sample
                or row.get('excerpt') is not False or spec['sample_rate'] != 16000
                or spec['speaker'] != speaker or spec['id'] != 'asvspoof2019_'+Path(sample).stem
                or sha256(spec['path']) != spec['sha256']):
            raise ValueError(f'取得済み全長原音の実SHA/metadata不一致: {sample}')
        specs.append(spec)
        dependencies.extend([path, Path(spec['path'])])
    receipt_paths = [RUN / 'checkpoints/asv-originals-000/remote-receipt.json']
    receipt_paths.extend(RUN / 'checkpoints' / f'human-original-inputs-{i:03d}' / 'remote-receipt.json'
                         for i in range(1, 8))
    receipt_paths.extend(RUN / 'checkpoints' / f'asv-partial104-additional-{i:03d}' /
                         'chunk-000/remote-receipt.json' for i in range(3))
    members = {}
    for path in receipt_paths:
        receipt = read(path)
        if receipt['status'] != 'fixed_version_readback_all_member_hashes_match':
            raise ValueError('原音既存private読戻し証跡が未成功')
        for member in receipt['files']:
            members[member['path']] = {'member': member, 'receipt_path': str(path),
                'receipt_sha256': sha256(path), 'library_file_id': receipt['library_file_id'],
                'file_id': receipt['file_id'], 'version': receipt['version']}
    references = []
    for spec in specs:
        relative = str(Path(spec['path']).relative_to(ROOT))
        reference = members[relative]
        if (reference['member']['sha256'] != spec['sha256']
                or reference['member']['bytes'] != Path(spec['path']).stat().st_size):
            raise ValueError('原音固定private memberのSHA/bytes不一致')
        references.append(reference)
    freeze(OUT / 'audio-preservation-references.json', {'scope': 'reference existing fixed originals only',
        'recordings': 100, 'references': references})
    dependencies.extend(receipt_paths)
    freeze(OUT / 'inputs.json', specs)
    for index in range(10):
        freeze(OUT / 'input-batches' / f'{index:02d}.json', specs[index*10:(index+1)*10])
    freeze(OUT / 'input-contract.json', {'role': 'human_ratings_only_availability_substudy',
        'recordings': 100, 'pairs': 80, 'speakers': 27, 'b_anchors': 20, 'full_length': True,
        'selection_sha256': sha256(OUT / 'selection.json'), 'inputs_sha256': sha256(OUT / 'inputs.json'),
        'plan_sha256': sha256(PLAN), 'availability_selection': timing,
        'original_audio_storage': 'references only; no duplicate acquisition or raw-audio preservation'})
    train_specs = read(RUN / 'corpora/readout-train/inputs.json')
    if len(train_specs) != 120 or len({r['speaker'] for r in train_specs}) != 40:
        raise ValueError('独立train120/40が不一致')
    train_sources = {}
    for method in METHODS:
        calibration, issues = load_train(method, train_specs)
        if issues:
            raise ValueError(f'既存train母統計未成功: {method}: {issues}')
        train_sources[method] = {'schema_sha256': calibration['schema_sha256'],
                                  'sources': calibration['sources']}
        dependencies.extend([TRAIN / 'schemas' / f'{method}.json', TRAIN / 'contracts' / f'{method}.json'])
        for spec in train_specs:
            folder = TRAIN / 'native' / method / spec['id']
            dependencies.extend([folder / 'features.json', folder / 'moments.npz'])
    dependencies.extend([*(ROOT / '.cache/references/prepared' / f'{method}.json' for method in METHODS if method not in ('hnm', 'world_harvest')),
        TRAIN / 'input-contract.json', TRAIN / 'calibration-cohort.json',
        RUN / 'corpora/readout-train/inputs.json', RUN / 'corpora/readout-train/manifest.json',
        RUN / 'inputs.json', RUN / 'preparation/runtime-env.sh'])
    freeze(OUT / 'train-dependencies.json', {'source': 'existing independent dev-clean120/40 moments only',
        'evaluation_frames_needed': False, 'methods': train_sources})
    freeze(OUT / 'dependency-sha256-v3.json', {str(p): sha256(p) for p in sorted(set(dependencies))})
    sources = source_receipt()
    sources.update({str(p.relative_to(ROOT)): sha256(p) for p in PACKAGE.iterdir()
                    if p.is_file() and p.suffix in ('.py', '.md', '.diff')})
    freeze(OUT / 'source-sha256-v3.json', sources)
    fixed = [OUT / name for name in ('selection.json', 'label-selection.json', 'inputs.json',
        'input-contract.json', 'train-dependencies.json', 'dependency-sha256-v3.json', 'source-sha256-v3.json',
        'audio-preservation-references.json')]
    fixed.extend(sorted((OUT / 'input-batches').glob('*.json')))
    freeze(OUT / 'preflight-freeze-v3.json', {'study_id': selection['id'], 'frozen_at_utc': read(OUT / 'preflight-freeze-v3.json')['frozen_at_utc'] if (OUT / 'preflight-freeze-v3.json').exists() else now(),
        'scope': 'input/source inventory; no feature inference or human agreement calculation',
        'methods': list(METHODS), 'counts': counts, 'fixed_files': {str(p): sha256(p) for p in fixed},
        'required_before_inference': ['independent static review', 'private fixed-version checkpoint readback',
                                      'parent release prioritizing main B/C']})
    print('preflight:', OUT / 'preflight-freeze-v3.json', sha256(OUT / 'preflight-freeze-v3.json'))


if __name__ == '__main__':
    main()
