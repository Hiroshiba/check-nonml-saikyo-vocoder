# 音素時刻と PPG：局所音響観測を補う評価の設計

調査記録：2026-10-19（日本時間）。**PPG と自動音素アラインメントは未実測。** 以下は一次資料と既存保存結果に基づく評価案であり、新指標による採点結果ではない。

## なぜ全文 ASR だけでは足りないか

既存の対象は英語 LibriSpeech 5録音・4話者、PML / RAW_SHAPE / RAW_FULL × native / ±3半音 ×2 seedの90条件。sample3（`121-121726-0012`）では局所高域 power が変わっても、保存 ASR の WER は全方式・全音高・全 seed で20%だった。認識内容が同じでも先行成分や子音の時間形状が同じとは限らない。

公式全文を対応させられる2録音のみ36/90条件で ASR を測定し、残54条件は切出し正解転記が未整備。原音2録音の CER / WER はともに0だった。切出しに全文を強制して欠測を埋めない。保存された文字列や logit のフレーム数から、保存されていない posterior 配列を復元することもできない。

## 三つの観測を混ぜない

|役割|残す量|何を保証しないか|
|---|---|---|
|固定区間の短窓音響観測|帯域 power、弱い成分と強い立上がりの交差時刻|音素ラベルや人間の知覚閾値|
|転記非強制の PPG|同時刻の音素クラス分布、silence、対象子音群の推移|物理的な雑音量、数 ms単位の真の発音開始|
|固定転記の forced alignment|音素の開始・終了・持続時間の差|転記にない挿入音の不存在、真の境界誤差|

