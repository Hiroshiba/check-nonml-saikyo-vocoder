# Stage2 符号遷移sidecar独立監査

## 結論

採用可能。元保存DのDecimalによる負/零/正比較と整数件数から、sidecar全3prior×3遷移の行列・分母・除外・strict reversal件数を独立確認し、不整合0。BF、exp、log、LSE、方式差の再計算、候補実行/import/testsは行っていない。

対象 `/workspace/shared/pitch-stage2-sign-review-20261020/package`。全9 manifest filesのbytes/SHA一致。JSONとCSV96データ行が一致。元canonical309行とsummaryのbytes/SHAは、前回監査したstage2結果と一致した。

## 定義と確認値

strict finite reversalは、source/targetがともにfiniteで、負→正または正→負の場合のみ。zeroは独立の行列classで、閾値を導入しない。非finiteを有限分母へ含めない。

次の値はS→L、L→E、S→Eの各遷移で同一だった。

| prior | finite分母 | 負→負 | 正→正 | strict finite reversal | 除外 |
|---|---:|---:|---:|---:|---:|
| static_frame0 | 309 | 154 | 155 | 0 | 0 |
| A_prediction_frozen | 104 | 95 | 9 | 0 | 205 |
| B_log_prediction_frozen | 309 | 159 | 150 | 0 | 0 |

zeroを含む有限遷移セルはすべて0。Aの除外205件はpositive_infinity→positive_infinity141件とnegative_infinity→negative_infinity64件。source/target kind件数も一致し、各priorでfinite+excluded=309。

ここでDは支持片側zeroに由来する±infinityだが、同じ無限大同士の方式差は別artifactでundefined/infinite_minus_infiniteとなる。Dのnonfinite205件と差のundefined205件を同一種類の値と扱わず、有限flip0の分母は104に限定する。

## 出典と一回実行記録

- 元canonical SHA256: `b5b5199bb71001106c9d65bc9c8637c4c2ce81a98ec1a0f03b7473ac5c2f57a6`、14,159,962 bytes。
- 元summary SHA256: `46e71efffa424c36f21dfe54d8d5ee0082ee9780fcdb1a1a6d8cde64c454e2b8`、5,722 bytes。
- sidecar入力archive pin: `1caa151838a24d9c15326c455ff1d174e9d44514c0f8b22a6448c70520b694e5`。原stage2 artifactを参照し、canonical/summaryを更新する処理はない。
- count_once.pyはread-onlyで原値を読み、Decimal文字列parseとzero比較、整数countを実施。実行開始時に新outputを作りattempt1/retry=falseを記録、終了前に原canonical/summary bytes不変を再確認する実装。
- 保存start/receipt/outer-waitはPID3824、attempt1、complete=true、rows309、source_unchanged=true、外側exit0/reaped=true/killed=falseで整合。外側elapsed約0.215秒、worker側約0.154秒で60秒以内。

単一の記録された実行についての整合確認であり、保存資料だけから記録外の全実行履歴を一般に証明するものではない。

## 解釈

前回の「D符号反転は未集計・未報告」という状態に、この独立sidecarを追加することで、上記の有限分母に限りstrict reversal0と報告できる。微小値を0に丸めた判定ではない。非認証の保存有限精度値の符号であり、真値の符号保証や新しいtracking/VUV/音質改善を意味しない。

監査JSON: `/workspace/shared/pitch-stage2-sign-audit-20261020.json`。
