"""旧PML版の計画に固定されたPML/WORLD区間生成契約。RAW_FULL生成用ではない。"""
import json
import os
import shutil
import sys
from pathlib import Path

from .chunk_contracts import ContractError, freeze, read, sha, validate_plan


class GenerationContext:
    def __init__(self, args):
        self.args = args
        self.plan = validate_plan(read(args.plan))
        self.plan_sha = sha(args.plan)
        self.stage = {'pml': 'pml-generation', 'world_harvest': 'world-generation'}[args.method]
        if args.method not in self.plan['methods'] or self.stage not in self.plan['required_stage_receipts']:
            raise ContractError('計画外の方式・生成stageです')
        if self.plan['formal_base'] != 'pml' or self.plan['formal_base_version'] != 'pml-lowband-fwcep60-v1':
            raise ContractError('旧PML専用計画の固定版が異なります。RAW_FULLには転用できません')
        self.chunk = next(c for c in self.plan['chunks'] if c['id'] == args.chunk)
        authorization = read(args.authorization)
        if (authorization.get('approved') is not True
                or authorization.get('run_plan_sha256') != self.plan_sha
                or authorization.get('generation_sha256') != self.plan['frozen_digests']['generation']
                or authorization.get('chunk_ids') != [args.chunk]
                or self.stage not in authorization.get('stage_ids', [])):
            raise ContractError('この計画・source・区間・stageの実行許可がありません')
        self.evidence = {}
        for path in (args.plan, args.bindings, args.inputs, args.authorization):
            self.pin(path, sha(path))
        bindings = read(args.bindings)
        self.inventories = {}
        for kind, digest in self.plan['frozen_digests'].items():
            path = (args.bindings.parent / bindings[kind]['path']).resolve()
            self.pin(path, digest)
            inventory = read(path)
            self.inventories[kind] = inventory
            if kind != 'cohort':
                if not inventory.get('files'):
                    raise ContractError('実ファイルの凍結一覧がありません')
                for row in inventory['files']:
                    self.pin(path.parent / row['path'], row['sha256'])
        runtime = self.inventories['runtime']
        if Path(sys.prefix).resolve() != Path(runtime['dsp_python_prefix']).resolve():
            raise ContractError('凍結したDSP Python環境と異なります')
        runtime_path = (args.bindings.parent / bindings['runtime']['path']).resolve()
        world = (runtime_path.parent / runtime['world_library_path']).resolve()
        self.require_bound(world)
        os.environ['NONML_WORLD_LIBRARY'] = str(world)
        repo = Path(__file__).resolve().parents[2]
        for path in (Path(__file__), Path(__file__).with_name('reference_generation.py'),
                     Path(__file__).with_name('chunk_contracts.py'), repo / 'BASELINE.json',
                     repo / 'scripts/pml_evaluation/run_native.py', repo / 'vocoderbench/world.py',
                     repo / 'vocoderbench/world.lock.json'):
            self.require_bound(path)
        for path in (repo / 'vocoderbench/pml').rglob('*.py'):
            self.require_bound(path)
        baseline = read(repo / 'BASELINE.json')
        if baseline['method'] != 'pml' or baseline['version'] != 'pml-lowband-fwcep60-v1':
            raise ContractError('旧PML版専用の生成入口です。現RAW_FULLへの切替後は旧版生成を拒否します')
        self.inputs = read(args.inputs)
        if list(self.inputs) != [r['case'] for r in self.plan['cases']]:
            raise ContractError('全120入力の順序が計画と異なります')
        self.cases = {r['case']: r for r in self.plan['cases']}
        for case, row in self.inputs.items():
            old = self.cases[case]
            for key in ('samples', 'sample_rate', 'speaker'):
                if row[key] != old[key]:
                    raise ContractError('入力契約の相違: ' + case + '/' + key)
            if row['expected_npy_sha256'] != old['input_sha256']:
                raise ContractError('入力SHA契約の相違')
            self.pin(args.input_root / row['path'], old['input_sha256'])
        self.verify()
        self.contract = {'schema_version': 2, 'run_plan_sha256': self.plan_sha,
                         'chunk_id': args.chunk, 'stage_id': self.stage, 'method': args.method,
                         'frozen_digests': self.plan['frozen_digests'], 'input_manifest_sha256': sha(args.inputs),
                         'bindings_sha256': sha(args.bindings), 'seed': 0, 'threads': 2,
                         'source_normalization': False, 'clip': False,
                         'formal_base': 'pml', 'formal_base_version': 'pml-lowband-fwcep60-v1'}
        root = args.output / args.chunk / self.stage
        attempts = sorted(root.glob('attempt-*'))
        self.previous = {}
        self.complete = False
        if attempts:
            last = attempts[-1]
            if read(last / 'contract.json') != self.contract:
                raise ContractError('既存attemptの契約が異なります')
            receipt = read(last / 'receipt.json') if (last / 'receipt.json').exists() else None
            if receipt:
                if (receipt.get('validation_state') != 'validated_end'
                        or receipt.get('run_plan_sha256') != self.plan_sha
                        or receipt.get('frozen_digests') != self.plan['frozen_digests']
                        or receipt.get('case_ids') != self.chunk['case_ids']):
                    raise ContractError('既存終端証跡が異なります')
                for item in receipt['artifacts']:
                    self.pin(last / item['path'], item['sha256'])
                self.verify()
                self.output, self.complete = last, True
                return
            if not args.resume_interrupted:
                raise ContractError('中断attemptを保持しています。原因確認後にresume-interruptedを指定してください')
            # 完了済みcaseは科学失敗も含めて固定。未終端caseだけ新attemptへ移す。
            for path in sorted((last / 'cases').glob('*/record.json')):
                record = read(path)
                case = record['case']
                if (case not in self.chunk['case_ids'] or record.get('validation_state') != 'validated_end'
                        or record.get('run_plan_sha256') != self.plan_sha
                        or record.get('method') != args.method
                        or record.get('input_sha256') != self.cases[case]['input_sha256']):
                    raise ContractError('中断attempt内のcase終端証跡が不正です')
                self.pin(path, sha(path))
                for item in record['artifacts']:
                    self.pin(item['path'], item['sha256'])
                self.previous[case] = record
            for folder in sorted((last / 'cases').glob('*')):
                if not folder.is_dir() or folder.name in self.previous:
                    continue
                case = folder.name
                if case not in self.chunk['case_ids']:
                    raise ContractError('中断attemptに予定外caseがあります')
                checkpoint = folder / 'encode.json'
                if not checkpoint.exists():
                    continue
                record = read(checkpoint)
                if (record.get('run_plan_sha256') != self.plan_sha or record.get('case') != case
                        or record.get('method') != args.method
                        or record.get('input_sha256') != self.cases[case]['input_sha256']):
                    raise ContractError('部分caseの解析記録が不一致です')
                record['partial_case'] = True
                record['rows'] = []
                for condition in ('native', 'pitch_minus3', 'pitch_plus3'):
                    path = folder / (condition + '.json')
                    if path.exists():
                        record['rows'].append(read(path))
                record['artifacts'] = record.get('artifacts', []) + [
                    {'path': str(p.resolve()), 'sha256': sha(p)}
                    for p in folder.rglob('*') if p.is_file()]
                for item in record['artifacts']:
                    self.pin(item['path'], item['sha256'])
                if record.get('payload'):
                    self.pin(record['payload']['path'], record['payload']['sha256'])
                for row in record['rows']:
                    if row['case'] != case or row['method'] != args.method or row['status'] not in ('failed', 'measured'):
                        raise ContractError('部分caseの条件記録が不正です')
                    for key in ('wave', 'generated_wave', 'edited_payload'):
                        if row.get(key):
                            self.pin(row[key]['path'], row[key]['sha256'])
                self.previous[case] = record
            self.verify()
        self.output = root / f'attempt-{len(attempts)+1:03d}'
        self.output.mkdir(parents=True, exist_ok=False)
        freeze(self.output / 'contract.json', self.contract)

    def pin(self, path, digest):
        path = Path(path).resolve()
        if path in self.evidence and self.evidence[path] != digest:
            raise ContractError('同一fileへのSHA指定が衝突しています')
        self.evidence[path] = digest

    def require_bound(self, path):
        if Path(path).resolve() not in self.evidence:
            raise ContractError('必要なfileが凍結一覧にありません: ' + str(path))

    def verify(self):
        if shutil.disk_usage(self.args.output.parent).free < 5 * 1024**3:
            raise ContractError('空き容量5GiB未満のため停止します')
        for path, digest in self.evidence.items():
            if sha(path) != digest:
                raise ContractError('凍結fileのSHAが変わりました: ' + str(path))

    def save_case(self, record):
        freeze(self.output / 'cases' / record['case'] / 'record.json', record)

    def finish(self, records):
        if [r['case'] for r in records] != self.chunk['case_ids']:
            raise ContractError('区間の生成記録順序が異なります')
        conditions = ['native', 'pitch_minus3', 'pitch_plus3'] if self.args.method == 'pml' else ['native']
        rows = []
        for record in records:
            if [r['condition'] for r in record['rows']] != conditions:
                raise ContractError('条件網羅性が不正です')
            for row in record['rows']:
                if row['status'] not in ('measured', 'failed'):
                    raise ContractError('生成行が終端状態ではありません')
                if row['status'] == 'measured':
                    wave = row['wave']
                    self.pin(wave['path'], wave['sha256'])
                rows.append(row)
            for item in record['artifacts']:
                self.pin(item['path'], item['sha256'])
        self.verify()
        freeze(self.output / 'summary.json', {'cases': records, 'rows': rows})
        artifacts = {str(p.resolve()): sha(p) for p in self.output.rglob('*') if p.is_file()}
        for record in records:
            artifacts.update({r['path']: r['sha256'] for r in record['artifacts']})
        receipt = {'schema_version': 2, 'stage_id': self.stage, 'method': self.args.method,
                   'validation_state': 'validated_end', 'run_plan_sha256': self.plan_sha,
                   'chunk_id': self.args.chunk, 'case_ids': self.chunk['case_ids'],
                   'frozen_digests': self.plan['frozen_digests'], 'rows': rows,
                   'artifacts': [{'path': p, 'sha256': h} for p, h in sorted(artifacts.items())]}
        freeze(self.output / 'receipt.json', receipt)
        return self.output / 'receipt.json'


def configure_threads():
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) not in (None, '2'):
            raise ContractError('対照生成のthread数は2固定です')
        os.environ[key] = '2'


def save_json(path, value):
    """途中記録も上書きせず、終端JSONは別名へ保存する。"""
    freeze(path, json.loads(json.dumps(value, allow_nan=False)))
