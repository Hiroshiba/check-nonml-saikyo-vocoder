"""固定済みViSQOL rawを集計し、非公開出典と公開準備済み日本語資料を分離する。"""
from __future__ import annotations

import argparse
from collections import Counter
import html
import json
from pathlib import Path

from all_metrics_common import METHODS, ROOT, RUN, now, read
from all_metrics_rankings_core import aggregate, pending
from all_metrics_vctk_summary import validate_row
from vocoderbench.quality_core import sha256, write_json

STUDY = RUN / 'vctk-availability16'
NAMES = {'hnm': 'HNM v3', 'world_harvest': 'WORLD（Harvest）', 'facodec': 'FACodec',
         'hifiglot': 'HiFi-Glot', 'golf': 'GOLF-ff', 'sifigan': 'SiFi-GAN',
         'llsm2': 'LLSM2 Layer 0', 'magphase': 'MagPhase'}
RATES = dict(zip(METHODS, (48000, 48000, 16000, 44100, 24000, 24000, 24000, 48000)))


def make_group(rows, inputs, recommended):
    specs = [s for s in inputs if not recommended or s['samples'] >= 8 * 48000]
    ids = {s['id'] for s in specs}
    selected = []
    for source in rows:
        if source['case'] not in ids:
            continue
        row = dict(source)
        if recommended and row['status'] == 'measured' and row['common_seconds'] < 8:
            row.update(origin_status='measured', status='not_applicable', value=None,
                       reason='共通区間8秒未満。上流失敗の状態は変更しない。')
        selected.append(row)
    group = aggregate({'id': 'visqol_audio_available16' + ('_8sec' if recommended else ''),
                       'methods': list(METHODS), 'direction': 'higher', 'rows': selected,
                       'planned_case_ids': sorted(ids), 'admissible_status': ['measured']})
    # The predeclared conditional display is only permitted after all128 terminal rows and primary0.
    all_terminal = len(rows) == 128 and all(not pending(r['status']) for r in rows)
    if not all_terminal or group['primary']['common_valid_recordings'] != 0:
        group['conditional'] = None
    return group


def public_cohort(cohort):
    if cohort is None:
        return None
    permitted = ('label', 'comparable_methods', 'excluded_methods', 'selection', 'same_as_primary',
                 'all_eight_methods', 'common_valid_recordings', 'common_valid_speakers',
                 'valid_bootstrap_replicates', 'requested_bootstrap_replicates', 'interval_limitation')
    value = {k: cohort[k] for k in permitted if k in cohort}
    value['methods'] = {m: {k: v for k, v in s.items() if k != 'speaker_means'}
                        for m, s in cohort['methods'].items()}
    return value


def public_group(group):
    return {k: group[k] for k in ('id', 'direction', 'terminal', 'method_states',
                                  'planned_recordings_per_method', 'planned_speakers_per_method',
                                  'bootstrap', 'aggregation')} | {
        'primary': public_cohort(group['primary']), 'conditional': public_cohort(group['conditional']),
        'available_case_auxiliary': {m: {k: v for k, v in s.items() if k != 'speaker_means'}
                                   for m, s in group['available_case_auxiliary'].items()}}


def fmt(value):
    return '欠測' if value is None else f'{value:.6f}'


def interval(value):
    return '算出不可' if value is None else f'[{value[0]:.6f}, {value[1]:.6f}]'


