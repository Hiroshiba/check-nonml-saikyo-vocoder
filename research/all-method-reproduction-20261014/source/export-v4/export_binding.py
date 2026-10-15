"""専用scalarの出典を最終snapshotと固定集合へ結合する。科学値は計算しない。"""
from pathlib import Path

from export_types import METHODS, digest, fail, identifier, loads, sequence, sha

ABX_RESULT_KEYS = (
    'analysis_complete artifacts bootstrap calibration_cohort cohorts common_triplets_sha256 '
    'contract_sha256 definitions estimands excluded_triplets exclusion_counts_by_method '
    'exclusion_counts_can_overlap extraction_exclusions finished_at_utc formal_base limits '
    'method_set methods official_source_audit_scope ranking raw_sources status strata_sha256 '
    'triplet_micro_auxiliary'
)
ABX_CONTRACT_KEYS = (
    'bootstrap_replicates bootstrap_seed calibration_cohort_sha256 distance downsampling '
    'estimands eval_records implementation_origin manifest_sha256 max_dtw_cells methods '
    'runtime scale schema_version source_audit_sha256 sources_sha256 tie_atol tie_error '
    'token_window train_exclusions train_records'
)
ABX_MANIFEST_KEYS = (
    'all_items counts created_at_utc excluded frozen_audio_manifest_sha256 id items label_file '
    'label_scope label_sha256 license scope_limit selection_plan_sha256 source_url triplets '
    'unmatched_utterances'
)
READOUT_RESULT_KEYS = (
    'analysis_complete artifacts calibration_cohort contract_sha256 estimands extraction_exclusions '
    'finished_at_utc formal_base limits methods models_sha256 predictions_sha256 raw_recordings_sha256 '
    'status train_target_support'
)
VCTK_RESULT_KEYS = 'all16 generated_at_utc quality_contract_sha256 recommended_duration results_sha256 source_sha256'
VCTK_GROUP_KEYS = (
    'admissible_status aggregation available_case_auxiliary bootstrap conditional direction id '
    'method_states methods planned_case_ids planned_recordings_per_method planned_speakers_per_method '
    'primary rankable rows terminal'
)
VCTK_CONTRACT_KEYS = (
    'alignment assets_path assets_sha256 backend_provenance comparison_samples derivative_storage '
    'environment gain_normalization input_contract_sha256 inputs_sha256 interval metric '
    'minimum_common_seconds minimum_coverage_each_waveform native_amplitude_rule pcm16_rule '
    'planned_methods planned_recordings planned_speakers ranking recommended_duration_stratum '
    'repetitions_after_first resampling sample_rate schema_version score_selection source_sha256 '
    'threads time_warp use_lattice_model use_speech_mode'
)
ASV_RESULT_KEYS = (
    'all8_primary_preserved_at all8_primary_sha256 analysis_complete bootstrap calibration_artifacts '
    'calibration_cohort_sha256 citations cohort conditional_method_selection conditional_selection_bias '
    'contract_sha256 estimands finished_at_utc formal_base limits methods ranking_scope selection_timing '
    'status uncertainty'
)
ASV_CONTRACT_KEYS = (
    'calibration_cohort_sha256 common_pairs feature_records inputs_sha256 method_selection_sha256 '
    'methods pre_score_freeze_sha256 replicates runtime seed selection_sha256 source_sha256 '
    'train_moment_sources'
)
ASV_METHODS = tuple(method for method in METHODS if method != 'magphase')
UNSET = object()


def exact_fields(value, names, where):
    # 未使用の私有欄を公開側へコピーしない。既知のトップレベルschemaも固定する。
    if type(value) is not dict or set(value) != set(names.split()):
        fail(where, '未知schemaまたは必須欄不足')


def exact_ids(value, expected, where):
    values = sequence(identifier)(value, where)
    if len(values) != len(set(values)) or set(values) != set(expected):
        fail(where, '固定ID集合との不一致または重複')


def record_ids(rows, keys, count, where):
    if type(rows) is not list or len(rows) != count:
        fail(where, '固定観測件数の不一致')
    identities = []
    for row in rows:
        if type(row) is not dict or not set(keys) <= row.keys():
            fail(where, '観測IDの必須欄不足')
        identities.append(tuple(identifier(row[key], where) for key in keys))
    if len(set(identities)) != count:
        fail(where, '固定観測IDが重複')
    return set(identities)


def input_cases(data, count, where, vctk=False):
    keys = 'id metadata path sample_rate samples sha256 speaker'
    if vctk:
        keys += ' audio source_flac_sha256'
    record_ids(data, ('id',), count, where)
    for row in data:
        exact_fields(row, keys, where)
        identifier(row['speaker'], where)
        sha(row['sha256'], where)
    return {row['id']: row['speaker'] for row in data}


