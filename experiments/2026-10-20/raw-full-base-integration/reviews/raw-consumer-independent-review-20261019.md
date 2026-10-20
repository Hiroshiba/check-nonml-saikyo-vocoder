# RAW consumer integration: independent static review

Date: 2026-10-19. Result: two display-migration blockers; no additional execution/API/freeze blocker found within the inspected scope.

## Review target and limits

Reviewed the expanded Git-external proposal at `raw-base-integration-proposal-20261019`, including base/proposed files, CONSUMERS.md and REVIEW-ja.md. Initial proposal.patch SHA256: `3539311bff95dde61d7d79f2ebed36c0fde6d9f59474a909c05cc1e6b26f5c84`.

Fixed source baseline: `d2fb3101898e91cec9377ceb28f08dd88e80af81`. Also read the locally retained USER_INSTRUCTIONS.md from the 20:55 document reread and read-only GitHub snapshots of audio_report.py, benchmark.py and references/report.py at that fixed commit. No repository writes, Git operations, package imports, tests, audio computations, renders, or lint runs were performed. This report is the only file written by this review. Core RAW numerical math was intentionally not re-reviewed. Exact repository Ruff verification belongs to the separate check.

The proposal is a partial tree. This review does not certify a complete repository-wide consumer search or that adoption HTML, top-level documents or registry are complete.

## Blocking findings

### R1 — schema-2 RAW report still announces HNM

Location: `proposed/vocoderbench/report.py:136,145,153`.

`run.py` generates schema_version=2 RAW results and calls `report.render`, which routes to `_render_current`. The method table now correctly consults saved_method_labels, but the same HTML still has the fixed title and H1 `自作HNMとWORLD（Harvest）の比較`, and its explanation states `自作HNMは独自の解析・合成系です`.

Consequently new RAW output is headed as an HNM comparison. This is a pre-existing stale literal exposed by an incomplete migration, not a DSP regression introduced by the changed lines. It blocks claiming that current-base report labels have been fully migrated.

Required fix: derive title/H1 and method-specific wording from the saved result's base/method labels, or use a method-neutral heading and explanation. Do not replace every occurrence with RAW_FULL, since the renderer also handles saved HNM/PML data. Existing historical result files need not change.

### R2 — RAW audio cards still carry the old PML label

Call site: `proposed/vocoderbench/report.py:148`.
Dependency: unchanged `vocoderbench/audio_report.py:6,16,31–32` at the fixed baseline, blob `1e40f854fac4364da89096e1c44df522a8492099`.

The report calls `audio_section(path.parent, base.get('method'), compact=True)`. That function imports CURRENT_LABELS and selects it in compact mode, without receiving the report's saved labels. CURRENT_LABELS intentionally remains `pml: PML低域拡張＋60FWCEP` to protect historical fallback. Thus new RAW audio captions and aria-labels still identify the old PML method even when adjacent table labels identify RAW_FULL. Updating site_summary.short_audio does not fix this distinct rendering path.

Required fix: allow audio_report.section to accept a saved-label mapping (backward-compatible optional keyword), pass the mapping computed by `_render_current`, and use it consistently for compact filtering/captions. Preserve historical defaults or derive them from the historical result. Do not globally change CURRENT_LABELS to RAW_FULL.

Source: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d2fb3101898e91cec9377ceb28f08dd88e80af81/vocoderbench/audio_report.py

## Positive static findings

