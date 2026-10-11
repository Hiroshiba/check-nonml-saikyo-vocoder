"""音声ごとの依存関係を保って、音響測定とMOS測定を並行する。"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
import multiprocessing
from pathlib import Path

from .benchmark_io import external_candidate, now, write
from .logging_utils import configure_logging
from .mos_batch import _case as mos_case, _initialize as initialize_mos

_candidate = None


def _initialize_acoustic(path):
    global _candidate
    configure_logging('acoustic-worker')
    _candidate = external_candidate(path)


def _acoustic(task):
    from .benchmark import acoustic_case
    case, output, retry = task
    acoustic_case(case, _candidate, Path(output), retry)
    return {key: case[key] for key in ('id', 'sr', 'language', 'style')}


def execute(args, cases):
    context = multiprocessing.get_context('spawn')
    write(args.output / 'pipeline_execution.json', {
        'started_at': now(), 'acoustic_workers': 2, 'mos_workers': 2, 'mos_threads_per_worker': 4})
    with ProcessPoolExecutor(max_workers=2, mp_context=context, initializer=_initialize_acoustic,
                             initargs=(str(args.candidate_package),)) as acoustic, \
            ProcessPoolExecutor(max_workers=2, mp_context=context, initializer=initialize_mos,
                                initargs=(str(args.mos_cache),)) as mos:
        pending = [acoustic.submit(_acoustic, (case, str(args.output), args.retry_failed)) for case in cases]
        predictions = []
        for index, future in enumerate(as_completed(pending), 1):
            case = future.result()
            predictions.append(mos.submit(mos_case, (case, str(args.output), args.retry_failed)))
            logging.info('音響測定 %s/%s 完了、MOSへ: %s', index, len(cases), case['id'])
        for index, future in enumerate(as_completed(predictions), 1):
            identifier, provenance = future.result()
            write(args.output / 'mos_provenance.json', provenance)
            logging.info('MOS %s/%s 完了: %s', index, len(cases), identifier)
