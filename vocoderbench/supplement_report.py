"""日本語・発声別の補助診断を、正式120件と混ぜずに要約する。"""
from collections import defaultdict
from html import escape

from .benchmark_io import ROOT, read, write
from .benchmark_summary import METRICS, paired, summarize, value

STYLES = {'normal': '通常', 'whisper': 'ささやき', 'falsetto': '裏声'}
METRIC_LABELS = {
    'mos': '音声品質の予測MOS ↑', 'estoi': '言葉の明瞭さ eSTOI ↑',
    'envelope': '短時間の音量変化の誤差 ↓', 'stft': 'スペクトル誤差 dB ↓',
    'band': '帯域ごとの音量誤差 dB ↓', 'level': '全体の音量誤差 dB ↓',
    'modulation': '音量の揺れ方の誤差 dB ↓', 'pitch': '音高推定差 p95 cent ↓',
    'voicing_loss': '原音の有声推定が出力で失われた割合 ↓',
    'full_scale': '振幅1以上の標本割合 ↓',
}


def number(value, digits=4):
    return '測定なし' if value is None else f'{value:.{digits}f}'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(
        f'<th>{escape(str(c))}</th>' for c in headers) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{escape(str(c))}</td>' for c in row) + '</tr>' for row in rows
    ) + '</tbody></table></div>'


def build_summary(report):
    rows = report['resynthesis']
    refs = {r['case']: r for r in rows if r['method'] == 'hnm'}
    scopes = {'全体': rows, **{name: [r for r in rows if r['style'] == style] for style, name in STYLES.items()}}
    result = {}
    for scope, items in scopes.items():
        result[scope] = {}
        for method in ('hnm', 'candidate', 'world_harvest'):
            selected = [r for r in items if r['method'] == method]
            seed_records = [s for r in selected for s in r.get('seed_diagnostics', [])]
            peaks = [s['values']['output_peak'] for s in seed_records if s['status'] == 'measured']
            result[scope][method] = {
                'rows': len(selected), 'processing_success': sum(r['status'] == 'measured' for r in selected),
                'metrics': {key: {**summarize(selected, key, higher),
                                 'difference_from_base': paired(selected, refs, key)}
                            for key, _, higher in METRICS},
                'peaks': {'planned_seed_outputs': sum(len(r.get('planned_noise_seeds', [])) for r in selected),
                          'measured_seed_outputs': len(peaks), 'above_one_outputs': sum(p >= 1 for p in peaks),
                          'maximum': max(peaks) if peaks else None}}
    original_groups = defaultdict(list)
    style_by_case = {c['id']: STYLES[c['style']] for c in report['cases']}
    for row in report['calibration']:
        original_groups['全体'].append(row)
        original_groups[style_by_case[row['case']]].append(row)
    return {'schema_version': 1, 'study_role': report['study_role'], 'groups': result,
            'original_mos': {scope: summarize(items, 'mos', True) for scope, items in original_groups.items()},
            'interpretation': '日本語4話者・各発声4録音の補助診断。正式120録音とは別集計。'}


def parent_section(report):
    labels = report['method_labels']
    directory = ROOT / report['contract']['parent']['result_path']
    directory = directory.parent
    summary = read(directory / 'summary.json')['全体']
    rows = [[labels[method], *[number(summary[method]['metrics'][key]['mean'], 3)
                             for key in ('mos', 'estoi', 'envelope')]]
            for method in ('candidate', 'hnm', 'world_harvest')]
    result = '<h2>判断の中心となる英語120録音の比較</h2><p>親実験で測定済みの値です。日本語12録音はこの平均へ加えていません。</p>'
    result += table(['方式', '音声品質の予測MOS ↑', '言葉の明瞭さ eSTOI ↑', '短時間の音量変化の誤差 ↓'], rows)
    samples = read(directory / 'audio_samples.json')['samples']
    first_case = samples[0]['case']
    result += '<p>英語の公開済み音声例（各2秒・日本語JVSの例ではありません）</p><div class="audio-grid">'
    for sample in samples:
        if sample['case'] == first_case:
            result += f'<div><p>{escape(labels[sample["method"]])}</p><audio controls preload="none" src="{escape(sample["data_uri"])}"></audio></div>'
    return result + '</div>'


def decision_section(output):
    path = output / 'decision.json'
    if not path.exists():
        return ''
    decision = read(path)
    return '<aside>' + ''.join(f'<p>{escape(str(decision[key]))}</p>'
                               for key in ('title', 'reason', 'limitations') if decision.get(key)) + '</aside>'


