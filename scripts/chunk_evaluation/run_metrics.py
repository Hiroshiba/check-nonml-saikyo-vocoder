"""固定区間波形を既存指標で測る。合成器・新しい指標数式は含めない。"""
import logging
import time
import traceback

from .chunk_contracts import CONDITIONS, ContractError
from .evaluation_io import Context, UpstreamUnavailable, add_arguments, configure_threads, raise_if_operational
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli


class Pair:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def pair(self, job, same_length=True):
        return self.x, self.y, 16000


def main():
    parser = LoggedArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--metric', required=True,
                        choices=('acoustic', 'erb', 'scoreq', 'utmosv2', 'speaker_ecapa', 'pitch'))
    parser.add_argument('--conditions', nargs='+', choices=CONDITIONS, default=['native'])
    args = parser.parse_args()
    configure_threads()
    import numpy as np
    if args.conditions not in (['native'], ['pitch_minus3', 'pitch_plus3']):
        raise ContractError('nativeまたは固定±3半音の組を指定してください')
    edited = args.conditions != ['native']
    if (edited and args.metric in ('acoustic', 'erb', 'scoreq')) or (not edited and args.metric == 'pitch'):
        raise ContractError('指標と条件の組が計画外です')
    stage_id = args.metric+('-edited' if edited else '')
    ctx = Context(args, stage_id)
    if ctx.complete:
        logging.info('既存stage終端を保持。再測定なし: %s', ctx.output)
        return
    from vocoderbench.quality_backends import EcapaSimilarity, ErbDistance, ScoreqReference, UtmosLocal
    from vocoderbench.quality_core import NotApplicable
    from vocoderbench.assessment.common import NotApplicable as AcousticNA
    from vocoderbench.assessment.acoustics import auditory
    from vocoderbench.assessment.controls import pitch
    from vocoderbench.extended_metrics import measure_extended
    from vocoderbench.metrics import compare_waveforms
    classes = {'erb': ErbDistance, 'scoreq': ScoreqReference,
               'utmosv2': UtmosLocal, 'speaker_ecapa': EcapaSimilarity}
    include_original = args.metric == 'utmosv2' and not edited
    methods = ctx.methods+(['original'] if include_original else [])
    ctx.expected_keys = {(c['case'], m, condition, args.metric) for c in ctx.cases
                         for m in methods for condition in args.conditions}
    options = ctx.asset_options(args.metric)
    backend, initialization_error, rows = None, ctx.initialization_failure, []
    if initialization_error is not None:
        from .chunk_contracts import freeze
        freeze(ctx.output/'initialization.json', initialization_error)
    work = ctx.output/'work'
    work.mkdir()
    for case in ctx.cases:
        for method in methods:
            for condition in args.conditions:
                previous = ctx.cached_row(case, method, condition, args.metric)
                if previous is not None:
                    ctx.record(previous)
                    rows.append(previous)
                    continue
                row = ctx.base_row(case, method, condition, args.metric)
                try:
                    output = case['reference'] if method == 'original' else case['outputs'][method][condition]
                    reference = case['outputs'][method]['native'] if args.metric == 'pitch' else case['reference']
                    x, y = ctx.wave(reference), ctx.wave(output)
                    row['length_difference_samples'] = len(y)-len(x)
                    row['output_file_sha256'] = output['sha256']
                    row['reference_file_sha256'] = reference['sha256']
                    common = not edited and args.metric != 'utmosv2'
                    if common:
                        n = case['common_samples']
                        if min(len(x), len(y)) < n:
                            raise UpstreamUnavailable('not_applicable', 'output_shorter_than_fixed_window')
                        x, y = x[:n], y[:n]
                    if args.metric == 'pitch' and len(x) != len(y):
                        raise UpstreamUnavailable('not_applicable', 'length_mismatch')
                    import hashlib
                    row['identity'] = {'scope': 'legacy_common_prefix' if common else 'full_length',
                                       'evaluated_samples': len(y), 'sample_rate': 16000,
                                       'reference_used': args.metric != 'utmosv2',
                                       'reference_pcm_sha256': hashlib.sha256(x.astype('<f8').tobytes()).hexdigest(),
                                       'output_pcm_sha256': hashlib.sha256(y.astype('<f8').tobytes()).hexdigest(),
                                       'output_float32_sha256': hashlib.sha256(y.astype('<f4').tobytes()).hexdigest(),
                                       'normalization': False, 'alignment': False,
                                       'silence_removal': False, 'threads': 2, 'extraction_seed': 20261012}
                    if args.metric in classes and backend is None:
                        if initialization_error is not None:
                            raise RuntimeError('モデル初期化失敗を保持: '+str(initialization_error))
                        tick = time.perf_counter()
                        try:
                            backend = classes[args.metric](options, args.assets.parent, work, 2)
                        except (OSError, MemoryError, ContractError):
                            raise
                        except Exception as error:
                            raise_if_operational(error)
                            initialization_error = {'status': 'failed', 'reason_code': 'model_initialization_failed',
                                                    'traceback': traceback.format_exc()}
                            from .chunk_contracts import freeze
                            freeze(ctx.output/'initialization.json', initialization_error)
                            logging.exception('モデル初期化失敗')
                            raise
                        from .chunk_contracts import freeze
                        freeze(ctx.output/'initialization.json',
                               {'wall_seconds': time.perf_counter()-tick, 'provenance': backend.provenance})
                    tick = time.perf_counter()
                    if args.metric == 'acoustic':
                        row['measurement'] = compare_waveforms(x, y, 16000)
                        row['extended'] = measure_extended(x, y, 16000, include_pitch=True,
                                                           include_temporal=True, is_speech=True)
                        try:
                            row['auditory_local'] = auditory({}, Pair(x, y))
                        except AcousticNA as error:
                            row['auditory_local'] = {'status': 'not_applicable', 'value': None, 'reason': str(error)}
                    elif args.metric == 'pitch':
                        detail = pitch({'target_cents': -300 if condition == 'pitch_minus3' else 300}, Pair(x, y))
                        row.update(value=detail['value'], detail=detail)
                        if detail['status'] != 'ok':
                            row.update(status='not_applicable', reason_code='insufficient_voiced_support')
                    else:
                        value, detail = backend.score(None if args.metric == 'utmosv2' else x, y, 16000)
                        if not np.isfinite(value):
                            raise ValueError('指標値が非有限数です')
                        row.update(value=float(value), detail=detail)
                    if row['status'] == 'pending':
                        row.update(status='measured', reason_code='none')
                    row['wall_seconds'] = time.perf_counter()-tick
                except (ContractError, OSError, MemoryError):
                    logging.exception('科学契約不一致でstage全体停止')
                    raise
                except UpstreamUnavailable as error:
                    status = error.status if error.status in ('unsupported', 'not_applicable') else 'upstream_failed'
                    row.update(status=status, reason_code=str(error), value=None)
                except (NotApplicable, AcousticNA) as error:
                    row.update(status='not_applicable', reason_code='outside_scope', reason=str(error), value=None)
                except Exception as error:
                    raise_if_operational(error)
                    logging.exception('個別指標処理失敗: %s %s %s', case['case'], method, condition)
                    row.update(status='failed', reason_code='model_initialization_failed' if initialization_error else 'metric_failed',
                               reason=str(error), traceback=traceback.format_exc(), value=None)
                ctx.record(row)
                rows.append(row)
    ctx.finish(rows)


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-metrics'))
