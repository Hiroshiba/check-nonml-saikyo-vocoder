# 保存 oracle 残差再解析の科学契約 v0.4（独立静的レビュー用）

作成日 2026-10-20。実装準備のみ。親の独立静的レビューへ返して停止する。
科学 run・データ生成・候補 import・tests/smoke・Git 登録/PR・create_blob は未実施。
現在の base は PML。PR67 Draft・既存500組/2500 score・旧失敗/回収記録を変更しない。

## 出典・範囲

Hiroshiba/check-nonml-saikyo-vocoder main `55e3ce03874404d3c076e5e08c72eb324a9b9d88`。
`experiments/2026-10-20/oracle-covariance/followup-design/README.md` と全5設計文書、`USER_INSTRUCTIONS.md` に従う。元文書の版・SHAは source manifest に収録する。未知テンプレート文書は境界の理解にのみ使用し、未知平均・位相推定・推定 direction を追加しない。設計文書中の採用前の表現より README の現在の判断を優先する。

目的は既使用500組（5 truth 各100）の記述的・事後設計による再解析。N=4096、K=L=64、既知平均を既に除去した raw residual、既知 geometry、H=I。原 q、乱数、phase 配列、三角関数を再生成しない。新しい仮説・候補・自然音声・音質評価・生理的原因確率・確率校正の主張なし。別 prior 探索・truth/test による prior 調整なし。

## 入力 v2

Cloud A の explicit input index を将来 `--input-index` と `--index-sha256` で渡す。今回ファイルは受領/読込しておらず、schema は親の通知に基づく。

- `schema=oracle-input-index`、`schema_version=2`、`data_kind=residual`。
- index は 1,427,508 bytes、SHA256 `79c47c6b1926359d636d63eca6b6bab161e2b2d5f28015bc16d5209a100350d2` に固定する。変更は別契約版として静的レビューする。
- `files` は絶対 path をキーとする `{path,bytes,sha256}` 1908件。最初に全500ID台帳を永続化し、回収済み旧scoreだけを独立読取・個別SHA照合・保存する。その後全参照ファイルのSHA/sizeを照合し、個別利用時も再照合する。探索・glob によるデータ発見・ファイル名推測・再生成・旧スコア再 fit はしない。
- 500 pairs の id と truth、pair_id 0..99 を検証。台帳・旧score読取・科学計算の順序は pair_id 昇順が第一キー、その中で W/A/V/S/J の round-robin に固定。時間制限で一つの truth に偏ることを避ける事前規則であり、結果依存の順序変更ではない。各 pair の `residual_file` は float64 `<f8`、C order `[2,4096]` NPY。train row 0、test row 1。ヘッダ記述 offset 128、各 row 32768 bytes、payload offset 128/32896 と payload SHA を照合。ロード済み row の bytes とも照合する。
- 残差は既に q を除いている。q の二重差引き、平均除去、gain/norm 補正、再切出しなし。
- geometry は float64 `[64,4]` NPY、列 q=g=0、h=1、z_cos=2、z_sin=3。sample n は行 n%64。保存 z を直接使い、有限精度の和を0に上書きしない。g/h 実 norm を計算して保存し、通知された値との絶対差 1e-12 超は入力不整合。q 列を平均処理へ使わない。
- 旧 score は各 `merged_pair_json` の `fits[model].test_log_density` に限定。モデル W/A/V/S/J、単位 nats/record。元 `original_pair_json` の回収前失敗を流用しない。CSV/元契約/回収記録も files の hash 照合対象とし変更しない。

## 推論・十分統計量

model prior は各1/5。A は [-0.8,0.8] の da 一様 1/1.6、V は半径1.5円板の面積一様 1/(π1.5²)、S/J は α∈[0,1) の dα 一様。共通 scale は dE/E。proper raw prior predictive とは呼ばず、方向 evidence 比で train-only weights を根拠付ける。train posterior が proper な場合のみ proper raw posterior predictive とする。

train/test は E と shape を共有、latent draws/AR初期状態は独立。joint covariance は C⊕C、AR 境界積を追加せず、S/J の周期係数を共有しない。pair 間 pooling なし。

T=Σx²。A は B=Σx[n]x[n-1]、D=Σ内部x²、各 record の初期値²と2列 innovation 行列の QR。V は phase energy と実 z の和。S/J は d=||direction||²、unit direction への射影 P と明示的直交残差の二乗和 O を計算し、O=T-P は使用しない。E=v+(d/L)τ²、α=(d/L)τ²/E、U*=sqrt(L/d)U。保存残差や direction 自体の書換えではない。T>0、O>0、P>=0、有限値、|(O+P)/T-1|≤1e-12 を要求。分解の閾値は固定された演算診断であり、科学的同等性幅ではない。

