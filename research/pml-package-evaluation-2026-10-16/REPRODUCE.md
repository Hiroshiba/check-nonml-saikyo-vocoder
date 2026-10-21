# 正式パッケージ評価の再現入口

## 入口と測定版

この保存結果はPMLパッケージのcommit `48322013c9c97c1cbb857ac1f8323cce6e5ff622` を使った固定120録音、seed 0の研究です。`scripts/pml_evaluation/` はその測定driverを引数化した公開用の入口です。合成アルゴリズムは変更していませんが、公開用driverで全測定を再実行したという意味ではありません。実測時の来歴と公開用driverのSHAを混同しないでください。

`vocoderbench.reference --include-current-base` は標準参照との無編集比較です。`benchmark` は開発候補の比較です。このページの追加品質・制御・表現評価は別の明示的な入口で、標準CLIの実行だけで全項目が自動計算されるものではありません。重い評価は節目に実行します。

## 入力の準備

リポジトリのrootでPython 3.12 / uvを使います。Linuxでは解析依存のビルドにC/C++コンパイラが必要です。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.corpus fetch
uv run --locked python scripts/pml_evaluation/prepare_inputs.py \
  --input-manifest research/pml-package-evaluation-2026-10-16/input-manifest.json \
  --output runs/pml-inputs
```

公式の固定コーパス取得は `data/clean_speech_v1.json` の配布元と利用条件に従います。取得済み音声は非公開のローカルキャッシュに保存してください。公開物には全120音声・モデル重みを含めません。NPY入力は整数PCMからfloat64へ変換した先頭最大6秒、無正規化・無音除去なしです。公開manifestは録音ID、話者、入力SHA、長さ、全方式共通窓を固定します。元波形からの復元をこのSHAで識別し、別音声への置換を許しません。

別の取得先を使うときはprepare_inputsの `--corpus-manifest` / `--corpus-cache` を指定できます。保存済みNPY入力がある場合はそのファイルを `{録音ID}.npy` として入力rootへ置き、次の解析入口がSHAを照合します。

## 新解析・保存・復号

```sh
uv run --locked python scripts/pml_evaluation/run_native.py \
  --input-manifest research/pml-package-evaluation-2026-10-16/input-manifest.json \
  --input-root runs/pml-inputs --output runs/pml-formal
```

出力は `input-contract.json`、`native-contract.json`、`native-summary.json` と `native/{録音ID}/record.json,parameters.pml,wave.npy` です。後続評価はこのrunを指定します。入力・合成ソース・driverのSHAとseedを固定し、同一契約の成功録音は再実行しません。未完・失敗のrecordがある場合は新しいoutputで実行してください。異なるソースの成果を同じrunへ継ぎ足しません。

解析と復号を別計時し、保存/読込I/Oは別記します。warmupや速度反復はしません。BLAS/OpenMPは2thread、1workerで直列実行します。同時に他の重い推論を走らせず、機械条件を記録してください。歴史値と同じ機械での速度優劣を保証しません。FLOAT出力の±1超過は記録し、クリップや正規化で隠しません。

## 環境と外部資源

合成用のNumPy/SciPy/pyreaper/pyworldはrepoのlockを参照します。実測で再利用した品質runtimeとlock環境にはsetuptools等の差があり、保存レポートの来歴を参照してください。予測MOS、SCOREQ、ECAPA、ASRは学習済み評価器を使いますが、合成器自体は非MLです。モデルの版・SHA・前処理を固定し、未取得のモデルを別のモデルへ自動置換しないでください。

ASRは全文正解のある55録音だけが対象です。独立trainの読み出し、音素ABX、ASVには主120とは別の特徴/アラインメント/評定の資源も必要です。取得可能な補助集合を元の計画数へ水増しせず、未対応項目を0誤差として集計しません。

## 追加品質・認識・seed反復

モデル取得、主120の音響/MOS/SCOREQ/ECAPA、55録音のASR、seed 1〜7、既存8方式との順位再集計、固定70/主120の速度集約は [品質再現手順](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/cb1d06f4b0b145e731a4f90644d4c7868321a0e8/scripts/pml_evaluation/QUALITY_REPRODUCTION.md) を参照してください。そこに示す `RUN` を上の `runs/pml-formal` へ揃え、各コマンドに同じ `--run-root` を渡します。旧方式の数値は公開済みのrawから引用し、前処理契約・共通支持が成立する範囲で比較します。

元の実測driverと公開用driverの対応は [native来歴](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/cb1d06f4b0b145e731a4f90644d4c7868321a0e8/scripts/pml_evaluation/native-driver-provenance.json) と [品質来歴](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/cb1d06f4b0b145e731a4f90644d4c7868321a0e8/scripts/pml_evaluation/portable-driver-provenance.json) に記録しています。いずれも公開用の可搬化後に全測定を再実行したものではありません。

## 編集・量子化・ABX・読み出し・ASV

[拡張評価の再現手順](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/cb1d06f4b0b145e731a4f90644d4c7868321a0e8/scripts/pml_evaluation/EXTENDED_REPRODUCTION.md) は `run_extended.py --run-root ... --corpora-root ... --historical-root ...` の入口、実行順、必要な別集合/旧特徴/評定の配置を記録しています。旧方式の全比較を再計算するための非公開入力・復元済み特徴が全てこのリポジトリに入っているわけではありません。必要資源が未入手なら該当ランキングの完全再実行はできず、公開済み保存値の閲覧・集約と区別してください。元driverのSHA、可搬化した箇所、各入力の出典は同手順の来歴/入力一覧へ対応付けています。
