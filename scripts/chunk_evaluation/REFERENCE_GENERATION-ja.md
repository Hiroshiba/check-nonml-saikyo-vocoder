# 現PML・固定WORLDの区間生成

本入口は既存科学APIへの公開可能な経路整理で、候補実装を含まない。PMLはscripts/pml_evaluation/run_native.pyと同じencode(seed=0)→save→load→decodeの順序を使う。旧120件一括CLIを12件で呼ばず、区間保存・現在のbase識別・明示decode seed0・immutable attemptsを追加したため、旧driverそのものを実行したとは記録しない。

PMLのnative/-3/+3は毎回、同じ元解析の保存済みパラメーターを読み込む。±3は編集後の独立payloadも保存・再読込してから復号する（元公開run_editsの直接decodeからの保存経路拡張）。編集間の連鎖、編集音声の再解析、クリップ、振幅正規化、長さ補正をしない。WORLDは固定source/共有libraryを用いたnativeのみ。WORLD編集は下流で未対応として表示する。

## 起動条件

rootが共通run-planを凍結し、実source/入力/runtime/モデル/前処理の親manifestとbindingsを作る。runtime親manifestにはdsp_python_prefix、quality_python_prefix、world_library_path（manifest親基準または絶対）と実files一覧が必要。PMLの全source、WORLD adapter/lock、BASELINE.json、元run_native.py、このroutingとchunk_contracts.pyをgeneration親manifestのfilesへ含める。

--inputsはcaseをキーとする辞書で、各行にspeaker/path/samples/sample_rate/expected_npy_sha256を持つ。pathは--input-root基準。全120件の順序と入力SHAは共通計画と照合する。

実行許可JSONはapproved=true、run_plan_sha256、generation_sha256、chunk_ids、stage_idsが必要。stage_idsはpml-generation/world-generation。許可JSONを作る操作はrootの実行判断後に行う。コード・計画の変更は新しい凍結・許可を必要とする。

```
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 \
  "$DSP/.venv/bin/python" -m scripts.chunk_evaluation.reference_generation \
  --plan "$PLAN" --bindings "$BINDINGS" --inputs "$INPUTS" --input-root "$INPUT_ROOT" \
  --authorization "$AUTHORIZATION" --output "$OUTPUT" --chunk chunk-01 --method pml
```

WORLDは--method world_harvest。区間末の品質評価と公開checkpoint/private成果物保存確認を親が行ってから次区間を許可する。科学処理は常に1つずつ実行する。

## 保存と再開

各stageのattempt-NNNは作成後に上書きしない。個別の科学APIで明示的に発生したValueError/FloatingPointError/RuntimeErrorだけを個別失敗にする。入力破損、I/O、環境不足、契約不一致、メモリ不足、プロセス中断は区間全体の運用中断で、validated_endを発行しない。Native crashはPythonの記録を残せない場合があるが、未終端attemptを成功・科学失敗へ変換しない。

終端済みattemptは科学失敗があっても検証してそのまま返す。科学失敗の救済再試行はしない。--resume-interruptedは運用中断後の新attemptを作り、保存済みのcase/encode/条件の終端記録を成功・科学失敗ともにSHA検証して引き継ぐ。未終端stageだけを実行する。旧部分attemptを上書きしない。

解析/編集/復号/入力読込/payload保存・読込/波形保存のwall・CPUを別々に記録する。保存元パラメーター、全120録音のencode特徴量shape/dtype/byte SHA、実payload bytesを残し、後段の表現評価に渡す。候補1thread、対照2thread、品質2threadの条件差を明示し、速度順位を作らない。

終端receiptはschema2のpml-generation（36条件）またはworld-generation（12条件）。rowsの成功waveはpath/SHA/N/SR/dtype、失敗はreason_codeを持つ。全pathはprivate領域で絶対pathを許す。公開checkpointへの直接転載は禁止。元波形の共通窓はplanから保持し、生成自体は入力全長。

現在の確認はAST・cached lint・独立静的review。試験信号、動作確認用音声、科学runは未実行。