r=1/2、h=rN/2、j=rK/2 として log I=-h log T+log J。W は J=1。A の無次元 kernel は (r/2)log(1-a²)-h log(1-2aB/T+a²D/T)-log1.6。V は -h logΣ(e_l/T)exp(-b·z_l)-b·(rKΣz_l)/2-log(πR²)。S/J は x=log t、t=ε/[L-(L-1)ε] として logL+(j+1)x-h log(O/T+(P/T)exp x)-2log(1+(L-1)exp x)。Jacobian を保持する。

raw per-model log predictive は logΓ(N)-logΓ(N/2)-(N/2)logπ+log I_joint-log I_train。BMA は同じ共通定数と joint/train の logsumexp 差。重みの train evidence 共通因子は除く（log I の定義を保存）。方向密度の絶対値は出力しない。raw nats/record と方向密度を差し引かない。

## 求積と固定診断

A: 停留点三次式の微分根で区間を単調区間に分割し、符号変化 root と極値の重根候補を保持、代数的全実根との照合も実施する。端点/根/曲率幅で分割。GL16/32/64 と別 GK 適応求積（epsabs 1e-12、epsrel 1e-11、limit128）を照合。正の QR 表示との log 差≤2e-7。根の残差・区間符号を保存。

V: 全円板 sector、制約付き mode と KKT、保存 z の gradient/Hessian、sector 接線 mass upper envelope。mode と曲率幅で初期分割し、GL8/16差または大きい envelope によるriskがactive内で最大のcellを二分する。smallは個別upper/M<1e-10の候補だけをupperの小さい順に累積し、合計upper/M≤1e-8の範囲に限る。残りはactiveへ戻す。log領域で処理し、非有限・丸め超過はfail-closed。cell 上限4096。4096個の現partition診断を計算してもgate未達なら分割せず cell_budget_exhausted を返す。4097個にはせず、旧partitionのrisk/omittedと新partitionの求積を混ぜない。最終partitionのGL8/16はcell保存値を再利用し、GL32、angular .37分割GL24を評価する。Cartesian b_x=R sin u,b_y=R cos u·vのGL24/48を必ず保持し、最新2段差≤2e-7かつ最新値対polar GL32差≤5e-7の両方を満たさない時だけ64、さらに96へ進む。96でも未達なら未収束、128は追加しない。最終GL32全cell massを分母にsmall/activeを再分類し、risk/omittedの各gateも再確認する。分類分母と規則名を保存する。固定次数のroots_legendreはcacheする。別座標は mode/幅で分割、Jacobian R²cos²u を保持。小 cell も計算から除外せず、その upper mass 総比≤1e-8 を要求する。mode optimizer 不成功/KKT残差>1e-3/支持外は未達。細分化優先 risk は保証誤差でない。seam 両側も全領域に含める。

S/J: log t の凹 mode と、左 tail の二つの解析上界の小さい方を使用する。log-concavity の有限区間端点から正の本体下限を作り、tail/下限≤1e-8 まで左端を延ばす。固定 α_max は導入しない。train と joint の h/j/O/P で別々に評価。GL16/32/64 と区間ごとの rescaled t 座標 GL80、GK の補助誤差を保存する。

収束 gate は直近2差それぞれ≤2e-7、別則/座標差≤5e-7、tail/探索 envelope 比≤1e-8、有限/整合 gate 合格。A/S/J の GK 相対誤差推定≤2e-7。V は partition の直近2差、active risk≤1e-8、Cartesian 最新2次数差≤2e-7 も要求。必須のmode/KKT/curvature、各則・Cartesian値、risk/envelope/tail、GK値/誤差は有限性を明示検査する。GK誤差/質量、curvature、KKT、omitted比は非負（正の量は正）を要求する。NaN比較で成功へ通さない。log mass/log riskは負値も許容する。どれも収束診断であり certified error ではない。数値目標1e-6を保証したとは言わない。統計量・Γ/π・logsumexp・丸めの厳密誤差保証は未解決。

各 log I の真誤差≤δ を仮定した場合のみ、predictive/BMA≤2δ、score差≤4δ が言える。実装は実際の refinement から BMA の変化と二つの BMA 表現差を記録するが、診断差を真誤差へ昇格させない。

## 失敗、比較、資源

