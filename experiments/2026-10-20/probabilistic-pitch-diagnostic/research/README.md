# 確率的F0・H0の診断に用いた調査と契約

この資料群は固定5入力の直接harmonic射影による確率診断の設計と静的レビューを記録する。実装コードは含めない。各文書冒頭の未実行表記は執筆時点の状態であり、後の実測結果は実験READMEと結果HTMLを参照する。

- implementation-contract.md: 実行したモデル・保存仕様・数値差分
- direct-projection-design.md: 選定前の数理・計算量の検討
- independent-static-review.md: 数式と実装の独立静的レビュー
- saved-analysis-static-review.md: 保存結果からの独立集計の静的レビュー
- interpretation-review.md: H0・prior・energy・octaveを読み違えないための説明
- colored-noise-future-review.md: 次段階候補の調査。AR法は未実装・未実験であり、今回の設定に混ぜていない

現在のbaseはPML。今回の診断は音声合成器や採用判断の変更ではない。作者MATLABのbit一致再現、校正済み確率、音質改善を主張しない。
