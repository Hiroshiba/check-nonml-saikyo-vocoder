"""来歴の公開scalar schema。公開relative名と私有locatorを区別する。"""
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit

from export_types import (H, IDS, METHODS, N, PATH, PRIVATE_LIST, PRIVATE_OBJECT,
                          S, STRINGS, boolean, fail, fields, identifier, integer, mapping,
                          nullable, obj, sequence, sha, string)


def relative_name(value, where):
    string(value, where)
    if not value or PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts or '\\' in value or ':' in value:
        fail(where, '公開相対名だけ許容')
    return value


def public_url(value, where):
    string(value, where)
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment):
        fail(where, '認証情報/queryのない公開HTTPS出典だけ許容')
    return value


def hashes(value, where):
    if type(value) is not dict:
        fail(where, '相対source名→SHAが必要')
    return {relative_name(k, where): sha(v, where) for k, v in value.items()}


def dependencies(value, where):
    string(value, where)
    result = {}
    for line in value.splitlines():
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', line)
        if not match or match[1] in result:
            fail(where, '既存version pin以外の依存記法。私有URL等は転記しない')
        result[match[1]] = match[2]
    return result


ENVIRONMENT = obj({**fields('python platform cpu', string), 'logical_cpu_count': integer,
    'packages': mapping(string), 'dependencies': dependencies})
SOURCE = obj({'repository': public_url, 'revision': string}, ('repository', 'revision'))
SOURCES = mapping(SOURCE)
RESAMPLER = obj({**fields('function scipy_version padtype up_down', string), 'source_sha256': H,
    'window': sequence(lambda v, p: string(v, p) if type(v) is str else N(v, p)),
    'up': integer, 'down': integer})
ASSET = obj({'path': PATH, 'bytes': integer, 'sha256': sha, 'expected_sha256': H}, ('sha256',))
AUDIO_HASHES = obj({'path': PATH, **fields('file_sha256 float64_sha256 float32_sha256 storage_source_float64_sha256', H),
    **fields('samples sample_rate', integer), **fields('seconds peak over_one_fraction', N),
    **fields('stored_dtype storage_rule', string), 'exact_float32_storage_requested': boolean,
    'float32_roundtrip_exact': nullable(boolean)})
PUBLIC_ARCHIVE = obj({'archive_url': public_url, 'member': relative_name,
    **fields('archive_bytes header_offset compressed_bytes uncompressed_bytes compression crc32', integer)})
METADATA = obj({**fields('id corpus speaker language style source_utterance_id official_rating_sample_id role '
    'split microphone golf_training_partition speaker_gender_as_distributed', S),
    'source': PUBLIC_ARCHIVE, 'source_member': relative_name,
    **fields('sample_rate source_samples excerpt_start_sample excerpt_samples', integer),
    **fields('source_duration_seconds excerpt_duration_seconds source_peak source_rms_dbfs full_scale_fraction '
             'source_full_scale_fraction excerpt_full_scale_fraction excerpt_rms_dbfs', N),
    **fields('decoded_pcm_sha256 source_sha256 wav_sha256 source_pcm_sha256 excerpt_pcm_sha256 input_npy_sha256 '
             'source_archive_sha256 source_float64_sha256 excerpt_float64_sha256', H),
    **fields('local_source local_wav transcript', PATH), 'reasons': STRINGS, 'exclusion_reasons': STRINGS})
INPUT = obj({'id': string, 'speaker': string, 'path': PATH, 'sha256': sha,
    'sample_rate': integer, 'samples': integer, 'metadata': METADATA, 'audio': AUDIO_HASHES,
    'source_flac_sha256': H}, ('id', 'speaker', 'path', 'sha256', 'sample_rate', 'samples'))
BASE = obj(fields('status method version reason comparison_reference comparison_reference_meaning '
                  'previous_version selection_report', S))