必要な10積分すべてが成功した pair だけ BMA を確定する。train5積分が成功すれば train weights/entropy 自体は保存できる。各モデル predictive は当該 train/joint が成功したときのみ保存。候補削除や成功モデルだけの再正規化なし。元 score、全500 ID、失敗理由/分母を保持する。結果 status は complete/partial/invalid_input/time_budget_exhausted、積分は converged/not_converged/invalid_input/time_budget_exhausted。

主比較は BMA 対旧5 plug-in の paired raw score 差。truth ごとの100組平均は欠測があれば null。成功部分集合の平均は条件付き記述として別列。全差分列を保存。test argmax/W救済数/新 hard threshold を主指標にしない。25個のBMA対旧5 plug-inのpaired差について10000回のpaired bootstrapを行い、percentile 95%（NumPy linear quantile）を保存する。PCG64とSeedSequence([20261020,2,truth_index,0,0,competitor_index])、truth/competitorはW/A/V/S/Jの0..4、chunk=128反復。各比較で固定stream。乱数はこの集計だけで、残差生成・shape quantileには使わない。欠測時は元100組の平均/CIをnullとし、成功subsetの条件付き平均/CI・成功ID・100組全差（欠測null）を別欄で保持。CIはpointwiseで多重比較保証なし。29分までに集計が完了しなければCI未達を明示し、各完了比較をsummary-progress.jsonへ保存する。最小HTMLは計算用サマリーで、公開用音声・図・既存品質比較リンクは後工程。

Python3.12、NumPy2.3.5、SciPy1.17.0、worker1。監督入口 `run_reanalysis.py` が子プロセスの起動前にBLAS/OpenMP関連5変数=1を指定する。子限定 RLIMIT_AS=1GiB、RLIMIT_CPU=1800秒を適用。認証・アクセス権限・永続OS設定は変更しない。`worker.py` を直接起動せず必ず監督入口を使う。

最大30分、27分で新規積分停止という上限を保持する。callback deadlineに加え監督が27分でSIGUSR1（新規停止フラグ）、29分30秒でSIGTERM、29分45秒でSIGKILL、29分50秒で待機を終え終端receipt用時間を予約する。workerのbootstrapは29分まで。workerはSIGTERM/SIGINTでfinallyへ移るが、native call中のSIGKILL、OOM、外部終了ではin-process finallyを保証しない。監督は科学ライブラリをimportせず、worker停止後に保存済み台帳から全500IDを含む別receiptを作り、未開始/実行中を未確定にする。監督自体の強制終了、OSの非割込みI/Oなどはこの仕組みだけでは保証できず、実行基盤側の外部watchdog/終了receiptも必要。今回それらの実運用は未検証。callbackだけの保証へ弱めない。

入力1ファイル128MiB上限、積分あたり評価点上限2,000,000、V最大cell4096。評価callbackのRSS監視に加えて上記address-space制限を実施する。1GiBはworkerの上限であり、監督の小さな追加RSSまで含むシステム全体の上限の証明ではない。

通常ファイルはatomic一時ファイルも含め出力総量116MiB以内で書込可否を決め、8MiBをlog増加、4MiBをreceipt/台帳の終端書込に予約する。worker logは1MiB×4世代以内（各formatted record最大8192bytes）、監督捕捉stdout/stderrは末尾4MiB。合計log最大8MiB、派生成果物総計128MiB。外部stderrの受信総bytes/保持bytes/破棄bytes、末尾要点を監督receiptに記録。log循環後も各pairの失敗診断とreason、worker/supervisor receiptに原因の要点を保持する。通常JSONは60MiB以内という個別上限も維持。

初期台帳/starting receiptは入力index、source manifest、geometry、科学ライブラリimportより前に作成する。各pairと各完了積分を逐次atomic保存。旧scoreは残差検証前の独立工程で取得/保存し、旧score自体が読めない時のみ未取得理由を保存する。preflight失敗・encode失敗・予算切れ・未処理例外でもfinallyで全件台帳と緊急receiptを標準libだけで書込。非有限診断はNaN/Infinity/-Infinityという明示文字列で失敗状態と共に保持し、成功値を0などへ置換しない。直前の未保存積分もworkerの終端receiptに含める。物理的な書込障害まで保証するものではなく、失敗時は既存initial台帳と外部stderr/監督receiptを根拠に未確定を残す。

receiptには開始/終了UTC、所要秒、実Python/NumPy/SciPy版、peak RSS、入力index SHA、review済source-manifest SHA、全500ID状態、原因を保存する。監督にはworker returncode/peak RSS/外部stderr量も記録。`--manifest-sha256` 引数に独立レビュー済manifestのSHAを必須とし、そのSHA照合後に全配布ファイルhashを照合する。manifest内自己申告だけでは実行しない。

