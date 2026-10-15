"""圧縮・分割済みの確定レポートを変換せず掲載し、保存値から一覧を作る。"""
import base64
import gzip
import hashlib
import html
import json
from pathlib import Path
import shutil


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
    source = root / item['path']
    if (not source.resolve().is_relative_to((root / 'research').resolve())
            or source.is_symlink()):
        raise ValueError(f'研究成果の公開位置が不正です: {source}')
    manifest_path = relative_file(source, 'artifact-manifest.json')
    manifest = json.loads(checked_bytes(manifest_path, item['artifact_manifest']))
    records = [dict(item['artifact_manifest'], name='artifact-manifest.json'), *manifest['files']]
    names = [record['name'] for record in records]
    if len(names) != len(set(names)) or len(names) != item['artifact_count']:
        raise ValueError('公開成果物の重複・件数不一致があります')
    required = {'index.html', 'results.json.gz', 'audio_samples.json', 'audio_credits.html'}
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


def comparison(data, item):
    """保存済み主値・順位・対応差を表示するだけで、統計量を再計算しない。"""
    groups = {group['id']: group for group in data['groups']}
    chosen = [groups[metric['group']] for metric in item['metrics']]
    methods = item['method_labels']
    if (list(methods) != data['methods']
            or data['formal_base']['comparison_reference'] != item['reference_method']):
        raise ValueError('登録した比較方式・当時のベースが保存結果と一致しません')
    for group in chosen:
        primary = group['primary']
        if (not primary['all_eight_methods']
                or primary['common_valid_recordings'] != item['recordings']
                or primary['common_valid_speakers'] != item['speakers']):
            raise ValueError('一覧の主比較分母が登録と一致しません')
    headings = ''.join(f'<th>{esc(metric["label"])}</th>' for metric in item['metrics'])
    rows = []
    for method, label in methods.items():
        cells = []
        for group in chosen:
            cell = group['primary']['methods'][method]
            value, difference = cell['value'], cell['hnm_difference']['value']
            if value is None or difference is None:
                text = '比較不能'
            else:
                text = (f'{value:.3f}（{cell["rank"]}位）'
                        f'<br><small>HNM差 {difference:+.3f}</small>')
            cells.append(f'<td>{text}</td>')
        rows.append(f'<tr><th scope="row">{esc(label)}</th>{"".join(cells)}</tr>')
    return ('<div class="scroll"><table><thead><tr><th>方式</th>' + headings
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


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
            f'<a href="{esc(link)}/index.html">全14例（レポート末尾）</a>'
            '。GOLF-ff・SiFi-GANの音声は許諾確認待ちです。</small></p>')


def preserved_cards(root, output, recorded_time, time_label):
    registry = read_json(root / 'research/pages-reports.json')
    if registry['schema_version'] != 1:
        raise ValueError('未対応の確定レポート登録形式です')
    cards, seen = [], set()
    for item in registry['reports']:
        if item['path'] in seen:
            raise ValueError('確定レポートの公開位置が重複しています')
        seen.add(item['path'])
        source = copy_artifacts(root, output, item)
        data = read_json(source / 'results.json.gz')
        if data['generated_at_utc'] != item['recorded_at']:
            raise ValueError('記録日時が保存済み集計と一致しません')
        link = item['path'] + '/index.html'
        card = (f'<article><h2><a href="{esc(link)}">{esc(item["title"])}</a></h2>'
                f'<small>記録：{time_label(item)}</small><p>{esc(item["summary"])}</p>'
                + comparison(data, item)
                + '<p><small>120録音・40話者の共通群、話者等重み。HNM差は方式−HNM。'
                '順位は点推定の順で、優越の確証や総合順位ではありません。'
                '予測MOSは未校正で、原音を超える知覚品質を示しません。'
                f'<a href="{esc(link)}">全指標・95%区間・欠測理由を見る</a></small></p>'
                + audio_preview(source, item) + '</article>')
        cards.append((recorded_time(item), item['path'], item['id'], card))
    return cards
