# stage2 入力 manifest v0 原本照合

## 結論

2026-10-20。既知の `stdout_sha256` selector 欠落以外に、今回の照合範囲で新しい不一致はない。候補の `BLOCKED_MISSING_ORIGINAL_STDOUT_HASH_SELECTOR_DO_NOT_RUN` と null は意図的な未凍結状態であり、採用・実行承認を意味しない。

候補コードの実行・import・tests、BF・r・exp・log の再計算、科学値の集計は行っていない。独立した標準ライブラリによるファイル bytes/hash、JSON selector と保存値の型・同一性照合のみ実施した。

## 対象と独立確認範囲

- 候補: `/workspace/shared/pitch-stage2-input-review-v0-20261020/package`。
- 3 owner 原本: `/workspace/shared/pitch-fixed-bf-results-review-20261020/` の owner ZIP と展開物。
- index: 既存 `pitch-fixed-candidate-source-review-20261020`。
- stage1 source v1: 既存 `pitch-fixed-candidate-source-review-v1-20261020`。
- stage2 source v1: 既存 `pitch-stage2-source-review-v1-20261020`。
- 元 selected の展開物: 既存 `pitch-bf-selected-input-review-v1-20261020`。

consumer の `/workspace/bf-stage1-*` 等の絶対 path は別環境の記録である。この監査では、その環境の実在・実行時解決を独立再確認したとはしない。shared 原本との内容同一性、および path 中の owner と原本 owner の対応を確認した。

selected 元 ZIP の bytes/SHA は親の既検証記録および index input-pins と一致する。今回その元 ZIP 自体を再取得・再ハッシュしてはいない。展開済み selected の全 pinned member は index input-pins のサイズ/SHA と独立一致した。元 NPZ の byte 同一性は本監査の対象外。

## ZIP・member・hash

候補 ZIP の SHA256:
`08d85edcafb07f6b1afb116e9879394cfe5449d254fee4e5e22d296155d62be6`

候補 ZIP の全11 member は package の同名ファイルと byte 一致。ARTIFACT-MANIFEST の自己除外10項目もサイズ/SHA 一致。候補 manifest SHA は STATIC-INPUT-CHECK の
`302a8416adc3038abbe7b3bb307e0af97b72f28eb4315e11ff34e20439212e15`
と一致する。

入力 manifest の index ZIP、stage1 source v1 ZIP のサイズ/SHA は shared 原本と一致。INPUT-LINEAGE の stage2 source v1 ZIP のサイズ/SHA も shared 原本と一致する。stage2 source v2 は今回未確認であり、v1 の lineage を v2 の検証済み記録として流用できない。STATIC-INPUT-CHECK の consumer Python/mpmath 環境照合は producer の記録であり、本監査で consumer 環境を再検証したものではない。

3 owner の archive サイズ/SHA および EXTERNAL-MANIFEST 自体の SHA は候補の値と一致。各 EXTERNAL-MANIFEST の全列挙 member のサイズ/SHA も ZIP 内 bytes と独立一致した。

|owner|archive bytes|archive SHA256|
|---|---:|---|
|0|2371434|7cba8c83de7703b0d688748b036bc68bc0330e7d06f53576a3e8058e1f73cdb2|
|1|2367284|9214784cc5feade7e3ac3717f971c32581c235f3f48ff88f9de395cc7517d624|
|2|2366598|be4b0a2bdb8d4bc83ca6a6ac0488012c251d24df5efe32746ae54925e1671476|

全 owner で `outer-owner-i/external.stdout` と `outer-owner-i/outer-end.json` は、ZIP 内原 bytes、shared の原展開物、候補 package の小コピーの三者で一致する。候補の各 path/hash/bytes は正しい owner に対応する。root prefix `""` は ZIP の実 member 配置と整合する。

## actualwait selector と raw 値

以下は保存値の転記であり、時間差の再算出ではない。

|owner|returncode 型/値|external_reaped 型/値|elapsed_at_real_wait 型/値|external_post_fsync.elapsed|
|---|---|---|---|---|
|0|int / 0|bool / true|float / 510.2745092360001|510.06233280999913|
|1|int / 0|bool / true|float / 507.8021681120008|507.6422821670003|
|2|int / 0|bool / true|float / 511.269913823|511.0583593150004|

`parent_wait_selectors.exitcode=["returncode"]`、`reaped=["external_reaped"]`、`elapsed_seconds=["elapsed_at_real_wait"]` は全 owner の outer-end 原本に解決される。短い `wait_seconds` や内側の clock 値へ誤接続していない。

全 owner で outer-end の owner、saved_external_receipt.owner、command の authorized owner、archive/path の owner が対応する。saved_external_receipt.parent_sha256 は selected v1 ZIP の SHA と一致。

outer-end の `external_post_fsync` object は、stdout を JSON として読んだ object と key集合・各値・各値の型まで一致する。全 owner の type は文字列 `external_post_fsync`、success は bool true、elapsed は float。これは新 source v2 で予定される照合の入力条件が実データに存在することの確認であり、v2 実装の正当性・採用条件全体を保証するものではない。

outer-end は stdout の SHA 字段を持たない。stdout bytes を今 hash 固定できることと、実行当時の wait receipt にその hash が保存されたことは異なる。null selector を既存 receipt にない架空字段で埋めたり、receipt を追補・置換して既存証拠と見なしてはならない。

## 最終 v1 manifest 到着後の最小差分確認

1. v2 source の ZIP/source manifest の新 pin、変更箇所と lineage を確認する。v0 の v1 source/STATIC-INPUT-CHECK を現行検証と誤表示しない。
2. selected/index/stage1 source、3 owner archive、外側 stdout/outer-end の既存 pin は不変を要求。変化があれば理由と原本同一性を再確認する。
3. stdout hash selector の代替が、原 outer-end の `external_post_fsync` と stdout の型厳密比較、かつ両者の ZIP 内原 bytes 照合であることを source と manifest で確認する。
4. exit/reaped/actualwait selector を維持し、stdout.elapsed を actualwait の代用にしない。
5. `adoption=all_owners_complete_only` を維持する。BLOCKED/null から確定 state への変更は独立レビューと別開始指示を省略する根拠にならない。

本書は未凍結候補の原本照合である。新たな owner 採用判定、点値抽出・差分集計、stage2 実行は行っていない。
