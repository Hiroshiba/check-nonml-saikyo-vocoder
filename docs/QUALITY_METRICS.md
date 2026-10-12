# 保存済み音声に追加する品質・話者・特徴距離の評価

本書は実装仕様です。ユーザー指示を追加・変更するものではありません。

## 今回追加するもの

直近に取得方法を整理した5項目を実装します。以前提案した18項目すべてを完成させたPRではありません。

| 項目 | 実装・入力 | 出力 | 今回の確認範囲 |
|---|---|---|---|
| 予測MOS | 固定UTMOSv2をローカル資産で構築 | 予測MOS | 既存の構築・推論方式を再利用。新経路での重み付き推論は未実行 |
| SCOREQ参照あり | 著者のfixed_nmr ONNX＋同一長の原音・再合成音 | 埋め込みのEuclidean距離 | 資産不足の扱いを確認。ONNX推論と上流との数値一致は未確認 |
| ViSQOL Audio | Google公式CLI＋Audio用SVRモデル＋48 kHz音声 | MOS-LQO | 公式の引数とPCM16制約を確認。バイナリでの推論は未実行 |
| 話者同一性 | SpeechBrain公式ECAPA構造＋embedding_model.ckpt | コサイン類似度 | 構造・encode_batchの処理を確認。実重みでの推論は未実行 |
| 人間評定と特徴距離 | 提供された話者特徴＋既存評定CSV | group別Spearman・評定対内の最近傍一致 | 人工順位を人間評定とする入力を拒否。JVS実データは未取得 |
| 補助：ERB | 32個のERB三角帯域でSTFTパワー包絡を比較 | dB絶対差とP95 | 手元の音声で初回＋5反復を実行 |

ERBは聴覚モデル全体でも、MOSへ校正した尺度でもありません。全帯域の再構成診断です。
この追加処理は音声の合成、方式の採用、過去結果の書き換えをしません。

## 実行例：既存固定比較を追加評価する

まず通常の比較で `results.json` と `waveforms/<case>/<method>.npy` を保存します。
音響比較が完了したディレクトリを次へ渡します。元の契約に保存されたベースの版を使用し、現在のBASELINE.jsonで上書きしません。

```sh
uv run --locked python -m vocoderbench.quality \
  --benchmark runs/fixed-comparison \
  --assets configs/quality-assets.example.json \
  --metrics utmosv2 erb \
  --repetitions 5 --threads 4 \
  --output runs/fixed-comparison-quality-001
```

SCOREQ、ECAPAを使う場合の追加依存は `onnxruntime==1.22.0` と `speechbrain==1.0.3` です。
通常比較のuv.lockは変更せず、追加評価の実行だけに依存を付与できます。
ネット接続がある環境で追加依存を事前準備し、取得済み資産を配置してください。

```sh
uv run --locked --with onnxruntime==1.22.0 --with speechbrain==1.0.3 \
  python -m vocoderbench.quality \
  --benchmark runs/fixed-comparison \
  --assets configs/quality-assets.example.json \
  --metrics utmosv2 scoreq speaker_ecapa erb \
  --repetitions 5 --threads 4 \
  --output runs/fixed-comparison-quality-002
```

追加依存を含めたuv実行環境の完全なオフライン構築は今回未検証です。上の `uv` は必要に応じてパッケージを取得します。
指標評価のPython処理そのものにはダウンロード機能がなく、HFのオフライン設定も有効にします。
モデルを欠いた状態で通信を試みたり、無関係な指標へ置き換えたりしません。

ViSQOL Audioは48 kHz専用とし、16 kHzの既存コーパスでは対象外になります。
48 kHzへ変換しただけで元録音に高域があったとはみなしません。

## 任意の方式・48 kHz音声を比較する

`configs/quality-inputs.example.json` のファイル名を実際の音声へ変更します。
任意の方式IDを使えます。HNMのパラメータ構造やAPIへの適合は要求しません。

```sh
uv run --locked python -m vocoderbench.quality \
  --manifest configs/quality-inputs.example.json \
  --assets configs/quality-assets.example.json \
  --metrics visqol_audio erb \
  --output runs/audio48-quality-001
```

