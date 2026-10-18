# 固定区間の多指標評価

この入口は既存の評価関数へ凍結波形を渡す。候補の合成実装をimportしない。従来のprivate入口と同じSHAの復元ではなく、新しい評価・保存sourceである。

## 開始前

固定120の計画、全10区間、主71軸と編集8軸、入力/合成source/評価source/runtime/model/前処理の親manifestを凍結する。入力は全長Nを維持し、計画のcommon_samplesは既存8方式の共通先頭窓を保持する。現baseはPML package版。過去metadataにある旧HNM/pending採用状態を新しい比較基準へ転載しない。

生成threadは候補1、PML/WORLD2、品質2。process初期化・I/O・codec計時を分け、異なる実行方式を同一速度条件と呼ばない。原音MOS120も新環境で測る。torch2.8と旧pilot2.5の同値性を主張しない。

品質認可JSONはapproved=true、run_plan_sha256、evaluator_sha256、chunk_ids（今から処理する1区間だけ）、stage_idsを要求する。保存まで確認した後で次区間の認可を作る。planのhashを書き換えて既存結果へ流用しない。

## 波形manifest

候補/PML/WORLD各生成receiptの全12件・条件・source/runtime・成果物SHAを検証し、freeze_chunk_wavesでprivate品質manifestを作る。引数は --plan --chunk --inputs --input-root --receipts --output。receipts JSONは方式ID→{path,sha256}。pathはそのJSON所在directoryからの相対、またはprivate絶対path。

候補nativeはCartesian q0だけ。直接native decodeは参照用の費用として区別する。WORLD編集はunsupported、生成失敗も具体的状態のまま残す。全候補のN/SR/float64/有限性を照合する。

## 評価

repo rootから `uv run --locked python -m scripts.chunk_evaluation.run_metrics` を使う。CPU品質環境を別途固定する場合は、そのPythonで同じmoduleを起動する。

共通引数は --plan --chunk --manifest --bindings --assets --output --authorization。run_metricsは --metric acoustic / erb / scoreq / utmosv2 / speaker_ecapa を1つずつ直列実行する。nativeが既定。acoustic/ERB/SCOREQ/native ECAPAは計画の共通先頭窓、UTMOSは全長。短い出力に合わせて窓を縮めない。

編集は --conditions pitch_minus3 pitch_plus3 と --metric pitch / utmosv2 / speaker_ecapa。pitchは同じ方式のnative全長を参照し、編集ECAPAは原音全長、編集MOSは出力自身の全長を測る。編集音へ原音STFT/eSTOIを主品質軸として追加しない。

ASRは run_asr moduleへ共通引数と --dataset を渡す。公式正解が全文を覆う55録音32話者だけ。残65は対象外。原音CERゲート0.20を維持し、別の認識器や正規化へ置換しない。

## 中断と科学失敗

既終端の科学失敗を再測定で救済しない。通常再起動は既存validated receiptを再利用して推論をしない。OSError/MemoryError、CPU割当不能、契約不一致は運用停止としてstage未完を保つ。

運用中断のみ、全保存artifactのhashを確認したroot監査済み --resume-authorization で別attemptへ再開する。許可はplan/chunk/stage/prior_attempt、classification=operational_interruption、resume_unfinished_only=true、全artifactsを指定する。過去terminal個票は成功/失敗とも保持し、未完分だけ続ける。ASR認識も再認識しない。モデル初期化の科学失敗は再開後も引き継ぐ。

## 逐次保存と最終集約

build_axis_rowsへ --plan --chunk --receipts --output を渡し、全stageのsummary/個票/receiptを結合して既存71軸＋編集群へ展開する。自由文・絶対pathを公開JSONへ全転記しない。

chunk_checkpointで公開固定列だけを保存する。区間完了は全体完了ではない。途中順位・採否を出さず、全予定ケース×軸の状態を保存する。全10区間が確定した後だけaggregateへ渡し、話者等重みとPML対応差、共通支持・区間・順位を計算する。数値のない行をゼロ誤差にしない。

公開対象は純粋評価code/schema、公開計画と小さな数値・失敗・来歴記録だけ。privateの波形manifest、bindings、raw traceback、候補実装、完全payload、原音全体、モデル、保存サービスIDはGitへ入れない。短音声の掲載は別の出典・権利確認後に行う。
