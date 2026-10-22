# pYIN のフレームごとの F0 支持を調べる計画

**状態：設計・コードの静的確認待ち。科学処理は未実行。** Apron の方式や正式ベースは変更しない。固定した pYIN 状態モデルの内部で、各フレームの無声状態全体と、有声488音高ビンそれぞれにどれだけ周辺確率があるかを調べる。これは F0 の正解、声の生理的有声、音声品質の判定ではない。全経路の一点確率や、音響的に異なる二本目の最適経路は今回求めない。

## 固定入力とモデル

既存 `research/pml-package-evaluation-2026-10-16/input-manifest.json` の120録音・40話者と、照合済み16 kHz mono float64 NPYだけを使う。既存の42/39/39話者非重複分割を変えない。`scipy.signal.resample_poly(x, 3, 2)` を一度適用し、連続24 kHz float64を pYIN に渡す。正規化、無音除去、trimming、補間は行わない。固定引数は `sr=24000, fmin=60, fmax=1000, frame_length=2048, hop_length=120, center=True, pad_mode='constant', fill_na=0, n_thresholds=100, beta_parameters=(2,18), boltzmann_parameter=2, resolution=0.1, max_transition_rate=35.92, switch_prob=0.01, no_trough_prob=0.01`。範囲と5 ms hopがApron入口と数値上同じでも、推定器・解析窓は同一ではない。

期待値は488有声ビン、無声を含む976状態、録音別414～1201フレーム、全123307フレーム。実値が違えば記録して失敗とし、時計を合わせるために補間しない。Python 3.12.14、NumPy 2.3.5、SciPy 1.17.0、Numba 0.68.0、librosa 0.11.0、既存入力helperとlibrosa実ファイルのSHAを開始時に照合する。librosa 0.11.0公開sourceの参照commitは `af8c839fb15317fa2712ea66e7a22da6a9267b32`。インストール済み `core/pitch.py` と `sequence.py` の実バイトからGit blob SHA1を計算し、公開commitのblob ID `195275311c80b4365e8e4d7e32da310696b4ec95` と `478da5b4f682533695ab7d092a6404462343f558` にそれぞれ一致することを読取りで確認した。この二ファイルだけの同一性であり、wheel全体のcommit来歴の証明ではない。実行時にはSHA256とblob IDを再照合する。上流では候補ビン割当て後にinclusiveな上限クリップがあるが、この入口ではクリップ/衝突件数を取得できない。件数は「未測定」とし、捕捉した因子を修正しない。

抽出は公開 `librosa.pyin` を各録音に一度だけ呼ぶ。内側の単一 `sequence.viterbi` 呼出しで実際の観測因子 O、遷移 T、初期 pi と経路をコピーし、元関数へ同じ引数を委譲して `finally` で復元する。公開 F0、voiced_flag、framewise voiced_prob も保持する。T/piはownerごとに最初の録音から一度だけ保存し、以後の各録音の実因子と比較する。異なればその実因子を別原本として保存して停止する。これは並列owner間の共有書込みを避け、同じTを120回保存しないためである。

## 保存因子だけによる周辺化

librosa `sequence.py` のViterbi入口と同じ `epsilon=librosa.util.tiny(O)` を使い、`u=log(O+epsilon), L=log(T+epsilon), r=log(pi+epsilon)` とする。公称ゼロ遷移にも `logepsilon` の重みがある。有効な条件付きモデル内部の支持であって、校正された物理的確率とは扱わない。各行先で公称正値の入辺集合 E と**厳密な補集合** C を分ける。Eの重みは保存された `log(T+epsilon)`、Cの重みは `logepsilon`。両voicing blockに同じ連続音高区間があることを、Tと転置Tの両方向で実因子から確認する。prefix/suffix対数和で補集合を求め、Eへ一様epsilon項を重ねて加えない。転置Tを行正規化しない。