- `pml/__init__.py` exposes RAWFullParameters and VERSION, and both save/load and save_parameters/load_parameters are aliases to the same payload functions. No public old PMLParameters alias remains. The payload reader requires a directory and both component and A/L files; this review found no public old-payload decode fallback.
- `pml_cli.py` advertises directory input/output and records pml.VERSION. Existing seed/edit arguments and timing boundaries are unchanged.
- `methods.py` still dispatches only pml operations to pml and WORLD edits to its own editor. Its flat ndarray scalar count includes inherited base arrays and A_raw/L_raw; representation text now names A/L.
- `run.py` saves labels alongside formal_base, so a later BASELINE change need not rename those saved results. The public RAW representation still fits the existing encode/edit/decode calls.
- `site_summary.saved_method_labels` prioritizes saved explicit labels. Without explicit labels, it identifies RAW only for the saved exact RAW version under method=pml; old/versionless records remain PML/HNM fallback. It never reads current BASELINE. report tables, schema-2 summary and site-summary audio paths use it correctly, subject to R1/R2.
- Current-base adapter strictly requires selected/pml/raw-full-fwcep60-v1. The reference catalog retains method family pml, 16 kHz, optional/current-base opt-in. Worker implicit-resampling refusal is preserved. Newly generated reference results store the formal version in their display label. The report-only branch reads saved results directly before generating new labels.
- `benchmark_io.py` uses the proposed BASELINE version for new RAW labels and hashes all pml/*.py, including new payload/raw files. Fixed-commit benchmark.py retains formal_base and complete contract comparison before resuming; changed base/source therefore cannot silently reuse old results through its main path. Its saved result records LABELS, and its scalar count traverses the flat arrays.
- All five retired generation drivers reject at the start of main before source/audio reading, encoding or output writes. Their helpers are still importable because the raise is not at module scope. run_quantization imports internal PMLParameters explicitly instead of the removed public alias. No new import reference to a removed public type was found in the inspected consumers.
- `run_edits.py` rejects only stage=decode immediately after argument parsing. Shared helper functions and the measure branch remain. The old native-source hash loop, driver/contract freeze and payload/audio checks were not relaxed. Historical measure work may still refuse the changed source, as intended.
- The three historical-feature reader changes are only explicit storage.load_parameters imports. Existing 2110-dimensional component projection, old single-file accounting and source/input freezes remain. These are historical component readers, not RAW representation evaluators or old synthesis fallbacks.
- Chunk generation retains its old plan version and complete source-binding/current-BASELINE checks before generation. The proposal only clarifies the old-version rejection messages/comments. No plan is silently reinterpreted as RAW.
- Historical method IDs and saved measurement records are not globally renamed. BASELINE previous_version correctly records the old PML base.

## Non-blocking/documentation cautions

- The package README/PORT_MAP still explicitly describe an unadopted proposal. That is accurate here; a final adoption commit must reconcile that wording with its actual status.
- BASELINE selection_report points at a planned adoption HTML path. This is not proof that the artifact exists or the whole adoption bundle is ready.
- The chunk generation module's first-line docstring still says current PML, although the added comments and context docstring identify it as historical. It would be clearer to make that first-line wording historical too, but the retained guards prevent old-labelled RAW generation.
- This static review is not runtime verification, numerical equivalence verification, or a request to add tests/measurements. No new scientific gates are proposed.

## Disposition

Fix R1 and R2 and independently reread those narrow presentation paths. Otherwise no consumer execution/freeze/public-alias blocker was identified in the inspected changes. Adoption HTML/decision/registry and top-level documents remain pending; the entire PR is not declared ready.

## Re-review: both findings closed

The proposal author corrected both paths, and I independently reread the resulting source. Final reviewed patch SHA256: `31696448f7cb403c0e822d02f218855b93aa0fe1e8179ec877be1e766e0cbb15`.

- R1 closed: `proposed/vocoderbench/report.py:134–135,138,147,155` now derives the heading and explanation from the saved method labels/base. The displayed value is escaped. This retains historical HNM/PML labels while correctly naming new RAW output.
- R2 closed: `proposed/vocoderbench/audio_report.py:9–11,18,34` adds an optional label mapping, defaults to historical constants for old callers, and uses the chosen mapping for compact inclusion, captions and aria-labels. `proposed/vocoderbench/report.py:150` passes its resolved saved labels. The mapping is read, not mutated.

Final consumer-review disposition: no unresolved blocker found in the inspected consumer paths. This supersedes the initial two-blocker disposition above. No runtime/render/test/audio work was used to close the findings. Adoption HTML/decision/registry, top-level documentation and overall bundle readiness remain separate and are not approved by this review.