class Binding:
    def __init__(self, sources, where):
        self.sources = sources
        self.where = where
        self.evidence = []

    def snapshot_hash(self, path):
        # add()で後から登録されたsourceは、最終snapshotの根拠にならない。
        value = self.sources.original_paths.get(str(path))
        if value is None:
            fail(self.where, '最終snapshotの初期出典一覧に保存SHAがない')
        return sha(value, self.where)

    def verify_hash(self, path, actual, expected=UNSET, snapshot=False):
        if snapshot:
            frozen = self.snapshot_hash(path)
            if frozen != actual:
                fail(self.where, '最終snapshotの出典SHAと不一致')
        if expected is not UNSET and sha(expected, self.where) != actual:
            fail(self.where, 'anchorに保存された出典SHAと不一致')
        if str(path) in self.sources.original_paths:
            if self.snapshot_hash(path) != actual:
                fail(self.where, 'snapshot内の同一出典SHAと不一致')
        source_id = self.sources.add(str(path), actual, 'dedicated_binding')
        if source_id not in self.evidence:
            self.evidence.append(source_id)

    def read(self, path, expected=UNSET, snapshot=False):
        raw = path.read_bytes()
        self.verify_hash(path, digest(raw), expected, snapshot)
        return loads(raw)

    def anchor(self, entry, folder):
        if 'anchor_results' not in entry:
            fail(self.where, '最終snapshot内anchor_resultsの明示が必要')
        path = Path(entry['anchor_results'])
        if not path.is_absolute() or path.name != 'results.json' or path.parent.name != folder:
            fail(self.where, '専用anchorの絶対経路または保存先が不一致')
        return path, self.read(path, snapshot=True)


def same_path(actual, expected, where):
    if Path(actual) != Path(expected):
        fail(where, 'anchorで固定した保存source経路と不一致')


def bind_abx(entry, path, data, binding):
    anchor, results = binding.anchor(entry, 'abx-rankings')
    exact_fields(results, ABX_RESULT_KEYS, 'ABX results')
    exact_ids(results['method_set'], METHODS, 'ABX result methods')
    exact_ids(results['methods'], METHODS, 'ABX methods')
    sources = results['raw_sources']
    if type(sources) is not dict or set(sources) != set(METHODS):
        fail('ABX', '固定8方式のraw source対応が必要')
    source = sources[entry['method']]
    exact_fields(source, 'path sha256 status_counts available_tokens', 'ABX raw source')
    same_path(path, source['path'], 'ABX')
    same_path(path, anchor.parent / 'raw' / (entry['method'] + '.json'), 'ABX')
    binding.verify_hash(path, entry['sha256'], source['sha256'])
    contract = binding.read(anchor.parent / 'contract.json', results['contract_sha256'])
    exact_fields(contract, ABX_CONTRACT_KEYS, 'ABX contract')
    exact_ids(contract['methods'], METHODS, 'ABX contract methods')
    manifest_path = anchor.parents[2] / 'corpora' / 'abxls120-triphones.json'
    manifest = binding.read(manifest_path, contract['manifest_sha256'])
    exact_fields(manifest, ABX_MANIFEST_KEYS, 'ABX frozen triplets')
    frozen = record_ids(manifest['triplets'], ('a', 'b', 'x', 'condition'), 4960, 'ABX manifest')
    for item in manifest['triplets']:
        exact_fields(item, 'a b x condition', 'ABX manifest triplet')
    actual = record_ids(data['triplets'], ('a', 'b', 'x', 'condition'), 4960, 'ABX raw triplets')
    if actual != frozen:
        fail('ABX', '全4960三つ組(a,b,x,condition)が固定manifestと不一致')
    for item in data['token_exclusions']:
        if item['method'] != entry['method']:
            fail('ABX', 'token除外の方式が入力sourceと不一致')


def bind_readout(entry, path, data, binding):
    anchor, results = binding.anchor(entry, 'readout-rankings')
    exact_fields(results, READOUT_RESULT_KEYS, 'readout results')
    exact_ids(results['methods'], METHODS, 'readout methods')
    same_path(path, anchor.parent / 'raw-recordings.json', 'readout')
    binding.verify_hash(path, entry['sha256'], results['raw_recordings_sha256'])
    inputs = binding.read(anchor.parents[2] / 'inputs.json', snapshot=True)
    cases = input_cases(inputs, 120, 'readout frozen inputs')
    actual = record_ids(data, ('case', 'speaker'), 120, 'readout raw recordings')
    if actual != set(cases.items()):
        fail('readout', '120録音case/speakerが固定inputsと不一致')
    for item in data:
        exact_ids(list(item['predictions']), METHODS, 'readout prediction methods')


