"""固定120録音の全文55録音だけを、新しい区間・試行内でASR評価する。"""
from __future__ import annotations

import hashlib
import importlib.metadata
import logging
import math
from pathlib import Path
import time
import traceback

from .chunk_contracts import digest, freeze, read, sha
from .evaluation_io import Context, ContractError, UpstreamUnavailable, add_arguments, configure_threads, raise_if_operational
from vocoderbench.logging_utils import LoggedArgumentParser, run_cli

MODEL = 'facebook/wav2vec2-base-960h'
REVISION = '22aad52d435eb6dbaf354bdad9b0da84ce7d6156'
# 同じ公式revisionの取得記録。ローカルの別モデルへの名前だけの置換を拒否する。
OFFICIAL_FILES = {
    'config.json': 'd3ec255c063d9f95057b553b19c20135b259875834a4fe9deb218a6be25b4cf3',
    'preprocessor_config.json': 'b225d617c025463b9e157e06afea8b90dc7078fc70b013c533328423e0486b4a',
    'tokenizer_config.json': 'dc790594f5bc351a4311c6624f40acd95850d4aaf2a5cb3c656c9b610720b608',
    'special_tokens_map.json': 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675',
    'vocab.json': '19727f8944fe6459fc3f240ae2c198395b740f6a029bd23e06656266b83bcf64',
    'README.md': 'fc52a0adfa64e446800f9944c6cf9b90da3127aba548860ea5714516ec8c18c7',
    'model.safetensors': '8aa76ab2243c81747a1f832954586bc566090c83a0ac167df6f31f0fa917d74a',
}


def dataset_contract(ctx, path):
    ctx.require_bound(path)
    records = read(path)['entries']
    entries = {entry['id']: entry for entry in records}
    if len(records) != 120 or len(entries) != 120 or set(entries) != {c['case'] for c in ctx.plan['cases']}:
        raise ContractError('ASR正解manifestと固定120録音が一致しません')
    selected = []
    for case in ctx.plan['cases']:
        entry = entries[case['case']]
        if (entry['speaker'], entry['excerpt_samples'], entry['sample_rate']) != (
                case['speaker'], case['samples'], 16000):
            raise ContractError('ASR正解の話者・標本数・標本化周波数が不一致です')
        source, excerpt, start = (entry[k] for k in ('source_samples', 'excerpt_samples', 'excerpt_start_sample'))
        if any(type(n) is not int for n in (source, excerpt, start)) or not 0 < excerpt <= source or not 0 <= start <= source-excerpt:
            raise ContractError('全文ASR対象を決める標本位置が不正です')
        if source == excerpt and start == 0:
            if entry['language'] != 'en' or not isinstance(entry['transcript'], str) or not entry['transcript'].strip():
                raise ContractError('全文ASR対象には公式英語正解が必要です')
            digest(entry['decoded_pcm_sha256'])
            selected.append(case['case'])
    if len(selected) != 55 or len({entries[c]['speaker'] for c in selected}) != 32:
        raise ContractError('ASR対象は固定全文55録音・32話者でなければなりません')
    return entries, selected


def asset_contract(ctx):
    options = ctx.assets['asr']
    if (options['model'], options['revision'], options['files']) != (MODEL, REVISION, OFFICIAL_FILES):
        raise ContractError('ASR公式モデル・revision・7ファイルの固定値が不一致です')
    directory = (ctx.args.assets.parent / options['directory']).resolve()
    if {p.name for p in directory.iterdir()} != set(OFFICIAL_FILES):
        raise ContractError('ASR資産directoryに欠落または未固定ファイルがあります')
    for name, expected in OFFICIAL_FILES.items():
        ctx.require_bound(directory / name)
        if sha(directory / name) != expected:
            raise ContractError(f'ASR公式資産のSHA256が不一致です: {name}')
    return directory


def initialize(directory):
    import numpy as np
    import torch
    from transformers import AutoModelForCTC, AutoProcessor
    from transformers.utils import logging as transformer_logging
    from vocoderbench.assessment.acoustics import content
    from vocoderbench.assessment.common import Inputs

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    transformer_logging.enable_propagation()
    transformer_logging.disable_default_handler()
    processor = AutoProcessor.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCTC.from_pretrained(directory, local_files_only=True,
                                          trust_remote_code=False, use_safetensors=True).eval().to('cpu')
    return {'np': np, 'torch': torch, 'processor': processor, 'model': model,
            'content': content, 'Inputs': Inputs}


