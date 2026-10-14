"""新runの実payload入出力証跡と派生一時ファイルの解放台帳。旧原文の復元ではない。"""
from __future__ import annotations

import json
from pathlib import Path
import time

from all_metrics_common import freeze, now, read
from vocoderbench.quality_core import sha256, write_json

TERMINAL = {'measured', 'failed', 'not_applicable'}
TEMPORARY_NAMES = {'quantized_float16.npz', 'quantized_float32.npz',
                   'interpolation_gain_minus6_endpoint.npz', 'interpolation_input_gain_alpha0p5.npz'}


def structure_hash(value):
    import hashlib
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def payload_identity(payload):
    return {key: payload[key] for key in ('path', 'sha256', 'bytes')}


def checked_file(payload):
    path = Path(payload['path'])
    if not path.is_file() or path.stat().st_size != payload['bytes'] or sha256(path) != payload['sha256']:
        raise ValueError(f'実payloadのfile SHA/bytes不一致: {path}')
    return path


def checked_reference(reference):
    path = Path(reference['path'])
    if sha256(path) != reference['sha256']:
        raise ValueError(f'永久証跡のhash不一致: {path}')
    return read(path)


def release_directory(root, method, case, payload):
    return Path(root).resolve() / 'latent-payload-releases' / method / case / payload['sha256']


def evidence(args, spec, condition, value):
    """呼出側の実保存・読込・import後に、不変の内容hash付き証跡を保存する。"""
    payload = value.get('actual_payload', value.get('payload'))
    if not payload:
        raise ValueError('実保存payloadを指定しない証跡は受け付けません')
    checked_file(payload)
    if not value.get('contract_sha256') or value.get('seed') != args.seed:
        raise ValueError('証跡の科学契約またはseedが不足・不一致です')
    quantization = value.get('quantization')
    if quantization is not None:
        a, b = quantization['native_decoder_arrays'], quantization['restored_decoder_arrays']
        if quantization['restored_decoder_input_identical'] != (a == b):
            raise ValueError('量子化のcanonical同一性宣言がhashと不一致です')
        if quantization['payload_file_bytes'] != payload['bytes']:
            raise ValueError('量子化の実容器bytesとpayloadが不一致です')
    endpoint = value.get('reencoded_endpoint_provenance')
    if endpoint:
        checked_reference(endpoint)
    record = {**value, 'schema_version': 1, 'case': spec['id'], 'method': args.method,
        'condition': condition, 'run_root': str(args.output_root.resolve()),
        'source_input_sha256': spec['sha256'],
        'payload_retention': 'temporary derived payload; retained=false is a policy, not an IO failure',
        'evidence_scope': 'caller-reported actual write-close-read-import and canonical hashes; not a second decode or a test'}
    digest = structure_hash(record)
    path = args.output_root / 'latent-provenance' / args.method / spec['id'] / f'{condition}-{digest}.json'
    freeze(path, record)
    return {'path': str(path), 'sha256': sha256(path), 'semantic_sha256': digest,
            'release_ledger_directory': str(release_directory(args.output_root, args.method, spec['id'], payload))}


def verify_native(row):
    source = row.get('native_representation')
    if not source:
        return
    path = Path(source['path'])
    if sha256(path) != source['sha256']:
        raise ValueError('不変の元native表現hashが変わりました')
    if source.get('record_sha256') and sha256(path.with_suffix('.json')) != source['record_sha256']:
        raise ValueError('不変の元native表現記録hashが変わりました')


def verify_release(payload, proof, reference):
    directory = release_directory(proof['run_root'], proof['method'], proof['case'], payload)
    if reference.get('release_ledger_directory') != str(directory):
        raise ValueError('永久証跡の派生payload解放先が不一致です')
    for path in sorted(directory.glob('*.intent.json'), reverse=True):
        intent = read(path)
        if (intent.get('actual_payload') != payload_identity(payload)
                or intent.get('case') != proof['case'] or intent.get('method') != proof['method']
                or intent.get('contract_sha256') != proof['contract_sha256']):
            continue
        completion = path.with_name(path.name.replace('.intent.json', '.completed.json'))
        if completion.exists():
            result = read(completion)
            if result.get('intent_sha256') != sha256(path) or result.get('payload_sha256') != payload['sha256']:
                raise ValueError('派生payload解放完了記録のhashが不一致です')
            if result.get('status') not in ('released', 'absence_observed_after_recorded_intent'):
                raise ValueError('派生payloadの解放完了状態が不正です')
            return {'status': result['status'], 'path': str(completion), 'sha256': sha256(completion)}
        return {'status': 'release_intent_without_final_confirmation', 'path': str(path), 'sha256': sha256(path)}
    raise ValueError('retained=falseのpayloadが不在ですが対応する解放台帳がありません')


