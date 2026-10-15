"""既知評価器の設定・asset内容hash・依存版だけを明示転記する。"""
from export_types import (H, IDS, N, PATH, PRIVATE_LIST, PRIVATE_OBJECT, S, STRINGS, boolean,
                          fields, integer, mapping, obj, sequence, sha, string)
from provenance_base import ASSET, ENVIRONMENT, RESAMPLER, hashes, public_url

ASSET_OPTIONS = obj({**fields('model embedding_model binary', PATH),
    **fields('model_sha256 embedding_model_sha256 binary_sha256', H),
    'domain': string, 'timeout_seconds': N})
ASSETS = obj({'schema_version': integer,
    'metrics': mapping(ASSET_OPTIONS, ('erb', 'scoreq', 'speaker_ecapa', 'visqol_audio'))})
MOS_PROVENANCE = obj({**fields('name quantity source_commit checkpoint_revision configuration predict_dataset '
    'device short_input_extension code_license weights_license independent_human_rating_calibration '
    'scope paper_protocol_difference initialization', string), 'source_repository': public_url,
    'checkpoint_sha256': sha, **fields('fold repetitions extraction_seed cpu_threads internal_sample_rate '
    'spectrogram_frames_per_repetition', integer), **fields('remove_silent_section nnpack_enabled spectrogram_inner_mixup', boolean),
    **fields('ssl_crop_seconds spectrogram_crop_seconds', N), 'packages': mapping(string)})
MOS = obj({'schema_version': integer, 'evaluator': string, 'source_sha256': sha,
    'provenance': MOS_PROVENANCE, 'checkpoint_sha256': sha, 'feature_configuration_sha256': hashes,
    'input': string, 'repetition_semantics': string})
ASR = obj({'schema_version': integer, **fields('recognizer recognizer_revision selection decoding normalization '
    'word_tokenization no_full_GT_reason', string), 'asset_sha256': hashes, 'source_sha256': hashes,
    'input_contract_sha256': sha, 'selected_case_ids': IDS,
    **fields('planned_cases planned_speakers planned_recognitions planned_assessments no_full_GT_cases sample_rate', integer),
    'maximum_reference_cer': N, 'packages': mapping(string),
    'full_native_preprocessing': obj({**fields('resampling scipy_version padtype float32', string),
        'window': sequence(lambda v, p: string(v, p) if type(v) is str else N(v, p)),
        **fields('trim align normalize clip', boolean)}),
    'execution': obj({**fields('torch_threads torch_interop_threads', integer), 'device': string,
        **fields('inference_mode trust_remote_code local_files_only use_safetensors', boolean)})})
SPEAKER = obj({'schema_version': integer, 'evaluator': string, 'embedding_model': PATH,
    'embedding_model_sha256': sha, 'input_contract_sha256': sha, 'source_sha256': hashes,
    'environment': ENVIRONMENT, **fields('seed threads repetitions', integer),
    **fields('reference output normalization alignment', string), 'resampling': RESAMPLER,
    'full_length_distinct_from_primary_common16_ecapa': boolean})
BACKEND = obj({**fields('algorithm domain recipe timing_scope process_cpu_scope wav_quantization', string),
    'source': public_url, **fields('sample_rate required_sample_rate padding_multiple bands', integer),
    **fields('window_ms hop_ms reference_power_floor_ratio', N),
    **fields('reference_cache normalize_embeddings_with_global_stats', boolean),
    'assets': mapping(ASSET, ('model', 'embedding_model', 'binary')), 'packages': mapping(string)})
METRIC_CONFIGURATION = obj({'evaluator': string, 'options': ASSET_OPTIONS, 'model_provenance': BACKEND,
    'source_sha256': hashes, 'environment': ENVIRONMENT, **fields('threads repetitions', integer),
    **fields('score_selection input_protocol', string)})
METRIC = obj({'evaluator': string, 'status': string, 'seconds': N,
    'provenance': BACKEND, 'configuration': METRIC_CONFIGURATION, 'configuration_sha256': H})
QUALITY_RESULT = obj({'schema_version': integer, 'created_at_utc': string,
    'environment': ENVIRONMENT, 'input': PRIVATE_OBJECT, 'input_file_sha256': PRIVATE_OBJECT,
    'metrics': mapping(METRIC, ('erb', 'scoreq', 'speaker_ecapa')),
    'network': string, 'reference_cache': boolean, 'repetitions': integer,
    'requested_metrics': IDS, 'rows': PRIVATE_LIST,
    'settings': ASSETS, 'source_sha256': hashes, 'threads': integer})
VISQOL = obj({'schema_version': integer, 'metric': string, 'planned_methods': IDS,
    **fields('planned_recordings planned_speakers sample_rate repetitions_after_first threads', integer),
    **fields('input_contract_sha256 inputs_sha256 assets_sha256', H), 'assets_path': PATH,
    'source_sha256': hashes, 'backend_provenance': BACKEND, 'environment': ENVIRONMENT,
    **fields('use_speech_mode use_lattice_model alignment gain_normalization time_warp', boolean),
    **fields('minimum_common_seconds minimum_coverage_each_waveform', N),
    **fields('native_amplitude_rule pcm16_rule comparison_samples score_selection derivative_storage '
             'ranking interval recommended_duration_stratum', string), 'resampling': RESAMPLER})
ACOUSTIC = obj({'schema_version': integer, 'source_sha256': hashes, 'environment': ENVIRONMENT,
    **fields('derivation_contract_sha256 input_contract_sha256', H), 'scope': string,
    'natural_f0_truth': S, 'estimated_pitch_consistency': boolean, 'auditory_local': string,
    'diagnostics_not_quality_ranks': STRINGS, 'raw_families_are_not_independent_votes': boolean})
DERIVATION = obj({'schema_version': integer, 'target_sample_rate': integer,
    **fields('source_sha256 input_contract_sha256', H), 'resampler': RESAMPLER,
    **fields('common_length missing_method alignment normalization silence_removal status_only_revisions', string),
    **fields('minimum_seconds minimum_coverage_every_waveform', N), 'native_retained': boolean})
