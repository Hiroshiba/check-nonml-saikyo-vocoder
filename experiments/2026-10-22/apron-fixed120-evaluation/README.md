# Apronの固定120録音評価：実行前計画

これは採用の審査ではなく、現在の作業ベース Apron（LLSM2 Layer1）の無編集・±3半音を、既存 LLSM2 Layer0 と旧 PML の保存値に照らして調べる研究準備です。**音声生成・品質推論はまだ実行していません。** 旧 PML と Layer0 の当時の識別子や結果は書き換えません。

## 入力と予定数

- `research/pml-package-evaluation-2026-10-16/input-manifest.json` の SHA-256 は `1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193`。16 kHz・40話者×3発話、120件の実bytes/SHA/NPYヘッダーを全件照合してから始めます。manifestの `common_samples` が唯一の固定共通先頭窓です。値から窓を選び直しません。
- manifestで最初に現れる話者順を0番14人（42録音）、1番13人（39録音）、2番13人（39録音）へ固定します。各担当は別出力で、全体で Apron 0/−3/+3 が360波形、Layer0無編集が120波形、合計480波形です。成功しなかった枝も予定分母から外しません。
- LLSM2 `d18cdf02b31819670e3bc23ead933ad9467da06d`、ciglet `895ba9b1c0eabee83d3544208bbc82420efa3206` の正規準備記録と全ファイルハッシュを `current_base.record()` で確認します。Apronは1録音につき解析を一度だけ行い、保存Layer1状態から各decode時に独立したchunkを再構成します。元HMがないことは既存engineが確認します。Layer0は既存 `build_llsm` を用い、解析・復号の前にそれぞれseed 0へ戻し、取得したchunkを必ず解放します。DSP threadは1です。
- nativeの24 kHz全長波形を元dtypeのNPYで保存し、実標本数・bytes・SHAを記録します。16 kHzへの変換は品質工程だけです。元入力の音量補正、位置合わせ、clip、無音除去を追加しません。

## 品質と過去値の扱い

無編集ではUTMOSv2をnative全長、SCOREQ（natural-domain telephone）・ECAPA・eSTOIを旧比較の固定16 kHz先頭共通窓で測ります。編集−3/+3半音はUTMOSv2とECAPAだけをnative全長で測り、ECAPAは元の全入力抜粋と編集音声全長をそれぞれ独立に16 kHzへ変換して比べます。意図した音高編集にSCOREQ/eSTOIの参照忠実度罰則を付けません。無編集のApron/Layer0は各4指標、編集Apronは各2指標で、全体の予定個票は1440件です。品質threadは2です。

品質資産は既存のUTMOS重み・設定2件、SCOREQ、ECAPAの5ファイルをSHAで照合します。モデルの取得・変更はしません。既存 `quality_backends.UtmosLocal`、`EcapaSimilarity`、`ScoreqReference`、`extended_metrics._estoi` の科学処理をそのまま使い、モデル由来の警告、個票の失敗とtracebackを残します。
各個票には採点に渡した参照・出力PCMの標本数とfloat64バイト列SHAも残し、native波形NPYのSHAとは区別します。モデル来歴・資産SHA・ソースSHAを別に固定します。

旧PMLの `pml_fwcep60_lowband_package_v1` とLayer0の `llsm2` には4指標×120件の保存個票があります。旧PMLは歴史的な別方式です。入力PCM・共通窓・出力波形SHA・採点器と重み・前処理・seedとthreadが合う個票だけを別の引用台帳へ入れ、単なる値の一致では引用しません。旧Layer0の保存全長波形120件はこの環境の既知場所で確認できなかったため、今回のLayer0無編集120出力を予定します。過去のLayer0品質値と新規個票は区別します。旧PML無編集の参照指標は固定共通窓、編集ECAPA/MOSは全長という範囲差を保ちます。今回のdriverは旧PMLの評価・合成を再実行しません。

