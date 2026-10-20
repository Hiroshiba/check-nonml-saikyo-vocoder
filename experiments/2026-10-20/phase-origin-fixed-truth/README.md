# 既知の生成条件で位相原点の校正を比べる設計（2026-10-20）

既知の解析的な波形qと一定F0を使い、5種類の生成条件に各100組を新しく用意する研究案です。旧500組の続きや修正ではありません。真の雑音パラメーターを固定し、原点既知のoracle評価と、学習側のデータだけで共通のOLS（最小二乗法）位相を求める評価の2得点を比べます。雑音の当てはめ、BMA、未知F0、自然音声評価、PML変更は加えません。

## 保存した設計とレビュー

- 位相契約：[最小契約の批判レビュー](design/train-only-phase-origin-contract-review-20261020.md)と[独立数理レビュー](design/train-only-phase-origin-contract-independent-review-20261020.md)。理想qの次数3、停留点を求める多項式の次数上限6、部分周期とAR過程の初期分布を整理しています。
- 新研究の正本と比較設計：[解析的な平均qを使う段階判断](design/phase-calibration-mean-provenance-decision-20261020.md)と[真の雑音パラメーターを固定する計画](design/phase-origin-fixed-truth-score-plan-20261020.md)。数値gateは誤差を数学的に保証しない候補条件です。
- 計画の独立確認：[数理・比較設計レビュー](design/phase-origin-fixed-truth-score-math-plan-review-20261020.md)と[実行境界レビュー](design/phase-origin-fixed-truth-score-execution-plan-review-20261020.md)。数値解法の完全仕様、丸めと密度誤差、全保存物の容量上限は未確定です。

## ソース準備と計算開始を分ける

source v2は静的レビューを通過し、500組を167・167・166組に分けた3ownerへ一回の開始指示を送りました。実計測の進捗・成功は未確認で、結果はありません。[固定契約・v1/v2監査・REAPER調査](followup-design/frozen-contract-and-reaper-20261020/README.md)に経過を保存しています。初期文書の「紙上停止」「実行不可」は当時の状態であり、v0・v1の未通過履歴も保持します。PMLを維持します。

6文書とMANIFESTはLibrary `libfile_6687ae2f7da88191ae6d3afd955718c1` v0から原bytesで保存しています。

## 計測前の参照式・表示案・v0監査

[局所得点の参照、参考音声の表示契約、source v0の独立監査など10文書](followup-design/README.md)を追加しました。−1/2 natsはW（白色雑音）の局所近似参照で合否閾値ではなく、未生成の人工参考音声5本も品質比較には使いません。
