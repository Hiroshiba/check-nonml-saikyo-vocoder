"""凍結済み区間波形の純粋評価I/O。候補合成器をimportしない。"""
import copy
import json
import logging
import os
import sys
from pathlib import Path

from .chunk_contracts import CONDITIONS, ContractError, freeze, read, sha, validate_plan


class UpstreamUnavailable(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def add_arguments(parser):
    for name in ('plan', 'manifest', 'bindings', 'assets', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--chunk', required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--resume-authorization', type=Path)


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def row_key(row):
    return row['case'], row['method'], row['condition'], row['metric']


class Context:
    def __init__(self, args, stage_id):
        self.args, self.stage_id = args, stage_id
        self.plan_sha = sha(args.plan)
        self.plan = validate_plan(read(args.plan))
        from .axis_registry import validate_registry
        validate_registry(self.plan)
        chunks = {r['id']: r for r in self.plan['chunks']}
        self.chunk = chunks[args.chunk]
        if stage_id not in self.plan['required_stage_receipts']:
            raise ContractError('予定外の評価stageです')
        authorization = read(args.authorization)
        if (authorization.get('approved') is not True
                or authorization.get('run_plan_sha256') != self.plan_sha
                or authorization.get('evaluator_sha256') != self.plan['frozen_digests']['evaluator']
                or authorization.get('chunk_ids') != [args.chunk]
                or stage_id not in authorization.get('stage_ids', [])):
            raise ContractError('この区間・stage・凍結評価ソースの実行許可がありません')
        self.methods = self.plan['methods']
        self.evidence = {}
        self.bound = set()
        self.expected_keys = None
        for path in (args.plan, args.manifest, args.bindings, args.assets, args.authorization):
            self.pin(path, sha(path))
        self.bindings = read(args.bindings)
        self.inventories = {}
        for kind, digest in self.plan['frozen_digests'].items():
            item = self.bindings[kind]
            path = (args.bindings.parent/item['path']).resolve()
            self.pin(path, digest)
            inventory = read(path)
            self.inventories[kind] = inventory
            if kind in ('evaluator', 'generation', 'runtime', 'assets', 'preprocessing'):
                if not inventory.get('files'):
                    raise ContractError('凍結inventoryに実file一覧がありません')
                for file in inventory['files']:
                    self.pin(path.parent/file['path'], file['sha256'])
                    self.bound.add((path.parent/file['path']).resolve())
        prefix = self.inventories['runtime']['quality_python_prefix']
        if Path(sys.prefix).resolve() != Path(prefix).resolve():
            raise ContractError('計画と異なる品質Python環境です')
        for path in Path(__file__).parent.glob('*.py'):
            self.require_bound(path)
        self.require_bound(args.assets)
        self.data = read(args.manifest)
        if (self.data.get('schema_version') != 2 or self.data.get('run_plan_sha256') != self.plan_sha
                or self.data.get('chunk_id') != args.chunk):
            raise ContractError('波形manifestが計画と一致しません')
        self.cases = copy.deepcopy(self.data['cases'])
        if [r['case'] for r in self.cases] != self.chunk['case_ids']:
            raise ContractError('区間の録音順序・対象が一致しません')
        expected = {r['case']: r for r in self.plan['cases']}
        for row in self.cases:
            old = expected[row['case']]
            if (row['speaker'] != old['speaker'] or row['common_samples'] != old['common_samples']
                    or row['reference']['sha256'] != old['input_sha256']
                    or row['reference']['samples'] != old['samples']):
                raise ContractError('原音・話者・固定共通窓が一致しません')
            if set(row['outputs']) != set(self.methods):
                raise ContractError('予定方式の波形状態に欠落があります')
            descriptors = [row['reference']]
            for outputs in row['outputs'].values():
                if set(outputs) != set(CONDITIONS):
                    raise ContractError('予定3条件の波形状態に欠落があります')
                descriptors.extend(outputs.values())
            for descriptor in descriptors:
                if descriptor['status'] == 'measured':
                    descriptor['path'] = str((args.manifest.parent/descriptor['path']).resolve())
                    self.pin(descriptor['path'], descriptor['sha256'])
                elif descriptor['status'] not in ('failed', 'unsupported', 'not_applicable'):
                    raise ContractError('未終端の波形を評価へ渡せません')
        for item in self.data['generation_receipts']:
            path = (args.manifest.parent/item['path']).resolve()
            self.pin(path, item['sha256'])
            receipt = read(path)
            if (receipt.get('validation_state') != 'validated_end'
                    or receipt.get('run_plan_sha256') != self.plan_sha
                    or receipt.get('chunk_id') != args.chunk
                    or receipt.get('frozen_digests') != self.plan['frozen_digests']):
                raise ContractError('生成終端証跡が一致しません')
        self.assets = read(args.assets)
        self.verify()
        root = args.output/args.chunk/stage_id
        previous = sorted(root.glob('attempt-*'))
        self.previous, self.complete = {}, False
        self.initialization_failure = None
        copied = []
        contract = {'schema_version': 2, 'run_plan_sha256': self.plan_sha,
                    'chunk_id': args.chunk, 'stage_id': stage_id,
                    'manifest_sha256': sha(args.manifest), 'assets_sha256': sha(args.assets),
                    'bindings_sha256': sha(args.bindings), 'frozen_digests': self.plan['frozen_digests']}
        if previous:
            last = previous[-1]
            if read(last/'contract.json') != contract:
                raise ContractError('過去attemptの契約が異なります')
            receipt = read(last/'receipt.json') if (last/'receipt.json').exists() else {}
            if receipt.get('validation_state') == 'validated_end':
                for item in receipt['artifacts']:
                    self.pin(last/item['path'], item['sha256'])
                self.verify()
                self.previous = {row_key(r): r for r in read(last/'summary.json')['rows']}
                self.output, self.complete = last, True
                self.contract_sha256 = sha(last/'contract.json')
                return
            if args.resume_authorization is None:
                raise ContractError('中断attemptを保持中。運用中断の監査済み再開許可が必要です')
            resume = read(args.resume_authorization)
            if (resume.get('approved') is not True or resume.get('run_plan_sha256') != self.plan_sha
                    or resume.get('chunk_id') != args.chunk or resume.get('stage_id') != stage_id
                    or Path(resume['prior_attempt']).resolve() != last.resolve()
                    or resume.get('classification') != 'operational_interruption'
                    or resume.get('resume_unfinished_only') is not True):
                raise ContractError('運用再開許可が一致しません')
            self.pin(args.resume_authorization, sha(args.resume_authorization))
            listed = {str((last/a['path']).resolve()): a['sha256'] for a in resume['artifacts']}
            actual = {str(p.resolve()) for p in last.rglob('*') if p.is_file()}
            if set(listed) != actual:
                raise ContractError('中断attemptの全artifact監査が必要です')
            for path, digest in listed.items():
                self.pin(path, digest)
            self.verify()
            for path in (last/'measurements').glob('*.json'):
                row = read(path)
                if row['status'] in ('pending', 'running'):
                    raise ContractError('未終端個票は原因監査が必要です')
                self.previous[row_key(row)] = row
            old_init = read(last/'initialization.json') if (last/'initialization.json').exists() else None
            if old_init and old_init.get('status') == 'failed':
                self.initialization_failure = old_init
            for path in last.rglob('*.json'):
                if path.relative_to(last).parts[0] in ('recognitions', 'sidecars'):
                    copied.append((path, path.relative_to(last)))
        self.output = root/f'attempt-{len(previous)+1:03d}'
        self.output.mkdir(parents=True, exist_ok=False)
        freeze(self.output/'contract.json', contract)
        self.contract_sha256 = sha(self.output/'contract.json')
        import shutil
        if args.resume_authorization is not None:
            shutil.copyfile(args.resume_authorization, self.output/'resume-authorization.json')
        for source, relative in copied:
            target = self.output/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def pin(self, path, digest):
        path = Path(path).resolve()
        if path in self.evidence and self.evidence[path] != digest:
            raise ContractError('同じfileに異なる凍結SHAがあります')
        self.evidence[path] = digest

    def require_bound(self, path):
        if Path(path).resolve() not in self.bound:
            raise ContractError('必要なfileが凍結inventoryにありません: '+str(path))

    def verify(self):
        for path, digest in self.evidence.items():
            if sha(path) != digest:
                raise ContractError('凍結fileのSHAが変化しました: '+str(path))

    def wave(self, descriptor):
        import numpy as np
        if descriptor['status'] != 'measured':
            raise UpstreamUnavailable(descriptor['status'], descriptor.get('reason_code', 'generation_failed'))
        path = Path(descriptor['path'])
        if sha(path) != descriptor['sha256']:
            raise ContractError('採用波形のSHAが変化しました')
        wave = np.load(path, allow_pickle=False)
        if (wave.ndim != 1 or not len(wave) or len(wave) != descriptor['samples']
                or descriptor['sample_rate'] != 16000
                or wave.dtype not in (np.dtype('float32'), np.dtype('float64'))
                or not np.isfinite(wave).all()):
            raise ContractError('波形のshape/N/SR/dtype/有限性が不正です')
        return wave.astype(np.float64)

    def asset_options(self, metric):
        options = dict(self.assets['metrics'].get(metric, {}))
        for key, value in options.items():
            if key != 'domain':
                path = (self.args.assets.parent/value).resolve()
                self.require_bound(path)
                options[key] = str(path)
        return options

    def base_row(self, case, method, condition, metric):
        return {'case': case['case'], 'speaker': case['speaker'], 'method': method,
                'condition': condition, 'metric': metric, 'status': 'pending',
                'value': None, 'reason_code': 'none', 'contract_sha256': self.contract_sha256}

    def cached_row(self, case, method, condition, metric):
        old = self.previous.get((case['case'], method, condition, metric))
        if old and old['status'] not in ('pending', 'running'):
            value = copy.deepcopy(old)
            value['previous_contract_sha256'] = old['contract_sha256']
            value['contract_sha256'] = self.contract_sha256
            return value
        return None

    def record(self, row):
        name = '__'.join(row_key(row))+'.json'
        freeze(self.output/'measurements'/name, row)

    def finish(self, rows):
        keys = [row_key(r) for r in rows]
        if self.expected_keys is None or len(keys) != len(set(keys)) or set(keys) != self.expected_keys:
            raise ContractError('stageの予定全行と結果行が一致しません')
        if any(r['status'] in ('pending', 'running') for r in rows):
            raise ContractError('未終端行が残っています')
        self.verify()
        freeze(self.output/'summary.json', {'rows': rows, 'contract_sha256': self.contract_sha256})
        import shutil
        for index, handler in enumerate(logging.getLogger().handlers):
            if isinstance(handler, logging.FileHandler):
                handler.flush()
                shutil.copyfile(handler.baseFilename, self.output/f'runner-log-{index}.txt')
        artifacts = [{'path': str(p.relative_to(self.output)), 'sha256': sha(p)}
                     for p in sorted(self.output.rglob('*')) if p.is_file() and p.name != 'receipt.json']
        receipt = {'schema_version': 2, 'stage_id': self.stage_id,
                   'run_plan_sha256': self.plan_sha, 'chunk_id': self.args.chunk,
                   'case_ids': self.chunk['case_ids'], 'frozen_digests': self.plan['frozen_digests'],
                   'validation_state': 'validated_end', 'artifacts': artifacts}
        freeze(self.output/'receipt.json', receipt)
        logging.info('区間stageの終端証跡を保存: %s', self.output/'receipt.json')
        return self.output/'receipt.json'


def configure_threads():
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        if os.environ.get(name) not in (None, '2'):
            raise ContractError('品質thread数は2へ固定してください')
        os.environ[name] = '2'


def raise_if_operational(error):
    message = str(error).lower()
    if isinstance(error, (OSError, MemoryError)) or (isinstance(error, RuntimeError) and any(
            token in message for token in ('out of memory', 'cannot allocate memory', "can't allocate memory", 'defaultcpuallocator'))):
        raise error
