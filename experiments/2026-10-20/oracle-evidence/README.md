# 予測混合の初回部分runと回収レビュー（2026-10-20）

現baseはPMLを維持します。人工信号の保存データを再解析した初回 evidence run-001 の記録です。自然音声の品質比較・MOSは未測定で、品質改善や新base採用を主張しません。[既存の品質比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html)と[元のoracle共分散研究](../oracle-covariance/README.md)は別の実験です。

## 初回runの結果

[原結果HTML](results/run-001/index.html)とreport13ファイルは受領bytesのまま保存しました。500組中49組が部分完了、451組が未処理。5000積分の内訳は成功392（V2を含む）、未収束96、明示停止2、未試行4510、BMA確定0です。2026-10-20 05:56 UTCの効率判断で早期停止し、27分上限には到達していません。

HTML・README内の「後続未実行」「Git登録・PR・Pages公開は行っていません」は、report作成2026-10-20 06:06 UTC（表示修正06:12 UTC）時点の記録です。今回の保存で原文は更新しません。

## 回収・統合レビューの原文

[文書束の説明](reviews/README-ja.md)は2026-10-20 06:33 UTCの保存時点です。文書内の未実装・未開始・未完了は各執筆時点の記録として保持します。回収runの結果はこのPRに未統合で、回収成功を主張しません。

- [Vの効率診断](reviews/V-efficiency-diagnosis-ja.md)
- [回収契約レビュー](reviews/recovery-contract-review-ja.md)
- [回収求積レビュー](reviews/recovery-quadrature-review-ja.md)
- [回収実行レビュー](reviews/recovery-execution-review-ja.md)
- [統合実行レビュー](reviews/union-v1-execution-review-ja.md)
- [親の静的監査](reviews/run001-parent-static-audit.json)
- [回収契約](reviews/recovery-CONTRACT-ja.md)
- [回収変更記録](reviews/recovery-CHANGES-ja.md)
- [回収経過](reviews/recovery-RECOVERY-ja.md)
- [ソース来歴manifest](reviews/recovery-source-manifest.json)（候補ソース自体は含みません）
- [文書manifest](reviews/DOCUMENT-MANIFEST.json)

## 保存と公開

report ZIP: 249343 bytes、SHA256 `6bc6ec0223b33ea15b067fb68ba00615bf1262449f732fae74ddf3d636afe823`。
docs ZIP: 63950 bytes、SHA256 `462d3cf42ca0c831b40947bd4009fbbce72a96f430984e6f55bda2ce958f0093`。
原results SHA256: `7b819eb2308e1310c636c5ce6f76f3313f25814653d058bc7417978aa2140e3d`。

Pages予定先は `research/oracle-evidence-run-001-2026-10-20/index.html`。registryは初回記録のみを登録し、レビュー原文はGit管理します。未採用実装・生音声・残差は含めません。Draft PRまでで停止し、マージと本番Pages確認は親の確認後です。


## 初代回収unionの保存記録（2026-10-20追記）

[初回run-001](results/run-001/index.html)と[初代回収union](results/recovery-union-001/index.html)を別の実行記録として参照できます。[回収unionの説明](results/recovery-union-001/README-ja.md)は3675成功積分・完全36/500組（W22/A14）を記録し、全25比較の全100平均・CIは未確定です。Bは固定snapshotで外部終了unknown、A/Cは保存終了確認あり。世代2B担当280の全件成功は報告受領・独立監査中、A/C未受領という本文作成時点の記録です。全体完了や品質改善を意味しません。

監査済みLibrary v1のpublic17ファイルをそのまま保存しました。元resultsはmtime=0の可逆gzipで、解凍SHAを確認済み。以前の「回収run未統合」等は初回文書作成時点の経過として保持しています。新しい公開先は `research/oracle-evidence-recovery-union-001-2026-10-20/index.html`。本追記はDraft保存時点で、マージ・Pages反映は未実施です。既存ChromiumのSUID sandbox設定不備によりブラウザー描画は未確認です。


## Gen2全500組の保存記録（2026-10-20追記）

[初回の部分run](results/run-001/index.html) → [世代1回収の36組](results/recovery-union-001/index.html) → [Gen2全500組](results/gen2-complete-001/index.html)を別記録として参照します。[今回の説明](results/gen2-complete-001/README-ja.md)は承認済みLibrary v2の48ファイルを原bytesで保持しています。5000積分・500組・truth各100組が揃い、全25比較の保存平均・pointwise 95% CIと保存平均に基づく記述的順位を表示します。PML維持、自然音声の品質・MOS・採用判断とは別です。

元unionの容量guardによるexit2/unresolved、compact保存の終了0、今回3shardの終了確認、祖先Bの終了unknownを区別します。compactの再構成500組・保存2500差exact・summary原bytes・両receiptと外部wait0は独立監査通過の報告を受領済み。全derived項目の失敗前未保存値との一致を主張しません。rawは可逆gzip一件に保存し、解凍原SHAを確認しました。

公開予定先は `research/oracle-evidence-gen2-complete-2026-10-20/index.html`。この追記の作成時点ではDraft保存までで、レビュー・マージ・配信確認は親の別工程です。ブラウザー描画は未確認。PR77の表記修正は取り込まず、旧report原本・旧数値・PR67・USER_INSTRUCTIONSは変更していません。
