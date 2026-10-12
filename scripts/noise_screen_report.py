"""固定120録音の雑音候補比較を、保存済み測定だけから公開用に集約する。"""
from collections import defaultdict
import html
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from vocoderbench import audio_samples  # noqa: E402
from vocoderbench.benchmark_io import read, sha, write  # noqa: E402
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli  # noqa: E402

LABELS = {'hnm': '現在のHNM v2', 'A': 'A：元パワーで重ね合わせ', 'B': 'B：長い合成窓',
          'C': 'C：短い合成窓', 'D': 'D：FFT端点の重み', 'E': 'E：振幅乱数を固定',
          'world_harvest': 'WORLD（Harvest）', 'identity': '原音'}
METRICS = [('mos', '予測MOS ↑', True), ('estoi', 'eSTOI ↑', True),
           ('stft', 'スペクトル誤差 dB ↓', False), ('band', '帯域誤差 dB ↓', False),
           ('envelope', '10 ms包絡誤差 ↓', False), ('level', '音量絶対誤差 dB ↓', False)]
SEED_KEYS = {'stft': 'mr_stft_db', 'band': 'band_mae_db',
             'envelope': '全帯域_10ms_rms_envelope_nrmse', 'level': 'rms_gain_error_db'}
HISTORICAL = ROOT / 'experiments/2026-10-12/noise-envelope/results/run-001'


def metric(row, key):
    if key in ('mos', 'estoi') and not any(s.get('seed') == 0 and s.get('status') == 'measured'
                                          for s in row.get('seed_diagnostics', [])):
        return None
    if key == 'mos':
        item = row.get('mos', {})
        value = item.get('value') if item.get('status') == 'measured' else None
    elif key == 'estoi':
        item = row.get('estoi', row.get('extended', {}).get('intelligibility', {}).get('estoi', {}))
        value = item.get('value') if item.get('status') == 'measured' else None
    else:
        items = row.get('seed_diagnostics', [])
        if not items or any(item.get('status') != 'measured' for item in items):
            return None
        values = [item.get('values', {}).get(SEED_KEYS[key]) for item in items]
        if any(v is None or not np.isfinite(v) for v in values):
            return None
        value = float(np.mean([abs(v) for v in values] if key == 'level' else values))
    return float(value) if value is not None and np.isfinite(value) else None


def flatten(data):
    if 'parts' not in data:
        return data.get('resynthesis', [])
    return [{**r, 'speaker': p['case']['speaker'], 'case': p['case']['id']}
            for p in data['parts'] for r in p['rows']]


