"""保存済み推定値・実分母・状態の明示schema。統計関数をimportしない。"""
from export_types import (COUNTS, H, COUNT, IDS, METHODS, METHOD_NUMBERS, N, PATH,
                          PRIVATE_OBJECT, S, STRINGS, boolean, enum,
                          fields, identifier, integer, interval, known_reason, mapping, nullable,
                          obj, reason, sequence, sha, string, with_reasons)

TARGETS = ('log_f0', 'rms_dbfs', 'spectral_slope')
CONDITIONS = ('within_speaker', 'across_speaker')
METHOD_COUNTS = mapping(COUNTS, METHODS)
SUPPORT = obj(fields('recordings speakers pairs triplets tokens b_anchors b_speakers anchors strata x_speakers', integer))
EXCLUSION = with_reasons(obj({**fields('case speaker method status split', identifier), 'reason': reason,
    'error': PATH, 'source_records': PRIVATE_OBJECT, 'path': PATH}), {})
CALIBRATION = nullable(obj({
    'methods': IDS, 'selection_uses_metric_values': boolean,
    'required_train_recordings': integer, 'required_train_speakers': integer,
    'rule': string, 'reselection': string,
    'excluded_methods': mapping(sequence(EXCLUSION), METHODS),
    'excluded_method_status_counts': METHOD_COUNTS,
}))
COHORT = nullable(obj({
    'id': identifier, 'scope': string, 'planned': SUPPORT, 'common': SUPPORT,
    'planned_complete': boolean, 'extraction_states': METHOD_COUNTS,
    **fields('planned_recordings planned_speakers common_recordings common_speakers', integer),
    'ids': IDS, 'speaker_counts': COUNTS, 'exclusions': sequence(EXCLUSION),
    'exclusion_counts': obj({'target_unavailable': integer,
        'prediction_unavailable_by_method': mapping(integer, METHODS), 'counts_can_overlap': boolean}),
}))
BOOTSTRAP_SUPPORT = obj({'speakers': IDS, 'point_support': SUPPORT,
    'support_columns': IDS, 'metric_columns': IDS})
BOOTSTRAP = nullable(obj({
    **fields('seed replicates requested_replicates', integer),
    **fields('unit', string), **fields('speakers axes array_axes support_columns conditions estimands method_axis', IDS),
    'sha256': H, 'path': PATH, 'support': BOOTSTRAP_SUPPORT, 'reason': known_reason,
    'by_condition': mapping(obj({'speakers': IDS, 'point_support': sequence(integer),
        'drawn_replicates': integer}), CONDITIONS),
}))
STATE = obj({
    'status_counts': COUNTS, 'status_category_counts': COUNTS, 'terminal': boolean,
    **fields('direct_measured analytic_identity finite_values planned_records', integer),
    'observation_unit': string, 'source_status_counts': COUNTS,
    'calibration_failure_counts': nullable(COUNTS), 'calibration_required_recordings': COUNT,
}, ('status_counts', 'terminal', 'finite_values'))
DELTA = obj({'value': N, 'ci95': interval,
    **fields('valid_replicates undefined_replicates', integer), 'definition': string}, ('value', 'ci95'))
CELL_FIELDS = {
    'value': N, 'rank': COUNT, 'ci95': interval, 'status': identifier, 'reason': reason,
    **fields('valid_recordings valid_speakers valid_replicates undefined_replicates', integer),
    'hnm_difference': DELTA, 'speaker_means': mapping(N),
    **fields('recording_equal_mean_auxiliary recording_equal_mae recording_equal_rmse random_candidate_expectation', N),
}
DENOM_FIELDS = {
    **fields('truth_tokens reference_errors output_errors decoded_alpha_points total_band_frame_cells '
             'reference_active_cells native_full_length_attributes total_frames valid_voiced_frames '
             'expected_voiced_frames reference_silent_frames serialized_bytes', COUNT),
    **fields('original_input_seconds original_seconds seconds', N),
    'actual_file_sha256': H, 'retained': boolean,
}


def denominator(value, where):
    return nullable(obj(DENOM_FIELDS))(value, where) if type(value) is dict else N(value, where)


ROW_FIELDS = {
    **fields('case speaker method status origin_status condition control origin', S),
    'value': N, 'raw_result_sha256': H, 'raw_result': PATH, 'reason': reason,
    'error': PATH, 'source_records': PRIVATE_OBJECT,
    'denominator': denominator,
    **fields('numerator total_frames expected_voiced_frames unmapped_frames reference_rate output_rate '
             'new_inference_seconds control_scale attribute_scale expected_response control_amount '
             'method_specific_all_detected_mae common_seconds common_samples native_sample_rate '
             'native_peak analysis48_peak source_original_seconds', N),
    'coverage': nullable(METHOD_NUMBERS), 'coverages': nullable(METHOD_NUMBERS),
    'event_status_counts': COUNTS, 'common_event_ids': IDS,
    'timing_phase_attempts': sequence(integer), 'full_native_length': boolean,
    **fields('scope interpretation reference metric unit direction started_at_utc finished_at_utc', S),
    **fields('input_pcm64_sha256 reference_pcm64_sha256 native_audio_sha256 '
             'source_manifest_sha256 contract_sha256', H),
    'derivation_path': PATH, 'measurement': PRIVATE_OBJECT,
    'pcm16_rounding': obj({**fields('minimum maximum', N), **fields('below_minimum_count above_maximum_count', integer)}),
    'payload_alone_is_self_contained_bitrate': boolean,
}


