# stage2 入力 manifest v1 最終静的レビュー

## 結論

**PASS。入力面で起動を妨げる不一致はない。** consumer F の実在 path・全 hash 再確認報告、および source v2 の別途独立レビュー PASS と併せ、別開始指示の下で起動可能な入力である。今回の監査自体は実行指示ではない。候補 import・実行・tests、科学値再計算・数値集計は行っていない。

対象: `/workspace/shared/pitch-stage2-input-review-v1-20261020/package`。
最終 INPUT-MANIFEST.candidate.json は4566 bytes、
SHA256 `4531e90f76d1246f56162bb7a34f713be129310aff90d94054ef7edf2d819c31` と独立一致した。

## v0 からの差分

構造比較により、変更は以下だけであることを確認した。

1. state が `frozen_reviewed`、unresolved が空配列。
2. 各 owner の external_stdout/parent_wait に、対応する ZIP member `outer-owner-i/external.stdout` / `outer-owner-i/outer-end.json` を追加。
3. 存在しない stdout_sha256 selector を除去し、`post_fsync_observation=["external_post_fsync"]` を追加。

saved_input/index/stage1_source の path・bytes・SHA・prefix、owner archive、外側証拠ファイルの path・bytes・SHA・prefix、EXTERNAL-MANIFEST SHA、exit/reaped/actualwait selector、all_owners_complete_only は不変。証拠原本の追補・改変・置換はない。

## 独立再確認した項目

- package の ARTIFACT-MANIFEST 全項目のサイズ/SHA、および最終入力 ZIP の全ファイル member と package bytes の一致。
- 3 owner archive のサイズ/SHA、各 EXTERNAL-MANIFEST 自体の SHA、その全列挙 member の ZIP 内サイズ/SHA。
- 各 member selector が ZIP に実在し、ZIP 原 bytes、v0 コピー、v1 コピーが完全一致すること。
- owner field と saved_external_receipt.owner の対応。
- exitcode selector は `returncode` に解決し、型 int・値0。reaped は `external_reaped` に解決し、型 bool・値true。
- elapsed selector は `elapsed_at_real_wait` に解決し、型 float。保存値は owner0=510.2745092360001、owner1=507.8021681120008、owner2=511.269913823。内側の短い wait_seconds や stdout elapsed へ取り違えていない。
- post_fsync_observation は原 outer-end の dict `external_post_fsync` に解決し、stdout JSON object と key集合・各値・各値の型まで一致する。type は文字列、success は bool true、elapsed は float。Python の bool/int の緩い等値だけで判定していない。
- INPUT-LINEAGE は source v2 を参照し、その ZIP62776 bytes / SHA `679dfd2982bcbb4110fea3934a8ede4683c6ebc0cb8cd8e5b120e923d635197e` は shared 保存 ZIP と独立一致。
- STATIC-INPUT-CHECK は source manifest `036bd46cc3bb33999040810c5a05df864ccedad68451cd01f00e3c215a298812` を記録しており、親から通知された独立レビュー対象と整合する。

## 確認範囲の区別

consumer F の絶対 path の実在は F の再確認報告に基づく。この shared 環境からその別環境の実在を再確認したとはしない。元 selected ZIP の今回の再ハッシュも行っていないが、v0 の入力 pin は完全不変で、前監査では元 selected 展開 member 全件を index input-pins と照合済み。

source v2 の実装全体の正当性は別独立レビューに依拠する。今回 source を import/実行せず、その ZIP lineage と実データ上の selector・型・原 bytes の適合を確認した。

STATIC-INPUT-CHECK の `proposed_state_only=true`、`parent_independent_review_pending=true`、`separate_start_instruction_required=true` は作成時点の監査待ち記録であり、入力の値不一致ではない。本レビューで静的入力確認は完了するが、作成時の原記録は改変しない。manifest の state だけで開始権限が自動成立するわけではない。

v0 詳細監査: `pitch-stage2-input-manifest-v0-independent-review-20261020.md`。
