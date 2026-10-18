"""Render saved terminal aggregates only; no feature extraction or model fitting.
Usage: python3 generate_report.py --summaries-root CONTEXT/results --output-dir NEW_DIR
"""
import argparse
import hashlib
import html
import json
from pathlib import Path

VIEWS = [('pml', 'pml2110'), ('candidate', 'amp3075'), ('candidate', 'rawcomplex4099')]
CONDITIONS = [('within_speaker', '話者内'), ('across_speaker', '話者間')]
ESTIMANDS = ['flat_stratum', 'x_speaker_macro', 'nested_phone_context']
TARGETS = ['log_f0', 'rms_dbfs', 'spectral_slope']
LABELS = {'pml2110': 'PML · pml2110', 'amp3075': 'candidate · amp3075', 'rawcomplex4099': 'candidate · rawcomplex4099'}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summaries-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    sources, docs = {}, {}

    def load(key, relative):
        b = (args.summaries_root / relative).read_bytes()
        d = json.loads(b)
        assert d['validation_state'] == 'validated_end'
        sources[key] = {'summary_label': relative, 'sha256': digest(b)}
        docs[key] = d
        return d

    projection = {
        'schema': 'feature-partial-scalar-projection-v1',
        'state': 'partial_complete_canonical_incomplete',
        'scope_counts': {
            'test_recordings': 120, 'test_speakers': 40, 'train_feature_recordings': 120,
            'abx_planned_triplets': 4960, 'abx_covered_recordings': 113, 'abx_covered_speakers': 39,
            'readout_valid_train_targets': {'log_f0': 119, 'rms_dbfs': 120, 'spectral_slope': 120},
        },
        'canonical_complex4099': {
            'state': 'not_evaluated', 'train_success': 115, 'train_failed': 5,
            'test_success': 117, 'test_failed': 3,
            'reason': '外挿域の負F0による8件の特徴観測失敗。全train120規約によりABX/readout未評価。ゼロ補完なし。',
        },
        'representations': {}, 'paired_comparisons': {}, 'sources': sources,
        'interpretation': {
            'runtime_design': 'train-cloud/test-dot/evaluation-cloud',
            'host_numerical_identity_proven': False,
            'rank_rule': '各指標の自身の点推定を小さい順に記述的順位付け。同値同順位。差の確証とは別。総合順位なし。',
            'own_intervals': '元ABX/readout summaryのci95。各表現自身の区間。',
            'paired_intervals': '元comparison summaryのdelta_ci95。candidate−PMLの対応差の区間。',
            'limits': [
                '固定ABX集合のカバレッジは113録音39話者。120全録音の音素比較ではない。',
                '音声品質そのもの、因果的な操作性、任意のニューラルreadout能力を証明しない。',
                '音素タイミング誤差やPPG指標ではない。',
                'canonical未完の部分結果。未評価を0点や最下位に置換しない。',
            ],
        },
    }
    for method, view in VIEWS:
        abx_key = f'abx/{method}/{view}'
        readout_key = f'readout/{method}/{view}'
        a = load(abx_key, f'abx/{method}/{view}/summary.json')
        b = load(readout_key, f'readout/{method}/{view}/summary.json')
        assert a['planned_triplets'] == a['measured_triplets'] == 4960
        assert b['planned_cases'] == 120
        rep = {'method': method, 'abx': {}, 'readout': {}, 'abx_planned': 4960, 'abx_measured': 4960}
        for condition, _ in CONDITIONS:
            for estimand in ESTIMANDS:
                key = f'{condition}/{estimand}'
                original = a['summaries'][key]
                rep['abx'][key] = {'value': original['value'], 'ci95': original['ci95'], 'source': abx_key}
        for key in TARGETS:
            original = b['summaries'][key]
            assert original['status'] == 'measured' and original['recordings'] == 120 and original['speakers'] == 40
            assert original['diagnostics']['valid_train'] == projection['scope_counts']['readout_valid_train_targets'][key]
            rep['readout'][key] = {k: original[k] for k in ['status', 'recordings', 'speakers', 'planned_recordings', 'speaker_macro_mae', 'ci95', 'constant_train_mean_speaker_macro_mae']}
            rep['readout'][key].update(valid_train_targets=original['diagnostics']['valid_train'], source=readout_key)
        projection['representations'][view] = rep
    for view in ['amp3075', 'rawcomplex4099']:
        key = f'comparison/{view}'
        d = load(key, f'comparison/{view}/summary.json')
        assert d['formal_base'] == 'pml'
        paired = {}
        for metric, values in d['results'].items():
            assert metric.startswith(('abx/', 'readout/'))
            support_key = 'abx' if metric.startswith('abx/') else metric
            support = d['support'][support_key]
            paired[metric] = {k: values[k] for k in ['candidate', 'pml', 'candidate_minus_pml', 'delta_ci95', 'lower_better']}
            paired[metric].update(source=key, planned=support['planned'], paired_measured=support['paired_measured'])
        assert len(paired) == 9
        projection['paired_comparisons'][view] = paired
    assert len(sources) == 8
    for kind, field in [('abx', 'value'), ('readout', 'speaker_macro_mae')]:
        for metric in projection['representations']['pml2110'][kind]:
            values = [r[kind][metric][field] for r in projection['representations'].values()]
            for rep in projection['representations'].values():
                value = rep[kind][metric][field]
                rep[kind][metric]['descriptive_rank'] = 1 + sum(other < value for other in values)
    for target in TARGETS:
        assert len({r['readout'][target]['constant_train_mean_speaker_macro_mae'] for r in projection['representations'].values()}) == 1
    # Whitelisted projection contains no raw records, coefficients, arrays or local paths.
    encoded = json.dumps(projection, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    assert '/workspace/' not in encoded and 'librispeech_' not in encoded
    with (out / 'scalar-projection.json').open('x') as f:
        f.write(encoded)
    with (out / 'source-summary-sha256.json').open('x') as f:
        json.dump({'schema': 'saved-summary-sha256-map-v1', 'summaries': sources}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    esc = html.escape

    def number(value, signed=False):
        return format(value, '+.6f' if signed else '.6f')

    def ci(values):
        return '[' + ', '.join(number(v) for v in values) + ']'

    def own(rep, kind, metric):
        row = projection['representations'][rep][kind][metric]
        value = row['value'] if kind == 'abx' else row['speaker_macro_mae']
        return (f'<td><span class="rank r{row["descriptive_rank"]}">{row["descriptive_rank"]}位</span> '
                f'<strong>{number(value)}</strong><span class="interval">自身の95%区間 {ci(row["ci95"])}</span></td>')

    def paired(view, metric):
        row = projection['paired_comparisons'][view][metric]
        return (f'<td><strong>{number(row["candidate_minus_pml"], True)}</strong>'
                f'<span class="interval">対応差の95%区間 {ci(row["delta_ci95"])}</span></td>')

    headers = ''.join(f'<th scope="col">{esc(LABELS[v])}</th>' for _, v in VIEWS)
    abx_rows, delta_abx = [], []
    for condition, label in CONDITIONS:
        for estimand in ESTIMANDS:
            metric = f'{condition}/{estimand}'
            title = f'{label}<small>{estimand}</small>'
            abx_rows.append('<tr><th scope="row">' + title + '</th>' + ''.join(own(v, 'abx', metric) for _, v in VIEWS) + '<td class="na">未評価</td></tr>')
            delta_abx.append('<tr><th scope="row">' + title + '</th>' + ''.join(paired(v, 'abx/' + metric) for v in ['amp3075', 'rawcomplex4099']) + '</tr>')
    readout_rows, delta_readout = [], []
    for metric in TARGETS:
        baseline = projection['representations']['pml2110']['readout'][metric]['constant_train_mean_speaker_macro_mae']
        readout_rows.append(f'<tr><th scope="row">{metric}</th>' + ''.join(own(v, 'readout', metric) for _, v in VIEWS) + f'<td>{number(baseline)}</td><td class="na">未評価</td></tr>')
        delta_readout.append(f'<tr><th scope="row">{metric}</th>' + ''.join(paired(v, 'readout/' + metric) for v in ['amp3075', 'rawcomplex4099']) + '</tr>')
    source_rows = ''.join(f'<tr><th scope="row">{esc(k)}</th><td class="hash">{s["sha256"]}</td></tr>' for k, s in sources.items())
    document = '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>固定特徴量評価 — 部分結果</title><style>
:root{color-scheme:light dark;--bg:#f5f6f8;--card:#fff;--ink:#202b3a;--muted:#586578;--line:#d8dee7;--accent:#345c79}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,sans-serif}main{max-width:1400px;margin:auto;padding:32px 24px 60px}header{border-top:5px solid var(--accent);padding-top:20px}h1{font-size:2rem;margin:6px 0}h2{font-size:1.45rem;margin:32px 0 8px}h3{font-size:1.1rem;margin:24px 0 8px}p{max-width:100ch}.eyebrow{color:var(--accent);font-weight:700}.note{background:var(--card);border:1px solid var(--line);border-left:4px solid #ac8754;padding:16px 20px;margin:22px 0}.wrap{overflow-x:auto;border:1px solid var(--line);background:var(--card);border-radius:6px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:13px 14px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}thead th{background:var(--bg);font-size:13px}tbody th{font-weight:600;min-width:170px}td{min-width:210px}small,.interval{display:block;font-size:12px;color:var(--muted);white-space:nowrap}strong{font-weight:650}.rank{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:2px 5px;white-space:nowrap}.r1{background:#dcebe3;color:#284f3a}.r2{background:#e4eaf1;color:#354c64}.r3{background:#eee9e0;color:#675742}.na{color:var(--muted);min-width:110px}.hash{font:12px/1.8 ui-monospace,monospace;overflow-wrap:anywhere}a{color:var(--accent)}footer{color:var(--muted);margin-top:35px}li{margin:6px 0}@media(prefers-color-scheme:dark){:root{--bg:#17202c;--card:#202c3a;--ink:#e4eaf3;--muted:#adb9ca;--line:#3d4b60;--accent:#9dc7e4}}@media print{body{background:white;color:#111}main{padding:0}.wrap{overflow:visible}table{font-size:10px}td,th{min-width:0;padding:6px}.interval{white-space:normal;font-size:9px}.note{break-inside:avoid}}
</style><main><header><div class="eyebrow">保存済み終端summaryの表示 · 再計算なし</div><h1>固定特徴量評価の部分結果</h1><p>PMLを比較基準として、candidateのamp3075・rawcomplex4099を示します。各指標は小さいほど誤差が小さい数値です。順位は3表現の点推定の記述的な順序であり、差の確証とは別です。総合順位は設けません。</p></header>
<div class="note"><strong>canonical_complex4099は未評価のまま保持</strong><br>特徴観測はtrain 115/120成功・5件失敗、test 117/120成功・3件失敗。8件とも外挿域の負F0で失敗しました。全train120規約を満たさないためABX/readoutは未評価です。0点補完・失敗除外による再fitは行っていません。</div>
<h2>ABX：固定集合での比較</h2><p>3表現とも4,960/4,960三つ組を測定。固定集合のカバレッジは<strong>113録音・39話者</strong>で、120全録音の音素比較ではありません。話者内・話者間それぞれの3集計をすべて掲載します。値は0〜1の元スケールです。</p>
<div class="wrap"><table><thead><tr><th scope="col">条件 / 集計</th>''' + headers + '''<th scope="col">canonical_complex4099</th></tr></thead><tbody>''' + ''.join(abx_rows) + '''</tbody></table></div>
<h3>ABX：PMLとの対応差</h3><p>差はcandidate − PML。負はcandidateの誤差が小さい方向です。下表は対応差の区間であり、上表の各表現自身の区間ではありません。</p>
<div class="wrap"><table><thead><tr><th scope="col">条件 / 集計</th><th scope="col">amp3075 − PML</th><th scope="col">rawcomplex4099 − PML</th></tr></thead><tbody>''' + ''.join(delta_abx) + '''</tbody></table></div>
<h2>固定線形readout</h2><p>評価対象は<strong>test 120録音・40話者</strong>。3表現ともtrain特徴120件すべてを用意し、事前規約に従って目的変数が有効なtrainを使用しています。有効教師値は<strong>log_f0が119件、rms_dbfs・spectral_slopeが各120件</strong>です。speaker_macro_mae、各表現自身の95%区間、定数train平均予測の誤差を示します。定数予測の誤差は3表現で共通であり、順位には含めません。</p>
<div class="wrap"><table><thead><tr><th scope="col">目的変数</th>''' + headers + '''<th scope="col">定数train平均予測 MAE</th><th scope="col">canonical_complex4099</th></tr></thead><tbody>''' + ''.join(readout_rows) + '''</tbody></table></div>
<h3>readout：PMLとの対応差</h3><p>各目的変数とも対応比較は120/120録音です。元comparison summaryの差と区間をそのまま掲載します。</p>
<div class="wrap"><table><thead><tr><th scope="col">目的変数</th><th scope="col">amp3075 − PML</th><th scope="col">rawcomplex4099 − PML</th></tr></thead><tbody>''' + ''.join(delta_readout) + '''</tbody></table></div>
<h2>解釈できる範囲</h2><ul><li>実行環境はtrain-cloud / test-dot / evaluation-cloud。ホスト間の数値同一性は未証明です。</li><li>この固定線形readoutから、音声品質そのもの、因果的な操作性、任意のニューラルreadout能力が証明されたとは言えません。</li><li>ABXはここで固定した表現比較です。音素タイミング誤差やPPG指標ではありません。</li><li>canonical未完を含む部分結果です。未評価に数値・順位は付けません。</li></ul>
<h2>出典と表示精度</h2><p>8個の既存終端summaryを参照しています。HTMLは小数点以下6桁へ表示丸めしています。<a href="scalar-projection.json">scalar JSON</a>には元の数値精度と各区間、対応差、件数を保持し、<a href="source-summary-sha256.json">出典SHA対応</a>で照合できます。自身の点推定と対応比較の点推定には集計上の浮動小数点の微差があり、どちらも元の値を保持しています。</p>
<div class="wrap"><table><thead><tr><th scope="col">summary</th><th scope="col">SHA-256</th></tr></thead><tbody>''' + source_rows + '''</tbody></table></div><footer>公開操作は行っていません。raw行・case対応表・モデル・音声・private絶対パスはこの表示用JSONに含みません。</footer></main></html>'''
    assert '/workspace/' not in document and 'librispeech_' not in document
    with (out / 'index.html').open('x') as f:
        f.write(document)
    # Byte identity of the original summaries remains unchanged.
    for source in sources.values():
        assert digest((args.summaries_root / source['summary_label']).read_bytes()) == source['sha256']
    print(json.dumps({'summaries': len(sources), 'abx_aggregates': 18, 'readout_aggregates': 9, 'paired_aggregates': 18, 'state': projection['state']}))


if __name__ == '__main__':
    main()
