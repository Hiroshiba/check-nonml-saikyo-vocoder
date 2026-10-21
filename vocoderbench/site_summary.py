"""一覧へ載せる比較指標と短い音声例を保存済みの記録から作る。"""
import html
import json
from statistics import median

LABELS = {'world_harvest': 'WORLD Harvest', 'world_dio': 'WORLD DIO',
          'llsm_world_dio': 'LLSM（WORLD DIOの音高）', 'identity': '原音（再合成の正解参照）'}
CURRENT_LABELS = {'apron': 'Apron（LLSM2 Layer1）', 'pml': 'PML低域拡張＋60FWCEP',
                  'hnm': '自作HNM', 'world_harvest': 'WORLD（Harvest）', 'identity': '原音'}
INDEX_METRICS = (
    ('mos', '予測MOS ↑'), ('estoi', '明瞭性 eSTOI ↑'),
    ('stft', 'スペクトル誤差 dB ↓'), ('band', '帯域の音量誤差 dB ↓'),
    ('envelope', '音量変動の誤差 ↓'), ('level', '音量差 dB ↓'),
)


def esc(value):
    return html.escape(str(value), quote=True)


def brief(results):
    data = json.loads((results / 'results.json').read_text(encoding='utf-8'))
    if data.get('study_role') == 'acg_lf_d1_first3_quality':
        return _brief_acg_first3(data, results)
    if data.get('study_role') == 'ar3_first3_development':
        return _brief_ar3_first3(data)
    if data.get('study_role') == 'd1_first3_development':
        return _brief_d1_first3(data)
    if data.get('study_role') == 'added_quality_control_metrics':
        return _brief_added_metrics(data)
    if data.get('study_role') == 'existing_references':
        from .references.report import table
        return '<p>' + esc(data['scope']) + '</p>' + table(data)
    if data.get('study_role') == 'current_base_and_references':
        return ('<p>現ベースと既存方式の固定比較。MOSはネイティブ全長、他は方式ごとの16 kHz共通先頭区間。'
                '単一合成seed。当時のベースとの差・95%区間・有効件数・被覆率は詳細に表示します。</p>'
                + _brief_expanded(data, results))
    if data.get('study_role') == 'supplement_to_completed_fixed_120':
        return _brief_supplement(data, results)
    if data.get('schema_version', 1) >= 3:
        return _brief_expanded(data, results)
    if data.get('schema_version', 1) >= 2:
        return _brief_current(data)
    rows = data['resynthesis']
    natural = any(row['kind'] == 'natural_speech' for row in rows)
    selected = [r for r in rows if (r['kind'] == 'natural_speech') == natural]
    reference = data['comparison_reference']
    body = []
    for method in dict.fromkeys(r['method'] for r in selected if r['method'] != 'identity'):
        records = [r for r in selected if r['method'] == method]
        values = []
        for r in records:
            value = r.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            if value is not None:
                values.append(value)
        failed = sum(r['status'] != 'measured' or r.get('measurement', {}).get('status') != 'ok' for r in records)
        cells = [LABELS.get(method, method), f'{median(values):.3f}' if values else '未測定',
                 f'{len(values)}/{len(records)}', failed]
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の比較。比較相手：{esc(LABELS.get(reference, reference))}。'
            '誤差は小さいほど原音に近く、知覚品質の順位ではありません。対応差は詳細に保存しています。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>スペクトル誤差中央値 dB</th>'
            '<th>有効／全件</th><th>処理・測定失敗</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def _brief_added_metrics(data):
    rows = []
    for item in data['comparison_summary']:
        if item['metric'] not in ('mos', 'speaker_ecapa', 'erb', 'scoreq'):
            continue
        cells = [item['label']]
        for method in ('hnm', 'world_harvest'):
            metric = item['methods'].get(method, {})
            value = metric.get('speaker_macro_mean')
            cells.append(f"{value:.3f}（{metric['valid_cases']}/120）" if value is not None else '未測定')
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    scoreq_count = data['scoreq_status']['measured_rows']
    return ('<p>固定120録音40話者の追加品質・制御測定。話者等重み。'
            '無編集MOSは同条件の歴史値、編集MOS・ECAPA・ERB等を追加実測。'
            f'SCOREQ有効{scoreq_count}/240件、ASRは55録音の補助集合。総合順位は作りません。</p>'
            '<div class="scroll"><table><thead><tr><th>指標</th><th>HNM v3（当時のベース）</th>'
            '<th>WORLD（Harvest）</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def _brief_supplement(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['groups']['全体']
    return _metric_table(data, summary)


def _brief_expanded(data, results):
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))['全体']
    return _metric_table(data, summary)