def bind_vctk(entry, path, data, binding):
    if 'anchor_results' in entry:
        fail('VCTK', 'VCTK anchorはsnapshot固定rankings-private自体。追加指定は不可')
    if path.name != 'rankings-private.json' or path.parent.name != 'vctk-availability16':
        fail('VCTK', '固定VCTK専用source保存先と不一致')
    binding.verify_hash(path, entry['sha256'], snapshot=True)
    exact_fields(data, VCTK_RESULT_KEYS, 'VCTK rankings')
    contract = binding.read(path.parent / 'quality-contract.json', data['quality_contract_sha256'])
    exact_fields(contract, VCTK_CONTRACT_KEYS, 'VCTK quality contract')
    exact_ids(contract['planned_methods'], METHODS, 'VCTK planned methods')
    if contract['planned_recordings'] != 16 or contract['planned_speakers'] != 4:
        fail('VCTK', '固定16録音4話者の契約が必要')
    inputs = binding.read(path.parent / 'inputs.json', contract['inputs_sha256'])
    cases = input_cases(inputs, 16, 'VCTK frozen inputs', vctk=True)
    if len(set(cases.values())) != 4:
        fail('VCTK', '固定話者集合の件数不一致')
    for key in ('all16', 'recommended_duration'):
        exact_fields(data[key], VCTK_GROUP_KEYS, 'VCTK ' + key)
        exact_ids(data[key]['methods'], METHODS, 'VCTK group methods')
    exact_ids(data['all16']['planned_case_ids'], cases, 'VCTK all16 planned IDs')
    layer = sequence(identifier)(data['recommended_duration']['planned_case_ids'], 'VCTK layer')
    if len(layer) != len(set(layer)) or not set(layer) <= cases.keys():
        fail('VCTK', '保存8秒層のIDが固定16録音外または重複')
    rows = data['all16']['rows']
    actual = record_ids(rows, ('case', 'method'), 128, 'VCTK rows')
    if actual != {(case, method) for case in cases for method in METHODS}:
        fail('VCTK', '固定16録音×8方式の128セルと不一致')
    for row in rows:
        if row['speaker'] != cases[row['case']] or row['contract_sha256'] != data['quality_contract_sha256']:
            fail('VCTK', '行の話者またはquality契約SHAと不一致')


def bind_asv(entry, path, data, binding):
    # ASV resultはraw-pairs SHAを持たない。保存handoff由来のsnapshot inventoryを必須にする。
    binding.verify_hash(path, entry['sha256'], snapshot=True)
    anchor, results = binding.anchor(entry, 'conditional-rankings')
    if anchor.parent.parent.name != 'human-availability100':
        fail('ASV', '固定availability100の保存先が必要')
    exact_fields(results, ASV_RESULT_KEYS, 'ASV conditional results')
    same_path(path, anchor.parent / 'raw-pairs.json', 'ASV')
    exact_ids(results['methods'], ASV_METHODS, 'ASV conditional methods')
    contract = binding.read(anchor.parent / 'contract.json', results['contract_sha256'])
    exact_fields(contract, ASV_CONTRACT_KEYS, 'ASV conditional contract')
    exact_ids(contract['methods'], ASV_METHODS, 'ASV contract methods')
    pairs = contract['common_pairs']
    if type(pairs) is not list or len(pairs) != 80:
        fail('ASV', '固定80共通対が必要')
    frozen = []
    for pair in pairs:
        if type(pair) is not list or len(pair) != 2:
            fail('ASV', '固定共通対は2音声IDが必要')
        frozen.append(tuple(identifier(value, 'ASV pair') for value in pair))
    if len(set(frozen)) != 80:
        fail('ASV', '固定共通対の重複')
    if record_ids(data, ('sample_a', 'sample_b'), 80, 'ASV raw pairs') != set(frozen):
        fail('ASV', '80派生距離対がcontractの共通対集合と不一致')
    for row in data:
        exact_ids(list(row['distances']), ASV_METHODS, 'ASV pair methods')


def bind_special(entry, path, data, sources):
    """公開するのは検証済みsource IDだけ。私有anchorや入力JSONは返さない。"""
    if not path.is_absolute():
        fail(entry['kind'], 'snapshot出典に対応する絶対経路が必要')
    binding = Binding(sources, entry['kind'])
    handlers = {'abx': bind_abx, 'readout': bind_readout, 'vctk16': bind_vctk, 'asv_distances': bind_asv}
    handlers[entry['kind']](entry, path, data, binding)
    return binding.evidence
