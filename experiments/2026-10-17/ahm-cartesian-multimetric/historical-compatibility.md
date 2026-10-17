# 保存済み7参照・旧8方式の引用互換性監査

2026-10-17。保存JSON・ソース・契約の読取専用監査。音声生成、モデル読込、指標再計算は実施していない。

結論：今回の79軸に対応する旧保存行は全79軸に存在する。ただし、今回の新runと「全条件が厳密同一」と認定して順位表へ追加できる測定値は、本監査では0軸。旧7参照＋HNM v3は、出典と旧実行条件を付けた別表の歴史参考として引用できる。今回の現ベースPML・候補・WORLDの同時比較とは分離する。

## 分類表

| 対象 | 分類 | 確認した根拠・残る差 |
|---|---|---|
| 固定集合の識別・原音入力・共通窓 | 1：この条件情報は同一として引用可能 | 120/120でcase、話者、入力N、16 kHz、入力NPY SHA256、全8方式の共通窓Nが今回の計画と一致。40話者。例：6秒入力→95840 samples（5.99秒）。測定値の一致を意味しない |
| 指標実装・資産の定義 | 1：照合済みの定義は引用可能 | 音響・MOS・ASR・話者の保存契約にある19件のソースSHAが今回のevaluator bundleと一致。編集音高のcontrols.pyも一致。モデルの内容SHA・設定は下記のとおり。全runtimeの同一性ではない |
| 音響65軸（STFT、帯域、RMS、ESTOI、YIN、包絡、変調、40 ms局所ERB等） | 2：歴史参考 | 旧8方式共通16 kHz先頭窓と数式は対応。各軸960行（120×8）の保存値・状態を確認。旧全出力PCMと今回実行環境の完全照合は未成立 |
| 20 ms ERB、SCOREQ、無編集ECAPAの3軸 | 2：歴史参考 | 旧qualityは共通窓、2 threads、反復1。ERB=32帯域/5 ms hop/20 ms窓。SCOREQ natural/ref・padding 320、ECAPA raw embeddingのモデル内容SHAは今回と一致。実行環境のbinary同一性は未立証 |
| 無編集native MOS 1軸・編集±3半音MOS 2軸 | 2：歴史参考 | 全長入力、UTMOSv2公式cc2700…、checkpoint revision506474…、内容SHA c8149d…、bvcc/fold0、seed20261012、反復1が一致。旧4 threadsに対し今回2 threads。native sample rateが方式で異なり、旧7参照の新runtime測定は行っていない |
| 増分CER/WER 2軸 | 2：歴史参考 | wav2vec2-base-960h revision22aad5…、資産SHA、greedy CTC、公式全文55録音32話者、原音CER gate0.20、NFKC/casefold/空白正規化が対応。全120のASR成功とは記述しない。旧出力からの保存評価である |
| 編集ECAPA 2軸・編集音高/未検出率4軸 | 2：歴史参考 | 編集ECAPAは原音excerpt全長参照、音高は同方式の無編集出力参照。±3半音条件・数式が対応。ただし方式ごとの編集可否・長さ処理を維持する必要あり。旧MagPhaseのepoch対応等を今回の単純等長条件と同一視しない |
| 旧native出力SHA→評価入力PCM→各保存値の全件連結 | 3：今回への厳密流用に必要な証拠不足 | 公開rawのraw_result_sha256は結果JSONのhashであり波形hashではない。旧synthesis契約・資産hash・120原音来歴はあるが、それだけで全方式全波形の一致を証明しない |
| runtime全体のbit同一性・速度比較 | 3：同一性証拠不足／速度は比較不可 | 主要package版は一致するが新runtime自身が旧binary同一性を主張していない。機械・ライブラリbinary・スレッド差がある。旧速度を今回の速度順位に加えない |
| GOLF/SiFi-GAN重みの独立revision | 3：保存証拠不足 | 旧来歴で独立model revision未保存と明記。内容SHAとcode revisionは別物として扱う |
| 2026-10-13 formal-hnm-v3-references | 2：別条件の歴史参考 | 当時の方式ごとのcommon_prefix。初例HNMは96000 samplesであり、今回の全8方式共通95840 samplesとは異なる。旧8方式共通窓の代用にしない |
| 2026-10-12 reference-methods | 2：少数例の歴史記録のみ | 2音声、MOSなし。固定120の採否比較へ混ぜない |

分類1は確認済みの「条件・定義情報」に限定する。分類2の値は旧実行を引用したもので、今回新しく計算した値ではない。欠測、適用外、未対応は保存状態を保ち、ゼロ・最下位順位に置換しない。旧HNMとの差・旧順位は当時の8方式内のものと明示し、現PMLとの差へ読み替えない。

## 公開済み出典（リポジトリ相対）

- `research/all-method-final-2026-10-15/results.json.gz`：共通窓、旧集計、対象、制限
- `research/all-method-final-2026-10-15/provenance-manifest.json`：入力、合成、音響、MOS、ASR、話者、制御、資産の保存契約
- `research/all-method-final-2026-10-15/raw-values.part-0001.json.gz`・`raw-values.part-0002.json.gz`：保存値・状態・結果出典hash
- `research/all-method-final-2026-10-15/publication-limitations.json`：hash・revision・公開範囲の限界
- `research/pml-package-evaluation-2026-10-16/input-manifest.json`：今回へ引き継いだ入力・共通窓
- `experiments/2026-10-13/formal-hnm-v3-references/results/run-001/results.json`：方式別共通窓の旧比較
- `experiments/2026-10-12/reference-methods/results/run-001/results.json`：2音声の旧記録

原音・全長出力・重み本体・私有経路・Library識別子は本稿へ掲載しない。数値再計算、順位再集計、新規測定の主張はしない。
