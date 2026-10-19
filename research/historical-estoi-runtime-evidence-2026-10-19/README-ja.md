# 旧8方式 eSTOI：測定時バージョンの根拠

2026年10月19日、旧8方式の既保存測定recordを確認し、公開済みeSTOI値 **全960件（120音声 × 8方式、40話者）** と照合した。case/methodのキー集合と元recordのSHA256が全件一致し、値・status・話者・元の測定statusにも不一致はなかった。欠落、余剰、重複は0件。

全960件の extended.intelligibility.estoi に **pystoi 0.4.1** が記録されていた。各件を確認した結果、extended=true、評価seed=0、内部sample rate=10000、内部無音除去閾値=40 dB、status=measured、warnings=[] も共通だった。1件から全件へ推定した結果ではない。

比較対象は公開射影のpitch=0・合成seed=0。元測定条件はuneditedで、共通契約は「8方式共通長の16 kHz入力、位置合わせ・ゲイン正規化なし」。全件が参照する契約SHA256は次のとおり。

6d7ec5bd484e8457204b041bc85cafcfaf9e9c1f943ac68f571bc8594da0ba1b

## 対象と証拠表

対象方式：HNM、WORLD Harvest、FACodec、HiFi-Glot、GOLF、SiFiGAN、LLSM2、MagPhase。

[既存公開データ](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/research/pml-package-evaluation-2026-10-16/quality-raw.json.gz)のSHA256：6f9404e925a21f50d8e6e947c041679df88e93ba147a1d4434a4f4e9f6695c7f

照合に使った既存比較用射影のSHA256：07bddea839629396026fa33808dd7002896dbabadbd216d99b75aaefd1bf8c7f

同梱 historical-estoi-runtime-evidence.json は、公開済みcase/method/value/status/source ID/raw SHAを全960行保持する。各recordで確認した共通バージョン・条件・契約SHA・照合結果は先頭にまとめた。source IDは照合先の公開行からそのまま保持し、元recordとの対応はraw SHAで確かめた。

証拠表のSHA256：8e1e02ef74f905fc70126edd87ad34d912c69a689db4d985a44b8f2bda661f31

## この確認の限界

旧8方式の測定時バージョンを示す証拠不足は解消した。ただし、パッケージ実体のbyte同一性は未確認。現在runとの互換性は未評価で、現在runとの比較に必要な科学的条件の照合は未完了である。今回の結果だけでは比較全体の妥当性は確定しない。

要約とは別に元recordを読み直し、全960件の照合範囲を再確認した。作業は既保存記録の読取・ハッシュ照合・証拠の整理のみで、新しい音声合成・指標計測は行っていない。
