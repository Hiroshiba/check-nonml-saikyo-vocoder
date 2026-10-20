# Phase origin fixed truth：source準備・修正版 v2

状態は **source_prepared_pending_independent_review_not_authorized**。科学実行・import・乱数draw・tests/smokeを準備時に一度も行わない。Sol/xhighの当依頼に限る選択であり、恒久指示の変更なし。AST/Ruffは構文・静的検査だけである。以下の閾値・密度精度・保存方式・停止時計は独立レビューへ提出する固定提案であり、実行可の判定ではない。別の開始指示が必要。

## 1. 科学範囲と正本

新study `phase-origin-fixed-truth-analytic-q-20261020-v1`。5 truth W/A/V/S/J × pair_id 0..99。N4096、L64、K64、fs16000、既知250Hz、H=I。train/testは同grid・同真原点φ0=0、独立の初期AR/innovation/s/j stream。二つのheld-out Gaussian scoreだけを比較し、両側で真noise parameterを固定する。PML唯一base。旧500を変更・再ラベル・再実行しない。noise fit、BMA、追加prior、未知q/F0、phase sweep、音声品質/追跡を追加しない。HTML・音声・Git工程なし。

真値（a,bc,bs,σ²,τs²,τj²）は正確な十進文字列でINPUTに固定：W=(0,0,0,.001,0,0)、A=(.6,0,0,.00064,0,0)、V=(0,.8,0,.001,0,0)、S=(0,0,0,.0005,.0005,0)、J=(0,0,0,.0005,0,.0005)。実装のa/τ²/生成スケールは下記binary64評価規約に従い、理想実数法則と区別する。

実数正本は x=2πu、q=(48−59cos x+8cos2x+3cos3x)/√4081、g=q、h=(−59sin x+16sin2x+9sin3x)/√1909。c=160/√4081、c_d=2π√(1909/4081)。qのgeometryは代数的に同じ `c sin^4(πu)(1+.3cos2πu)`、hはその解析微分の−1/c_d倍を80dpsで評価する。sin(πu)はsin(π min(u,1−u))で評価する。境界近傍の直接Fourier加算の桁落ちを避ける評価式選択であり新モデルではない。Fourier校正との有限精度の差は未実測、noncertified。実数64点のM_g=M_h=1、Σgh=0を、丸め配列の厳密性へ移さない。再RMS化・分散補正なし。

三層を区別する：(i) 理想解析Gaussian、(ii) 保存binary64 Yを正確な実数入力とした理想解析OLS、(iii) 固定多精度・binary64手続き。binary64生成器は連続Gaussian法則を厳密に生成せず、理想test期待差の−KL≤0は丸め生成法則の厳密恒等式と主張しない。有限testのΔ>0を拒否しない。

## 2. 80dps geometryと演算

φ_evalは厳密有理数。u=(n/64+φ) mod1、floor membershipはFractionによる厳密な有理整数演算。q/h/vは各64値だけ保存し、n mod64で4096値を無演算・byte同一の複製として復元する。gは保存qのalias、生成geometryはoracle geometryと同じ不変bytesを両recordが参照する。membershipは連続半開区間[start,end,label]。非zero φの観測周期は通常65群。端の群は独立通常分散で、端同士の共有や部分周期補正なし。

まずmp.isfinite(x)を明示検査し、非有限mpfはGate(mpf_nonfinite_before_fraction)として拒否する。特殊tupleをFractionへ渡さない。有限mpfからfloatへのOverflowErrorもGate(binary64_overflow)というpair数値失敗とし、zeroや飽和值へ救済しない。その後80dpsの有限mpfのmantissa/exponentを厳密Fractionへ変換し、CPython3.12 `float(Fraction)`で最近接ties-to-even binary64化する。これは80dps近似値に対する丸めであり、真の解析値のcorrect rounding・区間上界を保証しない。負zeroを含むmpmath表現の保証は付けず、mpmathが返すzeroを正zero化する。c/c_dは90桁以内の近似文字列とbinary64、実q/hの二乗平均と内積を保存する。非有限は失敗、値のclip/epsilon足しなし。

