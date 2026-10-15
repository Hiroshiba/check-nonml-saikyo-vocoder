"""18×8 coverage・元final_gate・長さと計時を保存値から明示転記する。"""
from export_science_schema import COHORT, STATE, build_group
from pathlib import Path

from export_types import (COUNTS, H, COUNT, IDS, METHODS, METHOD_NUMBERS, N, PATH,
                          PRIVATE_OBJECT, S, STRINGS, boolean, fail, fields,
                          identifier, integer, mapping, nullable, obj, reason,
                          sequence, string)


def build_report(bind):
    group, row = build_group(bind)
    denominator = obj({'common_valid_recordings': integer, 'common_valid_speakers': integer, 'cohort': COHORT})
    supplement = obj({**fields('group_id label anchor status status_label', string),
        'counts': STATE, 'primary': denominator, 'conditional': nullable(denominator),
        'conditional_included': boolean, 'does_not_replace_original': boolean})
    coverage_cell = obj({**fields('status label counting_note', string),
        'derived_axis_status_counts': COUNTS,
        'derived_axes': sequence(obj({'group_id': identifier, 'status': identifier,
            'comparable': boolean, 'counts': STATE, 'primary_common_recordings': COUNT,
            'primary_cohort': COHORT})), 'availability_supplements': sequence(supplement)})
    coverage = obj({**fields('family_count method_count cells', integer), 'meaning': string,
        'rows': sequence(obj({'family': integer, 'label': string, 'derived_axes': integer,
            'methods': mapping(coverage_cell, METHODS)}))}, ('family_count', 'method_count', 'cells', 'rows'))
    gate_row = bind(obj({**fields('case speaker method condition control stage group identity_key status', S),
        'path': PATH, 'terminal': boolean, 'unresolved_reason': reason, 'raw_result_sha256': H},
        ('stage', 'status', 'terminal')))
    gate = obj({'terminal': boolean, 'planned_records': integer, 'unresolved_records': integer,
        'stage_counts': COUNTS, 'status_counts': COUNTS, 'rows': sequence(gate_row), 'meaning': string},
        ('terminal', 'planned_records', 'unresolved_records', 'rows', 'stage_counts', 'status_counts'))
    excluded_seconds = obj(fields('input_preprocessing_seconds representation_save_seconds '
                                 'representation_load_seconds output_storage_seconds', N))
    lengths = obj({**fields('case speaker method status', identifier),
        **fields('source_seconds native_seconds native_sample_rate native_samples', N),
        'initialization_included': boolean, 'excluded_seconds': excluded_seconds})
    derivation = bind(obj({**fields('case speaker status', identifier), 'common_seconds': N,
        'coverage': nullable(METHOD_NUMBERS), 'omitted_tail_samples_16k': nullable(METHOD_NUMBERS),
        'full_length_seconds': METHOD_NUMBERS, 'source_result': PATH}))
    timing = obj({**fields('full120_group_ids supplement_group_ids', IDS),
        'supplement_batches': sequence(integer), 'planned_recordings': integer, 'planned_speakers': integer,
        'speaker_recording_counts': COUNTS,
        **fields('selection_basis operational_boundary_announced_utc_minute policy_record_created_at_utc '
                 'batch005_started_at_utc supplement_analysis_adopted_at_utc plan_wording_corrected_at_utc '
                 'review_scope review_counts_unit interval_scope full120_note supplement_note review_note', string),
        **fields('preregistered_before_all70_syntheses selection_used_metric_values_or_ranks raw_values_changed '
                 'additional_inference background_load_equivalence_established later_batch_isolation_certified_by_review', boolean),
        'storage_interference_duration_seconds': N, 'storage_interference_effect_on_timing': S,
        'review_counts': COUNTS, 'review_limitations': STRINGS, 'source_sha256': PRIVATE_OBJECT})
    initialization_record = bind(obj({'started_at_utc': string, 'seconds': N, 'inputs': PATH,
        'input_manifest_sha256': H, 'contract_sha256': H, 'requested_conditions': IDS,
        'edits_only': boolean}, ('seconds', 'requested_conditions', 'edits_only')))
    initialization_schema = bind(obj({'path': PATH, 'record': initialization_record}, ('path', 'record')))
    def initialization(value, where):
        result = initialization_schema(value, where)
        methods = [m for m in METHODS if Path(value['path']).name.startswith(m + '-')]
        if len(methods) != 1:
            fail(where, '既知初期化filenameの方式識別が不一致')
        result['method'] = methods[0]
        return result
    report = obj({
        'schema_version': integer, 'generated_at_utc': string, 'implementation_origin': string,
        'formal_base': obj(fields('status method version reason comparison_reference comparison_reference_meaning '
                                 'previous_version selection_report', S)),
        'methods': IDS, 'terminal': boolean, 'coverage': coverage, 'groups': sequence(group),
        'limitations': STRINGS, 'native_length_and_timing': sequence(lengths),
        'common16_derivation': sequence(derivation), 'timing_interpretation': timing,
        'native_initializations_excluded_from_speed': sequence(initialization),
        'source_sha256': PRIVATE_OBJECT, 'raw_source_inventory': PRIVATE_OBJECT,
        'final_gate': gate, 'input_manifest_sha256': H,
        'overall_winner': nullable(identifier), 'average_rank': N, 'publication_state': string,
        'availability_studies_replace_formal_groups': boolean,
        'quantization_common_supplement': obj({**fields('status note href results_href', string),
            **fields('results_sha256 html_sha256', H), 'family_ids': sequence(integer),
            'replaces_primary': boolean, 'counts_as_additional_independent_metric': boolean}),
    }, ('schema_version', 'methods', 'terminal', 'coverage', 'groups', 'final_gate',
        'raw_source_inventory', 'source_sha256', 'input_manifest_sha256', 'limitations'))
    return report, row