各caseの `outputs` に `baseline` として指定した方式を必ず含めます。原音は予約ID `identity` として自動追加します。
入力はモノラルWAVか浮動小数点PCMのNPYです。NPYには `sample_rate` が必須です。
ファイルは入力一覧・資産設定それぞれのJSONが置かれたディレクトリからの相対パス、または絶対パスで指定できます。
このCLIは無編集再合成専用です。長さ・サンプルレートが不一致なら失敗させ、自動整列、DTW、無音除去、音量補正を共通前処理では行いません。
自然音声・合成音声は1秒以上を対象にする予備プロトコルです。正弦波等には `kind: artificial_probe` を指定し、音声品質・話者指標を適用しません。
各指標に固有の再標本化・正規化・内部整列は別途存在し、各評価器の来歴へ記録します。

## 手元で取得した資産の置き方

`configs/quality-assets.example.json` を参照してください。使わない指標は設定を削除するかnullにできます。
`--metrics` で要求したのに設定がない指標は「未設定」です。黙って無視せず終了コード1を返します。
各資産の実SHA256・サイズを記録します。`model_sha256` 等、パスキーに `_sha256` を付けた設定で期待hashも固定できます。
UTMOSv2は既存実装と同じ既知SHA256を強制します。

- UTMOSv2: `checkpoint`、`config`、`preprocessor_config`。設定2ファイルは元の名前で同じディレクトリに置きます。
  既存 `mos.py` の完全なstate_dictをstrictに読む構築方式を使うため、初期化時に上書きされるwav2vec2/画像モデルの事前重みは追加取得しません。
  固定commit由来のutmosv2導入履歴も照合します。単なるZIP展開や別版を固定版と偽って使いません。
- SCOREQ: `fixed_nmr_telephone.onnx`（natural/ref）か `fixed_nmr_synthetic.onnx`（synthetic/ref）。domainを明示します。
  NRモデルは対象外です。公式に合わせ16 kHzへtorchaudioで再標本化し、320の倍数に右ゼロ埋めした波形をONNXへ渡します。
  両波形の埋め込みのEuclidean距離を計算します。ONNX出力の次元を確認し、MOSスカラーを距離として流用しません。
- ECAPA: `embedding_model.ckpt`。公式公開設定の80 mel・1024 channel・192次元の構造をコード内で明示します。
  `encode_batch(normalize=False)` と同じFbank→発話内平均正規化→埋め込みの経路です。
  話者分類・グローバル埋め込み正規化は使わないためclassifier・label_encoder・mean_var_norm_embの重みは不要です。
  動的な外部YAMLの読み込み・ダウンロードはしません。異なるECAPA構造はstrictロードで拒否します。
- ViSQOL: 実行権限のあるGoogle公式バイナリとAudio用 `libsvm_nu_svr_model.txt`。
  Python移植版を公式版と偽って呼びません。公式CLIがPCM16のみ対応のため、両波形を同じ規則で量子化します。
  丸め後にPCM16の範囲を超える入力は失敗とし、クリッピングや音量調整で隠しません。

モデル・私有音声・JVS音声をGitへ入れません。従来の `mos.py` の通常比較用ダウンロード動作は変更していません。

## 人間の話者類似度評定と特徴距離

音声対の品質評価とは別コマンドです。エンコーダーが作った話者ごとの特徴ベクトルを次のJSON形式で渡します。
実際のベクトルと既存評定の来歴を記録してください。以下の `vectors: {}` は書式説明であって実測データではありません。

```json
{
  "method": "evaluated_encoder",
  "feature_description": "どの特徴を抽出・選択したか",
  "pooling": "発話間・時間方向にどう集約したか",
  "rating_experiment": "既存評定の出典と刺激条件",
  "rating_kind": "human",
  "rating_direction": "higher_is_more_similar",
  "vectors": {}
}
```

