"""正式batchの証拠を非公開Library転送用120MiB以下chunkへまとめる。外部転送は別操作。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from all_metrics_common import ROOT, now, read
from vocoderbench.quality_core import sha256, write_json

MAX_RAW_BYTES = 120 * 1024**2


def plan_files(selection):
    """選択manifestは明示pathだけ。重み・cacheを黙って全量含めない。"""
    files = []
    root = ROOT.resolve()
    for value in selection['files']:
        path = (root / value).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'checkpoint対象がrepo内の実fileではありません: {value}')
        if any(part in ('.git', '.venv', '.cache') for part in path.relative_to(root).parts):
            raise ValueError('公式再取得可能なpackage/model cacheはこのraw checkpointへ含めません')
        if path.stat().st_size > MAX_RAW_BYTES:
            raise ValueError('単一fileが120MiB超。明示分割計画を作るまで転送しません')
        files.append({'path': str(path.relative_to(root)), 'bytes': path.stat().st_size, 'sha256': sha256(path)})
    if len({row['path'] for row in files}) != len(files) or not files:
        raise ValueError('対象fileは空/重複なしの明示一覧が必要です')
    return sorted(files, key=lambda row: row['path'])


def build(selection_path, output):
    selection = read(selection_path)
    if selection.get('purpose') != 'owner_private_formal_research_evidence':
        raise ValueError('非公開の正式研究証拠selectionだけを処理します')
    if not selection.get('batch_id') or not selection.get('stage'):
        raise ValueError('batch/stageを明示してください')
    if output.exists():
        raise FileExistsError('既存checkpointは上書きしません。新しいIDを指定してください')
    rows = plan_files(selection)
    chunks, current, size = [], [], 0
    for row in rows:
        if current and size + row['bytes'] > MAX_RAW_BYTES:
            chunks.append(current)
            current, size = [], 0
        current.append(row)
        size += row['bytes']
    if current:
        chunks.append(current)
    output.mkdir(parents=True)
    manifest = {'schema_version': 1, 'purpose': selection['purpose'], 'batch_id': selection['batch_id'],
                'stage': selection['stage'], 'created_at_utc': now(), 'source_sha256': sha256(__file__),
                'selection_path': str(selection_path), 'selection_sha256': sha256(selection_path),
                'root_for_restore': '.', 'files': rows, 'chunks': [], 'remote_status': 'not_uploaded',
                'permission_scope': 'Local archive only; owner must confirm applicable private-upload authorization separately.',
                'local_retirement': 'No originals are removed by this program.'}
    for index, members in enumerate(chunks):
        filename = f'evidence-{selection["batch_id"]}-{selection["stage"]}-{index:03d}.zip'
        path = output / filename
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for row in members:
                source = ROOT / row['path']
                if sha256(source) != row['sha256']:
                    raise ValueError('archive作成中に元fileが変わりました')
                archive.write(source, row['path'])
            archive.writestr('CHECKPOINT_MEMBERS.json', json.dumps({'files': members}, ensure_ascii=False, indent=2))
        if path.stat().st_size >= 128 * 1024**2:
            raise ValueError('転送chunkは128MiB未満が必要です')
        manifest['chunks'].append({'file': filename, 'bytes': path.stat().st_size,
            'sha256': sha256(path), 'member_count': len(members), 'uncompressed_file_bytes': sum(r['bytes'] for r in members)})
        write_json(output / 'manifest.json', manifest)
    manifest['finished_at_utc'] = now()
    manifest['total_archive_bytes'] = sum(row['bytes'] for row in manifest['chunks'])
    write_json(output / 'manifest.json', manifest)
    return manifest


def verify_readback(archive, expected, library_file_id, file_id, version, receipt):
    """固定version読戻しarchiveだけを全member照合し、復元locatorを残す。"""
    if sha256(archive) != expected:
        raise ValueError('固定version読戻しarchive SHA不一致')
    with zipfile.ZipFile(archive) as zipped:
        rows = json.loads(zipped.read('CHECKPOINT_MEMBERS.json'))['files']
        for row in rows:
            info = zipped.getinfo(row['path'])
            if info.file_size != row['bytes']:
                raise ValueError('読戻しmember bytes不一致')
            digest = hashlib.sha256()
            with zipped.open(row['path']) as stream:
                while block := stream.read(4 * 1024**2):
                    digest.update(block)
            if digest.hexdigest() != row['sha256']:
                raise ValueError('読戻しmember SHA不一致')
    write_json(receipt, {'schema_version': 1, 'status': 'fixed_version_readback_all_member_hashes_match',
        'archive_path': str(archive), 'archive_sha256': expected, 'archive_bytes': archive.stat().st_size,
        'library_file_id': library_file_id, 'file_id': file_id, 'version': version,
        'verified_at_utc': now(), 'member_count': len(rows), 'files': rows,
        'local_originals_removed': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    create = subs.add_parser('build')
    create.add_argument('--selection', type=Path, required=True)
    create.add_argument('--output', type=Path, required=True)
    check = subs.add_parser('verify-readback')
    check.add_argument('--archive', type=Path, required=True)
    check.add_argument('--sha256', required=True)
    check.add_argument('--library-file-id', required=True)
    check.add_argument('--file-id', required=True)
    check.add_argument('--version', type=int, required=True)
    check.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'build':
        build(args.selection, args.output)
    else:
        verify_readback(args.archive, args.sha256, args.library_file_id, args.file_id, args.version, args.receipt)
    return 0


if __name__ == '__main__':
    from vocoderbench.logging_utils import run_cli
    raise SystemExit(run_cli(main, 'all-metrics-checkpoint'))
