"""固定JVS12録音・5候補の完了済み補助診断を公開用に表示する。"""
from pathlib import Path
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from noise_screen_report import LABELS, METRICS, metric, number, table  # noqa: E402
from vocoderbench.benchmark_io import read, sha, write  # noqa: E402
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli  # noqa: E402


def summarize(parts):
    result = {}
    for style, label in ((None, '全12録音'), ('normal', '通常4録音'),
                         ('whisper', 'ささやき4録音'), ('falsetto', '裏声4録音')):
        subset = [p for p in parts if style is None or p['case']['style'] == style]
        groups = {}
        for method in ('identity', 'hnm', 'A', 'B', 'C', 'D', 'E'):
            rows = [p['original'] if method == 'identity' else next(r for r in p['rows'] if r['method'] == method)
                    for p in subset]
            metrics = {}
            for key, _, higher in METRICS:
                values = ([r['mos']['value'] for r in rows] if key == 'mos' and method == 'identity'
                          else [] if method == 'identity' else [metric(r, key) for r in rows])
                valid = [v for v in values if v is not None]
                diffs = []
                if method != 'identity':
                    for p, value in zip(subset, values):
                        base = metric(next(r for r in p['rows'] if r['method'] == 'hnm'), key)
                        if value is not None and base is not None:
                            diffs.append(value - base)
                metrics[key] = {'mean': statistics.mean(valid) if valid else None, 'valid': len(valid),
                                'planned': len(subset), 'mean_difference': statistics.mean(diffs) if diffs else None,
                                'improved_recordings': sum(v > 0 if higher else v < 0 for v in diffs),
                                'paired_recordings': len(diffs)}
            seeds = [s for r in rows for s in r.get('seed_diagnostics', [])]
            peaks = [s['values']['output_peak'] for s in seeds]
            scale = [s['full_scale'] for s in seeds]
            total = sum(s['sample_count'] for s in scale)
            exceeded = sum(s['at_or_above_full_scale_samples'] for s in scale)
            groups[method] = {'metrics': metrics, 'peak': max(peaks) if peaks else None,
                              'exceeded_outputs': sum(v >= 1 for v in peaks), 'outputs': len(peaks),
                              'exceeded_samples': exceeded if scale else None,
                              'exceeded_fraction': exceeded / total if total else None,
                              'exceeded_seconds': exceeded / 24000 if scale else None}
        result[label] = {'recordings': len(subset), 'methods': groups}
    return result


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'runs/noise-screen-jvs12')
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/2026-10-12/noise-stability/results/jvs-run-001')
    args = parser.parse_args()
    data = read(args.input / 'results.json')
    parts = data['parts']
    manifest = read(ROOT / 'data/jvs_available_v1.json')
    ids = {e['id'] for e in manifest['entries']}
    if (data['status'] != 'completed' or data['failures'] or len(parts) != 12 or
            {p['case']['id'] for p in parts} != ids or
            data['contract']['manifest_sha256'] != sha(ROOT / 'data/jvs_available_v1.json')):
        raise ValueError('固定JVS12録音の完了済み結果ではありません')
    for p in parts:
        if p['original']['mos']['status'] != 'measured' or len(p['rows']) != 6:
            raise ValueError('原音MOSまたは6方式の測定が不足')
        if {r['method'] for r in p['rows']} != {'hnm', 'A', 'B', 'C', 'D', 'E'}:
            raise ValueError('方式が不一致')
        for r in p['rows']:
            if (r['status'] != 'measured' or len(r['seed_diagnostics']) != 8 or
                    {s['seed'] for s in r['seed_diagnostics']} != set(range(8)) or
                    any(metric(r, k) is None for k, _, _ in METRICS)):
                raise ValueError('欠測・seed不足の結果は完了扱いしません')
    groups = summarize(parts)
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ('results.json', 'contract.json', 'mos_provenance.json', 'execution.json'):
        shutil.copyfile(args.input / name, args.output / name)
    write(args.output / 'summary.json', {'groups': groups, 'role': 'auxiliary_12_not_formal_120',
                                        'public_audio': False, 'label_mapping': LABELS})
    write(args.output / 'publication.json', {'source_sha256': sha(args.input / 'results.json'),
          'generator_sha256': sha(Path(__file__)), 'metric_helper_sha256': sha(Path(__file__).with_name('noise_screen_report.py')),
          'planned_syntheses': 576, 'completed_syntheses': 576, 'planned_mos': 84, 'completed_mos': 84})
    whisper = groups['ささやき4録音']['methods']
    base_mos = whisper['hnm']['metrics']['mos']['mean']
    c_mos = whisper['C']['metrics']['mos']['mean']
    base_estoi = whisper['hnm']['metrics']['estoi']['mean']
    c_estoi = whisper['C']['metrics']['estoi']['mean']
    d_mos = whisper['D']['metrics']['mos']['mean']
    finding = (f'ささやき4録音で、Cの予測MOSは{c_mos:.5f}（v2 {base_mos:.5f}）、'
               f'eSTOIは{c_estoi:.5f}（v2 {base_estoi:.5f}）。'
               f'Dの予測MOSは{d_mos:.5f}。英語での改善を日本語ささやきへ一般化できない。')
    page = '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>雑音合成5案を日本語の通常・ささやき・裏声で確認</title><style>
