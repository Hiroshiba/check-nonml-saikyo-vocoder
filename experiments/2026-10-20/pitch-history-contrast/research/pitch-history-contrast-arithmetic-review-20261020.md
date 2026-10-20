# 固定100組・履歴対比の独立算術静的レビュー

## 判定

**X/I の定義・有限値条件・Decimal 契約は静的に通過。ただし、必要な X/I の符号・range・該当 ID summary が欠けるため、現版の成果物契約は修正後再確認が必要。未実行。**

対象: `pitch-history-contrast-source-review-20261020/package`。確定 design 2文書、CONTRACT、全5 Python source、PAIRS、入力/source manifest を読んだ。候補 import/実行、tests/smoke、実際の X/I 減算、BF/exp/log/LSE/closure は行っていない。独立処理は stdlib の JSON 読取、hash、AST、固定 ID/分類の整数照合だけ。

## 要修正 F1: summary の範囲の縮小

確定 plan §6 は今回 X/I の群・prior 別の符号・range・該当 ID を許容している。一方 CONTRACT 29行は「件数だけ」「range/符号追加集計は行わない」と縮小し、worker.py 39–60行は kind 別 Counter と完了件数しか保存しない。親の最新要件ではこれらは結果解釈に必要な既定 summary であり、欠落を解消すべきである。

修正は、同じ正本 X/I の有限値の比較と整数計数に限定する。H/C、main/padding、prior、X/I、方向を分け、finite/undefined/missing の分母と負/零/正、有限 min/max と対応 pair ID（同値の扱いも固定）を明示する。非有限値を zero や有限分母に混ぜない。これは今回の条件間 X/I の記述であり、前 stage2 の D 符号遷移 sidecar の再集計とは異なる。追加 BF、差の再構成、closure、D 符号反転集計の許可ではない。

## 通過した算術・保存条件

- PAIRS は 0..99 の固定順100件。H は E-U−U-U、53..102 の50件、C は E-U−E-E、0..49 の50件。H main49/padding1、C main48/padding2。主要97とpadding3を保持し、効果や有限性による選別を行わない。各 pair の unique_ids は20。
- `contrast.calculate` は X[S/L/E] を左右の保存 D から、I[L_minus_S/E_minus_L/E_minus_S] を左右の保存 g から直接減算する。方向は常に E-U minus 比較条件。X を引き直して I を作らず、I_total の和置換もない。
- 新規 Decimal context は prec256、ROUND_HALF_EVEN、Emin−999999/Emax999999、capitals1/clamp0、空 flags、Inexact/Rounded/InvalidOperation/DivisionByZero/Overflow/Underflow/Subnormal/Clamped/FloatOperation の全9 trap。worker の全算術 loop を localcontext で囲む。文字列から Decimal を直接構築し、float、normalize、quantize を使わない。有限 zero 出力のみ文字列 "0" とし、原タグ・文字列は別途保持する。
- full20 が片方でも True でなければ全 prior 全 X/I を missing とする。未知タグ・不正 finite は通常欠測に隠さず例外で停止する。
- X は双方 finite だけで減算。missing が優先、他の非有限入力は undefined/nonfinite_condition_contrast。I は双方 g と、その方向の両 X が finite のときのみ減算し、missing を優先する。A の同符号 infinity 同士も zero にしない。支持・タグ一致は別 bool である。A を B で置換しない。
- canonical は原 D/g、支持 mask、両 frame pointer、missing_keys、固定 pair metadata を保持する。CSV は同じ result を転記し独立再計算しない。通常完了なら100行、3 prior×6 quantities の1800 CSVデータ行となる構造。
- input 前提検査は両観測 hash、原 frames、20候補軸48/148×K1..10、unique/K/r/S bits、static frame0 prior、C の元 A/B bits を照合し、不一致なら停止する。reference_id 自体の条件間一致を要求しない。原波形を新規測定するコードではない。
- 100件初期 ledger を先に保存。例外を捕捉して failure を残し再試行や精度増加をしない。完了扱いには100件・worker正常終了等を要求する。実行境界、OS予算、外側 wait の最終承認は別レビュー対象。

## 同一性と適用範囲

SOURCE-MANIFEST SHA256: `33f28af383b1c9f4f212bdc31af518a893f6cdcadf48cfa3f5c7bf18dd50cb66`。列挙16ファイルの bytes/SHA は全一致、5 Python は AST parse 通過。PAIRS SHA は入力 manifest と一致。

入力 ZIP の固定 SHA は既監査の stage2/selected/index と一致。ただし INPUT-MANIFEST の consumer-local 絶対 path はこのレビュー環境には存在しない。今回それらの path を開いた、または候補 receive を動かして全入力を再検証したとは主張しない。指定 consumer 環境での存在・実行前 hash 確認と独立入力レビューを条件とする。別 path への自動探索・置換は認めない。

このレビューは保存十進減算の設計を対象とし、256桁で必ず完了すること、60秒/128MiB内完了、元80桁値の真誤差・符号保証、C による一般的な未来漏洩不存在、H の単一因果機構、品質改善を認定しない。科学値・統計量は新計算していない。