def aggregate(rows, base, input_records):
    expected = defaultdict(set)
    rates = {r['id']: r['sample_rate'] for r in input_records}
    for r in input_records:
        expected[r['speaker']].add(r['id'])
    summary = {}
    for method in dict.fromkeys(r['method'] for r in rows):
        selected = [r for r in rows if r['method'] == method]
        metrics = {}
        for key, _, higher in METRICS:
            values = [v for r in selected if (v := metric(r, key)) is not None]
            diffs = defaultdict(dict)
            for r in selected:
                a, b = metric(r, key), metric(base.get(r['case'], {}), key)
                if a is not None and b is not None:
                    diffs[r['speaker']][r['case']] = a - b
            complete = [list(group.values()) for speaker, group in diffs.items()
                        if set(group) == expected[speaker]]
            means = np.asarray([np.mean(g) for g in complete])
            rng = np.random.default_rng(20261012)
            draws = means[rng.integers(len(means), size=(2000, len(means)))].mean(axis=1) if len(means) else []
            all_diffs = [x for group in diffs.values() for x in group.values()]
            metrics[key] = {'mean': float(np.mean(values)) if values else None,
                            'valid': len(values), 'planned': len(input_records),
                            'paired_cases': len(all_diffs), 'paired_complete_speakers': len(means),
                            'mean_difference': float(np.mean(means)) if len(means) else None,
                            'speaker_bootstrap_95': np.percentile(draws, [2.5, 97.5]).tolist()
                            if len(means) >= 2 else None,
                            'improved_cases': sum(v > 0 if higher else v < 0 for v in all_diffs),
                            'bootstrap_repetitions': 2000, 'bootstrap_seed': 20261012}
        seeds = [s for r in selected for s in r.get('seed_diagnostics', [])]
        valid = [s for s in seeds if s.get('status') == 'measured']
        peaks = [s.get('values', {}).get('output_peak') for s in valid]
        peaks = [p for p in peaks if p is not None]
        exceeded_cases = sum(any(s.get('values', {}).get('output_peak', 0) >= 1
                                 for s in r.get('seed_diagnostics', []) if s.get('status') == 'measured')
                             for r in selected)
        scale = [(r, s['full_scale']) for r in selected for s in r.get('seed_diagnostics', [])
                 if s.get('status') == 'measured' and s.get('full_scale')]
        total_samples = sum(s['sample_count'] for _, s in scale)
        exceeded_samples = sum(s['at_or_above_full_scale_samples'] for _, s in scale)
        summary[method] = {'rows': len(selected), 'metrics': metrics,
                           'peaks': {'valid_outputs': len(peaks), 'planned_outputs': len(input_records) *
                                     (1 if method == 'world_harvest' else 8),
                                     'at_or_above_one_outputs': sum(p >= 1 for p in peaks),
                                     'at_or_above_one_cases': exceeded_cases,
                                     'full_scale_sample_coverage': len(scale),
                                     'at_or_above_one_samples': exceeded_samples if scale else None,
                                     'at_or_above_one_fraction': exceeded_samples / total_samples if total_samples else None,
                                     'at_or_above_one_seconds': sum(s['at_or_above_full_scale_samples'] / rates[r['case']]
                                                                  for r, s in scale) if scale else None,
                                     'maximum': max(peaks) if peaks else None},
                           'failed_or_pending_seed_rows': sum(s.get('status') != 'measured' for s in seeds)}
    return summary


def number(value, signed=False):
    return '未測定' if value is None else format(value, '+.5f' if signed else '.5f')


def table(heads, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{html.escape(h)}</th>' for h in heads) + \
        '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{html.escape(str(c))}</td>' for c in row) +
                                       '</tr>' for row in rows) + '</tbody></table></div>'


def make_audio(args, data, world_data, historical, manifest, output):
    samples, missing = [], []
    records = {r['id']: r for r in manifest['entries']}
    wave_hashes = {(p['case']['id'], r['method']): r.get('waveform_sha256')
                   for p in data['parts'] for r in [p['original'], *p['rows']]}
    if not historical:
        wave_hashes.update({(p['case']['id'], r['method']): r.get('waveform_sha256')
                            for p in world_data['parts'] for r in p['rows']})
    for identifier in manifest['public_audio_example_ids']:
        entry = records[identifier]
        case = {'id': identifier, 'sr': entry['sample_rate'], 'kind': 'natural_speech'}
        for method in ('identity', 'hnm', 'A', 'B', 'C', 'D', 'E', 'world_harvest'):
            if method == 'world_harvest' and historical:
                old = read(HISTORICAL / 'audio_samples.json')['samples']
                match = [s for s in old if s['case'] == identifier and s['method'] == method]
                for sample in match:
                    samples.append({**sample, 'measurement_origin': 'historical_linux_run'})
                if not match:
                    missing.append(f'{identifier}/{method}')
                continue
            directory = args.input if method != 'world_harvest' else args.world.parent if args.world.is_file() else args.world
            path = directory / 'waveforms' / identifier / f'{method}.npy'
            if not path.exists():
                missing.append(f'{identifier}/{method}')
                continue
            if not wave_hashes.get((identifier, method)) or sha(path) != wave_hashes[identifier, method]:
                raise ValueError(f'公開音声の波形SHA不一致または記録なし: {path}')
            audio_samples.collect(samples, case, method, np.load(path, allow_pickle=False))
    audio_samples.save(samples, output)
    return samples, missing