:root{color-scheme:light dark;font:16px/1.75 system-ui,sans-serif}body{max-width:1200px;margin:auto;padding:24px}h1{font-size:1.8rem;line-height:1.35}h2{font-size:1.25rem;margin-top:2rem}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:8px;border-bottom:1px solid #8886;text-align:left;white-space:nowrap}th{background:#8882}a{color:light-dark(#1554ad,#91baff)}.notice{border-left:4px solid #d98616;padding:12px}</style>
<h1>雑音合成5案を日本語の通常・ささやき・裏声で確認</h1>
<p class="notice">固定JVS12録音・4話者の補助診断。正式な英語120録音と別集計。現在のHNM v2と5候補を576回合成、原音を含む84予測MOSを測定し、失敗0。</p>'''
    page += f'<p><strong>{finding}</strong></p>'
    page += '<p>音響指標は発話内8 seedを先に平均、予測MOS・eSTOIはseed 0。各群は発話を等重みで平均。各発声4録音だけなので一般的な優越・採用を判定しない。予測MOSは日本語・ささやき・裏声に対し未校正。原音の未測定指標は—と表示する。</p>'
    for label, group in groups.items():
        absolute, deltas, peaks = [], [], []
        for method, g in group['methods'].items():
            absolute.append([LABELS[method]] + ['—' if method == 'identity' and k != 'mos' else number(g['metrics'][k]['mean'])
                                              for k, _, _ in METRICS])
            if method not in ('identity', 'hnm'):
                deltas.append([LABELS[method]] + [number(g['metrics'][k]['mean_difference'], True) for k, _, _ in METRICS])
            if method != 'identity':
                peaks.append([LABELS[method], number(g['peak']), f"{g['exceeded_outputs']}/{g['outputs']}",
                              g['exceeded_samples'], number(g['exceeded_fraction']), number(g['exceeded_seconds'])])
        page += f'<h2>{label}：方式ごとの値</h2>' + table(['方式'] + [t for _, t, _ in METRICS], absolute)
        page += '<details><summary>v2との差と振幅上限</summary><p>差は候補−v2。MOS・eSTOIは正、誤差は負が改善。</p>'
        page += table(['方式'] + [t for _, t, _ in METRICS], deltas)
        page += table(['方式', '最大振幅', '振幅1以上／全seed出力', '超過標本', '超過標本率', '超過秒数'], peaks) + '</details>'
    rows = []
    for p in parts:
        if p['case']['style'] != 'whisper':
            continue
        base = next(r for r in p['rows'] if r['method'] == 'hnm')
        for r in p['rows']:
            if r['method'] in ('C', 'D'):
                rows.append([p['case']['speaker'], LABELS[r['method']], number(metric(r, 'mos')),
                             number(metric(r, 'mos') - metric(base, 'mos'), True), number(metric(r, 'estoi')),
                             number(metric(r, 'estoi') - metric(base, 'estoi'), True)])
    page += '<h2>ささやきの各録音：CとDの変化</h2>' + table(['話者', '方式', '予測MOS', 'MOS差', 'eSTOI', 'eSTOI差'], rows)
    page += '''<h2>解釈と記録</h2><p>通常・ささやき・裏声で文は同一とは限らず、発声差の因果効果とは扱わない。全12件でも独立話者は4人。seedやフレームを独立話者として数えない。振幅超過は聴感上の音割れを直接測ったものではない。日本語原音・加工音は公開しない。WORLDはこの補助再測定に含めず、過去比較を今回の実行へ混ぜない。</p>
