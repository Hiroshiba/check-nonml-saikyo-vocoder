# 初代回収unionの報告案（2026-10-20）

現baseはPMLを維持します。人工信号500組の保存値による記述的再解析です。自然音声の品質・MOSは未測定。成功部分集合は選択的であり、全体改善・品質改善・VUV校正・モデル採用を示しません。

[日本語HTML](index.html) / [既存自然120録音比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html) / [標準8方式比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/all-method-final-2026-10-15/index.html) / [初回report](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/oracle-evidence-run-001-2026-10-20/index.html)

## 結果と解釈

5000枠の成功3675、未収束759、時間切れ6、未試行560。完全36組（W22/A14/V0/S0/J0）、部分464組。各truthの母集団は100です。

全25比較で、母集団100組の平均差と95%区間はnull（未確定）です。W/Aの成功部分集合の10比較だけに保存済み10,000回bootstrapがあります。残る15比較はno_successful_pairsで、区間を作りません。区間は各比較のpointwise 95% percentile（NumPy linear）で、多重比較調整区間や全母集団の保証ではありません。

差はBMA − 旧plug-inモデル、単位nats/record。CSVは保存値を転記し、nullを明示します。新しい平均・CI・求積・bootstrapは計算していません。表示用HTMLのみ有効9桁へ丸めます。

## 実行と次段階

A（ID 0–32）とC（66–99）は保存された外部終了確認あり。B（33–65）は固定immutable snapshotの数値を使用し、外部終了はunknownです。Bの終了不明は来歴上の未確認で、759未収束・6時間切れ・560未試行という数値上の不足とは別理由です。

union外部開始07:01:14.837472、終了07:01:21.125719 UTC、6.288264975999482秒、exit2 provisional_partial。例外・強制停止なし。数値の保証付き誤差ではありません。

次世代gen2は3675成功を再利用し、残1325だけを対象に、同じmodel/prior/gateを保って二次上界で効率化する計測を依頼中です。その後B担当280の全件成功報告を受領し独立監査中ですが、A/Cは未受領で、全体の成功・収束・品質改善は未確認です。

## 対象と評価量

既使用の500 train/test pair（W/A/V/S/Jの固定truth各100組、各record N=4096）を、保存された既知平均除去済みraw residualとgeometryのまま再解析する。新しいデータ生成、平均・位相の再推定、残差の再正規化は行わない。

5モデルのpriorは各1/5。shape priorはAの[-0.8,0.8]上の一様分布、Vの半径1.5円板上の面積一様分布、S/Jのα∈[0,1)上の一様分布で固定する。共通scale測度はdE/Eとし、train/testはscaleとshapeを共有するが、record間の潜在変数とAR初期状態は独立とする。

train-onlyの方向evidenceからモデル重みを求め、train posteriorがproperである場合のraw posterior predictiveとBMAを、既存の5種類のplug-in test scoreに対して比較する。単位はnats/record。dE/Eによるraw prior predictive自体をproperな確率密度とは呼ばない。必要な候補が未達の場合にその候補だけを除外して重みを再正規化することはしない。

1 pairには5モデル×train/jointの10積分が必要である。3675成功slotは3675組の予測完成ではない。数値計算の成功はデータやモデル条件に依存し得るため、成功subsetの平均・CIは計算が完了した部分集合の条件付き記述である。bootstrapはこの選択性を解消せず、pointwise CIは25比較の同時保証でもない。

## 世代2の限定変更：全体結果の確認は未完

以下は2026-10-20に提供された保存契約・静的数理レビューの方法説明であり、この報告作成時に実装を実行・再検証したものではない。科学モデル、prior、支持、integrand、raw scoreの定義は変更しない。変更対象はV求積のcell mass上界である。

従来の接線最大密度×sector面積の上界に加え、anchor cから距離δ以内での位相確率比と共分散の下界を利用する。保存geometryのFmax=max||z_l||を用いると、実数演算ではCov_b≽exp(−2δFmax)Cov_cが成り立つ。この局所強凹性からlog kernelの二次上界を作り、sectorを含む回転rectangle上でGaussian関数を積分したmass上界と従来上界の小さい方を使う。境界でもgradientを0と仮定しない。

新しいkernel評価点は追加せず、既存anchor評価のHessianを利用する。不安定な固有値・区間確率・相殺が検出された場合は従来の接線上界へ戻す。hybrid求積は導入しない。全支持のGL8/16/32、angular別則、Cartesian24/48と必要時64/96の照合を維持する。

数値gateも維持する。最後の2段階差は各2e-7以下、別則・別座標との差は5e-7以下、small mass比・active riskは1e-8以下とし、有限性・整合性も要求する。積分当たり200万評価点、4096 cellsの上限は増やさない。これらは1e-6 natsを目標とした運用上の収束診断であり、真誤差の証明ではない。

## 再利用と数値上の留保

成功済み3675 slotは再計算せず、原値・診断・source/gate来歴を保持し、残る1325 slotだけを対象とする。V成功127件の内訳は初期版の2件と、その後の版の125件である。それぞれ元のgateで検証して再利用し、新しい二次上界で再評価・再合格したとは扱わない。

