# MOCHA fsew0 v1.1 時刻・長さ追補の独立レビュー

レビュー日：2026-10-20 UTC  
対象：`mocha-fsew0-timing-provenance-followup-20261020.md`

## 判定

**重大指摘・修正必須事項なし。文書上の同期方法と、現行配布ファイルの未確認事項を適切に分離している。**

本レビューは公開一次資料の内容と追補本文の論理の照合である。Cloud側のarchive、header、inventory、payloadを取得・閲覧しておらず、raw監査や「全460対」の独立再確認ではない。

## 一次本文との照合

Alan A. Wrench (2000), *A Multi-Channel/Multi-Speaker Articulatory Database for Continuous Speech Recognition Research*, PHONUS 5, pp.1–13 の大学リポジトリ本文を直接閲覧した。

https://eresearch.qmu.ac.uk/server/api/core/bitstreams/c2bbbbbb-7822-47f1-8ed8-39d13447bfad/content

- §2.2、§2.3.1（pp.6–7）：音声とlaryngographを同じPCのSoundblasterの2チャンネルで16 kHz・16 bit収録する説明、および別PCのEMA／EPGを含む開始信号・確認信号と1 kHz・20 ms音の説明は、追補と一致する。
- §2.3.2（pp.7–8）：音声–EMAでは同期音の開始を相関で検出し、音の継続時間を音声録音から差し引くという説明がある。音声–laryngographでは各信号を逆フィルタした残差同士の相関で同期する。後者のLPC係数は10 msごと、laryngograph 10次・音声18次。追補はこれらを正しく区別している。
- 原著はこの節で、現行fsew0 v1.1の発話別offset、ファイルの切り出し開始・終了、padding、残留誤差の一覧を与えていない。
- 20 msを`.wav`／`.lar`の長さ差やtrim量に読み替えていない。10 msを同期誤差・GCI精度と読み替えていない。

したがって、「公開文書には同時収録の説明しかない」という理解はこの原著により補完・修正される。一方、「現行v1.1の各ファイルがどの量だけ補正済みか」は、同期方法の記述だけでは確定しない。

## 配布説明との整合性

今回README v1.1を再閲覧し、前回同日に直接確認したv1.2・fsew0 v1.1固有README・LICENCEの内容とも照合した。

- https://data.cstr.ed.ac.uk/mocha/archive/README_v1.1.txt
- https://data.cstr.ed.ac.uk/mocha/README_v1.2.txt
- https://data.cstr.ed.ac.uk/mocha/README.fsew0.v1.1
- https://data.cstr.ed.ac.uk/mocha/LICENCE.txt

同じ発話ID、16 kHz／16 bit／NISTという形式の説明は、等長や同一物理時刻から始まることの保証ではない。EMA座標の補正、`.lab`の区間時刻、WinZipのheader破損注意を、音声–laryngographのsample数不一致の説明へ転用しない扱いも適切。

旧`archive/README.txt`は本レビュー時の直接取得経路では読めなかったため、その旧版の全文を独立確認済みとはしない。同期方法の判定は読めた原著本文に基づき、この取得失敗によって結論は変わらない。

補助的なSPS5抄録も確認したが、同期方法の本文根拠や現行配布ファイルの長さ差の説明としては使っていない。

https://www.phonetik.uni-muenchen.de/institut/veranstaltungen/SPS5/abstracts/03_abs.html

## Cloud報告と因果推論

追補は、サイズ・SHA-256・460対・920 header・欠落重複0・全対のsample_count差を**reported**として明示している。親が原inventoryをHTTP 403により取得できていないという受領状況も、独立検証未完了として扱っている。

このレビューでも数値の正しさ、当該archiveとの対応、差の符号・量・発話別分布は確認していない。HTTP 403は親から伝達された状況であり、本レビューがLibrary操作で再現した結果ではない。

追補は次のいずれも断定しておらず、妥当である。

1. 長さ不一致が破損または非同期を意味する。
2. 長さ不一致が原著の同期後処理から生じた。
3. 全対が正しく補正済みで、サンプル0が同じ時刻を表す。
4. 残差相関による同期が完全な生理的GCI真値を保証する。

原著は後処理の存在を確認する資料であって、現行ファイル個々の処理履歴を立証する台帳ではない、という追補の終了位置を支持する。

## 操作範囲

追補作成者へ「重大指摘なし」と連絡済み。凍結済みbundle、元追補、既存レビューは編集していない。本レビュー文書のみ新規保存した。

データ取得、音声解析、補正推定・実装、新実験、テスト、Git変更、Cloud／Library操作は行っていない。人工500、固定120、phase研究、PML baseの変更や新実験の許可として扱わない。
