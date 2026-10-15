"""日本語HTML。HNM比較を冒頭に置き、方向・区間・状態を同じ表へ表示。"""
from __future__ import annotations

from collections import Counter
from html import escape
import json

from export_render_constants import CREDITS_NAME, PUBLIC_IDS, PUBLIC_METHODS
from export_types import METHODS
from export_render_constants import FAMILIES

NAMES = {'original': '原音', 'hnm': 'HNM v3（現base）', 'world_harvest': 'WORLD Harvest', 'facodec': 'FACodec v1',
         'hifiglot': 'HiFi-Glot', 'golf': 'GOLF-ff', 'sifigan': 'SiFi-GAN',
         'llsm2': 'LLSM2 Layer0', 'magphase': 'MagPhase'}
DIRECTION = {'higher': '大きいほどこの指標が良い', 'lower': '小さいほどこの指標が良い', None: '診断・順位なし'}
CSS = '''
:root{color-scheme:light dark;--bg:#faf9f5;--fg:#222b32;--line:#d7d7d0;--accent:#235a50;--soft:#edf3ef}
@media(prefers-color-scheme:dark){:root{--bg:#151c20;--fg:#e5e8e5;--line:#435052;--accent:#a3dbce;--soft:#202f31}}
*{box-sizing:border-box}body{margin:auto;max-width:1440px;padding:32px 24px;background:var(--bg);color:var(--fg);font:16px/1.65 system-ui,sans-serif}
h1{line-height:1.3;font-size:2rem}h2{margin-top:3rem;border-bottom:2px solid var(--accent)}h3{margin-top:2rem}a{color:var(--accent)}
.scroll{overflow:auto}table{border-collapse:collapse;font-size:.9rem;width:100%;margin:1rem 0}th,td{border:1px solid var(--line);padding:.5rem;vertical-align:top;text-align:left}
th{background:var(--soft);position:sticky;top:0}.note{padding:1rem;border-left:4px solid var(--accent);background:var(--soft)}
small,.muted{opacity:.8}.number{font-variant-numeric:tabular-nums;white-space:nowrap}details{margin:.8rem 0}summary{cursor:pointer}
nav a{display:inline-block;margin:.3rem .8rem .3rem 0}audio{max-width:240px}code{overflow-wrap:anywhere}li{margin:.25rem 0}
'''


def e(value):
    return escape(str(value))


def number(value):
    return '—' if value is None else f'{value:.6g}'


def interval(value):
    return '—' if not value else f'[{number(value[0])}, {number(value[1])}]'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{e(h)}</th>' for h in headers) + \
        '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows) + \
        '</tbody></table></div>'


def counts(state):
    names = {'success': '許容成功', 'pending': '未完', 'failed': '失敗', 'not_applicable': '適用外',
             'unsupported': '未対応', 'other_terminal': 'その他終端'}
    text = ' / '.join(f'{names.get(key, key)} {count}' for key, count in state.get('status_category_counts', {}).items())
    result = e(text)
    if state.get('observation_unit') == 'input_feature_recording':
        result += '<br><small>状態の単位は入力録音の特徴抽出。評定対や指標値の件数ではありません。</small>'
    else:
        result += f'<br><small>直接値 {state.get("direct_measured", 0)}・同一性からの値 {state.get("analytic_identity", 0)}</small>'
    if state.get('status_counts', {}).get('pcm16_range_exceeded'):
        result += '<br><small>PCM16範囲超過による欠測: ' + e(state['status_counts']['pcm16_range_exceeded']) + '</small>'
    if state.get('calibration_failure_counts'):
        result += '<br><small>独立train校正の失敗: ' + e(json.dumps(state['calibration_failure_counts'], ensure_ascii=False)) + '</small>'
    return result


