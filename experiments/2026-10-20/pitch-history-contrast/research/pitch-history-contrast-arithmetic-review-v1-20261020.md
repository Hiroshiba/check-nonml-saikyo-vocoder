# 固定100組・履歴対比 v1 算術限定再レビュー

## 結論

**v0 の F1（X/I summary 欠落）は解消。今回の限定算術静的レビューに blocking はない。未実行。** 実行許可・実測完了・予算内完了の認定ではない。

対象は `pitch-history-contrast-source-review-v1-20261020/package` の summary.py、worker.py、CONTRACT、REVISION-v0-v1.diff と旧版との bytes 比較。候補 import/実行/tests/smoke、X/I の実減算、BF/exp/log/LSE は行っていない。

## summary の確認

- group、stratum(main/padding)、prior、quantity(X/I)、direction のタプルを key とする。固定100全件について既存 canonical result の各タグを worker が一度だけ observe に渡す。有限性による対象選別はない。
- 各群は finite/undefined/missing の3件数を0で初期化する。有限符号も negative/zero/positive の3件数を0で初期化する。非有限のときは件数更新後 return し、符号や extrema に入れない。想定外の canonical kind は例外で停止する。
- finite タグの十進文字列を既存 validate で exact Decimal 構築し、0 または保存 extrema との比較だけを行う。減算、exp/log、丸め、normalize、quantize、float 変換、平均等の新算術はない。
- min/max の更新には元の canonical decimal 文字列をそのまま保存する。厳密に小さい/大きい場合は ID 集合を置換し、数値同値なら pair_id を追加する。固定順 loop のため同値 ID は全て固定順に残る。finite 0件なら min/max は null のまま。
- 全有限符号件数の和は finite 件数になる構造。各5軸群の3 kind 件数の和は当該 H/C×main/padding の固定 pair 数となる。正常完了時は4 strata×3 priors×6 directions の72 summary groups を作る構造であり、空の符号/kind も0で明示される。
- worker は canonical JSONL と CSV に用いた同一 value を observe に渡し、結果を summary.groups に保存する。旧 kind Counter と完了件数も保持する。元 D の符号遷移を読まず、前段 sidecar の再集計はしない。
- CONTRACT は今回 X/I の比較・整数計数を明示許可し、前段 D 符号反転追加集計は禁止したまま。finite 0、全同値 ID、丸めなしを source と整合させている。

## 不変性・差分確認

旧版との bytes 完全一致を確認: source/contrast.py、inputs.py、storage.py、run.py、PAIRS.json、INPUT-MANIFEST.json、PREPARATION-AUDIT.json。したがって X/I の直接保存値減算、Decimal 256/ROUND_HALF_EVEN/全9 trap、有限/missing/undefined 条件、A infinity の扱い、固定 H50/C50 と主要97/padding3、元入力 pins は不変。

worker の実差分は summary import、summary辞書初期化、observe 呼出し、summary 出力 fields の追加のみで、添付 diff の当該部分と一致する。追加 evidence は runtime の数値経路に組み込まれていない。

SOURCE-MANIFEST SHA256: `2913969218f72c840f6083268533c531029f01fd2066095c754ab39f59fdbe4b`。列挙23ファイルの bytes/SHA 一致、runtime source 6ファイルの AST parse 通過を独立確認。

## 留保

上記はコードの制御構造と固定入力集合に基づく静的確認であり、実際の summary 件数・値・符号・extrema は未計算。既存レビューの consumer-local input 配置、外側実行境界・一回性、原波形を再測定していないこと、非独立人工系列、元数値の noncertified 性に関する留保は継続する。実行後は canonical/CSV/summary の保存値一致、72群の分母と全極値 ID、完了 receipt を別途監査する必要がある。