def recognition_path(ctx, case, method):
    return ctx.output / 'recognitions' / f'{case}__{method}.json'


def recognize(ctx, case, method, entry, selected, state, initialization):
    row = {'case': case['case'], 'speaker': case['speaker'], 'method': method,
           'condition': 'native', 'status': 'not_applicable', 'reason_code': 'full_transcript_unavailable',
           'contract_sha256': ctx.contract_sha256, 'value': None}
    descriptor = case['reference'] if method == 'original' else case['outputs'][method]['native']
    row.update(source_descriptor=descriptor, full_transcript_eligible=selected)
    target = recognition_path(ctx, case['case'], method)
    if target.exists():
        previous = read(target)
        identity = ('case', 'speaker', 'method', 'condition', 'contract_sha256',
                    'source_descriptor', 'full_transcript_eligible')
        if any(previous.get(key) != row[key] for key in identity):
            raise ContractError('保存済みASR認識の契約・入力identityが一致しません')
        if previous['status'] not in ('measured', 'failed', 'unsupported', 'not_applicable', 'upstream_failed'):
            raise ContractError('保存済みASR認識が終端状態ではありません')
        if not selected and (previous['status'], previous['reason_code']) != (
                'not_applicable', 'full_transcript_unavailable'):
            raise ContractError('対象外のASR認識へ別の状態が保存されています')
        if descriptor['status'] == 'measured' and sha(descriptor['path']) != descriptor['sha256']:
            raise ContractError('保存済みASR認識の入力音声が変更されました')
        if previous['status'] == 'measured' and (
                not selected or previous.get('audio_sha256') != descriptor['sha256']
                or previous.get('audio_path') != descriptor['path']
                or previous.get('samples') != descriptor['samples']
                or previous.get('sample_rate') != descriptor['sample_rate']
                or not isinstance(previous.get('text'), str)):
            raise ContractError('保存済みASR認識と対応する全長音声が一致しません')
        logging.info('監査済みASR認識をそのまま継承: %s %s %s', case['case'], method, previous['status'])
        return previous
    if selected and state is None:
        row.update(status='failed', reason_code='model_initialization_failed', initialization=initialization)
    elif selected:
        try:
            wave = ctx.wave(descriptor)
        except UpstreamUnavailable:
            logging.exception('ASR入力生成が終端失敗: %s %s', case['case'], method)
            row.update(status='unsupported' if descriptor['status'] == 'unsupported' else 'upstream_failed',
                       reason_code='unsupported_operation' if descriptor['status'] == 'unsupported' else 'generation_failed',
                       upstream_status=descriptor['status'], upstream_reason=descriptor.get('reason'))
        else:
            np, torch, processor = (state[key] for key in ('np', 'torch', 'processor'))
            if descriptor['sample_rate'] != 16000:
                raise ContractError('ASRは16kHz全長のみです。自動再標本化しません')
            if method == 'original':
                if len(wave) != entry['excerpt_samples']:
                    raise ContractError('ASR原音が公式全文長ではありません')
                pcm = hashlib.sha256(np.rint(wave * 32768).astype('<i2').tobytes()).hexdigest()
                if pcm != entry['decoded_pcm_sha256']:
                    raise ContractError('ASR原音PCMが公式固定集合と一致しません')
            row.update(audio_path=descriptor['path'], audio_sha256=descriptor['sha256'],
                       samples=len(wave), sample_rate=16000,
                       source_float64_sha256=hashlib.sha256(wave.astype('<f8').tobytes()).hexdigest())
            started, cpu = time.perf_counter(), time.process_time()
            try:
                pcm32 = wave.astype('<f4')
                if not np.isfinite(pcm32).all():
                    raise ValueError('ASR用float32変換で非有限値になりました')
                prepared = processor(pcm32, sampling_rate=16000, return_tensors='pt', padding=False)
                with torch.inference_mode():
                    logits = state['model'](**prepared).logits
                    if not torch.isfinite(logits).all().item():
                        raise ValueError('ASR出力logitsが非有限です')
                    tokens = torch.argmax(logits, dim=-1)
                text = processor.batch_decode(tokens)[0]
                if not isinstance(text, str):
                    raise ValueError('ASR出力は文字列が必要です')
                row.update(status='measured', reason_code='none', text=text,
                           input_float32_sha256=hashlib.sha256(pcm32.tobytes()).hexdigest(),
                           preprocessed_float32_sha256=hashlib.sha256(prepared.input_values.numpy().astype('<f4').tobytes()).hexdigest(),
                           logit_frames=int(logits.shape[1]))
            except (OSError, MemoryError, KeyboardInterrupt, ContractError):
                raise
            except Exception as error:
                raise_if_operational(error)
                logging.exception('ASR認識失敗: %s %s', case['case'], method)
                row.update(status='failed', reason_code='metric_failed', traceback=traceback.format_exc())
            row.update(inference_wall_seconds=time.perf_counter()-started,
                       inference_process_cpu_seconds=time.process_time()-cpu)
            if sha(descriptor['path']) != descriptor['sha256']:
                raise ContractError('ASR認識中に入力音声が変更されました')
    freeze(target, row)
    return row


