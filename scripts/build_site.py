"""保存済みの記録からGitHub Pages用一覧を生成し、内部リンクを検査する。"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/Hiroshiba/check-nonml-saikyo-vocoder'
CSS = '''
:root{color-scheme:light;--ink:#182f40;--accent:#116d73;--line:#d5e1e8}
body{margin:0;background:#f3f7f9;color:var(--ink);font:16px/1.8 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:40px 24px 80px}h1{font-size:clamp(26px,5vw,38px);line-height:1.4}
h2{margin-top:36px}a{color:#086777;overflow-wrap:anywhere}small{color:#506474}
article,.notice{background:white;border:1px solid var(--line);border-radius:12px;padding:20px 24px;margin:18px 0}
article h3{margin:0 0 8px}.notice{border-left:5px solid var(--accent)}code{overflow-wrap:anywhere}
li{margin:8px 0}nav{font-size:14px}footer{margin-top:40px;font-size:14px}
'''


def esc(value):
    return html.escape(str(value), quote=True)


def page(title, body):
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}'
            f'<footer>この一覧と解釈はAI作成物です。'
            f'<a href="{REPO}/blob/main/USER_INSTRUCTIONS.md">ユーザー指示</a>が優先します。'
            '</footer></main></body></html>')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def contained(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f'管理対象の外を参照しています: {relative}')
    return path


def repo_link(path, label):
    return f'<a href="{REPO}/blob/main/{esc(path)}">{esc(label)}</a>'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for name, value in attrs if name in ('href', 'src') and value)


def check_links(site):
    """ローカルファイルとリポジトリ内文書への参照を確認する。外部へ通信しない。"""
    count = 0
    for source in site.rglob('*.html'):
        parser = Links()
        parser.feed(source.read_text(encoding='utf-8'))
        for target in parser.targets:
            parts = urlsplit(target)
            prefix = REPO + '/blob/main/'
            if target.startswith(prefix):
                dest = contained(ROOT, unquote(parts.path.split('/blob/main/', 1)[1]))
            elif parts.scheme or parts.netloc or not parts.path:
                continue
            else:
                if parts.path.startswith('/'):
                    raise ValueError(f'プロジェクトの公開パスを保てない絶対リンク: {source}: {target}')
                dest = (source.parent / unquote(parts.path)).resolve()
                if not dest.is_relative_to(site.resolve()):
                    raise ValueError(f'公開フォルダの外へのリンク: {source}: {target}')
                if dest.is_dir():
                    dest /= 'index.html'
            if not dest.is_file():
                raise ValueError(f'リンク先がありません: {source}: {target}')
            count += 1
    return count


def build(output):
    # 書き出し先は固定し、誤指定による記録の削除を防ぐ。
    output = output.resolve()
    if output != ROOT / '_site':
        raise ValueError('公開用出力はリポジトリ直下の _site に限定しています')
    if output.is_symlink():
        raise ValueError('_site をシンボリックリンクにすることはできません')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    (output / '.nojekyll').write_text('')
    groups = []
    for manifest in sorted((ROOT / 'experiments').glob('*/*/experiment.json'), reverse=True):
        group = manifest.parent
        meta = read_json(manifest)
        day, topic = group.parent.name, group.name
        date.fromisoformat(day)
        if (meta['schema_version'] != 1 or meta['date'] != day or meta['topic'] != topic
                or meta['id'] != f'{day}-{topic}' or meta['timezone'] != 'Asia/Tokyo'):
            raise ValueError(f'日付・テーマ・ID・タイムゾーンが配置と一致しません: {manifest}')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', topic):
            raise ValueError(f'テーマ名は半角英小文字・数字・ハイフンで記入してください: {topic}')
        rel = group.relative_to(ROOT)
        public = output / rel
        public.mkdir(parents=True)
        shutil.copy2(manifest, public / manifest.name)
        notes = []
        for name in meta['notes']:
            note = contained(group, name)
            if not note.is_file() or note.suffix != '.md':
                raise ValueError(f'説明文書がありません: {note}')
            title = note.read_text(encoding='utf-8').splitlines()[0].lstrip('# ')
            notes.append('<li>' + repo_link(note.relative_to(ROOT), title) + '</li>')
        runs, seen = [], set()
        for run in meta['runs']:
            if not re.fullmatch(r'run-[0-9]{3,}', run['id']) or run['id'] in seen:
                raise ValueError(f'実行IDが不正または重複しています: {run["id"]}')
            seen.add(run['id'])
            if run['date'] != day or run['path'] != f'results/{run["id"]}':
                raise ValueError(f'実行日・パスが配置と一致しません: {run}')
            results = contained(group, run['path'])
            data = read_json(results / 'results.json')
            if not (results / 'index.html').is_file():
                raise ValueError(f'結果HTMLがありません: {results}')
            reference = data['comparison_reference']
            if reference not in {row['method'] for row in data['resynthesis']}:
                raise ValueError(f'比較相手の測定記録がありません: {results}')
            formal = data['formal_base']['method']
            if formal is not None and reference != formal:
                raise ValueError(f'当時のベースとの比較になっていません: {results}')
            dest = public / run['path']
            dest.mkdir(parents=True)
            for file in results.iterdir():
                if file.suffix not in ('.html', '.json') or not file.is_file():
                    raise ValueError(f'未定義の公開ファイルです: {file}')
                shutil.copy2(file, dest / file.name)
            label = '未選定' if formal is None else formal
            runs.append(f'<article><h3>{esc(run["title"])}</h3><p>{esc(run["date"])} · '
                        f'{esc(run["id"])}</p><p>当時の正式ベース：{esc(label)}。'
                        f'差分の比較相手：{esc(reference)}。</p><p>'
                        f'<a href="{esc(run["path"])}/index.html">比較結果を見る</a> ／ '
                        f'<a href="{esc(run["path"])}/results.json">全測定値（JSON）</a></p>'
                        f'<small>{esc(run.get("date_note", ""))}</small></article>')
        actual_runs = {p.name for p in (group / 'results').iterdir()} if (group / 'results').exists() else set()
        if actual_runs != seen:
            raise ValueError(f'一覧への登録がない実行結果があります: {group}')
        home = os.path.relpath(output / 'index.html', public)
        body = (f'<nav><a href="{esc(home)}">実験一覧に戻る</a></nav><h1>{esc(meta["title"])}</h1>'
                f'<p>{esc(day)}（日本時間） · {esc(topic)}</p><p>{esc(meta["summary"])}</p>'
                f'<div class="notice">状態：{esc(meta["status"])}</div><h2>調査・議論・レビュー</h2>'
                f'<ul>{"".join(notes)}</ul><h2>実行結果</h2>'
                + (''.join(runs) or '<p>調査段階です。測定結果はまだありません。</p>'))
        (public / 'index.html').write_text(page(meta['title'], body), encoding='utf-8')
        groups.append((rel, meta))
    if not groups:
        raise ValueError('公開する調査・実験グループがありません')

    library = Path('research/reference-survey')
    (output / library).mkdir(parents=True)
    for name in ('research_index_ja.html', 'research_sources.json'):
        shutil.copy2(ROOT / library / name, output / library / name)
    baseline = read_json(ROOT / 'BASELINE.json')
    shutil.copy2(ROOT / 'BASELINE.json', output / 'BASELINE.json')
    current = baseline['method'] or '未選定'
    by_date = defaultdict(list)
    for rel, meta in groups:
        by_date[meta['date']].append(f'<article><h3><a href="{rel}/index.html">{esc(meta["title"])}</a>'
                                   f'</h3><p>{esc(meta["summary"])}</p><small>テーマ：{esc(meta["topic"])}'
                                   f' · 実行記録 {len(meta["runs"])}件 · {esc(meta["status"])}</small></article>')
    body = ('<h1>非MLボコーダーの調査・実験記録</h1><p>日付とテーマから、調査・議論・比較結果を辿れます。'
            '日付は日本時間です。各実験のベース情報は測定時点のものを保持します。</p>'
            f'<div class="notice"><strong>現在の正式ベース：{esc(current)}</strong><br>'
            f'{esc(baseline["reason"])}<br><a href="BASELINE.json">現在のベース情報（JSON）</a></div>'
            f'<p>{repo_link("README.md", "プロジェクトの説明")} ／ '
            f'{repo_link("experiments/README.md", "ファイル構成と追加手順")} ／ '
            f'{repo_link("docs/STATUS.md", "現在の状態と次の作業")}</p>'
            + ''.join(f'<section><h2>{day}</h2>{"".join(cards)}</section>' for day, cards in by_date.items())
            + '<h2>共通の参考資料</h2><p><a href="research/reference-survey/research_index_ja.html">'
            '過去の調査資料一覧</a> ／ ' + repo_link('research/reference-survey/README.md', '資料の確認範囲')
            + '</p><p>過去のAI調査資料を含みます。記載された全資料を今回再確認したという意味ではありません。</p>')
    (output / 'index.html').write_text(page('非MLボコーダーの調査・実験記録', body), encoding='utf-8')
    redirects = {
        'reports/initial-comparison/index.html': 'experiments/2026-10-11/comparison-workbench/results/run-001/index.html',
        'docs/research/research_index_ja.html': 'research/reference-survey/research_index_ja.html',
    }
    for old, new in redirects.items():
        dest = output / old
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = os.path.relpath(output / new, dest.parent)
        dest.write_text(page('記録の移転先', '<h1>記録の場所が変わりました</h1>'
                             f'<p><a href="{esc(target)}">移転先の記録を開く</a></p>'), encoding='utf-8')
    count = check_links(output)
    print(f'{len(groups)} グループを生成し、{count} 件の内部リンクを確認しました: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    build(parser.parse_args().output)
