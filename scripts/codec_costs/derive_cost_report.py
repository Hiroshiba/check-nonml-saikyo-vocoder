"""Read saved measurements only; never import or execute codec/quality code."""
import argparse
import hashlib
import json
import logging
import math
import statistics
from collections import defaultdict
from pathlib import Path

CONDITIONS = {0: 'native', -3: 'pitch_minus3', 3: 'pitch_plus3'}


def read(path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def stats(values):
    return {'support': len(values), 'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None}


def valid(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


class Report:
    def __init__(self, cohort):
        self.duration = {c['id']: c['input']['excerpt_samples'] / c['input']['sample_rate'] for c in cohort['cases']}
        self.inputs = {c['id']: c['input']['sha256'] for c in cohort['cases']}
        self.observations = []
        self.states = []
        self.digests = set()
        self.plans = set()
        self.threads = {'candidate': None}

    def add(self, case, method, condition, category, metric, value, digest, unit='seconds'):
        if not valid(value):
            raise ValueError('Invalid observed scalar')
        self.digests.add(digest)
        self.observations.append({'case': case, 'method': method, 'condition': condition,
                                  'category': category, 'metric': metric, 'value': value,
                                  'unit': unit, 'input_duration_seconds': self.duration[case],
                                  'scientific_digest': digest})

    def output(self):
        groups = defaultdict(list)
        for row in self.observations:
            groups[tuple(row[k] for k in ('method', 'condition', 'category', 'metric', 'unit'))].append(row)
        summaries = []
        successful = {(r['method'], r['condition'], r['case']) for r in self.states
                      if r['status'] in ('ok', 'measured')}
        for key, rows in sorted(groups.items()):
            if len({r['case'] for r in rows}) != len(rows):
                raise ValueError('Duplicate measurement for a case; select one attempt explicitly')
            item = dict(zip(('method', 'condition', 'category', 'metric', 'unit'), key))
            item.update(planned_denominator=len(self.duration), measured_support=len(rows),
                        missing_or_failed=len(self.duration)-len(rows), values=stats([r['value'] for r in rows]))
            if key[1] != 'case':
                item['successful_condition_support'] = sum(
                    (key[0], key[1], r['case']) in successful for r in rows)
            else:
                item['successful_condition_support'] = None
            if key[-1] == 'seconds':
                item['rtf'] = stats([r['value']/r['input_duration_seconds'] for r in rows])
            if key[-1] == 'bytes':
                item['bytes_per_second'] = stats([r['value']/r['input_duration_seconds'] for r in rows])
                item['bits_per_second'] = stats([8*r['value']/r['input_duration_seconds'] for r in rows])
            summaries.append(item)
        coverage = []
        for method in sorted({r['method'] for r in self.states}):
            for condition in (('native',) if method == 'world_harvest' else CONDITIONS.values()):
                rows = [r for r in self.states if r['method'] == method and r['condition'] == condition]
                if len({r['case'] for r in rows}) != len(rows):
                    raise ValueError('Duplicate condition state')
                coverage.append({'method': method, 'condition': condition,
                                 'planned_denominator': len(self.duration),
                                 'successful_support': sum(r['status'] in ('ok', 'measured') for r in rows),
                                 'failed_or_other_terminal_support': sum(r['status'] not in ('ok', 'measured') for r in rows),
                                 'unobserved_support': len(self.duration)-len(rows)})
        return {'schema_version': 1, 'report_status': 'partial_derived_preparation_not_final',
                'planned_cases': len(self.duration), 'planned_conditions_per_method': {'candidate': 3*len(self.duration), 'pml': 3*len(self.duration), 'world_harvest': len(self.duration)},
                'duration_basis': 'full original encoded excerpt; not common quality window',
                'speed_ranking': None, 'codec_total_seconds': None,
                'shared_model_assets_bytes': None,
                'unknown': ['candidate isolated editor time', 'candidate isolated input/load/output I/O time',
                            'candidate unprofiled decode time', 'candidate pure whole analysis time',
                            'shared model asset byte inventory'],
                'thread_counts': self.threads,
                'candidate_thread_count_reported_by_operator': 1,
                'scientific_digests': sorted(self.digests), 'condition_states': self.states,
                'coverage': coverage, 'observations': self.observations, 'partial_summaries': summaries}


def candidate(report, root):
    """Use terminal chunk receipt binding; scalar projection is evidence, not original JSON."""
    seen = set()
    for receipt_path in sorted((root/'chunk-receipts').glob('*.json')):
        receipt, digest = read(receipt_path)
        if receipt.get('stage_id') != 'candidate-generation':
            continue
        if receipt.get('validation_state') != 'validated_end':
            continue
        report.digests.add(digest)
        report.plans.add(receipt['run_plan_sha256'])
        if len(report.plans) != 1:
            raise ValueError('Mixed candidate run plans')
        bindings = {}
        for row in receipt['rows']:
            case = row['case']
            if case not in report.duration:
                raise ValueError('Case outside frozen cohort')
            report.states.append({'case': case, 'method': 'candidate', 'condition': row['condition'],
                                  'status': row['status']})
            bindings[case] = row['case_receipt']['sha256']
        for case, expected in bindings.items():
            if case in seen:
                raise ValueError('Duplicate candidate case')
            seen.add(case)
            status, status_digest = read(root/'case-status'/f'{case}.json')
            if status_digest != expected or status['source_input_sha256'] != report.inputs[case]:
                raise ValueError('Candidate receipt/input binding mismatch')
            report.digests.add(status_digest)
            # Archive receipts establish original byte identities without unpacking payloads/audio.
            archive, archive_digest = read(root/status['archive']['receipt'])
            if archive_digest != status['archive']['receipt_sha256'] or not archive.get('verified'):
                raise ValueError('Archive receipt identity mismatch')
            archived = {f['path']: f for f in archive['files']}
            retained = {f['path']: f for f in status['retained_files']}
            for cost in status['costs']:
                path, source_digest = cost['sourcepath'], cost['sha256']
                identity = archived.get(path, retained.get(path))
                if identity is None or identity['sha256'] != source_digest:
                    raise ValueError('Cost source identity absent from lossless/retained receipt')
                # Do not claim fresh archive-byte verification; producer performed it.
                scalar = cost['scalar_costs']
                def add(category, metric, condition='case', unit='seconds', field=None):
                    value = scalar.get(field or metric)
                    if value is not None:
                        report.add(case, 'candidate', condition, category, metric, value, source_digest, unit)
                if path.endswith('/encoder-cost.json'):
                    for field in ('air_seconds', 'final_fit_seconds'):
                        add('analysis_components_with_instrumentation', field)
                    add('io', 'save_seconds')
                    add('pipeline_observation_not_codec_speed', 'total_seconds')
                    add('native_intermediate_payload', 'payload_bytes', unit='bytes')
                elif cost.get('cost_role') == 'q1_measurement_reference_only':
                    add('reference_diagnostic', 'direct_native_decode_seconds', field='seconds')
                elif path.endswith('/preparation.json'):
                    add('payload_preparation_with_io', 'preparation_seconds', field='seconds')
                    add('complete_formal_payload', 'payload_bytes', unit='bytes')
                elif '/outputs/' in path and path.endswith('/diagnostics.json'):
                    condition = CONDITIONS[scalar['semitone']]
                    add('decode_with_profile', 'render_seconds_including_profile', condition)
                    add('pipeline_observation_not_codec_speed', 'total_seconds', condition)
                elif '/parameters/' in path:
                    add('parameter_diagnostic_not_formal_edit', 'seconds', CONDITIONS[scalar['semitone']])
                elif path.endswith('/llsm/encode.json'):
                    for field, value in scalar.get('costs', {}).items():
                        category = 'initial_f0_io' if field in ('export_save_s', 'load_s') else 'initial_f0_components'
                        report.add(case, 'candidate', 'case', category, field, value, source_digest)


def references(report, summaries):
    for summary in summaries:
        data, digest = read(summary)
        receipt, receipt_digest = read(summary.parent/'receipt.json')
        contract, contract_digest = read(summary.parent/'contract.json')
        artifacts = {str(Path(a['path']).resolve()): a['sha256'] for a in receipt['artifacts']}
        if artifacts.get(str(summary.resolve())) != digest:
            raise ValueError('Reference summary differs from terminal receipt')
        if artifacts.get(str((summary.parent/'contract.json').resolve())) != contract_digest:
            raise ValueError('Reference contract differs from terminal receipt')
        if receipt['validation_state'] != 'validated_end' or receipt['run_plan_sha256'] not in report.plans:
            raise ValueError('Reference receipt is not terminal or belongs to another plan')
        if (receipt['method'] != contract['method'] or receipt['run_plan_sha256'] != contract['run_plan_sha256']
                or receipt['stage_id'] != contract['stage_id'] or receipt['chunk_id'] != contract['chunk_id']):
            raise ValueError('Reference contract identity mismatch')
        if receipt['frozen_digests'] != contract['frozen_digests']:
            raise ValueError('Reference frozen digest mismatch')
        report.digests.update((digest, receipt_digest, contract_digest))
        report.digests.update(receipt['frozen_digests'].values())
        report.threads[receipt['method']] = contract['threads']
        if len({c['case'] for c in data['cases']}) != len(data['cases']) or set(receipt['case_ids']) != {c['case'] for c in data['cases']}:
            raise ValueError('Reference case set mismatch')
        for case in data['cases']:
            cid, method = case['case'], case['method']
            if method != receipt['method'] or cid not in receipt['case_ids']:
                raise ValueError('Reference case/method outside receipt')
            if case['input_sha256'] != report.inputs[cid]:
                raise ValueError('Reference input mismatch')
            def costs(values, condition, reused=False):
                for field, value in values.items():
                    if field.startswith('analysis_'):
                        category = 'analysis'
                    elif field.startswith('decode_'):
                        category = 'decode'
                    elif field.startswith('editor_'):
                        category = 'edit'
                    elif 'load_' in field or 'save_' in field:
                        category = 'io'
                    else:
                        category = 'unclassified_observation'
                    report.add(cid, method, condition, category, ('previous_encode_' if reused else '')+field, value, digest)
            costs(case.get('costs', {}), 'case')
            costs(case.get('previous_encode_costs') or {}, 'case', reused=True)
            if (case.get('payload') or {}).get('bytes') is not None:
                report.add(cid, method, 'case', 'complete_formal_payload', 'payload_bytes', case['payload']['bytes'], digest, 'bytes')
            for row in case['rows']:
                allowed = ('native',) if method == 'world_harvest' else tuple(CONDITIONS.values())
                if row['case'] != cid or row['method'] != method or row['condition'] not in allowed:
                    raise ValueError('Reference row identity mismatch')
                report.states.append({'case': cid, 'method': method, 'condition': row['condition'],
                                      'status': row['status']})
                costs(row.get('costs', {}), row['condition'])
                if (row.get('edited_payload') or {}).get('bytes') is not None:
                    report.add(cid, method, row['condition'], 'complete_edited_payload', 'payload_bytes', row['edited_payload']['bytes'], digest, 'bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--reference-summary', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cohort, digest = read(args.candidate_root/'public-cohort.json')
    report = Report(cohort)
    report.digests.add(digest)
    candidate(report, args.candidate_root)
    references(report, args.reference_summary)
    # Exclusive creation prevents overwriting any existing scientific artifact.
    with args.output.open('x') as stream:
        json.dump(report.output(), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Derived cost report failed')
        raise
