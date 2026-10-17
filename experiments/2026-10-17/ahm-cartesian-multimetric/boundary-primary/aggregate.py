"""Reproduce descriptive statistics from six saved summaries; no inference."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import platform

import numpy as np

METHODS = ('boundary_hold', 'original_candidate', 'pml')
METRICS = ('utmosv2', 'speaker_ecapa')
CONDITIONS = (0, -3, 3)
SEED, REPLICATES = 20261017, 2000
LABELS = {'boundary_hold': '修正版', 'original_candidate': '元候補', 'pml': 'PML',
          'utmosv2': '自動MOS（UTMOSv2）', 'speaker_ecapa': '話者類似度（ECAPA）'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def paired(rows, metric, condition, cases, other):
    left = rows[metric, 'boundary_hold', condition]
    right = rows[metric, other, condition]
    speakers = sorted({left[c]['speaker'] for c in cases})
    groups = {s: [] for s in speakers}
    for c in cases:
        assert left[c]['speaker'] == right[c]['speaker']
        groups[left[c]['speaker']].append(left[c]['value'] - right[c]['value'])
    sums = np.array([sum(groups[s]) for s in speakers], dtype=np.float64)
    counts = np.array([len(groups[s]) for s in speakers], dtype=np.int64)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(speakers), size=(REPLICATES, len(speakers)))
    samples = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    interval = np.quantile(samples, [0.025, 0.975], method='linear')
    return {'contrast': 'boundary_hold-minus-' + other,
            'recording_count': len(cases), 'speaker_count': len(speakers),
            'cases': cases, 'speakers': speakers,
            'case_speakers': {c: left[c]['speaker'] for c in cases},
            'mean_paired_difference': float(np.mean([left[c]['value'] - right[c]['value'] for c in cases])),
            'descriptive_95_percent_interval': [float(x) for x in interval]}


def aggregate(rows, metric, condition, methods, expected_count):
    sets = [{c for c, r in rows[metric, m, condition].items() if r['status'] == 'measured'} for m in methods]
    cases = sorted(set.intersection(*sets))
    assert len(cases) == expected_count, (metric, condition, len(cases))
    means = {m: float(np.mean([rows[metric, m, condition][c]['value'] for c in cases])) for m in methods}
    contrasts = [paired(rows, metric, condition, cases, m) for m in methods if m != 'boundary_hold']
    return {'metric': metric, 'semitones': condition, 'recording_count': len(cases),
            'speaker_count': contrasts[0]['speaker_count'], 'cases': cases,
            'recording_equal_weight_means': means, 'paired_differences': contrasts}


def table(groups, methods):
    out = ['<div class="scroll"><table><thead><tr><th>指標</th><th>音高変更<br>半音</th><th>録音／話者</th>']
    out.extend('<th>' + LABELS[m] + '<br>平均</th>' for m in methods)
    out.extend('<th>修正版 − ' + LABELS[m] + '<br>対応差［記述的95%区間］</th>' for m in methods if m != 'boundary_hold')
    out.append('</tr></thead><tbody>')
    for g in groups:
        out.append(f"<tr><th>{LABELS[g['metric']]}</th><td>{g['semitones']:+d}</td><td>{g['recording_count']}／{g['speaker_count']}</td>")
        out.extend(f"<td>{g['recording_equal_weight_means'][m]:.6f}</td>" for m in methods)
        for d in g['paired_differences']:
            lo, hi = d['descriptive_95_percent_interval']
            out.append(f"<td>{d['mean_paired_difference']:+.6f}<br><small>［{lo:+.6f}, {hi:+.6f}］</small></td>")
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def render(data):
    status_rows = ''.join(
        f"<tr><th>{LABELS[s['metric']]}</th><td>{LABELS[s['method']]}</td><td>{s['planned_rows']}</td>"
        f"<td>{s['states'].get('measured', 0)}</td><td>{s['states'].get('upstream_failed', 0)}</td>"
        f"<td>{s['states'].get('failed', 0)}</td><td>{s['states'].get('not_applicable', 0)}</td></tr>"
        for s in data['state_counts'])
    hashes = ''.join(f"<tr><th>{LABELS[x['metric']]}／{LABELS[x['method']]}</th><td><code>{html.escape(x['sha256'])}</code></td></tr>" for x in data['input_summaries'])
    return '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>境界保持修正版：同一ホストでの自動MOS・話者類似度の記述統計</title>
<style>:root{color-scheme:light dark;font-family:system-ui,sans-serif;line-height:1.6}body{max-width:1250px;margin:auto;padding:28px}h1{font-size:1.7rem}h2{margin-top:2rem}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:10px;border:1px solid #8886;text-align:right}th:first-child,td:first-child{text-align:left}thead{background:#8882}.scroll{overflow:auto}.note{padding:14px;border-left:4px solid #7289a3;background:#8881}small{white-space:nowrap}code{font-size:.8rem;overflow-wrap:anywhere}p{max-width:90ch}</style>
<body><h1>境界保持修正版：同一ホストでの主指標2種の記述統計</h1>
<p>修正版・元候補・PMLを同一ホストで再計算した保存済み6 summaryの後処理です。旧環境の数値は混在させていません。平均と対応差は録音を等重みとします。</p>
<h2>3方式の共通成功集合</h2><p>各指標の0、−3、＋3半音で、3方式すべて成功した117、117、115録音だけを比較します。差は修正版から比較方式を引いた値です。</p>''' + table(data['three_method_common_success'], METHODS) + '''
<h2>修正版とPML：全120録音の比較</h2><p>各指標・各条件の全120録音による別集計です。上の共通成功集合とは分母が異なり、表をまたいだ数値の混合はしません。</p>''' + table(data['boundary_vs_pml_all_120'], ('boundary_hold', 'pml')) + '''
<h2>全2160行の状態</h2><p>測定成功2138行、元の生成失敗22行、追加の測定失敗0行、適用外0行です。元候補の生成失敗は11条件で、2指標にそれぞれ11行として残っています。欠測を0に置換していません。</p>
<p>修正版は全120録音×3条件の360条件で波形が利用可能であり、両指標とも360行すべて測定成功しています。</p>
<div class="scroll"><table><thead><tr><th>指標</th><th>方式</th><th>予定</th><th>測定成功</th><th>元の生成失敗</th><th>測定失敗</th><th>適用外</th></tr></thead><tbody>''' + status_rows + '''</tbody></table></div>
<h2>区間の計算方法</h2><p>各比較の成功録音を話者でまとめ、観測された話者数と同じ数の話者を復元抽出します。選ばれた話者の全録音を、重複抽出された話者はその回数だけ含め、録音平均の対応差を計算します。話者平均を等重みにする計算ではありません。</p>
<p>2000回、seed=20261017、NumPy default_rngを各比較で同じseedに初期化し、話者ID・録音IDを昇順に固定しました。区間はquantileの0.025・0.975（線形補間）です。これは記述的な区間であり、有意性の判定は行いません。表示は小数6桁、保存JSONは丸め前の値です。</p>
<h2>解釈の範囲</h2><div class="note"><p>自動MOS（UTMOSv2）はモデルの推定値であり、人が聴いて付けたMOSではありません。ECAPAの話者類似度は代理指標で、音高変更そのものにも影響されます。</p><p>対象は主指標2種のみであり、全79軸の再測定、codec速度の測定、総合順位、採用判断を示すものではありません。</p></div>
<h2>入力の識別</h2><p>元summaryは変更していません。入力SHA-256と全case集合、話者対応、集計規約を同梱JSONに記録しています。音声・モデルはこのHTMLに含みません。</p><div class="scroll"><table><thead><tr><th>入力</th><th>SHA-256</th></tr></thead><tbody>''' + hashes + '</tbody></table></div></body></html>\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, inputs, state_counts, failures, case_speakers = {}, [], [], {}, {}
    for metric in METRICS:
        for method in METHODS:
            relative = Path(method) / metric / 'summary.json'
            path = args.input_root / relative
            summary = json.loads(path.read_text())
            assert summary['validation_state'] == 'validated_end' and summary['metric'] == metric and summary['method'] == method
            assert len(summary['rows']) == 360
            inputs.append({'metric': metric, 'method': method, 'relative_path': relative.as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size})
            states = Counter(r['status'] for r in summary['rows'])
            state_counts.append({'metric': metric, 'method': method, 'planned_rows': 360, 'states': dict(states)})
            failures[metric, method] = set()
            for condition in CONDITIONS:
                subset = [r for r in summary['rows'] if r['semitones'] == condition]
                indexed = {r['case']: r for r in subset}
                assert len(subset) == len(indexed) == 120
                for r in subset:
                    assert r['metric'] == metric and r['method'] == method
                    assert r['speaker'] == case_speakers.setdefault(r['case'], r['speaker'])
                    if r['status'] == 'measured':
                        assert isinstance(r['value'], (int, float)) and np.isfinite(r['value'])
                    else:
                        assert method == 'original_candidate' and r['status'] == 'upstream_failed' and r['value'] is None
                        failures[metric, method].add((r['case'], condition))
                rows[metric, method, condition] = indexed
    assert len(case_speakers) == 120
    assert failures['utmosv2', 'original_candidate'] == failures['speaker_ecapa', 'original_candidate']
    assert len(failures['utmosv2', 'original_candidate']) == 11
    totals = Counter()
    for item in state_counts:
        totals.update(item['states'])
    assert dict(totals) == {'measured': 2138, 'upstream_failed': 22}
    conventions = {'input': 'six saved matched-host summaries only; no model inference or waveform access',
                   'means': 'recording-equal-weight arithmetic mean; missing values never imputed',
                   'common_success': 'intersection of measured case IDs for all three methods within metric and semitone',
                   'all_120': 'separate boundary_hold versus pml success intersection with 120 cases',
                   'contrast': 'boundary_hold minus comparator, paired by case within metric and semitone',
                   'bootstrap': {'unit': 'speaker', 'replicates': REPLICATES, 'seed': SEED,
                                 'rng': 'numpy.random.default_rng; reset for each comparison',
                                 'ordering': 'case and speaker IDs sorted lexicographically',
                                 'draw': 'rng.integers(0, speaker_count, size=(2000, speaker_count))',
                                 'estimator': 'sum of selected cluster difference sums / sum of selected recording counts; all recordings included with cluster multiplicity',
                                 'interval': 'numpy.quantile(samples, [0.025, 0.975], method=linear); descriptive only'},
                   'python': platform.python_version(), 'numpy': np.__version__,
                   'rounding': 'JSON unrounded; HTML six decimals', 'adoption_or_significance_test': 'not performed'}
    result = {'schema': 'boundary-quality-descriptive-report-v1', 'input_summaries': inputs,
              'aggregation_conventions': conventions, 'state_counts': state_counts,
              'total_states': dict(totals), 'all_case_ids': sorted(case_speakers),
              'original_failed_conditions': [{'case': c, 'semitones': s} for c, s in sorted(failures['utmosv2', 'original_candidate'])],
              'three_method_common_success': [aggregate(rows, metric, s, METHODS, {0: 117, -3: 117, 3: 115}[s]) for metric in METRICS for s in CONDITIONS],
              'boundary_vs_pml_all_120': [aggregate(rows, metric, s, ('boundary_hold', 'pml'), 120) for metric in METRICS for s in CONDITIONS]}
    write_json(args.output_dir / 'statistics.json', result)
    write_json(args.output_dir / 'input-sha256.json', {'inputs': inputs})
    rendered = render(result)
    assert '/workspace/' not in rendered and '<audio' not in rendered and '<script' not in rendered
    (args.output_dir / 'report.html').write_text(rendered)
    for item in inputs:
        assert sha(args.input_root / item['relative_path']) == item['sha256']
    outputs = [{'file': n, 'sha256': sha(args.output_dir / n), 'bytes': (args.output_dir / n).stat().st_size}
               for n in ('aggregate.py', 'statistics.json', 'report.html', 'input-sha256.json')]
    write_json(args.output_dir / 'completion.json', {'validation_state': 'validated_end', 'input_summary_count': 6,
               'input_rows': 2160, 'total_states': dict(totals), 'bootstrap_comparison_count': 18,
               'input_summaries_unchanged': True, 'outputs': outputs,
               'reproduce': 'python -B aggregate.py --input-root INPUT_RESULTS_DIRECTORY --output-dir OUTPUT_DIRECTORY'})
    print(json.dumps({'validation_state': 'validated_end', 'comparisons': 18, 'states': dict(totals)}))


if __name__ == '__main__':
    main()
