# 特徴量評価の中間状態

2026-10-17 18:39 UTC時点。全指標完了・候補採用の報告ではない。

固定train120とtest120の特徴量計算は10段の終端を保存した。各120予定行。元音声の目標量、振幅特徴amp3075、元の複素特徴rawcomplex4099、PML特徴pml2110は、train/testとも120件すべて成功した。

位相基準をそろえるcanonical_complex4099はtrain115成功・5失敗、test117成功・3失敗。最初のABX処理は「Full train120 required; no reduced calibration fit」で停止した。これは全学習例を必要とする事前条件の適用であり、115件へ減らして較正していない。ABX・readoutの比較値はこの停止時点ではまだない。

失敗の詳細記録を取得しつつ、全件揃っている残り3表現の既定ABX/readoutと2つのPMLとの比較を継続する。固定コーパス・特徴定義・ソース・閾値は変更しない。canonicalの不足を隠した全体完了checkpointは生成しない。

## 保存と再現情報

- 特徴量ソースfreeze SHA-256: `08ab208845490e0e8ed841059e6ec6f91e1b1adfea00495f567678cb5f9c5fed`
- 停止時点のprivate handoff ZIP SHA-256: `2ef992919354bc0d860d1c5db4fbaf1cbf011c6a996d8f2978df8a68efb3495c`
- ZIP内13ファイルのサイズ・SHAを受領側で検証済み。
- train-cloud / test-dot / evaluation-cloudの混在実行設計。ホスト間の数値同一性は未証明。
- 生特徴量・音声・private summaryは本ファイルに含めない。

通常音質79軸の既存結果は変更しない。別環境で実行している境界補間修正版の音質2指標の比較も、この特徴量評価とは別である。
