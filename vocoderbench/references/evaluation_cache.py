"""評価済みの行を条件付きで再利用し、再試行前の失敗を保存する。"""
from copy import deepcopy
import logging

from .common import digest, now, read, write


class EvaluationCache:
    def __init__(self, output):
        self.path = output / 'evaluation_partial.json'
        self.history_path = output / 'evaluation_history.json'
        self.contract_sha256 = digest(output / 'contract.json')
        data = read(self.path) if self.path.exists() else {}
        if data and (data.get('schema_version') != 2 or
                     data.get('contract_sha256') != self.contract_sha256):
            raise ValueError('途中評価の形式・条件が違います。別の出力先を指定してください')
        self.rows = {}
        for row in data.get('resynthesis', []) + data.get('calibration', []):
            key = (row['case'], row['method'])
            if key in self.rows:
                raise ValueError(f'途中評価の行が重複しています: {key}')
            self.rows[key] = row
        self.history = read(self.history_path) if self.history_path.exists() else []

    def lookup(self, case, method, signature):
        previous = self.rows.get((case, method), {})
        if previous and previous.get('evaluation_input') != signature:
            self.archive(previous, '評価入力が変わったため再利用しない')
            return {}
        return deepcopy(previous)

    def archive(self, row, reason):
        self.history.append({'archived_at': now(), 'reason': reason, 'row': deepcopy(row)})
        write(self.history_path, self.history)

    def save(self, row):
        self.rows[(row['case'], row['method'])] = deepcopy(row)
        # 再開直後に未訪問の行を消さない。原音のMOSも一行ずつ保存する。
        write(self.path, {'schema_version': 2, 'contract_sha256': self.contract_sha256,
                         'resynthesis': [r for r in self.rows.values() if r['method'] != 'identity'],
                         'calibration': [r for r in self.rows.values() if r['method'] == 'identity']})


class MosMeasurements:
    def __init__(self, args, cache):
        self.args, self.cache, self.evaluator = args, cache, None

    def measure(self, row, previous, waveform, sample_rate, case):
        saved = previous.get('mos', {})
        if not self.args.mos or saved.get('status') == 'measured':
            return deepcopy(saved) if saved else {'status': 'not_requested', 'value': None}
        if saved.get('status') == 'failed':
            if not self.args.retry_failed:
                return deepcopy(saved)
            self.cache.archive(previous, '失敗したMOS評価を明示指定で再試行')
        if self.evaluator is None:
            from ..mos import MosEvaluator
            self.evaluator = MosEvaluator(cache_root=self.args.mos_cache, repetitions=1,
                                          seed=20261012, threads=4)
        logging.info('予測MOSを計測: %s / %s', row['case'], row['method'])
        value = self.evaluator.predict(waveform, sample_rate,
                                       language=case['language'], style=case['style'])
        write(self.args.output / 'mos_provenance.json', self.evaluator.provenance)
        return value
