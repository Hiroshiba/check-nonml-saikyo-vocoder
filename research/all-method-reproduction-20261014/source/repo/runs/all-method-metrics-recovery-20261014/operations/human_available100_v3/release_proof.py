"""独立reviewと固定版読戻し証跡を小metadataの実SHAで照合する。"""
from pathlib import Path

from settings import ROOT, OUT, PACKAGE
from all_metrics_common import read
from vocoderbench.quality_core import sha256


def file_proof(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path), 'bytes': path.stat().st_size}


def read_proof(proof):
    actual = file_proof(proof['path'])
    if actual != proof:
        raise ValueError('release小metadataのpath/SHA/bytes不一致')
    return read(ROOT / proof['path'])


def verify_release(preflight_path, batch):
    preflight_proof = file_proof(preflight_path)
    release_path = OUT / 'execution-release-v3.json'
    release = read(release_path)
    source_path = OUT / 'source-sha256-v3.json'
    if (release.get('status') != 'approved_for_formal_measurement'
            or release.get('preflight_sha256') != preflight_proof['sha256']
            or batch not in release.get('released_batches', [])):
        raise ValueError('対象preflight/batchの親による資源実行releaseがありません')
    review = read_proof(release['independent_review'])
    if (review.get('status') != 'approved' or review.get('errors') != []
            or review.get('preflight_sha256') != preflight_proof['sha256']
            or review.get('source_inventory_sha256') != sha256(source_path)):
        raise ValueError('独立reviewの承認/対象source/preflightが不一致です')
    receipt = read_proof(release['private_checkpoint_readback'])
    if (receipt.get('status') != 'fixed_version_readback_all_member_hashes_match'
            or not receipt.get('library_file_id') or not receipt.get('file_id')
            or not isinstance(receipt.get('version'), int) or receipt['version'] < 0
            or not receipt.get('archive_sha256') or not receipt.get('archive_bytes')):
        raise ValueError('私有checkpointの固定版全member読戻しが未成功です')
    files = receipt['files']
    lookup = {row['path']: row for row in files}
    if len(files) != len(lookup) or len(files) != receipt['member_count']:
        raise ValueError('固定receiptのmember計数または一意性が不一致')
    expected = [preflight_path, ROOT / release['independent_review']['path']]
    expected.extend(Path(name) for name in read(preflight_path)['fixed_files'])
    expected.extend(p for p in PACKAGE.iterdir() if p.is_file() and p.suffix in ('.py', '.md', '.diff'))
    for path in expected:
        proof = file_proof(path)
        if lookup.get(proof['path']) != proof:
            raise ValueError(f'事前固定の必要memberが固定版証跡と不一致: {proof["path"]}')
    return {'release': file_proof(release_path), 'release_content': release,
        'review_proof': release['independent_review'], 'receipt_proof': release['private_checkpoint_readback'],
        'fixed_archive': {key: receipt[key] for key in ('library_file_id', 'file_id', 'version',
            'archive_sha256', 'archive_bytes', 'member_count')},
        'verified_required_members': len(expected)}
