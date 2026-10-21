"""HNM現ベース対参照方式の日本語レポート。表示のために波形を再測定しない。"""
import html

from .common import read, write
from .report_metrics import BY_KEY, METRICS
from .report_summary import build_summary, prepared_rows

CSS = '''
:root{color-scheme:light dark;--bg:#f5f7fa;--fg:#182b38;--panel:#fff;--line:#cbd7df;--muted:#536675;--link:#096c75}
@media(prefers-color-scheme:dark){:root{--bg:#111b25;--fg:#e2edf5;--panel:#1a2936;--line:#456;--muted:#b4c6d2;--link:#8ddce6}}
body{background:var(--bg);color:var(--fg);font:15px/1.7 system-ui,sans-serif;margin:0}
main{max-width:1220px;margin:auto;padding:24px}h1{font-size:clamp(25px,4vw,36px);line-height:1.4}
h2{margin-top:36px}h3{margin-top:24px}a{color:var(--link)}small{color:var(--muted)}
table{border-collapse:collapse;width:100%;background:var(--panel);font-variant-numeric:tabular-nums}
th,td{padding:10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}
th:first-child,td:first-child{text-align:left}th{white-space:normal}td{min-width:110px}
.scroll{overflow:auto;margin:16px 0}.base{background:color-mix(in srgb,var(--link) 8%,var(--panel))}
.audio{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
audio{width:100%}.audio section,.note{padding:14px;background:var(--panel);border:1px solid var(--line);border-radius:8px}
.note{border-left:4px solid var(--link)}details{margin:20px 0}summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;overflow-wrap:anywhere}nav{display:flex;flex-wrap:wrap;gap:18px}.value{font-weight:650}
'''
MAIN_GROUPS = (('予測音質・明瞭性・スペクトル', ('mos', 'estoi', 'stft')),
               ('帯域の音量・時間変化・音量保持', ('band', 'envelope', 'level')),
               ('変調・F0推定整合性・振幅上限', ('modulation', 'pitch', 'voicing_loss', 'full_scale')))


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, signed=False):
    if value is None:
        return '未測定'
    if value and abs(value) < .0005:
        return f'{value:+.2e}' if signed else f'{value:.2e}'
    return f'{value:+.3f}' if signed else f'{value:.3f}'


