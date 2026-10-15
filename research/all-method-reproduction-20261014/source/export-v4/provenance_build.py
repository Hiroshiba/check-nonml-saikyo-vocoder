"""保存済みViSQOL build来歴と依存内容hash。実行物は読み込まない。"""
from pathlib import PurePosixPath

from export_types import (H, N, PATH, PRIVATE_LIST, STRINGS, boolean, fields, integer,
                          obj, sequence, sha, string)
from provenance_base import ASSET, INPUT, PUBLIC_ARCHIVE, public_url, relative_name

SOURCE_FILE = obj({'path': relative_name, 'bytes': integer, 'sha256': sha}, ('path', 'sha256'))
BUILD = obj({'schema_version': integer, 'run': PATH, 'source_repository': public_url,
    **fields('created_utc status tag commit mode bazel_version compatibility_adjustment '
             'runtime_verification finalized_utc', string),
    **fields('required_sample_rate source_file_count conformance_version_from_official_header', integer),
    **fields('use_speech_mode use_lattice_model new_build historical_binary_sha_match cli_executed '
             'inference_executed tests_executed smoke_executed model_substituted source_algorithm_changes '
             'build_environment_isolated all_preparation_processes_completed', boolean),
    'historical_binary_sha256': H, 'source_hash_mismatches': STRINGS, 'build_attempts': PRIVATE_LIST,
    **fields('binary model source_archive bazel source_license build_script dependency_inventory '
             'dependency_file_manifest resolved_repositories cache_cleanup', ASSET)})


def runtime_library(value, where):
    result = obj({'path': PATH, 'requested_path': PATH, 'bytes': integer, 'sha256': sha},
                 ('path', 'sha256'))(value, where)
    result['filename'] = relative_name(PurePosixPath(value['path']).name, where)
    return result


DEPENDENCIES = obj({'created_utc': string, 'dependencies': sequence(obj({
    'repository': string, **fields('file_count bytes', integer),
    **fields('license_files build_rule_files', sequence(SOURCE_FILE)),
    'ordered_file_manifest_sha256': sha})),
    'repository_cache_archives': sequence(obj({'sha256': sha, 'key_matches_content': boolean, 'bytes': integer})),
    'system_runtime_libraries': sequence(runtime_library), 'dependency_manifest': ASSET,
    'original_visqol_source_file_count': integer, 'source_hash_mismatches': STRINGS,
    'runtime_verification': string})
ASV_PCM = obj({'status': string, 'sample': string, 'speaker': string, 'input': INPUT,
    'source': PUBLIC_ARCHIVE, 'source_sha256': sha, 'local_source': PATH,
    **fields('sample_rate samples', integer), 'full_duration_seconds': N,
    'full_source_float64_sha256': sha, 'pcm_identity_scope': string, 'excerpt': boolean,
    'finished_at_utc': string}, ('sample', 'speaker', 'input', 'sample_rate', 'samples', 'full_source_float64_sha256'))
