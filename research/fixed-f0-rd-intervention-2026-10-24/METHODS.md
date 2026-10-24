# 固定F0・Rd介入の測定と再集計

## 何を測ったか

英語40話者・各3録音の固定120録音に、同じ録音内で固定した乱数列を正負に加えた。大きさは原波形RMSの0.01、0.001、0.0001倍。参照HMPP解析120件で得たF0を共通に固定し、以後はF0再推定を止める。HMPPとHMCZTについて基準1条件・変更6条件を各録音で解析するため、参照を含め1800解析となる。

科学repoは`3f7b509b8313b5803dce2e1ededc8db9920367f1`。LLSM2は`d18cdf02b31819670e3bc23ead933ad9467da06d`、cigletは`895ba9b1c0eabee83d3544208bbc82420efa3206`を固定した。計測用の私有コードはGit外で保持する。

入力は[固定manifest](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/3f7b509b8313b5803dce2e1ededc8db9920367f1/research/pml-package-evaluation-2026-10-16/input-manifest.json)の16 kHz・mono・float64 NPY。manifest SHA256は`1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193`。公式LibriSpeech test-clean archiveは346663984 bytes、SHA256 `39fde525e59672dc6d1551919b1478f724438a95aa55f874b576be21967e6c23`。各担当がarchive、選択FLAC、PCM、入力NPYを照合したと報告している。WAVコンテナhashが履歴値と違う場合も、PCMと固定NPYの一致を別に記録した。

24 kHzへの変換は`scipy.signal.resample_poly(3,2)`。録音IDのSHA256先頭8 byteをlittle-endian整数としてPCG64へ渡し、正規乱数列を平均0・RMS 1へ合わせる。入力は`x ± ε rms(x) q`。同じqを正負と全εで共有する。nativeはfloat32、各解析の直前にseed 0、1 thread。Python3.12と固定repoのuv.lockを使用する契約である。親が受領したJSONだけでは、全依存環境やビルドの原本を独立に照合したことにはならない。

## 四つのセルと五つの差

H0/H1は基準・変更後の観測調波振幅、R0/R1はそれぞれの補間・平滑化後Rd。声道振幅をE(H,R)とし、E00/E11は自然なLayer1変換、E10/E01は研究用の組合せである。

- H_change_R0 = E10 − E00
- R_change_H0 = E01 − E00
- R_after_H = E11 − E10
- H_after_R = E11 − E01
- interaction = E11 − E10 − E01 + E00

主帯域は100〜8000 Hzの674点。補助帯域はDC/Nyquistを含む全1025点。各方式の差は4セル、方式間の比較は両方式8セルの全対象binが有限であり、共通F0が正の同じフレームだけを使う。除外フレームを0差で埋めない。

各録音・ε・符号・方式・帯域・差について、符号付き平均、符号付き中央値、正の差の割合、絶対値の95%点を保存した。方式差は同じ8セル支持で求めた統計量のHMCZT−HMPP。95%点の差は、フレームごとの方式差の95%点ではない。

各話者で3録音×正負の6対を平均し、40話者を等重みで平均した。各ε・帯域・差・統計量の全120区分で40話者・240対が揃っている。録音内の95%点を平均した値を、全フレームの95%点と呼ばない。差の95%点を足して全体の95%点を作ることもしない。

## 集計v3で直した判定

補間前と補間後のRdへ厳密な数値一致を要求していた判定を削除した。固定sourceの`interp_in_blank`は値をコピーするだけでなく演算で再構成し、raw値0はblankとして扱うため、この一致は保証されない。新たな許容差で合格へ変えたのではなく、数値差を別の観測項目へ移した。

元の配列・測定source・旧集計は変更していない。新しい集計は別ディレクトリで、元のsource-lockを参照して保存配列だけを読む。ファイル/配列hash、shape/dtype、固定F0、候補gridとindex、native config、5差fieldの同じfloat32演算順による照合、共通支持、完全話者の条件は維持した。比較計算の例外にはtracebackを残す。

測定source-lock SHA256は`726cbae72f73db9fe6e61ac86f8255aa8953cc2785d14bba90336933042b6b8f`。集計v3 lockは`61f30c5dc59289415e7d6e13fa913ae490eba4319a1d51cad700cd93127b8ddc`。その5モジュールと、読み込んだowner別run-contract/supervisor-summaryのSHAを出力に記録した。source-lockの作成時点の状態名「source_only_not_built_not_run」は、後日の実行結果へ書き換えていない。

旧集計の有効比較はowner0/1/2で59/32/63、無効は445/436/405。v3は504/468/468比較を集計可能とした。owner1について個別に理由を読んだのは先頭3件で、全436件の理由を同じだと推測していない。元担当の再集計による状態遷移と、親へ移した保存指標の照合を分ける。

補間前後の差は原因未確定として保持する。重複するbaselineを一度だけ数えた1680解析で、1035818の有限な非zero raw値を持つ解析×フレーム対のうち26064対が厳密には異なる。最大絶対差は6.437301635742188e-5、最大相対絶対差は7.563892331915836e-5。Rdの単位は無次元であり、これをそのままdB差と読まない。全件を丸め差と分類せず、元の値を修正しない。

## 試行履歴と保持の限界

最終的に採用した計測3担当は42/39/39録音を完了したと報告した。前のowner0は記録形式の不一致、次のowner0は準備後の空き容量不足で科学処理前に停止した。前のowner2はpyworldのimport失敗でnative呼出し0件だった。これらを新しい科学結果へ混ぜず、実行環境・配置を修正した別担当の結果を使う。後のv3再集計でnative処理は再実行していない。

親が受領したものは各担当の派生集計JSONである。全4セル配列、全Rd trace原配列、元のビルド/実行証跡の大きい束は転送未完了。親は保存JSONのbytes/SHA、全予定キー、support/point数、保存値の方式差、話者集計を照合したが、元フレームからの95%点やnative処理を独立に再現していない。この公開物の分割JSONは受領したscalar記録であり、未取得の配列の代替ではない。

この診断で復号・音声・MOS・知覚品質・生理的Rdの正解は測っていない。自然音声全体や既存方式に対する採用結果ではなく、現在のApronを維持する。

補間処理の出典：[固定cigletのinterp_in_blank](https://github.com/Sleepwalking/ciglet/blob/895ba9b1c0eabee83d3544208bbc82420efa3206/ciglet.h)、[cig_interp](https://github.com/Sleepwalking/ciglet/blob/895ba9b1c0eabee83d3544208bbc82420efa3206/ciglet.c)。新しい段階記録の不一致数から旧判定を再構成した件数は、owner別の有効59/32/63、無効445/436/405に一致した。これは旧判定の件数の照合であり、差の原因を丸めと確定するものではない。