w=exp(bc cos2πu+bs sin2πu)、Zφ=64点wのmp.fsum/64、v=RN64(σ²w/Zφ)。ZφをZ0や連続積分へ置換しない。a=RN64(十進a)、Pminus=RN64[Σ(i0..63) a^(2i) v[−1−i]/(1−a^128)]を80dpsで評価する。v/Pminusは丸め済Gaussian scoreの入力正本。AのP0=a²Pminus+v0は各密度精度で評価する。正でない分散は失敗。

乱数はpinしたNumPy2.3.5 PCG64/SeedSequence/standard_normal(dtype=float64)。各recordでinitial1、innovation4096、s64、j64を、それぞれ独立seed入力から一度だけ引く。τ=0でもs/j標準drawとscaled値を保存する。φ0=0なので生成周期は64。sqrtは80dpsで丸め済み分散を開平後RN64。r初期scaled値、r_n、r+s*g+j*h、Y=q+residualは明示的なbinary64乗算・加算・順序、FMA不使用。ARを周期resetせず、testへcarryしない。生成直後の各配列を次段階前にfsync保存する。

score residualの保存配列はnp.subtract(Y, RN64 q)のbinary64。密度評価はこの丸め済差配列を正本にせず、保存Yと保存qの二進有理値から各60/90dpsで引いた差を使う。保存residualはそのRN64診断配列。この区別をschemaに保持し、計算精度の不足を残差floorで救済しない。

## 3. train-only ideal OLSとroot gate

calibrateの引数はtrain配列と診断保存callbackだけ。truth/test/φ0/scoreを渡さない。qのFourier係数c_h=(−59,8,3)/√4081、A_h=−2c_h Σ(n昇順)Y_n cos(2πhn/64)、B_h=2c_h ΣY_n sin(2πhn/64)。各50/80dpsのcontext内でh=1,2,3、k=0..63のsin/cos表を独立評価し、n昇順のY_n×table[n mod64]をmp.fsumへ渡す。Yを先に位相ごとに加算しない。旧n全体角の有限精度評価とはbyte同一ではないが、理想OLSは同じ。速度・完走は未測定。Fdep=Σ(A_h cos hx+B_h sin hx)、F=ΣY²−96/√4081 ΣY+N+Fdep、x=2πφ。F'_xのz³倍の昇順係数はp[3+h]=h(B_h+iA_h)/2、p[3−h]=h(B_h−iA_h)/2、p[3]=0。solverへ降順7係数を渡す。

H=max(|A|,|B|)、Bscale=max(1,Σ|Y|)。各精度で独立に係数を作り、H=0→flat、H/Bscale≤1e−25→near_flat、max(|A3|,|B3|)/H≤1e−25→degree_uncertainの優先順で失敗。次数落としなし。precheck不合格の精度はsolver呼出し0。precheck通過時に50/80dps各一回だけ `mp.polyroots(coeffs,maxsteps=1000,extraprec=20,cleanup=False,error=True,roots_init=None)`。一方が失敗してももう一方の固定精度の予定評価を行い、追加精度・外側retry・別solver fallbackなし。

mpmath1.3.0実sourceの定義を読取確認した。Durand–Kerner、元精度のepsを収束閾値とし内部追加は20 **bits**。roots_init=NoneはPython複素数(0.4+0.9j)**n由来。小成分cleanupをせず、内部sort後に元精度へ丸めて返す。errは最大更新量と精度floorの推定値で、真値誤差/全根捕捉の認証ではない。NoConvergenceは根/err/実反復数を返さない。途中根・実反復数はAPI未返却/unknown、予定maxsteps1000とは区別する。返却済の全根・err・係数はgate前に保存し、未返却値を捏造しない。反復履歴は保存対象ではなくAPIも公開しない。

各精度で有限な複素根6個を要求する。各根の |P(z)|/Σ(k0..6)|p_k||z|^(6−k)≤1e−30。分母0は失敗。根積からmonic係数q_kを再構成し、max_k|q_k−p_k/p0| / max(1,max|p_k/p0|)≤1e−25（零係数も同じ全体尺度）。異なる根の相対距離 |z_i−z_j|/max(1,|z_i|,|z_j|)>1e−15。

||z|−1|≤1e−25→unit、≥1e−15→outside、それ以外→undecided失敗。outsideも全て保存する。unitは2個以上。候補角距離は最小円周cycle距離×2π、別候補間>1e−15 rad。arg/(2π) mod1を代表元にし、±φを同値扱いしない。6!対応を列挙し、全相対距離≤1e−25の対応がちょうど1つ、両精度の分類とbestが一致すること。

