# PML追加品質評価の再実行

この入口は測定後に作業ディレクトリを引数化した公開用版です。掲載済み測定を実行したファイルそのものではありません。合成・指標の数式は既存 `vocoderbench` に委譲します。変更点と元driverのSHAは `portable-driver-provenance.json` を参照してください。静的構文確認とcached lintのみ実施し、公開用CLIで120件を再測定してはいません。標準benchmarkや全補助評価の一括自動対応を意味しません。

## 入力と環境

リポジトリルートから実行します。Python 3.12、`uv sync --frozen` で本体の固定依存を導入します。追加品質用の依存は次の固定ファイルから導入します。

```sh
uv pip install --python .venv/bin/python -r scripts/pml_evaluation/quality-requirements.txt
export PYTHONPATH=.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
```

以後は `.venv/bin/python` を使い、自動syncで追加依存が削除されないようにします。掲載済み測定は既存のCPU環境を再利用しており、lockからの環境再構築と完全同一ではありません。特にsetuptools等の差は公開runtime記録に残しています。

原音は固定120件の公開manifestに対応する16kHz mono float64 NumPy配列です。音声ファイル・モデルはこのレポートに同梱しません。取得先の規約を確認し、native入口の説明に従って準備してください。`run_native.py` の出力をそのまま後続の `--run-root` に渡します。共通窓は旧8方式の公開最短先頭窓で固定し、値に応じた窓変更はしません。入力SHA不一致時は停止します。

## 評価モデルを取得

```sh
RUN=runs/pml-package-evaluation-2026-10-16
CACHE=.cache/mos
.venv/bin/python scripts/pml_evaluation/prepare_assets.py \
  --run-root "$RUN" \
  --provenance research/all-method-final-2026-10-15/provenance-manifest.json \
  --mos-cache "$CACHE"
```

公式固定URLからSCOREQ・ECAPA・ASRモデル（合計約839MB）、既存 `MosEvaluator.prepare()` でUTMOS重み（約819MB）と設定を取得します。既存キャッシュがあればSHA検証して再利用します。各ライセンスは旧公開provenanceを参照し、モデル再配布はしないでください。ダウンロード時に音声を送信する処理はありません。ネットワークを切って計算したい場合は準備完了後に `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` を指定します。

## 主品質・認識・seed反復

CPUの重い評価は同時に起動しないでください。

```sh
for METRIC in erb acoustic scoreq speaker_ecapa; do
  .venv/bin/python scripts/pml_evaluation/run_quality.py "$METRIC" --run-root "$RUN"
done
.venv/bin/python scripts/pml_evaluation/run_quality.py utmosv2 --run-root "$RUN" --model-cache "$CACHE"
.venv/bin/python scripts/pml_evaluation/run_asr.py --run-root "$RUN" --dataset data/clean_speech_v1.json
.venv/bin/python scripts/pml_evaluation/run_seed_variation.py --run-root "$RUN"
.venv/bin/python scripts/pml_evaluation/aggregate_seed_variation.py --run-root "$RUN"
.venv/bin/python scripts/pml_evaluation/aggregate_available.py --run-root "$RUN" --historical-root research/all-method-final-2026-10-15
```

SCOREQ/ECAPA/音響は固定共通窓120、UTMOSは新native全長120、ASRは全文GTのある55のみ。seed1〜7は保存済み同一payloadを再復号し、seed0と合わせて録音内で集約します。eSTOI/MOSはseed0のみです。UTMOSは毎call seed20261012、fold0・1抽出、2thread。旧8方式のUTMOSは4threadのため演算条件の完全一致やbit一致は主張しません。

各stageは録音単位JSONと契約を保存し、同一引数で再開できます。失敗だけをやり直す場合は測定CLIへ `--retry-failed` を追加します。source/入力/output/モデルの契約変更は別run-rootで行ってください。測定失敗・未対応はゼロ埋めしません。編集・量子化・ABXなどの追加入口はそれぞれの説明を参照してください。

## 保存結果だけを集約する

`aggregate_available.py` は同runのsummaryと旧公開rawだけを読み、推論しません。`aggregate_seed_variation.py` も同様です。元測定用driverと公開版のsource契約は異なるため、掲載済み測定を新CLIの再開入力として偽装しないでください。公開レポートの固定数値再集約には、そのレポートのbuild入口を使います。

速度4欄は保存native-summaryから次のように集計します。

```sh
.venv/bin/python scripts/pml_evaluation/aggregate_timing_cohorts.py \
  --native-summary "$RUN/native-summary.json" \
  --historical-results research/all-method-final-2026-10-15/results.json.gz \
  --output "$RUN/timing-cohorts.json"
```

旧固定70のID・話者・原入力秒を照合し、解析/復号それぞれを集約します。主表示は旧と同じ話者等重みRTFで、総時間/総音声秒のRTFとは区別します。新旧runの速度順位・総合順位・個別試聴例のRTFは作りません。
