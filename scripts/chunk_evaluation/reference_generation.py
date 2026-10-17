"""PML現baseと固定WORLDを12録音ずつ生成する公開用routing。"""
import argparse
import copy
import logging
from pathlib import Path
import time
import traceback

from .chunk_contracts import ContractError, sha
from .reference_context import GenerationContext, configure_threads, save_json


class ScientificFailure(Exception):
    """音声科学APIで発生した、個別録音・条件の明示的失敗。"""


def timed(costs, name, function, *, scientific=False):
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        try:
            return function()
        except (ValueError, FloatingPointError, RuntimeError) as error:
            if not scientific or isinstance(error, ContractError):
                raise
            raise ScientificFailure(str(error)) from error
    finally:
        costs[name + '_wall_seconds'] = time.perf_counter() - wall
        costs[name + '_cpu_seconds'] = time.process_time() - cpu


def descriptor(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def audit(params, method):
    """全録音の元encode特徴量を後段へ渡す。指標値は計算しない。"""
    import hashlib
    import numpy as np
    fields = ('fwcep', 'noise_mask', 'f0') if method == 'pml' else (
        'f0', 'time', 'spectral_envelope', 'aperiodicity')
    arrays = {}
    for name in fields:
        value = np.ascontiguousarray(getattr(params, name))
        arrays[name] = {'shape': list(value.shape), 'dtype': value.dtype.str,
                        'sha256': hashlib.sha256(value.tobytes()).hexdigest()}
    return {'n_samples': params.n_samples, 'sample_rate': params.sample_rate,
            'frames': len(params.f0), 'fields': arrays,
            'seed': params.seed if method == 'pml' else None,
            'origin': 'original_input_encode_saved_and_reloaded'}


def input_wave(ctx, case):
    import numpy as np
    row = ctx.inputs[case]
    path = ctx.args.input_root / row['path']
    if sha(path) != row['expected_npy_sha256']:
        raise ContractError('解析直前の原音SHA不一致')
    x = np.load(path, allow_pickle=False)
    if x.dtype != np.float64 or x.shape != (row['samples'],) or not np.isfinite(x).all():
        raise ContractError('元入力のdtype/shape/有限性が契約と異なります')
    return x


def run_case(ctx, case):
    import numpy as np
    from vocoderbench import pml, world

    api = pml if ctx.args.method == 'pml' else world
    folder = ctx.output / 'cases' / case
    folder.mkdir(parents=True, exist_ok=False)
    old = ctx.previous.get(case)
    if old and not old.get('partial_case'):
        ctx.verify()
        record = copy.deepcopy(old)
        record['reused_verified_terminal_case'] = True
        ctx.save_case(record)
        return record
    conditions = [('native', 0), ('pitch_minus3', -3), ('pitch_plus3', 3)] if api is pml else [('native', 0)]
    record = {'case': case, 'speaker': ctx.cases[case]['speaker'], 'method': ctx.args.method,
              'input_sha256': ctx.cases[case]['input_sha256'], 'common_samples': ctx.cases[case]['common_samples'],
              'costs': {}, 'rows': [], 'artifacts': [], 'payload': None, 'encode_status': 'pending', 'run_plan_sha256': ctx.plan_sha}
    save_json(folder / 'started.json', {'case': case, 'run_plan_sha256': ctx.plan_sha,
                                      'input_sha256': record['input_sha256']})
    x = timed(record['costs'], 'input_load', lambda: input_wave(ctx, case))
    if old:
        record['payload'] = copy.deepcopy(old['payload'])
        record['encode_audit'] = copy.deepcopy(old.get('encode_audit'))
        record['encode_status'] = old['encode_status']
        record['encode_reused_from'] = old.get('payload')
        record['encode_traceback'] = old.get('encode_traceback')
        record['previous_encode_costs'] = old.get('previous_encode_costs', old['costs'])
        if record['payload'] and sha(record['payload']['path']) != record['payload']['sha256']:
            raise ContractError('再試行元payloadのSHA不一致')
    else:
        try:
            params = timed(record['costs'], 'analysis',
                           lambda: pml.encode(x, 16000, seed=0) if api is pml else world.encode(x, 16000),
                           scientific=True)
        except ScientificFailure:
            logging.exception('個別解析の失敗: %s', case)
            record['encode_status'] = 'failed'
            record['encode_traceback'] = traceback.format_exc()
        else:
            payload = folder / ('parameters.pml' if api is pml else 'parameters.world.npz')
            timed(record['costs'], 'payload_save', lambda: api.save(params, payload))
            del params
            params = timed(record['costs'], 'payload_load', lambda: api.load(payload))
            if params.n_samples != len(x) or params.sample_rate != 16000 or (api is pml and params.seed != 0):
                raise ContractError('保存後のN/SR/seedが異なります')
            record.update(payload=descriptor(payload), encode_status='measured',
                          encode_audit=audit(params, ctx.args.method))
    if old:
        record['artifacts'] = copy.deepcopy(old['artifacts'])
    save_json(folder / 'encode.json', record)
    for condition, semitones in conditions:
        previous = next((r for r in old['rows'] if r['condition'] == condition), None) if old else None
        if previous and previous['status'] in ('measured', 'failed'):
            row = copy.deepcopy(previous)
            row['reused_verified_terminal_condition'] = True
            save_json(folder / (condition + '.json'), row)
            record['rows'].append(row)
            continue
        row = {'case': case, 'method': ctx.args.method, 'condition': condition,
               'status': 'failed', 'reason_code': 'generation_failed', 'wave': None, 'costs': {}}
        if record['encode_status'] != 'measured':
            row['upstream_failure'] = 'original_encode'
            save_json(folder / (condition + '.json'), row)
            record['rows'].append(row)
            continue
        # 毎条件で元保存payloadを再読込。±3間の逐次編集や再解析をしない。
        payload = record['payload']
        if sha(payload['path']) != payload['sha256']:
            raise ContractError('条件処理前に元payloadが変化しました')
        params = timed(row['costs'], 'original_payload_load', lambda: api.load(payload['path']))
        try:
            if semitones:
                params = timed(row['costs'], 'editor',
                               lambda: pml.edit_parameters(params, pitch_semitones=semitones), scientific=True)
                edited = folder / (condition + '.pml')
                timed(row['costs'], 'edited_payload_save', lambda: api.save(params, edited))
                params = timed(row['costs'], 'edited_payload_load', lambda: api.load(edited))
                if params.seed != 0 or params.n_samples != len(x) or params.pitch_shift_semitones != semitones:
                    raise ContractError('編集後保存payloadのseed/N/編集量が異なります')
                row['edited_payload'] = descriptor(edited)
            y = timed(row['costs'], 'decode',
                      lambda: pml.decode(params, seed=0) if api is pml else world.decode(params), scientific=True)
        except ScientificFailure:
            logging.exception('個別復号・編集の失敗: %s %s', case, condition)
            row['traceback'] = traceback.format_exc()
        else:
            wave_path = folder / (condition + '.npy')
            timed(row['costs'], 'wave_save', lambda: np.save(wave_path, y, allow_pickle=False))
            row['generated_wave'] = descriptor(wave_path)
            if y.shape != x.shape or y.dtype != np.float64 or not np.isfinite(y).all():
                row['reason_code'] = 'length_mismatch' if y.shape != x.shape else 'generation_failed'
                row['validation_failure'] = 'finite_mono_float64_same_N_required'
            else:
                row.update(status='measured', reason_code='none',
                           wave={**descriptor(wave_path), 'samples': len(y), 'sample_rate': 16000,
                                 'dtype': y.dtype.str})
        if sha(payload['path']) != payload['sha256']:
            raise ContractError('条件処理中に元payloadが変化しました')
        save_json(folder / (condition + '.json'), row)
        record['rows'].append(row)
    paths = {str(p.resolve()) for p in folder.rglob('*') if p.is_file()}
    if record['payload']:
        paths.add(record['payload']['path'])
    for row in record['rows']:
        if row['wave']:
            paths.add(row['wave']['path'])
    if old:
        paths.update(r['path'] for r in old['artifacts'])
    record['artifacts'] = [descriptor(p) for p in sorted(paths)]
    ctx.verify()
    record['validation_state'] = 'validated_end'
    ctx.save_case(record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'bindings', 'inputs', 'input-root', 'authorization', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--chunk', required=True)
    parser.add_argument('--method', choices=('pml', 'world_harvest'), required=True)
    parser.add_argument('--resume-interrupted', action='store_true')
    args = parser.parse_args()
    configure_threads()
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ctx = GenerationContext(args)
    if ctx.complete:
        print(ctx.output / 'receipt.json')
        return
    handler = logging.FileHandler(ctx.output / 'generation.log', mode='x', encoding='utf-8')
    logging.getLogger().addHandler(handler)
    logging.captureWarnings(True)
    try:
        # 依存欠落・共有libraryロード失敗は個別科学失敗として捕捉しない。
        import pyreaper  # noqa: F401
        import pyworld  # noqa: F401
        from vocoderbench import world
        world._lib()
        records = []
        for case in ctx.chunk['case_ids']:
            ctx.verify()
            records.append(run_case(ctx, case))
            logging.info('%s %s 記録保存', args.method, case)
        handler.flush()
        print(ctx.finish(records))
    except BaseException:
        logging.exception('運用・契約中断。既存attemptを保持し、終端receiptは発行しません')
        raise
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