<p>自動MOSはUTMOSv2の固定コード・重み・抽出seedで実施。この補助はCPU1スレッド。正式英語比較のMOSは別の実行条件記録を参照し、スレッド数の違いを同一条件と表現しない。採用条件や正式120件の分母を補助結果に合わせて変更しない。</p>
<p><a href="results.json">全測定JSON</a> · <a href="summary.json">発声別集計</a> · <a href="contract.json">条件</a> · <a href="mos_provenance.json">MOSの由来</a> · <a href="../run-001/index.html">正式英語120録音の比較</a> · <a href="../whisper-run-001/index.html">旧v1との複数seed診断</a> · <a href="../../reviews/jvs-five-findings.md">判断メモ</a></p></html>'''
    (args.output / 'index.html').write_text(page, encoding='utf-8')
    notes = ['# 日本語12録音での雑音合成5案の補助比較', '',
             '[結果HTML](../results/jvs-run-001/index.html) / [数値](../results/jvs-run-001/results.json)', '',
             '通常・ささやき・裏声を各4録音、4話者。576合成・84予測MOS、失敗0。正式英語120録音とは別集計。', '',
             finding, '', '## 発声別の数値', '']
    for label, group in groups.items():
        notes += [f'### {label}', '', '| 方式 | 予測MOS | eSTOI | 10 ms包絡誤差 |', '|---|---:|---:|---:|']
        for method, g in group['methods'].items():
            notes.append('| ' + ' | '.join([LABELS[method]] + [number(g['metrics'][k]['mean']) for k in ('mos', 'estoi', 'envelope')]) + ' |')
        notes.append('')
    notes += ['## 判断', '',
              '英語の探索的な改善を、そのまま日本語・ささやき・裏声の保証にしない。Cのささやき予測MOS/eSTOI低下を制約として残す。DのささやきMOS上昇も4録音の未校正予測なので総合優越とは扱わない。方式採用は別途、多指標・制御性・正式条件と併読する。', '',
              '音響指標は発話内8 seedを先に平均し、その後発話を平均。MOS/eSTOIはseed 0。原音はMOSのみ掲載し、他指標は未測定。4話者の12録音を12独立話者とは扱わず、seedを標本数へ加えない。発声間の文の違いもあり、発声のみの因果効果を分離できない。', '',
              '日本語原音・加工音は非公開。WORLDの新規合成はこの補助実行に含まない。以前のWORLD補助結果を同じ今回の実行に混ぜない。', '',
              'MOSはこの補助実行でCPU1スレッド。正式英語比較のMOSに別途CPU4スレッドの実行記録がある場合、計算条件の相違を明記する。品質処理やモデル重み・抽出seedの変更と、CPU実行設定の変更を区別する。', '',
              f"完了UTC：{data['finished_at']}。元結果SHA-256：{sha(args.input / 'results.json')}。完全な条件・モデル由来・各seed測定はJSONに保存した。"]
    review = args.output.parents[1] / 'reviews/jvs-five-findings.md'
    review.write_text('\n'.join(notes) + '\n', encoding='utf-8')
    print(finding)
    print(args.output)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'noise-jvs-report'))