def cohort_html(cohort, title):
    if cohort is None:
        return ''
    rows = []
    for method, s in sorted(cohort['methods'].items(), key=lambda item: item[1]['rank'] or 99):
        d = s['hnm_difference']
        rows.append('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in
                    (s['rank'] if s['rank'] is not None else 'なし', NAMES[method], fmt(s['value']),
                     interval(s['ci95']), fmt(d['value']), interval(d['ci95']))) + '</tr>')
    return (f'<h3>{html.escape(title)}</h3><p>共通有効 {cohort["common_valid_recordings"]}録音 / '
            f'{cohort["common_valid_speakers"]}話者。各話者内平均の後、話者を等重みに集約。'
            'MOS-LQOは高い方が良い。</p><div class="scroll"><table><thead><tr>'
            '<th>順位</th><th>方式</th><th>話者等重み平均</th><th>記述的95%区間</th>'
            '<th>同一録音でのHNM差</th><th>差の記述的95%区間</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main18-status', choices=('incomplete', 'complete'), required=True)
    args = parser.parse_args()
    inputs, raw = read(STUDY / 'inputs.json'), read(STUDY / 'results.json')
    input_contract = read(STUDY / 'input-contract.json')
    quality_contract = read(STUDY / 'quality-contract.json')
    signature = sha256(STUDY / 'quality-contract.json')
    if (raw['input_contract_sha256'] != sha256(STUDY / 'input-contract.json')
            or raw['quality_contract_sha256'] != signature
            or quality_contract['input_contract_sha256'] != sha256(STUDY / 'input-contract.json')
            or quality_contract['inputs_sha256'] != sha256(STUDY / 'inputs.json')
            or quality_contract['planned_methods'] != list(METHODS)
            or quality_contract['planned_recordings'] != len(inputs)
            or quality_contract['planned_speakers'] != len({s['speaker'] for s in inputs})):
        raise ValueError('集計rawと固定入力・品質契約のSHA/件数不一致')
    indexed = {s['id']: s for s in inputs}
    rows = raw['rows']
    for row in rows:
        if row.get('case') not in indexed or row.get('method') not in METHODS:
            raise ValueError('集計rawの固定case/method不一致')
        validate_row(row, indexed[row['case']], row['method'], signature, input_contract)
        raw_path = STUDY / 'quality' / row['case'] / f'{row["method"]}.json'
        if row != read(raw_path):
            raise ValueError('集計rawと保存された品質行が不一致')
    if len(rows) != 128 or any(pending(r['status']) for r in rows):
        raise ValueError('128予定状態すべて終端後にのみ最終報告を作成します')
    full, long = make_group(rows, inputs, False), make_group(rows, inputs, True)
    private = {'generated_at_utc': now(), 'all16': full, 'recommended_duration': long,
               'results_sha256': sha256(STUDY / 'results.json'),
               'quality_contract_sha256': sha256(STUDY / 'quality-contract.json'),
               'source_sha256': {str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                                 'scripts/all_metrics_rankings_core.py': sha256(ROOT / 'scripts/all_metrics_rankings_core.py')}}
    write_json(STUDY / 'rankings-private.json', private)
    limitations = [
        '取得できた全16録音・4話者を性能測定前に固定した、利用可能性による限定補助比較です。正式126録音比較は未完了です。100録音以上という正式比較条件を満たしません。',
        '48 kHz入力のシステム比較です。各方式の本来の帯域制限を含み、16/24/44.1 kHz出力の変換を真の48 kHz高域再現能力とは呼びません。',
        'GOLFでは4話者とも公開test区分です。HiFi-GlotにはVCTKコーパスの学習重複があり、当該話者の学習有無は不明です。全方式で学習外の集合という保証はありません。',
        '公式ViSQOL Audio CLIと固定の学習済み48 kHz Audio SVRを使用。人の新規評定ではありません。初回値のみ集計し、CLIの反復を独立した評定として数えません。',
        '原音と全8方式の成功出力に共通する先頭区間を使用。3秒以上・各波形の95%以上が必要です。時間整列、時間伸縮、音量補正、振幅クリップは行いません。',
        'nativeピークまたはPCM16丸めが範囲外なら該当品質値を欠測とし、成功した合成波形と元の失敗状態を保持します。欠測を0点や最下位にしません。',
        '原音8秒以上は9録音、8秒未満は7録音です。推奨長の補助層は原音と共通区間の両方が8秒以上の場合だけです。',
        '4話者の2000回話者bootstrap（seed20261014）による95%区間は記述的です。母集団推論として精密とは言えず、多重比較補正はありません。',
        '全8主順位の共通有効数が0の場合のみ、128状態の終端後に有効値が1件以上ある全方式を固定した条件付き補助群を別掲します。得点や共通数の最大化では方式を選びません。HNMを含まなければHNM差は欠測です。',
        '単一指標から総合勝者や新ベース採用は決めません。主研究の18指標全体と混ぜず、VCTK原音・生成音声・生値の出典記録は非公開に保持します。']
    public = {'title': 'VCTK取得済み16録音による48 kHz入力ViSQOL Audio限定補助比較',
              'generated_at_utc': now(), 'main18_study_status': args.main18_status,
              'formal126_status': 'incomplete_unmeasured', 'below100_recordings': True,
              'metric': 'ViSQOL Audio', 'unit': 'MOS-LQO', 'direction': 'higher',
              'planned_recordings': 16, 'planned_speakers': 4, 'planned_rows': 128,
              'status_counts': dict(Counter(r['status'] for r in rows)),
              'native_sample_rates': RATES, 'all16': public_group(full),
              'recommended_duration': public_group(long), 'limitations': limitations,
              'publication_status': 'prepared_only; separate publication approval pending',
              'audio': 'private_only; no public VCTK clips'}
    out = STUDY / 'report'
    write_json(out / 'summary.json', public)
    title = public['title']
    state_text = '主研究18指標全体は未完了です。' if args.main18_status == 'incomplete' else '主研究18指標の状態とは別の補助比較です。'
    body = f'<h1>{title}</h1><p class="warning">正式126録音は未測定・未完了。100録音以上の条件を満たさない16録音・4話者の限定補助結果です。{state_text}</p>'
    body += '<h2>全8方式の比較を最初に</h2>' + cohort_html(public['all16']['primary'], '全16候補：全8方式共通の主比較')
    body += cohort_html(public['all16']['conditional'], '全16候補：終端後の成功方式固定による条件付き補助比較')
    body += '<h2>8秒以上の推奨長に限った補助層</h2>'
    body += cohort_html(public['recommended_duration']['primary'], '原音9候補かつ共通区間8秒以上：全8方式')
    body += cohort_html(public['recommended_duration']['conditional'], '8秒以上：条件付き補助比較')
    body += '<h2>方式ごとの全有効値と欠測</h2><p>方式別の対象が異なるため、この表には順位を付けません。</p><div class="scroll"><table><thead><tr><th>方式</th><th>native Hz</th><th>有効録音/16</th><th>有効話者/4</th><th>補助平均</th><th>状態</th></tr></thead><tbody>'
    for m in METHODS:
        s = public['all16']['available_case_auxiliary'][m]
        cells = (NAMES[m], RATES[m], s['valid_recordings'], s['valid_speakers'], fmt(s['value']),
                 json.dumps(public['all16']['method_states'][m]['status_counts'], ensure_ascii=False))
        body += '<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in cells) + '</tr>'
    body += '</tbody></table></div><h2>適用範囲と読み方</h2><ul>' + ''.join(f'<li>{html.escape(x)}</li>' for x in limitations) + '</ul>'
    body += '<p>集計JSON：<a href="summary.json">summary.json</a>。公開は未承認で、これは公開準備用の資料です。原音・合成音声は非公開です。</p>'
    document = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + title + '</title><style>body{color-scheme:light dark;font:16px/1.65 system-ui,sans-serif;max-width:1200px;margin:auto;padding:24px}h1{font-size:1.8rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #888;padding:8px;text-align:left}.scroll{overflow:auto}.warning{border:2px solid #b66;padding:16px}li{margin:.6em 0}a{color:#3a8cca}</style><body>' + body + '</body></html>'
    (out / 'index.html').write_text(document)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