元三角停留残差は |Σh(−A_h sin hx+B_h cos hx)| / Σh(|A_h|+|B_h|)≤1e−30。候補全てに要求。Fdep昇順bestと次善のgap/H>1e−20。bestの F''_x/H>0 かつ>1e−20、非正/flatを別statusで拒否。50/80のbest Fdep/H差≤1e−25。全根・係数再構成・二精度一致はnoncertified運用gate、共通係数誤りや真のglobal解の完全捕捉を認証しない。

80dps φ_rootの有限mpf値を厳密Fraction化し、10^40倍の整数商/剰余でties-to-evenを一回、1は0にmod正規化して、40桁decimal有理φ_evalを固定する。近似rootからの丸め誤差≤.5e−40 cycleだけを意味する。φ_eval=0、64φ_evalが整数、root50/root80/φ_evalの64種類floor membership不一致、root80のsample境界最小距離≤10×二精度の円周差は失敗。φ_evalの停留残差≤1e−30と、元Fdepのbest順位維持も必要。境界救済・oracle snappingなし。

## 4. Gaussian密度・精度gate

両側の丸めgeometryを正本としたN4096のjoint density。θを回転/refitしない。定数−Nlog(2π)/2を同じmp精度で共通使用。各scoreにlogdet、二次形式Q、定数、scoreを保存する。Δ=estimated−oracle、nats/record。

W/V：対角vでlogdet=Σlog v、Q=Σe²/v。A：P0項e0²/P0、残りΣ(e_n−a e_(n−1))²/v_n、logdet=logP0+Σ(n≥1)logv_n。S/J：各実観測blockのD=diag(v)、f=qまたはh、τ²は対応真値のRN64。z=e/√v、w=f/√v、T=Σw²、α=(Σwz)/T。Q=Σ(z−αw)²+α²T/(1+τ²T)、logdet=Σlogv+log1p(τ²T)。T=0またはτ²=0は白色へ正確に分岐し、normで割らない。dense N×N/Cholesky禁止。

精度は60/90dpsを最初から各一回。oracleは校正前に評価・保存し、calibration失敗でも保持する。推定側成功時だけ同じ2精度評価。estimated60/90も各返却直後にlogdet/Q/定数/scoreをestimated_score60/90としてatomic/fsync保存し、その後に次の精度を開始する。返却前killは未返却のまま、返却済60を90側中断で失わない。各logdet/Q/定数/score/Δについて |x60−x90|/max(1,|x90|)≤1e−40、有限・Q≥0を要求する。Δ60は保存60dps score同士の差を90dpsで計算して照合する。90dpsを主保存値（90桁以内、最大128 ASCII bytes/token）。この一致は演算整合のnoncertified診断であり、真の解析Gaussian密度の誤差認証や境界保証ではない。geometry丸め誤差をこのgateで認証したと主張しない。誤差gate不合格をthreshold緩和・追加精度で救済しない。

## 5. raw schema・失敗

機械可読SCHEMA.jsonを併用する。各pairはraw appendファイルと最大16KiB JSON metadata、50/80 root JSON各12KiB。rawはheaderなしlittle-endian binary64連続。metadataのname/offset/bytes/shape/dtype/SHA256により全配列を可逆復元する。blob intentをmetadataへatomic/fsync→raw append/fsync→完了descriptor更新/fsyncの順。途中kill時のintentと残存raw/partialを消さず、未完配列を保存済みとはしない。root診断更新は情報を追加し、以前の返却済根を失敗後に削除しない。byte cap超過はowner停止であり、診断tokenの切捨てや科学配列削除をしない。エラー文だけ固定1024bytes以内。

生成一次配列はrecordごとinitial standard/scaled、innovation、s/j standard/scaled、AR、合成residual、Y。q/g/h/v/Pminusは共有のoracle64点geometryを参照。oracle診断residualはoracle score段の前に一回保存し、校正失敗時も保持する。estimated診断residualはestimated geometry成功後に一回保存する。両方に到達した場合の総本数は従来どおり2で、再保存・raw重複をしない。estimated64点geometryも保存する。aliasは正確に同一bytesの場合に事前に定義したq→g、oracle geometry→両recordだけ。seedのみの代替なし。未使用τのdrawも保持する。phase・membership・定数・norm・seed入力・実初期stateもmetadataへ保存。

