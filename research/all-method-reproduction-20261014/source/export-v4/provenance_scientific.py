"""制御・表現・専用推定の固定設定。raw配列は取り込まない。"""
from export_types import (H, IDS, N, PATH, PRIVATE_LIST, PRIVATE_OBJECT,
                          boolean, fields, integer, mapping, obj, sequence, string)
from provenance_base import ENVIRONMENT, hashes

NUMBERS = sequence(N)
ATTRIBUTES = obj(fields('pitch_cents level_db slope_db_per_octave duration_seconds', N))
COMMON = {'schema_version': integer, 'source_sha256': hashes, 'sources_sha256': hashes,
    **fields('input_contract_sha256 inputs_sha256 calibration_cohort_sha256', H),
    'implementation_origin': string, 'methods': IDS, 'environment': ENVIRONMENT,
    **fields('planned_cases planned_speakers seed threads repetitions', integer)}
CONTROLS = obj({**COMMON, 'conditions': IDS, 'missing_policy': string,
    'pitch': obj({'semitones': NUMBERS, **fields('reference estimator magphase_mapping', string)}),
    'gain': obj({'db': NUMBERS, 'reference': string, 'waveform_gain_postprocessing': boolean}),
    'time': obj({'methods': IDS, 'requested_scale': N, 'endpoint_renormalization': boolean,
        **fields('expected_time main_comparison', string), 'event_rule': obj({
            **fields('power_window_seconds minimum_peak_spacing_seconds candidate_height_fraction_of_original_peak_power '
                     'absolute_power_floor search_half_width_seconds minimum_observed_to_reference_peak_ratio', N),
            'selection': string})}),
    'preservation': obj({'methods': IDS, **fields('reference audio_scope slope time', string)}),
    'interference': obj({**fields('gain_delta_db gain_control_scale', N),
        'attribute_scales': ATTRIBUTES, 'expected_response': ATTRIBUTES,
        'pitch_off_diagonal_expected_response': string})})
SLOPE = obj({**COMMON, 'control_amounts_db_per_octave': NUMBERS,
    **fields('pivot_hz low_hz high_hz', N), **fields('amplitude_rule frequency_grid unchanged measurement reference scope failure_policy', string),
    **fields('external_waveform_dsp original_representation_modified', boolean), 'world_library_sha256': H,
    'hnm_fields': obj(fields('harmonic_envelope noise_psd', string)),
    'world_fields': obj({'spectral_envelope': string})})
EDIT = obj({**COMMON, 'curves': mapping(sequence(sequence(lambda v, p: string(v, p) if type(v) is str else N(v, p)))),
    'quality': IDS, **fields('source_reference control_reference content_metric pending_policy', string),
    **fields('no_composite_curve_quality_scalar edited_audio_reference_distance_penalty', boolean)})
LATENT = obj({**COMMON, 'protocol': string,
    **fields('not_the_existing_curves_CLI overall_score_or_aggregate_rank', boolean),
    'representation_points': IDS, 'interpolation_alpha': NUMBERS,
    'auditory': obj({'rate': integer, **fields('reference resampling different_lengths definition', string)}),
    'attributes': obj({'scope': string, 'slope_band_hz': NUMBERS, 'tolerances': ATTRIBUTES,
        **fields('perceptual_JND absolute_F0_truth', boolean)}),
    'interpolation': obj(fields('meaning diagnostics', string)),
    **fields('controls magphase_time_map analytic_identity bytes pending_quality', string),
    'quality': obj(fields('mos ecapa scope', string))})
TARGET = obj({'source_sha256': hashes, 'input_contract_sha256': H,
    'yin': obj(fields('frame_ms hop_ms fmin fmax threshold rms_threshold prefilter_hz', N)),
    'slope_band_hz': NUMBERS, 'units': obj(fields('log_f0 rms_dbfs spectral_slope', string))})
RUNTIME = obj(fields('python numpy scipy', string))
FEATURE_HASH = obj(fields('record_sha256 moments_sha256 transient_frame_npy_sha256', H))
TRAIN_HASH = obj({'case': string, **fields('record_sha256 moments_sha256 transient_frame_npy_sha256', H)})
ABX = obj({**COMMON, **fields('manifest_sha256 source_audit_sha256', H),
    'train_records': mapping(sequence(TRAIN_HASH)), 'eval_records': mapping(mapping(FEATURE_HASH)),
    'train_exclusions': PRIVATE_LIST, **fields('distance scale token_window', string),
    **fields('max_dtw_cells bootstrap_seed bootstrap_replicates', integer),
    **fields('tie_atol tie_error', N), 'downsampling': boolean, 'estimands': IDS, 'runtime': RUNTIME})
TARGET_HASH = obj({'case': string, 'record_sha256': H, 'missing_reasons': mapping(string)})
READOUT = obj({**COMMON, 'alpha': N, 'runtime': RUNTIME,
    'train_records': mapping(sequence(TRAIN_HASH)), 'eval_records': mapping(mapping(FEATURE_HASH)),
    'train_exclusions': PRIVATE_LIST, **fields('train_targets eval_targets', sequence(TARGET_HASH)),
    **fields('scaling aggregation', string), 'bootstrap_replicates': integer})
HUMAN_FEATURE = obj(fields('mean_sha256 record_sha256 frame_npy_sha256 frame_canonical_sha256 contract_sha256', H))
HUMAN = obj({**COMMON, **fields('method_selection_sha256 pre_score_freeze_sha256 selection_sha256', H),
    'common_pairs': sequence(IDS), 'feature_records': mapping(mapping(HUMAN_FEATURE)),
    'train_moment_sources': mapping(sequence(TRAIN_HASH)), 'runtime': RUNTIME, 'replicates': integer})
INPUT_NATIVE = obj({'source_sha256': H, **fields('source_samples source_sample_rate native_samples native_sample_rate', integer),
    'native_input_float64_sha256': H, 'input_quantization': string, 'resampling': obj({
        'up': integer, 'down': integer, 'function': string, 'padtype': string,
        'window': sequence(lambda v, p: string(v, p) if type(v) is str else N(v, p))})})
NATIVE_INPUT_RECORD = obj({**fields('case method condition status origin started_at_utc finished_at_utc', string),
    'contract_sha256': H, 'input': INPUT_NATIVE, 'seed': integer,
    'audio': PRIVATE_OBJECT, 'controls': PRIVATE_OBJECT, 'representation': PRIVATE_OBJECT,
    **fields('analysis_process_cpu_seconds analysis_seconds input_preprocessing_seconds length_delta_native_samples '
             'output_storage_seconds representation_load_seconds representation_save_seconds '
             'synthesis_process_cpu_seconds synthesis_seconds', N),
    'error': PATH, 'traceback': PATH})