前向き `alpha[0]=r+u[0]`、以後 `alpha[t]=u[t]+F_T(alpha[t−1])`、`logZ=logsumexp(alpha[last])`。後向きは `beta[last]=0`、`beta[t]=F_(T転置)(u[t+1]+beta[t+1])`。`loggamma=alpha+beta−logZ` をfloat64で求める。固定順の対数和、非有限値検査、全警告を残す。各フレームの有声全量・無声全量の対数値、`logaddexp`正規化のずれと線形質量のずれをそのまま保存し、再正規化・clippingはしない。異なる密な縮約順とのビット一致も、厳密誤差包絡も主張しない。

有声**対数**周辺量の最大ビンを選ぶ。同値なら番号の小さいビンを使う。線形化後のunderflowによる偽の同値を避けるためである。各フレームでこのビンからの符号付きoffset（1ビン10 cent）へ、**無条件**の有声質量を移す。録音内では全フレーム数を分母にし、物理的に存在しないoffsetは0質量のままにする。全120の集計はまず各録音の平均を作り、その120録音を等重みとする。失敗が1件でもあれば「全120平均」は利用不可とする。別のframe加重集計は作らない。±1200 centは図示時の幾何学的目印であり、octave誤りの分類ではない。全経路joint候補や独立した候補経路を周辺量から捏造しない。

Apronの元 `06b6da5e` runに残るLayer1配列のframe field0は、LLSM後の改良済み点F0である。公開済み元レポートの `provenance.json` 原SHAと記録済み測定commit、元owner契約の全固定source hash・入力manifest・解析条件を照合してから、元16k入力SHA、元24k float64入力SHA、frame数、config0/1、float32で保存されたhop=`float32(0.005)`、整数 `frame_index × 120 / 24000` 秒を照合する。float32の0.005をfloat64の0.005と直接比較しない。正のApron値がpYIN範囲外でもclampせず、文脈上の範囲外件数とする。欠落や不一致があればoverlayを詳細理由付きで利用不可にし、主たるpYIN周辺支持まで失敗にしない。後日の図は既定の公開2録音 `librispeech_1089-134686-0008` と `librispeech_1188-133604-0003` だけで、既公開の原音・Apron試聴へリンクする。新しい音声やMOSは作らない。

## 五役二巡の設計確認

第1巡：確率モデル役はepsilon込み全状態周辺化を要求。実装役は密な前後向きの費用と公称正値/補集合の分離を指摘。音声物理役はモデル内支持を雑音エネルギーや真の有声と分離。評価役は120録音すべてと元ビン分布の保存を要求。批評役は、極小の隣接差と系列長で左右される「全経路の一点質量」を音響候補の十分性の代理にしないと指摘した。

第2巡：実Tから両方向の区間を検証するepsilon-aware forward/backward、無声全量と無条件有声ビン量、閾値なしのmodal-offset要約を採用した。Apron既存点トレースは時計と原本を照合した文脈表示に限る。密なViterbi自体は元 `librosa.pyin` 内で残り、固定120全体で約1173億の前状態演算という静的見積りになる。実所要時間は未測定。新codec・品質改善・真F0精度の主張はしない。

## 保存量、終了条件、将来の公開範囲

入力からは重複音声を保存しない。Oは最大合計 `123307×976×8=962781056 B`、有声対数周辺配列は `123307×488×8=481390528 B`。ownerごとのTは各 `976×976×8=7620608 B`、alpha最大は約9.4 MBの一時メモリで、保存しない。これに元F0/経路/無声量/記録/原本SHAを加えて新runの全保持量を2 GiB以内に制限する。大きな `time×976×976` 配列は作らない。ファイル/各録音/owner証拠を保存し、容量超過時は原本を削らず失敗として止める。lossless NPYのOと有声対数周辺配列はローカルのみ。将来の公開候補は120録音すべての各フレームUV/V支持、各録音の全offset平均、録音等重みの全120平均、失敗・数値診断・設定とローカル配列SHA。図は前述2録音に限る。公開は**別ターンの判断**で、今はGitHub/Libraryへ実結果を送らない。

