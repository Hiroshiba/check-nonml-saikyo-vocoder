# 来歴・出典・公開上の注意

## 凍結と再現情報

評価基盤の読取開始版はcommit `0ec565920087c3bd094f7b05510485a75bed755a`。今回の実行前契約では、原音NPYと実際の評価PCM、候補・対照ソース、評価関数、実行driver、モデル、実行環境、出力波形、保存payloadのSHA256を区別します。候補生成の実行前凍結記録SHA256は `2049d5dc59748912a1510bcbe568c5a435962ad1d2d5bdcb5306576bf45e6277`。2026年10月17日03:14 UTC頃に生成を開始しました。このhashは凍結記録の識別子であり、全ファイル共通のhashではありません。正確な開始・終了と評価stageの最終ソース対応は実行記録から追記します。

候補実装と再現用私有資源はこのDraftには含みません。hashの公開だけで誰でも全実験を再実行できるとは主張しません。純粋評価driverの公開も、候補encoder/decoderが公開済みであることを意味しません。原音・モデル等の出典と、結果を生んだ版・公開用に整理した版を分けます。

## 音声

[LibriSpeech / OpenSLR 12](https://www.openslr.org/12/)の[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)に従います。Vassil Panayotov、Guoguo Chen、Daniel Povey、Sanjeev Khudanpurのコーパスで、元朗読はLibriVoxのボランティアによる録音です。

音声例は固定録音 `1089-134686-0008` と `1188-133604-0003` の先頭最大2秒を予定します。音声を掲載する段階で、録音ID、開始／終了sample、標本化周波数、処理内容、ファイルSHAを保存します。原音例は抜粋と形式変換、合成例は各方式の解析・再合成／音高変更であることを明記します。配布元による本研究の推奨を意味しません。全長入力・全長合成音・完全payload・別集合の評定個票は公開しません。

## aHMとCOVAREP

上流参照は[COVAREP固定commit](https://github.com/covarep/covarep/tree/5a2be5d6b776f14a0b275c69fde90eb13849e60d)。[ライセンス説明](https://github.com/covarep/covarep/blob/5a2be5d6b776f14a0b275c69fde90eb13849e60d/LICENSE.txt)はファイル別のライセンスを確認するよう求めています。aHM本体・関連補助のLGPL-3.0-or-laterと、VOICEBOX由来補助のGPL-2.0-or-laterが混在するため、依存全体をLGPLのみと記述しません。

- G. Degottex, Y. Stylianou, “Analysis and Synthesis of Speech using an Adaptive Full-band Harmonic Model,” IEEE TASLP 21(10):2085–2095, 2013
- G. Degottex, J. Kane, T. Drugman, T. Raitio, S. Scherer, “COVAREP – A collaborative voice analysis repository for speech technologies,” ICASSP 2014

今回のPython実装はMATLABとの数値同等性を証明したものではありません。Cartesian編集は今回の固定条件で、上流著者の編集実装の完全再現とは呼びません。初期F0には固定LLSM経路を含み、そのソース・依存・入力対応も実行来歴へ記録します。

今回の範囲は結果・説明・短音声です。将来コードを配布する場合は著作権・ライセンス・変更表示・対応ソースなどを別途整理します。コードのライセンスを数値出力・入力由来音声へ機械的に同一適用する判断ではありません。[GNUの出力に関する説明](https://www.gnu.org/licenses/gpl-faq.en.html#WhatCaseIsOutputGPL)も参照し、上流同梱の著作物を出力へ混入させません。

## 評価器

UTMOSv2は[公式実装](https://github.com/sarulab-speech/UTMOSv2/tree/cc2700db57bb83ee13dc31ebe1b868c254e15d09)、SCOREQは[公式配布](https://zenodo.org/records/15739280)、ECAPAは[SpeechBrain公式モデル](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)、ASRは[公式モデル](https://huggingface.co/facebook/wav2vec2-base-960h)を使用します。固定revision・ファイルSHA・前処理・依存版を実行記録に残し、モデル重みを再配布しません。

学習済みモデルは評価器に使用し、候補合成器をML化するものではありません。予測MOSや埋め込み類似度の高得点だけで、人間の自然さ・同一話者感・48 kHz対応の優越を宣言しません。