def denominator(primary):
    if 'common_valid_recordings' in primary:
        return f'共通 {primary["common_valid_recordings"]}録音・{primary["common_valid_speakers"]}話者'
    cohort = primary.get('cohort', {})
    names = {'recordings': '録音', 'speakers': '話者', 'pairs': '対', 'triplets': '三つ組',
             'tokens': '音素区間', 'b_anchors': '基準録音', 'b_speakers': '基準話者'}
    if 'planned' in cohort or 'common' in cohort:
        sections = []
        for key, label in [('planned', '予定'), ('common', '共通有効')]:
            counts_ = cohort.get(key, {})
            sections.append(label + ': ' + '・'.join(f'{counts_[name]}{text}' for name, text in names.items() if name in counts_))
        return ' / '.join(sections)
    if 'planned_recordings' in cohort:
        return (f'予定 {cohort["planned_recordings"]}録音・{cohort.get("planned_speakers", "—")}話者 / '
                f'共通 {cohort.get("common_recordings", 0)}録音・{cohort.get("common_speakers", 0)}話者')
    return '比較分母の実証跡は未到着'


def label(group):
    if group['label'] != group['id']:
        return group['label']
    names = {'pitch_minus3': '音高−3半音', 'pitch_plus3': '音高＋3半音',
        'gain_minus6': '音量−6dB', 'gain_plus6': '音量＋6dB', 'time_scale1p25': '時間1.25倍',
        'time_preservation': '時間保存', 'slope_preservation': '傾斜保存', 'slope_minus3': '傾斜−3dB/oct',
        'slope_plus3': '傾斜＋3dB/oct', 'gain': '音量操作', 'pitch': '音高操作', 'time': '時間操作',
        'slope': '傾斜操作', 'unedited': '未編集', 'relative_f0_mae': '相対F0 MAE',
        'missing_voiced_fraction': '有声未検出率', 'rms_frame_mae': 'RMSフレームMAE',
        'pitch_cents': '推定音高', 'level_db': '音量', 'slope_db_per_octave': '傾斜',
        'duration_seconds': '全長', 'absolute_normalized_response_error': '正規化応答絶対誤差',
        'absolute_duration_error': '全長絶対誤差', 'missing_event_fraction': 'イベント未検出・比較不能率',
        'common_event_mae': '共通イベントMAE', 'native_slope_error': 'native傾斜誤差',
        'predicted_mos': '予測MOS', 'speaker_similarity': '話者類似度', 'delta_from_unedited': '未編集との差'}
    return '・'.join(names.get(part, part) for part in group['id'].split('.')[1:])


def ranking_table(group, selected):
    rows = []
    cells = selected.get('methods', {})
    for method in METHODS:
        cell = cells.get(method, {})
        delta = cell.get('hnm_difference') or {}
        state = group['method_states'][method]
        rows.append([e(NAMES[method]), e(number(cell.get('rank'))), e(number(cell.get('value'))),
            e(interval(cell.get('ci95'))), e(number(delta.get('value'))), e(interval(delta.get('ci95'))),
            counts(state), e('対象' if method in selected.get('comparable_methods', group['methods']) else '比較対象外')])
    return table(['方式', '順位', '値', '95%区間', 'HNMとの差', '差の95%区間', '全予定状態', '比較集合'], rows)


def display_unit(group):
    # 元結果のunitは維持し、目標値の単位と絶対誤差の単位だけを区別する。
    return 'dB（RMS目標値はdBFS）' if group['id'] == '15.rms_dbfs' else group['unit']


def note_lines(value):
    if isinstance(value, dict):
        return [f'{key}: {line}' for key, item in value.items() for line in note_lines(item)]
    if isinstance(value, (list, tuple)):
        return [line for item in value for line in note_lines(item)]
    return [] if value is None else [str(value)]


