"""保存済みの比較HTML・JSONを実験記録へ登録する。再計測・再描画はしない。"""
from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import re
import shutil
import tempfile
from zoneinfo import ZoneInfo

from ..logging_utils import LoggedArgumentParser, run_cli
from .catalog import METHODS
from .common import ROOT, digest, now, read, write

REQUIRED = ('index.html', 'results.json', 'summary.json', 'audio_samples.json')
OPTIONAL = ('contract.json', 'execution.json', 'processes.json', 'mos_provenance.json')


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('記録日時にはUTCオフセットが必要です')
    return result


def publish(source: Path, topic: str, title: str, provenance: dict | None = None) -> Path:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', topic):
        raise ValueError('テーマ名は半角英小文字・数字・ハイフンで指定してください')
    source = source.resolve()
    for name in REQUIRED:
        if not (source / name).is_file():
            raise FileNotFoundError(f'保存する比較結果がありません: {source / name}')
    data = read(source / 'results.json')
    if data.get('study_role') != 'existing_references':
        raise ValueError('このコマンドは既存方式の比較結果専用です')
    names = data['selected_methods']
    if not names or len(names) != len(set(names)) or set(names) - METHODS.keys():
        raise ValueError('方式の選択が不正です')
    if data['formal_base']['method'] is not None:
        raise ValueError('既存方式だけの比較に自作ベースを設定しないでください')
    records = data['resynthesis']
    pairs = [(row['case'], row['method']) for row in records]
    expected = {(case['id'], method) for case in data['contract']['inputs'] for method in names}
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError('未実行・失敗を含む全入力×選択方式の記録が必要です')
    samples = read(source / 'audio_samples.json')['samples']
    if any(sample['method'] not in ['identity', *names] for sample in samples):
        raise ValueError('選択外の方式の音声例が混在しています')
    recorded_at = data['generated_at']
    timestamp(recorded_at)
    started_at = data.get('execution', {}).get('started_at', recorded_at)
    day = timestamp(started_at).astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
    group = ROOT / 'experiments' / day / topic
    manifest_path = group / 'experiment.json'
    completed = sum(row['status'] == 'measured' for row in records)
    smoke = data['contract']['scope'] == 'smoke'
    summary = (f'WORLDを含む既存方式の再合成比較。{len(names)}方式・{data["planned_cases"]}音声、'
               f'再合成・評価完了{completed}/{len(records)}件。'
               + ('少数音声の動作確認であり、品質の採用判定ではありません。' if smoke
                  else '方式・帯域・情報量の違いと、欠測を分けて記録します。'))
    if manifest_path.exists():
        meta = read(manifest_path)
        if (meta.get('date'), meta.get('topic'), meta.get('timezone')) != (day, topic, 'Asia/Tokyo'):
            raise ValueError('既存の実験登録と保存先が一致しません')
    elif group.exists():
        raise ValueError('登録情報のない既存フォルダには追加しません')
    else:
        meta = {'schema_version': 1, 'id': f'{day}-{topic}', 'date': day, 'topic': topic,
                'timezone': 'Asia/Tokyo', 'title': title, 'summary': summary,
                'status': '動作確認の記録' if smoke else '比較結果の記録',
                'notes': ['README.md'], 'runs': []}
    for run in meta['runs']:
        old = group / run['path'] / 'publication.json'
        if old.exists() and read(old)['copied_files'].get('results.json') == digest(source / 'results.json'):
            raise ValueError('同じ測定結果は登録済みです。再計測として重複登録しません')
    number = max((int(run['id'].split('-')[1]) for run in meta['runs']), default=0) + 1
    run_id = f'run-{number:03d}'
    target = group / 'results' / run_id
    if target.exists():
        raise FileExistsError(f'過去の結果は上書きしません: {target}')
    files = [*REQUIRED, *(name for name in OPTIONAL if (source / name).is_file())]
    hashes = {name: digest(source / name) for name in files}
    run = {'id': run_id, 'date': day, 'title': title, 'path': f'results/{run_id}',
           'recorded_at': recorded_at, 'recorded_at_source': '元のresults.jsonのgenerated_at',
           'date_note': '元の測定日時を保持。Gitへの保存日時はpublication.jsonに別記。'}
    group.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.publication-', dir=group) as temporary:
        stage = Path(temporary)
        for name in files:
            shutil.copyfile(source / name, stage / name)
            if digest(stage / name) != hashes[name]:
                raise ValueError(f'保存時に内容が変わりました: {name}')
        logs = {str(p.relative_to(source)): p.read_text(encoding='utf-8', errors='replace')
                for p in sorted((source / 'logs').glob('*.log'))}
        write(stage / 'worker_logs.json', logs)
        worker_records = {str(p.relative_to(source)): read(p)
                          for p in sorted((source / 'native').glob('*/*.json'))}
        write(stage / 'worker_records.json', worker_records)
        write(stage / 'publication.json', {'schema_version': 1, 'archived_at': now(),
              'measurement_generated_at': recorded_at, 'source_provenance': provenance or {},
              'copied_files': hashes, 'rerun': False, 'html_regenerated': False,
              'note': '元のHTML・JSONを変更せず保存。全長波形・モデル・原音全体は公開対象外。'})
        target.parent.mkdir(exist_ok=True)
        stage.rename(target)
    if not manifest_path.exists():
        note = (f'# {title}\n\n{summary}\n\n'
                f'結果は [{run_id}](results/{run_id}/index.html) にあります。'
                'HTML内に音声を埋め込み、全測定値・条件・ワーカーログは隣のJSONに保存しています。\n\n'
                'これは既存方式の比較であり、自作ベースの測定・選定はしません。'
                'DACは明示選択時だけ追加し、未選択なら欠落や失敗には数えません。\n\n'
                '## 記録と公開\n\n'
                'ローカルの比較結果を保存しただけではGitHub Pagesには出ません。'
                'このフォルダとexperiment.jsonをPRへ含め、mainへマージした後、'
                'Pagesの公開処理が成功すると一覧と音声付きHTMLが公開されます。\n\n'
                'コピー元とファイルのSHA-256はpublication.jsonに記録しています。'
                '復元・HTMLの保存を新規の計測と数えません。少数音声の確認では、'
                '固定120音声の品質比較や自動MOS測定を完了したとは扱いません。\n\n'
                '## 音声の出典\n\n'
                '正式集合の音声は [コーパスの説明](../../../docs/CORPUS.md) を参照してください。'
                '動作確認の2音声は [LLSM2の固定版README](https://github.com/Sleepwalking/libllsm2/'
                'blob/d18cdf02b31819670e3bc23ead933ad9467da06d/README.md) のTest Soundsに由来します。'
                '[CMU ARCTIC](http://festvox.org/cmu_arctic/) のarctic_a0001.wavと、'
                '[unfaのAre you ready?](https://freesound.org/people/unfa/sounds/258342/)です。'
                '比較用に先頭最大5秒を使用し、公開音声例は原音・再合成の先頭最大2秒です。'
                '再合成には各方式の標本化周波数への変換が含まれ、音量合わせはしていません。\n')
        (group / 'README.md').write_text(note, encoding='utf-8')
    meta['runs'].append(run)
    write(manifest_path, meta)
    if data.get('failure_count'):
        logging.warning('失敗・欠測を含む結果を、その状態のまま保存しました')
    logging.info('保存先: %s。Pages公開はこの変更のmainへの反映後です', target)
    return target


def main():
    parser = LoggedArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='比較コマンドの出力先')
    parser.add_argument('--topic', default='reference-methods')
    parser.add_argument('--title', default='WORLDと追加6方式の再合成比較')
    parser.add_argument('--provenance', type=Path, help='復元元のCI・成果物ID等を記録したJSON')
    args = parser.parse_args()
    target = publish(args.source, args.topic, args.title,
                     read(args.provenance) if args.provenance else None)
    print(target.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'reference-publish'))