def render(summary, status, historical, samples, missing_audio):
    groups = summary['methods']
    absolute, differences, peak_rows, uncertainty = [], [], [], []
    for method, group in groups.items():
        label = LABELS[method] + ('（過去測定）' if method == 'world_harvest' and historical else '')
        absolute.append([label] + [number(group['metrics'][k]['mean']) +
                                  (f" ({group['metrics'][k]['valid']}/120)" if group['metrics'][k]['valid'] != 120 else '')
                                  for k, _, _ in METRICS])
        if method != 'hnm':
            differences.append([label] + [number(group['metrics'][k]['mean_difference'], True) for k, _, _ in METRICS])
        p = group['peaks']
        peak_rows.append([label, f"{p['at_or_above_one_outputs']}/{p['valid_outputs']}",
                          f"{p['at_or_above_one_cases']}/120", number(p['maximum']),
                          p['at_or_above_one_samples'] if p['at_or_above_one_samples'] is not None else '未測定',
                          number(p['at_or_above_one_fraction']), number(p['at_or_above_one_seconds']),
                          f"{p['valid_outputs']}/{p['planned_outputs']}"])
        if method not in ('hnm', 'world_harvest'):
            for k, title, _ in METRICS:
                m = group['metrics'][k]
                interval = m['speaker_bootstrap_95']
                uncertainty.append([label, title, number(m['mean_difference'], True),
                                    '未測定' if interval is None else f'[{interval[0]:+.5f}, {interval[1]:+.5f}]',
                                    f"{m['improved_cases']}/{m['paired_cases']}",
                                    f"{m['paired_complete_speakers']}/40"])
    page = '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>雑音の時間形状と乱数を変える5案：固定120音声比較</title><style>
:root{color-scheme:light dark;font:16px/1.7 system-ui,sans-serif}body{max-width:1250px;margin:auto;padding:24px}h1{line-height:1.35;font-size:1.8rem}h2{font-size:1.25rem;margin-top:2rem}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:8px;border-bottom:1px solid #8886;text-align:left;white-space:nowrap}th{background:#8882}a{color:light-dark(#1554ad,#91baff)}audio{width:250px}article{display:inline-block;margin:8px;vertical-align:top}.warning{border-left:4px solid #d98616;padding:12px;background:#8881}</style>
<h1>雑音の時間形状と乱数を変える5案</h1><p>固定120録音・40話者。現在のHNM v2と5候補、既存比較対象WORLD（Harvest）。</p>'''
    page += f'<p class="warning">測定状態：{html.escape(status)}。候補を自動採用する結果ではない。</p>'
    original = summary['original_mos']
    absolute.insert(0, ['原音', number(original['mean']) + (f" ({original['valid']}/120)" if original['valid'] != 120 else '')] + ['—'] * 5)
    page += '<p>各値は固定120録音の発話平均（欠測時だけ有効件数を併記）。音響指標は発話内8 seedを先に平均、MOS・eSTOIはseed 0。音量誤差は各seedの絶対値を平均した。原音はMOSだけを掲載し、未測定項目をゼロとしない。MOSは人間評定による独立校正前の探索的予測。</p>'
    if summary.get('effective_mos_contract'):
        page += '<p>英語MOSは開始前にCPUスレッド数を予定1から4へ変更。モデル・重み・音声seed・抽出seed・反復数は維持した。WORLDと日本語補助はCPU1スレッドの別実行で、CPU実行条件まで同一とは扱わない。<a href="effective_mos_contract.json">有効MOS条件</a>と<a href="../../reviews/execution-adjustment.md">変更記録</a>を参照。</p>'
    page += table(['方式'] + [t for _, t, _ in METRICS], absolute)
    page += '<h2>現在のv2との差</h2><p>候補−現在ベース。MOS・eSTOIは正、誤差は負が改善。</p>'
    if historical:
        page += '<p class="warning">WORLDは同じ固定120音声の過去Linux実行を参照。今回のWindows実行と環境が異なり、差は参考値。今回WORLDを再測定したことや同一実行条件を意味しない。過去の結果は変更していない。</p>'
    page += table(['方式'] + [t for _, t, _ in METRICS], differences)
    page += render_audio(samples, missing_audio)
    page += '<h2>振幅上限の診断</h2><p>振幅1以上の閾値超過。聴感上の音割れを直接数えた値ではない。seed出力数と録音数を区別する。</p>'
    page += '<p>超過標本数・率・秒数は全seed出力の合計。超過秒数は複数出力の総和で、独立した録音時間ではない。欠測値は補完しない。</p>'
    page += table(['方式', '超過出力／有効出力', '超過録音／120', '最大振幅', '超過標本数', '超過標本率', '超過秒数', '有効／予定出力'], peak_rows)
    page += '<h2>対応する話者を単位にした不確かさ</h2><p>各発話のseed平均から候補−v2を計算し、3発話が揃った話者を等重みで平均。40話者を再抽出する2000回の百分位bootstrap（seed 20261012）。区間は探索的95%区間で、多候補・多指標の検定補正をしていない。seedを独立話者と数えない。欠測があれば完全な3発話が揃う話者だけを区間へ使う。</p>'
    page += table(['候補', '指標', '差の話者平均', '探索的95%区間', '改善発話／対応発話', '完全話者／40'], uncertainty)
    page += '''<h2>記録と適用範囲</h2><p>学習モデルを使わない合成器の改善候補を比較する研究。予測MOS評価器は学習モデル。正式な採否は多指標・制御性・失敗例・条件を併読して別に判断し、この表示から自動決定しない。</p>
