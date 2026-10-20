# First-difference post-F0 adapter: static injection boundary

Date: 2026-10-21 JST. Design only, not an implementation, execution, retry, quality, or adoption authorization.

## Decision

The pinned PML source has no existing public or internal entry point accepting already postprocessed F0 and performing the complete remaining analysis. `pml_analysis.analyze` unconditionally calls the original `f0_postprocess` at line 105. Feeding a new post-F0 into that API would apply the old postprocess again. `codec.encode` also invokes that analyzer, after running REAPER. Neither is a valid injection route for a new postprocessor.

Use a separately named, Library-only experimental adapter with a very small, source-mapped copy of the analysis orchestration after postprocessing. Reuse the existing computational helpers and codec/storage implementations. Do not change the formal Git base, vendored source, old candidate source, original result, or original failure status. The duplication is approximately 24 lines of analysis orchestration, not a new StoneMask, CheapTrick, PDD, NM, FWCEP, storage, or synthesis implementation.

The new R, L, and F cells must all use exactly the same new postprocessor and this same adapter. Original R remains the original REAPER → original `analyze`/postprocessor → original codec path. For the already received first three records, original R is an immutable reference to the existing native result, not a rerun through either adapter.

## 1. Pinned source and exact anchors

Local source root inspected: `/workspace/shared/pml-candidate-sequence-source-20261021-v2/`.

Repository/base commit: `Hiroshiba/check-nonml-saikyo-vocoder` at `2251f947032296c6cdf03e8022c74eefbeef17e8`.

- `SOURCE_MANIFEST.json` SHA256: `06b86cbafc3556e5bee25752ee1f592d592554298524a2762264483e97e38eae`.
- `DEPENDENCY_SOURCE_MANIFEST.json` SHA256: `90fdeacbb4212323b78e991dab2ff4ac6772025e0f6ea534aaa7f3b5e65b7115`.
- `native_adapter.py` SHA256: `9cb5a17caf711b46f3a3bd58a01652d99b51e4ab036be5cb4f8e9224c24bb890`.

The local hashes above were read-only checked against the inspected files. Git blob IDs below are the pinned dependency manifest's lineage, not newly fetched Git objects.

| Source | Pinned Git blob SHA1 | Source SHA256 | Relevant lines |
|---|---|---|---|
| `pml_analysis.py` | `61f71548f8afc88fe0f44c8ebbcff19b311a5489` | `9460b53c28d1fde3a99f66820de17b0d3f4bc18bec35ab43a349ca753b56708d` | postprocess 14–78; NM 81–96; analyze 99–126 |
| `pml_pdd.py` | `841cb92999a072092fb78af24a23f79243f82053` | `d87f2f2cd3bdc16367e956eaa742502a6c2ebf509a4e63eb5e666c8e0ef7521c` | local RNG and PDD pipeline 179–190 |
| `codec.py` | `4fe77b9986718774476ab91a26f5ab6ea4785481` | `86d4e9db6dc6c7857917b729eb1046f6bc4a9b2f59536826f64cc19845e053f1` | original R extraction 38–65; FWCEP/params 66–92; decode 95–125 |
| `storage.py` | `3a9b80c16540d243cec4dad4cb21ef88263993e1` | `6f9da667daca00da9e31f7be436b9bc412d2510a426359a43eeb0c6add154095` | save 16–39; load 42–95 |
| `parameters.py` | `3a525f78d9e21b5ac7c9270ba40428f3823a657f` | `dcc3e45c28602354ee6b06a8622ed242c876fdfe90982630ef03deb997b0b2f5` | strict F0 validation 49–50; saved times 62–64 |

