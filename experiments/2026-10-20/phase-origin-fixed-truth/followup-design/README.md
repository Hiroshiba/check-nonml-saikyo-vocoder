# 位相原点校正の計測前研究とv0監査（2026-10-20）

source v0は実行前監査を通過しておらず、修正中です。v1は未完成、科学実行は0です。ここでは紙上の参照式、将来の表示案、修正版を受け入れるための監査記録を保存しています。ベース手法はPMLを維持します。

## 局所得点の参照と参考音声の表示案

- [局所得点の紙上導出](phase-origin-local-score-reference-20261020.md)と[独立レビュー](phase-origin-local-score-reference-independent-review-20261020.md)：局所の−1/2 nats/recordは理想モデルの近似参照で、合否閾値ではありません。
- [人工入力の参考音声表示契約](phase-origin-reference-audio-presentation-contract-20261020.md)と[独立レビュー](phase-origin-reference-audio-independent-review-20261020.md)：5本は未生成の人工入力を表示する案です。音質比較や品質改善例として扱いません。レビューに残った修正事項も保持しています。

## v0の監査と修正版の受入れ準備

- [root依存関数のソース確認](phase-root-dependency-source-review-20261020.md)：依存関数の仕様と保証範囲の読取記録です。
- v0の独立監査：[実行境界・保存契約](phase-origin-source-execution-review-v0-20261020.md)、[入力・生成・来歴](phase-origin-source-input-review-v0-20261020.md)、[数理](phase-origin-source-math-review-v0-20261020.md)。部分的な確認通過と、実行を妨げる未解消事項を区別します。
- [ソース受入れ確認票](phase-origin-source-acceptance-checklist-20261020.md)と[保存成果物の読取監査計画](phase-origin-saved-artifact-audit-plan-20261020.md)：後続の確認手順であり、実行許可や結果監査の通過記録ではありません。

10文書とMANIFESTはLibrary `libfile_a30c172039788191ad171ac37a8124fe` v0から原bytesで保存しています。初期設計と未通過監査を残し、修正版の完成・再監査・計算開始の判断と区別します。
