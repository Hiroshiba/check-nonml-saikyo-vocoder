"""日本語HTML。HNM比較を冒頭に置き、方向・区間・状態を同じ表へ表示。"""
from __future__ import annotations

from html import escape
import json
from pathlib import PurePosixPath
from urllib.parse import urlparse

from all_metrics_common import METHODS
from all_metrics_rankings_coverage import FAMILIES

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
    result = e(text) + f'<br><small>直接値 {state.get("direct_measured", 0)}・同一性からの値 {state.get("analytic_identity", 0)}</small>'
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


def group_section(group):
    anchor = 'group-' + group['id']
    text = f'<section id="{e(anchor)}"><h3>{e(label(group))}</h3>'
    text += f'<p>{e(group.get("scope", ""))}<br>{e(group["unit"])}・{e(DIRECTION[group["direction"]])}</p>'
    if group.get('note'):
        text += f'<p class="note">{e(group["note"])}</p>'
    if group.get('observation_unit') == 'method_fixed_assets':
        rows = [[e(NAMES[r['method']]), e(number(r['value'])), e(r['status'])] for r in group['method_constants']]
        return text + '<p>方式ごとの定数です。録音へ複写せず、順位・話者区間はありません。</p>' + table(['方式', '宣言bytes', '状態'], rows) + '</section>'
    primary = group['primary']
    if group.get('planned_recordings_per_method') is not None:
        text += f'<p>予定 {group["planned_recordings_per_method"]}録音・{group["planned_speakers_per_method"]}話者 / 方式</p>'
    text += f'<p>{e(denominator(primary))}</p>' + ranking_table(group, primary)
    conditional = group.get('conditional')
    if conditional and not conditional.get('same_as_primary'):
        text += '<details><summary>終端後に成功方式を固定した補助比較</summary>'
        text += f'<p>{e(conditional["selection"])} {e(denominator(conditional))}</p>'
        text += ranking_table(group, conditional) + '</details>'
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
    if len(ids) > 2:
        raise ValueError('公開音声は既存許諾の2録音までです')
    for sample in samples:
        src = sample['src']
        parsed = urlparse(src)
        if (sample.get('seconds', 3) > 2 or sample.get('start_seconds') != 0
                or sample.get('existing_public_excerpt') is not True
                or parsed.scheme or parsed.netloc or '..' in PurePosixPath(src).parts or src.startswith('/')):
            raise ValueError('音声例は許可済み先頭2秒の公開相対pathだけ指定してください')
        rows.append([e(sample['case']), e(NAMES.get(sample['method'], sample['method'])),
                     f'<audio controls preload="none" src="{e(src)}"></audio>'])
    return table(['録音', '方式', '先頭2秒'], rows)


def render(report, samples=()):
    groups = report['groups']
    first = [group for group in groups if group['id'] in ('1.native_mos', '2.scoreq', '5.ecapa', 'existing.estoi')]
    text = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    text += f'<title>全8方式の音質・制御・表現を軸別に比較</title><style>{CSS}</style><body>'
    text += '<h1>全8方式の音質・制御・表現を軸別に比較</h1><h2>現base HNM v3と既存方式の比較</h2>'
    text += '<p class="note">順位は各指標・条件・比較群の中だけで読みます。単純平均順位、総合勝者、新base採用はありません。MOSは予測値です。HNMとの差は「方式−HNM」で、良い方向は各表に示します。</p>'
    text += f'<p>作成UTC: {e(report["generated_at_utc"])}。' + ('全予定工程が終端。失敗・適用外を含みます。' if report['terminal'] else '未完了の途中集計。未到着を0にしていません。') + '</p>'
    text += audio_section(samples)
    for group in first:
        text += group_section(group)
    text += '<nav><a href="#coverage">全18群の適用状態</a><a href="#methods">集約と限界</a><a href="#all-values">各条件の全値と順位</a><a href="results.json">集約JSON</a></nav>'
    text += '<h2 id="coverage">全18評価群×全8方式の状態</h2>'
    rows = [[e(f'{row["family"]}. {row["label"]}'), e(row['derived_axes']),
             *[e(row['methods'][method]['label']) for method in METHODS]] for row in report['coverage']['rows']]
    text += table(['評価群', '派生軸数', *[NAMES[m] for m in METHODS]], rows)
    text += '<p>派生軸は同じ録音を繰り返し使います。軸数を独立した評価項目数、録音数、票数にはしません。状態件数は各表で示します。</p>'
    text += '<h2 id="methods">集約・区間・比較範囲</h2><ul>' + ''.join(f'<li>{e(value)}</li>' for value in report['limitations']) + '</ul>'
    text += '<h2 id="all-values">各条件の全値と順位</h2>'
    for family in [*range(1, 19), 0]:
        text += f'<h2>{e(FAMILIES.get(family, "既存音響診断・速度"))}</h2>'
        for group in groups:
            if group['family'] == family and group not in first:
                text += group_section(group)
    text += '<h2>長さ・除去末尾・初期化</h2><p>native全長、16kHz派生全長、共通長、被覆率、除去された末尾、速度に含めない秒数はJSONに録音別で保存しています。共通先頭区間を全長忠実性とは呼びません。</p>'
    text += '</body></html>\n'
    return text