PPG は音声単位上の時変分布であり、発音距離や pitch と発音の分離に使われている。ただし原論文の評価は、今回の弱い先行雑音に対する検出性能を確かめたものではない。[Churchwell・Morrison・Pardo, 2024](https://arxiv.org/html/2402.17735v1)

## PPG の時間精度と距離の注意

調査した公式実装の固定版 `f61e331543fabd6bfbd249441ec75adb54a0bfe2` は、既定 Mel 入力が16 kHz、10 ms hop、64 ms窓、40クラス（silence を含む）で、非因果 Transformer を使う。10 ms刻みの出力でも、10 msだけの独立した音響証拠を見ているわけではない。全文を推論してから固定時刻を読み、条件ごとに短く切って文脈を変えない。[公式設定](https://github.com/interactiveaudiolab/ppgs/blob/f61e331543fabd6bfbd249441ec75adb54a0bfe2/ppgs/config/defaults.py)、[モデル](https://github.com/interactiveaudiolab/ppgs/blob/f61e331543fabd6bfbd249441ec75adb54a0bfe2/ppgs/model/transformer.py)

公式の窓配置に従う名目中心は0.005＋0.010j秒となる。この規約では sample3 の early [2.080,2.094)秒に入るのは2.085秒の1フレームで、その64 ms窓は約[2.053,2.117)秒と strong 区間にも重なる。これは設定からの算術であり、まだ得られていない PPG の実測値ではない。

silence は万能の雑音クラスではない。閉鎖ラベルを破裂音へ統合する mapping もあるため、クラスが変わった時刻を破裂の物理的開始と同一視しない。また公式距離関数は成分ごとの平方根を取って和を作り、通常の Jensen–Shannon divergence と同じ式ではない。距離名だけで定義を代用せず、生分布と式を保存する。[音素集合](https://github.com/interactiveaudiolab/ppgs/blob/f61e331543fabd6bfbd249441ec75adb54a0bfe2/ppgs/phonemes.py)、[距離実装](https://github.com/interactiveaudiolab/ppgs/blob/f61e331543fabd6bfbd249441ec75adb54a0bfe2/ppgs/core.py)

認識器が雑音に頑健なことは内容評価では利点だが、先行雑音を見逃す可能性でもある。逆に ±3 半音や声質の変化に反応しても、それだけで発音誤りとはいえない。本対象での感度・不変性は未確認。

公式の [PPG 配布モデル](https://huggingface.co/CameronChurchwell/ppgs/tree/407a830baa843ec7f5dbc1cbcc7a819d721c1d4f) は公開で、当該 revision のカードは MIT を表示している。依存関係を含めた実行条件の固定は検討中で、モデルの導入・推論・PPG 実測はまだ行っていない。表示ライセンスの確認と、実行全体の再現性確認を分ける。

## 自動境界は補助として使う

MFA では同じ転記・辞書・音素列を原音と出力に与え、開始差、終了差、持続時間差を別々に残せる。ただし転記にない先行音は silence や隣の音素へ吸収され得る。強制後のラベルが合うだけでは内容保持を証明できない。[MFA 原論文（McAuliffe ほか, 2017）](https://www.isca-archive.org/interspeech_2017/mcauliffe17_interspeech.pdf)

標準刻みは10 ms、fine-tune は1 ms刻みでも特徴窓は25 msである。**刻みを細かくしても同じ精度が得られるとは限らない。** 原論文の歴史的条件では音素境界差の中央値が約11 msだったが、その値を現モデルや今回のボコーダー出力の誤差幅へ移せない。[公式 fine-tune の注意](https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/implementations/fine_tune.html)

既存 ASR の文字 CTC は音素 PPG ではなく、blank はラベルを出さない経路記号で、物理的 silence ではない。blank の割合や非 blank ピーク幅を、そのまま無音率や音素持続時間に使わない。[TorchAudio 公式 CTC 解説](https://docs.pytorch.org/audio/2.7.0/tutorials/ctc_forced_alignment_api_tutorial.html)

## 次の測定案と守る比較条件

1. 主観測は、原音で固定した先行・強部・後続区間の帯域 power と−30 / −20 / −10 dB交差を維持する。sample3 の既存早期区間は[2.080,2.094)秒、強部は[2.103,2.126)秒。後続区間が未固定なら出力を見て選ばず、原音側の規則を先に決める。
2. 追加するなら、固定 PPG 一つで5原音＋保存90出力を全文推論し、全クラス分布と時刻を保存する案を検討する。未推論・低信頼・範囲外は欠測として明示する。silence の argmax だけで原音の「物理的無音」を決めない。
3. MFA は公式全文のある2録音に限定した補助案。音素別に符号付き・絶対の開始／終了／持続時間差を残し、対応不能・発音変種・低信頼を分母から黙って除かない。辞書と話者適応の条件を先に固定する。
4. native と ±3 半音、原音相対と同一音高・seed の PML 相対を分ける。5録音・2 seedを独立した90録音に数えない。既知症状の sample3 と他録音の固定イベントも分ける。
5. DTW、候補ごとの無音 trim、時刻合わせ、音量正規化で先行や尾を消さない。先行成分の減少と、子音本体・低域有声成分・後続音の保存を同時に見る。

5原音＋90出力の入力音声総時間は約496.565秒（8.28分）だが、これは推論所要時間ではない。PPG / MFA の実行時間・精度・閾値・総合順位は未測定であり、正式120例への拡大や基準方式の変更を決める材料はまだない。

## 既存測定の出典

- 90条件の固定後段指標集約 SHA-256：`1bee17075fc78e939cb4e36fe10ff23e5be87ff12585bf9758f8e6c0136b7f14`
- 同測定の完了記録：`ff07641c19cb6a6ef2ab4e8807d4b6abc50a2a49ff82258a74c1b9954b6df142`

入力は [LibriSpeech / OpenSLR 12](https://www.openslr.org/12/)（Vassil Panayotov, Guoguo Chen, Daniel Povey, Sanjeev Khudanpur、© 2014 Vassil Panayotov、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)）。研究用の固定切出し・再合成・音高編集に対する保存観測を引用した。本書に音声や転記本文は含めない。
