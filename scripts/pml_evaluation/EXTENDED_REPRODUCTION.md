# PML 追加評価の再実行入口

このディレクトリは実測 driver をパス指定可能にした公開版です。**この公開版は未実行**です。掲載値を生成した実測版の SHA と公開版 SHA は `extended-driver-provenance.json` に区別しています。計算式・seed・支持集合・失敗/未対応の扱いは変更していません。新しいテストは実装していません。

## 共通契約

リポジトリをインストールした Python 環境で、まず `prepare_inputs.py` と `run_native.py` を実行してください（主 README）。公開入口は必ず `run_extended.py` を使います。内部の driver は直接実行しません。別の実測 run の JSON をそのまま新 run に混ぜないでください。各記録の絶対パス、driver SHA、input/native contract SHA はその run に結びついています。

```
python scripts/pml_evaluation/run_extended.py \
  --run-root /absolute/path/to/new-run \
  --corpora-root /absolute/path/to/corpora \
  --historical-root /absolute/path/to/historical \
  --asv-input-root /absolute/path/to/human-similarity \
  --model-cache /absolute/path/to/utmosv2 \
  extended/run_edits --stage decode
```

共通パス引数は stage の前、既存 driver の引数は stage の後に置きます。モデル取得と環境は `QUALITY_REPRODUCTION.md`。編集/量子化 MOS は同じ weights/ と wav2vec2_config/ を参照し、ECAPA は run-root/assets/ecapa/embedding_model.ckpt を使います。入力は prepare_inputs が作る絶対 input.path、native/<id>/{record.json,parameters.pml,wave.npy} を使います。wrapper は最初に公開 native driver/source/input の hash 契約を検証します。

## 実行順

下記の stage 名を上のコマンド末尾に指定します。RTF 計測終了後に実行し、他の重い処理と重ねないでください。

1. `extended/run_edits --stage decode` → `extended/run_edits --stage measure` → `extended/summarize_edits` → `extended/summarize_pitch_support`
2. `extended/run_preservation` → `extended/summarize_preservation`
3. `extended/extract_features` → `extended/run_train_features` → `extended/run_readout`
4. `abx/run_abx`（既存オプションは内部 driver の argparse を参照）→ `abx/compare_abx`
5. `auxiliary/extract_asv` → `auxiliary/aggregate_asv`
6. `extended/run_quantization` → `extended/measure_quantization` → `extended/summarize_quantization`
7. `extended/run_edit_quality speaker_ecapa` と `extended/run_edit_quality utmosv2`
8. `extended/run_quantized_quality speaker_ecapa` と `extended/run_quantized_quality utmosv2`
9. `extended/summarize_quality quality speaker_ecapa`（quality/quantization-quality × speaker_ecapa/utmosv2 の各組合せ）
10. 主 unedited UTMOS と上記 MOS が揃ってから `extended/record_mos_reuse` → `extended/rank_extended`。readout は `extended/rank_readout`。最後に `extended/write_coverage`。

量子化は標準 .pml の変更ではありません。FWCEP/F0 の float16/float32 研究用 NPZ を実際に保存・読戻しして評価し、binary NM は保持します。容量の定義は標準 payload と分離します。編集は ±3 半音と ±6 dB。時間伸縮・傾斜制御・補間・再量子化など未実装項目は unsupported のままです。ASV は音声合成 MOS ではなく既存評定との特徴距離の関係です。

## 外部入力・固定 manifest

`extended-input-inventory.json` に必要ファイルの相対配置と元実測 SHA を記録しています。private Library ID は実行入口に使いません。音声、モデル、聴取者別生データは同梱しません。次の元データを各利用条件の範囲内で取得し、既存の取得スクリプトで生成します。取得や既存方式の再計測はこの wrapper が暗黙実行するものではありません。

- 主評価120: リポジトリ data/clean_speech_v1.json と prepare_inputs。発話/話者/PCM hash を固定。
- Train120/40話者: https://www.openslr.org/resources/12/dev-clean.tar.gz 。既存 scripts/all_metrics_datasets_contract.py と all_metrics_datasets_train.py の選択規則を利用。6秒以内、先頭から、正規化なし。corpora-root/readout-train/inputs.json と audio/<id>.npy を置く。学習・評価の話者/発話/hash の交差を禁止し、標準化は train のみ。
- ABX: https://download.zerospeech.com/datasets/abxLS.datasets.zip の test-clean/triphone-test-clean.item。既存 all_metrics_datasets_abx.py / all_metrics_datasets_abx_sources.py で固定集合・PCM一致証跡を作る。corpora-root に abxls120-triphones.json、abxls120-source-identity.json、preserved-sources/abx-labels/triphone-test-clean.item。ラベル SHA は e327222d6c16b1e8c541994e8dc58949d0fcefc4ca5b6d7b1ace3df373ef60f3。三つ組の再抽選はしない。
- ASV: 既存 research/all-method-corpora-plan-recovery-2026-10-14.md と scripts/all_metrics_datasets_human.py / all_metrics_human_data.py の公式評定CSV・ASVspoof2019取得元/規約/固定規則に従う。asv-input-root に selection.json、audio-inputs/asvspoof2019_<stem>.npy、audio-records/<stem>.json。聴取者 ID を含む元 CSV は公開しない。元計画105録音/84対、取得104録音、旧方式との共通評価は100録音/80対。この集合を拡張して既存値と混ぜない。

### 旧比較値が必要な stage

PML単独の計測は旧 scalar を必要としません。比較ランキングには historical-root 以下が必要です。

- edited-comparison/{raw-records.json,group-contracts-and-aggregates.json,compatibility-check.json}
- feature-assessment/readout-rankings/{raw-recordings.json,results.json,contract.json} と feature-assessment/targets/{train,evaluation}/<id>.json
- feature-assessment/abx-rankings/contract.json と feature-assessment/abx-rankings/raw/<method>.json（hnm/world_harvest/facodec/hifiglot/golf/sifigan/llsm2/magphase）
- asv-human-contract.json と human-availability100/conditional-private-evidence/pair-distances.json

これらは旧公開測定スクリプトの保存結果またはその同一 SHA のアーカイブから準備します。必要な録音別/三つ組別値を持たず集計平均だけから復元することはできません。未入手の場合、PML単独までを再実行できても旧方式ランキング全体を再現できません。旧互換性記録の source_checks は source/ 以後のリポジトリ相対位置を照合し、期待 SHA を変更しません。モデル・環境・入力の互換性は元契約どおり必須です。歴史的に4スレッド、新PML2スレッドだった点も保持します。

公開化の静的確認は AST/Ruff/行数のみです。公開入口の実行成功や全入力が公開配布済みであることを意味しません。
