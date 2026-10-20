# MOCHA fsew0 v1.1 の時刻・長さの来歴：公開一次資料の追補

閲覧日：2026-10-20（UTC）

## 結論

- **confirmed（文書上）**：MOCHA 元論文は録音後の同期処理を説明している。したがって「同時収録との説明しかない」ではない。
- **unconfirmed（配布実体との対応）**：今回読んだ公式資料では、`fsew0_v1.1.tar.gz` の `.wav` / `.lar` 各ファイルの開始時刻、切り出し終端、適用済みの offset 値、`sample_count` 差との対応は確認できなかった。
- **判断保留**：Cloud の「全 460 対で sample_count が異なる」という報告だけで、破損・非同期とも、正しく補正済みとも断定しない。同時収録、同一サンプルレート、同期処理の説明は、現行配布ファイルの長さ一致・サンプル 0 の同時刻・epoch 精度の保証とは別である。

この追補は公開 README・ライセンス・公式説明・元論文の閲覧だけによる。新たな archive / 音声データの取得、波形解析、補正の推定・実装はしていない。凍結済み bundle と既存ノートは変更せず、人工 500、固定 120 の品質集合、現在の phase 研究、PML base に変更を加えない。

## 1. 今回の出発点：Cloud 報告であり独立確認ではない

親から受領した Cloud の header 監査報告：

- 対象：公式 `fsew0_v1.1.tar.gz`
- サイズ：162,523,086 bytes
- SHA-256：`b966246d8ec2ffb89203b9c633d47ff16ae17ebe66b1ba446055136966ffe597`
- 460 ID のすべてに `.wav` / `.lar` が各 1 個あり、欠落・重複 0。
- 920 header はすべて 16 kHz、mono、2-byte PCM、little endian、1024-byte header で、payload の計算も一致したとの報告。
- 一方、`sample_count` は全 460 対で異なったとの報告。

**状態：reported / independent verification unconfirmed。** 原文 inventory は Library HTTP 403 により転送できず、親も本追補の調査者も独立照合していない。この数値を、本追補が確認した実体検査結果や公開資料の記述として扱わない。差の符号・大きさ・発話別一覧も本追補では確認していない。

## 2. 公式配布文書で確認したこと

### 2.1 一般 README

資料：
- 現行の一般 README：<https://data.cstr.ed.ac.uk/mocha/README_v1.2.txt>
- 旧版：<https://data.cstr.ed.ac.uk/mocha/archive/README_v1.1.txt>
- 旧版：<https://data.cstr.ed.ac.uk/mocha/archive/README.txt>
- 配布目次：<https://data.cstr.ed.ac.uk/mocha/>

**confirmed**：

- §1.1 は serial port 通信を用いた 3 台の PC への同時収録、§1.4 は同期への配慮を述べる。
- §2.4–2.5 は同じ 3 桁の発話 ID を持つ `.wav` と `.lar`、両者の 16 kHz / 16-bit / NIST header 形式を説明する。
- EMA の時刻チャンネルと `.lab` の開始・終了時刻は記載されている。ただし、それらは `.wav` / `.lar` 間の offset 表ではない。

**unconfirmed**：上記 README に、`.wav` / `.lar` が等長であるとの要件、個別の切り出し境界、サンプル 0 の物理的時刻、offset 値一覧、`sample_count` 不一致の説明は見つからなかった。

一般 README v1.2 の WinZip ASCII 変換に関する header 破損注意は確認したが、今回の Cloud 作業にその処理があった証拠ではなく、長さ差の原因説明として流用しない。

### 2.2 fsew0 v1.1 固有 README

資料：<https://data.cstr.ed.ac.uk/mocha/README.fsew0.v1.1>

**confirmed**：Release v1.1 では ASCII / HTK label が含まれ、EMA コイル再装着後の位置的不連続を処理したと説明する。

