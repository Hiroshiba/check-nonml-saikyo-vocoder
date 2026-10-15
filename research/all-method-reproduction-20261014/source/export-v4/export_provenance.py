"""固定した既知JSONだけを読む来歴転記。directory探索・wave/model読込なし。"""
from pathlib import Path

from export_types import (H, METHODS, digest, enum, fail, identifier, integer, loads,
                          obj, sequence, sha)
import provenance_base as base
import provenance_build as build
import provenance_evaluators as evaluator
import provenance_scientific as science
from provenance_links import crosslinks, input_links

STUDIES = {
    'main120': ('inputs.json', 120),
    'readout_train120': ('corpora/readout-train/inputs.json', 120),
    'asv_formal105': ('human-similarity/inputs.json', 105),
    'vctk_formal126': ('vctk-audio/inputs.json', 126),
    'asv_available100': ('human-availability100/inputs.json', 100),
    'vctk_available16': ('vctk-availability16/inputs.json', 16),
}
# 相対位置はschemaごとに固定。入力manifestで任意ファイルを選ばせない。
FIXED = {
    'input_contract': ('input-contract.json', base.INPUT_CONTRACT),
    'train_input_contract': ('readout-train/input-contract.json', base.TRAIN_INPUT_CONTRACT),
    'vctk_input_contract': ('vctk-availability16/input-contract.json', base.VCTK_INPUT_CONTRACT),
    'asv_input_contract': ('human-availability100/input-contract.json', base.ASV_INPUT_CONTRACT),
    'reference_lock': ('../../vocoderbench/references/sources.lock.json', base.REFERENCE_LOCK),
    'world_lock': ('../../vocoderbench/world.lock.json', base.WORLD_LOCK),
    'acquisition_assets': ('preparation/checkpoint-safe/evaluation-assets-no-http-headers.json', base.ACQUISITION_ASSETS),
    'mos': ('mos/configuration.json', evaluator.MOS),
    'asr': ('asr/configuration.json', evaluator.ASR),
    'speaker': ('speaker-full/configuration.json', evaluator.SPEAKER),
    'quality_assets': ('quality-inputs/assets.json', evaluator.ASSETS),
    'visqol_assets': ('vctk-audio/quality-assets.json', evaluator.ASSETS),
    'visqol_contract': ('vctk-availability16/quality-contract.json', evaluator.VISQOL),
    'visqol_build': ('preparation/visqol/provenance.json', build.BUILD),
    'visqol_dependencies': ('preparation/visqol/dependency-inventory.json', build.DEPENDENCIES),
    'visqol_source_files': ('preparation/visqol/source-files.sha256.json', sequence(build.SOURCE_FILE)),
    'derived16': ('derived16/contract.json', evaluator.DERIVATION),
    'acoustic': ('acoustic/contract.json', evaluator.ACOUSTIC),
    'controls': ('controls/contract.json', science.CONTROLS),
    'slope': ('controls-slope/contract.json', science.SLOPE),
    'edit': ('edit-quality/contract.json', science.EDIT),
    'latent': ('latent-evaluation/contract.json', science.LATENT),
    'targets': ('feature-assessment/targets/contract.json', science.TARGET),
    'abx_contract': ('feature-assessment/abx-rankings/contract.json', science.ABX),
    'readout_contract': ('feature-assessment/readout-rankings/contract.json', science.READOUT),
    'human_contract': ('human-availability100/conditional-rankings/contract.json', science.HUMAN),
}
KINDS = (*FIXED, 'inputs', 'synthesis', 'quality_result', 'main_input_processing', 'asv_input_pcm')
ENTRY = obj({'kind': enum(*KINDS), 'sha256': H, 'study': enum(*STUDIES),
    'method': enum(*METHODS), 'case': identifier, 'batch': integer, 'attempt': integer}, ('kind', 'sha256'))
MANIFEST = obj({'private_results_sha256': sha, 'run_root': lambda v, p: v if type(v) is str else fail(p, '私有run_root文字列'),
    'entries': sequence(ENTRY)}, ('private_results_sha256', 'run_root', 'entries'))


