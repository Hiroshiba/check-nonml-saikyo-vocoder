# 保存済み音声に追加する品質・話者・特徴距離の評価

本書は実装仕様です。ユーザー指示を追加・変更するものではありません。

## 当初の追加内容と確認範囲（2026-10-12）

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

各caseの `outputs` に `baseline` として指定した方式を必ず含めます。原音は予約ID `identity` としてUTMOSv2だけを自動測定します。参照型指標の原音自己比較は行いません。
入力はモノラルWAVか浮動小数点PCMのNPYです。NPYには `sample_rate` が必須です。
ファイルは入力一覧・資産設定それぞれのJSONが置かれたディレクトリからの相対パス、または絶対パスで指定できます。
このCLIは保存済み音声の追加評価用です。SCOREQ・ViSQOL・ERBの参照距離は無編集再合成の比較に用い、意図した編集を原音との差で罰する尺度にはしません。適用条件を満たす編集点は、非参照UTMOSv2、または全点で固定した適切な参照に対するECAPA話者類似度の入力として別工程から渡せます。声質変更など話者保持を目的としない操作にECAPAを一律要求しません。参照型指標は長さ・サンプルレートが不一致なら失敗させ、自動整列、DTW、無音除去、音量補正を共通前処理では行いません。非参照のUTMOSv2は出力固有の全長・標本化周波数で測ります。
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
結果は指標×ケース×方式ごとに保存し、比較基準との差を表示します。原音はUTMOSv2のみです。平均の総合点は作りません。

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

## 2026-10-14更新: 現行の既存方式比較の保存出力

この更新は測定を行わず、現行mainの静的解析だけの開発方針へ合わせたものです。
当初の確認欄・レビューにある少数音声、ERB自己比較、CLI起動等は当時の記録であり、今回再実行した結果ではありません。
今後、原音 `identity` はUTMOSv2予測MOSだけを測定します。SCOREQ・ViSQOL・ECAPA・ERBで原音と原音を自動比較する行は作りません。
各再合成出力を原音と比較する通常の参照型評価は維持します。

現行の標準入口は [REFERENCES.md](REFERENCES.md) の `vocoderbench.reference` です。保存先を追加評価へ渡します。
以下は後日の研究実行用で、このPRでは実行していません。

```sh
uv run --locked python -m vocoderbench.quality \
  --reference-run runs/references-120 \
  --assets configs/quality-assets.example.json \
  --metrics utmosv2 speaker_ecapa erb \
  --repetitions 5 --threads 4 \
  --output runs/references-120-quality-001
```

- 入力は `results.json`（schema_version 5）、それと一致する `contract.json`、原音の `inputs.json`、`inputs/<case>.npy`、`native/<method>/<case>.json` と同名の `.npy` です。現在の実装は `status.json` や出力WAVを保存する形式ではありません。
- NPYは全長の保存音声です。公開済みの短い音声例や共通先頭区間から全長を復元せず、公開HTML/JSONだけでは追加計測できません。NPYのない状態は測定不能として記録します。
- 選択方式とケースは元の契約から取得します。欠落した方式出力や失敗行を除外せず、予定行を残します。原音・出力の記録hashを読み込み時に照合し、原音は契約のPCM hashも照合します。
- 比較基準は元の `comparison_reference` を使い、正式な開発ベース指定 `formal_base` は別にそのまま保存します。既存方式のみの標準比較は通常WORLDが比較基準、formal_base.methodはnullです。現HNMを明示併記した比較では保存時のHNMが比較基準ですが、現在のBASELINE.jsonから選び直しません。
- 元の契約、ソース・入力・モデル識別子、seed、各方式の出力記録を保持します。追加評価の反復は同じ保存音声への評価器反復であり、元の解析・合成時間や合成seed反復を置き換えません。
- 参照型指標はネイティブ標本化周波数と原音が不一致、または全長が不一致なら値はnullです。追加評価の共通入力処理は再標本化・切り詰め・ゼロ埋め・整列をしません。元の比較にある `common_prefix` の補助値も転記しません。
- UTMOSv2は非参照なので原音を読まず、各出力の固有標本化周波数・全長だけで評価します。原音についても同じ単一音声のMOSだけを残し、原音対原音の自己差分は測りません。1秒未満・無音等の適用条件は維持します。元のMOSは削除・変更・流用せず、このPRで再測定もしません。

`--benchmark` は従来の開発候補比較の `waveforms/<case>/<method>.npy` を読む互換入口として残します。
現在の標準7方式や現HNM併記のネイティブ保存出力には `--reference-run` を使います。
既存benchmark内の追加既存方式は別の `references/` 以下に保存されるため、必要ならその実行先へ `--reference-run` を別途指定します。
任意方式は引き続き `--manifest` で指定します。例の `baseline` は比較差の基準であり、`formal_base: null` は開発ベースを指定しない意味です。

## 曲線への品質証跡の受け渡し

