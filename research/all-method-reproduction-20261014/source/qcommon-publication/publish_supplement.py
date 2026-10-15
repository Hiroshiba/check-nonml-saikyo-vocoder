"""全120終端後だけ、保存済み補助値をallowlistで公開表示へ接続する静的草案。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
from pathlib import Path

METHODS = ('hnm', 'world_harvest', 'facodec', 'hifiglot', 'golf', 'sifigan', 'llsm2', 'magphase')
CONDITIONS = ('quantized_float16', 'quantized_float32')
NAMES = dict(zip(METHODS, ('HNM v3（現base）', 'WORLD Harvest', 'FACodec v1', 'HiFi-Glot', 'GOLF-ff', 'SiFi-GAN', 'LLSM2 Layer0', 'MagPhase')))
STATUS_LABELS = {'measured': '実測', 'ok': '実測', 'analytic_identity': '厳密同一性による値',
    'upstream_failed': '上流失敗', 'failed': '測定失敗', 'failed_evidence_or_transform': '証跡・変換処理失敗',
    'not_applicable': '適用外', 'unsupported': '未対応', 'excluded_method': '固定補助集合の対象外'}
CONTRACT_SHA256 = 'dd0a439858c3a6864346712cbd3dbed05a550fd4da8c10f49706f478d948db6f'
NOTES = [
    '事後追加の独立補助です。元strict全長比較の値・適用外を置換しません。',
    '各精度で元入力と固定比較方式のnative＋point全波形を共通16 kHzへ変換し、同じ最短先頭窓を採用。最低1秒、各波形95%coverage。整列・伸縮・長さ合わせpaddingなし。',
    '40 ms Hann、5 ms間隔、32 ERB帯域の絶対power dB差。小さい方が同方式nativeに近い。20 ms ERB品質群・MOS・JNDとは別です。',
    '元nativeの対象fieldのdtype・座標・精度は方式で異なります。q32では完全恒等になる方式とfloat64からfloat32へ変化する方式が混在します。名目精度は全配列一律ではありません。',
    '同じSNR・摂動量・有効bit削減量を与えた比較ではありません。analytic_identityの0順位を、同じ大きさの摂動に対する耐性優位とは解釈しません。',
    '同一canonical decoder入力と実PCM証拠の差0はanalytic_identity。直接実測の0と別に数え、欠測/失敗を0に置換しません。',
    '成功方式条件付き群は全120×8point終端後に成功waveが1件以上ある方式全てを固定。共通数を増やす再選別なし。100録音未満は限定群です。',
    '話者内平均→話者等重み。既存seed20261014/2000話者bootstrapの記述95%区間、2話者未満CIなし、多重比較未調整。HNM差は同じ録音・同じ話者draw。',
    '#18は同じ聴覚結果を参照します。追加の独立指標や投票ではなく、payload bit/sは元入力秒数が分母。総合勝者・平均順位なし。',
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def bad(value):
        raise ValueError(f'非有限JSON値: {value}')
    return json.loads(Path(path).read_text(), parse_constant=bad)


def number(value):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
        raise ValueError('有限数またはnullが必要です')
    return value


def interval(values):
    if values is None:
        return None
    if not isinstance(values, list) or len(values) != 2:
        raise ValueError('95%区間は2値が必要です')
    return [number(x) for x in values]


def fixed_counts(data):
    allowed = {'measured', 'ok', 'analytic_identity', 'upstream_failed', 'failed',
        'failed_evidence_or_transform', 'not_applicable', 'unsupported', 'excluded_method'}
    if set(data) - allowed or any(type(v) is not int or v < 0 for v in data.values()):
        raise ValueError('未終端または未定義の状態件数です')
    return dict(data)


def selected_group(data, condition, members, expected):
    if data.get('terminal') is not True or data.get('comparable_methods') != list(members):
        raise ValueError('固定集合または終端状態が不一致です')
    if data.get('planned_recordings_per_method') != 120 or data.get('planned_speakers_per_method') != 40:
        raise ValueError('主120録音40話者の分母が必要です')
    rows = data['rows']
    ids = [(r['case'], r['method']) for r in rows]
    if len(rows) != 960 or len(set(ids)) != 960 or set(ids) != {(case, m) for case in expected for m in METHODS}:
        raise ValueError('全120×8状態が必要です')
    fixed_cases = set(expected)
    speakers = {}
    for row in rows:
        if row['speaker'] != expected[row['case']]:
            raise ValueError('固定input manifestとcase/speaker対応が一致しません')
        if row['case'] in speakers and speakers[row['case']] != row['speaker']:
            raise ValueError('同一録音の話者が方式間で一致しません')
        speakers[row['case']] = row['speaker']
    if len(fixed_cases) != 120 or len(set(speakers.values())) != 40:
        raise ValueError('120録音40話者の固定集合が必要です')
    valid = {m: set() for m in METHODS}
    for row in rows:
        value = number(row['value'])
        success = row['status'] in ('measured', 'ok', 'analytic_identity')
        if success and value is None or not success and value is not None:
            raise ValueError('statusと有限valueの対応が不正です')
        if success:
            valid[row['method']].add(row['case'])
    common = set.intersection(*(valid[m] for m in members)) if members else set()
    common_speakers = {expected[case] for case in common}
    if (data['common_valid_recordings'] != len(common) or data['common_valid_speakers'] != len(common_speakers)
            or data['limited_group'] != (len(common) < 100) or set(data['methods']) != set(members)):
        raise ValueError('保存rowsと共通録音/話者/方式の分母が一致しません')
    result = {k: data[k] for k in ('common_valid_recordings', 'common_valid_speakers', 'limited_group')}
    result.update(comparable_methods=list(members), excluded_methods=[m for m in METHODS if m not in members],
        planned_recordings_per_method=120, planned_speakers_per_method=40, terminal=True,
        unit='dB', direction='lower', methods={}, method_states={}, length_and_coverage={})
    for method in METHODS:
        local = [r for r in rows if r['method'] == method]
        if len(local) != 120 or {r['case'] for r in local} != fixed_cases or any(r['condition'] != condition for r in local):
            raise ValueError('精度別の予定rowが一致しません')
        actual = dict(Counter(r['status'] for r in local))
        state = data['method_states'][method]
        if state['status_counts'] != actual or state['planned_records'] != 120 or state['terminal'] is not True:
            raise ValueError('保存状態件数がrowと一致しません')
        direct = sum(r['status'] in ('measured', 'ok') and r['value'] is not None for r in local)
        identical = sum(r['status'] == 'analytic_identity' and r['value'] is not None for r in local)
        if state['direct_measured'] != direct or state['analytic_identity'] != identical or state['finite_values'] != direct + identical:
            raise ValueError('保存rowsと直接実測/厳密同一/有限値の件数が一致しません')
        direct_zero = sum(r['status'] in ('measured', 'ok') and r['value'] == 0 for r in local)
        canonical = Counter()
        for r in local:
            q = r.get('source_records', {}).get('point', {}).get('quantization') or {}
            flag = q.get('restored_decoder_input_identical')
            canonical['unchanged' if flag is True else 'changed' if flag is False else 'unavailable'] += 1
        result['method_states'][method] = {'status_counts': fixed_counts(actual),
            'direct_measured': state['direct_measured'], 'analytic_identity': state['analytic_identity'],
            'direct_measured_zero': direct_zero, 'canonical_input_identity_counts': dict(canonical),
            'upstream_wave_status_counts': {side: fixed_counts(data['upstream_wave_status_counts'][method][side]) for side in ('native', 'point')}}
        if method in members:
            value = data['methods'][method]
            delta = value['hnm_difference']
            if value['valid_recordings'] != len(common) or value['valid_speakers'] != len(common_speakers):
                raise ValueError('方式別有効数が同じ共通群の分母と一致しません')
            if not common and any(x is not None for x in (value['value'], value['rank'], value['ci95'], delta['value'], delta['ci95'])):
                raise ValueError('共通0では値/順位/区間/差はnullでなければなりません')
            if len(common_speakers) < 2 and (value['ci95'] is not None or delta['ci95'] is not None):
                raise ValueError('2話者未満のCIはありません')
            if 'hnm' not in members and (delta['value'] is not None or delta['ci95'] is not None):
                raise ValueError('HNM不在の群にpaired差があります')
            result['methods'][method] = {'value': number(value['value']), 'rank': number(value['rank']),
                'ci95': interval(value['ci95']), 'valid_recordings': value['valid_recordings'],
                'valid_speakers': value['valid_speakers'], 'hnm_difference': {'value': number(delta['value']), 'ci95': interval(delta['ci95'])}}
        diagnostic = data['length_and_coverage'][method]
        result['length_and_coverage'][method] = {
            k: number(diagnostic[k]) for k in ('signed_length_delta_seconds_min', 'signed_length_delta_seconds_max',
                'length_delta_observations', 'minimum_pair_coverage')}
        result['length_and_coverage'][method]['maximum_omitted_tail_seconds'] = {
            side: number(diagnostic['maximum_omitted_tail_seconds'][side]) for side in ('native', 'point')}
        result['length_and_coverage'][method]['strict_primary_auditory_status_counts'] = fixed_counts(diagnostic['strict_primary_auditory_status_counts'])
    return result


def public_result(raw, contract, source_digest, addendum_digest, specs):
    if raw.get('contract_sha256') != CONTRACT_SHA256 or raw.get('post_hoc') is not True:
        raise ValueError('承認済みv2契約と事後追加属性が必要です')
    if len(raw['groups']) != 2 or {g['condition'] for g in raw['groups']} != set(CONDITIONS):
        raise ValueError('両精度を省略せず表示してください')
    expected = {s['id']: s['speaker'] for s in specs}
    if len(specs) != 120 or len(expected) != 120 or len(set(expected.values())) != 40:
        raise ValueError('固定input manifestの120録音40話者が必要です')
    result = {'schema_version': 1, 'post_hoc': True, 'family_ids': [17, 18],
        'counts_as_additional_independent_metric': False, 'replaces_primary': False,
        'proposal_recorded_at_utc': contract['proposal_recorded_at_utc'], 'contract_fixed_at_utc': contract['fixed_at_utc'],
        'execution_revision': 2, 'v1_interruption': '値0件で計算前の時刻marker読取gate停止。運用修正後のv2を使用。',
        'contract_sha256': CONTRACT_SHA256, 'private_summary_content_sha256': source_digest,
        'interpretation_addendum_sha256': addendum_digest, 'notes': NOTES, 'groups': [], 'overall_winner': None}
    for item in raw['groups']:
        primary = selected_group(item['primary'], item['condition'], METHODS, expected)
        candidate = item['conditional']
        selection = candidate.get('selection', {})
        if selection.get('all_planned_points_terminal') is not True or selection.get('planned_points') != 960:
            raise ValueError('全120終端後の成功方式集合が未固定です')
        selected = [m for m in METHODS if selection['point_wave_status_counts'][m].get('measured', 0) > 0]
        if selected != selection['members'] or selection['contract_sha256'] != CONTRACT_SHA256:
            raise ValueError('wave成功状態だけの集合固定と一致しません')
        states = {m: fixed_counts(selection['point_wave_status_counts'][m]) for m in METHODS}
        if any(sum(v.values()) != 120 for v in states.values()) or any(states[m] != primary['method_states'][m]['upstream_wave_status_counts']['point'] for m in METHODS):
            raise ValueError('集合固定時の全方式120point状態がありません')
        if candidate.get('same_as_primary') is True:
            if selected != list(METHODS) or candidate.get('new_measurements') != 0:
                raise ValueError('全8と同一群の引用条件が不正です')
            conditional = {'same_as_primary': True, 'summary_reference': 'primary', 'new_measurements': 0}
        else:
            conditional = selected_group(candidate, item['condition'], selected, expected)
            conditional['same_as_primary'] = False
        conditional.update(selection_fixed_at_utc=selection['fixed_at_utc'],
            point_wave_status_counts=states, comparable_methods=selected,
            excluded_reasons={m: '全120予定pointの成功waveが0' for m in METHODS if m not in selected})
        result['groups'].append({'condition': item['condition'], 'primary': primary, 'conditional': conditional,
            'information_rate_auditory_reference': 'same condition primary/conditional values, not an independent metric'})
    return result


def render(report):
    def show(value):
        return '—' if value is None else f'{value:.6g}'
    def ci(value):
        return '—' if value is None else f'[{show(value[0])}, {show(value[1])}]'
    def counts(value):
        return ' / '.join(f'{STATUS_LABELS[k]} {v}' for k, v in value.items())
    def table(headers, rows):
        return '<div class="scroll"><table><tr>' + ''.join('<th>'+escape(x)+'</th>' for x in headers) + '</tr>' + ''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
    out = ['<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
        '<title>事後追加：量子化共通先頭区間の聴覚差</title><style>:root{color-scheme:light dark}body{max-width:90rem;margin:auto;padding:2rem;font:16px/1.65 system-ui}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #888;padding:.5rem;text-align:right}td:first-child,th:first-child{text-align:left}</style>',
        '<h1>事後追加：量子化共通先頭区間の聴覚差</h1>',
        '<p>HNMを含む全8方式固定の補助表を先に示します。元の厳格全長primaryは主レポートに保持しています。</p>',
        '<p>提案 '+escape(report['proposal_recorded_at_utc'])+' ／ 固定 '+escape(report['contract_fixed_at_utc'])+'</p>',
        '<p>'+escape(report['v1_interruption'])+'</p>',
        '<ul>'+''.join('<li>'+escape(n)+'</li>' for n in report['notes'])+'</ul>']
    for group in report['groups']:
        out.append('<h2>'+('float16保存点' if group['condition'] == CONDITIONS[0] else 'float32保存点')+'</h2>')
        for key, label in [('primary', '全8方式固定の補助'), ('conditional', '終端後の成功wave方式固定の補助')]:
            g = group[key]
            if g.get('same_as_primary'):
                out.append('<p>成功方式集合は全8と同一です。上の測定値を引用し、追加計算していません。</p>')
                continue
            out.append('<h3>'+label+'</h3><p>共通 '+str(g['common_valid_recordings'])+'/120録音、'+str(g['common_valid_speakers'])+'/40話者。'+('限定群（100録音未満）。' if g['limited_group'] else '')+'</p>')
            rows, lengths = [], []
            for m in METHODS:
                v = g['methods'].get(m, {})
                s = g['method_states'][m]
                d = g['length_and_coverage'][m]
                delta = v.get('hnm_difference', {})
                rows.append([NAMES[m], show(v.get('rank')), show(v.get('value')), ci(v.get('ci95')), show(delta.get('value')), ci(delta.get('ci95')),
                    s['direct_measured'], s['direct_measured_zero'], s['analytic_identity'], counts(s['status_counts'])])
                lengths.append([NAMES[m], show(d['signed_length_delta_seconds_min'])+' ～ '+show(d['signed_length_delta_seconds_max']),
                    show(d['minimum_pair_coverage']), show(d['maximum_omitted_tail_seconds']['native']), show(d['maximum_omitted_tail_seconds']['point']),
                    counts(d['strict_primary_auditory_status_counts'])])
            out.append(table(['方式','順位','話者平均 dB','95%区間','HNM差 dB','差の95%区間','直接実測','うち実測0','厳密同一の0','全120予定状態'],rows))
            out.append(table(['方式','point−native全長差 秒','両側の最小使用率','nativeの除外末尾最大 秒','量子化点の除外末尾最大 秒','元strict聴覚状態'],lengths))
            if g.get('excluded_methods'):
                out.append('<p>除外（全120予定pointの成功waveが0）：'+escape('、'.join(NAMES[m] for m in g['excluded_methods']))+'</p>')
    out.append('<p><a href="results.json">公開向け補助JSON</a> ／ <a href="../index.html">主18項目レポートへ</a></p></html>')
    return ''.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--expected-results-sha256', required=True)
    parser.add_argument('--interpretation-addendum', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('公開表示先は存在しない新directoryだけを使用します')
    if digest(args.results) != args.expected_results_sha256:
        raise ValueError('ownerが指定した完成snapshot SHAと一致しません')
    if digest(args.contract) != CONTRACT_SHA256 or CONTRACT_SHA256 not in args.interpretation_addendum.read_text():
        raise ValueError('契約またはmandatory解釈addendumが不一致です')
    contract = read(args.contract)
    if digest(args.inputs) != contract['input_manifest']['sha256']:
        raise ValueError('固定契約のinput manifest SHAと一致しません')
    report = public_result(read(args.results), contract, digest(args.results), digest(args.interpretation_addendum), read(args.inputs))
    report['generated_at_utc'] = datetime.now(timezone.utc).isoformat()
    # 既存値のallowlist転記だけ。raw/path/traceback/Library locatorを渡す経路は設けない。
    args.output.mkdir(parents=True)
    (args.output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    (args.output/'index.html').write_text(render(report), encoding='utf-8')
    manifest = {'contract_sha256': CONTRACT_SHA256, 'renderer_sha256': digest(__file__),
        'files': [{'name': name, 'sha256': digest(args.output/name), 'bytes': (args.output/name).stat().st_size} for name in ('results.json', 'index.html')],
        'scientific_values_recomputed': False, 'whole_18_study_completion_claim': False}
    (args.output/'artifact-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
