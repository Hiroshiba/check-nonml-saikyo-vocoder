"""圧縮・分割済みの確定レポートを変換せず掲載し、保存値から一覧を作る。"""
import base64
from datetime import date
import gzip
import hashlib
import html
import io
import json
from pathlib import Path, PurePosixPath
import shutil
from urllib.parse import quote
import wave

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
    source_areas = ('experiments', 'research') if navigation else ('research',)
    if (source_relative.is_absolute() or '..' in source_relative.parts
            or not source_relative.parts or source_relative.parts[0] not in source_areas):
        raise ValueError('公開元の相対パスが不正です')
    source_area = source_relative.parts[0]
    source = root / source_relative
    if (not source.resolve().is_relative_to((root / source_area).resolve())
            or source.is_symlink()):
        raise ValueError(f'研究成果の公開位置が不正です: {source}')
    manifest_path = relative_file(source, 'artifact-manifest.json')
    manifest = json.loads(checked_bytes(manifest_path, item['artifact_manifest']))
    records = [dict(item['artifact_manifest'], name='artifact-manifest.json'), *manifest['files']]
    # 公開束のname/path表記を受け付け、元manifestのbytesは変更しない。
    for record in records:
        if 'name' in record and 'path' in record and record['name'] != record['path']:
            raise ValueError('公開成果物のname/pathが一致しません')
        record['name'] = record.get('name', record.get('path'))
        if not isinstance(record['name'], str) or not record['name']:
            raise ValueError('公開成果物の相対ファイル名がありません')
    names = [record['name'] for record in records]
    if len(names) != len(set(names)) or len(names) != item['artifact_count']:
        raise ValueError('公開成果物の重複・件数不一致があります')
    required = ({'index.html'} if navigation else
                {'index.html', 'results.json.gz', 'audio_samples.json', 'audio_credits.html'})
    if not required.issubset(names):
        raise ValueError('一覧に必要な公開成果物がありません')
    for record in records:
        name = record['name']
        allowed = (('.html', '.json', '.json.gz', '.svg', '.wav', '.md', '.csv', '.png', '.css')
                   if navigation else ('.html', '.json', '.json.gz'))
        if not name.endswith(allowed):
            raise ValueError(f'未定義の公開形式です: {name}')
        file = relative_file(source, name)
        content = checked_bytes(file, record)
        if len(content) >= 10 * 1024 * 1024:
            raise ValueError(f'公開単体サイズが10 MiB以上です: {name}')
        if navigation and name.endswith('.wav'):
            with wave.open(io.BytesIO(content), 'rb') as sample:
                if (sample.getnframes() < 1 or sample.getframerate() < 1
                        or sample.getnframes() / sample.getframerate() > 5):
                    raise ValueError(f'公開WAVは5秒以下の短例に限ります: {name}')
        target = output / item['path'] / name
        if target.exists():
            raise ValueError(f'既存の公開先と衝突します: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        checked_bytes(target, record)
    return source, set(names)


def audio_listing_link(item, name, artifact_names, suffix):
    """コピー済み成果物内の、URLとしても安全な相対ファイルだけを参照する。"""
    if not isinstance(name, str) or not name:
        raise ValueError('一覧音声の参照先には相対ファイル名が必要です')
    relative = PurePosixPath(name)
    if (relative.is_absolute() or '..' in relative.parts or name != relative.as_posix()
            or any(char in name for char in '\\:?#%')
            or any(ord(char) < 32 or ord(char) == 127 for char in name)):
        raise ValueError(f'一覧音声の公開相対パスが不正です: {name}')
    if name not in artifact_names or not name.endswith(suffix):
        raise ValueError(f'一覧音声の参照先が公開成果物にありません: {name}')
    return quote(item['path'] + '/' + name, safe='/')


def navigation_audio_listing(item, artifact_names):
    """指標の有無と独立に、保存済み短音声と帰属への参照を表示する。"""
    if 'audio_listing' not in item:
        return ''
    listing = item['audio_listing']
    if not isinstance(listing, dict):
        raise ValueError('一覧音声の登録形式が不正です')
    for key in ('caption', 'note'):
        if not isinstance(listing.get(key), str) or not listing[key].strip():
            raise ValueError(f'一覧音声の説明がありません: {key}')
    samples = listing.get('samples')
    if not isinstance(samples, list) or not samples:
        raise ValueError('一覧音声には1件以上の短例が必要です')
    attribution = audio_listing_link(item, listing.get('attribution_path'), artifact_names, '.html')
    cards, seen = [], set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError('一覧音声の短例登録が不正です')
        link = audio_listing_link(item, sample.get('path'), artifact_names, '.wav')
        if sample['path'] in seen:
            raise ValueError('一覧音声の短例が重複しています')
        seen.add(sample['path'])
        label = sample.get('label')
        if not isinstance(label, str) or not label.strip():
            raise ValueError('一覧音声の短例に表示名がありません')
        cards.append(f'<div><p>{esc(label)}</p><audio controls preload="none" '
                     f'aria-label="{esc(label)}" src="{esc(link)}"></audio></div>')
    return (f'<p>{esc(listing["caption"])}</p><div class="audio-grid">'
            + ''.join(cards) + f'</div><p><small>{esc(listing["note"])} '
            f'<a href="{esc(attribution)}">出典・許諾・改変表示</a></small></p>')


def navigation_card(item, time_label, artifact_names):
    """案内作成日時・比較範囲と任意の音声を示し、測定日時とは区別する。"""
    created_on = date.fromisoformat(item['created_on']).isoformat()
    if created_on != item['created_on']:
        raise ValueError('案内作成日はYYYY-MM-DDで指定してください')
    created_label = (f'案内作成：<time datetime="{created_on}">{created_on}</time>'
                     '（UTCの日付。各レポートの測定・集計日時とは別）')
    if 'created_at' in item:
        created_label = ('案内作成（測定時刻とは別）：'
                         + time_label({'recorded_at': item['created_at']}))
    link = item['path'] + '/index.html'
    return (f'<article><h2><a href="{esc(link)}">{esc(item["title"])}</a></h2>'
            f'<small>{created_label}</small>'
            f'<p>{esc(item["comparison_scope"])}</p>'
            + navigation_audio_listing(item, artifact_names)
            + f'<p><a href="{esc(link)}">比較範囲・完了状態と元レポートを見る</a></p>'
            + '</article>')


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
        source, artifact_names = copy_artifacts(root, output, item)
        if kind == 'navigation-only':
            # 実際の案内作成日時が未登録の場合だけ、従来の日単位キーを維持する。
            timestamp = item.get('created_at', item['created_on'] + 'T00:00:00+00:00')
            sort_time = recorded_time({'recorded_at': timestamp})
            if 'created_at' in item and sort_time.date().isoformat() != item['created_on']:
                raise ValueError('案内作成日時のUTC日付がcreated_onと一致しません')
            card = navigation_card(item, time_label, artifact_names)
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

