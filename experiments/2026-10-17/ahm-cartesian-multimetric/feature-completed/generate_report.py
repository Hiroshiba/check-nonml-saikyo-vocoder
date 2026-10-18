"""Display frozen v1 scalar results alongside completed canonical v2 aggregates.
No feature extraction, inference, fitting, bootstrap, or audio generation.
Run only after receipt and provenance review of the final v2 handoff.
"""
import argparse
import copy
import hashlib
import html
import json
import math
from pathlib import Path

OLD_SHA = '68adca548712ddcf557627fee7e008f4920ea5f3f8db98df07927d27074e3ce2'
FREEZE = 'a32742ae13fe2098bc4bb9e5e08d94ae42cf9d5e07cae300797b34ca0b317b97'
VIEW = 'canonical_complex4099'
TARGETS = ('log_f0', 'rms_dbfs', 'spectral_slope')
ABX = tuple(f'{c}/{e}' for c in ('within_speaker', 'across_speaker')
            for e in ('flat_stratum', 'x_speaker_macro', 'nested_phone_context'))
TARGET_LABELS = {'log_f0': '対数F0（自然対数Hz）', 'rms_dbfs': '音量（RMS dBFS）', 'spectral_slope': 'スペクトル傾斜（dB/oct）'}
LABELS = {'pml2110': '現PML', 'amp3075': '振幅', 'rawcomplex4099': '元の複素値',
          VIEW: '位相時計を引いた複素値 v2'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def render(data):
    def num(value):
        return '—' if value is None else f'{value:.6f}'

    def interval(values):
        return '区間なし' if values is None else '[' + ', '.join(num(v) for v in values) + ']'

    def table(headers, rows):
        head = ''.join('<th>' + html.escape(x) + '</th>' for x in headers)
        body = ''.join('<tr>' + ''.join('<td>' + v + '</td>' for v in row) + '</tr>' for row in rows)
        return '<div class="scroll"><table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>'

    doc = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>固定特徴量評価：canonical v2補完</title><style>'
    doc += 'body{max-width:1400px;margin:32px auto;padding:0 22px;font:16px/1.65 system-ui;color:#213044;background:#f6f8fa}.scroll{overflow:auto;background:white}table{border-collapse:collapse;width:100%}th,td{padding:12px;border-bottom:1px solid #ddd;vertical-align:top;text-align:left;min-width:180px}small{display:block;color:#536277}h2{margin-top:38px}.note{padding:16px;background:#fff0cf}a{color:#155ba0}.rank{display:inline-block;padding:2px 7px;border:1px solid #bbb;border-radius:5px;margin-right:8px}.r1{background:#fbe4a2;font-weight:bold}.r2{background:#e2e8ed;font-weight:bold}.r3{background:#edceb5;font-weight:bold}@media(prefers-color-scheme:dark){body{background:#17212d;color:#e4eaf2}table,.scroll{background:#202d3b}td,th{border-color:#425265}.note,.notice{background:#423720;color:#f1e8d6}a{color:#99c8ff}small{color:#bac6d5}}</style>'
    doc += '<h1>固定特徴量評価：canonical v2を追加</h1><p>比較基準は現PML。振幅・元の複素値・位相時計を引いた複素値は同じ候補の観測方法です。独立した3方式や3票として数えません。音声品質の総合勝者やbase変更は、この評価から決めません。</p>'
    doc += '<p><strong>今回の読み取り：</strong>canonical v2のABXは6集計すべてでPMLより高い誤り率の点推定でした。音量・スペクトル傾斜の固定線形読み出しもPMLより誤差が大きく、位相時計を引く処理だけで扱いやすい特徴空間になったとは言えません。情報そのものの不存在や、全ての読み出し方法での劣位を意味しません。追加診断では、120録音中1録音でtrain定数だった周波数列が大きな二乗半径を生みました。この録音を含むABXは4,960中81組ですが、該当フレームとの重なりや層別集計への寄与は未確認です。距離尺度による影響と音声情報の不足を区別して読みます。</p><p class="note">canonical v1はtrain5件・test3件で外挿F0が負になり未評価でした。その記録を残し、外挿範囲だけ端点保持にしたv2を別runで計測しました。新しいtrain/test momentsは各120件。旧3表現は保存値の再利用で、新たに再計算した値ではありません。</p>'
    doc += '<p><a href="../feature-partial/index.html">旧部分結果・v1失敗記録</a> ／ <a href="scalar-projection.json">元精度の数値・支持・SHA</a></p>'
    reps = data['representations']
    for kind, field, title, desc in (
        ('abx', 'value', '音素ABX', '全体4,960三つ組（同一話者186、異話者4,774）。各ABX行の対応支持はこの条件別の件数です。固定集合のカバレッジは113録音・39話者です。120録音すべてを覆う比較ではありません。'),
        ('readout', 'speaker_macro_mae', '固定線形readout', '独立train120とtest120録音・40話者。log F0の有効教師値は119件、他は120件。録音単位の時間平均から読み出す固定ridgeの誤差です。対数F0の教師値は原音で推定できた有声フレームの平均であり、保存F0そのものや絶対F0真値ではありません。')):
        doc += '<h2>' + title + '</h2><p>' + desc + ' 小さいほど誤差が小さく、順位は点推定の記述的順序です。95%区間は差の区間ではありません。</p>'
        rows = []
        for metric in reps['pml2110'][kind]:
            row = [html.escape(TARGET_LABELS.get(metric, metric))]
            for view in LABELS:
                value = reps[view][kind][metric]
                rank = value['descriptive_rank']
                row.append(f'<span class="rank r{rank}">{rank}位</span><b>{num(value[field])}</b><small>自身の95%区間 {interval(value["ci95"])}</small>')
            if kind == 'readout':
                row.append(num(reps['pml2110'][kind][metric]['constant_train_mean_speaker_macro_mae']))
            rows.append(row)
        doc += table(['指標'] + list(LABELS.values()) + (['定数train平均 MAE'] if kind == 'readout' else []), rows)
        delta_rows = []
        for metric in reps['pml2110'][kind]:
            row = [html.escape(TARGET_LABELS.get(metric, metric))]
            for view in ('amp3075', 'rawcomplex4099', VIEW):
                v = data['paired_comparisons'][view][kind + '/' + metric]
                row.append(num(v['candidate_minus_pml']) + '<small>対応差の95%区間 ' + interval(v['delta_ci95']) + '</small>' + f'<small>対応支持 {v["paired_measured"]}/{v["planned"]}</small>')
            delta_rows.append(row)
        doc += '<h3>現PMLとの対応差</h3><p>候補−PML。負なら候補の誤差が小さい方向です。総合点・平均順位は作りません。</p>'
        doc += table(['指標'] + [LABELS[x] + ' − PML' for x in ('amp3075', 'rawcomplex4099', VIEW)], delta_rows)
    diagnostics = []
    for view in LABELS:
        for target in TARGETS:
            v = reps[view]['readout'][target]['diagnostics']
            diagnostics.append([LABELS[view], TARGET_LABELS[target], str(v['dimensions']), str(v['constant_dimensions']), str(v['matrix_rank']), str(v['valid_train'])])
    doc += '<details><summary>次元数・定数次元・数値階数の診断</summary><p>数値階数は性能順位ではありません。固定alpha=1、各目的変数の有効trainによる尺度調整です。</p>' + table(['表現', '目的変数', '次元', '定数次元', '数値階数', '有効train'], diagnostics) + '</details>'
    doc += '<h2>読み方と限界</h2><ul>' + ''.join('<li>' + html.escape(x) + '</li>' for x in data['interpretation']['limits']) + '</ul>'
    doc += '<p>複素特徴の時間平均は位相の相殺を受け得ます。線形読み出しの弱さを、復号可能な情報が存在しないこととは言い換えません。PMLとの差の区間と、表現ごとの区間を区別してください。</p>'
    doc += '<h2>新しい出典</h2><p>旧8summaryのSHAは引用元projection、新しい5summaryは下表に保持します。モデル・raw行・生特徴量・音声は含みません。HTMLの数値は小数6桁に表示丸めしています。</p>'
    doc += table(['summary', 'SHA-256'], [[html.escape(k), '<small>' + v + '</small>'] for k, v in data['new_canonical_v2']['source_summaries'].items()])
    return doc + '</html>'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old-projection', type=Path, required=True)
    ap.add_argument('--old-results', type=Path, required=True)
    ap.add_argument('--v2-results', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    blob = args.old_projection.read_bytes()
    require(digest(blob) == OLD_SHA, 'Previously published scalar projection changed')
    old = json.loads(blob)
    projection = copy.deepcopy(old)
    sources = {}
    diagnostic_keys = ('alpha', 'valid_train', 'constant_dimensions', 'matrix_rank', 'dimensions', 'constant_prediction')
    for method, view in (('pml', 'pml2110'), ('candidate', 'amp3075'), ('candidate', 'rawcomplex4099')):
        source_key = f'readout/{method}/{view}'
        source = old['sources'][source_key]
        raw = (args.old_results / source['summary_label']).read_bytes()
        require(digest(raw) == source['sha256'], 'Old readout summary identity changed')
        original = json.loads(raw)
        for target in TARGETS:
            diagnostic = original['summaries'][target]['diagnostics']
            projection['representations'][view]['readout'][target]['diagnostics'] = {k: diagnostic[k] for k in diagnostic_keys}

    def load(relative):
        raw = (args.v2_results / relative).read_bytes()
        data = json.loads(raw)
        require(data['validation_state'] == 'validated_end', 'Nonterminal source')
        freeze = data.get('source_freeze_sha256', data.get('contract', {}).get('source_freeze_sha256'))
        require(freeze == FREEZE, 'Unexpected v2 scientific freeze')
        sources[relative] = digest(raw)
        return data

    moment_hashes = {}
    for split in ('train', 'test'):
        name = f'{split}/candidate/{VIEW}/summary.json'
        m = load(name)
        require(m['planned_cases'] == 120 and len(m['rows']) == 120, 'Incomplete planned moment set')
        require(len({r['case'] for r in m['rows']}) == 120, 'Duplicate moment cases')
        require([r['case'] for r in m['rows']] == m['case_ids'], 'Moment case order mismatch')
        require(all(r['status'] == 'measured' for r in m['rows']),
                'Canonical moments incomplete; prepare a missing-results report instead')
        require(m['contract']['view'] == VIEW and m['contract']['method'] == 'candidate', 'Moment identity mismatch')
        moment_hashes[split] = sources[name]
    aname = f'abx/candidate/{VIEW}/summary.json'
    rname = f'readout/candidate/{VIEW}/summary.json'
    cname = f'comparison/{VIEW}/summary.json'
    a, r, c = load(aname), load(rname), load(cname)
    require(a['planned_triplets'] == a['measured_triplets'] == 4960, 'ABX missing support')
    require(r['planned_cases'] == 120, 'Readout plan mismatch')
    for item in (a, r):
        require(item['contract']['view'] == VIEW and item['contract']['method'] == 'candidate', 'Representation mismatch')
        for split in ('train', 'test'):
            require(item['contract'][f'{split}_summary_sha256'] == moment_hashes[split], 'Moment linkage mismatch')
    require(c['formal_base'] == 'pml' and c['view'] == VIEW, 'Comparison identity mismatch')
    expected_sources = {sources[aname], sources[rname],
                        old['sources']['abx/pml/pml2110']['sha256'],
                        old['sources']['readout/pml/pml2110']['sha256']}
    require({x['sha256'] for x in c['source_summaries']} == expected_sources,
            'Paired comparison does not link the exact prior PML and new canonical summaries')
    require(c['support']['abx']['paired_measured'] == 4960, 'ABX paired support missing')
    rep = {'method': 'candidate', 'abx': {}, 'readout': {}, 'abx_planned': 4960, 'abx_measured': 4960}
    for key in ABX:
        v = a['summaries'][key]
        rep['abx'][key] = {'value': v['value'], 'ci95': v['ci95'], 'source': aname}
    for key in TARGETS:
        v = r['summaries'][key]
        require(v['status'] == 'measured' and v['recordings'] == 120 and v['speakers'] == 40, 'Readout missing support')
        require(v['diagnostics']['valid_train'] == (119 if key == 'log_f0' else 120), 'Training target support changed')
        support = c['support']['readout/' + key]
        require(support['paired_measured'] == 120 and len(support['speakers']) == 40, 'Readout paired support missing')
        rep['readout'][key] = {k: v[k] for k in ('status', 'recordings', 'speakers', 'planned_recordings',
                                               'speaker_macro_mae', 'ci95', 'constant_train_mean_speaker_macro_mae')}
        rep['readout'][key].update(valid_train_targets=v['diagnostics']['valid_train'], source=rname)
        rep['readout'][key]['diagnostics'] = {k: v['diagnostics'][k] for k in diagnostic_keys}
        expected = old['representations']['pml2110']['readout'][key]['constant_train_mean_speaker_macro_mae']
        require(abs(v['constant_train_mean_speaker_macro_mae'] - expected) < 1e-12, 'Constant baseline changed')
    projection['representations'][VIEW] = rep
    paired = {}
    for metric in tuple('abx/' + x for x in ABX) + tuple('readout/' + x for x in TARGETS):
        v = c['results'][metric]
        require(v['lower_better'] is True, 'Unexpected metric direction')
        paired[metric] = {k: v[k] for k in ('candidate', 'pml', 'candidate_minus_pml', 'delta_ci95', 'lower_better')}
        s = c['support']['abx' if metric.startswith('abx/') else metric]
        paired[metric].update(source=cname, planned=s['planned'], paired_measured=s['paired_measured'])
    projection['paired_comparisons'][VIEW] = paired
    raw_abx_path = args.v2_results / f'abx/candidate/{VIEW}/raw-triplets.json'
    raw_abx = raw_abx_path.read_bytes()
    require(digest(raw_abx) == a['raw_sha256'], 'ABX raw linkage mismatch')
    raw_triplets = json.loads(raw_abx)
    require(len(raw_triplets) == 4960 and all(v['status'] == 'measured' for v in raw_triplets), 'ABX support incomplete')
    condition_counts = {condition: sum(v['condition'] == condition for v in raw_triplets)
                        for condition in ('within_speaker', 'across_speaker')}
    require(condition_counts == {'within_speaker': 186, 'across_speaker': 4774}, 'Fixed condition support changed')
    projection['scope_counts']['abx_triplets_by_condition'] = condition_counts
    for comparisons in projection['paired_comparisons'].values():
        for metric, value in comparisons.items():
            if not metric.startswith('abx/'):
                continue
            require(value['planned'] == value['paired_measured'] == 4960, 'Prior full ABX support changed')
            value['whole_run_planned'] = value['planned']
            value['whole_run_paired_measured'] = value['paired_measured']
            value['support_scope'] = 'abx_condition'
            count = condition_counts[metric.split('/')[1]]
            value['planned'] = value['paired_measured'] = count
    projection['abx_support_source'] = {'path': f'abx/candidate/{VIEW}/raw-triplets.json', 'sha256': digest(raw_abx)}
    projection['schema'] = 'feature-completed-scalar-projection-v3' 
    projection['state'] = 'completed_with_separate_canonical_v2'
    projection['canonical_v1_history'] = projection.pop('canonical_complex4099')
    projection['new_canonical_v2'] = {'train_measured': 120, 'test_measured': 120,
                                     'source_freeze_sha256': FREEZE, 'source_summaries': sources}
    projection['prior_projection_sha256'] = OLD_SHA
    projection['interpretation']['limits'] = [
        'v1の失敗記録を保持したまま、端点外挿だけを修正したv2を追加。旧3表現は保存値の再利用。',
        'ABX集合のカバレッジは113録音39話者。120全録音の音素比較ではない。',
        '同じ候補の3表現を3方式・独立した3票と数えない。総合順位なし。',
        '録音平均に対する固定線形readout。情報の不存在、因果的操作性、音声品質を直接証明しない。',
        '既存開発集合であり、独立した最終検証ではない。ホスト間の数値同一性は未証明。']
    projection['interpretation']['runtime_design'] = '旧3表現はv1保存値を引用。canonical v2のmoments・ABX・readout・対応比較は別Cloud run。入力payloadの出自と数値ホスト同一性は別。'
    projection['interpretation']['rank_rule'] = '同じ全支持を持つ4表現の点推定による記述的順位。同値同順位。差の確証と別。'
    for kind, field in (('abx', 'value'), ('readout', 'speaker_macro_mae')):
        for metric in projection['representations']['pml2110'][kind]:
            values = [v[kind][metric][field] for v in projection['representations'].values()]
            require(all(isinstance(v, (float, int)) and math.isfinite(v) for v in values), 'Nonfinite rank value')
            for v in projection['representations'].values():
                v[kind][metric]['descriptive_rank'] = 1 + sum(x < v[kind][metric][field] for x in values)
    encoded = json.dumps(projection, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    require('/workspace/' not in encoded and 'librispeech_' not in encoded, 'Private detail in public projection')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / 'scalar-projection.json').write_text(encoded)
    (args.output_dir / 'index.html').write_text(render(projection))
    print(json.dumps({'state': projection['state'], 'representations': len(LABELS),
                      'new_source_summaries': len(sources), 'output_sha256': digest(encoded.encode())}))


if __name__ == '__main__':
    main()