def assess(ctx, case, method, entry, reference, output, state):
    row = ctx.base_row(case, method, 'native', 'asr')
    row['measurement'] = None
    row['reference_recognition_sha256'] = sha(recognition_path(ctx, case['case'], 'original'))
    row['output_recognition_sha256'] = sha(recognition_path(ctx, case['case'], method))
    row['reference_status'], row['output_status'] = reference['status'], output['status']
    for recognition in (reference, output):
        if recognition['status'] != 'measured':
            row.update(status=recognition['status'], reason_code=recognition['reason_code'], value=None)
            return row
    if state is None:
        row.update(status='failed', reason_code='model_initialization_failed', value=None)
        return row
    sidecar = ctx.output / 'sidecars' / f'{case["case"]}__{method}.json'
    freeze(sidecar, {'truth': entry['transcript'], 'reference_text': reference['text'], 'output_text': output['text'],
                    'evidence_kind': 'asr_output', 'recognizer': MODEL, 'recognizer_revision': REVISION,
                    'language': 'en', 'normalization': 'nfkc_casefold_whitespace', 'word_tokenization': 'whitespace',
                    'reference_audio_sha256': reference['audio_sha256'], 'output_audio_sha256': output['audio_sha256'],
                    'contract_sha256': ctx.contract_sha256})
    job = {'transcripts': str(sidecar), 'reference': reference['audio_path'],
           'output': output['audio_path'], 'maximum_reference_cer': .20}
    try:
        result = state['content'](job, state['Inputs'](ctx.output))
        if result['status'] == 'ok' and result['reference_usable'] and math.isfinite(result['value']):
            row.update(status='measured', reason_code='none', value=result['value'])
        elif result['status'] == 'partial' and not result['reference_usable'] and result['value'] is None:
            row.update(status='reference_cer_gate_exceeded', reason_code='reference_cer_gate_exceeded', value=None)
        else:
            raise ValueError('既存content測定が想定外の終端状態です')
        row.update(measurement=result, sidecar_sha256=sha(sidecar))
    except (OSError, MemoryError, KeyboardInterrupt, ContractError):
        raise
    except Exception as error:
        raise_if_operational(error)
        logging.exception('ASR内容保持集計失敗: %s %s', case['case'], method)
        row.update(status='failed', reason_code='metric_failed', value=None, traceback=traceback.format_exc())
    return row


