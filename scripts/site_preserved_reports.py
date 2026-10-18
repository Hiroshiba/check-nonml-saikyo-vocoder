"""圧縮・分割済みの確定レポートを変換せず掲載し、保存値から一覧を作る。"""
import base64
from datetime import date
import gzip
import hashlib
import html
import json
from pathlib import Path
import shutil

from site_metric_comparison import comparison


def esc(value):
    return html.escape(str(value), quote=True)


def read_json(path):
    content = path.read_bytes()
    if path.suffix == '.gz':
        content = gzip.decompress(content)
    return json.loads(content)


def relative_file(base, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'公開相対パスが不正です: {name}')
    path = base / relative
    if not path.resolve().is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError(f'公開ファイルがありません: {name}')
    return path


def checked_bytes(path, record):
    content = path.read_bytes()
    if len(content) != record['bytes'] or hashlib.sha256(content).hexdigest() != record['sha256']:
        raise ValueError(f'公開成果の固定SHA・サイズが一致しません: {path}')
    return content


def copy_artifacts(root, output, item):
    relative = Path(item['path'])
    if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'research':
        raise ValueError('公開先はresearch内の相対パスで指定してください')
    navigation = item.get('kind') == 'navigation-only'
    source_relative = Path(item['source_path']) if navigation else relative
    source_area = 'experiments' if navigation else 'research'
    if (source_relative.is_absolute() or '..' in source_relative.parts
            or not source_relative.parts or source_relative.parts[0] != source_area):
        raise ValueError('公開元の相対パスが不正です')
    source = root / source_relative
    if (not source.resolve().is_relative_to((root / source_area).resolve())
            or source.is_symlink()):
        raise ValueError(f'研究成果の公開位置が不正です: {source}')
    manifest_path = relative_file(source, 'artifact-manifest.json')
    manifest = json.loads(checked_bytes(manifest_path, item['artifact_manifest']))
    records = [dict(item['artifact_manifest'], name='artifact-manifest.json'), *manifest['files']]
    names = [record['name'] for record in records]
    if len(names) != len(set(names)) or len(names) != item['artifact_count']:
        raise ValueError('公開成果物の重複・件数不一致があります')
    required = ({'index.html'} if navigation else
                {'index.html', 'results.json.gz', 'audio_samples.json', 'audio_credits.html'})
    if not required.issubset(names):
        raise ValueError('一覧に必要な公開成果物がありません')
    for record in records:
        name = record['name']
        if not name.endswith(('.html', '.json', '.json.gz')):
            raise ValueError(f'未定義の公開形式です: {name}')
        file = relative_file(source, name)
        content = checked_bytes(file, record)
        if len(content) >= 10 * 1024 * 1024:
            raise ValueError(f'公開単体サイズが10 MiB以上です: {name}')
        target = output / item['path'] / name
        if target.exists():
            raise ValueError(f'既存の公開先と衝突します: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        checked_bytes(target, record)
    return source


def navigation_card(item):
    """案内作成日と比較範囲だけを表示し、元の測定日時とは区別する。"""
    created_on = date.fromisoformat(item['created_on']).isoformat()
    if created_on != item['created_on']:
        raise ValueError('案内作成日はYYYY-MM-DDで指定してください')
    link = item['path'] + '/index.html'
    return (f'<article><h2><a href="{esc(link)}">{esc(item["title"])}</a></h2>'
            f'<small>案内作成：<time datetime="{created_on}">{created_on}</time>'
            '（UTCの日付。各レポートの測定・集計日時とは別）</small>'
            f'<p>{esc(item["comparison_scope"])}</p>'
            f'<p><a href="{esc(link)}">比較範囲・完了状態と元レポートを見る</a></p>'
            '</article>')


def audio_preview(source, item):
    data = read_json(source / 'audio_samples.json')
    cards = []
    for method in item['audio_methods']:
        matches = [sample for sample in data['samples']
                   if sample['case'] == item['audio_case'] and sample['method'] == method]
        if len(matches) != 1:
            raise ValueError('一覧に指定した許諾済み音声例が一意にありません')
        sample = matches[0]
        uri = sample['data_uri']
        if not uri.startswith('data:audio/wav;base64,'):
            raise ValueError('一覧の音声形式がWAVではありません')
        wave = base64.b64decode(uri.split(',', 1)[1], validate=True)
        if hashlib.sha256(wave).hexdigest() != sample['wav_sha256']:
            raise ValueError('一覧の音声SHAが保存記録と一致しません')
        if sample['start_sample'] != 0 or sample['n_samples'] / sample['sample_rate'] > 2:
            raise ValueError('一覧の音声が許諾確認済みの先頭2秒を超えています')
        label = '原音' if method == 'original' else item['method_labels'][method]
        cards.append(f'<div><p>{esc(label)}</p><audio controls preload="none" '
                     f'aria-label="{esc(label)}・先頭2秒" src="{esc(uri)}"></audio></div>')
    link = item['path']
    return ('<p>同じ録音の先頭2秒（原音・HNM・WORLD）</p><div class="audio-grid">'
            + ''.join(cards) + '</div><p><small>LibriSpeech test-clean / CC BY 4.0。'
            '切出し・解析再合成を含みます。'
            f'<a href="{esc(link)}/audio_credits.html">出典・許諾・改変表示</a> ／ '
            f'<a href="{esc(link)}/index.html">全18例を聴く</a>'
            '。GOLF-ff・SiFi-GANの追加4例は、今回の研究比較用途に限った掲載判断に基づきます。</small></p>')


def preserved_cards(root, output, recorded_time, time_label):
    registry = read_json(root / 'research/pages-reports.json')
    if registry['schema_version'] != 2:
        raise ValueError('未対応の確定レポート登録形式です')
    cards, seen = [], set()
    for item in registry['reports']:
        kind = item.get('kind', 'comparison')
        if kind not in ('comparison', 'navigation-only'):
            raise ValueError('未対応の確定レポート種別です')
        if item['path'] in seen:
            raise ValueError('確定レポートの公開位置が重複しています')
        seen.add(item['path'])
        source = copy_artifacts(root, output, item)
        if kind == 'navigation-only':
            card = navigation_card(item)
            # 日単位の案内を並べるためだけのキー。測定時刻を補完しない。
            sort_time = recorded_time({'recorded_at': item['created_on'] + 'T00:00:00+00:00'})
            cards.append((sort_time, item['path'], item['id'], card))
            continue
        data = read_json(source / 'results.json.gz')
        if data['generated_at_utc'] != item['recorded_at']:
            raise ValueError('記録日時が保存済み集計と一致しません')
        link = item['path'] + '/index.html'
        card = (f'<article><h2><a href="{esc(link)}">{esc(item["title"])}</a></h2>'
                f'<small>集計保存：{time_label(item)}</small>'
                f'<p><small>{esc(item["measurement_note"])}</small></p>'
                f'<p>{esc(item["summary"])}</p>'
                + comparison(data, item, expanded=True)
                + '<p><small>各列に比較対象と共通分母を表示しています。'
                '順位は保存済み点推定の順で、優越の確証や総合順位ではありません。'
                f'<a href="{esc(link)}">全指標・95%区間・欠測理由を見る</a></small></p>'
                + audio_preview(source, item)
                + comparison(data, item, expanded=False)
                + f'<p><a href="{esc(item["path"])}/quantization-common-window/index.html">'
                '量子化の共通窓補助を見る</a>（厳密同長の適用外を残した別解析）</p>'
                + '</article>')
        cards.append((recorded_time(item), item['path'], item['id'], card))
    return cards
