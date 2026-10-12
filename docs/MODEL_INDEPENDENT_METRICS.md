# 方式に依存しない内容・制御・特徴表現の追加指標

本書はAI作成の実装仕様であり、ユーザー指示より優先しない。添付調査の後半で再提案された18項目を対象とする。撤回されたHNM固有の周期内雑音・位相診断を共通要件へ戻さない。

## 実装範囲

`vocoderbench.assessment` は保存済み波形・特徴量・操作条件・評価証跡を読み、13項目を計算する独立CLIである。内部にF0や調波配列を持つことを候補へ要求しない。現ベース、既存比較CLI、依存関係、`USER_INSTRUCTIONS.md` は変更しない。

| 調査の番号 | 入口 | 今回の到達点・未完了範囲 |
|---|---|---|
| 1・2・3・5・13 | 別PR #27 | UTMOSv2・SCOREQ・ViSQOL Audio・ECAPA・人間評定との近傍一致。今回へ複製しない。実資産での校正完了とはしない |
| 4 | `incremental_content` | 保存済みASR出力と既知の正解から増分CER／WER。ASR推論は別工程 |
| 6 | `auditory_local` | 元の標本化周波数のERB間隔帯域誤差、局所P95、指定区間。完全な聴覚モデルではない |
| 7 | `pitch_tracking` | 指定cent軌跡、任意の絶対F0軌跡、指定時間写像、UV・欠測・範囲外件数 |
| 8 | `gain_tracking` | サンプル単位の指定ゲインから期待RMSを作る動的追従。知覚ラウドネスではない |
| 9 | `local_time` | 既知の孤立イベントの局所時間誤差。自然音声の音素境界は未対応 |
| 10 | `timbre_tracking` | 音響的スペクトル傾斜のみ。フォルマント・息っぽさの知覚制御は未校正 |
| 11 | `interference` | ±操作の中央差分と指定期待応答との差。全非対角成分を0へ強制しない |
| 12 | `quality_curve` | 保存済み非参照品質・話者・認識証跡の編集量別曲線。証跡が足りない場合は部分測定 |
| 14 | `phoneme_abx` | 固定距離・明示三つ組の同話者／異話者ABX。同点0.5。公式集計との同値性は未確認 |
| 15 | `attribute_access` | 話者・発話を分離した固定Ridge読み出し。属性別誤差・定数ベース・パラメータ数 |
| 16 | `interpolation` | 保存した補間点の復号音で属性急変・逆行・品質の谷を計算。復号自体は別工程 |
| 17 | `robustness` | 宣言した物理的摂動と保存済み復号音の曲線。全配列への同分散雑音は要求しない |
| 18 | `information_rate` | 実表現ファイルのbytes・bit/sと品質・制御。量子化／符号化／復号は別工程 |

これは「18項目の実モデル評価が完成した」という変更ではない。新しい13項目にも、部分実装・証跡入力・限定された測定器を含む。主観的な自然さ、方式の採用、使用可能な編集幅は今回の人工プローブから決めない。

## 実行

```sh
uv sync --locked
uv run --locked python -m vocoderbench.assessment --list-metrics
uv run --locked python -m vocoderbench.assessment \
  --manifest configs/assessment-inputs.example.json \
  --output runs/assessment-real-001 --repetitions 5
```

例示JSONの波形パス・方式・話者等は実データへ変更する。波形はモノラルWAV、または `{"path":"audio.npy","sample_rate":48000}`。WAVの整数PCMは振幅へ変換するが、正規化、クリップ、再標本化、ダウンミックス、無音切除、自動整列、長さの切り詰めはしない。

追加指標だけの依存は既存のNumPy・SciPyと標準ライブラリ。既存YIN・ログ処理を再利用する。外部モデル・重みの自動ダウンロードや、任意コードの動的実行はしない。

### 再生成可能な人工入力

```sh
uv run --locked python -m vocoderbench.assessment.probes --output runs/assessment-inputs-001
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --locked python -m vocoderbench.assessment \
  --manifest runs/assessment-inputs-001/manifest.json \
  --output runs/assessment-probes-001 --repetitions 5
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --locked python -m vocoderbench.assessment \
  --manifest runs/assessment-inputs-001/failure-manifest.json \
  --output runs/assessment-failures-001 --repetitions 1
```

人工入力は48 kHz・主に1.2秒の正弦波、既知の時間イベント、傾斜付き雑音、記号列、単純な特徴配列。自然音声・実ボコーダーではない。ASR用記号列は音声の認識結果を装わず `synthetic_token_fixture` とする。表現量プローブは8/12/16 bitの実際の波形ビット列であり、ボコーダーの性能結果ではない。

両例は部分測定／対象外を含むので終了コード1になる。成功へ書き換えたり `|| true` で結果を隠したりしない。全jobが `ok` の場合だけ終了コード0。結果HTMLの各行・JSONの理由と、実行ログを読む。これは測定記録を作る研究用CLIであり、assert・pytest・自動音質合否テストは追加していない。

## 共通入力・出力契約

