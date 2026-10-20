# RAW_FULL adoption bundle: independent static review

2026-10-19 UTC. Reviewed the Git-external `raw-base-integration-proposal-20261019/proposed` tree against its base snapshots and the retained accepted source artifacts. This is a review of a proposed adoption change, not evidence of remote merge or deployment. Actual main remains PML until adoption is applied.

## Disposition

One narrow documentation blocker was found: `proposed/vocoderbench/pml/PORT_MAP.md` still labels its new section `RAW_FULL 統合提案（Git外、未採用）`. That accurately describes the local review stage but should not ship as the adoption-change description. Use prospective wording describing selection in this change, while preserving the static-only verification caveat. No scientific-value, report/decision, BASELINE, registry or manifest blocker was found in the inspected bundle.

The currently present proposal.patch appears to precede the new report/top-level documents. Regenerate the final delivery patch from the completed tree; this review primarily concerns the proposed files, not that stale patch.

## Scope and limits

Read-only shell inspection, diffs, JSON/gzip parsing of saved documents and SHA256/byte-count checks only. No vocoder import or execution, builds, tests, rendering, audio loading/playback/conversion, new measurements, or Git operations. This review report is the only file written. Core math and consumer reviews were read separately; their static findings are not converted into runtime guarantees here. No all-79-axis, eight-seed, zero-warning or other new adoption gate is introduced.

## Metadata and documentation coherence

- BASELINE selects only method family `pml`, version `raw-full-fwcep60-v1`, retaining previous version `pml-lowband-fwcep60-v1`. Comparison-reference semantics explicitly distinguish the current unique development base from historical saved comparisons.
- BASELINE and decision both point exactly to `research/raw-full-adoption-selection-2026-10-20/index.html`; this proposed file exists.
- README, STATUS, PML API documentation, EVALUATION and the historical PML evaluation introduction consistently describe selection in this change. They do not claim the remote repository has already adopted it. Old STATUS entries are explicitly historical.
- The package README now uses prospective selection wording. Public save/load directory semantics, required A/L, absence of old independent decoding, gain path and unmeasured gain performance agree with the independently reviewed API change.
- The old PML evaluation text is preserved under a historical framing. No prior measurement files are changed in this partial proposed tree. Existing registry entries compare identically; only one entry is appended. This is not a full repository-wide historical-file audit.

## Scientific values and interpretation

The four source byte hashes in decision.json match retained quality report, historical comparison gzip, pure-RTF report and clip manifest. Parsed saved-data comparison found no mismatch across 313 copied quality/RTF/storage fields. All 40 historical method rows across four axes retain their 440 scientific/status fields, including exact rational means, competition ranks and support counts. Their `source` field intentionally now points to the saved historical comparison row rather than reproducing its nested upstream source descriptor; the original source is reachable through that exact pointer and hash.

HTML values and rankings agree with decision.json: RAW ranks 2/3/2/2 for eSTOI/MR-STFT/ERB40/ECAPA. Directions, native seed-0 supplementary scope, 120 recordings/40 speakers and rank emphasis are explicit. No overall score/rank or all-method MOS comparison is invented.

The report displays small mean benefits and concrete losses together: MOS +0.07676038675838046 with 195/720 adverse pairs and 22 warnings; edited F0 +0.18156969916476828 with an interval crossing zero; voiced misses +0.154538134 percentage points with 219/480 adverse pairs and 28 warnings; CER/WER adverse differences on only 55 GT recordings, 32 speakers and 330 pairs, without fabricated confidence intervals or zero-valued missing cases. Native fidelity and speaker metrics retain their separate directions and counts. Undefined warning thresholds are not described as zero harm.

Saved storage +17.120749314956374% includes payload and metadata. Main120 speaker-equal wall RTF operands are copied exactly: PML analysis/decode 1.0402107147462065 / 0.18330100549968464; RAW 1.0165404049159603 / 0.1929033522864625. Approximate +5.24% decode cost and −2.28% analysis time are qualified as single fixed-order measurements, not universal speedups or timing of the newly integrated package.

Selection is explicitly a post-hoc engineering tradeoff, not superiority/noninferiority proof. Development-used support, two generation seeds, edited/native reference limitations, unmeasured gain/full-feature distance/interpolation and arbitrary-pitch/48 kHz limits remain visible.

## Historical false flag

Decision preserves `historical_adoption_evaluation_complete=false`. Its frozen SPECIFICATION-ja.md hash is independently matched (`62b9592f486e18d92e887cf712157cc3990ec4fec6f99bdf60b3b4812f73e80c`), and line 17 explicitly requires the historical `adoption_evaluation_complete=false`. Quality-completion `complete=true` is not conflated with adoption evaluation completion. The new selection status and activation text separately describe adoption in this change.

## Manifest, registry and audio

Artifact manifest has schema 1 and a UTC created_at explicitly marked document assembly time. Both file byte counts and SHA256s match. Registry manifest bytes/hash match; artifact_count=3 equals the two listed artifacts plus the manifest itself. Existing registry entries are unchanged. The 2026-10-20 path versus 2026-10-19 UTC creation is consistent with the Japan-time date documented in STATUS.

Three audio entries match clip-manifest pointers /clips/3, /clips/49 and /clips/50, including case, variant, pitch, seed, start/end, published path, size and hash. Those paths exist in the retained published bundle. HTML uses those exact public paths and includes attribution/license navigation. The retained publication-state record documents prior +3 PML/RAW seed-0 browser playback and live RAW byte verification; its RAW hash matches the decision. I did not newly fetch/play any audio and do not claim independent current network verification of all three URLs. The report correctly states existing published audio is reused without new conversion/normalization.

## Reviewed artifact identity

- decision.json: 137520 bytes; SHA256 `40596faa5c6eb9a46c13d153f6f5fad33e104dd5586609a9e7e428bdad07c605`
- index.html: 22835 bytes; SHA256 `b0c2a62fdcad641443b45ccb552023ce883c7cde4a8d9f3586f43b8199a5445e`
- artifact-manifest.json: 450 bytes; SHA256 `d21d095d26d2e1f85cc709ebaf9bc5631e3ed76a02bbb64c56d3081d46b11f2e`

After the narrow PORT_MAP wording correction and final patch refresh, no further blocker is identified within this static review's scope. Any later artifact change requires corresponding manifest/registry refresh.

## Narrow re-review: blocker closed

Independently reread PORT_MAP after the parent's correction. The heading now says `2026-10-19 RAW_FULL 統合（本変更で選択）`; the source-reading/static-only caveat remains. This closes the documentation blocker above. Final disposition: **no unresolved blocker found within the reviewed static bundle scope**. Parent will regenerate the complete patch and delivery hashes; that final packaging remains separate from this file-level review.