INPUT_CONTRACT = obj({'schema_version': integer, 'source_commit': string,
    **fields('dataset_sha256 input_preparation_source_sha256 plan_sha256', H), 'methods': IDS,
    'native_sample_rates': mapping(integer, METHODS), 'seed': integer, 'formal_base': BASE,
    **fields('scope recovery_boundary reuse original_storage', string)})
TRAIN_INPUT_CONTRACT = obj({'schema_version': integer,
    **fields('role implementation_origin scope', string),
    **fields('inputs_sha256 manifest_sha256 evaluation_inputs_sha256 plan_sha256', sha),
    'selection_rule': obj({
        **fields('split salt speaker_selection candidate_selection_order final_manifest_and_inputs_order '
                 'audio_validation on_invalid_selected_audio excerpt', string),
        'source_url': public_url,
        **fields('recordings_per_speaker recordings speakers', integer),
        **fields('selection_uses_audio_or_scores normalization silence_trimming', boolean),
        'disjoint_from_evaluation': IDS}),
    'selection_inputs_sha256': obj(fields('archive_sha256 archive_file_index_sha256 '
        'speaker_labels_sha256 plan_sha256', sha))},
    ('schema_version', 'role', 'inputs_sha256', 'manifest_sha256', 'evaluation_inputs_sha256',
     'plan_sha256', 'selection_rule', 'selection_inputs_sha256'))
VCTK_INPUT_CONTRACT = obj({'schema_version': integer,
    **fields('study selection_rule formal126_status below100_limitation source_preprocessing '
             'training_overlap publication preparation', string),
    'source_manifest_path': PATH, 'source_manifest_sha256': sha,
    **fields('planned_recordings planned_speakers source_sample_rate seed threads', integer),
    'recordings_per_speaker': mapping(integer), 'methods': IDS,
    'native_sample_rates': mapping(integer, METHODS), 'gain_normalization': boolean,
    'comparison': obj({'sample_rate': integer,
        **fields('all8_required alignment time_warp gain_normalization native_full_length_retained', boolean),
        **fields('minimum_seconds minimum_coverage_every_waveform', N), 'on_missing_method': string}),
    'duration_layers': obj({**fields('planned_at_least8_seconds planned_below8_seconds', integer),
        'actual_common8sec_support': string}),
    'formal_base': BASE, 'source_sha256': hashes},
    ('schema_version', 'source_manifest_sha256', 'planned_recordings', 'planned_speakers',
     'methods', 'native_sample_rates', 'source_sample_rate', 'comparison', 'source_sha256'))
ASV_INPUT_CONTRACT = obj({'role': string,
    **fields('recordings pairs speakers b_anchors', integer), 'full_length': boolean,
    **fields('selection_sha256 inputs_sha256 plan_sha256', sha),
    'availability_selection': obj({
        **fields('adopted_at_utc timing_precision selection rule original105_gate', string),
        **fields('uses_rating_values uses_feature_or_metric_values replaces_original105 '
                 'missing_recording_treated_as_success', boolean),
        'availability_review_sha256': sha}), 'original_audio_storage': string},
    ('role', 'recordings', 'pairs', 'speakers', 'b_anchors', 'full_length', 'selection_sha256',
     'inputs_sha256', 'plan_sha256', 'availability_selection', 'original_audio_storage'))
REPRESENTATION = obj({'version': integer, 'method': string, 'serialization': string,
    **fields('decoder_input external_decoder_assets_required payload_alone_is_self_contained_bitrate '
             'integer_fields_are_not_rounded', boolean),
    'shared_decoder_assets': hashes, 'sources': SOURCES, 'prepared_record_sha256': H,
    **fields('quantization_fields floating_storage_rounding interpolation_metadata_rule', string),
    **fields('missing_native_controls quantization_exclusions', STRINGS),
    'interpolation_rule': obj(fields('scope primary_pitch derived_fields phase fixed_fields magphase '
                                    'positive_amplitude_power facodec alignment', string))})
