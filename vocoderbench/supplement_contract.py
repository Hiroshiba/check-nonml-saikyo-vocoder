"""完了した正式120録音比較に従属する、取得済みJVS補助研究の条件確認。"""
from collections import Counter
import json
from pathlib import Path

from . import corpus
from .benchmark_io import ROOT, now, read, sha, source_contract, write
from .logging_utils import run_process
from .mos import CHECKPOINT_NAME, CHECKPOINT_SHA256, CONFIG_HASHES, MosEvaluator

PARENT = ROOT / 'experiments/2026-10-12/noise-envelope/results/run-001'
MANIFEST = ROOT / 'data/jvs_available_v1.json'
MANIFEST_SHA = '1ff7a449b5f44580d6b48c187209c9786522880a7630ebfacf081660b2df4520'
FORMAL_SHA = '644f4d57483366bb20d8dbcfdaa254e354aed4af8318a6a2984bb2e8b3ddc9c1'


def verified_parent(candidate):
    parent = read(PARENT / 'results.json')
    contract = read(PARENT / 'contract.json')
    entries = corpus.read_manifest(corpus.MANIFEST)['entries']
    ids = {entry['id'] for entry in entries}
    if (sha(corpus.MANIFEST) != FORMAL_SHA or contract['manifest_sha256'] != FORMAL_SHA
            or len(ids) != 120 or len({e['speaker'] for e in entries}) != 40):
        raise ValueError('固定された正式120録音・40話者の親比較を確認できません')
    if parent['planned_cases'] != 120 or {c['id'] for c in parent['cases']} != ids:
        raise ValueError('親結果が正式120録音に対応していません')
    expected = {(identifier, method) for identifier in ids for method in ('hnm', 'candidate', 'world_harvest')}
    rows = parent['resynthesis']
    if len(rows) != 360 or {(r['case'], r['method']) for r in rows} != expected:
        raise ValueError('親比較の方式・録音の組が不足または重複しています')
    originals = parent['calibration']
    if len(originals) != 120 or {r['case'] for r in originals} != ids:
        raise ValueError('親比較の原音測定が120件に対応していません')
    terminal = {'measured', 'failed', 'partial_failure'}
    if any(r['status'] not in terminal for r in rows):
        raise ValueError('親比較には計算待ちの方式があります')
    if any(r.get('mos', {}).get('status') not in ('measured', 'failed') for r in rows + originals):
        raise ValueError('親比較のMOSが完了していません')
    if any(len(r.get('seed_diagnostics', [])) != (1 if r['method'] == 'world_harvest' else 8)
           or any(s['status'] not in ('measured', 'failed') for s in r['seed_diagnostics']) for r in rows):
        raise ValueError('親比較の反復測定が未確定です')
    current = json.loads(json.dumps(source_contract(corpus.MANIFEST, candidate)))
    current['method_sources']['hnm']['repository_commit'] = contract['method_sources']['hnm']['repository_commit']
    if current != contract:
        differing = [key for key in contract if current.get(key) != contract[key]]
        raise ValueError(f'親と共有する方式・測定器・依存条件が異なります: {differing}')
    return contract, {
        'result_path': str((PARENT / 'results.json').relative_to(ROOT)),
        'result_sha256': sha(PARENT / 'results.json'),
        'contract_path': str((PARENT / 'contract.json').relative_to(ROOT)),
        'contract_sha256': sha(PARENT / 'contract.json'),
        'planned_recordings': 120, 'planned_rows': 360, 'completed_rows': len(rows),
        'failed_rows': sum(r['status'] != 'measured' for r in rows),
        'planned_mos': 480, 'completed_mos': len(rows + originals),
        'failed_mos': sum(r['mos']['status'] != 'measured' for r in rows + originals),
        'public_report': '../../../noise-envelope/results/run-001/index.html',
    }


def cached_mos(cache):
    files = {Path('weights') / CHECKPOINT_NAME: CHECKPOINT_SHA256,
             **{Path('wav2vec2_config') / name: digest for name, digest in CONFIG_HASHES.items()}}
    for path, expected in files.items():
        source = cache / path
        if not source.is_file() or sha(source) != expected:
            raise FileNotFoundError(f'固定MOSキャッシュが未取得または不一致です。追加取得しません: {path}')
    return {'configuration': MosEvaluator(cache_root=cache).provenance,
            'cache_sha256': {str(path): digest for path, digest in files.items()}}


def build(args, cases):
    shared, parent = verified_parent(args.candidate_package)
    manifest = corpus.read_manifest(MANIFEST)
    if sha(MANIFEST) != MANIFEST_SHA or manifest['public_audio_example_ids']:
        raise ValueError('JVS補助集合または音声非公開の条件が一致しません')
    if (len(cases) != 12 or len({c['id'] for c in cases}) != 12
            or len({c['speaker'] for c in cases}) != 4
            or Counter(c['style'] for c in cases) != {'normal': 4, 'whisper': 4, 'falsetto': 4}):
        raise ValueError('補助集合は固定4話者×3発声の12録音である必要があります')
    return {'schema_version': 1, 'study_role': 'supplement_to_completed_fixed_120',
            'parent': parent, 'shared_conditions': shared, 'manifest_sha256': MANIFEST_SHA,
            'manifest_id': manifest['id'], 'inputs': manifest['entries'],
            'entry_source_sha256': {p.name: sha(p) for p in sorted((ROOT / 'vocoderbench').glob('supplement*.py'))},
            'summary_source_sha256': sha(ROOT / 'vocoderbench/benchmark_summary.py'),
            'mos': cached_mos(args.mos_cache),
            'planned': {'recordings': 12, 'speakers': 4, 'resynthesis_rows': 36,
                        'syntheses_including_seeds': 204, 'predicted_mos': 48},
            'network': 'offline_existing_cache_only', 'public_audio': False,
            'interpretation': '発声様式別の補助診断。正式120件の分母・採否閾値は変更しない。'}


def initialize(args, cases):
    contract = build(args, cases)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / 'contract.json'
    if path.exists():
        if read(path) != contract:
            raise ValueError('補助研究の保存条件と異なります。新しい出力先を指定してください')
    else:
        write(path, contract)
        write(args.output / 'execution.json', {'started_at': now(), 'status': 'not_started',
              'parent_commit': run_process(['git', 'rev-parse', 'HEAD'], cwd=ROOT).stdout.strip()})
    return contract