manifestは `schema_version:1`、`baseline_method`、`scope`、`jobs` を持つ。各jobには `id,metric,case,condition,method,seed,speaker,language,style,kind` が必要。kindは `speech` または `artificial_probe`。同一の指標・case・condition・method・seedの重複は拒否する。未知の話者情報を架空の個別話者へ増やさず、未確認であることを同一ラベルとscopeへ記録する。

相対ファイルパスはmanifestのあるディレクトリ基準であり、dataset／sidecar内のパスも同じ基準。ファイル・入力条件・実装のSHA256を保存し、実行中に入力が変わったら停止値を残す。pickleは読み込まない。既存結果ディレクトリは上書きしない。

通常出力は `manifest.json,results.json,index.html,run.log`。各回の結果、壁時計時間・プロセスCPU時間、初回、反復中央値・P95・最小・最大を残す。指標モジュールのimport時間は初期化欄、共通import・プロセス起動は対象外。各反復にファイルI/O・ハッシュ・参照解析を含む。ASR／品質モデルの推論、符号化・復号は含まない。失敗までの時間も保存するが成功した指標の実行時間と混ぜない。

ベースとの差は指標・case・condition・seedが一致し、双方がokかつ同単位のスカラーのときだけ計算する。行列や属性別の結果を総合点にしない。発話間の統計・信頼区間・メモリ計測はこのCLIには未実装。seed・話者等の行ラベルは保持するが、複数seedのばらつきを今回実測したわけではない。

`partial,not_applicable,unavailable,failed,inconsistent_repetitions` を区別する。欠測値はnull。解析成功区間の誤差の隣に分母・測定不能件数を置く。「ok」は実装が指定計算を終えた意味であり、人間知覚への妥当性や低い誤差を意味しない。

## 波形指標の定義と指定項目

**4：内容保持。** `reference,output,transcripts,maximum_reference_cer` を指定。sidecarには `truth,reference_text,output_text,evidence_kind,recognizer,recognizer_revision,language,normalization,reference_audio_sha256,output_audio_sha256` が必要。同じ認識器・前処理で両音声を認識してから保存する。これは利用者の証跡宣言であり、認識実行の独立監査ではない。

正規化は `identity` または `nfkc_casefold_whitespace`。CERはその後ASCII空白を除いたUnicode文字列、WERは `word_tokenization:"whitespace"` が指定された語列のLevenshtein距離／正解長。日本語WERには別工程で固定した分かち書きが必要。句読点を勝手に落とさない。原音CERが事前上限を超えた場合は生の誤り率と増分を残し、primary valueはnull・partialにして品質比較から外す。

**6：局所構造。** 40 ms Hann、5 ms hop、パディングなしSTFTのパワーを40 Hz〜NyquistのERB間隔32三角帯域へ面積正規化して集約。床は `max(1e-14,最大参照帯域電力×1e-8)`。全帯域×フレームの絶対dB差の平均、フレーム内帯域RMSEの系列とP95、帯域別誤差を保存する。床以下同士の差も主平均へ含むので、単一正弦波の+3 dBが主値3 dBになるとは限らない。有効セル数・全セル数を併記する。optional `intervals:[{start,end,label}]` は参照側で事前固定した秒区間。これはgammatoneや知覚的JNDではない。

**7：ピッチ。** referenceは原録音ではなくその方式の無編集復号音。`target_cents` はスカラーまたは `{"times":[0,1.2],"values":[0,300]}`。時刻は出力側。絶対目標を持つ場合は `target_f0_hz` も指定。既存の独立YIN（80 ms窓・10 ms hop、65〜700 Hz、2 kHz前処理）を使用。有声／無声をまたぐ補間を避け、指定写像上の最近傍参照フレームを用いる。測定F0からの相対誤差を真値誤差とは呼ばない。UV・範囲外・未対応端・600 cent超・±1 octave付近の件数を別に保存する。窓内UV境界と急速変化は推定誤差を含む。

長さが異なる場合、`time_map:{reference_seconds:[...],output_seconds:[...]}` は両軸とも狭義単調増加、両波形の開始・終了を覆う。無制約DTWで出力へ都合よく合わせない。

**8：ゲイン。** `target_gain_db` のスカラー／時系列を参照の各サンプルへ掛け、20 ms・5 ms hop RMSと出力を比較。期待RMS>1e-7を有効、出力RMS床1e-12。静かな区間、完全無出力、波形ピーク、振幅1超過の率も残す。時間伸縮とゲインの同時操作は本入口では未対応。

**9：局所時間。** `probe_kind:"isolated_energy_events"`、`event_seconds`、`time_map`、`search_half_width_seconds`、`minimum_peak_ratio` を指定。5 ms移動電力ピークを既知写像の周辺で検出する。探索区間の重複・波形外を拒否。未検出イベントは0 msにしない。イベントの指定写像に対する計測であり、全長が合っただけの成功判定ではない。

**10：傾斜。** `low_hz,high_hz,target_delta_db_per_octave` を指定。40 ms窓・10 ms hopの平均スペクトル電力をlog2周波数とdBで一次回帰。帯域最大から80 dB下の床。音響的傾斜の差であり、未校正のフォルマント値を実装へ混ぜない。