def special_notes(group):
    """専用評価の定義・学習対象・不確実性を、値の表の直前に併記する。"""
    notes = []
    family = group['family']
    if family == 1 or group['id'].endswith('.predicted_mos'):
        notes.append('予測MOSは今回の音声群の人間評定では校正していない自動予測です。'
                     'FACodecの予測値が原音より高くても、聴感上の優越を証明しません。')
    if family == 4:
        notes.append('増分CER/WERは再合成音と原音の認識誤り率の差です。負値は使用した音声認識器で'
                     '原音より誤り率が下がったことを表し、人間にとって内容が改善した証拠ではありません。')
    if family == 14:
        condition, estimand = group['id'].split('.', 1)[1].split('/')
        definition = (group.get('definitions') or {}).get(estimand)
        if definition:
            notes.append('集計順序（各段階を等重み）: ' + definition)
        notes.append('層は条件・有向音素対・文脈・A話者・X話者で定義し、まず層内の三つ組を平均する。'
                     '三つ組全体の単純平均とは別の集計。')
        if condition == 'within_speaker':
            planned = group['primary'].get('cohort', {}).get('planned', {})
            if 'recordings' in planned and 'speakers' in planned:
                notes.append(f'同話者ABXの対象は{planned["recordings"]}録音・{planned["speakers"]}話者に限定。'
                             '主評価120録音全体の結果ではない。')
    if family == 15:
        target = group['id'].split('.', 1)[1]
        support = (group.get('train_target_support') or {}).get(target)
        evidence = group.get('train_target_evidence')
        if support:
            planned = (group.get('calibration_cohort') or {}).get('required_train_recordings', '—')
            notes.append(f'独立学習集合（train）の目標値が有効な録音: {support["valid_recordings"]}/{planned}録音・'
                         f'{support["valid_speakers"]}話者。評価集合の分母とは別。')
        if evidence:
            reasons = Counter(row['missing_reasons'][target] for row in evidence['records']
                              if target in row.get('missing_reasons', {}))
            names = {'no positive voiced YIN estimates': 'YINで正値の有声F0推定が得られない'}
            notes.extend(f'学習目標値の欠測理由: {names.get(reason, reason)}（{count}録音）。0埋めしない。'
                         for reason, count in reasons.items())
        if target == 'log_f0':
            notes.append('目標値はHz単位の推定F0の自然対数。MAEはln(Hz)の差の絶対誤差であり、Hzやcentの誤差ではない。')
        elif target == 'rms_dbfs':
            notes.append('RMS目標値はdBFS。表のMAEとHNMとの差は、その差分の単位であるdBで示す。')
    if family in (14, 15):
        notes.append('95%区間は今回固定した独立学習集合と校正・学習済みパラメータに条件付き。'
                     '学習集合を再抽出・再学習する不確実性は含まない。')
    notes.extend(note_lines(group.get('uncertainty')))
    notes.extend(note_lines(group.get('limits')))
    return ('<div class="note"><ul>' + ''.join(f'<li>{e(note)}</li>' for note in dict.fromkeys(notes))
            + '</ul></div>') if notes else ''


def statistical_notes(group):
    if group['family'] == 13:
        aggregation = '録音対等重みの相関／B話者等重みの最近傍一致。話者グラフに条件付きの記述的node再抽出区間。'
    elif group['family'] == 14:
        aggregation = '直前の専用定義に従う層・X話者・音素対と文脈の集約。話者グラフに条件付きのnode再抽出区間。'
    else:
        aggregation = group.get('aggregation', '同じ録音→話者内平均→話者等重み。')
    return ('<p class="note">' + e(aggregation) + ' '
            '有効な比較支持がある場合の設定は最大2000回・seed20261014。共通0や2話者未満では区間を算出しません。実行回数は保存証拠に従います。95%区間は記述的で多重比較未補正。HNM差は同じ比較集合・同じ再抽出による「方式−HNM」。'
            '同点は未丸め値の絶対1e-12/相対1e-9許容差を同点群先頭と比較する競技順位。'
            '区間の重なりだけで同点や有意差を決めません。失敗・適用外・未完は0点や最下位にしません。</p>')


