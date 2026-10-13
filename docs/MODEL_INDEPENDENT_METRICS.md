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

これは「18項目の実モデル評価が完成した」という変更ではない。新しい13項目にも、部分実装・証跡入力・限定された測定器を含む。主観的な自然さ、方式の採用、使用可能な編集幅は人工信号の測定だけから決めない。

導入・校正は段階を分ける。最初は1〜6の再合成評価、次に7〜9・11の制御、続いて13・17の特徴表現を優先し、その他は実際の入力と根拠が整った項目から使う。全18項目を一度に実測する条件にはしない。自然さ・忠実性・制御・特徴表現は別軸として読む。評価用MLはボコーダーの非ML条件とは分け、16 kHzの固定比較や人工48 kHz信号を日本語48 kHz録音での評価済み実績へ読み替えない。

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

### 既知変換による測定研究

`assessment.probes` は既知の音高・ゲイン・時間写像・スペクトル傾斜を与える6条件だけを生成する。各jobに調べる音響的な問いを記録する。ERBは+3 dBの狭帯域入力への感度、ピッチは相対追従と既知F0軌跡への誤差、ゲインは連続振幅変化、局所時間は非一様写像、傾斜は固定帯域、干渉はゲインに対する属性応答を対象とする。

測定研究として目的・対象・条件を固定した場合の入力生成例：

```sh
uv run --locked python -m vocoderbench.assessment.probes --output runs/acoustic-research-inputs-001
uv run --locked python -m vocoderbench.assessment \
  --manifest runs/acoustic-research-inputs-001/manifest.json \
  --output runs/acoustic-research-001 --repetitions 5
```

これは通常の開発確認やCIでは実行しない。研究入力は48 kHz・主に1.2秒の解析的波形で、自然音声の品質、実方式の性能、48 kHz録音の高域再現を証明しない。F0真値は既知の解析式から10 msごとに与え、フレーム時刻への線形補間誤差も限界に含める。雑音RNGは42、jobのseed 0は固定条件の識別ラベルで、独立した複数seedの測定ではない。正式ベースの比較行はないため比較基準は `unselected`、差分はnullとする。

原音ERB自己比較、故意の偽ハッシュ・欠落ファイル・非有限値・短音・長さ不一致等、動作確認専用の生成と再実行手順は削除した。架空ASR記号列・玩具特徴・同点ABX等の確認用生成も含めない。通常の入力ガード、定義域外・失敗・欠測の保存は維持する。終了コードは結果状態に従い、値を0で埋めたり成功へ書き換えたりしない。

2026-10-13の旧15条件・90計算と異常7条件は[当時の記録](../experiments/2026-10-13/model-independent-metrics/README.md)にそのまま保存する。現在の6条件の実測結果として転記しない。今回の調整では入力生成・合成・指標計算・モデル推論を実行していない。

## 共通入力・出力契約

manifestは `schema_version:1`、`baseline_method`、`scope`、`jobs` を持つ。各jobには `id,metric,case,condition,method,seed,speaker,language,style,kind` が必要。kindは `speech` または `artificial_probe`。同一の指標・case・condition・method・seedの重複は拒否する。未知の話者情報を架空の個別話者へ増やさず、未確認であることを同一ラベルとscopeへ記録する。

相対ファイルパスはmanifestのあるディレクトリ基準であり、dataset／sidecar内のパスも同じ基準。ファイル・入力条件・実装のSHA256を保存し、実行中に入力が変わったら停止値を残す。pickleは読み込まない。既存結果ディレクトリは上書きしない。

通常出力は `manifest.json,results.json,index.html,run.log,run-log.json`。終了時に生ログを保存し、そのファイルのSHA256と全文をJSONにも包んでHTMLからリンクする。各回の結果、壁時計時間・プロセスCPU時間、初回、反復中央値・P95・最小・最大を残す。指標モジュールのimport時間は初期化欄、共通import・プロセス起動は対象外。各反復にファイルI/O・ハッシュ・参照解析を含む。ASR／品質モデルの推論、符号化・復号は含まない。失敗までの時間も保存するが成功した指標の実行時間と混ぜない。

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

## #27の品質結果を曲線へ渡す

[品質曲線の入力例](../configs/assessment-quality-curve.example.json)は未実測の雛形であり、ハッシュ風の架空値や実測値は埋めていない。次の順で実際の音声・評価結果を指定する。

