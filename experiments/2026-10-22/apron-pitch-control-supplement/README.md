# ApronとLayer0の音高操作を同じ条件で比べる補助計画

固定120録音評価の集計を見た後、比較に足りない対照を特定して作った**後発の補助計画**です。最初の評価に事前登録した比較とは扱いません。固定版 `06b6da5e` による元評価は480波形・1,440品質個票まで完了したとの報告を受けています。これは作成時の計画です。その後、固定commit `9440f7e6997c1a6f0262809b88ce5c3b253cc7f9` で240波形・720個票を計測し、欠測0で終了しました。[結果と個票](../../../research/apron-fixed120-evaluation-2026-10-22/index.html)に別枠で掲載しています。元結果・作業ベースApronは変更していません。

## 追加するのはLayer0の編集音声240本と品質720件

入力は[固定120録音のmanifest](../../../research/pml-package-evaluation-2026-10-16/input-manifest.json)の40話者×3発話です。元評価と同じ話者単位の42・39・39録音を3担当に割り当てます。Layer0の−3/+3半音を各録音から1本ずつ、計240波形だけ新たに生成します。音質は、この240波形にUTMOSv2と全長ECAPAを各1回ずつ適用して480件、保存済みのApron無編集とLayer0無編集に全長ECAPAを各1回適用して240件、合計720件を追加します。失敗や欠測があっても、予定分母240波形・720個票を減らしません。

保存済みのUTMOSv2は全条件とも24 kHzの出力全長が対象なので再利用します。Apron編集ECAPAも全長の保存値を再利用します。一方、無編集ECAPAの既存値は16 kHzの固定共通先頭区間だけを評価しました。編集ECAPAの全長値との差から編集の悪化を推論せず、無編集2条件だけ全長で追加採点します。SCOREQ・eSTOI・F0診断、±6 dB、48 kHzは対象にしません。現行の入力は16 kHz、native出力は24 kHzです。

## 解析・保存と比較の境界

[既存のLayer0操作](../../../scripts/all_metrics_llsm_control.py)の `augment_llsm().edit` を用います。新しいDSPやLayer1の補正は加えません。固定入力を24 kHzへ同じ方法で変換し、各録音でDIO・StoneMaskを含むLayer0解析を一度行います。無編集の解析chunkを保持し、そのコピーから−3/+3半音を独立に編集します。解析前と各復号前にseed 0へ戻します。Layer0無編集の元評価では解析chunkが保存されていないため、元出力と同じchunkを編集したとは言えません。新しいLayer0無編集やApron音声は合成しません。

ECAPAは元入力の16 kHz固定全長抜粋と、各出力の全長を独立に16 kHzへ変換した波形で採点します。UTMOSv2は24 kHzのnative全長です。clip、位置合わせ、音量正規化、無音除去を追加しません。品質処理は2 thread、DSPは1 threadとし、元のbackend・資産・seedを照合します。元のnative契約・個票・波形SHA、元品質の個票・資産・実モデル来歴を読み取りで参照し、補助ドライバーのSHAは別に記録します。元の `scripts/apron_fixed120` にファイルを増やすと、そのディレクトリを含む元の `source_hashes()` が変わるため、補助処理は `scripts/apron_pitch_control` に分離しました。

各録音・各符号について、UTMOSv2と全長ECAPAを別々に、①編集後のApron−Layer0、②各方式の編集後−無編集、③その②のApron側とLayer0側の差として読む計画です。元のUTMOSv2とApron編集ECAPAだけを同じ範囲の値として引用します。値が届いても合成指標や新しい閾値は作らず、良い値が出るまで測り直しません。これらは予測MOSと話者埋め込みの変化であり、真F0、生理的な有声・無声、声道形状の因果証明ではありません。

## 五つの仮想役による二巡の設計確認

実在の5人による査読ではありません。第1巡では、音響役が編集済みLayer0対照の欠落、評価役が無編集ECAPAの採点範囲の違いを指摘しました。再現役は元Layer0のchunkが残っていないこと、実装役は元コードのソース契約を変えない別パッケージの必要性を示しました。批評役は、測定済みUTMOSv2とApron編集ECAPAの再測定を避け、得点だけでApronの採否を決めないよう求めました。第2巡では、全員が上記240波形・720個票、元結果の参照SHAと失敗を含む予定分母、範囲をそろえた対応差に絞る形で応答しました。

## 実行前の照合と停止線