各録音には `attempt-0001` 以降の独立ディレクトリを割り当てます。途中の成功枝は原ファイルのbytes/SHA照合後にだけ再利用し、失敗・中断の原attemptは残します。再測定は明示的な `--retry-failed` のときだけです。上流nativeの保存個票が変わった場合、品質は新しい出力rootで計測し、旧記録を維持します。全体契約が異なる出力rootへの再開は拒否します。`summary.json` は未訪問録音も `not_run` として示し、品質の欠測は値nullと理由に分けます。CLIログは全warningと例外stackを外側へ保存します。終了0は担当の予定個票が全測定済み、終了2は欠測・失敗あり、他の終了とtimeoutは未完了です。旧PML引用や順位は、この工程の成功判定に含めません。

## 実行コマンド（親レビュー後にのみ使用）

このPRは入口の準備だけです。次は固定入力・依存の実パスを再照合し、新しいrun rootを用意してから実行します。以下の `OWNER` は0、1、2をそれぞれ一度指定します。同時実行は資源確認後に最大3担当までとし、品質はnativeの終了後に別工程で行います。`/usr/bin/time -v` のRSSは実測であり、`ulimit -v` は仮想アドレス空間の制限です。

```sh
REPO=/workspace/check-nonml-apron-fixed120-evaluation-20261022
PY=/workspace/check-nonml-saikyo-vocoder/.venv/bin/python
INPUT=/workspace/check-nonml-saikyo-vocoder/runs/fixed120-input-preparation-20261020/inputs
CACHE=/workspace/llsm2-layer1-preparation-20261021-v2/runtime-cache
ASSETS=/workspace/check-nonml-saikyo-vocoder/runs/pml-quality-assets-preparation-20261021-v1
RUN=/workspace/check-nonml-saikyo-vocoder/runs/apron-fixed120-evaluation-20261022-v1
MANIFEST="$REPO/research/pml-package-evaluation-2026-10-16/input-manifest.json"
OWNER=0
mkdir -p "$RUN/evidence/native/$OWNER"
PYTHONPATH="$REPO" VOCODERBENCH_LOG_DIR="$RUN/evidence/native/$OWNER/logs" PYTHONDONTWRITEBYTECODE=1 \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
/usr/bin/time -v timeout --signal=TERM --kill-after=10s 1800s \
bash -c 'ulimit -v 8388608; exec "$@"' _ "$PY" -B -m scripts.apron_fixed120.native \
  --input-manifest "$MANIFEST" --input-root "$INPUT" --runtime-cache "$CACHE" \
  --owner "$OWNER" --output "$RUN/native/owner-$OWNER" \
  >"$RUN/evidence/native/$OWNER/stdout.log" 2>"$RUN/evidence/native/$OWNER/stderr.log"
```

品質は指標ごと、担当ごとに別の新規出力を使います。`METRIC` は `utmosv2`、`ecapa`、`scoreq`、`estoi` の4種類で、それぞれ上の全担当について指定します。UTMOS/ECAPAは担当録音数×4、SCOREQ/eSTOIは×2の個票が予定分母です。

```sh
METRIC=utmosv2
mkdir -p "$RUN/evidence/quality/$OWNER/$METRIC"
PYTHONPATH="$REPO" VOCODERBENCH_LOG_DIR="$RUN/evidence/quality/$OWNER/$METRIC/logs" \
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 BLIS_NUM_THREADS=2 \
/usr/bin/time -v timeout --signal=TERM --kill-after=10s 3600s \
bash -c 'ulimit -v 12582912; exec "$@"' _ "$PY" -B -m scripts.apron_fixed120.quality \
  --input-manifest "$MANIFEST" --input-root "$INPUT" --asset-root "$ASSETS" \
  --native-output "$RUN/native/owner-$OWNER" --owner "$OWNER" --metric "$METRIC" \
  --output "$RUN/quality/$METRIC/owner-$OWNER" \
  >"$RUN/evidence/quality/$OWNER/$METRIC/stdout.log" \
  2>"$RUN/evidence/quality/$OWNER/$METRIC/stderr.log"
```

運用上のwall上限はnative担当1800秒、品質の担当×指標3600秒、terminate後10秒でkillです。nativeのAS上限は8 GiB、品質は12 GiBで、実RSSではありません。新規Layer1保存物とモデル作業領域を含むdisk使用量は測定前の空き容量で確認します。分割・出力先・上限を変える場合は別の計画として先にレビューします。±6 dB、48 kHz、人工10刺激C、独自DSP改善はこの計画に含めません。