def coverage_cell(cell):
    text = e('元計画: ' + cell['label'])
    for supplement in cell.get('availability_supplements', []):
        state = supplement['counts']
        text += '<hr><a href="' + e(supplement['anchor']) + '">' + e(supplement['label']) + '</a><br>'
        text += e(supplement['status_label']) + '<br>' + counts(state)
        text += '<br><small>全8主群: ' + e(denominator(supplement['primary'])) + '</small>'
        if supplement['conditional']:
            text += '<br><small>条件付き: ' + e(denominator(supplement['conditional']))
            text += e('・この方式を含む' if supplement['conditional_included'] else '・この方式は対象外') + '</small>'
    return text


def quantization_supplement(report, family):
    item = report.get('quantization_common_supplement', {})
    if item.get('status') != 'available':
        return '<p class="note">量子化共通窓の事後別補助は未添付。元の厳格全長比較・適用外を維持します。</p>'
    return (f'<p id="quantization-common-window-family-{family}" class="note">'
            '事後追加の量子化共通先頭区間による聴覚差。元の厳格全長比較を置換しません。'
            '方式ごとの入力変化量が異なり、同じ摂動強度の耐性比較ではありません。'
            '<a href="' + e(item['href']) + '">全8固定・成功方式条件付きの補助結果と長さ差</a> ／ '
            '<a href="' + e(item['results_href']) + '">補助JSON</a>。'
            '#17と#18は同一聴覚値を参照し、独立した評価や投票には数えません。</p>')


def group_section(group):
    anchor = 'group-' + group['id']
    text = f'<section id="{e(anchor)}"><h3>{e(label(group))}</h3>'
    text += f'<p>{e(group.get("scope", ""))}<br>{e(display_unit(group))}・{e(DIRECTION[group["direction"]])}</p>'
    if group.get('note'):
        text += f'<p class="note">{e(group["note"])}</p>'
    if group.get('observation_unit') == 'method_fixed_assets':
        rows = [[e(NAMES[r['method']]), e(number(r['value'])), e(r['status'])] for r in group['method_constants']]
        return text + '<p>方式ごとの定数です。録音へ複写せず、順位・話者区間はありません。</p>' + table(['方式', '宣言bytes', '状態'], rows) + '</section>'
    primary = group['primary']
    if group.get('planned_recordings_per_method') is not None:
        text += f'<p>予定 {group["planned_recordings_per_method"]}録音・{group["planned_speakers_per_method"]}話者 / 方式</p>'
    text += f'<p>{e(denominator(primary))}</p>' + special_notes(group) + statistical_notes(group) + ranking_table(group, primary)
    conditional = group.get('conditional')
    if conditional and not conditional.get('same_as_primary'):
        text += '<details><summary>終端後に成功方式を固定した補助比較</summary>'
        text += f'<p>{e(conditional["selection"])} {e(denominator(conditional))}</p>'
        text += statistical_notes(group) + ranking_table(group, conditional) + '</details>'
    if group.get('available_case_auxiliary'):
        rows = [[e(NAMES[m]), e(number(v['value'])), e(v['valid_recordings']), e(v['valid_speakers'])]
                for m, v in group['available_case_auxiliary'].items()]
        text += '<details><summary>方式ごとの全有効録音（比較分母が異なる無順位補助）</summary>'
        text += table(['方式', '話者等重み値', '有効録音', '有効話者'], rows) + '</details>'
    auxiliary = group.get('specialized_auxiliary')
    if auxiliary:
        text += '<details open><summary>固定train校正成功方式の専用補助・無順位</summary>'
        text += f'<p>{e(auxiliary["selection"])} {e(denominator(auxiliary))}</p>'
        text += ranking_table(group, auxiliary)
        text += '<p>除外方式も状態列に残します。専用統計の区間を継承し、主全8のnullは置換しません。</p></details>'
    return text + '</section>'