予定台帳500行を科学前に保存、owner=global_id mod3、global_id=100truth_id+pair_id、167/167/166。各pair最大1attempt、owner内昇順。pair status started/complete/numerical_failure、stage・inflight・失敗理由を保存。返却済oracle片側値は保持。数値gate失敗はその行を欠測として続行、capacity/I/O/MemoryError/未知例外/timeoutはowner停止。予定台帳・原raw・partialを残す。全予定100/truthを分母とし、未着手と不明は実終了/metadataの証拠に従い区別する。

summaryの実行入口は隔離済み。source/summarize.pyはoptimization設定を明示検査後に常に拒否する。旧prototypeはdeferred/*.py.txtへ資料として保持し、実行source/承認済集計器とは扱わない。将来はtypedな全process証拠、owner/source/claim/原raw hash、予定分母と欠測の意味を別レビュー・別指示で固定してから集計する。complete行やparent-tool-waitの存在だけで未終了ownerを採用しない。今回の原科学範囲・全100分母・成功条件付き参考・CIなしの原則は不変。

## 6. Seed・依存と実行境界

study UTF8 SHA256をlittle-endian uint32×8へ静的分解し、SeedSequence入力=[8語,0x50484153,truth_id,pair_id,split_id,component_id]。components initial/innovation/s/j=0/1/2/3、split train/test=0/1。全4000入力は静的に一意、旧6語mappingとは長さ13対6で非同一。PRNG出力非重複の証明ではない。各将来workerはdraw前に全4000のPCG64初期stateを生成・hash一意性確認し、その全hashを保存。生成時stateを照合し、値を選び直さない。この初期化も準備中は実施しない。全環境を通した新study名の未使用と唯一owner割当は親が開始時に確認する。

DEPENDENCIES.jsonに現在のPython3.12.14 executable hash/sys.version、mpmath1.3.0の87py hashes、NumPy2.3.5の配布物hashとmetadataを完全pin（可変pycを除く）。runtimeは全必須pinをif→明示例外で検査し、assertへ依存しない。全CLI入口でsys.flags.optimizeとPYTHONOPTIMIZEを記録し、前者非zeroまたは後者が未指定/空/0以外なら明示拒否する。-Bだけで最適化を防止したとは扱わない。拒否時も原stderrへ設定を残す。runtimeは科学import前にmetadata/specと全固定hashを照合し、実import元も照合する。BLAS関連5環境変数はimport前に1固定。mpmathはruntime child環境のMPMATH_NOGMPY=1/NOSAGE=1、SAGE/STRICT flag不在でpure-Python backendをpinし、実backendも照合する。この設定は将来entrypoint内だけであり、準備環境の永続設定は変更していない。追加install/設定変更なし。実際のOS/native thread稼働や性能の保証はしていない。数値BLASのdense演算は使わない。

`external.py --permit-new-study`は将来の明示開始用entrypoint。既存authoritative claims directory、未使用out、owner、期待source SHAが必須。resolve済みsource/claims/outは同一・祖先・子孫の全重複を拒否し、symlink ancestryも拒否する。sourceを汚すclaim/outを作らない。claim原本はJSON serialized bytesをO_EXCL作成前に4096以下と明示検査し、原本/claim-copy/RUN各4096を固定枠で計上する。原claimのO_NOFOLLOW+O_EXCL/fsync後は削除しない。起動前失敗も試行として保持し、別claims-dirによる重複を親が全ホストで防ぐ。source準備版のフラグは開始承認の代わりではない。旧BF入口とは無関係。

## 7. 時間・資源・終端

共通monotonic起点は外側入口（検証・claim・保存を含める）。独立supervisorとouterが科学処理を行わない。1owner=1science worker、最大3同時、worker RLIMIT_AS512MiB/CPU840s、owner wall900s/output64MiB。supervisor/outerのRSSは別記し、合計512MiBと主張しない。RAM/完走率/時間の実測保証なし。絶対elapsed予定は次のとおり。

### durable起動と例外cleanup

processes.runはPopen後のselector/identity/log準備から全処理をtry/finallyへ含める。finallyは証拠・logのflush/fsync/closeより先に既知process groupをkillし、期限内の実waitを試みる。保存例外がkill/waitを飛ばさない。取得不能なexit code、reap不能、cleanup失敗はnull/unknown。cleanupのfile I/O失敗は後から記録し、終了を捏造しない。signal記録は(pid,start_ticks,signal)ごとの一回で、failover同PIDへの反復追記なし。/proc/statはcomm終端の最後の')'から分割してstart_ticks/PPID/pgrpを読むため、comm内空白に依存しない。

Popen childはhandshake.pyを先に起動し、実science/監督sourceへまだexecしない。自分のpid/PPID/pgrp/start_ticksをrole-birth.jsonへatomic/fsyncする。親は一致確認してrole-parent-ack.jsonをdurable保存。workerはさらにouterがworker-birthを受領しworker-outer-ack.jsonをfsyncするまで待つ。両ackを検査しrole-exec-authorized.jsonをfsyncして初めて元commandへexecする。元PID/start_ticksはexec後も同じ。各起動handshakeの待機は30秒以内かつ科学838秒より前。identity/ack保存失敗ならscienceへ進まない。単なるpoll発見の前に科学が始まる経路を閉じる。

Linux preexecでPR_SET_PDEATHSIG=SIGKILLと親PID再確認を行い、親死亡の設定前raceも拒否する。outer/supervisorはPR_SET_CHILD_SUBREAPERにより孤児化した既知/未観測子を引き受け、cleanupでkillと実waitpidを試みる。supervisor喪失直前にworker PIDをpollできなかった場合も、durable handshake＋親死亡signalでscienceの生存を許可しない。非特権Python exec・Linux機能が必要で、設定不能なら起動失敗。これは当該process内だけの将来設定で、準備環境のOS設定を変更していない。OS停止不能I/Oやkill/reap未確認は保証せずunknown。unknown時のinventoryはsnapshotであってimmutable成果とは扱わない。

- 838s：独立supervisorがworker process groupへTERM（新pair開始も止める）。
- 840s：supervisorが生存workerへKILL。outerも観測した元PID/starttime一致のworker groupへ独立failover KILL。進行中polyrootsにも適用し、solver返却を待たない。OSのsignal配送/停止不能I/Oまで厳密時刻で保証する意味ではない。
- 845s：worker wait/reap期限。未reapならreturncode=null/unknown、成功にしない。
- 通常850sまで終端保存を目指し、860s以後はsupervisor成功exit禁止。
- 865/870s：outerがsupervisor groupへTERM/KILL、880sまで実wait。記録したworkerにもKILLを適用する。
- 890s未満：outerのmanifest/fsync後観測を保存して正常exit。900sは親の最終強制観測期限。外側tool終了が900sを超えれば成功にしない。

### tracebackレベルのエラーログ

USER_INSTRUCTIONS.mdの「エラーログは必ずスタックトレースレベルまで」を適用する。予期せぬ例外、I/O/Capacity/依存pin/起動/監視失敗と、例外として捕捉するGate/NoConvergenceについて、発生位置・chainを含むtracebackを原stderrへ出す。伝播させる例外はchainを保持し、最終境界で記録する。正常な/proc消失・既に終了したPIDへのsignalのraceはエラー成功化ではなく通常のプロセス観測として区別する。

監視/cleanupで捕捉した例外は、まずsys.exc_infoの参照だけをRAMに保持する。tracebackの整形にはlinecache等のI/Oがあるため、kill/実waitの全試行後に初めてformat/原stderrへのwriteを行う。log flush/fsync/closeやログ出力失敗が先行して子の停止/実waitを飛ばさない。記録のための科学再実行はしない。

diagnostics.pyは各processのtraceback出力を131072bytes以内（末尾marker予約512bytes）に制限する。超過はtruncated_bytes/complete=false、書込/整形失敗はwrite_errors/complete=falseを記録し、完全保存と偽称しない。Gate記録が不完全ならownerを停止する。worker/supervisor/outer receiptはその時点のtraceback_loggingを保持し、原stream全体の完全性は独立したseen/retained/overflow値で確認する。outerの最終記録以後の未捕捉例外もCLI guardが原stderrへtracebackを出し、実tool失敗原文へ残る。stderr自体が書けない場合は可能なreceiptの不完全flagと親の実失敗観測に従い、成功扱いにしない。NoConvergenceの未返却根/err/実反復数を、この例外ログで捏造したと扱わない。

stdout/stderrはworker/ supervisor別の原bytes。各stream通常128KiB、overflow検出read4096bytesまで135168bytesを保存し、overflowは明示失敗。cap以降の非保持bytes数を記録して完全原出力と称さない。通常は候補stdout出力をしない。raw/receipt破損、ENOSPC、kill時は原partialとログを残す。workerのreceiptはworkerだけ、supervisorは独立wait/観測/ledger、outerは実supervisor wait/原PID/PPID/stat/cmdline/UTC/signal/RSSを保存する。過去PID不在だけで終了を作らない。

最終artifact manifestをfsyncした後のouter-last-observationを別ファイルとして保存する。manifest自身・その後の観測は自己hash対象にせず、後段delivery manifestが全bytesをhashする。receiptの書き直しなし。親はouter自身の実tool終端原文を科学outputと別のevidence directoryへ全bytes保存する。4096超でも切り捨てず、rawの実bytes/SHA/path、typedな実returncode/reaped/owner/outer PID/観測UTC/起点からelapsedをphase-origin-parent-tool-terminal-v1 proofへ保存する。この原文・proofは科学64MiB枠外の後段保存工程であり、無断でowner原本へ追加しない。900s未満のwait0・両child wait0・最終fsync観測と全保存を照合して初めてprocess成功とする。source側が自分自身の実exitを先取りして捏造しない。正常process終了と全500の科学成功は別軸。

### owner-ledgerの対象と完全性

supervisorはsourceでpinしたINPUTの全500 planned rowsと出力planned-ledger.jsonの一致を明示確認し、自owner行だけを固定順で列挙する。各行の参照先は正確なpair-XXX.jsonだけであり、pair-*.json等の広いglobは使わない。roots50/roots80 recordをpair metadataとして読まない。全167/167/166行について、欠落はmissing/start_unconfirmed、JSON/必要field/row対応の不備はinvalid/unknown、started/inflightはincompleteと明示する。存在しないfileから未起動・完了を勝手に推測しない。数値failureの終端metadataと科学成功は別statusで保持する。worker receiptがcompletedでもowner-ledgerに欠落/不完全があればsupervisorはcompletedとしない。後段の科学採用をこの台帳だけで認定しない。

### 例外のない異常eventの呼出しstack

docs/DEVELOPMENT.md:23の要件に従い、TERM/KILL/failover・cleanup KILL・log overflow・reap期限到達・child nonzero終了・欠落/不完全なplanned pair観測にも呼出しstackを付ける。signalは先に試行し、その直後のfile名/行番号/function名をメモリへ凍結する。stack取得時はlinecache・整形・log I/Oを行わず、監視側の出力はcleanupのkill/実wait後だけにする。検出箇所の行番号を後日のframe.f_linenoで読み替えない。signal/overflow記録は既存の一回性を維持する。

例外tracebackと異常call stackは既存131072bytes/process枠を共有する。128framesを超えたstack取得、byte超過、書込/整形失敗はcomplete=falseと専用counterで不完全性を保持する。原stderr全体の完全性はparentのseen/retainedも併用し、完全保存と偽称しない。faulthandlerを各CLI entryでstderrへ有効化し、取得可能なnative異常終了時のPython stackを残す（C/C++内部全stackの保証ではない）。そのraw出力も既存parent stream capの対象で、native fatal signalではreceipt不在・終了不明を捏造補完しない。

## 8. 厳密bytesと保存移送

BYTE-BUDGET.jsonの論理file bytesを上限とする。filesystem割当block/metadataはこの値に含まれないため、disk空きも確認しENOSPCを失敗扱いにする。base主要10配列=327680bytes/pair。追加draw/scaledと2geometryを含むrawは実最大334896bytes、保守cap334960bytes。root2×12288、metadata16384を含めpair最大375920bytes。167pair=62778640。固定枠1MiB、終端枠2MiB、通常atomic残存partial最大16384を加え65940752bytes、64MiBまで1168112bytes余裕。166ownerにも167の上限を適用。通常書込guardは終端2MiBを侵食しない。古いfinal+新partialの二重存在も計上。失敗rawを削って適合させない。byte guardで数値処理が止まる場合も予定分母は維持する。

固定1MiBにsource/input/dependency/contract snapshot、全500予定台帳、4000初期state hash270336bytes、claim原本/claim-copy/RUN各4096を含める。終端2MiBは4原log各135168、worker receipt65536、owner ledger131072、supervisor receipt131072、postfsync4096、outer wait131072、artifact manifest131072、last4096、durable birth/ack/exec-authorized計7file各4096＋最大control partial8192、最大同時終端partial327680を含む。準備時にコピー予定固定file合計と宣言capを整数算術で確認する。

全子の実wait/reap確認後の**別保存工程**として `package_saved.py` が全immutable fileをpathソート順に連結する論理byte streamを作り、payload上限31MiBの`payload.bin`を各ZIP_STOREDへ収める。packing前にresolve済owner原本/source/claims/transfer outの全包含を拒否し、typedな親tool proof、supervisor/worker両wait/reap、durable PID/starttime結合、immutable inventory全file hashesと集合、source/input/dependency/contract pinsを照合する。終了不明はpackingを拒否する。終了済failed ownerの原物保存は科学成功とは区別する。各partは通常の独立ZIPで32MiB未満。任意byte切断を通常ZIPと偽称しない。PARTS-MANIFESTは元file path/offset/bytes/SHA、全stream bytes、part順/offset/payload SHA/ZIP SHAとmember名を持つ。全partをstream読取し元file hashesまで検証。圧縮率を仮定しない。親tool raw/proofも全bytesを論理streamへ加え、保存工程のdiskはその実長を含むpart全長＋header＋manifest上限を整数で事前算定する。--staging-byte-budgetと空きdiskが足りなければ元原文を保持して保存工程を拒否する。原文に固定4096 capや切捨ては設けない。manifest1MiB枠を超えるほど巨大な原文はさらに別保存契約が必要で、既保存原文は削らない。公式Libraryの実転送上限は将来の保存時に確認する（32MiBのサービス保証を新たに主張しない）。さらに小さい上限なら科学を再実行せず、この保存工程だけをレビュー改訂する。upload失敗は同じimmutable bytesの転送だけを再開し、科学claimは再利用しない。

### 親による失敗証拠保全（通常packingと別工程）

worker未起動のpreflight/handshake失敗等で通常package_savedのchild_spawned/終了証拠gateを満たせなくても、gateを緩めない。保全は親の別の明示指示後だけに行い、新しい一般化packing入口は実装しない。通常packingの拒否理由・原stderrも証拠として残す。

保存対象は元tool終端原文、claim原本、存在するstdout/stderr、生成済みreceipt、partial、失敗時点のfile一覧と観測時刻/bytes/hashである。未生成fileは欠落理由を記録し、receiptや数値を後から作り直さない。既存原本を変更・削除せず、科学再実行・owner再割当・claim再利用をしない。科学採用不可の別artifactとして扱う。

分類は観測証拠に従う。未起動は起動前拒否等の積極的証拠がある場合だけ、終了確認済みは実wait/reap等の一次記録がある場合だけ。file不在やPID不在だけではそのどちらも認定しない。記録が足りなければ終了不明のままにする。process起動とscience kernel到達は別の状態として記載する。

終了不明でmutableかもしれないfileを写す場合は、コピー開始/終了とfile観測時刻を付けたsnapshotと表示する。元fileが途中で変化した可能性・hash/長さの不一致・raw/log欠落を明示し、immutable run完了、全原値保存成功、通常採用を宣言しない。snapshot ZIP自体のbytes/hashを固定できても、元runの終了・不変性や科学的完全性の証明にはならない。Library移送も別の正式保存工程であり、失敗を科学再実行の理由にしない。

## 9. 未解決・レビュー条件

noncertified gateを受容するか、80dps geometry近似と丸めGaussianを今回の数値対象として受容するかは親の独立数理レビューが必要。API互換性はsource読取確認済みだが、実際の収束・時間・RAM・保存cap適合率は未測定。計算結果によるgate調整は禁止。global実行済study inventory、claims唯一性、outerの実tool wait保存は親の将来の責任。source全文の静的レビュー・これらの判断・別開始指示が揃うまで起動しない。