**unconfirmed**：この README は音声–laryngograph の切り出しや sample 数の差を説明していない。EMA の位置補正を `.wav` / `.lar` の時刻補正と読み替えない。

同 README が参照する旧 URL は以下。今回の閲覧では本文を取得できず、下記 §3 の大学リポジトリ版と同一ファイルであるとの照合もしていない。

- <http://sls.qmced.ac.uk/pubs/wrench001.pdf>
- <http://sls.qmced.ac.uk/pubs/wrench002.pdf>

### 2.3 ライセンス

資料：<https://data.cstr.ed.ac.uk/mocha/LICENCE.txt>

**confirmed**：研究・教育・個人利用の条件、表示保持、変更明示、商用利用の事前書面許諾、無保証の記載を閲覧した。時刻合わせや sample 数の説明はない。閲覧のみで、申請・同意・再配布はしていない。

## 3. 元論文に実際にある同期手順

Alan A. Wrench (2000), *A Multi-Channel/Multi-Speaker Articulatory Database for Continuous Speech Recognition Research*, PHONUS 5, pp. 1–13.

- 大学リポジトリ書誌：<https://eresearch.qmu.ac.uk/items/588a0243-580d-4da3-9e40-bf437f9d59cf>
- 本文 PDF：<https://eresearch.qmu.ac.uk/server/api/core/bitstreams/c2bbbbbb-7822-47f1-8ed8-39d13447bfad/content>

**confirmed（今回、本文を直接閲覧）**：

- §2.2、§2.3.1（印刷 pp.6–7）：音声と laryngograph は同じ PC の Soundblaster の 2 チャンネルで 16 kHz / 16-bit 収録。EMA と EPG は別 PC。録音開始信号と確認信号の後、1 kHz・20 ms の音を鳴らす手順を述べる。
- §2.3.2（pp.7–8）：音声–EMA は、各発話と同期音サンプルの相関で音の開始を検出し、音の継続時間を音声録音から差し引くと説明する。音声–laryngograph は、両信号を逆フィルタした残差の相関で同期する。LPC は laryngograph が 10 次、音声が 18 次で、係数は 10 ms ごとに生成する。

**記述の限界**：これはコーパス作成時の方法であり、`fsew0 v1.1` の各ファイルに施した移動量・切り出し・padding・共通時刻原点や、その後の残留誤差の表ではない。10 ms は LPC 係数更新間隔であり、同期誤差や GCI ラベルの精度と同一視しない。上記方法が今回報告された長さ差を生んだとの因果関係も、本文からは確認できない。

補助的に閲覧した元発表の抄録：
Wrench & Hardcastle (2000), *A Multichannel Articulatory Speech Database and its Application for Automatic Speech Recognition*：
<https://www.phonetik.uni-muenchen.de/institut/veranstaltungen/SPS5/abstracts/03_abs.html>

この URL では抄録だけを確認した。全文確認の根拠には用いず、長さ差の追加説明も得られなかった。

## 4. 残る未確認事項と終了位置

| 問い | 状態 |
|---|---|
| コーパス作成時に音声–laryngograph 同期処理を行うとの一次記述はあるか | confirmed：元論文 §2.3.2 |
| 当該 v1.1 の全 460 対にどの手順・offset が適用されたか | unconfirmed |
| 長さ差が冒頭・末尾のどちらに由来するか、または別の処理か | unconfirmed |
| 各 `.wav` と `.lar` のサンプル 0 が同じ物理的時刻か | unconfirmed |
| 全 460 対の長さ差の原因、破損の有無、残留同期誤差 | unconfirmed |
| EGG / 残差相関の同期が完全な生理的 GCI 真値を保証するか | 保証を確認していない。そう扱わない |

本追補で新たに確認できたのは「公開元論文に音声–laryngograph の後処理同期が明記されている」点までである。現行配布の時刻対応の保証や、報告された sample_count 差の説明には到達していない。推測補正・新実験・追加取得は行わず、文書調査としてここで終了する。