def audio_section(samples):
    if not samples:
        return '<p>短い音声例はこの生成時点では未添付です。</p>'
    rows = []
    ids = {sample['case'] for sample in samples}
    if not ids <= set(PUBLIC_IDS):
        raise ValueError('公開音声は既存許諾の2録音までです')
    for sample in samples:
        if sample.get('publication_status') == 'withheld':
            rows.append([e(sample['case']), e(NAMES[sample['method']]),
                         '公開保留: ' + e(sample['reason'])])
            continue
        src = sample['data_uri']
        if (sample.get('seconds', 3) > 2 or sample.get('start_seconds') != 0
                or sample.get('existing_public_excerpt') is not True
                or sample['method'] not in PUBLIC_METHODS or not src.startswith('data:audio/wav;base64,')):
            raise ValueError('音声例は許可済み先頭最大2秒の埋込WAVだけ指定してください')
        rows.append([e(sample['case']), e(NAMES.get(sample['method'], sample['method'])),
                     f'<audio controls preload="none" src="{e(src)}"></audio>'])
    return (f'<p><a href="{e(CREDITS_NAME)}">音声の出典・帰属・変更・原文notice</a> ／ '
            '<a href="audio_samples.json">区間・標本化周波数・SHA-256</a></p>'
            '<p>音声の公開保留は数値測定の失敗ではありません。全8方式の数値順位・比較分母は維持します。'
            '各方式の先頭最大2秒を示し、全体の品質は音声例だけで判断しません。</p>'
            + table(['録音', '方式', '先頭最大2秒・公開状態'], rows))


def render(report, samples=()):
    groups = report['groups']
    first = [group for group in groups if group['id'] in ('1.native_mos', '2.scoreq', '5.ecapa', 'existing.estoi')]
    text = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    text += f'<title>全8方式の音質・制御・表現を軸別に比較</title><style>{CSS}</style><body>'
    text += '<h1>全8方式の音質・制御・表現を軸別に比較</h1><h2>現base HNM v3と既存方式の比較</h2>'
    text += '<p class="note">順位は各指標・条件・比較群の中だけで読みます。単純平均順位、総合勝者、新base採用はありません。MOSは予測値です。HNMとの差は「方式−HNM」で、良い方向は各表に示します。</p>'
    text += f'<p>作成UTC: {e(report["generated_at_utc"])}。' + ('元計画の全予定工程が終端。失敗・適用外を含みます。' if report['terminal'] else '元計画は未完了。終端した各群の結果を別々に示し、全18完成とは呼びません。') + '</p>'
    text += audio_section(samples)
    for group in first:
        text += group_section(group)
    text += '<nav><a href="#coverage">全18群の適用状態</a><a href="#methods">集約と限界</a><a href="#all-values">各条件の全値と順位</a><a href="results.json">集約JSON</a><a href="source-inventory-manifest.json">出典一覧・圧縮JSON</a></nav>'
    text += '<h2 id="coverage">全18評価群×全8方式の状態</h2>'
    rows = [[e(f'{row["family"]}. {row["label"]}'), e(row['derived_axes']),
             *[coverage_cell(row['methods'][method]) for method in METHODS]] for row in report['coverage']['rows']]
    text += table(['評価群', '派生軸数', *[NAMES[m] for m in METHODS]], rows)
    text += '<p>元計画の状態は別群の完了で変更しません。ASV100・VCTK16の状態と実分母は同じセル内に別記します。派生軸は同じ録音を繰り返し使います。軸数を独立した評価項目数、録音数、票数にはしません。状態件数は各表で示します。</p>'
    text += '<h2 id="methods">集約・区間・比較範囲</h2><ul>' + ''.join(f'<li>{e(value)}</li>' for value in report['limitations']) + '</ul>'
    text += '<h2 id="all-values">各条件の全値と順位</h2>'
    for family in [*range(1, 19), 0]:
        text += f'<h2>{e(FAMILIES.get(family, "既存音響診断・速度"))}</h2>'
        if family in (17, 18):
            text += quantization_supplement(report, family)
        for group in groups:
            if group['family'] == family and group not in first:
                text += group_section(group)
    text += '<h2>長さ・除去末尾・初期化</h2><p>native全長、16kHz派生全長、共通長、被覆率、除去された末尾、速度に含めない秒数はJSONに録音別で保存しています。共通先頭区間を全長忠実性とは呼びません。</p>'
    text += '</body></html>\n'
    return text