<p><a href="results.json">全結果JSON</a> · <a href="summary.json">集計JSON</a> · <a href="contract.json">測定条件</a> · <a href="publication.json">集計・参照元SHA</a> · <a href="../jvs-run-001/index.html">日本語12録音の5候補比較</a> · <a href="../whisper-run-001/index.html">ささやきのseed診断</a> · <a href="../../reviews/control-findings.md">制御性の確認</a> · <a href="../../research.md">調査</a> · <a href="../../reviews/criteria.md">事前の比較条件</a></p></html>'''
    return page


def render_audio(samples, missing_audio):
    page = '<h2>同じ英語2録音の固定先頭2秒</h2><p>固定manifestで事前選定した2録音。位置合わせ・音量正規化・クリッピング・リサンプリングなしのfloat32 WAV。全録音の品質を2例だけで判断しない。日本語音声は公開しない。</p>'
    for identifier in dict.fromkeys(s['case'] for s in samples):
        page += f'<h3>{html.escape(identifier)}</h3>'
        for s in samples:
            if s['case'] == identifier:
                label = LABELS[s['method']] + ('（過去測定）' if s.get('measurement_origin') else '')
                page += f'<article><div>{html.escape(label)}</div><audio controls preload="none" src="{s["data_uri"]}"></audio></article>'
    if missing_audio:
        page += '<p>未取得音声：' + html.escape(', '.join(missing_audio)) + '</p>'
    return page


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--world', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/2026-10-12/noise-stability/results/run-001')
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    source = args.input / 'results.json'
    if not source.exists():
        raise FileNotFoundError('最終results.jsonがありません。未集約の途中結果は公開しません')
    data = read(source)
    parts = data.get('parts', [])
    current = flatten(data)
    input_records = data['contract']['input_records']
    planned_ids = {r['id'] for r in input_records}
    if len(planned_ids) != 120 or len({r['speaker'] for r in input_records}) != 40:
        raise ValueError('このレポートは固定120録音・40話者専用です')
    expected_pairs = {(identifier, method) for identifier in planned_ids for method in ('hnm', 'A', 'B', 'C', 'D', 'E')}
    complete = (len(current) == 720 and {(r['case'], r['method']) for r in current} == expected_pairs
                and all(r.get('status') == 'measured' and all(metric(r, k) is not None for k, _, _ in METRICS)
                        and len(r.get('seed_diagnostics', [])) == 8
                        and {s['seed'] for s in r.get('seed_diagnostics', [])} == set(range(8)) for r in current)
                and len(parts) == 120 and all(p['original'].get('mos', {}).get('status') == 'measured' for p in parts))
    if not complete and not args.allow_partial:
        raise ValueError('未完了・欠測があります。途中表示には--allow-partialを明示してください')
    historical = args.world is None
    world_path = HISTORICAL / 'results.json' if historical else args.world / 'results.json' if args.world.is_dir() else args.world
    world_data = read(world_path)
    if world_data.get('contract', {}).get('manifest_sha256') != data['contract']['manifest_sha256']:
        raise ValueError('WORLDと現在比較の固定manifest SHAが一致しません')
    world_rows = [r for r in flatten(world_data) if r['method'] == 'world_harvest']
    if any(r['case'] not in planned_ids for r in world_rows):
        raise ValueError('WORLDの録音IDが固定集合と一致しません')
    world_complete = (len(world_rows) == 120 and {r['case'] for r in world_rows} == planned_ids
                      and all(r.get('status') == 'measured' and
                              len(r.get('seed_diagnostics', [])) == 1 and
                              r['seed_diagnostics'][0].get('seed') == 0 and
                              all(metric(r, k) is not None for k, _, _ in METRICS) for r in world_rows))
    if not world_complete and not args.allow_partial:
        raise ValueError('WORLD参照に未完了・欠測があります')
    refs = {r['case']: r for r in current if r['method'] == 'hnm'}
    groups = aggregate(current + world_rows, refs, input_records)
    if historical:
        for m in groups.get('world_harvest', {}).get('metrics', {}).values():
            m['speaker_bootstrap_95'] = None
            m['comparison_scope'] = 'historical_environment_descriptive_difference_only'
    candidates = [m for m in ('A', 'B', 'C', 'D', 'E') if groups.get(m, {}).get('metrics', {}).get('mos', {}).get('valid') == 120]
    best = max(candidates, key=lambda m: groups[m]['metrics']['mos']['mean']) if candidates else None
    card = {m: groups[m] for m in ('hnm', best, 'world_harvest') if m in groups}
    summary = {'schema': 'noise-screen-summary-v1', 'methods': groups, '全体': card,
               'card_candidate': best, 'card_selection': '予測MOS平均最大の候補。採用・総合優越ではない',
               'world_origin': 'historical_linux' if historical else 'current_separate_execution'}
    original = [p['original']['mos']['value'] for p in parts if p['original'].get('mos', {}).get('status') == 'measured'
                and p['original']['mos'].get('value') is not None]
    summary['original_mos'] = {'mean': float(np.mean(original)) if original else None, 'valid': len(original)}
    effective = args.input / 'effective_mos_contract.json'
    if effective.exists():
        summary['effective_mos_contract'] = read(effective)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / 'summary.json', summary)
    data.update(schema_version=3, planned_cases=120, comparison_reference='hnm', method_labels=LABELS,
                formal_base=data['contract']['formal_base'],
                index_methods=[m for m in ('identity', 'hnm', best, 'world_harvest') if m],
                resynthesis=[{'case': r['case'], 'method': r['method'], 'status': r['status'],
                              'detail_location': 'parts' if r['method'] != 'world_harvest' else 'world_reference.rows'}
                             for r in current + world_rows],
                world_reference={'origin': summary['world_origin'], 'source_sha256': sha(world_path), 'rows': world_rows})
    if historical:
        data['method_labels'] = {**LABELS, 'world_harvest': 'WORLD（過去Linux測定）'}
    write(args.output / 'results.json', data)
    for name in ('contract.json', 'execution.json', 'mos_provenance.json'):
        if (args.input / name).exists():
            shutil.copyfile(args.input / name, args.output / name)
        if (world_path.parent / name).exists():
            shutil.copyfile(world_path.parent / name, args.output / ('world_' + name))
    if effective.exists():
        shutil.copyfile(effective, args.output / effective.name)
    write(args.output / 'publication.json', {'source_results_sha256': sha(source),
          'world_results_sha256': sha(world_path), 'generator_sha256': sha(Path(__file__)),
          'world_origin': summary['world_origin'], 'complete_current_measurements': complete})
    samples, missing = make_audio(args, data, world_data, historical, read(ROOT / 'data/clean_speech_v1.json'), args.output)
    status = '現在の6方式は測定完了' if complete and world_complete else '部分測定・未完了を含む'
    (args.output / 'index.html').write_text(render(summary, status, historical, samples, missing), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'complete': complete, 'card_candidate': best,
                      'audio_examples': len(samples), 'missing_audio': missing}, ensure_ascii=False))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'noise-screen-report'))
