"""保存済み正式PML評価から公開レポートを作る。再測定・順位再計算はしない。"""
import argparse
import copy
import gzip
import hashlib
import html
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

PML = 'pml_fwcep60_lowband_package_v1'
LABELS = {'hnm': 'HNM v3（比較時のベース）', 'world_harvest': 'WORLD Harvest',
          'facodec': 'FACodec', 'hifiglot': 'HiFi-Glot', 'golf': 'GOLF-ff',
          'sifigan': 'SiFi-GAN', 'llsm2': 'LLSM2 Layer0', 'magphase': 'MagPhase',
          PML: 'PML 低域変更＋60 FWCEP', 'pml': 'PML 低域変更＋60 FWCEP',
          'time_preservation': '無編集の時間保持（ms）', 'slope_preservation': '無編集の傾斜保持（dB/oct）',
          'unedited': '無編集', 'pitch_minus3': '音高 −3半音', 'pitch_plus3': '音高 ＋3半音',
          'gain_minus6': '音量 −6dB', 'gain_plus6': '音量 ＋6dB',
          'pitch_cents': '音高の絶対変化（cent）', 'level_db': '音量の絶対変化（dB）',
          'slope_db_per_octave': '傾斜の絶対変化（dB/oct）', 'duration_seconds': '長さの絶対変化（秒）',
          'log_f0': '対数F0の読み出し誤差', 'rms_dbfs': 'RMSの読み出し誤差（dBFS）',
          'spectral_slope': '傾斜の読み出し誤差（dB/oct）',
          'rating_spearman': '声同一性評定との順位相関', 'rated_neighbor_top1': '評定候補内の近傍一致率',
          'within_speaker/flat_stratum': '同一話者内・層平均',
          'within_speaker/x_speaker_macro': '同一話者内・X話者等重み',
          'within_speaker/nested_phone_context': '同一話者内・音素文脈の入れ子平均',
          'across_speaker/flat_stratum': '話者間・層平均',
          'across_speaker/x_speaker_macro': '話者間・X話者等重み',
          'across_speaker/nested_phone_context': '話者間・音素文脈の入れ子平均'}
CASES = ['librispeech_1089-134686-0008', 'librispeech_1188-133604-0003',
         'librispeech_121-121726-0012', 'librispeech_1221-135766-0005',
         'librispeech_1089-134686-0032']
CSS = '''body{font:16px/1.7 system-ui,sans-serif;margin:0;background:#f2f5f7;color:#16313e}main{max-width:1350px;margin:auto;padding:28px}section{padding:24px;background:#fff;border:1px solid #d5e0e5;border-radius:14px;margin:20px 0}h1{font-size:30px}a{color:#006f83}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border:1px solid #ccd9df;text-align:left}th{background:#edf3f6}small{display:block;color:#536b78;font-size:12px}.scroll{overflow:auto}.rank{display:inline-block;border:1px solid #7e8c92;border-radius:4px;padding:0 5px;font-weight:bold}.r1{background:#ffdc70;color:#342900;border:2px solid #9e7300}.r2{background:#d9e3ea;color:#243746;border:2px solid #647785}.r3{background:#eed0b5;color:#573319;border:2px solid #98613c}.audio-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}audio{display:block;width:100%;margin:8px 0}.note{border-left:4px solid #d39335;padding:14px;background:#fff5de}summary{cursor:pointer;font-weight:bold}details{margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}input{font:inherit;padding:8px;width:min(90%,600px)}.pml{font-weight:600}nav a{margin-right:16px}@media(max-width:650px){main{padding:12px}section{padding:16px}.audio-grid{grid-template-columns:1fr}}@media(prefers-color-scheme:dark){body{background:#0e1b22;color:#e5eef1}section{background:#162a35;border-color:#38505b}th{background:#203b49}td,th{border-color:#48606b}small{color:#bed0d7}a{color:#74d3e0}.note{background:#3a301d}input{background:#203b49;color:#fff}}'''


def esc(x):
    return html.escape(str(x), quote=True)


def read(path):
    return json.loads(path.read_text())


