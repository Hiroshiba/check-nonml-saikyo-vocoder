"""VCTK126 ViSQOL実測の全予定行・話者等重み順位・記述的区間を保存する。"""
from __future__ import annotations

from collections import Counter
from math import isfinite
from numbers import Real
from pathlib import Path

import numpy as np

from all_metrics_common import METHODS, now, read
from all_metrics_vctk_inputs import VCTK_RUN
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json


def finite_real(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def validate_row(row, spec, method, signature, input_contract):
    expected = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
                'metric': 'visqol_audio', 'contract_sha256': signature,
                'source_manifest_sha256': input_contract['source_manifest_sha256']}
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError(f"集計行の識別子または契約が不一致: {spec['id']}/{method}")
    if row.get('status') == 'measured':
        samples, seconds = row.get('common_samples'), row.get('common_seconds')
        if not finite_real(row.get('value')):
            raise ValueError(f"有限実数でない実測値: {spec['id']}/{method}")
        if (not isinstance(samples, int) or isinstance(samples, bool) or samples < 3 * 48000
                or samples > spec['samples'] or not finite_real(seconds)
                or seconds != samples / 48000):
            raise ValueError(f"実測共通区間の不一致: {spec['id']}/{method}")
    elif row.get('value') is not None:
        raise ValueError(f"未測定行に値が存在: {spec['id']}/{method}")


def speaker_summary(rows, shared_speakers=None):
    if any(not finite_real(r['value']) for r in rows):
        raise ValueError('話者集計に有限実数でない値が含まれます')
    speakers = sorted(shared_speakers or {r['speaker'] for r in rows})
    by_speaker = {s: [r['value'] for r in rows if r['speaker'] == s] for s in speakers}
    means = np.array([np.mean(by_speaker[s]) for s in speakers if by_speaker[s]])
    interval = None
    if len(means) >= 2:
        rng = np.random.default_rng(20261014)
        draws = rng.integers(0, len(means), (2000, len(means)))
        interval = np.quantile(means[draws].mean(axis=1), [.025, .975]).tolist()
    return {'speaker_equal_mean': float(np.mean(means)) if len(means) else None,
            'speaker_bootstrap_95_percentile_interval': interval, 'valid_recordings': len(rows),
            'bootstrap_iterations_requested': 2000,
            'bootstrap_iterations_executed': 2000 if len(means) >= 2 else 0,
            'interval_status': 'computed' if len(means) >= 2 else 'insufficient_valid_speakers',
            'valid_speakers': len(means), 'speaker_means': {
                s: float(np.mean(values)) for s, values in by_speaker.items() if values},
            'recording_equal_mean_auxiliary': float(np.mean([r['value'] for r in rows])) if rows else None}


def cohort_summary(rows, inputs, recommended=False):
    expected = {i['id'] for i in inputs if not recommended or i['samples'] / 48000 >= 8}
    valid = {m: {r['case'] for r in rows if r['method'] == m and r['status'] == 'measured'
                 and r['value'] is not None and (not recommended or r['common_seconds'] >= 8)} for m in METHODS}
    common = expected.intersection(*(valid[m] for m in METHODS))
    speakers = sorted({i['speaker'] for i in inputs if i['id'] in common})
    summaries = {}
    baseline = {r['case']: r for r in rows if r['method'] == 'hnm' and r['case'] in common}
    for method in METHODS:
        method_rows = [r for r in rows if r['method'] == method and r['case'] in common]
        summaries[method] = speaker_summary(method_rows, speakers)
        paired = [{**r, 'value': r['value'] - baseline[r['case']]['value']} for r in method_rows]
        summaries[method]['paired_difference_vs_hnm'] = speaker_summary(paired, speakers)
        summaries[method]['paired_difference_scope'] = '同じ共通録音の方式−HNM。話者内平均後、話者paired bootstrap。'
    ordered = sorted(METHODS, key=lambda m: -(summaries[m]['speaker_equal_mean']
        if summaries[m]['speaker_equal_mean'] is not None else -np.inf))
    anchor, anchor_rank = None, None
    for number, method in enumerate(ordered, 1):
        value = summaries[method]['speaker_equal_mean']
        tied = anchor is not None and value is not None and np.isclose(value, anchor, rtol=1e-9, atol=1e-12)
        rank = anchor_rank if tied else number
        summaries[method]['rank'] = rank if value is not None else None
        if not tied:
            anchor, anchor_rank = value, rank
    return {'planned_recordings': len(expected), 'planned_speakers': len({i['speaker'] for i in inputs if i['id'] in expected}),
            'common_valid_recordings': len(common), 'common_valid_speakers': len(speakers),
            'case_ids': sorted(common), 'methods': summaries,
            'scope': f'原音8秒以上{len(expected)}候補かつ共通区間8秒以上' if recommended else '固定126候補・全8同一区間の共通有効集合'}