def build_group(bind):
    cell = bind(obj(CELL_FIELDS, ('value', 'rank', 'ci95', 'status', 'hnm_difference')))
    comparison = nullable(obj({
        'methods': mapping(cell, METHODS), 'cohort': COHORT,
        **fields('common_valid_recordings common_valid_speakers valid_bootstrap_replicates requested_bootstrap_replicates', integer),
        **fields('case_ids speaker_ids comparable_methods', IDS),
        'excluded_methods': nullable(lambda v, p: IDS(v, p) if type(v) is list
                                     else mapping(sequence(EXCLUSION), METHODS)(v, p)),
        **fields('label interval_limitation selection', string),
        **fields('all_eight_methods same_as_primary ranking', boolean),
        'calibration_cohort': CALIBRATION, 'exclusion_counts_by_method': nullable(mapping(integer, METHODS)),
        'excluded_triplets': nullable(sequence(obj({'triplet': obj(fields('a b x condition', identifier)),
            'failed_methods': IDS}))), 'selection_sha256': H,
    }, ('methods', 'comparable_methods')))
    row = bind(obj(ROW_FIELDS, ('case', 'speaker', 'method', 'status', 'value')))
    constants = bind(obj({k: ROW_FIELDS[k] for k in ('method', 'status', 'origin_status', 'value',
        'raw_result', 'raw_result_sha256', 'scope', 'payload_alone_is_self_contained_bitrate', 'error')},
        ('method', 'status', 'value')))
    evidence = bind(obj({'source_result': PATH, 'source_sha256': H, 'records': sequence(obj({
        'case': identifier, 'record_sha256': sha,
        'missing_reasons': mapping(known_reason, TARGETS)}, ('case', 'record_sha256', 'missing_reasons')))}))
    group = bind(obj({
        **fields('id label unit scope note condition kind observation_unit aggregation '
                 'comparison_role conditional_scope conditional_withheld_reason source_status', S),
        'family': integer, 'direction': enum('lower', 'higher', None),
        **fields('methods planned_methods planned_case_ids admissible_status', IDS),
        **fields('rankable speaker_bootstrap_eligible terminal supplementary', boolean),
        **fields('planned_recordings_per_method planned_speakers_per_method planned_method_constants '
                 'planned_rows direct_measured_rows analytic_identity_rows expected_eligible_recordings '
                 'expected_eligible_speakers', COUNT),
        'rows': sequence(row), 'reference_only_rows': sequence(row),
        'method_constants': sequence(constants), 'method_states': mapping(STATE, METHODS),
        'primary': comparison, 'conditional': comparison, 'specialized_auxiliary': comparison,
        'available_case_auxiliary': mapping(cell, METHODS), 'bootstrap': nullable(bind(BOOTSTRAP)),
        'status_counts': COUNTS,
        'extraction_path': sequence(lambda v, p: integer(v, p) if type(v) is int else identifier(v, p)),
        'transform': S, 'configuration_sha256': sequence(sha),
        **fields('group_source source_result selection_plan', PATH),
        **fields('group_source_sha256 source_sha256 selection_plan_sha256', H),
        'uncertainty': nullable(lambda v, p: STRINGS(v, p) if type(v) is list else string(v, p)),
        'limits': nullable(STRINGS),
        'definitions': nullable(obj(fields('flat_stratum x_speaker_macro nested_phone_context', string))),
        'train_target_support': nullable(mapping(obj({'valid_recordings': integer, 'valid_speakers': integer,
            'valid_ids': IDS}), TARGETS)),
        'train_target_evidence': nullable(evidence),
        'extraction_exclusions': nullable(sequence(EXCLUSION)),
        'train_failures_by_method': nullable(METHOD_COUNTS), 'calibration_cohort': CALIBRATION,
        'group_terminal_evidence': obj({
            **fields('all_planned_rows_terminal status_only_selection_verified global_final_gate_replaced', boolean),
            **fields('planned_rows planned_recordings_per_method common_recordings', integer),
            'comparable_methods': IDS,
            **fields('source_result_sha256 conditional_source_sha256 selection_sha256 summary_sha256', H)}),
    }, ('id', 'family', 'direction', 'unit', 'methods', 'method_states', 'primary', 'conditional', 'terminal')))
    return group, row