def render(report, output):
    labels = report['method_labels']
    summary = build_summary(report)
    decision = decision_section(output)
    parent_comparison = parent_section(report)
    write(output / 'summary.json', summary)
    groups = summary['groups']
    overview = []
    for method in ('candidate', 'hnm', 'world_harvest'):
        row = groups['全体'][method]
        overview.append([labels[method], *[number(row['metrics'][key]['mean'], 3)
                                        for key in ('mos', 'estoi', 'envelope')]])
    overview.append(['原音（予測MOSの参照）', number(summary['original_mos']['全体']['mean'], 3), '—', '—'])
    main_table = table(['方式', '音声品質の予測MOS ↑', '言葉の明瞭さ eSTOI ↑', '短時間の音量変化の誤差 ↓'], overview)
    deltas = groups['全体']['candidate']['metrics']
    env = deltas['envelope']['difference_from_base']['mean_difference']
    baseline_env = groups['全体']['hnm']['metrics']['envelope']['mean']
    if env is not None and baseline_env:
        headline = f"短時間の音量変化の誤差はベース比で{abs(env / baseline_env * 100):.1f}%{'減少' if env < 0 else '増加'}。"
    else:
        headline = '短時間の音量変化の比較には欠測があります。'
    headline += f"予測MOSの平均差は{number(deltas['mos']['difference_from_base']['mean_difference'], 3)}です。"
    style_rows = []
    for style in STYLES.values():
        for method in ('candidate', 'hnm', 'world_harvest'):
            metrics = groups[style][method]['metrics']
            style_rows.append([style, labels[method], *[number(metrics[key]['mean'], 3)
                                                      for key in ('mos', 'estoi', 'envelope', 'pitch')]])
    style_table = table(['発声（各4録音）', '方式', '予測MOS ↑', 'eSTOI ↑', '音量変化の誤差 ↓', '音高推定差 cent ↓'], style_rows)
    detailed_rows = []
    for scope, methods in groups.items():
        for key, _, _ in METRICS:
            for method, row in methods.items():
                metric = row['metrics'][key]
                diff = metric['difference_from_base']
                ci = diff['speaker_bootstrap_95']
                detailed_rows.append([scope, labels[method], METRIC_LABELS[key], number(metric['mean']),
                    number(diff['mean_difference']), f"{number(ci[0])}〜{number(ci[1])}" if ci else '算出なし',
                    f"{metric['valid']}/{metric['total']}"])
    detail_table = table(['発声', '方式', '測定する性質', '平均', '当時のベースとの差', '差の95%区間', '測定できた録音／予定'], detailed_rows)
    case_rows = []
    for row in report['resynthesis']:
        peaks = [s['values']['output_peak'] for s in row.get('seed_diagnostics', []) if s['status'] == 'measured']
        case_rows.append([row['case'], STYLES[row['style']], labels[row['method']],
                          *[number(value(row, k)) for k in ('mos', 'estoi', 'envelope', 'pitch')],
                          number(max(peaks) if peaks else None), '完了' if row['status'] == 'measured' else '未完了・失敗'])
    case_table = table(['録音', '発声', '方式', '予測MOS', 'eSTOI', '音量変化誤差', '音高推定差 cent', '8回中最大振幅（WORLDは1回）', '処理'], case_rows)
    peak_rows = [[scope, labels[method], f"{row['peaks']['above_one_outputs']}/{row['peaks']['measured_seed_outputs']}",
                  number(row['peaks']['maximum'])] for scope, methods in groups.items() for method, row in methods.items()]
    peak_table = table(['発声', '方式', '振幅1以上になった出力／測定出力', '最大振幅'], peak_rows)
    issues = []
    for row in report['resynthesis'] + report['calibration']:
        if row.get('status') != 'measured':
            issues.append([row['case'], labels[row['method']], '処理', row.get('error', row['status'])])
        if row.get('mos', {}).get('status') != 'measured':
            issues.append([row['case'], labels[row['method']], '予測MOS', row.get('mos', {}).get('reason', '未完了')])
        extended = row.get('extended', {})
        estoi = (extended.get('intelligibility') or {}).get('estoi') or {}
        if estoi.get('status') != 'measured':
            issues.append([row['case'], labels[row['method']], '明瞭さ eSTOI', estoi.get('reason', '測定結果なし')])
        pitch = extended.get('pitch_consistency') or {}
        if pitch.get('absolute_difference_cents_p95') is None:
            if not pitch.get('reference_estimated_voiced_frames'):
                reason = '原音に有声と推定された区間がなく、音高差は評価不能'
            elif not pitch.get('both_estimated_voiced_frames'):
                reason = '原音と出力の両方で有声と推定された対応区間がなく、音高差は評価不能'
            else:
                reason = pitch.get('reason', '音高差の測定結果なし')
            issues.append([row['case'], labels[row['method']], '音高推定差', reason])
    issue_table = table(['録音', '方式', '測定', '理由'], issues) if issues else '<p>処理失敗・個別指標の評価不能はありません。</p>'
    parent = report['contract']['parent']['public_report']
    content = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>日本語の通常・ささやき・裏声：補助比較</title><style>