1. 無編集・編集音を同じ全長ファイルで固定する。#27の `--manifest` で各編集点を識別できるcase・methodとして列挙し、必要な `utmosv2`／`speaker_ecapa` だけを評価する。各caseにはmanifestが求める比較基準の出力を含める。speaker_ecapaを使う場合は全編集点の話者比較参照を同じ音声にする。SCOREQ・ViSQOL・ERBは編集量曲線の品質点へ自動変換しない。
2. #27は `<quality出力先>/quality-evidence-index.json` の `points` にcase・methodごとの対応を出力する。各 `quality_evidence` の値はquality出力先からの相対パスであり、同じディレクトリの `quality-evidence-<digest>.json` を指す。`audio_path` と `audio_sha256` も照合する。
3. 該当点の `quality_evidence` をassessment manifest基準の相対パス（または絶対パス）へ解決し直して `points[].quality_evidence` に入れる。`output` は品質を測った同一ファイルを指す。WAVへ変換し直すとファイルハッシュが変わるため、NPYを評価した場合は同じNPYを `{"path":"...npy","sample_rate":実際の周波数}` で指定する。雛形の `REPLACE_WITH_...` はindexの実際のパスへ置き換える。
4. 無編集点のamountは0、`reference` はその無編集復号音と同じファイルにする。比較する各方式について同じcase・condition・seedのjobを追加する。例の `comparison-baseline` は実際の比較基準へ変更し、比較基準のjobがなければ方式間の差はnullのままにする。

sidecarは `utmosv2 → predicted_mos`、`speaker_ecapa → speaker_similarity` だけを対応させる。#27の `measured` を `ok` に写し、未設定・失敗・対象外は元の状態とnullを保持する。valueは#27が出力した初回値で、反復平均へ変えない。評価器名・単位・評価器の設定と重み等を識別する `configuration_sha256` を保持し、同じ曲線内で設定が変われば拒否する。SCOREQ距離をMOSと呼んだり、小さいほど良い距離の符号を逆転したりしない。

音声ファイルのハッシュが不明・不一致の場合は、その証跡で測定済みの値を使わない。証跡なしは欠測またはpartialとなり、0点として補完しない。話者指標を意図した声質変更へ一律に要求しない。モデル推論と初期化・初回・反復時間は#27の元結果に残り、assessmentの曲線計算時間へ合算しない。

## 固定比較からの入力と実験登録

1. `vocoderbench.reference` の実行先を保存する。正式な入力は `inputs.json` とそこで指定された原音NPY、方式ごとの `native/<method>/<case>.json` とNPYである。公開用の `results.json`・短い試聴音声だけでは全長の追加測定はできない。固定120件の現在の記録には現ベースと既存方式があるが、既存方式のみの別実験へ現ベースを後付けしない。
2. 追加品質は #27 の `vocoderbench.quality --reference-run` で同じ保存先から読める。既存の `--benchmark` は従来のbenchmark保存形式専用。参照あり指標で原音／方式の標本化周波数・長さが違う場合は、追加品質側で黙って合わせず欠測を残す。非参照のUTMOSv2は各出力自身の標本化周波数で評価する。評価用前処理を研究で採用する場合は、その音声・条件・ハッシュを別版のmanifestへ保存する。
3. assessment側の `reference`・`output` には同じ全長WAV、または標本化周波数を明示したNPYを指定する。再合成の聴覚帯域距離では原録音と復号音、制御追従と編集量0の参照ではその方式の無編集復号音を使い分ける。reference比較は無編集音しか生成しないので、編集曲線には別工程で保存した実際の編集音・操作条件が必要。
4. `baseline_method` は当時の比較基準を明記し、比較する現ベース・既存方式ごとに同じcase・condition・seedのjobを用意する。対応行がない差はnullのままにする。元の `formal_base`、比較条件、元レポートの場所とハッシュは研究記録に残し、現在のbaseへ置き換えない。
5. 全長入力・モデル・生ログ・品質sidecar／証跡と実行結果一式は研究用保存先に保持し、追加評価は毎回新しい `runs/` へ出力する。Pages用の補助先 `experiments/YYYY-MM-DD/<theme>/results/<id>/` は平坦なHTML・JSONだけを許可するため、実行先を丸ごと移さない。assessmentからは完了時の `results.json,index.html,manifest.json,run-log.json` をコピーする。生の `run.log`・NPY・WAV・下位ディレクトリは補助先に入れず、完全保存先とハッシュをテーマのREADMEに記す。私有データや絶対ローカルパスを公開してよいか確認し、公開用の加工が必要なら元の研究記録を保持したまま別物として明示する。公開manifestは条件の記録であり、記載パスの実入力までPagesに同梱されたことを意味しない。新たな音声取得や推論はこのPR調整では行っていない。
6. 同じ比較の補助評価は元テーマの `experiment.json` の `supplements` に `id,title,path` を登録する。主比較の `runs` や母集団平均へ混ぜず、テーマのREADMEから元比較と追加評価の両方へリンクする。例：

```json
{"id":"additional-metrics-001","title":"同じ保存音声の追加評価","path":"results/additional-metrics-001"}
```

各補助先には `results.json` が必要。HTMLがあれば併せて公開される。別日の継続研究は新しい日付のグループから元比較へリンクする。元比較が公開している試聴音声へのリンクを補助記録の説明に付け、音声を再合成しない。実際の研究結果・公開の工程は [記録の構成](../experiments/README.md) と [公開手順](PUBLISHING.md) に従う。サイト生成の予行・リンク検査を今回の開発確認として実行しない。