def main():
    inputs = read(VCTK_RUN / 'inputs.json')
    input_contract = read(VCTK_RUN / 'input-contract.json')
    quality_contract = read(VCTK_RUN / 'quality-contract.json')
    signature = sha256(VCTK_RUN / 'quality-contract.json')
    if (quality_contract['input_contract_sha256'] != sha256(VCTK_RUN / 'input-contract.json')
            or quality_contract['inputs_sha256'] != sha256(VCTK_RUN / 'inputs.json')
            or quality_contract['planned_methods'] != list(METHODS)
            or len(inputs) != quality_contract['planned_recordings']
            or len({i['speaker'] for i in inputs}) != quality_contract['planned_speakers']
            or len({i['id'] for i in inputs}) != len(inputs)
            or any(i['sample_rate'] != 48000 for i in inputs)):
        raise ValueError('入力集合と品質測定契約が不一致')
    rows = []
    for spec in inputs:
        for method in METHODS:
            path = VCTK_RUN / 'quality' / spec['id'] / f'{method}.json'
            if path.exists():
                row = read(path)
                validate_row(row, spec, method, signature, input_contract)
            else:
                row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
                       'metric': 'visqol_audio', 'status': 'not_run', 'value': None,
                       'contract_sha256': signature,
                       'source_manifest_sha256': input_contract['source_manifest_sha256']}
            rows.append(row)
    raw = {'schema_version': 1, 'generated_at_utc': now(), 'rows': rows,
           'planned_rows': len(inputs) * len(METHODS), 'source_sha256': sha256(Path(__file__)),
           'input_contract_sha256': sha256(VCTK_RUN / 'input-contract.json'),
           'quality_contract_sha256': sha256(VCTK_RUN / 'quality-contract.json')}
    write_json(VCTK_RUN / 'results.json', raw)
    summary = {
        'schema_version': 1, 'metric': 'visqol_audio', 'unit': 'MOS-LQO', 'direction': 'higher',
        'generated_at_utc': now(), 'results_sha256': sha256(VCTK_RUN / 'results.json'),
        'status_counts': dict(Counter(r['status'] for r in rows)),
        'all8_common': cohort_summary(rows, inputs),
        'recommended_duration_auxiliary': cohort_summary(rows, inputs, recommended=True),
        'all_valid_per_method_auxiliary': {m: {
            **speaker_summary([r for r in rows if r['method'] == m and r['status'] == 'measured']),
            'status_counts': dict(Counter(r['status'] for r in rows if r['method'] == m))} for m in METHODS},
        'limitations': [
            '主LibriSpeech120群から独立したVCTK7話者126録音の48 kHz入力システム比較。',
            'HNM/WORLDは既存48 kHz構成。他の低帯域模型のupsampleを真の48 kHz対応と呼ばない。',
            'GOLFの既知train/validation話者との重複なし。HiFi-GlotはVCTK訓練コーパス重複あり当話者不明。',
            f'{sum(i["samples"]/i["sample_rate"] < 8 for i in inputs)}原音は8秒未満。'
            f'推奨8–10秒の補助層は{sum(i["samples"]/i["sample_rate"] >= 8 for i in inputs)}原音候補と同一条件の共通区間で限定。',
            '7話者のbootstrap区間は記述的。126録音を126独立話者や反復CLIを独立MOS評定として扱わない。',
            '合成失敗とPCM16範囲外を区別し、欠測を0点や最下位へ置換しない。',
            '順位の単純平均・総合勝者・新ベース採用は行わない。',
            'VCTK入力・生成・派生波形は公開しない。'],
        'bootstrap': {'unit': 'speaker', 'iterations_requested': 2000, 'seed': 20261014,
                      'interval': 'percentile 95%', 'multiple_comparison_adjustment': False}}
    write_json(VCTK_RUN / 'summary.json', summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-vctk-summary'))
