"""入力ごとに独立した固定MOS推論。並列数で抽出seedを変えない。"""
from concurrent.futures import ProcessPoolExecutor
import logging
import multiprocessing
from pathlib import Path

import numpy as np

from .benchmark_io import now, read, write
from .logging_utils import configure_logging

_evaluator = None


def _initialize(cache):
    global _evaluator
    configure_logging('mos-worker')
    from .mos import MosEvaluator
    _evaluator = MosEvaluator(cache_root=cache, repetitions=1, seed=20261012, threads=4)
    _evaluator.prepare()


def _case(task):
    case, output, retry = task
    output = Path(output)
    part = output / 'parts' / f"{case['id']}.json"
    data = read(part)
    for row in [data['original'], *data['rows']]:
        if row['mos']['status'] != 'pending' and not (retry and row['mos']['status'] == 'failed'):
            continue
        if row['mos']['status'] == 'failed':
            row.setdefault('mos_failure_history', []).append(row['mos'])
        wave = output / 'waveforms' / case['id'] / f"{row['method']}.npy"
        seed_zero_ok = (row['method'] == 'identity' or any(
            item['seed'] == 0 and item['status'] == 'measured' for item in row.get('seed_diagnostics', [])))
        if wave.exists() and seed_zero_ok:
            row['mos'] = _evaluator.predict(np.load(wave, allow_pickle=False), case['sr'],
                                           language=case['language'], style=case['style'])
        else:
            row['mos'] = {'status': 'failed', 'value': None, 'reason': '有効なseed 0の合成波形がない'}
            logging.error('MOS入力欠落: %s', wave, stack_info=True)
        write(part, data)
        logging.info('MOS %s / %s: %s', case['id'], row['method'], row['mos']['status'])
    return case['id'], _evaluator.provenance


def score(args, cases):
    tasks = []
    for case in cases:
        part = args.output / 'parts' / f"{case['id']}.json"
        if not part.exists():
            raise ValueError(f'音響比較が未完了です: {case["id"]}')
        meta = {key: case[key] for key in ('id', 'sr', 'language', 'style')}
        tasks.append((meta, str(args.output), args.retry_failed))
    write(args.output / 'mos_execution.json', {'workers': 2, 'threads_per_worker': 4, 'started_at': now()})
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'),
                             initializer=_initialize, initargs=(str(args.mos_cache),)) as pool:
        for index, (identifier, provenance) in enumerate(pool.map(_case, tasks), 1):
            write(args.output / 'mos_provenance.json', provenance)
            logging.info('MOS完了 %s/%s: %s', index, len(tasks), identifier)
