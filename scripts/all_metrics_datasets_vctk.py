"""取得前に凍結した新規則から48 kHz VCTK7話者各18録音を選定する。"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from all_metrics_common import freeze, now, read
from all_metrics_datasets_contract import RULES, SPEAKERS, plan_path, require_plan
from all_metrics_datasets_remote import CACHE, OUT, ROOT, RemoteZip, save_json, sha
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256

SALT = RULES['vctk']['salt']


def reference_record(source, locator, speaker):
    path, metadata = source.member(locator)
    info = sf.info(path)
    wave, rate = sf.read(path, dtype='float64')
    excerpt = wave[:min(len(wave), rate * 10)]
    finite = bool(np.isfinite(wave).all())
    reasons = []
    if rate != 48000 or wave.ndim != 1 or info.subtype != 'PCM_16':
        reasons.append('not_mono_pcm16_48000')
    if not finite:
        reasons.append('nonfinite')
    source_power = float(np.mean(wave**2)) if finite and wave.size else 0.0
    excerpt_power = float(np.mean(excerpt**2)) if finite and excerpt.size else 0.0
    if min(source_power, excerpt_power) <= 0:
        reasons.append('zero_power')
    source_clip = float(np.mean(np.abs(wave) >= 1-1/32768)) if finite and wave.size else None
    excerpt_clip = float(np.mean(np.abs(excerpt) >= 1-1/32768)) if finite and excerpt.size else None
    if source_clip is not None and max(source_clip, excerpt_clip) > .001:
        reasons.append('clipping_fraction')
    if len(wave)/rate < 3:
        reasons.append('source_below_3_seconds')
    item = {'id': 'vctk_'+path.stem, 'speaker': speaker, 'corpus': 'VCTK-0.92',
        'language': 'en', 'style': 'normal', 'microphone': 'mic1', **metadata,
        'sample_rate': rate, 'source_samples': len(wave), 'source_duration_seconds': len(wave)/rate,
        'excerpt_start_sample': 0, 'excerpt_samples': len(excerpt),
        'excerpt_duration_seconds': len(excerpt)/rate,
        'source_float64_sha256': sha(wave.astype('<f8').tobytes()),
        'excerpt_float64_sha256': sha(excerpt.astype('<f8').tobytes()),
        'source_peak': float(np.max(np.abs(wave))) if finite and wave.size else None,
        'source_rms_dbfs': float(10*np.log10(source_power)) if source_power > 0 else None,
        'source_full_scale_fraction': source_clip, 'excerpt_full_scale_fraction': excerpt_clip,
        'golf_training_partition': 'test', 'exclusion_reasons': reasons}
    freeze(OUT / 'vctk-reference-records' / f'{item["id"]}.json', item)
    return item


def selection(source, speaker):
    candidates = sorted((e for e in source.entries if e['member'].endswith('_mic1.flac')
                         and Path(e['member']).parent.name == speaker),
        key=lambda e: (-e['uncompressed_bytes'], sha((SALT+e['member']).encode()), e['member']))
    if len({e['member'] for e in candidates}) != len(candidates):
        raise ValueError('VCTK archive内のmember名重複')
    freeze(OUT / 'vctk-candidate-order' / f'{speaker}.json', candidates)
    accepted, excluded = [], []
    for locator in candidates:
        item = reference_record(source, locator, speaker)
        if item['exclusion_reasons']:
            excluded.append(item)
        else:
            accepted.append(item)
        logging.info('VCTK reference: %s accepted=%d reasons=%s', item['id'], len(accepted), item['exclusion_reasons'])
        if len(accepted) == 18:
            break
    if len(accepted) != 18:
        raise RuntimeError(f'事前条件に適合する18録音が不足: {speaker}')
    for item in accepted:
        wave, rate = sf.read(ROOT / item['local_source'], dtype='float64')
        excerpt = wave[:item['excerpt_samples']]
        wav = CACHE / 'vctk/excerpts' / (item['id']+'.wav')
        wav.parent.mkdir(parents=True, exist_ok=True)
        if wav.exists():
            stored, stored_rate = sf.read(wav, dtype='float64')
            if stored_rate != rate or not np.array_equal(stored, excerpt):
                raise ValueError('保存済みVCTK抜粋が新固定入力と不一致')
        else:
            sf.write(wav, excerpt, rate, subtype='PCM_16')
        item['local_wav'], item['wav_sha256'] = str(wav.relative_to(ROOT)), sha256(wav)
    return accepted, excluded


def main():
    plan = require_plan('vctk')
    manifest_path = OUT / 'vctk126.json'
    if manifest_path.exists():
        if read(manifest_path)['selection_plan_sha256'] != sha256(plan_path('vctk')):
            raise ValueError('保存済みVCTK manifestと新規則が不一致')
        return 0
    source = RemoteZip('vctk')
    if read(source.index)['url'] != plan['rule']['archive_url']:
        raise ValueError('VCTK cached ZIP索引の配布元が不一致')
    freeze(OUT / 'vctk-acquisition-contract.json', {'schema_version': 1,
        'selection_plan_sha256': sha256(plan_path('vctk')), 'archive_index_sha256': sha256(source.index),
        'archive_url': source.url, 'archive_bytes': source.size, 'speakers': list(SPEAKERS)})
    rows, rejected = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for accepted, excluded in pool.map(lambda s: selection(source, s), SPEAKERS):
            rows.extend(accepted)
            rejected.extend(excluded)
            save_json(OUT / 'vctk-selection-progress.json', {'entries': rows, 'excluded': rejected})
    counts = Counter(e['speaker'] for e in rows)
    if (set(counts) != set(SPEAKERS) or set(counts.values()) != {18}
            or len({e['source_sha256'] for e in rows}) != 126 or len({e['id'] for e in rows}) != 126):
        raise ValueError('指定7話者各18独立録音が揃っていません')
    manifest = {'schema_version': 1, 'id': 'vctk48k126-recovery-v1', 'created_at_utc': now(),
        'implementation_origin': 'new_selection_not_old_manifest_reconstruction',
        'selection_rule': plan['rule'], 'selection_plan_sha256': sha256(plan_path('vctk')),
        'archive_index_sha256': sha256(source.index),
        'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'citation': 'Yamagishi, Veaux, and MacDonald (2019), CSTR VCTK Corpus, version 0.92, doi:10.7488/ds/2645',
        'sample_rate': 48000, 'microphone': 'mic1', 'entries': sorted(rows, key=lambda e: e['id']),
        'excluded': rejected, 'counts': {'recordings': len(rows), 'speakers': len(counts),
            'excerpts_below_8_seconds': sum(e['excerpt_duration_seconds'] < 8 for e in rows),
            'excerpts_at_least_8_seconds': sum(e['excerpt_duration_seconds'] >= 8 for e in rows)},
        'duration_scope': 'predeclared 3–10 seconds', 'normalization': 'none', 'silence_trimming': 'none',
        'source_files_preserved': True, 'training_overlap': plan['rule']['training_scope']}
    freeze(manifest_path, manifest)
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-vctk-selection'))