def main():
    parser = LoggedArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--dataset', type=Path, required=True, help='事前固定した公式全文・切出し情報のJSON')
    args = parser.parse_args()
    configure_threads()
    ctx = Context(args, 'asr')
    ctx.expected_keys = {(c['case'], m, 'native', 'asr') for c in ctx.cases for m in ctx.methods}
    entries, selected = dataset_contract(ctx, args.dataset)
    directory = asset_contract(ctx)
    if ctx.complete:
        if read(ctx.output / 'configuration.json')['dataset_sha256'] != sha(args.dataset):
            raise ContractError('検証済みASR試行と正解manifestが一致しません')
        logging.info('既存の検証済みASR試行を使用します。新規推論は行いません: %s', ctx.output)
        return int(any(r['status'] in ('failed', 'upstream_failed') for r in read(ctx.output / 'summary.json')['rows']))
    configuration = {'recognizer': MODEL, 'recognizer_revision': REVISION, 'asset_sha256': OFFICIAL_FILES,
                     'dataset_sha256': sha(args.dataset), 'contract_sha256': ctx.contract_sha256,
                     'selected_case_ids': selected, 'planned_cases': 55, 'planned_speakers': 32, 'excluded_cases': 65,
                     'normalization': 'nfkc_casefold_whitespace', 'word_tokenization': 'whitespace',
                     'maximum_reference_cer': .20, 'sample_rate': 16000,
                     'scope': 'full native wave; no crop, alignment, resampling, gain, clipping or silence removal',
                     'decoding': 'argmax logits then CTC collapse; no language model; batch_size=1',
                     'execution': {'device': 'cpu', 'float32_before_processor': True, 'torch_threads': 2,
                                   'torch_interop_threads': 1, 'local_files_only': True, 'trust_remote_code': False,
                                   'use_safetensors': True, 'inference_mode': True},
                     'retry_policy': 'audited operational resume only; preserve all terminal records and recognitions; no scientific remeasurement'}
    freeze(ctx.output / 'configuration.json', configuration)
    cached = {(case['case'], method): ctx.cached_row(case, method, 'native', 'asr')
              for case in ctx.cases for method in ctx.methods}
    state, started = None, time.perf_counter()
    initialization = ctx.initialization_failure
    if initialization is not None:
        if (initialization['status'], initialization['reason_code']) != ('failed', 'model_initialization_failed'):
            raise ContractError('継承したASR初期化失敗の状態が不正です')
        logging.info('過去の科学的ASR初期化失敗を保持し、再初期化しません')
    elif any(case['case'] in selected and cached[(case['case'], method)] is None
             for case in ctx.cases for method in ctx.methods):
        try:
            state = initialize(directory)
            packages = {name: importlib.metadata.version(name) for name in
                        ('numpy', 'scipy', 'torch', 'transformers', 'safetensors', 'tokenizers')}
            initialization = {'status': 'measured', 'reason_code': 'none', 'packages': packages}
        except (OSError, MemoryError, KeyboardInterrupt, ContractError):
            raise
        except Exception as error:
            raise_if_operational(error)
            logging.exception('ASR初期化失敗。対象の全予定行へ失敗を保存します')
            state = None
            initialization = {'status': 'failed', 'reason_code': 'model_initialization_failed',
                              'traceback': traceback.format_exc()}
        initialization['wall_seconds'] = time.perf_counter()-started
    else:
        initialization = {'status': 'not_required', 'reason': 'no unfinished eligible ASR measurements'}
    freeze(ctx.output / 'initialization.json', initialization)
    if state is not None:
        ctx.require_bound(Path(state['content'].__code__.co_filename))
        ctx.require_bound(Path(state['Inputs'].__init__.__code__.co_filename))
    rows = []
    for case in ctx.cases:
        entry, eligible = entries[case['case']], case['case'] in selected
        reference = None
        for method in ctx.methods:
            row = cached[(case['case'], method)]
            if row is None:
                if reference is None:
                    reference = recognize(ctx, case, 'original', entry, eligible, state, initialization)
                output = recognize(ctx, case, method, entry, eligible, state, initialization)
                row = assess(ctx, case, method, entry, reference, output, state)
            else:
                logging.info('監査済みASR終端測定をそのまま継承: %s %s %s', case['case'], method, row['status'])
            ctx.record(row)
            rows.append(row)
            logging.info('ASR %s %s: %s', case['case'], method, row['status'])
    expected = {(c['case'], m) for c in ctx.cases for m in ctx.methods}
    if len(rows) != len(expected) or {(r['case'], r['method']) for r in rows} != expected:
        raise ContractError('ASR区間の全予定行が揃っていません')
    if sha(args.dataset) != configuration['dataset_sha256']:
        raise ContractError('ASR評価中に正解manifestが変更されました')
    asset_contract(ctx)
    receipt = ctx.finish(rows)
    logging.info('ASR区間の終端証跡: %s', receipt)
    return int(any(row['status'] in ('failed', 'upstream_failed') for row in rows))


if __name__ == '__main__':
    raise SystemExit(run_cli(main, 'chunk-asr'))
