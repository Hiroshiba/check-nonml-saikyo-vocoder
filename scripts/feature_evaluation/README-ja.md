# 固定120音声の特徴評価

保存済みの特徴表現を比較する汎用評価器です。新しい実装として準備・独立静的レビューを行いました。旧環境で失われた実装の復元ではなく、このコードによる科学測定結果はまだありません。

候補固有の係数観測器、解析器、学習用音声の生成routing、実入力、設定、認可、非公開payloadは含めません。公開ファイルは評価基盤だけです。通常の波形品質評価とは別directoryで、実測に使用する凍結済み配置を公開用copyへ移動しません。

## 評価契約

- 独立train120録音・40話者各3件、test120録音・別40話者各3件。音声とsource identityの交差を拒否します。
- 主表現canonical_complex4099、補助amp3075、診断rawcomplex4099、新PML2110を扱います。候補固有の列構築は外部の凍結済み観測器へ渡します。
- ABX尺度は録音ごとの中心化population分散を保存し、録音等重みの総分散で計算します。旧second moment差分は使いません。
- 固定4960 ABX組を変更せず、保存actual timesでtoken区間を切ります。Euclidean DTW、上限200万cell、tie許容1e-12、既存の話者グラフbootstrapを用います。
- Ridgeはalpha=1。録音平均特徴をtarget-valid train録音平均の標準偏差で尺度化します。ABX全frame尺度を転用しません。定数train平均の予測と、高次元・rank・定数列の診断も残します。
- 候補とPMLは同じ測定済み支持で対応比較します。欠測を0にせず、全120/4960の予定分母と失敗を残します。全train120の特徴が揃わないviewではfitを拒否します。
- frame全行列を永続化せず、payloadから逐次観測し、momentsとactual timesを保存します。ABXのframe cacheは2録音です。

## 構成と起動順

同じdirectoryの各CLIをPythonのscriptとして起動します。例：python scripts/feature_evaluation/extract_moments.py --context CONFIG_DIRECTORY --split train --method pml --view pml2110。隣接moduleはscript directoryからimportされます。汎用moduleを独立packageとしてpython -mで呼ぶ形は提供しません。

1. build_input_audits.py：全10区間のcandidate/PML終端receiptと全保持artifactを照合し、全120の入力監査を作成。
2. extract_moments.py：--split trainまたはtest、--method candidateまたはpml、--viewを指定。--targets-only時はmethod/viewを指定せず、既存の独立targetのみ計算。
3. abx_evaluate.py、readout_evaluate.py：同じcontext/method/viewで逐次計算。
4. paired_compare.py：候補viewごとに新PMLと対応比較。
5. public_checkpoint.py：--outputへ明示allowlistのscalar JSONを出力。path、録音ID、payload、tracebackを公開射影しません。未完了はincomplete、値/順位なしで報告できます。

各CLIの入力引数はソースのargparse定義を参照してください。実行用contextにはsource-freeze、settings、明示認可、監査済み入力と表現payload、runtimeが必要です。公開directoryだけでは解析・測定を開始できません。設定や認可例に実private pathを含めて公開しないでください。

## 安全な実行と保存

全科学処理は1threadで逐次実行し、通常品質評価と重ねません。OPENBLAS_NUM_THREADS、OMP_NUM_THREADS、MKL_NUM_THREADS、NUMEXPR_NUM_THREADSを全て1に設定します。source/input/runtime全hashを開始前と終端で照合します。空き5GiB＋active1GiBを最低条件とし、train解析用の容量は別に見積・承認します。

完了momentsはcontractと全hash一致時だけskipします。部分attemptはdirectoryごと保存してから明示手続で復旧し、科学失敗を都合よく再測定しません。signal、メモリ不足、完全性不一致を科学失敗や成功に変換しません。派生moment/target summaryも開始と終端で再照合します。

公開コードの静的確認はASTとcached Ruffのみです。新規テストは実装していません。解析用payloadの永続保全、実行認可、全120の生成完了をこの公開copyで満たしたとは扱いません。
