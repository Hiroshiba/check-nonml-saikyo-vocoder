"""事後追加の量子化共通窓を固定し、許可済み正式batchだけを逐次保存する。"""
from __future__ import annotations

import argparse
from collections import Counter
import logging
from pathlib import Path
import time
import traceback

from common_windows import (BASE, CONDITIONS, METHODS, ROOT, RUN, SOURCE,
    batch_gate, case_group, compact_record, evidence, read, source_record)
from summarize_windows import render, result_path, summarize, validate_result_sources
from all_metrics_common import freeze, now
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import environment, sha256, write_json

DEPENDENCIES = ['scripts/all_metrics_common.py', 'scripts/all_metrics_controls.py',
    'scripts/all_metrics_latent_evaluation_common.py', 'scripts/all_metrics_latent_provenance.py',
    'scripts/all_metrics_rankings_core.py', 'vocoderbench/assessment/acoustics.py',
    'vocoderbench/assessment/common.py', 'vocoderbench/assessment/controls.py',
    'vocoderbench/quality_core.py', 'vocoderbench/metrics.py', 'vocoderbench/logging_utils.py']


def source_hashes():
    paths = [*SOURCE.glob('*.py'), SOURCE / 'plan.md', SOURCE / 'protocol.json',
             *(ROOT / p for p in DEPENDENCIES)]
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(paths)}


def freeze_contract(review):
    if (BASE / 'contract.json').exists():
        raise FileExistsError('固定済み契約は上書きしません')
    decision = read(review)
    if decision.get('approved_for_contract_freeze') is not True:
        raise ValueError('独立reviewの固定許可がありません')
    actual = source_hashes()
    if decision.get('reviewed_source_sha256') != actual:
        raise ValueError('独立review対象と現source一式が一致しません')
    protocol = read(SOURCE / 'protocol.json')
    contract = {**protocol, 'execution_status': 'fixed_before_first_supplement_value',
        'fixed_at_utc': now(), 'independent_review': evidence(review),
        'source_sha256': actual, 'environment': environment(),
        'input_contract': evidence(RUN / 'input-contract.json'), 'input_manifest': evidence(RUN / 'inputs.json'),
        'source_contracts': [evidence(RUN / f'synthesis-contracts/{m}.json') for m in METHODS] +
            [evidence(RUN / f'latent-contracts/{m}/quantization.json') for m in METHODS]}
    freeze(BASE / 'contract.json', contract)
    for source, digest in actual.items():
        path = ROOT / source
        destination = BASE / 'source-snapshot' / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        if sha256(destination) != digest:
            raise ValueError('source保存hash不一致')
    freeze(BASE / 'adoption.json', {'at_utc': now(), 'post_hoc': True,
        'reason': protocol['reason'], 'contract': evidence(BASE / 'contract.json'),
        'first_supplement_value_computed': False, 'independent_review': evidence(review)})
    return sha256(BASE / 'contract.json')


def checked_contract():
    path = BASE / 'contract.json'
    data = read(path)
    if data['source_sha256'] != source_hashes():
        raise ValueError('固定sourceと現source不一致。元結果を残し、新版rootを別途定義してください')
    for item in [data['input_contract'], data['input_manifest'], *data['source_contracts']]:
        if sha256(item['path']) != item['sha256']:
            raise ValueError(f'固定input/元科学契約が変化しました: {item["path"]}')
    return sha256(path)


def authorization(path, signature, batch=None, conditional=False):
    value = read(path)
    if value.get('approved_for_formal_measurement') is not True or value.get('contract_sha256') != signature:
        raise ValueError('この固定契約の正式実行許可がありません')
    if batch is not None and batch not in value.get('approved_batches', []):
        raise ValueError('このbatchの正式実行許可がありません')
    if conditional and value.get('approved_conditional') is not True:
        raise ValueError('成功方式固定後の条件付き補助群実行許可がありません')
    return evidence(path)


def source_case(spec, condition):
    return {method: {'native': source_record(spec, method, 'unedited'),
                     'point': source_record(spec, method, condition)} for method in METHODS}


def case_failure(spec, condition, group, members, error, records):
    rows = []
    for method in METHODS:
        row = {'case': spec['id'], 'speaker': spec['speaker'], 'method': method,
            'condition': condition, 'group_id': group, 'status': 'failed_evidence_or_transform',
            'value': None, 'error': error, 'reason': '正式補助処理の例外。未到着や科学的NAへ置換しない。'}
        if records:
            row['source_records'] = {s: compact_record(r) for s, r in records[method].items()}
            row['upstream_statuses'] = {s: r['status'] for s, r in records[method].items()}
        rows.append(row)
    return {'case': spec['id'], 'speaker': spec['speaker'], 'condition': condition,
        'group_id': group, 'members': list(members), 'rows': rows,
        'common_window': {'status': 'failed_evidence_or_transform', 'value': None, 'error': error}}


