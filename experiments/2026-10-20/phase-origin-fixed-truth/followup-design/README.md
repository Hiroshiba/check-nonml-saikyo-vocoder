# 位相原点校正の理論・参照資料と監査記録（2026-10-20）

[予測密度の混合と波形平均の違い](mixture-synthesis-distinction-20261020/README.md)を紙上補足として保存しました。半周期ずれた二候補の等重み平均で最小周期が半分になる仮想的な反例です。現在の推定分布・知覚上の音高・音質の測定とは区別し、二乗誤差による点予測と対数得点による密度予測、共通位相と区間別位相、完全な予測標本に必要な条件付き雑音を分けます。独立レビュー後の明確化・再確認済みで、合成方針は未採用です。

[有声確率を不完全な参照で評価する条件](../../voicing-reference-uncertainty/README.md)を別グループに保存しました。参照誤りの識別限界、独立レビュー後の修正、MOCHAの標本数差の報告を扱います。長さ差を同期ずれと同一視せず、以前の文書束とPMLを維持します。

## 数値積分案とMOCHAの時刻調査を追補し、採用・集計は保留

[数値設計とMOCHAの時刻情報の文書束](numerics-and-mocha-timing-20261020/README.md)に、7研究・レビュー文書とREADME・MANIFESTの計9ファイルを原bytesで保存しました。Library `libfile_503bc72fa93881919d12c3349ab0100e` v0の文書だけを収録しています。前の文書束は変更していません。

今回のREADMEの説明に対応する原文は、次のリンクから参照できます。

- 数値積分：[安定計算と誤差評価の設計](numerics-and-mocha-timing-20261020/phase-origin-circle-integral-numerical-design-20261020.md)、[指摘と修正後の独立確認](numerics-and-mocha-timing-20261020/phase-origin-circle-integral-numerical-independent-review-20261020.md)、[検証付き積分APIの静的監査](numerics-and-mocha-timing-20261020/phase-origin-verified-integration-api-review-20261020.md)。
- 期待得点：[局所線形モデルの参照式](numerics-and-mocha-timing-20261020/phase-origin-local-predictive-score-reference-20261020.md)と[独立レビュー](numerics-and-mocha-timing-20261020/phase-origin-local-predictive-score-independent-review-20261020.md)。
- MOCHA：[音声・EGGの時刻と長さの来歴](numerics-and-mocha-timing-20261020/mocha-fsew0-timing-provenance-followup-20261020.md)と[独立レビュー](numerics-and-mocha-timing-20261020/mocha-fsew0-timing-independent-review-20261020.md)。

数値積分案は2点の指摘を修正し、独立確認を受けた紙上設計です。具体的な方式・閾値・実装・実験は未採用です。局所線形Gaussianモデルの3つの期待得点式も独立レビュー済みですが、properな円周事前分布を使う有限標本や実500には適用しません。python-flint 0.9.0／FLINT 3.6.0のAPI監査は静的資料の確認だけです。Python側の呼出し口はC側の停止状態を公開しないため、指定した許容誤差ではなく返却区間の幅を判定する必要があります。実環境への導入や動作確認は行っていません。

MOCHAは別Cloudが公式fsew0_v1.1 archiveのheaderだけを監査し、音声wavと喉頭信号larの460対・920headerの容量整合と、全対のsample_count不一致を報告しました。原inventoryはLibraryのHTTP403で未転送であり、保存データの独立照合は未完了です。元論文には逆フィルタ残差の相関を使った同期の説明がありますが、現配布の各時刻ずれ・端点・長さ差の原因は不明です。波形解析・補正やコーパス採用は行っていません。前の文書の「コーパス未取得」は、当時の調査記録として保持します。

実500は全計算workerが終了0、外側が終了2、167・167・166組完了との報告のままです。過去の全子終了unknown、`immutable=false`、通常packing拒否を保持し、正式集計も担当ごとの暫定集計も保留します。拒否された科学成果・MOCHA原データの転送再試行や別経路転送は行っていません。PMLを維持します。

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
