"""既存方式だけの比較表。方式の品質順位やベース採用を宣言しない。"""
import html
from statistics import mean, median

from .common import read, write

CSS = '''
:root{color-scheme:light dark;--bg:#f5f7fa;--fg:#182b38;--panel:#fff;--line:#cbd7df}
@media(prefers-color-scheme:dark){:root{--bg:#111b25;--fg:#e2edf5;--panel:#1a2936;--line:#456}}
body{background:var(--bg);color:var(--fg);font:15px/1.8 system-ui,sans-serif;margin:0}
main{max-width:1180px;margin:auto;padding:28px}table{border-collapse:collapse;width:100%;background:var(--panel)}
th,td{padding:10px;border-bottom:1px solid var(--line);text-align:right}th:first-child,td:first-child{text-align:left}
.scroll{overflow:auto}.audio{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
audio{width:100%}a{color:inherit}details{margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}
'''


def esc(value):
    return html.escape(str(value), quote=True)


def numeric(row, metric):
    if metric == 'mos':
        return row.get('mos', {}).get('value')
    if metric == 'rtf':
        return row.get('rtf')
    common = row.get('common_prefix', {})
    if metric == 'stft':
        return common.get('measurement', {}).get('mr_stft_log_magnitude_mae_db')
    if metric == 'estoi':
        return (common.get('extended', {}).get('intelligibility') or {}).get('estoi', {}).get('value')
    if metric == 'length_ms' and 'length_delta_samples' in row:
        return 1000 * row['length_delta_samples'] / row['native_sample_rate']
    return None


def summary(data):
    result = {}
    for method in data['selected_methods']:
        rows = [r for r in data['resynthesis'] if r['method'] == method]
        item = {'planned': data['planned_cases'], 'completed': sum(r['status'] == 'measured' for r in rows),
                'full_length_matches': sum(r.get('measurement', {}).get('status') == 'ok' for r in rows),
                'metrics': {}}
        for key in ('mos', 'estoi', 'stft', 'rtf', 'length_ms'):
            values = [numeric(r, key) for r in rows if r['status'] == 'measured']
            values = [value for value in values if value is not None]
            item['metrics'][key] = {'mean': mean(values) if values else None,
                                     'median': median(values) if values else None, 'valid': len(values)}
        result[method] = item
    return result


def table(data):
    rows = []
    for method, item in summary(data).items():
        cells = [data['method_labels'][method], f"{data['native_sample_rates'][method]/1000:g}",
                 f"{item['completed']}/{item['planned']}"]
        for key in ('rtf', 'mos', 'estoi', 'stft', 'length_ms'):
            metric = item['metrics'][key]
            value = metric['median'] if key in ('rtf', 'length_ms') else metric['mean']
            cells.append('未測定' if value is None else f'{value:.3f} ({metric["valid"]}/{item["planned"]})')
        rows.append('<tr>' + ''.join('<td>' + esc(c) + '</td>' for c in cells) + '</tr>')
    labels = ['方式', '標本化周波数 kHz', '完了/予定', 'RTF中央値 ↓', '予測MOS平均 ↑',
              '共通区間eSTOI ↑', '共通区間STFT dB ↓', '生成長差 ms']
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>' + esc(x) + '</th>' for x in labels) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def render(data, output):
    write(output / 'summary.json', summary(data))
    audio = read(output / 'audio_samples.json') if (output / 'audio_samples.json').exists() else {'samples': []}
    sample_rows = audio['samples']
    chosen = next((r['case'] for r in sample_rows if r['method'] == 'identity'), None)
    audio_html = '<div class="audio">' + ''.join(
        f'<section><p>{esc(data["method_labels"][row["method"]])}</p>'
        f'<audio controls preload="none" src="{esc(row["data_uri"])}"></audio></section>'
        for row in sample_rows if row['case'] == chosen) + '</div>'
    failures = '\n\n'.join(f'{row["case"]} / {row["method"]}: ' + row.get('error', row.get('evaluation_error', ''))
                             for row in data['resynthesis'] if row['status'] != 'measured')
    process_errors = '\n'.join(f'{p["method"]}: {p.get("error", p.get("returncode"))}; {p.get("log", "")}'
                               for p in data.get('processes', []) if p.get('returncode') != 0 or p.get('error'))
    failures = '\n\n'.join(v for v in (process_errors, failures) if v)
    text = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>既存方式の再合成比較</title>
<style>{CSS}</style></head><body><main><h1>既存方式の再合成比較</h1>
<p>{esc(data['scope'])}。{esc(data['generated_at'])}。自作ベースの測定・採用判定は行いません。</p>
{table(data)}
<p>RTFは解析・合成秒数÷音声秒数。初期化、リサンプリング、評価を除外した単回値の中央値です。
複数回の速度測定はPR #24を参照してください。標本化周波数・保持情報量が異なるため音質を揃えた順位ではありません。</p>
<h2>同じ入力区間の音声</h2><p>各方式のネイティブ出力の先頭最大2秒。音量補正なし。</p>{audio_html}
<h2>全長と補助指標を区別</h2><p>生成音声の長さを切り詰めたりゼロ埋めして保存しません。
全長比較の状態・長さ差をJSONへ記録し、表のeSTOI/STFTは入力帯域にリサンプリングした共通先頭区間の補助値です。
位置合わせ・時間伸縮・ゲイン補正なし。区間外の欠落を品質合格として扱いません。
予測MOSは各ネイティブ全長出力を既存UTMOSv2へ渡した未校正の予測で、新規の人間評定ではありません。</p>
<p>DAC: {esc('明示指定により追加' if 'dac' in data['selected_methods'] else '任意・未選択（取得・実行なし）')}。
操作性・特徴空間・下流学習・GPU速度は本実行の測定対象外です。</p>
<p><a href="results.json">全測定値・条件</a> ／ <a href="summary.json">集計</a> ／ <a href="audio_samples.json">音声例</a></p>
<details><summary>失敗と欠測</summary><pre>{esc(failures or '処理失敗なし。個別指標の未測定は表・JSONを参照。')}</pre></details>
</main></body></html>'''
    (output / 'index.html').write_text(text, encoding='utf-8')
