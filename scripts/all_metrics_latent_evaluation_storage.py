"""凍結評価式を保った保存層。重複batchを索引化し旧JSONを可逆圧縮する。"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

from all_metrics_common import ROOT, RUN, freeze, now, read
import all_metrics_latent_evaluation as evaluation
import all_metrics_latent_evaluation_resume as resume
from vocoderbench.logging_utils import run_cli
from vocoderbench.quality_core import sha256, write_json

BASE = RUN / 'latent-evaluation'


def compressed_archive(path):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive = BASE / 'storage-originals' / f'{digest}.json.gz'
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix('.part')
        temporary.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))
        temporary.replace(archive)
    if gzip.decompress(archive.read_bytes()) != raw:
        raise ValueError('保存JSONの可逆gzip読戻しが原本と完全一致しません')
    return {'original_path': str(path), 'original_sha256': digest, 'original_bytes': len(raw),
        'archive_path': str(archive), 'archive_sha256': sha256(archive), 'archive_bytes': archive.stat().st_size,
        'decompressed_exact_bytes_verified': True}


def compact_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
    temporary.replace(path)


def batch_index(value):
    rows = []
    for row in value['rows']:
        source = BASE / 'measurements' / f'{row["case"]}__{row["method"]}.json'
        rows.append({'case': row['case'], 'method': row['method'], 'status': row['status'],
            'raw_result': str(source), 'raw_result_sha256': sha256(source),
            'input_fingerprint': row.get('input_fingerprint')})
    return {'updated_at_utc': value['updated_at_utc'], 'rows': rows,
        'storage_schema': 'measurement_reference_index',
        'scope': '詳細値は各raw_result。評価定義・個別結果の情報は変えていない。'}


def storage_write(path, value):
    path = Path(path)
    if path.parent.name == 'history':
        write_json(path, value)
        proof = compressed_archive(path)
        write_json(path, {'storage_schema': 'exact_gzip_original', **proof})
    elif path.parent == BASE and path.name.startswith('batch-'):
        write_json(path, batch_index(value))
    else:
        compact_json(path, value)


def migrate_existing():
    for path in [*sorted((BASE / 'measurements').glob('*.json')),
                 *sorted(BASE.glob('batch-*.json')), *sorted((BASE / 'history').glob('*.json'))]:
        value = read(path)
        if value.get('storage_schema') in ('exact_gzip_original', 'measurement_reference_index'):
            continue
        ledger = BASE / 'storage-migrations' / f'{path.parent.name}-{path.stem}.json'
        if ledger.exists() and sha256(path) == read(ledger)['replacement_sha256']:
            continue
        proof = compressed_archive(path)
        if path.parent.name == 'measurements':
            compact_json(path, value)
        elif path.parent.name == 'history':
            write_json(path, {'storage_schema': 'exact_gzip_original', **proof})
        else:
            write_json(path, batch_index(value))
        proof.update(replacement_sha256=sha256(path), replacement_bytes=path.stat().st_size,
                     at_utc=now(), scientific_values_unchanged=True)
        if ledger.exists():
            ledger = ledger.with_name(f'{ledger.stem}-{time.time_ns()}.json')
        write_json(ledger, proof)


def main():
    freeze(BASE / 'storage-contract.json', {'schema_version': 1,
        'scientific_contract_sha256': sha256(BASE / 'contract.json'),
        'operational_source_sha256': {str(Path(__file__).relative_to(ROOT)): sha256(__file__)},
        'measurements': 'complete same JSON values, whitespace-only compaction',
        'batches': 'references to complete per-case raw JSON with current file SHA',
        'history': 'exact original UTF8 JSON bytes gzip, actual decompression equality, original and gzip SHA',
        'scientific_functions_or_inputs_changed': False})
    if sys.argv[1:] == ['--migrate-existing']:
        migrate_existing()
        return 0
    evaluation.write_json = storage_write
    return resume.main()


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'all-metrics-latent-evaluation-storage'))