Direct pinned source links: [analysis](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_analysis.py#L99-L126), [PDD](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_pdd.py#L179-L190), [codec](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/codec.py#L95-L125), [storage](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/storage.py#L16-L95).

Additional exact local adapter anchors:

- `native_adapter.validate_input`, lines 9–19: existing audio contract.
- `native_adapter.check_grid`, lines 22–29: exact float64 saved 5 ms grid.
- `native_adapter.encode_external`, lines 32–51: L/F-only raw shape/grid guard, original analyzer invocation, identical FWCEP/parameter construction.
- `native_adapter.persist_trace`, lines 54–70: current trace writer. Actual arrays are directly under `branches/{name}/`, not a nested `trace/` directory.
- `native_adapter.run_branch`, lines 73–117: original branch dispatch, save/load/decode, actual output shape checks, trace-finalization behavior.
- `artifact.Output.step`, lines 135–153: stage/exception events; `capture_notices`, lines 198–217: scoped warning/logger capture and restoration.

## 2. Exactly what changes inside F0 postprocessing

Create an explicitly named function such as `f0_postprocess_first_difference_v1`. Its source lineage is the body of original `f0_postprocess`, lines 15–78, with only the smoothing operation at lines 48–49 replaced. Retain the existing defaults, preprocessing, grid construction, interpolation order, dtype assignment behavior, jitter rule, fallback, diagnostics, and final checks.

Preserved operations, in source order:

1. Copy raw input and preserve source dtype, shape handling and validation: lines 15–23.
2. Same diagnostics and all-unvoiced fallback to the existing minimum: lines 24–36.
3. Same interpolation through positive raw values and existing inclusive clip to 65..700 Hz: lines 37–40.
4. Same selected row indices, mean raw time step, `fc`, `hshift`, internal `arange` grid, and linear interpolation to `data`: lines 41–47.
5. Replace only the original Butterworth construction and `filtfilt` operation: original lines 48–49.
6. Same interpolation of the new `smooth` back into the source-dtype F0 array: line 50.
7. Same jitter, dtype-specific threshold, optional regular-grid resampling, output diagnostics, and finite/positive final validation: lines 51–78.

The new smooth operation is the already specified finite first-difference solve, not a new family or tuning proposal:

- For m internal-grid samples, D has shape (m−1)×m and `(Dz)[i] = z[i+1] − z[i]`; there is no division by the time step.
- `A = I + ρ DᵀD`, with `ρ = 1/(2−sqrt(2))` fixed.
- Solve `A smooth = data` once, in linear Hz on that same internal grid.
- Natural finite endpoints: endpoint diagonal `1+ρ`, interior diagonal `1+2ρ`, and adjacent off-diagonals `−ρ`. No periodic wrap, extra padding, or invented extension.
- ρ is not the selector's existing λ=1. The selector is not changed.
- One solver/arithmetic realization must be fixed in a future source manifest. No runtime solver dispatch, fallback solver, regularization, clipping, epsilon repair, or retry with a different result.

For the L/F 5 ms raw grid, the source formulas give the existing internal approximately 2.5 ms grid. Do not substitute a 5 ms smoothing grid. For R, calculate the internal grid from the exact received R raw times exactly as the original source does; do not normalize R times to the L/F grid. The source's mean-step arithmetic, `arange` endpoint exclusion, and jitter-dependent resampling stay intact.

Existing diagnostics may be retained as historical keys, but a new mandatory model identity must explicitly name the first-difference smoother. A generic `step_removal=true` must not imply that the original Butterworth was executed. Exact ρ representation, internal sample count/grid identity, solver identity, and new postprocessor source hash belong in the new branch provenance, not in the old original files.

## 3. Thinnest honest processed-F0 boundary

A new, explicitly named helper, for example `analyze_from_postprocessed_f0`, is part of the new adapter. It does not already exist in the pinned package.

Its computational body is source-mapped to original `analyze` lines 102–104 and 106–126. It accepts the already computed `f0s` and its diagnostic dictionary, omitting only original line 105. It retains:

- contiguous float64 waveform conversion and mono/finite validation: 102–104;
- contiguous float64 `times` and `cf0`: 106–107;
- `pyworld.stonemask(x, cf0, times, fs)`: 108;
- `pyworld.cheaptrick(..., fft_size=dftlen)`, original power validation and `sqrt(power)` amplitude: 109–112;
- the existing `analyze_pdd(x, fs, f0s, dftlen, seed)`: 113;
- the existing `noise_mask(f0s, pdd, fs)` at its unchanged 0.75 threshold: 114 and 81–96;
- the same features and downstream diagnostics: 115–126.

The new wrapper validates the original input, accepts an identity-checked raw contour, calls `f0_postprocess_first_difference_v1` exactly once, immediately records the returned post-F0 and diagnostics, then calls the new processed-F0 helper. Recording the post-F0 before downstream analysis allows a StoneMask/PDD failure to retain the actual completed postprocessing result, without reconstructing it later. This trace bookkeeping is not an additional scientific transform.

An equally thin single new raw-F0 analyzer could copy 102–126 and replace line 105 with the new postprocessor call. The split helper is preferable only because it makes the one-postprocess boundary explicit and permits immediate capture. It must not become a generic callable/solver-selection injection framework.

Do not:

- feed new post-F0 to original `analyze` or `encode_external`;
- run `codec.encode` to generate the new R raw again for the first three records;
- monkeypatch `pml_analysis.f0_postprocess`, module globals, `pyworld`, `sys.modules`, or imported function bindings;
- dynamically rewrite/execute the source of `analyze`, use frame interception, or install a temporary replacement through a context manager;
- replace only `params.f0` while retaining SPEC/PDD/NM from a different clock;
- replace the synthesis/PDD clock with `refined_ct_f0`.

The source explicitly limits StoneMask refinement to CheapTrick: original lines 113–120 send post-F0, not refined F0, to PDD and synthesis. Preserve that distinction.

## 4. Same FWCEP, payload, loader and decoder

After the new analysis returns, the adapter reuses the same existing validation and parameter expressions from `native_adapter.py` 44–51 / `codec.py` 66–86:

- SPEC shape Jpost×2049, finite and strictly positive;
- saved/post time grid bitwise equal to float64 `arange(Jpost)*float64(0.005)`;
- existing `fwcep.encode_log(log(SPEC), 16000, 59)` and only its original float32 payload conversion;
- existing `PMLParameters`, with analyzed NM and post-F0, original n_samples, seed=0, default pitch shift=0;
- existing `save_parameters`, followed by existing `load_parameters`, then existing `decode(stored, seed=0)`;
- native output finite float64, mono shape exactly `(n_samples,)`, with no normalization, clip, trim, or alignment.

Storage remains `PMLFWC01` / `pml-fwcep60-lowband-v1`. The body is float64 F0, 60 float32 FWCEP coefficients, and little-bit-order packed binary NM. The original body checksum, exact field set, size, padding, dtype/shape and constructor gates remain. New experiment provenance belongs in sidecar files, not a changed payload schema.

`PMLParameters` strict `50 < F0 < 700` is not relaxed. In particular, the original inclusive preprocessing upper clip can produce exactly 700 for R; the new path does not move that value inward to make a payload valid. Any failure remains a failure.

## 5. R-specific raw contract, without accidental resampling

The current `encode_external` raw validation at lines 37–40 is specific to L/F: it requires exactly `(1+(N−1)//80, 2)` float64 and bit-exact fixed 5 ms raw times. It is invalid to apply this guard to actual REAPER raw.

Define two provenance/shape guards before the one shared new postprocessor:

- L/F: require the exact archived two-column submitted/raw member; expected J, float64, finite, fixed raw-time bit pattern, and identity with the saved selection receipt.
- R: require the exact archived `branches/pml/raw_f0.npy` member and its own received shape/dtype/file/data SHA; then the original postprocessor's finite/strictly increasing raw-time contract. Do not require L/F J or L/F raw-time bits.

Both then use the exact same first-difference postprocessor and postprocessed-F0 backend. Only after preserved jitter/resample handling is the fixed saved 5 ms grid checked. The L/F saved frame-count check remains against L/F J; for R, check its actual returned post frame count and fixed saved-grid bits, without inventing equality to L/F or its own raw count.

The first-three JSON inventory records the mismatch clearly:

| Record suffix | R raw frames | Original R saved post/native frames | L/F raw frames |
|---|---:|---:|---:|
| 0008 | 1195 | 1194 | 1200 |
| 0011 | 1196 | 1195 | 1200 |
| 0032 | 814 | 814 | 818 |

These counts are metadata observations, not a new waveform or filter calculation. Do not align same-index R and L/F post arrays when their grids/frame counts differ.

## 6. First-three reuse receipt and immutable original status

Received envelope:

- Path: `/workspace/shared/pml-native-first-received-20261021/delivery.zip`.
- Library ID/version recorded by parent: `libfile_c4a085e9297481918bae5d8bbbea6e0f`, version 0.
- Envelope bytes/SHA256: `19922354` / `a78bc6019de20a8ff702165b60121c5263324cb0c8c47514a1777498149d0a7a`.
- Inner `native/native.zip` bytes/SHA256: `19911267` / `8c402790d826825d87dbadcc7cd908d7747e629c2ea9342dc9408d2c5264dc96`.
- Inner `FILES.json` SHA256 recorded by the independent failure replay: `12e38db01ed45e964d361024516e4cae3ad21298822317c699a6e72884f4d5e1`.
- Actual native exit remains 2; native status remains `native_incomplete_scientific_failures`; original quality approval remains false.

Use these actual two-column raw members, not a reconstructed REAPER raw contour or reselected L/F. Prefix for every row is `records/librispeech_1089-134686-` followed by its suffix, then `/branches/`:

| Suffix | Branch member | Shape | Member SHA256 |
|---|---|---|---|
| 0008 | `pml/raw_f0.npy` | 1195×2 | `ce115dd602fc9711555ef9630505277b00b7d8e18a691078cbe85958ab27acba` |
| 0008 | `L/raw_f0.npy` | 1200×2 | `02ca4253a814f771624a7764336fb8b819986c4f9861fb35a96b709f9f059b91` |
| 0008 | `F/raw_f0.npy` | 1200×2 | `125cc51fc217a8f12a5d097d7557325a07d3b9af1bc349b0916cdc249f102a55` |
| 0011 | `pml/raw_f0.npy` | 1196×2 | `dd2532305862147bb5b31c437901f0b8574ce46363ff976a39ba1f8e1b409ace` |
| 0011 | `L/raw_f0.npy` | 1200×2 | `d1b31c949ff64d45f323501f47e6ee5bd434ffb0623b0b71cf2b7cd66c772b4c` |
| 0011 | `F/raw_f0.npy` | 1200×2 | `1248c1a97bed4284aa39eb8d8268a0e8e54da2396d261682596c8ffb01ddcc4a` |
| 0032 | `pml/raw_f0.npy` | 814×2 | `bc75738a0a744d8cd63aa88f1a990455a02a541450873e3b6b8d649bcf29397c` |
| 0032 | `L/raw_f0.npy` | 818×2 | `12d227b7ef6e352cb2b77c25c786fe46c47dbca344732eb2ace22887bca06922` |
| 0032 | `F/raw_f0.npy` | 818×2 | `cac1d80915c4d247494b0b045d646994435a22ef8b45e5efca2149f84fbb9d0a` |

All above raw dtypes are `<f8`. The inventory also records data SHA256 and member byte sizes. Pin those exact fields in the future machine-readable raw receipt; do not substitute the file hashes for data hashes or reconstruct them without reading the actual permitted arrays. L/F `submitted_raw_f0.npy` has the same file/data identity as its corresponding two-column `raw_f0.npy`. The selector's own `raw_f0.npy` is one-dimensional and is not the direct analysis input member.

Original R native members are `records/{id}/branches/pml/native.npy`, with these immutable member SHA256 values:

- 0008: `66fa9fe6bb6e0880a2213e700ec59f6dd8af48283c5c350d980d948bf12644f6`, float64 shape 96000.
- 0011: `19db23acecafc5665e49ab0037adf2647aeebbadcee67b34b6cc67c48641b7c2`, float64 shape 96000.
- 0032: `80bf274d7883bff30b22f1eae1ea2a40cb7d3f7fdc0bc75162dc90e44faa6cc8`, float64 shape 65440.

Original L/F do not acquire native-success references: all six remain the original failures. The independent diagnostic replay at `/workspace/shared/pml-native-failure-selection-replay-20261021/actual-saved-selection-verdict.json` matched saved L/F paths, offsets and objectives only. Its diagnostic exit 0 is not native exit 0, not independent likelihood recomputation, and not quality approval. It permits no claim that the original B experiment succeeded.

A future first-three new-post experiment would consume the same archived original input bytes and these nine raw contours, run only the three new-post cells per record, and reference original R output/original L/F failure receipts. It would not call `LocalPotentialMath.build`, `collect_potentials`, `select_local`, `select_sequence`, REAPER, or the original postprocessor. The original B quality phase and remaining 117-record expansion stay blocked; this design does not release them.

## 7. Identity and schema gates for the new artifact

Use distinct identities such as `R/original-reference`, `R/first-difference-v1`, `L/first-difference-v1`, and `F/first-difference-v1`; do not reuse a formal `pml` success label for experimental R.

Every planned branch receipt should identify:

1. Record ID, selector identity R/L/F, original input manifest SHA, exact original input member/file/data identity, n_samples and sample rate.
2. Source envelope/inner archive/FILES identities, raw member path/bytes/file SHA/data SHA/dtype/shape, raw-time identity and original raw-source branch. R and L/F guard kind must be explicit.
3. Original failed-native source/receipt identity, independent failure-replay receipt identity, and whether the cell is a read-only old reference or a newly executed experimental cell.
4. New hypothesis/postprocessor version, fixed D/ρ definition, frozen scalar representation/solver source identity, complete new source manifest and Library source receipt identity; same identity across new R/L/F.
5. Pinned base commit, dependency manifest, every reused vendor file hash, actual Python/dependency/thread runtime, analysis/decode seed=0.
6. Completed stage and exact status: raw admitted, post completed, backend completed, parameters constructed, saved, loaded, decoded. A later failure never makes an earlier actual array unavailable or fabricates later output.
7. Post-F0/time-bit and refined-CheapTrick-F0 identity, diagnostics, payload identity, native identity and actual outer execution/exit/capture/packing receipt, only where actually produced.

New schema and source manifest have separate versions; never edit the original schema/manifests to insert the new experiment. Record which source byte range was copied unchanged, which original operation was replaced, the new destination range, and destination SHA. Carry the original PML/sigproc copyright, license and port mapping notices. Static source lineage is a necessary provenance record, not empirical equivalence of the new orchestration.

Reverify envelope, manifest and every consumed member identity before an authorized numerical import/load. Preserve original archives and receipts. No new output may overwrite them. Input/output/source/receipt collisions, path escape, symlink/duplicate archive member ambiguity, missing/extra expected branch identity, dtype/shape mismatch, and receipt disagreement are hard provenance errors, not scientific missing-data substitutions.

These are identity/capture gates and the existing native contracts only. This memo defines no new acoustic criterion, quality threshold, tuning rule, independent test set, or scientific adoption gate.

## 8. Minimal module plan and state ownership

A sufficient future Library-only layout has three small new Python modules, each at most 400 lines:

- `first_difference_post.py`: the explicitly named copied postprocessor body, fixed first-difference solve, and local diagnostics. No waveform codec, candidate selector, registry, or mutable cache.
- `native_post_adapter.py`: explicit one-postprocess wrapper, approximately 24-line source-mapped post-F0 analysis backend, identical FWCEP/parameter construction, and thin branch save/load/decode orchestration. Reuse existing `validate_input`, `check_grid`, trace/Output and storage/decode helpers where the contracts match. Do not reuse current `run_branch` dispatch unchanged: lines 83–84 select only original encode or original external analyzer.
- `run_saved_first3_post.py`: standard-library source/receipt/member verification first, fixed first-three branch plan, then the authorized driver and capture/finalization. It imports no selector/local-potential engine for this reuse path and contains no old-model execution entry point.

Module lengths are proposed ceilings, not existing implementation measurements. There is no need to duplicate the candidate scientific engine or create a fourth generic codec. Existing immutable dependencies and their manifests/licenses are included unchanged in a separately identified Library source artifact if code preparation is later authorized.

Scientific state is explicit in function arguments, local arrays, and a per-branch trace object. No module-global choice of postprocessor, solver, selector, grid, branch, seed, or temporary function substitution. No global RNG seed; existing `analyze_pdd` creates its local RandomState at lines 179–186, and decoder receives explicit seed=0. Different F0 paths can consume random numbers differently despite the same seed; identical timewise noise is not promised.

The parent's intended exception is retained: in a single dedicated process, existing `artifact.capture_notices` may temporarily capture warnings and logging and restore them in its existing `finally` scope (198–217), solely for complete notice recording. It is not a scientific injection mechanism. Do not expand a ban on mutable scientific state into a new logger architecture. Existing `Output.step`/failure handling and external stderr/actual-exit capture must retain full messages and tracebacks, including a failure before or after postprocessing; no truncation, silent suppression, clipping or candidate dropping.

Retain the existing pinned numerical/runtime/thread and resource/capture contracts. Any separately required outer execution or resource permission remains a launch gate. The driver must not claim internal `CAPTURE` alone proves OS completion, success, or Library delivery.

## 9. Remaining blockers and current authorization boundary

Resolved by this static design:

- Existing processed-F0 API absence is established from actual source, not assumed.
- A minimal no-doublepost, no-monkeypatch boundary exists through explicitly disclosed source-mapped orchestration copying.
- R's raw-grid exception and actual archive member identities are separated from L/F validation.
- Original results, failures, original R source path, and strict payload/native contracts can remain unchanged.

Still required before code preparation or execution, as applicable:

- Parent scientific review/acceptance of the separately named first-difference hypothesis and its finite endpoint semantics. This report does not certify acoustic suitability or native success.
- Explicitly frozen future solver arithmetic/scalar representation and source lineage. No solver is implemented or tested here, and no fallback is proposed.
- Separately authorized code preparation, immutable new source/Library receipt, and static audit of the one-call graph and copied ranges.
- Separately authorized numerical execution in the required environment, with original input/raw receipt gates, limits and actual external execution evidence. The present task is not that authorization.
- Existing original B quality and 117-record blocks remain. A new-post result cannot retroactively unblock the old experiment or prove original L/F quality.

No blocked action was attempted. The pending items are design/authorization boundaries, not tool denials.

## Work actually performed

Read-only local source inspection and text hashing; existing JSON receipt/diagnostic reading; ZIP member-list/JSON inventory inspection only, using standard-library archive handling. No project/vendor or numerical-package import, waveform/NPY-array read, new array arithmetic, filter solve/replay, analysis, resynthesis, quality metric, source implementation, test/help/smoke run, Git operation, network operation, Cloud write, or Library write. This Markdown design file is the only deliverable written for this task.
