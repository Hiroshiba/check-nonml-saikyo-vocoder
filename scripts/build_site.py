"""保存済みの記録からGitHub Pages用一覧を生成し、内部リンクを検査する。"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vocoderbench.logging_utils import LoggedArgumentParser, configure_logging, run_cli  # noqa: E402
configure_logging('build-site')
from vocoderbench.site_summary import brief, short_audio  # noqa: E402
from site_preserved_reports import preserved_cards  # noqa: E402
from site_pml_report import pml_cards  # noqa: E402

REPO = 'https://github.com/Hiroshiba/check-nonml-saikyo-vocoder'
CSS = '''
:root{color-scheme:light dark;--ink:#182f40;--accent:#116d73;--line:#d5e1e8;--bg:#f3f7f9;--surface:#fff;--muted:#506474;--link:#086777}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:40px 24px 80px}h1{font-size:clamp(26px,5vw,38px);line-height:1.4}
h2{margin-top:36px}a{color:var(--link);overflow-wrap:anywhere}small{color:var(--muted)}
article,.notice{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 24px;margin:18px 0}
article h2,article h3{margin:0 0 8px;font-size:20px}.notice{border-left:5px solid var(--accent)}code{overflow-wrap:anywhere}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:8px;text-align:right}th:first-child,td:first-child{text-align:left}.audio-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}audio{width:100%;max-width:100%}@media(prefers-color-scheme:dark){:root{--ink:#e6edf4;--accent:#68c8c6;--line:#3b4b60;--bg:#0f1724;--surface:#182438;--muted:#b3c1d0;--link:#7fdae8}}li{margin:8px 0}nav{font-size:14px}footer{margin-top:40px;font-size:14px}
.metric-section{margin:18px 0}.metric-section summary{cursor:pointer;font-weight:700;text-decoration:underline;text-underline-offset:4px}
.metric-note{font-size:14px}.metric-comparison caption{text-align:left;font-weight:700;padding:8px 0}
.metric-comparison th{vertical-align:top}.metric-comparison small{display:inline-block;line-height:1.5;font-weight:400}
.rank{display:inline-block;white-space:nowrap;font-size:13px;padding:0 7px;border:1px solid transparent;border-radius:5px}
.rank-1,.rank-2,.rank-3{font-weight:800;border:2px solid currentColor}.rank-1{background:var(--rank-gold);border-style:double;border-width:3px}
.rank-2{background:var(--rank-silver)}.rank-3{background:var(--rank-bronze)}.metric-unavailable{color:var(--muted)}
:root{--rank-gold:#fff0b3;--rank-silver:#e8edf1;--rank-bronze:#f9e2cb}
@media(prefers-color-scheme:dark){:root{--rank-gold:#504112;--rank-silver:#35465a;--rank-bronze:#58391e}}

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


def recorded_time(run):
    """永続化した記録日時を使い、checkout時刻やファイル名で順序を変えない。"""
    value = datetime.fromisoformat(run['recorded_at'])
    if value.tzinfo is None:
        raise ValueError('記録日時にはUTCオフセットが必要です')
    return value.astimezone(timezone.utc)


def time_label(run):
    local = recorded_time(run).astimezone(ZoneInfo('Asia/Tokyo'))
    return (f'<time datetime="{esc(run["recorded_at"])}">'
            f'{local:%Y年%m月%d日 %H:%M}（日本時間）</time>')


def group_listing_time(meta):
    """初回公開、案内作成、明示されたzoneのグループ日付の順で使う。"""
    if 'published_at' in meta:
        run = {'recorded_at': meta['published_at']}
        return (recorded_time(run),
                '初回公開（Pagesデプロイ完了）：' + time_label(run))
    if 'created_at' in meta:
        run = {'recorded_at': meta['created_at']}
        return (recorded_time(run),
                '案内作成（測定時刻とは別）：' + time_label(run))
    day = date.fromisoformat(meta['date'])
    zone_name = meta['timezone']
    zone = ZoneInfo(zone_name)
    # 日頭は内部の並べ替え専用で、実時刻として保存・表示しない。
    sort_time = datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)
    zone_label = '日本時間' if zone_name == 'Asia/Tokyo' else zone_name
    label = (f'研究グループの日付：<time datetime="{esc(meta["date"])}">'
             f'{day:%Y年%m月%d日}</time>'
             f'（{esc(zone_label)}、時刻未記録。同日内の厳密な前後は不明）')
    return sort_time, label


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
    groups, reports = [], []
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
        for run in sorted(meta['runs'], key=recorded_time, reverse=True):
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
            reports.append((recorded_time(run), rel, meta, run))
            label = '未選定' if formal is None else formal
            runs.append(f'<article><h3>{esc(run["title"])}</h3><p>記録：{time_label(run)} · '
                        f'{esc(run["id"])}</p><p>当時の正式ベース：{esc(label)}。'
                        f'差分の比較相手：{esc(reference)}。</p><p>'
                        f'<a href="{esc(run["path"])}/index.html">比較結果を見る</a> ／ '
                        f'<a href="{esc(run["path"])}/results.json">全測定値（JSON）</a></p>'
                        f'<small>{esc(run.get("date_note", ""))}</small></article>')
        supplements = []
        for item in meta.get('supplements', []):
            identifier = item['id']
            if (not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identifier)
                    or identifier in seen or item['path'] != f'results/{identifier}'):
                raise ValueError(f'補助記録のID・パスが不正または重複しています: {item}')
            seen.add(identifier)
            source = contained(group, item['path'])
            read_json(source / 'results.json')
            dest = public / item['path']
            dest.mkdir(parents=True)
            for file in source.iterdir():
                if file.suffix not in ('.html', '.json') or not file.is_file():
                    raise ValueError(f'未定義の補助公開ファイルです: {file}')
                shutil.copy2(file, dest / file.name)
            entry = 'index.html' if (source / 'index.html').is_file() else 'results.json'
            supplements.append(f'<li><a href="{esc(item["path"])}/{entry}">'
                               f'{esc(item["title"])}</a></li>')
        actual_runs = {p.name for p in (group / 'results').iterdir()} if (group / 'results').exists() else set()
        if actual_runs != seen:
            raise ValueError(f'一覧への登録がない実行結果があります: {group}')
        home = os.path.relpath(output / 'index.html', public)
        body = (f'<nav><a href="{esc(home)}">実験一覧に戻る</a></nav><h1>{esc(meta["title"])}</h1>'
                f'<p>{esc(day)}（日本時間） · {esc(topic)}</p><p>{esc(meta["summary"])}</p>'
                f'<div class="notice">状態：{esc(meta["status"])}</div><h2>調査・議論・レビュー</h2>'
                f'<ul>{"".join(notes)}</ul><h2>実行結果</h2>'
                + (''.join(runs) or '<p>公開済みの測定結果はまだありません。</p>')
                + ('<h2>補助記録</h2><ul>' + ''.join(supplements) + '</ul>' if supplements else ''))
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
    method = baseline['method']
    current = ('自作HNM ' + baseline['version'].removeprefix('hnm-') if method == 'hnm'
               else 'PML低域拡張＋60FWCEP' if method == 'pml'
               else 'Apron（LLSM2 Layer1・固定120録音の品質測定済み）' if method == 'apron'
               else method or '未選定')
    cards = []
    for _, rel, meta, run in sorted(reports, key=lambda item: (item[0], str(item[1]), item[3]['id']), reverse=True):
        results = ROOT / rel / run['path']
        link = rel / run['path'] / 'index.html'
        card = (f'<article><h2><a href="{esc(link)}">{esc(run["title"])}</a></h2>'
                     f'<small>記録：{time_label(run)} · '
                     f'<a href="{esc(rel)}/index.html">調査・議論</a></small>'
                     f'<p>{esc(meta["summary"])}</p>' + brief(results) + short_audio(results)
                     + '</article>')
        cards.append((recorded_time(run), str(rel), run['id'], card))
    cards.extend(preserved_cards(ROOT, output, recorded_time, time_label))
    cards.extend(pml_cards(ROOT, output, recorded_time, time_label))
    for rel, meta in groups:
        if not meta['runs']:
            sort_time, label = group_listing_time(meta)
            card = (f'<article><h2><a href="{esc(rel)}/index.html">{esc(meta["title"])}</a></h2>'
                    f'<small>{label}</small>'
                    f'<p>{esc(meta["summary"])}（調査中・比較結果なし）</p></article>')
            cards.append((sort_time, str(rel), meta['id'], card))
    cards = [item[3] for item in sorted(cards, key=lambda item: item[:3], reverse=True)]
    body = ('<h1>非MLボコーダーの調査・実験記録</h1><p>初回公開日時を優先し、'
            '未登録なら案内作成・記録日時を使い、新しい順に並べています。'
            '時刻は日本時間です。日付だけの既存案内はUTCの日付、'
            '公開・案内作成の時刻がない研究グループは登録タイムゾーンのグループ日付を表示します。'
            '日付だけの研究グループは時刻未記録で、同日内の厳密な前後は不明です。</p>'
            f'<div class="notice"><strong>現在の正式ベース：{esc(current)}</strong><br>'
            f'{esc(baseline["reason"])}<br><a href="BASELINE.json">現在のベース情報（JSON）</a></div>'
            f'<p>{repo_link("README.md", "プロジェクトの説明")} ／ '
            f'{repo_link("experiments/README.md", "ファイル構成と追加手順")} ／ '
            f'{repo_link("docs/STATUS.md", "現在の状態と次の作業")}</p>'
            + ''.join(cards)
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


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    build(parser.parse_args().output)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'build-site'))
