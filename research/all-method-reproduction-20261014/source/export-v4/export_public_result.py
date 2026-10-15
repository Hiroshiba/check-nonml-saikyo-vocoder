"""独立review・本番実行許可後だけ使う公開候補CLI。Git/Library/network操作なし。"""
from __future__ import annotations

import argparse
import gzip
import logging
from pathlib import Path
import warnings

from export_materialize import Payload, audio, quantization, raw_parts, source_inventory
from export_provenance import provenance
from export_report_schema import build_report
from export_sources import Sources, reviewed_reasons
from export_special_scalars import extra_records
from export_types import (MAX_BYTES, METHODS, digest, encoded, fail, file_entry,
                          loads, sha)
from public_renderer import render


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def arguments():
    parser = Parser(description=__doc__)
    parser.add_argument('--private-results', type=Path, required=True)
    parser.add_argument('--expected-private-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True, help='新規の公開候補directory')
    parser.add_argument('--private-output', type=Path, required=True, help='公開候補と交差しない新規私有directory')
    parser.add_argument('--licensed-audio', type=Path, required=True, help='既成14clip成果directory')
    parser.add_argument('--quantization-public', type=Path)
    parser.add_argument('--special-sources', type=Path, help='種類・path・完成SHA・件数を固定した私有manifest')
    parser.add_argument('--special-sources-sha256')
    parser.add_argument('--provenance-sources', type=Path, required=True, help='完成snapshotへ固定した私有来歴入力manifest')
    parser.add_argument('--provenance-sources-sha256', required=True)
    parser.add_argument('--reviewed-reasons', type=Path, help='理由本文SHAから独立review済み公開説明への対応')
    parser.add_argument('--reviewed-reasons-sha256')
    args = parser.parse_args()
    for path, expected in ((args.special_sources, args.special_sources_sha256),
                           (args.provenance_sources, args.provenance_sources_sha256),
                           (args.reviewed_reasons, args.reviewed_reasons_sha256)):
        if bool(path) != bool(expected):
            fail('arguments', '追加入力とowner固定SHAは対で指定')
        if expected:
            sha(expected, 'expected SHA')
    sha(args.expected_private_sha256, 'private SHA')
    output, private = args.output.resolve(), args.private_output.resolve()
    if output.exists() or private.exists() or output in private.parents or private in output.parents or output == private:
        fail('output', '非既存・非交差の公開候補/私有directoryが必要')
    return args


def validate_snapshot(report, sources):
    if report['schema_version'] != 1 or report['methods'] != list(METHODS):
        fail('report', '全8方式固定の最終schema1が必要')
    gate = report['final_gate']
    if report['terminal'] is not gate['terminal']:
        fail('report', '元global/final_gate terminalの不一致')
    coverage = report['coverage']
    if (coverage['family_count'], coverage['method_count'], coverage['cells']) != (18, 8, 144):
        fail('coverage', '18×8の保存coverageが必要')
    if [r['family'] for r in coverage['rows']] != list(range(1, 19)):
        fail('coverage', '18群が欠落または重複')
    if any(set(r['methods']) != set(METHODS) for r in coverage['rows']):
        fail('coverage', '全8方式の保存cellが必要')
    groups = report['groups']
    if len({g['id'] for g in groups}) != len(groups):
        fail('groups', '群ID重複')
    # 元ASV105/VCTK126の取得制限だけを未完として残す。主120未終端なら停止。
    historical_stages = {'vctk-native', 'vctk-quality', 'human-features', 'human-rankings'}
    for row in gate['rows']:
        if row['terminal']:
            continue
        original_group = row['stage'] == 'ranking-group' and row.get('group', '').startswith(('3.', '13.'))
        missing_manifest = False
        missing_paths = {'vctk': 'vctk-audio/inputs.json', 'human': 'human-similarity/inputs.json'}
        if (row['stage'] in missing_paths and row['status'] == 'pending_manifest'
                and row.get('unresolved_reason') == 'planned_manifest_absent'):
            ref = next((s for s in sources.records if s['source_id'] == row.get('path_source_id')), None)
            missing_manifest = bool(ref and ref['sha256'] is None and ref['private_path']
                                    and ref['private_path'].endswith('/' + missing_paths[row['stage']]))
        if row['stage'] not in historical_stages and not original_group and not missing_manifest:
            fail('main terminal', '主工程の未終端が残る。正式梱包は全main終端後')
    if report.get('overall_winner') is not None or report.get('average_rank') is not None:
        fail('report', '総合勝者・平均順位を追加しない')


def recording_records(report):
    records, receipts = [], []
    for group in report['groups']:
        for field, observation in [('rows', 'metric_recording'), ('reference_only_rows', 'original_mos_reference_only')]:
            if field not in group:
                continue
            rows = group.pop(field)
            start = len(records)
            records.extend({'kind': observation, 'group_id': group['id'], 'row': row} for row in rows)
            receipt = {'group_id': group['id'], 'field': field, 'observation_unit': observation,
                       'begin': start, 'end': len(records), 'record_count': len(rows),
                       'projected_rows_sha256': digest(encoded(rows))}
            receipts.append(receipt)
            group[field + '_export'] = receipt
    return records, receipts


def missing_evidence(private_report, special_missing):
    return [
        '公開候補は保存済みscalar・推定値・状態の証拠。全波形・全特徴・モデル・元評定CSVを含む再現archiveではない。',
        '来歴manifestは既知の保存JSONから明示転記。個別不足はprovenance-manifest.jsonのmissing_evidenceに列挙し、全hash完備を自動宣言しない。',
        '全方式の失敗原因の公開日本語説明は保存短理由またはreviewed-reasonsで明示する。未レビュー理由は私有証跡にある事実だけを表示。',
        '初期化は保存秒数・方式・要求条件を別記。完全recordの私有経路は非公開。速度から除外した保存値を保持し補正しない。',
        *(['元ASV105/VCTK126のfinal_gateは未完。全18成功・全18完了を主張しない。']
          if not private_report['terminal'] else []),
        *special_missing,
    ]


def main():
    args = arguments()
    args.private_output.mkdir(parents=True)
    handler = logging.FileHandler(args.private_output / 'export.log', encoding='utf-8')
    logging.getLogger().addHandler(handler)
    logging.captureWarnings(True)
    warnings.simplefilter('default')
    original = args.private_results.read_bytes()
    if digest(original) != args.expected_private_sha256:
        fail('private results', 'owner固定の完成snapshot SHAと不一致')
    private_report = loads(original)
    reasons = reviewed_reasons(args.reviewed_reasons, args.reviewed_reasons_sha256)
    sources = Sources(private_report, digest(original), reasons)
    exporter_sources = []
    for name in ('export_public_result.py', 'export_materialize.py', 'export_report_schema.py',
                 'export_science_schema.py', 'export_sources.py', 'export_special_scalars.py',
                 'export_binding.py', 'export_provenance.py', 'provenance_base.py',
                 'provenance_build.py', 'provenance_evaluators.py', 'provenance_scientific.py', 'provenance_links.py',
                 'export_types.py', 'public_renderer.py', 'export_render_constants.py'):
        path = Path(__file__).parent / name
        exporter_sources.append(sources.add(str(path), digest(path.read_bytes()), 'public_export_source'))
    schema, row_schema = build_report(sources.bind)
    report = schema(private_report, 'report')
    validate_snapshot(report, sources)
    records, receipts = recording_records(report)
    extra, extra_receipts, missing = extra_records(args.special_sources, args.special_sources_sha256, sources, row_schema)
    offset = len(records)
    for receipt in extra_receipts:
        receipt['begin'] += offset
        receipt['end'] += offset
    records.extend(extra)
    payload = Payload()
    lineage, lineage_missing = provenance(args.provenance_sources, args.provenance_sources_sha256, sources, private_report)
    payload.json('provenance-manifest.json', lineage)
    missing.extend(lineage_missing)
    samples = audio(payload, args.licensed_audio)
    missing.extend(quantization(payload, args.quantization_public, report.get('quantization_common_supplement', {})))
    parts = raw_parts(payload, records)
    parts.update(collections=receipts, dedicated_collections=extra_receipts,
                 scope='最終結果に存在する録音別行＋明示入力した専用scalar。全指標の全rawという意味ではない。')
    payload.json('raw-values-manifest.json', parts)
    report['public_scalar_artifacts'] = {'manifest': 'raw-values-manifest.json',
        'source_inventory_manifest': 'source-inventory-manifest.json',
        'private_results_sha256': digest(original), 'scientific_values_recomputed': False,
        'evidence_level': 'saved_scalar_projection_not_full_waveform_reproduction_archive'}
    payload.json('source-inventory-manifest.json', source_inventory(payload, sources.public()))
    payload.json('publication-limitations.json', {'limitations': missing_evidence(private_report, missing)})
    # gzipは保存名だけ変更。JSON内の値・順位・CI・範囲は同じ。
    summary = encoded(report)
    summary_name = 'results.json' if len(summary) <= MAX_BYTES else 'results.json.gz'
    payload.add(summary_name, summary if summary_name.endswith('.json') else gzip.compress(summary, mtime=0))
    html = render(report, samples)
    if summary_name != 'results.json':
        if html.count('href="results.json"') != 1:
            fail('renderer', 'summaryリンクの接続箇所が変化')
        html = html.replace('href="results.json"', 'href="results.json.gz"')
    payload.add('index.html', html.encode())
    payload.json('artifact-manifest.json', {
        'private_results_sha256': digest(original), 'terminal': private_report['terminal'],
        'scientific_values_recomputed': False, 'published': False,
        'summary': summary_name, 'per_file_limit_bytes': MAX_BYTES,
        'source_inventory_manifest': 'source-inventory-manifest.json',
        'exporter_source_ids': exporter_sources,
        'files': payload.entries(),
        'manifest_self_hash': '自己参照を避けるため、このmanifest自体のbytes/SHA/Git blob SHAは私有publication-candidatesに記録。',
    })
    # 全生成・サイズ/私有文字列検査が通ってから公開候補directoryを作る。
    args.output.mkdir(parents=True)
    payload.write(args.output)
    if args.private_results.read_bytes() != original:
        fail('private results', '入力snapshotが途中で変更された。公開不可')
    archive = gzip.compress(original, compresslevel=9, mtime=0)
    (args.private_output / 'private-results.json.gz').write_bytes(archive)
    (args.private_output / 'source-reverse-map.json').write_bytes(encoded(sources.private()))
    candidate = {'published': False, 'private_results_sha256': digest(original),
        'private_archive': file_entry('private-results.json.gz', archive),
        'public_candidates': payload.entries(), 'public_file_count': len(payload.files),
        'excluded_from_publication': ['private-results.json.gz', 'source-reverse-map.json',
                                     'publication-candidates.json', 'export.log'],
        'rows_transferred': len(records), 'scalar_manifest_sha256': digest(payload.files['raw-values-manifest.json'])}
    (args.private_output / 'publication-candidates.json').write_bytes(encoded(candidate))
    logging.info('公開候補保存完了。外部書込なし。元terminal=%s、候補%dファイル', report['terminal'], len(payload.files))
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        raise SystemExit(main())
    except Exception:
        logging.exception('公開候補梱包を中止。生成途中directoryは公開しないでください')
        raise SystemExit(1)
