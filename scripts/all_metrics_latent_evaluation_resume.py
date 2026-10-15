"""凍結評価式を保ち、旧ECAPA失敗行の対象波形を保存証跡から同定する。"""
from __future__ import annotations

import logging
from pathlib import Path
import traceback

from all_metrics_common import ROOT, RUN, freeze, read
from all_metrics_control_eval_equivalence import verified_record
import all_metrics_latent_evaluation as evaluation
from all_metrics_latent_evaluation_common import quality
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256


def quality_with_failure_evidence(spec, method, record):
    results = quality(spec, method, record)
    name = 'speaker_similarity'
    if results[name]['status'] != 'pending_quality':
        return results
    condition = record['condition']
    for folder in ('latent-speaker/measurements', 'speaker-full/measurements'):
        path = RUN / folder / f'{spec["id"]}__{method}__{condition}.json'
        if not path.exists():
            continue
        row = read(path)
        state = row.get('status', 'unavailable')
        if state == 'measured' or state.startswith('pending'):
            continue
        evidence = {'status': 'quality_failure_evidence_insufficient', 'value': None,
            'source_status': state, 'source_result': str(path), 'source_result_sha256': sha256(path),
            'source_record_at_attempt': row.get('source_record'),
            'source_record_sha256_at_attempt': row.get('source_record_sha256'),
            'reason': row.get('error', row.get('reason')),
            'operational_ingestion_contract_sha256': sha256(RUN / 'latent-evaluation/failure-ingestion-contract.json')}
        source = row.get('source_record')
        expected = row.get('source_record_sha256')
        if source and expected:
            try:
                proof = verified_record(source, expected, RUN / 'latent-evaluation/storage-equivalence')
                native = read(source)
                audio = native.get('audio', {})
                same = all(audio.get(k) == record['audio'][k]
                           for k in ('file_sha256', 'float64_sha256', 'sample_rate', 'samples'))
                if same:
                    evidence.update(status=state, target_identity=proof,
                        origin='existing_failure_same_wave_verified_by_saved_source_record',
                        identity_fields=['file_sha256', 'float64_sha256', 'sample_rate', 'samples'])
                else:
                    evidence['identity_problem'] = '保存されたsource記録の対象waveが現在の測定点と一致しません'
            except Exception as error:
                logging.exception('旧ECAPA失敗行の対象証跡を同定できません: %s', path)
                evidence['identity_problem'] = f'{type(error).__name__}: {error}'
                evidence['identity_traceback'] = traceback.format_exc()
        else:
            evidence['identity_problem'] = '失敗時点のsource_recordまたは保存SHAがありません'
        results[name] = evidence
        if evidence['status'] != 'quality_failure_evidence_insufficient':
            break
    return results


def main():
    paths = [Path(__file__), ROOT / 'scripts/all_metrics_control_eval_equivalence.py']
    freeze(RUN / 'latent-evaluation/failure-ingestion-contract.json', {
        'schema_version': 1, 'scientific_contract_sha256': sha256(RUN / 'latent-evaluation/contract.json'),
        'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        'scope': 'ECAPA失敗行にaudio_sha256がない場合だけ対象証拠を補足。科学評価式・波形・推論条件は不変。',
        'identity': '失敗行のsource_recordと保存SHAを検証。可逆JSON圧縮は旧原本exact SHAと復元構造一致を要求。対象wave file/PCM hashとrate/samples完全一致。',
        'unresolved': 'quality_failure_evidence_insufficient; missing quality is never zero',
        'original_failed_results_preserved': True,
        'original_scientific_source_preserved': True})
    evaluation.quality = quality_with_failure_evidence
    return evaluation.main()


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-evaluation-resume'))
