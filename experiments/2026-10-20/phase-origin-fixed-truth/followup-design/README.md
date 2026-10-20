# 位相原点校正の計測前研究とv0監査（2026-10-20）

## 予測理論と参照資料を保存し、実500の集計保留を維持

[理論・一次資料・失敗原因調査の文書束](predictive-theory-and-epoch-sources-20261020/README.md)をLibrary `libfile_ecf58c823b2c8191b8557cd4995b1c7d` v0から原bytesで保存しました。10文書とREADME・MANIFESTの計12ファイルです。原文中のファイル名は、次のリンクから参照できます。

- 理論：[連続位相の予測積分](predictive-theory-and-epoch-sources-20261020/phase-origin-white-predictive-integral-reference-20261020.md)と[独立レビュー](predictive-theory-and-epoch-sources-20261020/phase-origin-white-predictive-integral-independent-review-20261020.md)、[固定φの期待得点の対称性証明](predictive-theory-and-epoch-sources-20261020/phase-origin-white-equivariance-risk-reference-20261020.md)と[独立レビュー](predictive-theory-and-epoch-sources-20261020/phase-origin-white-equivariance-independent-review-20261020.md)、[予測理論の一次資料](predictive-theory-and-epoch-sources-20261020/phase-predictive-primary-precedents-20261020.md)。理想W（白色雑音）では、連続位相混合予測の固定φでの反復期待logscoreが理想global OLS（最小二乗法）より厳密に高いという紙上論証です。予測積分の文書で保留した対称性の論証を、後続の別紙とレビューが補います。各学習条件・各実現値、現行数値500組、音質、W以外への改善保証には使いません。
- コーパス：[MOCHA-TIMIT・CMU ARCTIC・Keeleの一次資料調査](predictive-theory-and-epoch-sources-20261020/epoch-reference-corpus-source-review-20261020.md)と[独立レビュー](predictive-theory-and-epoch-sources-20261020/epoch-reference-corpus-independent-review-20261020.md)。当時はコーパス実体を未取得・未検品でした。EGGやpitchmarkは完全なGCI真値ではありません。別Cloudが開始したMOCHA実体header調査と区別し、原文の未取得状態を保持します。
- 失敗原因と保存範囲：[proc childrenの失敗分析](predictive-theory-and-epoch-sources-20261020/phase-origin-proc-children-failure-analysis-20261020.md)、[将来の子終了監視案](predictive-theory-and-epoch-sources-20261020/phase-origin-child-wait-portability-design-20261020.md)、[失敗時の写しの受入れ限界](predictive-theory-and-epoch-sources-20261020/phase-origin-failed-snapshot-acceptance-boundary-20261020.md)。原因は未確定で、将来案は過去の終了確認を補完しません。

実500は3hostの計算workerが実終了0、外側が終了2、167・167・166組完了との報告です。各hostの保存値の読取監査では欠落・不一致なしと報告されていますが、親によるrawの独立検証は未完了です。`/proc/self/task/{PID}/children` の読取失敗、過去の全子終了unknown、`immutable=false`、通常packing拒否を保持します。写しは各hostに保全済みですが、正規Library uploadの `tools/list` はHTTP403で拒否されています。親判断により正式集計もhost別暫定集計も行いません。この文書保存では実験データに触れず、転送再試行・別経路転送・権限操作は行っていません。PMLを維持し、以下の過去記録を各執筆時点の状態として読みます。

最新の[v2固定契約・v1/v2監査・REAPER調査](frozen-contract-and-reaper-20261020/README.md)を別の束に保存しました。v2の静的レビュー通過と3ownerへの開始指示を記録し、3担当とも外側の処理は終了していますが、すべての子プロセスの終了確認が不完全なため、正式な集計には進んでいません。各担当の計算プロセスは終了コード0、外側の処理は終了コード2でした。完了記録はowner0が167組、owner1が167組、owner2が166組で、計500組すべてにあると報告されています。ただし、保存物の全体監査と科学結果の採用は未完了です。

終了処理で `/proc/self/task/{PID}/children` を読めず、すべての子プロセスの終了を確認できませんでした。通常の梱包は、必要な終了確認の条件を満たさず拒否されています。原成果は変更せず、取得時点の写しとして別途保全しています。現在のPID不在を過去の終了確認の証拠とは扱わず、元の失敗状態を保持します。



この束の保存時点では、source v0は監査未通過で修正中、v1は未完成、科学実行は0でした。ここでは紙上の参照式、将来の表示案、修正版を受け入れるための監査記録を保存しています。ベース手法はPMLを維持します。

## 局所得点の参照と参考音声の表示案

- [局所得点の紙上導出](phase-origin-local-score-reference-20261020.md)と[独立レビュー](phase-origin-local-score-reference-independent-review-20261020.md)：−1/2 nats/recordはW（白色雑音）の理想モデルでの局所近似参照で、合否閾値ではありません。
- [人工入力の参考音声表示契約](phase-origin-reference-audio-presentation-contract-20261020.md)と[独立レビュー](phase-origin-reference-audio-independent-review-20261020.md)：5本は未生成の人工入力を表示する案です。音質比較や品質改善例として扱いません。独立レビューの指摘と契約への反映を記録しています。

## v0の監査と修正版の受入れ準備

- [root依存関数のソース確認](phase-root-dependency-source-review-20261020.md)：依存関数の仕様と保証範囲の読取記録です。
- v0の独立監査：[実行境界・保存契約](phase-origin-source-execution-review-v0-20261020.md)、[入力・生成・来歴](phase-origin-source-input-review-v0-20261020.md)、[数理](phase-origin-source-math-review-v0-20261020.md)。部分的な確認通過と、実行を妨げる未解消事項を区別します。
- [ソース受入れ確認票](phase-origin-source-acceptance-checklist-20261020.md)と[保存成果物の読取監査計画](phase-origin-saved-artifact-audit-plan-20261020.md)：後続の確認手順であり、実行許可や結果監査の通過記録ではありません。

10文書とMANIFESTはLibrary `libfile_a30c172039788191ad171ac37a8124fe` v0から原bytesで保存しています。初期設計と未通過監査を残し、修正版の完成・再監査・計算開始の判断と区別します。