CSVの列は `speaker_a,speaker_b,group,rating` です。JVSの配布ファイルは、この明示形式へ変換して使います。
評定の生ファイル形式の自動推測・JVSアーカイブ展開・特徴抽出はこのPRには含めません。
異なる評定実験や比較条件を混ぜず、groupに記録します。同一話者対の個人評定は同一条件内で事前集約します。

```sh
uv run --locked python -m vocoderbench.quality_similarity \
  --features /path/to/speaker_features.json \
  --ratings /path/to/existing_human_ratings.csv \
  --repetitions 5 --output runs/similarity-001.json
```

同名のHTMLも出力します。group別Spearman相関、有効対数・予定対数、話者数、欠けた特徴を全行保存します。
最近傍一致は、各話者について評定がある2人以上の相手内で計算します。全コーパスの最近傍ではありません。
人間側の同率最高はすべて正解に含め、特徴側の同率最高は等確率として一致率を平均します。
距離の重みを評定へ当てはめず、正規化した特徴のコサイン類似度を使います。
話者対の組合せを独立被験者数として扱わないため、単純なp値・信頼区間は出しません。
人間評定に使われた音声との対応・刺激条件・学習データ重複の妥当性は、別途確認が必要です。

## 結果と計測時間

音声側は `results.json`、`summary.json`、`contract.json`、`index.html` を新しい出力先に保存します。
既存結果を上書きせず、音声も勝手に複製・公開しません。固定比較から実行した場合、元の音声付きレポートへのリンクを載せます。
結果は指標×ケース×方式ごとに保存し、ベースとの差を表示します。平均の総合点は作りません。

- 初期化時間: パッケージの読み込み、資産hash確認、モデル構築・読み込みを含みます。
- 初回: ケースごとの最初の指標呼び出しです。最初のケース以外はモデルはすでに温まっています。
- 反復: 同一入力・同一合成seedを5回計測し、各回の値・実経過秒・親プロセスCPU秒、中央値・最小・最大を保存します。
  MOS抽出seedは毎回固定し、反復計算を5つの独立MOS評定や品質向上のためのアンサンブルと扱いません。
- 入力WAV/NPYの読込・入力hashは指標呼び出し時間から除きます。指標固有の再標本化と両音声の推論は含みます。
- ViSQOL CLIは各呼出しにプロセス起動・モデル読み込み・PCM16 WAV入出力を含みます。
  そのCPU秒はPython親プロセスのみで、C++子プロセスのCPU時間ではありません。
- 人間評定側の時間は距離・順位集約のみです。エンコーダーの特徴抽出時間を含みません。

利用不可、未設定、対象外、失敗、一部反復失敗は区別し、品質値をnullにします。
要求した行がすべて測定できた場合だけ終了コード0です。終了コード0は品質合格ではありません。
入力ファイルが途中で変更された場合は失敗とします。途中までのJSONは逐次残しますが、中断再開機能はまだありません。
この追加CLIは1評価器ずつ読み込みます。実メモリ上限内での全モデル連続実行は未確認です。

## 一次資料と実装上の確認

- [SCOREQ公式コード](https://github.com/alessandroragano/scoreq/blob/main/src/scoreq/scoreq.py): ONNXモデル選択、16 kHz前処理、320倍数padding、距離計算。
- [UTMOSv2公式推論](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/docs/inference.md): fold・抽出反復・条件ID。
- [ECAPA公式構造](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/a9f171aee6b706ea72b35dfe6d9dbd07947c2555/hyperparams.yaml): Fbank、構造、発話内正規化。
- [SpeechBrain encode_batch](https://github.com/speechbrain/speechbrain/blob/v1.0.3/speechbrain/inference/classifiers.py): 埋め込みの推論経路。
- [ViSQOL公式入力読込](https://github.com/google/visqol/blob/v3.3.3/src/wav_reader.cc): 16-bit PCMの制約。
- [ViSQOL公式CLI](https://github.com/google/visqol/blob/v3.3.3/src/commandline_parser.cc): Audio/SpeechとCSV出力の引数。

品質値の妥当性・実重みの相互互換性は、モデルと音声を取得後に検証してください。
