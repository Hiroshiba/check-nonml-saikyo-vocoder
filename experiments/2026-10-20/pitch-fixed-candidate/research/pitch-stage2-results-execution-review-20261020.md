# 固定候補stage2実行成果物：実行・保存証拠監査

2026-10-20 UTC。対象 `pitch-stage2-results-review-20261020/package`。原保存JSON/CSV/整数件数/selector/hash/文字列の照合のみ。候補実行/import/tests、BF・log・exp・科学算術再計算、再集計・極値再探索なし。数値妥当性は別担当。

## 結論

**実行・保存artifactは採用可能。blockerなし。** 全4180unique、309frameが完了し、原stage1保存値と出典、CSV転記、終了証拠が一致する。科学的誤差保証・音声品質改善を認定するものではない。

## 原本・pins・一回性

- ARTIFACT-MANIFEST掲載25files＋自己manifestの集合、全bytes/SHA一致。OUTPUT-MANIFEST掲載fileの全bytes/SHA一致。
- 同梱source-referenceは承認v2の原fileとbyte同一。source SHA `036bd46cc3bb33999040810c5a05df864ccedad68451cd01f00e3c215a298812`。
- 同梱完成INPUT-MANIFEST SHA `4531e90f76d1246f56162bb7a34f713be129310aff90d94054ef7edf2d819c31`。output/pinsのinputs objectと型・値込み同一。実command/receipt/claimの承認SHAと整合。
- claimはこのinput SHAに対する1件。source/input SHAが一致しretry禁止。保存証拠上の一回性を確認したもので、未提出の別ホスト実行不存在まで証明しない。
- stage1の各owner原fileを既往artifact-manifestと全件再hashし、一致。stage2による原stage1書換えなし。sourceからのstage1起動経路もなく、receiptはstage1_claims_or_processes_touched=false。

## Canonical・原値・出典

unique-resultsはID0..4179の4180行。固定indexのK/r_bits/owner/reference_idsと全件一致。S_bitsは原indexのsaved_logBF_bitsに一致。stage1_status全件matched_noncertified。

全4180のstage1 journal pointerについてarchive SHA、member SHA、start/end行のpoint境界・unique_id、最終ledger array_index/member SHAを照合。保存A80_raw/L80_raw計8360文字列は指定owner journalの80桁A/Lイベントと完全一致。S_inputの元selected行とvalues.logBF指定も固定reference index一致。新しいBFを生成・補修していない。

frame-resultsは309行、全full20_complete true、missing_keys空。各20reference_ids/index pointerは固定frame indexと一致。三priorの各20input pointerについて、staticはframe0選択行/values.initial_prior_payload、Aは当該行/values.prediction_prior、Bは当該B行/log_priorで固定referenceと全件一致。

point-summary CSVは4180行、pair-summary CSVは309×3=927行。ID、canonical_line、status、支持数、S/L/EのD、標準三差のkind/decimal/reasonはcanonical文字列と全件一致。空欄を0へ置換していない。

summaryのunique4180/frame309はcanonical件数一致。各保存極値はsummary指定IDのcanonical decimalと文字列一致することを確認した。極値の再探索・順位再計算やLSE等の再集計はしていない。summaryの科学的解釈・全tag/符号の詳細監査は別担当の結論と合わせる。

## 実wait・fsync・資源

外側開始2026-10-20 09:52:32.193765 UTC、実wait終了09:52:41.283247 UTC、monotonic elapsed **9.089476447999914秒**。outer exitcode0/reaped true/無signal、overall_success true。

内部worker PID3721、worker exit0/reaped true、termination_unknown false。progress_snapshot=[3,308,4180,309]、progress_complete true、worker receipt validated。workerは全owner採用true・80dps・unique4180/frame309を記録。内部elapsed_after_wait8.969847950000258秒。

stdoutのstage2_post_fsyncとouter保存objectは型込み一致し、success true、最終保存後elapsed8.994310067000697秒。stdout SHAはouterの値一致、stderr空。内部completeだけでなく、最終fsync後観測と外側実wait<300を併せ採用する。

worker peak RSS **92764KiB**、supervisor peak16372KiB。worker自己計測の保存値であり、独立外部RSS測定やtree合算保証ではない。managed output実bytes合計 **22554766**、claimを含め64MiB未満。worker512MiB/総wall300秒の契約内。failure/partialを成功へ読み替える証拠なし。

## 採用上の留保

source/input/result原本とpointer解決先を不変保持する。80桁設定・stage1 matchedラベルは厳密精度保証ではない。固定人工309frame・三prior条件の記述に限定し、全grid/F0/VUV/MOS・自然音声品質・exact時間再追跡・方式採用へ外挿しない。

機械可読監査要約: `pitch-stage2-result-execution-audit-20261020.json`。