Gaussian rectangle上界は実数演算での真積分の上界であって、任意のGL離散近似値の上界まで自動的に保証するものではない。既存のcell massとの整合gateは残し、不一致を成功へ変更しない。

固有値の余裕、CDF差の安定化、上向きpaddingは保守性を狙った数値処理だが、丸め誤差全体を包絡する区間演算ではない。従来上界を含めてcertified bound/errorとは呼ばない。本稿時点では世代2の結果を評価しておらず、cell数削減、予算内完了、精度到達、予測性能改善のいずれも未確認である。

## 終了来歴と解釈の境界

世代1はA/Cの終了成果物とBの固定immutable snapshotを使用する。Bの数値を欠落扱いせず、祖先実行の外部終了はunknownのまま保持する。世代2自身のworker終了・returncodeと祖先Bの終了未確認は別の事実である。世代2が正常終了したとしても、祖先Bの終了証明や全履歴の全面的な終了確認にはならない。

本解析は既使用データによる事後設計の記述的再解析であり、新しい確認実験ではない。音質指標、自然音声評価、聴取評価、autoMOSは実施していない。生理学的原因の確率校正、自然音声への一般化、音質向上、ボコーダ方式の採用を示さない。現baseはPML、PR67はDraft維持を前提とし、本報告を採用判断とはしない。

世代2の方法を固定したsource manifest SHA256（提供された識別子）：2278c3e1c03e651e21ef68ab2f6b4daa7974e044d9654bcb8c598f7332a319c1。世代2のsourceや測定結果は今回の入力ZIPに含まれず、ここでは照合・実行していない。求積、派生量、bootstrapの再実行による再検算も行っていない。

## 原本と復元

同梱original内は、resultsの可逆gzipを除き入力ZIPの原bytesです。元results 13220296 bytes、SHA256 `e1b9122441e5d62f73ee0ad3dda45450517b5731851c8bda144906723b47a269`。元receipt、input index、外部終了証拠、ledger、初回結果も保持しました。A/Cの終了確認はresultsのprovenance.terminal_confirmationsに保存された証拠の引用です。個別terminal-A/Cファイルや各shardの外部終了原本自体は入力ZIPに含まれず、取得・再観測していません。

merged-slots.json（12503398 bytes、SHA256 `1486fb61b4664aaa10d69b4c7b1780e649356882fe8db5e4953a6d83c66556f4`）は重複配置しません。空の2ログも省略します。全原本は次で復元できます。

- Library `libfile_3c413dce2c448191ab381a692979bbfd` version 0
- file `file_0000000072cc81fd8df5c3547abcd8df`
- ZIP `oracle-union-run-001-20261020.zip`、1637126 bytes
- SHA256 `5108cec78a458cb9b087768a99812c3bd6342af24e3265e63ac1e0377f76a44d`
- source manifest SHA `5ba5e987786d8e31eacb5b549e42b90ebb921681376755e5027517e5c8d54ded`
- input index SHA `cca181945f8e08d51840ac5b6b7c477f59a6053d2023f81179a975f3d61cd9dd`

original/input-artifact-manifest.jsonは入力ZIPのmanifest原本で、省略したファイルも列挙します。このbundleの実在一覧はルートartifact-manifest.jsonです。親の独立監査通過は依頼時の報告を引用し、今回再計算・float監査を行ったとは主張しません。

## 公開案と未確認

新パス案：`research/oracle-evidence-recovery-union-001-2026-10-20/index.html`。現公開の初回reportを上書きしません。本案から旧reportへリンク済みで、将来公開する際は初回reportの案内に新パスへのリンクを追加すれば相互に移動できます。旧reportは今回変更していません。

統合resultsは圧縮原本 results.json.gz として配布します。gzip mtime=0、level=9。解凍後13220296 bytes、SHA256 e1b9122441e5d62f73ee0ad3dda45450517b5731851c8bda144906723b47a269 に完全一致します。圧縮は配布処理のみで科学計算ではありません。

既存Pages builderはnavigation-onlyの.json.gzを許可し、圧縮後サイズは10 MiB未満です。builder変更は不要です。public/artifact-manifest.jsonを公開用一覧とします。元の計算用HTMLはリンク先が未圧縮results.jsonのままなので、原bytesでpreserved/に保管し、公開対象から除外します。元Library v0と元resultsは保持しています。

Git書込み・PR・公開なし。ブラウザーによる描画・画面確認は未実施。Bの外部終了はunknown、Gen2 Bは担当280全件成功の報告を受領し独立監査中、A/Cは未受領です。未確認を成功と補完していません。未採用ソース、個人音声、内部メモ・coordination文は追加していません。


## 次段階の報告受領状況

世代2の更新（2026-10-20）：Gen2 Bの担当280は全件成功との報告を受領し、独立artifact監査中です。A/Cは結果未受領です。これは報告受領時点の事実であり、Gen2全体完了・独立監査合格・品質改善を示しません。


## 描画確認の結果

既存Chromiumをsandbox有効で起動したが、SUID sandbox helperの設定不備で起動失敗。追加install・権限変更・sandbox無効化は行わず停止。描画・画面確認とスクリーンショットは未実施。