追加評価は常に `quality-evidence-index.json` と、対象音声ごとの `quality-evidence-<digest>.json` を出力します。
`digest` は `[case, method]` のJSON（UTF-8、ensure_ascii=false、キー整列、空白なし）に対するSHA-256です。
ユーザー指定IDをパスへ直接連結せず、同じcase・methodは同じ相対名になります。各実行は新規出力先を要求するので過去の証跡は上書きしません。

一覧の形式は次のとおりです（値は書式説明で、実測結果ではありません）。

```json
{
  "schema_version": 1,
  "points": [
    {
      "case": "speech_001",
      "method": "world_harvest",
      "quality_evidence": "quality-evidence-<digest>.json",
      "audio_path": "/path/to/output.npy",
      "audio_sha256": "<実ファイルのSHA-256、取得できなければnull>",
      "scores": {"predicted_mos": "not_configured"}
    }
  ],
  "path_base": "追加評価の出力ディレクトリ（この一覧と同じ階層）。利用側manifestからの相対パスへ直して指定する。"
}
```

各証跡ファイルの中核は、PR #30の `assessment.curves.evidence` が読む次の形式です。

```json
{
  "audio_sha256": "<評価した出力ファイル全体のSHA-256>",
  "scores": {
    "predicted_mos": {
      "status": "not_configured",
      "value": null,
      "evaluator": "vocoderbench.quality_backends.UtmosLocal",
      "configuration_sha256": "<評価器の設定・モデル来歴等のSHA-256>",
      "unit": "predicted MOS"
    }
  }
}
```

- 対応はUTMOSv2→`predicted_mos`、ECAPA→`speaker_similarity`（unitは`cosine`）だけです。ViSQOL・SCOREQ・ERBをMOSや話者類似度に名前替えしません。
- 元行が `measured` の場合だけ `status: ok` と初回値を保存します。`partial_failure`、`failed`、`unavailable`、`not_configured`、`not_applicable` 等はその状態とnullを残します。要求しなかった指標はscoresへ入れません。
- 評価器設定のhashは、評価器クラス、設定値、読み込めたモデル・設定ファイルの実hashと上流版、評価ソースhash、依存・環境、スレッド、反復数、初回値選択・入力条件を識別します。初期化秒数や測定値はhashへ混ぜません。初期化できなかった評価器はモデル来歴がnullのままで、実モデルを確認済みと偽りません。
- 証跡には完全な `configuration`、`source_metric`、`direction`、元結果の行番号、理由、`initialization_seconds`、`measurement`（初回と各反復）も保存します。初期化・初回・反復の範囲、値の方向、採点・集約規則は変更しません。
- 元行を欠測ごと落としません。音声が存在せずhashを取得できない証跡も一覧にはnullで残しますが、その証跡を曲線へ有効入力として渡すことはできません。
- 曲線manifestの各pointへ、一覧で対応を確認した `quality_evidence` パスを指定します。そのパスは曲線manifestから解決できる位置へ直し、`output` は同じバイト列の音声を指してください。NPYをWAVへ変換するとhashが変わるため、その証跡を流用しません。
- 曲線の要求指標名は `quality_metrics: ["predicted_mos", "speaker_similarity"]` です。人工信号への音声品質評価、条件途中での評価器変更、音声hash不一致はPR #30側の既存適用条件に従います。渡すファイルがあるだけで全指標の測定完了とは扱いません。
- 参照距離SCOREQ・ViSQOL・ERBは無編集再合成用です。曲線に渡す非参照MOSと固定参照の話者類似度は、各編集点が評価器の適用条件を満たす場合に限ります。長さ変更を伴う編集や異なる録音間補間のためにECAPA等の同一長・同一標本化周波数の制約を緩めてはいません。対象・参照の意味が一致する条件だけを選びます。

## 結果の保存と公開

追加評価の実測後は、元の比較の `experiment.json` の `supplements` へ新しいID・日本語title・`results/新しいID` のpathを登録します。
主比較の `runs` や保存済み `results.json`、HTML、判断を上書きせず、主比較の固定集合・平均へ追加評価を混ぜません。
公開用補助ディレクトリは直下のHTML・JSONのみ対応しています。元実行先を丸ごとコピーせず、`results.json`・`summary.json`・`contract.json`・`index.html` と必要な `quality-evidence-*.json` だけを新しい補助ディレクトリへ保存します。品質証跡はこの制約に合わせ同階層のJSONにしています。
`work/` やログのディレクトリ、NPY・WAV、モデルは元実行先に残し、`experiments/.../results/` に入れません。
元の音声付き比較への相対リンクは、そのままの移設で解決する配置を事前に確認してください。配置変更が必要な場合は元のHTML・JSONを保持したまま別の公開用コピーを作り、リンク変更とコピー元hashを記録してください。
公開前に個人音声・モデル・全長音声を含めていないことを確認し、[実験記録](../experiments/README.md) と [公開手順](PUBLISHING.md) に従います。
`quality` は `supplements` の自動登録や公開を行いません。今回、測定・補助結果登録・Pages生成の予行は実行していません。