def digest(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def clean(value):
    """数値を変えずに実行機ローカルパスを論理的な出典名へ置換する。"""
    if isinstance(value, dict):
        return {clean(k): clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'/workspace/scratch/[^/]+/pml-full-evaluation-20261016/', 'evaluation/', value)
        value = re.sub(r'/workspace/scratch/[^/]+/pml-vocoder-pr-20261016/', 'repository/', value)
        value = re.sub(r'/workspace/scratch/[^/]+/', 'research-run/', value)
    return value


def write_json(path, data):
    body = json.dumps(clean(data), ensure_ascii=False, indent=2, allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(body, mtime=0) if path.suffix == '.gz' else body)


def number(x):
    return '—' if x is None else f'{x:.5g}'


def interval(row):
    ci = row.get('ci95')
    return '' if not ci else f'<small>95%区間 [{number(ci[0])}, {number(ci[1])}]</small>'


def cell(row, key='value'):
    rank = row.get('rank')
    badge = '' if rank is None else f' <span class="rank r{rank}">{rank}位</span>'
    return number(row.get(key)) + badge + interval(row)


def table(methods, key='value', difference=False):
    rows = []
    for name, row in methods.items():
        diff = row.get('hnm_difference', {})
        last = f'<td>{number(diff.get("value"))}{interval(diff)}</td>' if difference else ''
        rows.append(f'<tr class="{"pml" if name in (PML, "pml") else ""}"><th>{esc(LABELS.get(name,name))}</th><td>{cell(row,key)}</td>{last}</tr>')
    extra = '<th>HNMとの差・対応付き95%区間</th>' if difference else ''
    return '<div class="scroll"><table><thead><tr><th>方式</th><th>保存点推定・順位・95%区間</th>' + extra + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def metric_name(identifier):
    names = {'7':'音高追従', '8':'音量追従', '11':'操作干渉', '12':'編集後品質',
             '17':'量子化感度', '18':'容量と品質', 'pitch':'音高群', 'gain':'音量群',
             'relative_f0_mae':'相対音高MAE', 'missing_voiced_fraction':'YIN有声欠落率',
             'rms_frame_mae':'フレームRMS誤差', 'predicted_mos':'予測MOS',
             'speaker_similarity':'ECAPA話者類似度', 'delta_from_unedited':'無編集との差',
             'delta':'無編集との差', 'absolute_normalized_response_error':'正規化応答誤差',
             'control':'操作追従', 'erb':'同native出力とのERB距離',
             'native':'標準保存', 'payload_bitrate':'実容量レート',
             'quantized_float16':'研究float16保存', 'quantized_float32':'研究float32保存'}
    return ' / '.join(LABELS.get(t, names.get(t, t)) for t in identifier.split('.'))


def status_text(counts):
    names = {'measured':'測定済', 'partial':'部分欠測', 'unsupported':'実装未対応',
             'not_applicable':'適用外', 'upstream_failed':'前工程の失敗',
             'failed':'失敗', 'pending':'進行中', 'missing':'欠測'}
    return '、'.join(f'{names.get(k,k)} {v}' for k,v in counts.items())


def document(title, body):
    return f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style><main>{body}</main></html>'


def audio_assets(evaluation, repo, output):
    import numpy as np
    from scipy.io import wavfile
    old = repo / 'research/pml-fwcep-2026-10-16'
    saved = read(old / 'audio-samples.json')['samples']
    natives = {r['case']: r for r in read(evaluation / 'native-summary.json')['rows']}
    entries = []
    assets = output / 'assets'
    assets.mkdir(exist_ok=True)
    for case in CASES:
        for method in ['original', 'hnm', PML]:
            destination = assets / f'{case}-{method}.wav'
            if method == PML:
                record = natives[case]
                path = evaluation / 'native' / case / 'wave.npy'
                if digest(path)['sha256'] != record['audio']['sha256']:
                    raise ValueError(f'新正式音声SHA不一致: {case}')
                wave = np.load(path, allow_pickle=False)
                wavfile.write(destination, 16000, wave[:96000].astype(np.float32))
                source = {'native_wave_sha256': record['audio']['sha256'], 'seed': 0,
                          'conversion': 'float64 to FLOAT32 WAV; no gain or clipping'}
            else:
                old_method = 'hnm_reference' if method == 'hnm' else method
                sample = next(s for s in saved if s['case'] == case and s['method'] == old_method)
                shutil.copyfile(old / sample['path'], destination)
                source = {'historical_asset_sha256': digest(destination)['sha256'],
                          'conversion': '既存許諾済み同録音の掲載WAVをbyte単位で再利用'}
            sample_rate, samples = wavfile.read(destination)
            if len(samples) / sample_rate > 6.00001:
                raise ValueError('固定許諾例の6秒を超えています')
            entries.append({'case': case, 'method': method, 'path': str(destination.relative_to(output)),
                            'sample_rate': sample_rate, 'samples': len(samples), **digest(destination), **source})
    return entries


def audio_previews(media, output):
    from scipy.io import wavfile
    previews = []
    for item in media:
        if item['case'] != CASES[0]:
            continue
        rate, samples = wavfile.read(output / item['path'])
        destination = output / 'assets' / f'preview-{item["method"]}.wav'
        wavfile.write(destination, rate, samples[:2 * rate])
        previews.append({'case': item['case'], 'method': item['method'],
                         'label': '原音' if item['method'] == 'original' else LABELS[item['method']],
                         'path': str(destination.relative_to(output)), 'seconds': min(len(samples) / rate, 2),
                         'parent_wav_sha256': item['sha256'], **digest(destination)})
    return previews


def build(evaluation, repo, output):
    output.mkdir(parents=True, exist_ok=True)
    sources = {}
    def load(name):
        path = evaluation / name
        if not path.exists():
            return None
        sources[name] = digest(path)
        return read(path)
    quality = load('available-comparison.json')
    native = load('native-aggregate.json')
    timing = load('timing-cohorts.json')
    edits = load('extended/edit-summary.json')
    readout = load('extended/readout-comparison/results.json')
    abx = load('extended/abx/comparison/results.json')
    asv = load('auxiliary/human-results.json')
    unsupported = load('extended/unsupported-coverage.json')
    preservation = load('extended/preservation/aggregate.json')
    edit_ecapa = load('extended/quality/speaker_ecapa/aggregate.json')
    edit_mos = load('extended/quality/utmosv2/aggregate.json')
    common_edits = load('extended/common-comparison/results.json')
    pitch_support = load('extended/pitch-support-explanation.json')
    seeds = load('results/seed-variation/stability-summary.json')
    quant = load('extended/quantization-measurements/aggregate.json')
    quant_ecapa = load('extended/quantization-quality/speaker_ecapa/aggregate.json')
    quant_mos = load('extended/quantization-quality/utmosv2/aggregate.json')
    raw_quality = copy.deepcopy(quality)
    for group in quality['groups']:
        group.pop('raw_rows', None)
        for method in group['primary']['methods'].values():
            method.pop('speaker_means', None)
    data = {'schema_version': 1, 'evaluation_id': 'pml-package-seed0-fixed120',
            'formal_base_at_measurement': 'hnm-v3', 'adoption': 'recommended_next_research_base_in_pr43',
            'decision': {'recommendation': '次の研究baseとしてPML採用を推奨', 'current_main_base': 'hnm-v3',
                         'pr': 'https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/pull/43',
                         'scope': '全面優越や人間による品質実証ではない。予測品質と話者保持の改善を次の研究の出発点にする。'},
            'quality': quality, 'native': native, 'timing_cohorts': timing, 'edits': edits['summary'],
            'readout': readout, 'abx': abx, 'asv': asv, 'edit_ecapa': edit_ecapa, 'edit_mos': edit_mos,
            'unsupported': unsupported, 'preservation': preservation,
            'extended_common_comparison': common_edits, 'pitch_support': pitch_support, 'seed_variation': seeds, 'quantization': quant, 'quantization_ecapa': quant_ecapa, 'quantization_mos': quant_mos, 'source_files': sources}
    write_json(output / 'quality-raw.json.gz', raw_quality)
    write_json(output / 'results.json.gz', data)
    media = audio_assets(evaluation, repo, output)
    write_json(output / 'audio-samples.json', {'samples': media})
    title = '正式PMLパッケージの全追加評価：品質・制御・特徴表現'
    body = f'<h1>{title}</h1><p>固定120録音・40話者、PML package v1 / seed 0。既存8方式との同条件比較。</p>'
    body += '<nav><a href="#quality">品質比較</a><a href="#coverage">評価範囲</a><a href="#audio">音声5例</a><a href="#extended">制御・表現</a><a href="#provenance">来歴</a></nav>'
    body += '<section id="quality"><h2>まず、既存方式と比較</h2><p>HNM v3と比べて、予測MOS・明瞭性・話者類似度には改善が見られます。一方、スペクトル忠実度、音高、特徴の線形読み出しには弱点が残ります。総合順位は作りません。次の研究baseとしてPMLの採用を推奨します。無編集・編集後の予測品質と話者保持の改善を次の研究の出発点にします。現mainのbaseはHNMで、PR #43がPMLへの更新提案です。全非ML方式への全面優越や、人間による品質実証を意味しません。</p><ul><li>弱点：音高追従誤差は比較8方式中7位。特徴読み出しは音高8/9位、音量・傾斜9/9位。スペクトル忠実度にも課題が残ります。</li><li>未対応：native48kHz、時間伸縮、傾斜操作、特徴補間。欠測・失敗と区別して以下に示します。</li></ul><p></p><p>今回の固定120録音は継続比較用集合で、PML探索に用いた10録音等も含み、完全未使用のholdoutではありません。旧研究の設定選定に使わなかった追加108録音集計とは別です。旧研究seed 20261015の数値を置換していません。</p>'
    prominent = ['1.native_mos', 'existing.estoi', '2.scoreq', '5.ecapa', 'existing.erb20', 'existing.stft20.spectral_convergence', 'existing.pitch.missing_fraction']
    body += '<label>指標を絞り込む <input id="filter" type="search" placeholder="例：MOS、音高、ERB"></label>'
    secondary_opened = False
    for group in sorted(quality['groups'], key=lambda g: (g['id'] not in prominent, prominent.index(g['id']) if g['id'] in prominent else 0)):
        if group['id'] not in prominent and not secondary_opened:
            body += '<details id="more-metrics"><summary>残りの品質・音響・認識指標をすべて表示</summary>'
            secondary_opened = True
        view = group['primary']
        opened = ' open' if group['id'] in prominent[:1] else ''
        direction = {'higher': '高いほど良い', 'lower': '低いほど良い'}.get(group['direction'], '診断値・優劣なし')
        body += f'<details class="metric"{opened}><summary>{esc(group["label"])} — {esc(direction)}</summary><p>{esc(group["scope"])} 単位：{esc(group["unit"])}。共通支持 {view["common_valid_recordings"]}録音 / {view["common_valid_speakers"]}話者。</p>{table(view["methods"],difference=True)}</details>'
    if secondary_opened:
        body += '</details>'
    body += '<p>UTMOSv2は人間評定そのものではなく予測値です。ECAPAも人の話者類似性を保証しません。負の増分CERは認識器の診断で、原音より音質が高いという意味ではありません。順位は保存された競技順位です。同順位と順位の飛びを維持。点順位は有意差を保証しません。話者を2000回再抽出した区間で、合成seed変動・多重比較を含みません。ASRは全文正解のある55録音32話者、静音診断は108録音です。</p></section>'
    coverage = [('無編集品質・音響・認識', '測定済', '71軸。各軸で9方式共通の有限支持。'),
                ('解析・復号速度 / 実容量', '測定済', '120録音。解析と復号を別計時。旧計時との速度順位なし。'),
                ('音高±3半音・音量±6dB追従', '測定済', '各120録音。欠落有声・誤検出・範囲外の分母も保持。'),
                ('無編集の傾斜保持', '測定済', '120録音。傾斜を編集できるという意味ではない。'),
                ('無編集の時間保持', '部分欠測', '108件measured・12件partial。時間伸縮操作とは別。'),
                ('特徴線形読み出し / ABX', '測定済', '独立train120で尺度を固定。読み出し120 / ABX 4960三つ組。'),
                ('ASV既存人間評定との対応', '条件付き測定済', '共通80対100録音。元予定105録音の1本は未取得。'),
                ('編集後の話者類似度', '測定済', '無編集＋4編集、全長600件。主品質の共通冒頭区間と別。'),
                ('編集後の予測MOS', '測定済', '4編集×120録音。方式間順位は条件付き共通支持。'),
                ('量子化感度・話者類似度・予測MOS', '測定済', '研究用NPZでの感度。標準保存APIの量子化対応とは別。'),
                ('合成seed 0〜7の変動', '音響65軸測定済', '低コスト音響のみ。MOS/eSTOIはseed0のみで乱数安定性未確認。話者bootstrapとは別。'),
                ('時間伸縮・傾斜操作・補間', '実装未対応', 'ゼロ誤差や最下位として埋めない。'),
                ('VCTK native48kHz', '実装未対応', '凍結PMLは16kHz限定。16kへ下げて戻す代替は未実施。')]
    body += '<section id="coverage"><h2>何を測り、何が残っているか</h2><table><tr><th>評価</th><th>状態</th><th>対象・制限</th></tr>' + ''.join(f'<tr><th>{a}</th><td>{b}</td><td>{c}</td></tr>' for a,b,c in coverage) + '</table></section>'
    body += '<section id="audio"><h2>同じ5録音で聴き比べ</h2><p>各先頭最大6秒。PMLは今回の正式seed 0出力、原音・HNMは既存の同録音です。波形の音量正規化はしていません。</p>'
    for case in CASES:
        body += f'<h3>{case}</h3><div class="audio-grid">'
        for a in [a for a in media if a['case'] == case]:
            label = '原音' if a['method'] == 'original' else LABELS[a['method']]
            body += f'<div>{label}<audio controls preload="none" src="{a["path"]}"></audio></div>'
        body += '</div>'
    body += '<p><a href="audio_credits.html">音声の出典・改変・許諾</a></p></section>'
    body += '<section id="extended"><h2>特徴表現・制御性</h2><h3>特徴からの線形読み出し</h3><p>尺度・読み出し器の学習は別のdev-clean 120録音で、評価集合と話者を分離。同じ学習群と同じ目的量で比較しています。この学習群の独立性と、評価120録音が探索に未使用かどうかは別の問題です。PMLは音高8位、RMS9位、傾斜9位です。特定の線形読み出し器に対する結果で、情報が不可逆に失われた証明ではありません。</p>'
    for key, result in readout['metrics'].items():
        body += f'<details><summary>{esc(LABELS.get(key,key))} — {result["recordings"]}録音/{result["speakers"]}話者</summary>{table(result["methods"],"speaker_macro_mae")}</details>'
    body += '<h3>音素特徴ABX</h3><p>4960共通三つ組。公式部分群113録音39話者。特徴次元の標準化と特徴群の等重みは異なり、NM2049列の影響を受けます。全コーパス公式順位ではありません。</p>'
    for key, result in abx['estimands'].items():
        body += f'<details><summary>{esc(LABELS.get(key,key))} — 誤り率・小さいほど良い</summary>{table(result["methods"])}</details>'
    body += '<h3>既存の人間評定との対応（ASV）</h3><p>再合成音を人が聴いた評価ではなく、原音対への既存の声同一性評定と特徴距離の関係です。共通80対・100録音・27話者・20 anchor。MagPhaseの旧抽出は全失敗で順位外、8方式比較です。</p>'
    for key in ['rating_spearman', 'rated_neighbor_top1']:
        body += f'<details><summary>{esc(LABELS.get(key,key))} — 大きいほど良い</summary>{table({m:r[key] for m,r in asv["results"].items()})}</details>'
    body += '<h3>編集追従</h3><p>音高誤差は共通有声でのみ計算。YIN判定上の欠落有声が大きく、共通有声の誤差だけで編集成功とは判断できません。音が実際に消えたことの直接証明ではありません。旧研究の小標本約2.8centとは支持・版・集約が異なり、単純に差を取れません。基準有声は各方式の無編集再合成へのYIN判定です。同じ録音集合でもフレーム支持は方式別なので、この表には方式間順位を付けません。期待F0が測定範囲外の下157・上41フレームは欠落分母からすでに除外済みで、欠落率を範囲外だけで説明することはできません。</p><table><tr><th>操作</th><th>誤差・95%区間</th><th>欠落有声 / 期待有声フレーム</th></tr>'
    for key, row in edits['summary'].items():
        if 'speaker_macro' not in row:
            continue
        den = row.get('frame_denominators', {})
        unit = 'cent' if key.startswith('pitch') else 'dB'
        body += f'<tr><th>{esc(LABELS.get(key,key))}</th><td>{number(row["speaker_macro"])} {unit}{interval(row)}</td><td>{den.get("missing_voiced_frames","—")} / {den.get("expected_voiced_frames","—")}</td></tr>'
    body += '</table><p>全分母・範囲外・誤検出・干渉は保存JSONに収録。</p>'
    body += '<h3>無編集の時間・傾斜保持</h3><p>時間は検出できた1966/1978イベント上の録音MAEを話者等重み。部分欠測12録音も検出イベントだけで寄与し、未検出12イベントをゼロ誤差にしません。時間伸縮や傾斜編集への対応ではありません。</p>'
    body += table(preservation['metrics'], 'speaker_macro_mae')
    body += '<h3>編集後のECAPA話者類似度</h3><p>全長で原音を話者参照に使用。音高ターゲットの正しさや人間の話者同一性そのものを表しません。主品質表の共通冒頭区間の値とは別条件です。</p>'
    body += table(edit_ecapa['by_condition'], 'speaker_macro_mean')
    body += '<h3>編集後の予測MOS</h3><p>各編集120録音40話者。目標音程の正しさはこの予測値では評価できないため、追従誤差と欠落率を併せて確認します。</p>'
    body += table(edit_mos['by_condition'], 'speaker_macro_mean') + '</section>'
    body += '<section><h2>編集・量子化も、同じ録音支持で既存方式と比較</h2><p>以下は対応する既存方式すべての有効録音の共通集合へ揃えた条件付き比較です。上のPML単独120録音の表とは支持が異なります。例えば−3半音追従MAEは共通106録音、欠落率は107録音です。共通なのは録音であり、YIN有声フレームは方式別です。</p><p>一部の方式に未対応・適用外・前工程失敗がある群は、その状態と分母を明記します。順位を良くするために方式を選別していません。編集比較は編集非対応のFACodecを除く8方式なので、同じ無編集PMLの予測MOSでも主品質の3/9位に対して2/8位となります。比較対象集合の違いであり、品質が変わったわけではありません。量子化の保存表現・容器は方式ごとに異なり、同じビットレートでの比較ではありません。</p>'
    body += '<details><summary>編集・量子化の全61比較群を表示</summary>'
    for g in common_edits['groups']:
        body += f'<details><summary>{esc(metric_name(g["id"]))}</summary>'
        if g['status'] != 'measured':
            body += '<p>追加測定中。確定順位なし。</p></details>'
            continue
        direction = {'higher': '高いほど良い', 'lower': '低いほど良い'}.get(g['direction'], '診断値')
        body += f'<p>{direction}。単位：{esc(g["unit"])}。共通 {g["common_recordings"]}録音 / {g["common_speakers"]}話者、{len(g["included_methods"])}方式。</p>'
        body += table(g['methods'])
        body += '<details><summary>各方式の測定・欠測状態</summary><ul>'
        body += ''.join(f'<li>{esc(LABELS.get(m,m))}：{esc(status_text(c))}</li>' for m,c in g['status_counts'].items())
        body += '</ul></details></details>'
    body += '</details></section>'
    body += '<section><h2>保存精度を落とした場合の感度</h2><p>F0とFWCEPをfloat16またはfloat32で研究用NPZへ実保存し、読み戻して復号しました。NMビット列等は保持。標準.pml形式の変更・量子化APIの実装ではありません。容量差には容器の違いも含みます。各120録音40話者です。</p><table><tr><th>研究保存精度</th><th>実NPZ容量</th><th>同じnative出力とのERB距離（dB）</th><th>ECAPA（原音参照・全長）</th><th>予測MOS</th></tr>'
    for precision, row in quant['precisions'].items():
        body += f'<tr><th>{precision}</th><td>{number(row["research_npz_capacity"]["actual_kbps"])} kbps</td><td>{number(row["auditory"]["speaker_macro"])}{interval(row["auditory"])}</td><td>{number(quant_ecapa["by_condition"][precision]["speaker_macro_mean"])}{interval(quant_ecapa["by_condition"][precision])}</td><td>{number(quant_mos["by_condition"][precision]["speaker_macro_mean"])}{interval(quant_mos["by_condition"][precision])}</td></tr>'
    body += '</table><p>ERB距離は元の非量子化PML出力との差で、原音への忠実度や可聴限界ではありません。float16の予測MOS差は無編集に対して約＋0.019ですが、対応差の95%区間は0を跨ぎ、品質改善とは断定できません。float16とfloat32の方式順位は比較対象と支持が異なるため直接比較しません。</p>'
    for precision, row in quant['precisions'].items():
        body += f'<details><summary>{precision}：属性変化と編集追従</summary><p>属性変化は同じnative出力との差。音高の比較支持は条件ごとに変わり得るため、誤差だけを直接比較しません。分母はJSONに保存。</p>{table(row["absolute_attribute_changes"],"speaker_macro")}{table(row["controls"],"speaker_macro")}</details>'
    body += '</section>'
    body += '<section><h2>合成乱数seed 0〜7の変動</h2><p>同じ解析済み特徴から合成乱数だけを変えた8反復。録音ごとに固定8seedの平均・母標準偏差・最大−最小を計算し、話者内平均の後に話者等重みで集約しました。65軸を測定、静音3軸のみ108録音、その他120録音です。</p><p>これは固定8seed内の変動の記述であり、CIではありません。seedを独立録音として標本数に加えず、新しい順位も付けません。MOS・eSTOIはseed 0のみのため、それらの乱数安定性は未確認です。</p><details><summary>65軸の乱数変動を表示</summary><table><tr><th>指標 / 単位</th><th>完全支持 録音/話者</th><th>平均</th><th>録音内母標準偏差の集約</th><th>録音内範囲の集約</th></tr>'
    for g in seeds['groups']:
        v = g['speaker_equal_weight']
        body += f'<tr><th>{esc(g["label"])} / {esc(g["unit"])}</th><td>{g["complete_recordings"]} / {g["complete_speakers"]}</td><td>{number(v["mean"])}</td><td>{number(v["standard_deviation"])}</td><td>{number(v["range"])}</td></tr>'
    body += '</table></details></section>'
    body += '<section><h2>速度と容量</h2><table><tr><th>固定70・解析RTF</th><th>固定70・復号RTF</th><th>主120・解析RTF</th><th>主120・復号RTF</th></tr><tr>'
    for cohort in ['fixed70', 'main120']:
        for stage in ['analysis', 'decode']:
            body += f'<td>{number(timing["cohorts"][cohort][stage]["speaker_equal_weight_rtf"])}</td>'
    body += '</tr></table><p>録音RTF→話者内平均→話者等重み。固定70は旧公開と同じ70録音24話者・353.14秒、主120は120録音40話者・615.935秒です。以前示した総処理秒÷総音声秒（時間加重）とは集計式が異なり、混在させていません。</p>'
    body += '<p>初回import等を含む1回逐次測定、保存/読み込みは別計時で除外。共有ホスト負荷は制御外。旧方式は初期化を除外した別計時なので速度順位は付けません。同じ70IDでも実行条件が同じという意味ではありません。</p>'
    body += f'<p>標準形式の実保存量 {native["payload_bytes"]:,} B、{number(native["payload_kbps"])} kbps。16kHz・16bit PCMの256 kbpsより大きく、低ビットレート音声コーデックとは呼べません。</p><p>4録音60試料が|振幅|&gt;1、最大約1.427。科学計測は浮動小数でクリップせず行いました。</p></section>'
    body += '<section id="provenance"><h2>来歴と再現</h2><p><a href="results.json.gz">集約・制御・部分欠測JSON</a> ／ <a href="quality-raw.json.gz">71軸の保存個票・集約</a> ／ <a href="provenance.json">ソース・契約SHA</a> ／ <a href="input-manifest.json">入力manifest</a> ／ <a href="REPRODUCE.md">再現手順</a></p><p>新PMLだけを今回再計測し、既存方式は同入力・同評価器を照合した保存値を引用。旧研究の図と探索経過は<a href="../pml-fwcep-2026-10-16/mechanism.html">特徴量と仕組みの説明</a>および<a href="../pml-fwcep-2026-10-16/index.html">旧研究レポート</a>へ。そちらの音声・図・seed・支持集合は今回の正式評価とは異なります。</p><p>評価実行は既存環境を再利用。PRのuv.lockから環境を完全再構築した実行ではありません。旧MOS推論は4 threads、新MOSは2 threadsで、setuptools等にも環境差があります。評価器・モデル・音声窓・seed契約は照合していますが、実行環境全体のビット単位同一性は主張しません。小さい点推定差の順位は有意優越を意味しません。依存差と固定実装SHAは来歴JSONへ記録。PRでのbase更新提案と、48kHz・未対応操作の研究完了は別です。今回の採用推奨は残る課題を解決したという意味ではありません。</p></section>'
    body += '''<script>document.getElementById('filter').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('.metric').forEach(x=>{x.hidden=!x.textContent.toLowerCase().includes(q);if(q)x.open=!x.hidden});if(q)document.getElementById('more-metrics').open=true})</script>'''
    (output / 'index.html').write_text(document(title,body))
    credits = '<h1>固定5例の出典・改変</h1><p>LibriSpeech test-clean / OpenSLR 12。Vassil Panayotov（Daniel Povey協力）、LibriVox由来。<a href="https://www.openslr.org/12">配布元</a>、<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。録音IDは各欄に記載。先頭最大6秒の抜粋です。</p><p>原音とHNMは既存許諾確認済み掲載WAVをそのまま再利用。新PMLは16kHz解析・seed 0再合成、FLOAT32 WAVへ変換。音量正規化・クリップなし。過去の掲載WAVはPCM16変換です。著者が今回の改変を推奨しているという意味ではありません。</p>'
    (output / 'audio_credits.html').write_text(document('音声の出典と改変',credits))
    provenance = {'source_files': sources, 'package': load('package-source-provenance.json'),
                  'runtime': load('runtime-vs-pr-dependencies.json'),
                  'native_contract': load('native-contract.json'),
                  'quantization_contract': load('extended/quantization/contract.json'),
                  'mos_reuse': load('extended/mos-reuse-provenance.json'),
                  'publication': '固定5例の短音声のみ。全長コーパス・重み・私有保存先は含めない。'}
    write_json(output / 'provenance.json', provenance)
    metrics = []
    for g in quality['groups']:
        if g['id'] in prominent or g['id'].startswith('4.'):
            metrics.append({'key':g['id'],'label':g['label'], 'values':{m:{'mean':r['value'],'rank':r['rank']} for m,r in g['primary']['methods'].items()}})
    for key, result in readout['metrics'].items():
        metrics.append({'key': 'readout.' + key, 'label': LABELS[key] + '（120録音・9法）',
                        'values': {m: {'mean': r['speaker_macro_mae'], 'rank': r['rank']} for m, r in result['methods'].items()}})
    for key in ['within_speaker/flat_stratum', 'across_speaker/flat_stratum']:
        metrics.append({'key': 'abx.' + key, 'label': 'ABX ' + LABELS[key] + '（9法）',
                        'values': {(PML if m == 'pml' else m): {'mean': r['value'], 'rank': r['rank']} for m, r in abx['estimands'][key]['methods'].items()}})
    for key in ['rating_spearman', 'rated_neighbor_top1']:
        metrics.append({'key': 'asv.' + key, 'label': LABELS[key] + '（80対・8法）',
                        'values': {m: {'mean': r[key]['value'], 'rank': r[key]['rank']} for m, r in asv['results'].items()}})
    for cohort, cohort_label in [('fixed70', '固定70'), ('main120', '主120')]:
        for stage, stage_label in [('analysis', '解析'), ('decode', '復号')]:
            metrics.append({'key': f'{cohort}.{stage}', 'label': f'{cohort_label}・{stage_label}RTF（話者等重み）',
                            'missing_label': '別計時・順位なし',
                            'values': {PML: {'mean': timing['cohorts'][cohort][stage]['speaker_equal_weight_rtf'], 'rank': None}}})
    metrics.append({'key': 'payload_kbps', 'label': '標準実容量 kbps', 'missing_label': '詳細の容量比較を参照',
                    'values': {PML: {'mean': native['payload_kbps'], 'rank': None}}})
    first_metrics = ['1.native_mos', '2.scoreq', '5.ecapa', 'existing.estoi', 'existing.erb20']
    metrics.sort(key=lambda m: first_metrics.index(m['key']) if m['key'] in first_metrics else len(first_metrics))
    listing = {'id': output.name, 'path': f'research/{output.name}', 'recorded_at': datetime.now(UTC).isoformat(),
               'title': title, 'summary':'正式package seed 0の120録音評価。品質改善と制御・表現の弱点を併記。次の研究baseとしてPML採用を推奨。予測品質・話者保持の改善と、音高追従・特徴読み出し等の弱点を併記。現mainはHNM、PR #43は更新提案。',
               'cohort':'品質は軸別9方式共通支持。ASR55、静音108、その他120録音。',
               'expanded_metrics': 5, 'method_labels':LABELS, 'methods':[PML,'hnm','world_harvest'], 'metrics':metrics,
               'audio': audio_previews(media, output),
               'audio_case':CASES[0], 'mechanism_path':'../pml-fwcep-2026-10-16/mechanism.html'}
    write_json(output / 'listing.json',listing)
    manifest = {'schema_version':1, 'scope':'新正式package測定・固定5短例・保存値。次の研究baseとしてPML採用推奨、PR更新提案。',
                'files':[{'name':str(p.relative_to(output)),**digest(p)} for p in sorted(output.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json']}
    write_json(output / 'artifact-manifest.json',manifest)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--evaluation',type=Path,required=True)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.evaluation,args.repository,args.output)