def location(entry):
    kind = entry['kind']
    if 'case' in entry and (Path(entry['case']).name != entry['case'] or entry['case'] in ('.', '..')):
        fail(kind, 'caseは単一の論理IDであり経路ではない')
    selectors = set(entry) - {'kind', 'sha256'}
    expected = {'inputs': {'study'}, 'synthesis': {'method'}, 'quality_result': {'batch', 'attempt'},
                'main_input_processing': {'case'}, 'asv_input_pcm': {'case'}}.get(kind, set())
    if selectors != expected:
        fail(kind, '既知のselectorだけを明示する')
    if kind == 'inputs':
        return STUDIES[entry['study']][0], sequence(base.INPUT)
    if kind == 'synthesis':
        return f'synthesis-contracts/{entry["method"]}.json', base.SYNTHESIS
    if kind == 'quality_result':
        if entry['batch'] > 11 or entry['attempt'] < 1:
            fail(kind, '固定12batchの保存attemptだけ許容')
        return f'quality/common-{entry["batch"]:02d}-attempt{entry["attempt"]:02d}/results.json', evaluator.QUALITY_RESULT
    if kind == 'main_input_processing':
        return f'native/hnm/{entry["case"]}/unedited.json', science.NATIVE_INPUT_RECORD
    if kind == 'asv_input_pcm':
        return f'human-similarity/audio-records/{entry["case"]}.json', build.ASV_PCM
    return FIXED[kind]


def provenance(manifest_path, expected, sources, private_report):
    blob = manifest_path.read_bytes()
    if digest(blob) != expected:
        fail('provenance manifest', 'owner固定SHA不一致')
    manifest = MANIFEST(loads(blob), 'provenance manifest')
    if manifest['private_results_sha256'] != sources.private_digest:
        fail('provenance manifest', '最終private snapshotへ結合していない')
    run = Path(manifest['run_root']).resolve()
    if sources.original_paths.get(str(run / 'inputs.json')) != private_report['input_manifest_sha256']:
        fail('provenance manifest', 'run_rootが最終snapshotの主入力と不一致')
    rows, docs, entries, seen = [], {}, {}, set()
    for entry in manifest['entries']:
        relative, schema = location(entry)
        path = (run / relative).resolve()
        identity = (entry['kind'], entry.get('study', entry.get('method', entry.get('case', entry.get('batch')))))
        if identity in seen:
            fail('provenance', '重複する来歴入力')
        seen.add(identity)
        key = entry['kind'] if identity[1] is None else ':'.join(map(str, identity))
        value = entry['sha256']
        original = sources.original_paths
        if str(path) in original and original[str(path)] != value:
            fail(key, '元snapshotの保存SHAと不一致。未到着を現在値で補完しない')
        if entry['kind'] in ('synthesis', 'mos', 'asr', 'quality_result', 'main_input_processing') and str(path) not in original:
            fail(key, '実使用sourceとして必要なsnapshot inventory結合がない')
        if value is None:
            if (entry['kind'] != 'inputs' or entry['study'] not in ('asv_formal105', 'vctk_formal126')
                    or str(path) not in original or original[str(path)] is not None or path.exists()):
                fail(key, 'nullは元未到着105/126のmanifestだけ')
            data, clean = None, None
        else:
            content = path.read_bytes()
            if len(content) > 32 * 1024 * 1024 or digest(content) != value:
                fail(key, '既知小JSONのサイズ/SHA不一致')
            data = loads(content)
            clean = schema(data, key)
        source_id = sources.add(str(path), value, 'provenance_' + entry['kind'])
        selectors = {k: entry[k] for k in ('study', 'method', 'case', 'batch', 'attempt') if k in entry}
        rows.append({'kind': entry['kind'], **selectors, 'source_id': source_id, 'sha256': value,
                     'binding': 'snapshot_inventory' if str(path) in original else 'owner_fixed_additional_evidence_with_explicit_crosschecks',
                     'status': 'original_manifest_absent' if value is None else 'saved_evidence', 'data': clean})
        docs[key], entries[key] = data, {**entry, 'source_id': source_id}
    required = [*FIXED, *(f'inputs:{s}' for s in STUDIES), *(f'synthesis:{m}' for m in METHODS),
                *(f'quality_result:{b}' for b in range(12))]
    missing = [key + ': 来歴入力未指定' for key in required if key not in docs]
    missing.extend(input_links(docs, entries, private_report))
    missing.extend(crosslinks(docs, entries))
    manifest_id = sources.add(str(manifest_path), expected, 'private_provenance_input_manifest')
    return {'schema_version': 1, 'private_results_sha256': sources.private_digest,
        'input_manifest_source_id': manifest_id, 'scientific_values_recomputed': False,
        'evidence_level': 'saved_hashes_and_settings_not_model_or_waveform_archive',
        'formal_missing_and_availability_are_distinct': True, 'records': rows,
        'missing_evidence': missing,
        'hash_scope': 'hashは元JSONの保存値。wave/model内容を再読込・再生成せず、出典JSONの実bytesだけ照合。'}, missing
