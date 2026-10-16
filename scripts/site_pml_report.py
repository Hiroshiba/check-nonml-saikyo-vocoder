"""保存済みPML採用研究を公開一覧に追加する。本番Pages生成からだけ呼ぶ。"""
import hashlib
import html
import json
import shutil
from pathlib import Path


def pml_cards(root, output, recorded_time, time_label):
    cards = []
    for name in ['pml-fwcep-2026-10-16', 'pml-package-evaluation-2026-10-16']:
        relative = Path('research') / name
        if (root / relative / 'listing.json').is_file():
            cards.extend(pml_card(root, output, recorded_time, time_label, relative))
    return cards


def pml_card(root, output, recorded_time, time_label, relative):
    source = root / relative
    data = json.loads((source / 'listing.json').read_text())
    manifest = json.loads((source / 'artifact-manifest.json').read_text())
    destination = output / relative
    destination.mkdir(parents=True, exist_ok=True)
    for entry in manifest['files']:
        path = source / entry['name']
        if not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('PML公開素材のパスが管理対象外です')
        if path.stat().st_size != entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'PML公開素材の保存条件が一致しません: {path}')
        target = destination / entry['name']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(source / 'artifact-manifest.json', destination / 'artifact-manifest.json')
    def esc(value):
        return html.escape(str(value), quote=True)
    methods = data.get('methods', ['fwcep60', 'hnm_reference', 'world_reference'])
    rows = []
    for metric in data['metrics']:
        cells = []
        for method in methods:
            item = metric['values'].get(method, {})
            mean, rank = item.get('mean'), item.get('rank')
            if mean is None:
                cells.append(f'<td>{esc(metric.get("missing_label", "未測定"))}</td>')
            else:
                rank_html = f'<span class="rank rank-{int(rank)}">{int(rank)}位</span>' if rank is not None else ''
                cells.append(f'<td>{float(mean):.5g} {rank_html}</td>')
        rows.append(f'<tr><th>{esc(metric["label"])}</th>{"".join(cells)}</tr>')
    def metric_table(selected_rows):
        return ('<div class="scroll"><table><thead><tr><th>指標</th>'
                + ''.join(f'<th>{esc(data["method_labels"][m])}</th>' for m in methods)
                + '</tr></thead><tbody>' + ''.join(selected_rows) + '</tbody></table></div>')
    limit = data.get('expanded_metrics', len(rows))
    table = metric_table(rows[:limit])
    if limit < len(rows):
        table += ('<details><summary>音響・認識・表現・速度の指標を表示</summary>'
                  + metric_table(rows[limit:]) + '</details>')
    audios = ''.join(f'<div>{esc(a["label"])}<audio controls preload="none" src="{relative}/{esc(a["path"])}"></audio></div>' for a in data['audio'])
    mechanism = data.get('mechanism_path', 'mechanism.html')
    card = (f'<article><h2><a href="{relative}/index.html">{esc(data["title"])}</a></h2>'
            f'<small>記録：{time_label(data)}</small><p>{esc(data["summary"])}</p>'
            f'<p>{esc(data["cohort"])} 表示3方式の中だけの順位ではありません。</p>{table}'
            f'<div class="audio-grid">{audios}</div><p><a href="{relative}/{esc(mechanism)}">特徴量と仕組みの図解</a></p></article>')
    return [(recorded_time(data), str(relative), data['id'], card)]
