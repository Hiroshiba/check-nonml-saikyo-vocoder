# B保存log prior追加版：入力監査と反事実計画への追記案

2026-10-20。対象：`/workspace/shared/pitch-bf-selected-input-review-v1-20261020`。

## 0. 結論

追加版の内部整合監査で不一致は見つからなかった。

- 旧Aの11ファイルは、前版の実ファイルとbyte単位で全一致。
- Bの6180候補IDと309frameは、Aの固定2周波数×K1..10と完全対応。
- B log_prior6180値とlog_prior_H0の309値はすべて有限。value/hex/binary64 bitsの3者が全一致。
- Bの有限log priorをそのまま凍結すれば、全309frameで両周波数群の条件付き比較を数学的に定義できる。Aの通常確率priorにあった全zero群の制約を、このB条件に引き継がない。
- ただしBは旧A logBFを入力にした既存log-state軌道である。A priorの復元でも、新exact BFで過去から再追跡した軌道でもない。

元NPZ/source本体は未同梱。producerによる元bit照合・source629件の確認と、本監査による納品ファイル内の整合確認を区別する。

今回、BF/r/exp/oddsの計算、候補コードの実行・import、tests、再追跡、Git変更は行っていない。標準ライブラリでファイルbytes、JSON字段、ID、有限性、float表現、記録されたhashの一致だけを監査した。packageは変更せず、本書だけを外部の共有作業ディレクトリへ保存した。

## 1. 転送とファイル完全性

親によるZIP確認：1213332 bytes、SHA256
`2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d`。
本担当は展開済み内容を監査した。

v1は旧A11ファイル＋B追加6ファイルの計17。B-extraction-manifestが列挙する自己以外16ファイルのbytes/SHA256を実ファイルから照合し全一致。旧11ファイルは前版ディレクトリと直接bytes比較し、すべて一致した。B-provenance内のA_files_sha256_unchangedとも一致。

主な追加ファイル：

- B-log-prior-selected.jsonl：1042821 bytes、SHA256 `e7d457488c5f1562c6d42607f3cae401a44f22479e84d5dc95bcb8762961b861`。
- B-frames.json：236595 bytes、SHA256 `c3dc99e390fa52d36fb84f71b875a9c867f8e20d62c3da3e539a28b587f16e8a`。
- B-provenance.json：237279 bytes、SHA256 `ba610a33ea5282f4e90595f596964eecee907a2e4fbae629b5b547d732ee2f66`。
- B-SOURCE_MANIFEST.json：89587 bytes、SHA256 `4c73761a5ea91dc21bc791a792b8507c853f8582b2841afa2c9a576eb57b6377`。

旧extraction-manifestはAの記録のまま保持されており、Bを列挙しないことは欠落ではない。

## 2. 候補・frame・表現

Bの候補キーは(condition,frame_id,f_index,K)。6180件で重複なし、Aの全候補キー集合と一致する。したがってU-U/E-U/E-E各103frame、各frameのindex48/148×K1..10に欠落・余分なし。

Bの各レコードはcondition/frame_id/f_index/K/log_priorだけを持つ。F0Hz・fixed_rowはBに重複保存されていないが、AとのID joinで固定軸へ対応する。順番だけでjoinしない。

B-framesは309件、(condition,frame_id)の重複・欠落なし。Aとのtime_seconds、support_class、A_json/A_npz参照が一致。全309件のobservation_statusはvalid、metadata_matchはtrueである。後者はproducerの元記録照合結果でもあり、consumerが未添付の元B JSONを直接読んだことにはならない。

6489個のlog値について、すべてtag=finiteで、十進valueをbinary64へ読んだbits、hexを読んだbits、bits_beが一致した。negative_infinity/positive_infinity/NaNの実レコードは0。候補log_prior6180件とH0の309件に欠落なし。

これはbinary64表現の整合であって、元実数精度・推論精度の保証ではない。log値をexpして通常確率へ戻す操作は行っていない。有限のlog値0が存在する場合も通常確率zeroではないため、Aの保存zero監査をlog値のzero判定へ流用しない。

## 3. source・pins・原本参照

B-provenanceのsourcesは1245項目。各B frameのB_npz/B_json/B_receipt、A_npz/A_jsonが表に存在し、conditionとframe番号に整合する。A側source-referencesと共通する619項目はbytes/SHAの記録が一致。

B-SOURCE_MANIFESTには629のSHA pinがある。そのうち622はB-provenance.sourcesにもあり、hashが一致。残り7はB-provenance側にはないが、次の同梱A記録へ照合できる。

- model.py、measurements.py、旧Aの3receipt、旧A result.jsonの6項目：A source-referencesと一致。
- storage.pyの1項目：A SOURCE_MANIFESTのfrozen_filesと一致。

従って629 pinについて同梱metadataとの整合は確認できた。ただし629原ファイルをconsumerが読み取ってhashしたわけではない。

Bの主なsource pin：

