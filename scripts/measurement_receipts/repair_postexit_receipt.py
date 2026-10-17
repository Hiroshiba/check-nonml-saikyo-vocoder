"""Audit a narrowly authorized Torch exit-cleanup omission without recomputing metrics."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, data):
    with path.open('x') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--runtime-bundle', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    args = parser.parse_args()
    original = args.receipt.resolve()
    base = original.parent
    tool = Path(__file__).resolve()
    pinned = {p.resolve(): sha(p) for p in (original, args.plan, args.runtime_bundle, args.authorization, tool)}
    receipt, plan, auth = read(original), read(args.plan), read(args.authorization)
    require(receipt.get('schema_version') == 2 and receipt.get('validation_state') == 'validated_end', 'Not terminal schema 2')
    require(receipt['run_plan_sha256'] == sha(args.plan) and receipt['frozen_digests'] == plan['frozen_digests'], 'Plan mismatch')
    require(sha(args.runtime_bundle) == plan['frozen_digests']['runtime'], 'Runtime mismatch')
    require(auth.get('approved') is True and auth.get('classification') == 'torch_atexit_temporary_module_cleanup', 'Repair authorization missing')
    require(auth.get('run_plan_sha256') == sha(args.plan) and auth.get('original_receipt_sha256') == sha(original)
            and auth.get('repair_tool_sha256') == sha(tool), 'Authorization identity mismatch')
    require(auth.get('chunk_id') == receipt['chunk_id'] and auth.get('stage_id') == receipt['stage_id'], 'Authorization scope mismatch')
    require(receipt['stage_id'] in ('utmosv2', 'utmosv2-edited', 'speaker_ecapa', 'speaker_ecapa-edited', 'scoreq', 'asr'), 'Not a Torch model stage')
    leaves = read(args.runtime_bundle)['files']
    evidence = []
    for item in leaves:
        if item['path'].endswith('/torch/distributed/nn/jit/instantiator.py'):
            path = (args.runtime_bundle.parent/item['path']).resolve()
            require(sha(path) == item['sha256'], 'Torch generator changed')
            text = path.read_text()
            require('_TEMP_DIR = tempfile.TemporaryDirectory()' in text and 'atexit.register(_TEMP_DIR.cleanup)' in text, 'Cleanup provenance absent')
            pinned[path] = item['sha256']
            evidence.append(path)
    require(len(evidence) == 1, 'Ambiguous Torch generator evidence')
    missing, retained, seen = [], [], set()
    for item in receipt['artifacts']:
        name = item['path']
        require(name not in seen, 'Duplicate artifact')
        seen.add(name)
        path = (base/name).resolve()
        require(path.is_relative_to(base), 'Original artifact outside attempt')
        if path.is_file():
            require(sha(path) == item['sha256'], 'Surviving artifact changed: '+name)
            pinned[path] = item['sha256']
            retained.append(item)
        else:
            require(not path.exists(), 'Artifact is no longer a file')
            missing.append(item)
    require(missing and missing == auth.get('missing_artifacts'), 'Missing artifacts differ from explicit authorization')
    pattern = r'work/tmp/(tmp[A-Za-z0-9_]+)/(_remote_module_non_scriptable\.py|__pycache__/_remote_module_non_scriptable\.cpython-312\.pyc)'
    matches = [re.fullmatch(pattern, item['path']) for item in missing]
    require(len(missing) == 2 and all(matches), 'Only the exact Torch generated pair can be omitted')
    require(len({match.group(1) for match in matches}) == 1, 'Temporary directories differ')
    py = next(item for item in missing if item['path'].endswith('.py'))
    require(py['sha256'] == '8205b16956fb264841ecd8644784a0d157f87df79b17c16825dc1163433ce5d8', 'Unknown generated source content')
    require({'contract.json', 'summary.json', 'initialization.json'} <= seen, 'Scientific evidence absent')
    summary = read(base/'summary.json')
    measurement_paths = {item['path'] for item in retained if item['path'].startswith('measurements/')}
    require(len(measurement_paths) == len(summary['rows']), 'Scientific row count differs')
    for row in summary['rows']:
        name = 'measurements/'+'__'.join(str(row[k]) for k in ('case', 'method', 'condition', 'metric'))+'.json'
        require(name in measurement_paths and read(base/name) == row, 'Individual scientific row differs')
    audit_path = base/'postexit-repair-audit.json'
    repaired_path = base/'receipt-postexit.json'
    require(not audit_path.exists() and not repaired_path.exists(), 'Repair output already exists')
    audit = {'schema_version': 1, 'classification': auth['classification'], 'scientific_remeasurement': False,
             'original_receipt_sha256': sha(original), 'repair_tool_sha256': sha(tool),
             'original_artifact_count': len(receipt['artifacts']), 'retained_artifact_count': len(retained),
             'omitted_missing_artifacts': missing, 'note': 'Torch atexit removed its generated temporary module and bytecode. Original receipt retained; every surviving artifact and scientific row verified unchanged.'}
    for path, digest in pinned.items():
        require(sha(path) == digest, 'Evidence changed during audit')
    save(audit_path, audit)
    added = [original, audit_path, tool, args.authorization.resolve(), args.plan.resolve(), args.runtime_bundle.resolve(), *evidence]
    new = dict(receipt)
    new['postexit_repair'] = audit
    new['artifacts'] = retained + [{'path': os.path.relpath(p, base), 'sha256': sha(p)} for p in added]
    for path, digest in pinned.items():
        require(sha(path) == digest, 'Evidence changed before repaired receipt')
    save(repaired_path, new)
    print(json.dumps({'receipt': str(repaired_path), 'sha256': sha(repaired_path), 'omitted_count': len(missing)}))


if __name__ == '__main__':
    main()