def grid(headers, rows):
    return ('<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{esc(h)}</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def tr(cells, base=False):
    return ('<tr class="base">' if base else '<tr>') + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'


def metric_cell(metric, is_base):
    result = (f'<span class="value">{number(metric["mean"])}</span><br>'
              f'<small>有効 {metric["valid"]}/{metric["total"]}</small>')
    if is_base:
        return result + '<br><small>差分の基準</small>'
    delta = metric['difference_from_base']
    interval = delta['speaker_bootstrap_95']
    ci = f'[{number(interval[0], True)}, {number(interval[1], True)}]' if interval else '算出不能'
    return result + (f'<br>Δ {number(delta["mean_difference"], True)}<br><small>95%区間 {ci}<br>'
                     f'対比較 {delta["paired"]}/{delta["total"]}・{delta["speakers"]}話者</small>')


def metric_table(data, scope, keys):
    rows = []
    reference = data['comparison_reference']
    for method in data['selected_methods']:
        item = scope[method]
        rows.append(tr([esc(data['method_labels'][method]),
                        *(metric_cell(item['metrics'][key], method == reference) for key in keys)], method == reference))
    return grid(['方式', *(BY_KEY[key].label for key in keys)], rows)


def original_mos(item):
    return (f'<p class="note">原音の全長予測MOS：平均 {number(item["mean"])}、'
            f'中央値 {number(item["median"])}、有効 {item["valid"]}/{item["total"]}。'
            '原音は方式数に含めず、自己音響比較も追加していません。原音MOSの併記は評価器の校正ではありません。</p>')


def coverage_cell(metric):
    return f'{number(metric["mean"])} / {number(metric["minimum"])}<br><small>{metric["valid"]}/{metric["total"]}</small>'


def length_table(data, scope):
    rows = []
    for method in data['selected_methods']:
        item = scope[method]
        m = item['metrics']
        length = m['length_ms']
        cells = [esc(data['method_labels'][method]), f'{data["native_sample_rates"][method]/1000:g}',
                 f'{item["processing_success"]}/{item["planned"]}',
                 f'{item["full_length_matches"]}/{item["planned"]}',
                 f'{number(length["median"], True)}<br><small>[{number(length["minimum"], True)}, '
                 f'{number(length["maximum"], True)}]・{length["valid"]}/{length["total"]}</small>',
                 coverage_cell(m['reference_coverage']), coverage_cell(m['output_coverage']),
                 f'{number(m["rtf"]["median"])}<br><small>{m["rtf"]["valid"]}/{m["rtf"]["total"]}</small>',
                 f'{number(m["native_peak"]["maximum"])}<br><small>{m["native_peak"]["valid"]}/{m["native_peak"]["total"]}</small>']
        rows.append(tr(cells, method == data['comparison_reference']))
    return grid(['方式', '生成 kHz', '合成・音響完了/予定', '16 kHz全長一致/予定',
                 '生成長差 ms 中央値 [最小,最大]', '原音被覆率 平均/最小', '出力被覆率 平均/最小',
                 'RTF中央値 単回', 'ネイティブ全長ピーク最大'], rows)


def audio_section(data, output):
    path = output / 'audio_samples.json'
    samples = read(path).get('samples', []) if path.exists() else []
    cases = list(dict.fromkeys(row['case'] for row in samples if row['method'] == 'identity'))
    parts = []
    for index, case in enumerate(cases):
        by_method = {row['method']: row for row in samples if row['case'] == case}
        cards = []
        for method in ['identity', *data['selected_methods']]:
            sample = by_method.get(method)
            label = data['method_labels'][method]
            if not sample:
                cards.append(f'<section><p>{esc(label)}</p><p>音声例なし（未生成・未保存）</p></section>')
                continue
            if not sample['data_uri'].startswith('data:audio/wav;base64,'):
                raise ValueError('音声例はWAV形式で保存してください')
            cards.append(f'<section><p>{esc(label)} · {sample["sample_rate"]/1000:g} kHz · '
                         f'{sample["n_samples"]/sample["sample_rate"]:.2f}秒</p>'
                         f'<audio controls preload="none" aria-label="{esc(label + " " + case)}" '
                         f'src="{esc(sample["data_uri"])}"></audio></section>')
        parts.append(f'<details{" open" if index == 0 else ""}><summary>{esc(case)}</summary>'
                     '<div class="audio">' + ''.join(cards) + '</div></details>')
    return ''.join(parts) or '<p>公開可能な音声例は未保存です。</p>'


def pitch_counts(data):
    rows = prepared_rows(data)
    keys = ('total_frames', 'reference_estimated_voiced_frames', 'output_estimated_voiced_frames',
            'both_estimated_voiced_frames', 'reference_voiced_output_unvoiced_frames',
            'reference_unvoiced_output_voiced_frames', 'difference_over_600_cents_frames')
    body = []
    for method in data['selected_methods']:
        selected = [(row.get('common_prefix', {}).get('extended', {}).get('pitch_consistency') or {})
                    for row in rows if row['method'] == method]
        cells = [esc(data['method_labels'][method])]
        for key in keys:
            values = [row[key] for row in selected if isinstance(row.get(key), int)]
            cells.append(f'{sum(values)}<br><small>{len(values)}/{len(selected)}録音</small>' if values else '未測定')
        body.append(tr(cells))
    return grid(['方式', '全フレーム', '原音有声推定', '出力有声推定', '両有声推定',
                 '原音有声→出力無声', '原音無声→出力有声', '両有声で600 cent超'], body)


def missing_section(data, aggregate):
    parts = []
    for method in data['selected_methods']:
        body = []
        for metric in METRICS:
            item = aggregate['全体'][method]['metrics'][metric.key]
            reasons = '欠測なし' if not item['missing_reasons'] else '<br>'.join(
                f'{esc(reason)}：{count}録音' for reason, count in item['missing_reasons'].items())
            delta = item['difference_from_base']
            ci_reason = delta.get('ci_unavailable_reason') or '算出済み'
            body.append(tr([esc(metric.label), f'{item["valid"]}/{item["total"]}',
                            f'{delta["paired"]}/{delta["total"]}', reasons, esc(ci_reason)]))
        parts.append(f'<details><summary>{esc(data["method_labels"][method])}：全指標の有効数・欠測理由</summary>'
                     + grid(['指標', '有効/予定', '対比較可能/予定', '欠測理由', '95%区間'], body) + '</details>')
    original = aggregate['original_mos']['全体']
    reasons = original['missing_reasons']
    parts.append('<p>原音MOS：' + ('欠測なし' if not reasons else '、'.join(
        f'{esc(reason)} {count}録音' for reason, count in reasons.items())) + '</p>')
    failures = '\n\n'.join(f'{row["case"]} / {row["method"]}: '
        + str(row.get('error') or row.get('evaluation_error') or row['status'])
        for row in data['resynthesis'] if row['status'] != 'measured')
    process = '\n\n'.join(f'{p["method"]}: {p.get("error", p.get("returncode"))}; {p.get("log", "")}'
        for p in data.get('processes', []) if p.get('returncode') != 0 or p.get('error'))
    errors = '\n\n'.join(part for part in (process, failures) if part)
    return ''.join(parts) + f'<details><summary>処理失敗・ログの参照</summary><pre>{esc(errors or "処理失敗なし")}</pre></details>'


def detailed_section(data, aggregate):
    parts = []
    for family in dict.fromkeys(metric.family for metric in METRICS):
        keys = [m.key for m in METRICS if m.family == family]
        tables = ''.join(metric_table(data, aggregate['全体'], keys[i:i+3]) for i in range(0, len(keys), 3))
        parts.append(f'<details><summary>{esc(family)}：詳細の保存値</summary>{tables}</details>')
    return ''.join(parts)



def environment_note(data):
    contract = data['contract']
    host = contract.get('host_environment', {}).get('packages', {})
    reference_environments = set()
    for method, item in contract.get('prepared_methods', {}).items():
        if method in {'hnm', 'pml', 'yubiwa'}:
            continue
        env = item.get('environment', {})
        packages = dict(line.split('==', 1) for line in env.get('dependencies', '').splitlines() if '==' in line)
        reference_environments.add(f"Python {env.get('python', '未記録').split()[0]} / "
                                  f"NumPy {packages.get('numpy', '未記録')} / SciPy {packages.get('scipy', '未記録')}")
    description = (f"現ベース・音響評価・MOS：Python {contract.get('host_python', '未記録')} / "
                   f"NumPy {host.get('numpy', '未記録')} / SciPy {host.get('scipy', '未記録')}。"
                   + '参照方式の隔離環境：' + '、'.join(sorted(reference_environments))
                   + f"。合成は{contract.get('threads', '未記録')}スレッド、"
                   + f"MOSは{contract.get('mos_protocol', {}).get('cpu_threads', '未記録')}スレッド。CPU実行。")
    return '<p>' + esc(description) + '</p>'

def render(data, output):
    aggregate = build_summary(data)
    write(output / 'summary.json', aggregate)
    scope = aggregate['全体']
    planned = data['planned_cases']
    speakers = len({item['speaker'] for item in data['contract']['inputs'] if item.get('speaker')})
    original = aggregate['original_mos']['全体']
    synthesized_mos = sum(item['metrics']['mos']['valid'] for item in scope.values())
    total_mos = planned * (len(data['selected_methods']) + 1)
    version = data['formal_base'].get('version', data['comparison_reference'])
    reference_count = len(data['selected_methods']) - 1
    title = f'{version.upper().replace("-V", " v")}と既存{reference_count}方式の固定{planned}音声比較'
    comparisons = ''.join(f'<h3>{heading}</h3>{metric_table(data, scope, keys)}' for heading, keys in MAIN_GROUPS)
    attributes = []
    labels = {'F': '女性（配布属性F）', 'M': '男性（配布属性M）'}
    for name, subset in aggregate.items():
        if not name.startswith('配布属性/'):
            continue
        attribute = name.split('/', 1)[1]
        first = next(iter(subset.values()))
        tables = ''.join(f'<h3>{heading}</h3>{metric_table(data, subset, keys)}' for heading, keys in MAIN_GROUPS)
        attributes.append(f'<details><summary>{esc(labels.get(attribute, attribute))}：'
                          f'{first["planned"]}録音・{first["speakers"]}話者</summary>'
                          + original_mos(aggregate['original_mos'][name]) + tables + '</details>')
    text = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>{CSS}</style></head><body><main><h1>{esc(title)}</h1>
<p>{esc(data['generated_at'])}。当時の現ベース：{esc(version)}。新方式の採用判定ではありません。</p>
<nav><a href="#comparison">比較表</a><a href="#audio">音声</a><a href="#coverage">全長・被覆率</a>
<a href="#attributes">男女属性別</a><a href="#details">目的別詳細</a><a href="#missing">欠測</a><a href="#conditions">条件・限界</a></nav>
<section id="comparison"><h2>現ベースと既存方式の比較</h2>
<p>上段は有効録音の平均、Δは同じ録音の「各方式 − 現ベース」。各セルに有効/予定、対比較可能/予定、話者数と95%区間を示します。
↑は大きいほど、↓は小さいほどその指標上で良い値です。符号付き差や出力レベルには一律の良し悪しを付けません。</p>
<p class="note">MOSはネイティブ全長出力の予測。eSTOI以下の音響値は16 kHzへ変換した「方式ごとの原音との共通先頭区間」の補助診断です。
方式によって比較区間が異なり、欠けた末尾は音響誤差に含まれません。差分や区間推定でもこの限界は残ります。総合点・品質順位は作りません。</p>
{comparisons}{original_mos(original)}
<p>予測MOSの有効数：合成 {synthesized_mos}/{planned * len(data['selected_methods'])}、原音 {original['valid']}/{planned}、
合計 {synthesized_mos + original['valid']}/{total_mos}。欠測を0点にせず、指標ごとに分母を示します。</p></section>
<section id="audio"><h2>同じ入力区間の音声</h2>
<p>許諾された固定英語例の先頭最大2秒。ネイティブ標本化周波数のfloat32 WAVを埋め込み、音量補正・クリッピング・位置合わせはしません。
再生音量を低めから調整してください。短い例だけで全{planned}録音の品質を判断しません。</p>{audio_section(data, output)}</section>
<section id="coverage"><h2>出力全長・評価区間・速度</h2>{length_table(data, scope)}
<p>全長一致は16 kHzへ変換後の長さが原音と一致して音響比較が成立した件数です。生成長差はネイティブの出力長−入力長。
被覆率は共通先頭区間/各全長で、1が全体です。原音側の不足は末尾欠落、出力側の不足は末尾追加を示します。
RTFは解析・合成秒数÷入力秒数の単回診断で、初期化・入出力変換・評価を除外します。中央値は録音間の中央値で、反復速度測定の精度を意味しません。
現ベースは本体のPython環境、参照方式は隔離環境で実行し、Python・NumPy・PyTorchなどの版も異なります。
方式の違いだけに速度差を帰属できません。実行環境・CPU・スレッド数はresults.jsonのcontractと保存ワーカー記録を参照してください。
上表のピークはネイティブ全長出力、振幅1以上の割合は16 kHz共通区間に由来し、別の値です。</p></section>
<section id="attributes"><h2>配布元の男女属性別</h2>
<p>配布元のF/Mラベルをそのまま使います。声から性別を推測していません。各層も録音等重みで集計し、層内の話者を再抽出します。
属性間の差には話者・収録内容の違いが含まれ、性別の因果効果や他の属性への一般化は示しません。属性不明は除外せず別群にします。</p>
{''.join(attributes)}</section>
<section id="details"><h2>目的別の詳細</h2>
<p>以下は同じ保存済み測定値の内訳です。平均・中央値・最小/最大・良し悪しを定義できる指標の悪い側5%平均はsummary.jsonに保存します。
帯域ごとの符号付きdB差は正なら出力が大きく、負なら小さい値です。指標数による多数決はしません。</p>
{detailed_section(data, aggregate)}
<h3>F0推定の成立範囲</h3><p>表はフレームの合計と有効録音数です。フレームを独立話者として数えていません。
F0は絶対正解がない自然音声の推定整合性です。cent差は双方有声推定のフレームだけなので、有声の欠測・増加と併読してください。
同じYIN測定器の共通誤り、65–700 Hzの範囲、2 kHz低域前処理の影響が残ります。</p>{pitch_counts(data)}</section>
<section id="missing"><h2>全指標の欠測理由</h2><p>欠測・未実行・未定義をゼロ誤差へ置き換えません。
録音ごとの欠測理由はsummary.json、元の状態・警告・測定値はresults.jsonに保持します。</p>{missing_section(data, aggregate)}</section>
<section id="conditions"><h2>集計条件と解釈の限界</h2>{environment_note(data)}<ul>
<li>合成seedは{esc(data['contract'].get('seed'))}の1条件。以前のHNM開発比較の8 seed平均とは別実験で、混合・転記していません。
UTMOSv2の評価抽出seedは20261012、反復は1です。</li>
<li>対応差の95%区間は配布元男女属性で層化し、話者を復元抽出してその話者の有効録音対をまとめて保持するbootstrapです。
seed 20261012・2000反復・百分位区間。各反復も録音等重みです。欠測は補完せず、有効話者が2人未満・話者情報不明なら区間を出しません。
多数の比較への補正はなく、区間が0を跨がないだけで知覚品質の優越を断定しません。</li>
<li>方式ごとの短い共通区間しか比較できない場合、対応差の母集団と評価範囲が揃いません。被覆率と欠測を先に確認してください。
位置合わせ・DTW・ゲイン合わせ・無音除去は共通前処理に加えていません。eSTOI内部の公式前処理は別です。</li>
<li>今回の固定英語{speakers}話者{planned}録音は以前の開発・選択でも使用され、未使用の最終検証集合ではありません。
日本語、ささやき、裏声、多言語、独立した真値F0、48 kHz原収録音声の品質を今回評価したとは扱いません。
16 kHz素材を高い標本化周波数へ変換しても高域再現の証拠にはなりません。</li>
<li>予測MOSは既存UTMOSv2による未校正の予測で、新しい人間評定ではありません。eSTOIは明瞭性、STFTはスペクトル差、
包絡・変調は音量の時間変化を測る補助診断です。低エネルギー区間は人の無音ラベルではなく、振幅上限超過も録音時クリッピングの証明ではありません。</li>
<li>DAC：{esc('明示選択' if 'dac' in data['selected_methods'] else '未選択・未取得・未実行')}。
属性操作、特徴空間、保存形式、下流TTS、GPU・ストリーミングの品質や速度は今回の対象外です。</li></ul>
<p><a href="results.json">全測定値・固定条件</a> ／ <a href="summary.json">全指標・対応差・欠測集計</a> ／
<a href="audio_samples.json">音声例とSHA-256</a> ／
<a href="https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/CORPUS.md">音声の出典</a></p>
</section></main></body></html>'''
    (output / 'index.html').write_text(text, encoding='utf-8')
