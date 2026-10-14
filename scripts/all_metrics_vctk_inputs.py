"""VCTK126の独立48 kHz補助研究入力を照合・固定する。動作確認用実行はしない。"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from all_metrics_common import METHODS, ROOT, RUN, audio_info, freeze, read, save_audio
from all_metrics_datasets_contract import SPEAKERS, plan_path, require_plan
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, sha256

VCTK_RUN = RUN / 'vctk-audio'
MANIFEST = RUN / 'corpora/vctk126.json'
NATIVE_RATES = dict(zip(METHODS, (48000, 48000, 16000, 44100, 24000, 24000, 24000, 48000)))


def pcm_hash(wave):
    return hashlib.sha256(np.asarray(wave, dtype='<f8').tobytes()).hexdigest()


def main():
    plan = require_plan('vctk')
    dataset = read(MANIFEST)
    if (dataset.get('schema_version') != 1 or dataset.get('selection_rule') != plan['rule']
            or dataset.get('selection_plan_sha256') != sha256(plan_path('vctk'))):
        raise ValueError('新VCTK manifestの選択規則/事前契約が不一致')
    manifest_hash = sha256(MANIFEST)
    entries = dataset['entries']
    counts = Counter(e['speaker'] for e in entries)
    if (len(entries) != 126 or set(counts) != set(SPEAKERS) or set(counts.values()) != {18}
            or len({e['id'] for e in entries}) != 126 or len({e['source_sha256'] for e in entries}) != 126):
        raise ValueError('7話者各18録音の126件が必要です')
    contract = {
        'schema_version': 1, 'study': 'VCTK126 independent ViSQOL Audio supplement',
        'source_manifest_path': str(MANIFEST), 'source_manifest_sha256': manifest_hash,
        'selection_plan_sha256': sha256(plan_path('vctk')), 'selection_rule': plan['rule'],
        'methods': list(METHODS), 'native_sample_rates': NATIVE_RATES,
        'hnm_world_scope': '既存encode/decodeの48 kHz構成。主120件の16 kHz構成とは独立。新方式ではない。',
        'comparison_scope': '48 kHz入力システム比較・帯域制約込み。低帯域出力のupsampleを真の48 kHz対応と呼ばない。',
        'source_sample_rate': 48000, 'planned_recordings': 126, 'planned_speakers': 7,
        'recordings_per_speaker': dict(counts), 'seed': 0, 'threads': 2,
        'source_preprocessing': '公式wav48_silence_trimmedのmic1。上流の事前無音除去あり。追加無音除去なし。',
        'excerpt_rule': '凍結manifestのstart/sample数。原録音の先頭最大10秒。追加cropなし。',
        'gain_normalization': False, 'source_quantization': 'official FLAC and preserved excerpt PCM16 WAV',
        'training_overlap': {
            'golf': '全7話者は公開test partition。既知train/validation話者との重複なし。',
            'hifiglot': 'VCTK訓練コーパスとの重複あり。当該7話者の訓練有無は不明。',
            'other_models': '当該話者の学習外保証なし。全方式held-out集合とは主張しない。'},
        'durations': {'minimum_seconds': 3.0, 'maximum_seconds': 10.0,
                      'below_8_seconds': sum(e['excerpt_samples']/e['sample_rate'] < 8 for e in entries),
                      'at_least_8_seconds': sum(e['excerpt_samples']/e['sample_rate'] >= 8 for e in entries),
                      'limitation': '公式推奨8–10秒を満たす実件数は別の補助層として記述。'},
        'comparison': {'sample_rate': 48000, 'minimum_common_seconds': 3.0,
                       'minimum_coverage_every_waveform': .95,
                       'length_rule': 'min(original and all eight successful native outputs derived at 48 kHz)',
                       'alignment': False, 'time_warp': False, 'normalization': False,
                       'amplitude_rule': 'native/derived peak>1またはround(32768*x) PCM16範囲超過は該当品質値null。clipなし。',
                       'cohort': '全8成功派生の共通先頭区間。全8順位は全8指標有効の同一録音集合。'},
        'formal_base': read(ROOT / 'BASELINE.json'),
        'license': dataset['license'], 'license_url': dataset['license_url'], 'citation': dataset['citation'],
        'publication': '入力・合成・派生波形はローカルのみ。VCTK波形はGit/公開物へ含めない。',
        'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                          'scripts/all_metrics_common.py': sha256(ROOT / 'scripts/all_metrics_common.py')},
    }
    freeze(VCTK_RUN / 'input-contract.json', contract)
    inputs = []
    for entry in entries:
        source, excerpt = ROOT / entry['local_source'], ROOT / entry['local_wav']
        if sha256(source) != entry['source_sha256'] or sha256(excerpt) != entry['wav_sha256']:
            raise ValueError(f'原FLAC/抜粋WAVのhash不一致: {entry["id"]}')
        original, source_sr = sf.read(source, dtype='float64')
        wave, sample_rate = sf.read(excerpt, dtype='float64')
        if source_sr != 48000 or sample_rate != 48000 or wave.ndim != 1 or original.ndim != 1:
            raise ValueError('VCTK元録音と抜粋は48 kHz monoが必要です')
        start, n = entry['excerpt_start_sample'], entry['excerpt_samples']
        if (len(original) != entry['source_samples'] or len(wave) != n
                or pcm_hash(original) != entry['source_float64_sha256']
                or pcm_hash(wave) != entry['excerpt_float64_sha256']
                or not np.array_equal(wave, original[start:start + n])):
            raise ValueError(f'元波形frame metadata/抜粋PCM64不一致: {entry["id"]}')
        if (start != 0 or n != min(len(original), 48000*10)
                or not 3 <= n / sample_rate <= 10 or not np.isfinite(wave).all()):
            raise ValueError('事前に固定した3–10秒・有限PCMの条件違反')
        path = VCTK_RUN / 'inputs' / f'{entry["id"]}.npy'
        info = audio_info(path, sample_rate) if path.exists() else save_audio(path, wave, sample_rate)
        if info['float64_sha256'] != entry['excerpt_float64_sha256']:
            raise ValueError('保存済みNPYのPCM64不一致')
        inputs.append({'id': entry['id'], 'speaker': entry['speaker'], 'path': str(path),
                       'sha256': info['file_sha256'], 'sample_rate': sample_rate, 'samples': n,
                       'audio': info, 'source_flac_sha256': entry['source_sha256'],
                       'excerpt_wav_sha256': entry['wav_sha256'], 'metadata': entry})
    freeze(VCTK_RUN / 'inputs.json', inputs)
    for offset in range(0, len(inputs), 10):
        freeze(VCTK_RUN / 'input-batches' / f'{offset // 10:02d}.json', inputs[offset:offset + 10])
    freeze(VCTK_RUN / 'input-environment.json', environment())
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-vctk-inputs'))