def _metric_table(data, summary):
    """各方式の保存済み平均値を、品質の異なる観点で並べる。"""
    rows = []
    for method, group in summary.items():
        cells = [data['method_labels'][method]]
        for key, _ in INDEX_METRICS:
            metric = group['metrics'][key]
            value = metric['mean']
            text = f'{value:.3f}' if value is not None else '未測定'
            if value is not None and metric['valid'] != data['planned_cases']:
                text += '（部分測定）'
            cells.append(text)
        rows.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    headings = '<th>方式</th>' + ''.join(f'<th>{esc(label)}</th>' for _, label in INDEX_METRICS)
    return ('<div class="scroll"><table><thead><tr>' + headings + '</tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')


def _brief_current(data):
    rows = data['resynthesis']
    natural = any(row['kind'] == 'natural_speech' for row in rows)
    selected = [r for r in rows if (r['kind'] == 'natural_speech') == natural]
    reference = data['comparison_reference']
    refs = {r['case']: r for r in selected if r['method'] == reference}
    body = []
    for method in dict.fromkeys(r['method'] for r in selected if r['method'] != 'identity'):
        records = [r for r in selected if r['method'] == method]
        values, deltas = [], []
        for row in records:
            value = row.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            base = refs.get(row['case'], {}).get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
            if value is not None:
                values.append(value)
                if base is not None:
                    deltas.append(value - base)
        failed = sum(r['status'] != 'measured' or r.get('measurement', {}).get('status') != 'ok' for r in records)
        cells = [CURRENT_LABELS.get(method, method), f'{median(values):.3f}' if values else '—',
                 f'{len(values)}/{len(records)}',
                 f'{len(deltas)}/{len(records)}', f'{failed}/{len(records)}']
        body.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in cells)+'</tr>')
    kind = '自然音声' if natural else '人工信号'
    return (f'<p>{kind}の再合成。比較相手：{esc(CURRENT_LABELS.get(reference, reference))}。対応差は詳細に保存しています。'
            '誤差は小さいほど原音に近く、知覚品質の順位ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>誤差中央値 dB</th>'
            '<th>有効／全件</th><th>比較可能／全件</th><th>失敗／全件</th>'
            f'</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def _brief_d1_first3(data):
    quality = data['quality']
    rows = []
    for method in data['index_methods']:
        if method == 'identity':
            continue
        records = [r for r in data['resynthesis'] if r['method'] == method]
        succeeded = sum(r['status'] == 'native_succeeded' for r in records)
        reused = all(r['execution_kind'] == 'prior_byte_reuse' for r in records)
        measured = sum(r['branch'] == method and r['status'] == 'measured'
                       for r in quality['records'])
        cells = [data['method_labels'][method], f'{succeeded}/{len(records)}',
                 '旧バイト再利用' if reused else '新規解析・保存・復号',
                 f'{measured}/{4*len(records)}']
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    first = data['record_ids'][0]
    scores = {(r['branch'], r['metric']): r for r in quality['records'] if r['record_id'] == first}
    values = []
    for method in data['index_methods']:
        branch = 'original' if method == 'identity' else method
        cells = [data['method_labels'][method]]
        for metric in quality['metrics']:
            row = scores.get((branch, metric['id']))
            cells.append(f"{row['value']:.6f}" if row else '対象外')
        values.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    headings = ''.join(f'<th>{esc(m["label"])}</th>' for m in quality['metrics'])
    return ('<p>同じ1話者の既観測3録音による開発比較です。品質v2は51/51個票を測定済み。'
            '4指標は一貫した改善を示さず、正式ベースはPMLを維持します。'
            '独立検証・固定120録音完了・方式採用ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>native成功／対象</th>'
            '<th>今回の処理</th><th>品質個票 有効／予定</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>'
            f'<p>以下の値は先頭ID {esc(first)} だけの保存個票です。表示は小数第6位に丸めています。'
            '原音はUTMOS参考のみで、全3録音・区間・対応差・原値は詳細に記載しています。</p>'
            '<div class="scroll"><table><thead><tr><th>条件</th>' + headings + '</tr></thead><tbody>'
            + ''.join(values) + '</tbody></table></div>'
            '<p>SCOREQだけ小さい方向、他3指標は大きい方向です。平均・順位・有意性は主張しません。'
            '旧IIRのL/F失敗を保持し、RTF（実時間比）はraw F0以降の部分計時なので旧PML過去値と速度比較できません。</p>'
            '<p>短例は掲載専用の先頭2秒で、品質測定入力ではありません。LibriSpeech / '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。'
            '変換式・出典・SHAは詳細レポートに記載しています。</p>')


def _brief_ar3_first3(data):
    quality = data['quality']
    rows = []
    for method in data['index_methods']:
        if method == 'identity':
            continue
        records = [r for r in data['resynthesis'] if r['method'] == method]
        succeeded = sum(r['status'] == 'native_succeeded' for r in records)
        reused = all(not r['newly_executed'] for r in records)
        measured = sum(r['branch'] == method and r['status'] == 'measured'
                       for r in quality['records'])
        cells = [data['method_labels'][method], f'{succeeded}/{len(records)}',
                 '保存済み参照（再解析なし）' if reused else '新規解析・保存・復号',
                 f'{measured}/{4*len(records)}']
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    first = data['record_ids'][0]
    scores = {(r['branch'], r['metric']): r for r in quality['records'] if r['record_id'] == first}
    values = []
    for method in data['index_methods']:
        branch = 'original' if method == 'identity' else method
        cells = [data['method_labels'][method]]
        for metric in quality['metrics']:
            row = scores.get((branch, metric['id']))
            cells.append(f"{row['value']:.6f}" if row else '対象外')
        values.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    headings = ''.join(f'<th>{esc(m["label"])}</th>' for m in quality['metrics'])
    return ('<p>同じ1話者の既観測3録音による開発比較です。AR3の新6枝がnative成功し、参照12枝は保存バイトを再利用。品質75/75個票は全件新規測定です。'
            '旧L/F比の変化は指標・録音で混在し、PML比では新2条件とも3録音でECAPA・eSTOI・SCOREQが劣りました。正式ベースはPMLを維持します。'
            '独立検証・固定120録音完了・方式採用ではありません。</p>'
            '<div class="scroll"><table><thead><tr><th>方式</th><th>native保存済み／対象</th>'
            '<th>今回の処理</th><th>品質個票 有効／予定</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>'
            f'<p>以下の値は先頭ID {esc(first)} だけの保存個票です。表示は小数第6位に丸めています。'
            '原音はUTMOS参考のみで、全3録音・区間・対応差・原値は詳細に記載しています。</p>'
            '<div class="scroll"><table><thead><tr><th>条件</th>' + headings + '</tr></thead><tbody>'
            + ''.join(values) + '</tbody></table></div>'
            '<p>SCOREQだけ小さい方向、他3指標は大きい方向です。平均・順位・有意性は主張しません。'
            '旧IIRのL/F失敗を保持し、RTF（実時間比）はraw F0以降の部分計時なので旧PML過去値と速度比較できません。</p>'
            '<p>短例は掲載専用の先頭2秒で、品質測定入力ではありません。LibriSpeech / '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。'
            '変換式・出典・SHAは詳細レポートに記載しています。</p>')


def _brief_acg_first3(data, results):
    first = data['record_ids'][0]
    quality = data['quality']
    scores = {(r['branch'], r['metric']): r for r in quality['records']
              if r['record_id'] == first}
    ranks = json.loads((results / data['descriptive_ranks']).read_text(encoding='utf-8'))
    positions = {(r['method'], r['metric']): r['rank'] for r in ranks['records']
                 if r['record_id'] == first}
    rows = []
    for method in data['index_methods']:
        branch = 'original' if method == 'identity' else method
        cells = ['<td>' + esc(data['method_labels'][method]) + '</td>']
        for metric in quality['metrics']:
            row = scores.get((branch, metric['id']))
            if row is None:
                cells.append('<td>対象外</td>')
                continue
            rank = positions.get((branch, metric['id']))
            text = f"{row['value']:.6f}" + ('（参考・順位外）' if rank is None else f'（{rank}位）')
            cells.append('<td>' + ('<strong>' + esc(text) + '</strong>' if rank == 1 else esc(text)) + '</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    headings = ''.join(f'<th>{esc(m["label"])}</th>' for m in quality['metrics'])
    return ('<p>同じ1話者の既知3録音による開発比較です。新ACGの品質24値と、条件照合済みの引用39値を記録しました。'
            'PML比では新L/Fの全6枝でECAPA・eSTOIが低く、SCOREQ距離が高い方向でした。'
            'UTMOSは0008・0011で低く、0032で高くなり、正式ベースはPMLを維持します。</p>'
            f'<p>以下は先頭ID {esc(first)} のみの保存値と、同じ指標・採点範囲の合成5条件内の順位です。'
            '1位を太字で示し、同値は同順位とします。順位は丸める前の原値から計算し、原音は参考として除外しました。</p>'
            '<div class="scroll"><table><thead><tr><th>条件</th>' + headings + '</tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>'
            '<p>SCOREQだけ小さい方向、他3指標は大きい方向です。全3録音の原値・48対応差・採点区間・25警告は詳細へ。'
            '従来AR3との変化は指標・録音で混在します。PMLとの差を密度だけの原因とせず、音高精度・一般化・有意差・採用は判断しません。</p>'
            '<p>18短例は既存の掲載JSONを参照する先頭2秒です。LibriSpeech / '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。品質測定にはこの掲載コピーを使っていません。</p>')


def short_audio(results, *, heading='同じ区間の音声'):
    path = results / 'audio_samples.json'
    if not path.exists():
        measurements = json.loads((results / 'results.json').read_text(encoding='utf-8'))
        if measurements.get('study_role') == 'supplement_to_completed_fixed_120':
            parent = results.parents[2] / 'noise-envelope/results/run-001'
            return short_audio(parent, heading='英語の音声例')
        return '<p><small>この過去の記録には音声例を保存していません。</small></p>'
    data = json.loads(path.read_text(encoding='utf-8'))
    measurements = json.loads((results / 'results.json').read_text(encoding='utf-8'))
    current = measurements.get('schema_version', 1) >= 2
    labels = measurements.get('method_labels', CURRENT_LABELS if current else LABELS)
    samples = data.get('samples', [])
    if measurements.get('study_role') == 'acg_lf_d1_first3_quality':
        sources = {}
        for ref in data['references']:
            name = ref['audio_json']
            if name not in sources:
                sources[name] = json.loads((results / name).read_text(encoding='utf-8'))['samples']
            found = [s for s in sources[name] if s['case'] == ref['case'] and s['method'] == ref['method']]
            if len(found) != 1:
                raise ValueError('音声参照の録音・条件が一意に対応していません')
            samples.append(found[0])
    refs = [s for s in samples if s['method'] == 'identity']
    if not refs:
        return '<p>比較できる原音の音声例がありません。</p>'
    chosen = next((s for s in refs if s['case'].startswith('librispeech_')), refs[0])
    cards = []
    if current:
        order = measurements.get('index_methods', ['candidate', 'identity', 'hnm', 'world_harvest'])
        visible = order if 'index_methods' in measurements else labels
        samples = sorted((s for s in samples if s['method'] in labels and s['method'] in visible),
                         key=lambda s: order.index(s['method']) if s['method'] in order else len(order))
    for sample in samples:
        if sample['case'] != chosen['case']:
            continue
        uri = sample['data_uri']
        if not uri.startswith('data:audio/wav;base64,'):
            raise ValueError('音声例はWAV形式で保存してください')
        cards.append(f'<div><p>{esc(labels.get(sample["method"], sample["method"]))}</p>'
                     f'<audio controls preload="none" aria-label="{esc(labels.get(sample["method"], sample["method"]))}" '
                     f'src="{esc(uri)}"></audio></div>')
    if current:
        return (f'<p>{esc(heading)}（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）</p>'
                '<div class="audio-grid">'+''.join(cards)+'</div>')
    return (f'<p>短い音声例：{esc(chosen["label"])}（{chosen["n_samples"]/chosen["sample_rate"]:.1f}秒）。'
            '同じ原音・区間を各方式で比較できます。</p><div class="audio-grid">'+''.join(cards)+'</div>')