このcheckoutには、下の `INPUT`、`CACHE`、`ASSETS`、`ORIGINAL_RUN` の実ファイルがありません。コマンドは**実行例であり、実行・計測はしていません**。開始前に元実行の契約・全波形と品質個票、固定入力・資産・source/runtimeを照合し、親が実パスと保存余地を確認する必要があります。元結果は読み取り専用で、新しいrun rootだけへ出力します。元のソース・結果・日時は書き換えません。

```sh
REPO=/workspace/check-nonml-saikyo-vocoder
PY="$REPO/.venv/bin/python"
MANIFEST="$REPO/research/pml-package-evaluation-2026-10-16/input-manifest.json"
INPUT="$REPO/runs/fixed120-input-preparation-20261020/inputs"
CACHE=/workspace/llsm2-layer1-preparation-20261021-v2/runtime-cache
ASSETS="$REPO/runs/pml-quality-assets-preparation-20261021-v1"
ORIGINAL_RUN="$REPO/runs/apron-fixed120-evaluation-20261022-v2"
RUN="$REPO/runs/apron-pitch-control-supplement-20261022-v1"
OWNER=0  # 1、2についても別の出力・証拠directoryで一回ずつ指定
set -C
mkdir -p "$RUN/evidence/native/$OWNER"
PYTHONPATH="$REPO" PYTHONDONTWRITEBYTECODE=1 VOCODERBENCH_LOG_DIR="$RUN/evidence/native/$OWNER/logs" \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
"$PY" -B -m scripts.apron_fixed120.launch --phase native \
  --cwd "$REPO" --evidence "$RUN/evidence/native/$OWNER" -- \
  "$PY" -B -m scripts.apron_pitch_control.native \
  --input-manifest "$MANIFEST" --input-root "$INPUT" --runtime-cache "$CACHE" \
  --original-native "$ORIGINAL_RUN/native/owner-$OWNER" --owner "$OWNER" \
  --output "$RUN/native/owner-$OWNER" \
  >"$RUN/evidence/native/$OWNER/outer.stdout.log" 2>"$RUN/evidence/native/$OWNER/outer.stderr.log"
```

nativeの各担当を閉じた後、`METRIC` を `utmosv2` と `ecapa` にそれぞれ指定し、各担当につき別出力で実行する想定です。品質は計6起動です。

```sh
METRIC=utmosv2
mkdir -p "$RUN/evidence/quality/$OWNER/$METRIC"
PYTHONPATH="$REPO" PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
VOCODERBENCH_LOG_DIR="$RUN/evidence/quality/$OWNER/$METRIC/logs" \
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 BLIS_NUM_THREADS=2 \
"$PY" -B -m scripts.apron_fixed120.launch --phase quality \
  --cwd "$REPO" --evidence "$RUN/evidence/quality/$OWNER/$METRIC" -- \
  "$PY" -B -m scripts.apron_pitch_control.quality \
  --input-manifest "$MANIFEST" --input-root "$INPUT" --asset-root "$ASSETS" \
  --original-native "$ORIGINAL_RUN/native/owner-$OWNER" \
  --supplement-native "$RUN/native/owner-$OWNER" \
  --original-utm "$ORIGINAL_RUN/quality/utmosv2/owner-$OWNER" \
  --original-ecapa "$ORIGINAL_RUN/quality/ecapa/owner-$OWNER" \
  --owner "$OWNER" --metric "$METRIC" --output "$RUN/quality/$METRIC/owner-$OWNER" \
  >"$RUN/evidence/quality/$OWNER/$METRIC/outer.stdout.log" \
  2>"$RUN/evidence/quality/$OWNER/$METRIC/outer.stderr.log"
```

既存launcherの制限はnativeがアドレス空間8 GiB・1,800秒、品質が12 GiB・3,600秒で、どちらもTERM後10秒の猶予を置いて直接子を回収します。RSS制限との混同はしません。各試行には追記専用の開始・枝・終了記録と全警告・tracebackを残し、中断や失敗からの再実行は `--retry-failed` の明示と新しい試行番号を必要とします。片枝だけ成功した場合もその枝を採点し、失敗枝は欠測として残します。品質契約は補助nativeの最新試行と枝原本のSHAに結び、native再試行後に旧品質値を再利用しません。実行前の照合で停止した場合は外側の証拠を残し、個票完了とは数えません。元の試行は不変に保ち、成功・失敗・未訪問を予定分母から落としません。全240波形と720個票の予定工程を失敗も含めて閉じた時点で停止し、改善が得られるまで延長しません。
