"""検証済みstage rawから固定軸へ展開。途中値・自由文を公開値へ混ぜない。"""
import math
from pathlib import Path

from .axis_registry import legacy, specs, validate_registry
from .chunk_checkpoint import checked
from .chunk_contracts import ContractError, freeze, read, sha, validate_plan
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def project(raw, spec):
    _, extract, _ = legacy()
    status, reason, value = raw['status'], raw.get('reason_code', 'metric_failed'), raw.get('value')
    detail = {}
    if spec['metric'] == 'acoustic':
        value, state, detail = extract(raw, spec)
        if state in ('measured', 'ok') and finite(value):
            status, reason = 'measured', 'none'
        elif status == 'measured':
            status, reason = 'not_applicable', 'insufficient_voiced_support' if 'pitch' in spec['id'] else 'outside_scope'
    elif spec['metric'] == 'pitch_missing':
        part = raw.get('detail', {})
        num, den = part.get('missing_voiced_frames'), part.get('expected_voiced_frames')
        if status in ('measured', 'not_applicable') and finite(num) and finite(den) and den > 0:
            value, status, reason, detail = num/den, 'measured', 'none', {'numerator': num, 'denominator': den}
        else:
            value = None
    elif spec['metric'].startswith('asr_') and status in ('measured', 'partial'):
        measure = raw.get('measurement', {})
        score = measure.get('scores', {}).get(spec['metric'][4:], {})
        if measure.get('reference_usable') is True and score.get('status') == 'ok' and finite(score.get('delta')):
            value, status, reason = score['delta'], 'measured', 'none'
        else:
            value, status, reason = None, 'reference_cer_gate_exceeded', 'reference_cer_gate_exceeded'
    if status == 'measured' and not finite(value):
        status, reason, value = 'not_applicable', 'outside_scope', None
    if status != 'measured':
        value = None
    allowed = {'none', 'generation_failed', 'metric_failed', 'model_initialization_failed',
               'unsupported_operation', 'outside_scope', 'full_transcript_unavailable',
               'reference_cer_gate_exceeded', 'insufficient_voiced_support', 'no_low_energy_segment',
               'length_mismatch', 'output_shorter_than_fixed_window', 'invalid_f0',
               'diagnostic_failed', 'other_classified_failure'}
    if reason not in allowed:
        reason = 'unsupported_operation' if status == 'unsupported' else 'generation_failed' if status == 'upstream_failed' else 'other_classified_failure'
    row = {'case': raw['case'], 'method': raw['method'], 'condition': spec['condition'],
           'axis': spec['id'], 'value': value, 'status': status, 'reason_code': reason}
    if (type(detail.get('numerator')) is int and type(detail.get('denominator')) is int
            and 0 <= detail['numerator'] <= detail['denominator']):
        row.update(support_numerator=detail['numerator'], support_denominator=detail['denominator'])
    return row


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--chunk', required=True)
    parser.add_argument('--receipts', type=Path, required=True, help='stage ID -> {path,sha256}のprivate JSON')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signature = sha(args.plan)
    plan = validate_plan(read(args.plan))
    validate_registry(plan)
    chunk = {r['id']: r for r in plan['chunks']}[args.chunk]
    mapping = read(args.receipts)
    if set(mapping) != set(plan['required_stage_receipts']):
        raise ContractError('必要な全stageのreceiptを指定してください')
    stages, evidence = {}, [(args.plan, signature), (args.receipts, sha(args.receipts))]
    for name, item in mapping.items():
        path = checked(args.receipts.parent/item['path'], item['sha256'])
        evidence.append((path, item['sha256']))
        receipt = read(path)
        if (receipt.get('schema_version') != 2 or receipt.get('stage_id') != name
                or receipt.get('validation_state') != 'validated_end'
                or receipt.get('run_plan_sha256') != signature or receipt.get('chunk_id') != args.chunk
                or receipt.get('case_ids') != chunk['case_ids']
                or receipt.get('frozen_digests') != plan['frozen_digests']):
            raise ContractError('stage終端の結合条件が一致しません')
        artifacts = {str((path.parent/a['path']).resolve()): a['sha256'] for a in receipt['artifacts']}
        for artifact, digest in artifacts.items():
            checked(artifact, digest)
            evidence.append((artifact, digest))
        if name.endswith('-generation'):
            continue
        summary = path.parent/'summary.json'
        checked(summary, artifacts[str(summary.resolve())])
        raw = read(summary)['rows']
        index = {}
        for row in raw:
            key = (row['case'], row['method'], row['condition'])
            if key in index:
                raise ContractError('stage raw行が重複しています')
            record = path.parent/'measurements'/('__'.join((row['case'], row['method'], row['condition'], row['metric']))+'.json')
            checked(record, artifacts[str(record.resolve())])
            if read(record) != row:
                raise ContractError('個票とstage summaryが一致しません')
            index[key] = row
        stages[name] = index
    rows = []
    for spec in specs(plan['methods']):
        for case in chunk['case_ids']:
            for method in spec['methods']:
                key = (case, method, spec['condition'])
                if key not in stages[spec['stage']]:
                    raise ContractError('予定軸のraw行がありません')
                rows.append(project(stages[spec['stage']][key], spec))
    for path, digest in evidence:
        checked(path, digest)
    args.output.mkdir(parents=True, exist_ok=True)
    row_path = args.output/'axis-rows.json'
    freeze(row_path, {'rows': rows})
    stage_paths = {name: {'path': str((args.receipts.parent/item['path']).resolve()), 'sha256': item['sha256']}
                   for name, item in mapping.items()}
    freeze(args.output/'receipt.json', {'schema_version': 2, 'validation_state': 'validated_end',
           'run_plan_sha256': signature, 'chunk_id': args.chunk, 'case_ids': chunk['case_ids'],
           'frozen_digests': plan['frozen_digests'], 'stage_receipts': stage_paths,
           'rows_path': row_path.name, 'rows_sha256': sha(row_path)})


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-axis-rows'))