抽出成功原本を解析前に閉じ、全件成功・終端summaryと原本全件SHA付きsealが揃ったownerだけを解析する。共有T/piの固定契約違反ではその後の録音を開始せず、未実行数と元失敗証拠を残す。要約も終端済み解析ownerとsealだけを読む。録音失敗をゼロ支持として補わず、未実行件数と分母を別々に示す。有限な対数値を線形化して0になった件数と、構造上の `−inf` からの0は別に記録する。観測因子、警告、stack、外側全stdout/stderr、実exit・signal・回収、各fileのbytes/SHAを新規run内へ保持する。勝手な再試行、閾値調整、警告切捨てはしない。各科学子は1 thread/8 GiB address-space、抽出1800秒・解析3600秒、TERM後10秒でKILLし唯一のlauncherが回収する。4CPU/16GiB環境では同一runのlockで最大2子に制限し、開始前に空きディスクと`MemAvailable`がそれぞれ4 GiB以上か確認する。2 GiBは新run全体の保存目標で、外側launcherは稼働中も約2秒間隔で実容量を観測し、超過を検知した子を停止・回収する。観測間隔と最終receiptの分だけ超過し得るため、絶対上限や全失敗ログの閉鎖を保証しない。原本は削除・切捨てしない。

## 将来の実入口（今は実行しない）

親の別判断と静的レビューの後、新しい `RUN` と各phase/ownerの証拠領域を作る。`INPUT_ROOT` は固定120 NPY、`ORIGINAL_RUN` は `apron-fixed120-evaluation-20261022-v2` の保存済みrun。全phaseで `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=VECLIB_MAXIMUM_THREADS=BLIS_NUM_THREADS=1`、`PYTHONDONTWRITEBYTECODE=1`。本番の各コマンドを独立した新規 evidence directory で一度だけ起動する。launcherの `--run-root` は2 GiB保存上限の対象で、証拠・抽出・解析・要約をすべて含む。

```sh
PY=/workspace/check-nonml-saikyo-vocoder/.venv/bin/python
REPO=/workspace/check-nonml-apron-f0-marginals-20261022
MANIFEST="$REPO/research/pml-package-evaluation-2026-10-16/input-manifest.json"
INPUT_ROOT=/workspace/check-nonml-saikyo-vocoder/runs/fixed120-input-preparation-20261020/inputs
ORIGINAL_RUN=/workspace/check-nonml-saikyo-vocoder/runs/apron-fixed120-evaluation-20261022-v2
RUN=/workspace/check-nonml-saikyo-vocoder/runs/apron-f0-marginals-20261022-v1
# 親の起動承認後だけ、RUNが未存在であることを確認して作成する。
mkdir -p -- "$RUN/factors" "$RUN/analysis" "$RUN/compact" "$RUN/evidence"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
$PY -B -m scripts.apron_f0_marginals.launch --phase extract --run-root "$RUN" --evidence "$RUN/evidence/extract-0" --cwd "$REPO" -- \
  "$PY" -B -m scripts.apron_f0_marginals.extract --input-manifest "$MANIFEST" \
  --input-root "$INPUT_ROOT" --owner 0 --output "$RUN/factors/owner-0"
$PY -B -m scripts.apron_f0_marginals.launch --phase analyze --run-root "$RUN" --evidence "$RUN/evidence/analyze-0" --cwd "$REPO" -- \
  "$PY" -B -m scripts.apron_f0_marginals.analyze --input-manifest "$MANIFEST" \
  --input-root "$INPUT_ROOT" --original-run "$ORIGINAL_RUN" \
  --factor-root "$RUN/factors/owner-0" --owner 0 --output "$RUN/analysis/owner-0"
$PY -B -m scripts.apron_f0_marginals.launch --phase summarize --run-root "$RUN" --evidence "$RUN/evidence/summarize" --cwd "$REPO" -- \
  "$PY" -B -m scripts.apron_f0_marginals.summarize --input-manifest "$MANIFEST" \
  --input-root "$INPUT_ROOT" --factor-parent "$RUN/factors" \
  --analysis-parent "$RUN/analysis" --output "$RUN/compact/summary"
```

owner 1/2は `--owner` とfactor/analysis/evidenceの末尾だけを変え、同じ固定入力を照合する。3 ownerの抽出を終えて各原本を確認してから解析し、全ownerの解析を終えてから要約する。抽出時の公開pYIN呼出しには元の密なViterbi費用が残るため、1800秒以内との約束はない。時間・数値・容量の失敗を観測した場合は、その条件のまま停止して親へ報告する。
