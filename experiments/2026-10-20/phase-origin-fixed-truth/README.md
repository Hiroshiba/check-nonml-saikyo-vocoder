# 既知の生成条件で位相原点の校正を比べる設計（2026-10-20）

既知の解析的な波形qと一定F0を使い、5種類の生成条件に各100組を新しく用意する研究案です。旧500組の続きや修正ではありません。真の雑音パラメーターを固定し、原点既知のoracle評価と、学習側のデータだけで共通のOLS（最小二乗法）位相を求める評価の2得点を比べます。雑音の当てはめ、BMA、未知F0、自然音声評価、PML変更は加えません。

## 保存した設計とレビュー

- 位相契約：[最小契約の批判レビュー](design/train-only-phase-origin-contract-review-20261020.md)と[独立数理レビュー](design/train-only-phase-origin-contract-independent-review-20261020.md)。理想qの次数3、停留点を求める多項式の次数上限6、部分周期とAR過程の初期分布を整理しています。
- 新研究の正本と比較設計：[解析的な平均qを使う段階判断](design/phase-calibration-mean-provenance-decision-20261020.md)と[真の雑音パラメーターを固定する計画](design/phase-origin-fixed-truth-score-plan-20261020.md)。数値gateは誤差を数学的に保証しない候補条件です。
- 計画の独立確認：[数理・比較設計レビュー](design/phase-origin-fixed-truth-score-math-plan-review-20261020.md)と[実行境界レビュー](design/phase-origin-fixed-truth-score-execution-plan-review-20261020.md)。数値解法の完全仕様、丸めと密度誤差、全保存物の容量上限は未確定です。

## ソース準備と計算開始を分ける

ソース準備を別Cloudに依頼済みです。ソースレビュー、最終契約の確定、計算開始の別判断は未完了で、生成・計測は一度も行っていません。文書中の「紙上停止」「実行不可」は計測が許可されていない状態を示し、ソース準備の依頼とは区別します。ベース手法はPMLを維持します。

6文書とMANIFESTはLibrary `libfile_6687ae2f7da88191ae6d3afd955718c1` v0から原bytesで保存しています。