SIFIGAN_CONFIG = obj({**fields('hydra', PRIVATE_OBJECT), **fields('in_dir out_dir stats checkpoint_path', PATH),
    **fields('seed sample_rate mcep_dim mcap_dim', integer),
    **fields('frame_period f0_floor f0_ceil sine_amp noise_amp', N),
    **fields('df_f0_type sine_f0_type', string), **fields('f0_factors dense_factors', sequence(N)),
    **fields('aux_feats signal_types', STRINGS),
    'generator': obj({**fields('_target_ nonlinear_activation', string),
        **fields('in_channels out_channels channels kernel_size', integer),
        **fields('upsample_scales upsample_kernel_sizes', sequence(integer)),
        **fields('share_upsamples share_downsamples bias use_weight_norm', boolean),
        'nonlinear_activation_params': obj({'negative_slope': N}),
        'source_network_params': obj({'resblock_kernel_size': integer,
            'resblock_dilations': sequence(sequence(integer)), 'use_additional_convs': boolean}),
        'filter_network_params': obj({'resblock_kernel_sizes': sequence(integer),
            'resblock_dilations': sequence(sequence(integer)), 'use_additional_convs': boolean})})})
PREPARED = obj({'schema_version': integer, 'method': string, 'prepared_at': string,
    'environment': ENVIRONMENT, **fields('lock_sha256 requirements_sha256 world_lock_sha256', H),
    'files': hashes, 'sources': SOURCES, 'note': string, 'formal_base': BASE})
SYNTHESIS = obj({'schema_version': integer, 'method': string, 'prepared': PREPARED,
    'source_sha256': hashes, 'input_contract_sha256': sha,
    **fields('threads seed native_sample_rate', integer), 'runtime': ENVIRONMENT,
    **fields('encode_only waveform_only', boolean), 'available_conditions': IDS,
    **fields('waveform_postprocessing analysis_reuse waveform_storage native_payload_storage randomness', string),
    'adapter_info': obj({'variant': string, 'parameter_count': integer, 'noise_seed': integer,
        'source_hashes': hashes, 'representation_contract': REPRESENTATION,
        'checkpoint': PATH, 'checkpoint_sha256': lambda v, p: sequence(sha)(v, p) if type(v) is list else sha(v, p),
        'stats_sha256': H, 'compile': string, 'analysis_file_io_included': boolean, 'config': SIFIGAN_CONFIG,
        'checkpoint_key_audit': sequence(obj({'missing_keys': STRINGS, 'unexpected_keys': STRINGS}))}),
    'capabilities': mapping(obj({**fields('control unit description limitation', string),
        **fields('amount target_cents target_gain_db', N), **fields('changes_duration time_map_required', boolean)})),
    'timing_definition': obj({**fields('analysis synthesis codec_rtf_denominator native_comparison', string),
        'separate': STRINGS})}, ('method', 'prepared', 'source_sha256', 'input_contract_sha256', 'adapter_info'))
WEIGHT = obj({'path': relative_name, 'sha256': sha, 'hf_repo': string, 'revision': string,
    'filename': relative_name, 'url': public_url, 'gdrive_id': identifier}, ('path', 'sha256'))
REFERENCE_LOCK = obj({'schema_version': integer, 'provenance': string, 'sources': SOURCES,
    'weights': mapping(sequence(WEIGHT), ('facodec', 'hifiglot', 'golf', 'sifigan', 'dac'))})
WORLD_LOCK = obj({'schema_version': integer, 'repository': public_url, 'revision': string,
    **fields('license rng_policy compiler', string), 'flags': STRINGS, 'sources': hashes})
ACQUISITION_ASSETS = obj({'source_file': relative_name, 'source_sha256': sha, 'scope': string,
    'assets': sequence(obj({'id': string, 'url': public_url, 'path': PATH,
        **fields('expected_sha256 sha256', H), 'started_at_utc': string, 'inference_performed': boolean,
        'status': string, 'bytes': integer, 'attempts': PRIVATE_LIST}, ('id', 'url', 'sha256', 'status')))})