def verify_identity(row, proof):
    quantization = row.get('quantization')
    if quantization is None:
        return
    if quantization != proof.get('quantization'):
        raise ValueError('復号行と永久証跡の量子化条件が一致しません')
    base, _, control = row['condition'].partition('__')
    operation = row.get('representation_operation', {})
    if (proof.get('condition') != base or operation.get('control_after_import') != (control or 'unedited')
            or operation.get('payload') != row['feature_artifact']['path']):
        raise ValueError('量子化点と読込後操作の対応が永久証跡と不一致です')
    a, b = quantization['native_decoder_arrays'], quantization['restored_decoder_arrays']
    if quantization['restored_decoder_input_identical'] != (a == b):
        raise ValueError('canonical同一性が保存hashと矛盾しています')
    assets = Path(quantization['shared_asset_manifest'])
    if sha256(assets) != quantization['shared_asset_manifest_sha256']:
        raise ValueError('固定共有資産manifestのhash不一致')
    if row.get('origin') == 'existing_verified_waveform_identical_decoder_input':
        if not quantization['restored_decoder_input_identical']:
            raise ValueError('canonical入力が異なる量子化点をnative波形引用にしません')
        prior = checked_reference({'path': row['reused_waveform_record'],
                                   'sha256': row['reused_waveform_record_sha256']})
        if prior.get('status') != 'measured':
            raise ValueError('引用元波形は成功済みでなければなりません')
        if any(prior.get(key) != row.get(key) for key in ('case', 'method', 'seed')):
            raise ValueError('引用元波形のcase/method/seedが不一致です')
        if prior.get('condition') != (control or 'unedited'):
            raise ValueError('量子化後の操作と引用元native操作が一致しません')
        keys = ('file_sha256', 'float64_sha256', 'sample_rate', 'samples')
        if any(prior['audio'][key] != row['audio'][key] for key in keys):
            raise ValueError('analytic identityの前提となるPCM引用が不一致です')
        if sha256(prior['audio']['path']) != prior['audio']['file_sha256']:
            raise ValueError('引用元の実波形file hash不一致')


def verify_retained_evidence(row):
    """成功行の実波形と不変証跡を照合。解放を未測定や測定値0へ変えない。"""
    if row.get('status') != 'measured':
        return {'status': 'not_a_success_row', 'source_status': row.get('status')}
    verify_native(row)
    if row.get('audio') and sha256(row['audio']['path']) != row['audio']['file_sha256']:
        raise ValueError('保存成功波形のfile hash不一致')
    payload = row.get('feature_artifact')
    if not payload:
        if row.get('quantization'):
            raise ValueError('量子化の成功行にpayload証跡がありません')
        return {'status': 'existing_native_endpoint_without_derived_payload'}
    if payload.get('retained', True):
        checked_file(payload)
        return {'status': 'retained_file_verified'}
    reference = row.get('provenance')
    if not reference:
        raise ValueError('retained=falseの成功行に永久入出力証跡がありません')
    proof = checked_reference(reference)
    actual = proof.get('actual_payload', proof.get('payload'))
    if not actual or payload_identity(actual) != payload_identity(payload):
        raise ValueError('成功行と永久入出力証跡のpayloadが一致しません')
    for key in ('case', 'method', 'contract_sha256', 'seed'):
        if proof.get(key) != row.get(key):
            raise ValueError(f'永久入出力証跡と復号行の条件が一致しません: {key}')
    if proof.get('source_input_sha256') != row.get('input_source_sha256'):
        raise ValueError('元入力と永久証跡のhash不一致')
    if proof.get('native_representation_sha256') not in (None, row['native_representation']['sha256']):
        raise ValueError('永久証跡の元native表現hash不一致')
    verify_identity(row, proof)
    if proof.get('reencoded_endpoint_provenance'):
        endpoint = checked_reference(proof['reencoded_endpoint_provenance'])
        if any(endpoint.get(key) != proof.get(key) for key in ('case', 'method', 'contract_sha256', 'seed', 'source_input_sha256')):
            raise ValueError('補間端点の永久証跡が中間点と不一致です')
        recorded = row.get('reencoded_endpoint', {})
        if recorded.get('decoder_arrays') != endpoint.get('decoder_arrays'):
            raise ValueError('補間端点canonical hashと永久証跡が不一致です')
        if proof.get('alpha') == 1.0 and proof.get('decoder_arrays') != endpoint.get('decoder_arrays'):
            raise ValueError('alpha1の復号入力が実再解析端点と一致しません')
    if Path(payload['path']).exists():
        checked_file(payload)
        state = {'status': 'temporary_payload_still_present'}
    else:
        state = verify_release(payload, proof, reference)
    return {'status': 'permanent_actual_io_evidence_verified', 'retained': False, 'release': state}