## 独立レビュー前の未解決事項

1. Cloud A の実index/元contractをこの環境で読んでおらず、schema互換性は通知と静的読解のみ。実際の入力検証は未実行。
2. 実runtime/メモリ/収束率/誤差は未検証。V異座標全件照合は高コストで30分完走を保証しない。予算不足は未達のまま保持。
3. process-local RLIMIT_ASと監督signal/watchdogをソースに実装したが実行確認はしていない。監督までkillされる場合、OS非割込み処理、receipt書込障害、全体RSSの厳密上限は実行基盤の外部receipt/制約が必要。単独callback保証とはしない。
4. 浮動小数点の正下限/tail/envelopeは区間演算による保証でない。根の近接/退化、極端energy、別座標の未解像は未達になり得る。
5. 途中mesh全体は保存せず、完了積分と原因・評価数・時間を保持。新規計測先のみ。旧run-001を不変回収元にする明示recoveryはRECOVERY-ja.mdに従い、同じ出力先の自動resumeは行わない。
6. ASTとcached Ruffは科学的正しさ・正規化・実runtime互換性を証明しない。次工程は親の独立静的レビュー。科学run開始は今回含まれない。

## 静的再レビューR1/R2の限定修正

容量監視は `scandir` と各項目の単一statを使う。列挙済み項目のstat時に発生したFileNotFoundError（rename・置換・log回転中の消失）だけを再走査対象とし、最大3走査の最大合計bytesを採用する。走査/permission/その他I/O errorは伝播する。非atomic監視の性質と通常116MiB/総128MiB/log8MiB/receipt予約は変更しない。想定外のファイル種類も無視せずエラーにする。

persistはrow全体の非有限診断を理由にderivedを削除しない。converged積分の必須値は従来どおりfinite検査し、不正な当該積分をnot_convergedにする。派生値は依存関係ごとに扱い、当該train/jointが無効なモデルのpredictive、全trainが揃わない場合のweights/entropy、10積分等が揃わないBMAだけを未確定にする。正常な全trainから得たweightsと別候補predictiveは保持する。派生成功値自身のfinite検査も残す。不正値はinvalid_componentsや元診断に明示文字列で保持し、成功モデルだけで再正規化しない。

bootstrap来歴はrequested_replicates=10000とcompleted_replicatesを分離する。各chunk完了後に回数をsummary-progressへ保存し、running中・期限中断時のCIはnull。強制終了時は最後に永続化できた完了chunk数であり、その後未保存の進捗は不明。10000回後のfinite/quantile検査にも合格した場合だけcompleteのCIを使用する。数学・prior・支持・積分gate・入力SHA・round-robin順は変更しない。

## 次版の計算予算と回収

今回のCartesian手順は独立レビュー後の明示変更であり、旧run失敗の遡及成功化ではない。最悪node数は24/48計103680、64追加147456、96追加331776、全4次数582912。実装は実際のu/v分割と次数で必要点数を数え、残2 million予算に入らなければ評価前にBudgetExceededとして未達保存する。GL32/alternateの既知必要点数も事前比較する。必須gateを省いて成功にせず、予算例外では最後の完了partitionの診断要約・stage・済んだ照合値を追加評価なしで保存する。全meshを復元する機能ではない。

次版はrun-001の392成功（非V390+旧V2）を原値・旧gate・旧sourceのまま回収し、失敗/未試行4608slotだけ新計算する。原結果ZIP/入力/旧manifest/旧契約を固定SHAで照合する。旧392の新gateによる再評価を主張しない。詳細はRECOVERY-ja.md。

次版の3分割計画は0–32/33–65/66–99。各pair_idの全5truthを一緒に扱う。新slot数1258/1650/1700、合計4608。各shardは1 worker、30分外部上限、worker RLIMIT_AS1GiB、管理出力128MiB、log8MiB。最大3worker同時、合計最大90 worker-minutes、shard出力最大384MiB。監督RSSは各別枠であり、全プロセス合計3GiBのhard capとはしない。初回単一runの実施条件とは別の次版計画。

shardは全500組の旧scoreとslotを保持するが未統合と表示し、派生値・25比較bootstrapは重複計算しない。unionは測定を再実行しない集計専用、最大5分、管理出力128MiB。全5000slotの出自/重複/欠落/sourceを検査し、派生値と指定bootstrapを一度だけ算出する。unionは今回文章契約のみで未実装。今回計測・並列実行は開始しない。レビュー後の別指示を待つ。