:root{{color-scheme:light dark;--bg:#f6f8fb;--surface:#fff;--ink:#172a3a;--line:#d8e2ea;--link:#126d8a}}
body{{background:var(--bg);color:var(--ink);font:16px/1.7 system-ui,sans-serif;margin:0}}main{{max-width:1150px;margin:auto;padding:32px 24px}}a{{color:var(--link)}}
table{{border-collapse:collapse;width:100%;background:var(--surface);font-size:14px}}td,th{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}td:first-child,th:first-child{{text-align:left}}
.scroll{{overflow:auto}}.audio-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}audio{{width:100%}}details{{padding:14px;border:1px solid var(--line);margin:16px 0;border-radius:8px}}summary{{cursor:pointer;font-weight:600}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1724;--surface:#182438;--ink:#e6edf4;--line:#3b4b60;--link:#7fdae8}}}}
</style><main><h1>日本語の通常・ささやき・裏声：補助比較</h1>
{decision}<p><strong>{escape(headline)}</strong></p>{main_table}
<p>日本語4話者・12録音の補助診断です。正式な英語120録音とは別集計で、各発声4録音だけの結果です。MOSは音声品質を推定する値、eSTOIは言葉の明瞭さに対応する指標で、高いほど良い方向です。音量変化の誤差は10 msごとの包絡のずれで、低いほど原音に近くなります。</p>
<p>JVSの原音・加工音は利用条件を踏まえて公開していません。<a href="{escape(parent)}">英語120録音の正式比較・公開済み音声例</a>を参照してください（日本語の音声例ではありません）。</p>
{parent_comparison}<h2>発声による違い</h2>{style_table}
<p>予測MOSは日本語・ささやき・裏声に対して未校正です。原音も含めた探索的な値で、発声様式の価値を採点するものではありません。原音の平均予測MOSは、{escape('、'.join(f'{name} {number(summary["original_mos"][name]["mean"], 3)}' for name in STYLES.values()))}でした。</p>
<details><summary>音量上限と局所的な振幅</summary>{peak_table}<p>浮動小数点の波形を保持しており、この測定で振幅を切り落としていません。振幅1以上は再生・整数音声への書出しで歪みにつながり得ますが、超過だけで聴感上の音割れが確定するわけではありません。8反復は8人の話者を意味しません。</p></details>
<details><summary>全指標と、ベースに対する変化の幅</summary>{detail_table}<p>差は候補またはWORLDから当時のベースHNM v1を引いた値です。区間は4話者単位の復元抽出2,000回による参考値で、広い日本語話者集団への保証ではありません。各発声の文は同一とは限らず、発声だけの因果効果は判断できません。</p></details>
<details><summary>12録音それぞれの結果</summary>{case_table}</details>
<details><summary>測定できなかった項目と理由</summary>{issue_table}</details>
<details><summary>条件・指標の読み方</summary><p>入力は24 kHz・先頭最大6秒。音量補正・時間位置の調整・無音除去は行いません。HNMと候補のスペクトル・帯域・音量・包絡・変調誤差は雑音seed 0〜7を録音内で平均し、その後に録音を等重みで平均します。WORLDは1回、MOS・eSTOI・音高・振幅1以上の標本割合はseed 0です。振幅1以上になった出力数と最大振幅の表は8seed全て（WORLDは1回）を使います。MOSの内部16 kHz変換とeSTOIの内部10 kHz変換は、符号化入力の変更とは別です。</p>
<p>音高には真値がなく、独立測定器による原音と出力の推定整合性です。ささやきでも測定器が周期性を推定する場合があり、生理的な有声の正解とはみなしません。centは音程差で100 centが1半音、p95はフレームごとの誤差の95パーセンタイルです。測定なしは0誤差ではありません。性別・転記は不明なため推測で埋めず、CER/WERは測定しません。</p></details>
<p>生成日時：<time datetime="{escape(report['generated_at'])}">{escape(report['generated_at'])}</time></p>
<p><a href="results.json">全数値</a> ／ <a href="summary.json">集計値</a> ／ <a href="contract.json">事前に固定した条件</a> ／ <a href="execution.json">実行記録</a></p></main></html>'''
    (output / 'index.html').write_text(content, encoding='utf-8')
    return summary