def measure_batch(batch, signature, permission, conditional=False):
    gate = batch_gate(batch)
    if gate['status'] != 'terminal':
        raise ValueError(f'正式batch gateが未完: {gate}')
    specs = read(RUN / f'input-batches/{batch:02d}.json')
    fixed_specs = read(RUN / 'inputs.json')
    if len(specs) != 10 or specs != fixed_specs[batch * 10:(batch + 1) * 10]:
        raise ValueError('batch入力が固定全120manifestの予定sliceと完全一致しません')
    batch_manifest = evidence(RUN / f'input-batches/{batch:02d}.json')
    group = 'successful-methods' if conditional else 'all-eight'
    receipts = []
    for condition in CONDITIONS:
        members = list(METHODS)
        selection = None
        if conditional:
            selection = read(BASE / 'membership' / f'{condition}.json')
            if selection['contract_sha256'] != signature:
                raise ValueError('条件付き集合の固定契約不一致')
            members = selection['members']
            if members == list(METHODS):
                receipts.append({'condition': condition, 'status': 'same_as_primary', 'new_measurements': 0})
                continue
        for spec in specs:
            path = result_path(group, condition, spec['id'])
            records = None
            if path.exists():
                prior = read(path)
                if prior['contract_sha256'] != signature or prior['batch_gate']['sha256'] != gate['sha256']:
                    raise ValueError('保存済み補助測定の契約または終端gateが不一致です')
                if prior.get('batch_manifest') != batch_manifest:
                    raise ValueError('保存済みbatch manifestが変化しています')
                validate_result_sources(prior)
                receipts.append({'status': 'resumed_without_recomputation', **evidence(path)})
                continue
            started = now()
            try:
                records = source_case(spec, condition)
                result = case_group(spec, records, condition, members, group)
            except Exception:
                logging.exception('共通窓補助の正式case失敗: %s %s', spec['id'], condition)
                result = case_failure(spec, condition, group, members, traceback.format_exc(), records)
            result.update(contract_sha256=signature, started_at_utc=started, finished_at_utc=now(),
                batch=batch, batch_manifest=batch_manifest, batch_gate=gate, authorization=permission, selection=selection,
                original_input=spec, scientific_retries=0)
            freeze(path, result)
            receipts.append({'status': 'new_formal_result', **evidence(path)})
    receipt = {'batch': batch, 'group': group, 'contract_sha256': signature, 'at_utc': now(),
        'authorization': permission, 'gate': gate, 'batch_manifest': batch_manifest, 'results': receipts,
        'new_synthesis_or_inference': False, 'prior_primary_modified': False}
    freeze(BASE / 'execution' / f'batch-{batch:02d}-{group}-{time.time_ns()}.json', receipt)
    return receipt


def select_members(signature):
    gates = [batch_gate(b) for b in range(12)]
    if any(g['status'] != 'terminal' for g in gates):
        raise ValueError('全120×8予定point終端前には成功方式集合を固定しません')
    specs = read(RUN / 'inputs.json')
    for condition in CONDITIONS:
        path = BASE / 'membership' / f'{condition}.json'
        states, sources = {m: Counter() for m in METHODS}, []
        for spec in specs:
            for method in METHODS:
                row = source_record(spec, method, condition)
                states[method][row['status']] += 1
                sources.append(row['record_evidence'])
        members = [m for m in METHODS if states[m]['measured'] > 0]
        value = {'contract_sha256': signature, 'condition': condition,
            'members': members, 'excluded_methods': [m for m in METHODS if m not in members],
            'point_wave_status_counts': {m: dict(v) for m, v in states.items()},
            'planned_points': 960, 'all_planned_points_terminal': True,
            'selection': 'measured point waveform >=1; independent of auditory values',
            'excluded_reasons': {m: '全120予定pointの成功waveが0' for m in METHODS if m not in members},
            'source_records': sources, 'batch_gates': gates}
        if path.exists():
            prior = read(path)
            if any(prior.get(k) != v for k, v in value.items()):
                raise ValueError('固定済み成功方式集合または根拠が変化しました。再選別しません')
        else:
            freeze(path, {**value, 'fixed_at_utc': now()})


def save_summary(signature):
    folder = BASE / 'summaries' / str(time.time_ns())
    report = summarize(signature)
    report['generated_at_utc'] = now()
    freeze(folder / 'results.json', report)
    (folder / 'index.html').write_text(render(report), encoding='utf-8')
    inventory = [evidence(p) for p in (folder / 'results.json', folder / 'index.html')]
    freeze(folder / 'manifest.json', {'files': inventory, 'contract_sha256': signature})
    write_json(BASE / 'latest-summary.json', {'at_utc': now(), 'files': inventory,
        'manifest': evidence(folder / 'manifest.json')})
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'measure', 'select', 'summarize'))
    parser.add_argument('--review', type=Path)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--batch', type=int, choices=range(12))
    parser.add_argument('--conditional', action='store_true')
    args = parser.parse_args()
    if args.action == 'freeze':
        if args.review is None:
            parser.error('freezeには--reviewが必要です')
        print(freeze_contract(args.review))
        return 0
    signature = checked_contract()
    if args.action in ('measure', 'select'):
        if args.authorization is None:
            parser.error('正式測定/集合固定には--authorizationが必要です')
        permission = authorization(args.authorization, signature, args.batch, args.conditional or args.action == 'select')
        if args.action == 'select':
            select_members(signature)
        else:
            if args.batch is None:
                parser.error('measureには--batchが必要です')
            measure_batch(args.batch, signature, permission, args.conditional)
    print(save_summary(signature))
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'quantization-common-windows-formal'))
