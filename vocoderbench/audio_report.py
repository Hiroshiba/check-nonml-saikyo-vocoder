"""保存した実音声を、原音と合成方式を並べて表示する。"""
from collections import defaultdict
import html
import json

from .site_summary import CURRENT_LABELS, LABELS


def section(directory, base, *, compact=False, labels=None):
    # Existing callers keep their historical labels; result renderers supply saved labels.
    labels = (CURRENT_LABELS if compact else LABELS) if labels is None else labels
    path = directory / 'audio_samples.json'
    if not path.exists():
        return '<h2>原音と各方式の音声</h2><p>この記録には音声例を保存していません。</p>'
    data = json.loads(path.read_text(encoding='utf-8'))
    groups = defaultdict(list)
    for item in data['samples']:
        if compact and item['method'] not in labels:
            continue
        groups[item['case']].append(item)
    parts = ['<h2>原音と各方式の音声</h2><p>'+html.escape(data['selection_note'])+'</p>',
             '<p>原音は無加工再合成の正解参照です。自然音声を編集した後の正解波形ではありません。'
             'ここで音声を聴けることは、新しい聴取実験や人による品質評定を実施したという意味ではありません。</p>']
    if compact:
        parts = ['<h2>同じ区間の音声を比較</h2><p>原音は無加工再合成の正解参照です。'
                 '音量の正規化はしていません。</p>']
    for case, samples in groups.items():
        parts.append('<h3>'+html.escape(samples[0]['label'])+'</h3><p><small>'+html.escape(case)+'</small></p><div class="audio-grid">')
        samples.sort(key=lambda s: (s['method'] != 'identity', s['method'] != base, s['method']))
        for item in samples:
            uri = item['data_uri']
            if not uri.startswith('data:audio/wav;base64,'):
                raise ValueError('音声例はWAVで保存してください')
            label = labels.get(item['method'], item['method'])
            if item['method'] == base:
                label += '（ベース）' if compact else '（正式ベース）'
            parts.append('<div><p>'+html.escape(label)+'</p><audio controls preload="none" aria-label="'
                         +html.escape(label, quote=True)+'" src="'+html.escape(uri, quote=True)+'"></audio>'
                         +f'<p><small>{item["n_samples"]/item["sample_rate"]:.1f}秒・{item["sample_rate"]} Hz</small></p></div>')
        parts.append('</div>')
    return ''.join(parts)