- log_filter.py：`f73219b6f195d23d2ea671039a01a7a21e5a925dfa3af8252f4cf84175bb1d67`
- run.py：`36e383c78c0fa44cc34159b378a4f7235c76998b2bc796dc723b2209d594bcec`
- EXECUTION-CONTRACT-ja.md：`5e83e47b1460dcb28a9e531027b84a12a0c99cad0e4df4093abfe93fb9cdda80`

B-provenanceのsource_evidenceは、run.pyの64–83行が同condition/frameのA NPZ logBFを読みstate.updateへ渡し、100–101行で返されたpriorをlog_priorへ保存する、と報告する。これはproducerのsource読取証拠であり、本bundleにはrun.py本文がないため本担当による行単位再検証とはしない。

元receipt/NPZ/JSON/sourceのpathはproducer側来歴。自動取得、candidate import、実行はしていない。producerの原bit一致報告と今回の納品値内部一致は別段階の保証である。

## 4. B priorの意味と正規化の限界

既存log-state契約と今回のsource_evidenceに基づき、B log_priorは旧B軌道の当該観測更新前に保存されたH1の(f,K) joint予測log質量として扱う。static初期prior、観測更新後log_joint、F0/K marginal、H1内だけの条件付き分布とは区別する。

対応するH0予測log質量はB-frames.log_prior_H0。全grid461×10のlog_priorとH0を合わせる正規化の契約があっても、このbundleは20候補subsetだけなので全状態の正規化を独立に確認できない。subsetを再正規化済みとみなさない。

B priorはlog(A prediction_prior)ではない。過去に同じ保存A logBFを使っていても、通常確率Aとlog状態Bは別の数値状態履歴である。旧Aのzeroの原因をBの有限値だけから各演算へ一意に帰属させない。

今回Bにlog_prior_H0が追加されたことは、exact H0/VUVを計算するための全候補exact BFが揃ったことを意味しない。新しいH0正規化は対象外のまま。

## 5. 既存反事実計画への追記案

既存計画・A監査を消さず、「旧B log prior固定」の独立した読出し条件として次を追記する。本書では提案だけを記し、計画本体の置換や数値適用はしない。

### 5.1 入力のjoinと名称

同一(condition,frame_id,f_index,K)で、

- A selected.jsonlから元cod、J/fit、保存ℓ_S。
- B-log-prior-selected.jsonlから保存b=log_prior。

を結合する。BのrやBFを新しく生成したと呼ばない。Aの初期prior、Aのprediction_prior、Bのlog_priorを途中で混ぜない。

条件名は「旧B log-state予測prior固定・固定20セルBF置換」。Bも旧Laplace観測値に依存した過去軌道なので、「exact tracker」「exact filtered posterior」と呼ばない。

### 5.2 計算可能な量の紙上定義

将来、独立に検証されたexact ℓ_Eが利用可能となった場合、bをそのままlog重みとし

    A_a^S = LSE_k(b_ak + ℓ_S,ak),
    A_a^E = LSE_k(b_ak + ℓ_E,ak)

を定義する。pair log oddsはA_1−A_2。B priorを一度expしたり、通常確率へ丸めてからlogを取り直す必要はない。

元計画の周辺化補正・K条件付き分布の恒等式は、旧重みをBのb+ℓ_Sから定義すればそのまま適用できる。ただしA条件の旧重みとは別なので、A/B間の周辺化補正の差はBF差だけでなく履歴prior重みの違いを含む。

本節は式の適用範囲を示すのみであり、LSE/exp/BF/oddsは今回数値評価していない。

### 5.3 Aの保存zeroとの違い

Bの選択log priorは全6180セルで有限なので、全309frameで両周波数のK混合を数学的に定義できる。A条件で205frameが片側全zeroだった制約はBにはない。

これはBに替えればexact BFが候補を救済する、という結果ではない。旧Aのzeroを復元しているのではなく、別の保存prior条件で同じ観測BFを比較する。Bの有限log値をexpしてunderflowさせ、そのzeroを再び構造的支持として扱わない。

数値精度、同じrにおけるLaplace再現、参照法の検証、近似差と再現差の分離は引き続き必要。finiteというだけで計算後の順位や補正の大きさは分からない。

### 5.4 保持する非主張

- 全grid exact BF、global MAP、P(f*|H1)、無条件F0質量は計算できない。
- H0/VUVのexact再正規化もできない。
- 旧B priorを固定した比較は、exact BFを全時刻に適用してprior/memoryを更新した軌道ではない。
- A/B prior条件の比較を、同じprior下の純粋なLaplace誤差比較と呼ばない。
- 音質、F0精度、改善・採用判断へ拡張しない。

## 6. 完了点と証拠の区別

確認したもの：展開ファイル内部hash、A11ファイル不変、BのID/時刻/support/A参照対応、6489log値のfinite/bit内部一致、source/pin metadataの矛盾なし。

producer報告に依存するもの：元NPZとのbit一致、元receiptの照合、実source629ファイルのhash照合、BがA保存logBFを読んだ実行来歴の本文行確認。

未実施：BF/r/exp/odds、推論・遷移再実行、candidate実行/import/tests、全状態正規化、品質評価。

本入力監査を完了とし、追加計算は開始しない。