**11：干渉。** `low_hz,high_hz,attribute_scales,sweeps`。sweepは `control,control_unit,delta,control_scale,minus,plus,expected_response`。属性キーは `pitch_cents,level_db,slope_db_per_octave,duration_seconds`。正規化誤差は `(中央差分−期待応答)×control_scale/attribute_scale`。各単位・尺度・期待応答を開発集合で決めて固定する。中央値F0等の全体属性であり、局所的な副作用全てを測るものではない。

## 特徴量と曲線の指定

**14：ABX。** `dataset,feature_weights,distance,distance_calibration_id`、任意で `tie_atol,max_dtw_cells`。datasetは `representation,extraction_revision,items,triplets` を持つ。itemは `id,features,speaker,phone,context`。featuresはフレーム×次元の.npyで、HNM固有フィールドを要求しない。距離は正の固定重みを掛けた `angular=acos(cos)/pi` または `euclidean`。全経路の累積コスト最小DTWの経路長正規化。DTW上限は既定200万セル／対。

tripletは `a,b,x,condition`。A/Bは同じ話者・違う音素、XはAと同音素、三者の左右文脈は同じ。conditionは `within_speaker` または `across_speaker`。同点は0.5。音素の向き・文脈・話者組を層として条件別macroと全体microを保存する。ZeroSpeech／fastabxの全手順との数値一致は未確認。人工的な距離同点を成功0にしない。

**15：読み出し。** 同じdataset形式に `target_units`、itemに `split,utterance_id,targets` を追加し、jobで `targets,ridge_alpha` を固定。splitはtrain/evaluation、話者と発話の重複は禁止。特徴の時間平均、trainのみの標準化、中心化目的変数へのSVD Ridgeを使う。評価側で正規化・重み・alphaを調整しない。学習を用いるのは評価用読み出しであり、非ML条件のエンコーダー／デコーダーを変更しない。

**12：品質曲線。** `control,control_unit,points` と無編集 `reference`。pointsは `amount,output`、任意で `transcripts,quality_evidence`。操作量0の音声ハッシュとreferenceが一致することが必要。`quality_metrics` は `predicted_mos,speaker_similarity` から選ぶ。参照距離SCOREQを意図的編集の劣化罰則へ流用しない。

品質sidecarは `audio_sha256,scores`。各scoreは `status,value,evaluator,configuration_sha256,unit`。configハッシュには重み・版・前処理を識別する設定を含め、同じ曲線内で変えない。人工入力への音声品質は適用外。1・5を実行する評価器そのものは別PR／外部工程であり、このCLIが推論したと表示しない。声質を意図的に変える曲線では話者保存を無条件に要求しない。

**16：補間。** `endpoint_relation` はsame_phoneまたはaligned_utterance、`interpolation_rule,low_hz,high_hz,attribute_tolerances,points` を指定。各pointは `alpha,output,feature_artifact`。0・1・中間を含む最低3点。属性の差分、差分変化、端点線形からの差、許容差を超える逆行を保存する。品質証跡があれば両端点より低い中間の谷を測る。有限点の診断を連続性の証明にはしない。

**17：頑健性。** `reference,perturbation,perturbation_unit,decoder_revision,points`、pointは `amount,output,feature_artifact`。摂動0を含める。入力生成は方式の責任とし、単位の違う内部配列を一律に乱す実装にしない。

**18：表現量。** `reference,serialization_rule,decoder_revision,points`、pointは `configuration,output,feature_artifact`。指定実ファイル全体のヘッダー込みbytes×8／参照秒を保存する。共有辞書や外部補助情報も必要な方式では、それらを含む自己完結したアーカイブをartifactとして渡す。配列要素数をbit/sと呼ばない。

17・18の各pointは任意の品質sidecarと `controls` を持てる。controlsは `metric:"pitch_tracking"` または `"gain_tracking"` と出力・目標等。各point自身の無編集復号音を制御参照にする。品質または制御が足りない場合はpartial。保存されたfeatureとoutputの本当の復号対応は宣言・ハッシュまでであり、このCLIが復号を再実行して証明するわけではない。

## 根拠と確認範囲

添付調査の最新18項目・計測失敗・部分実測の区別を実装要求として読んだ。旧調査の500件確認や198回の旧計測を今回再実施したとは主張しない。実装時には次の一次資料も参照した。

- ZeroSpeech公式の距離・ABX条件: https://zerospeech.com/tasks/task_1/how_to/ 、https://zerospeech.com/tasks/task_1/
- SciPy STFTの窓・境界・padding: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.stft.html
- scikit-learn公式のgroup分離の説明: https://scikit-learn.org/stable/modules/cross_validation.html
- リポジトリ内の独立F0仕様: [既存F0実装](../vocoderbench/metrics.py)、[既存追加指標](../vocoderbench/extended_metrics.py)

新規指標の式・固定条件・集計は本実装の測定仕様であり、上記文献に妥当性が保証された主観品質尺度ではない。自然音声の実コーパス、実方式の編集出力、認識・品質モデルの実資産、既存評定との照合は後続の検証である。