def release_payload(payload, targets, args, spec, reason):
    """全依存行保存後、派生NPZだけを解放。nativeと結果JSONは変更しない。"""
    if payload.get('retained', False) is not False:
        return {'status': 'retained_by_policy'}
    path = Path(payload['path'])
    expected_folder = args.output_root / 'native' / args.method / spec['id']
    if path.name not in TEMPORARY_NAMES or path.parent.resolve() != expected_folder.resolve() or path.is_symlink():
        raise ValueError('解放対象はこのcaseに属する指定済み派生NPZだけです。元nativeは保持します')
    states, contract_hashes, outcome_count, io_proofs = [], set(), 0, []
    for target in map(Path, targets):
        if not target.exists():
            return {'status': 'pending_terminal_records', 'missing': str(target)}
        row = read(target)
        if row.get('case') != spec['id'] or row.get('method') != args.method:
            raise ValueError('解放前の依存行case/method不一致')
        if row.get('status') is None and target.name == 'interpolation_gain_minus6_endpoint.json':
            if payload_identity(row['payload']) != payload_identity(payload):
                raise ValueError('再解析端点metadataのpayload不一致')
        elif row.get('status') not in TERMINAL:
            return {'status': 'pending_terminal_records', 'source_status': row.get('status'), 'path': str(target)}
        else:
            outcome_count += 1
            if row['status'] == 'measured':
                verify_retained_evidence(row)
        contract_hashes.add(row.get('contract_sha256'))
        states.append({'path': str(target), 'sha256': sha256(target), 'status': row.get('status', 'endpoint_metadata'),
                       'permanent_provenance': row.get('provenance')})
        if row.get('provenance'):
            proof = checked_reference(row['provenance'])
            actual = proof.get('actual_payload', proof.get('payload'))
            if actual and payload_identity(actual) == payload_identity(payload):
                if (proof.get('case'), proof.get('method'), proof.get('seed'), proof.get('source_input_sha256')) != (
                        spec['id'], args.method, args.seed, spec['sha256']):
                    raise ValueError('解放前の不変IO証跡とcase/method/seed/sourceが不一致')
                if proof.get('contract_sha256') != row.get('contract_sha256'):
                    raise ValueError('解放前の不変IO証跡とterminal行の契約が不一致')
                quantization = proof.get('quantization')
                canonical = quantization.get('restored_decoder_arrays') if quantization else proof.get('decoder_arrays')
                if canonical and canonical.get('sha256') and canonical.get('array_count', 0) > 0:
                    io_proofs.append(row['provenance'])
    if not outcome_count or len(contract_hashes) != 1 or None in contract_hashes:
        raise ValueError('解放前に同一契約の全依存条件のterminal記録が必要です')
    if not io_proofs:
        checked_file(payload)
        retained = (args.output_root / 'latent-payload-retention' / args.method / spec['id']
                    / payload['sha256'] / f'{structure_hash(states)}.json')
        freeze(retained, {'schema_version': 1, 'status': 'retained_failure_payload_without_complete_io_proof',
            'case': spec['id'], 'method': args.method, 'actual_payload': payload_identity(payload), 'retained': True,
            'contract_sha256': next(iter(contract_hashes)), 'terminal_records': states,
            'reason': '実read-import/canonical証跡が成立する前の失敗payloadを未診断のまま解放しません。'})
        return {'status': 'retained_failure_payload_without_complete_io_proof', 'record': str(retained)}
    directory = release_directory(args.output_root, args.method, spec['id'], payload)
    if not path.exists():
        for previous in sorted(directory.glob('*.intent.json'), reverse=True):
            intent = read(previous)
            if intent.get('actual_payload') == payload_identity(payload):
                completed = previous.with_name(previous.name.replace('.intent.json', '.completed.json'))
                if not completed.exists():
                    write_json(completed, {'status': 'absence_observed_after_recorded_intent',
                        'intent_sha256': sha256(previous), 'payload_sha256': payload['sha256'], 'finished_at_utc': now()})
                return {'status': 'already_absent_with_release_evidence', 'record': str(completed)}
        raise ValueError('派生payloadが不在ですが既存解放記録がありません')
    checked_file(payload)
    intent_path = directory / f'{time.time_ns()}.intent.json'
    freeze(intent_path, {'schema_version': 1, 'case': spec['id'], 'method': args.method,
        'contract_sha256': next(iter(contract_hashes)), 'actual_payload': payload_identity(payload),
        'retained': False, 'successful_decode_present': any(row['status'] == 'measured' for row in states),
        'permanent_actual_io_proofs': io_proofs,
        'status': 'release_intent', 'started_at_utc': now(), 'terminal_records': states,
        'reason': reason, 'native_representation_and_waves_unchanged': True,
        'source_sha256': sha256(__file__)})
    path.unlink()
    completion = intent_path.with_name(intent_path.name.replace('.intent.json', '.completed.json'))
    freeze(completion, {'status': 'released', 'intent_sha256': sha256(intent_path),
        'payload_sha256': payload['sha256'], 'finished_at_utc': now()})
    return {'status': 'released', 'record': str(completion), 'sha256': sha256(completion)}
