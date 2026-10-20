# 真noise固定・共通train-only位相原点校正：実行前契約案

2026-10-20。対象 Hiroshiba/check-nonml-saikyo-vocoder。**紙上設計のみ。状態：科学的比較は定義済み、実行契約は候補、実行不可。** 本文の数値gate・予算は事前検討の提案であり、実装・生成・tests・smoke・計測・Git変更・run開始の承認ではない。五仮想役二roundは一人の机上検討で、五名の独立査読ではない。

## 1. 一つの問いと停止線

既知解析的q、既知一定250 Hz、同始点独立train/testにおいて、真noise parameter θを固定し、trainだけで推定した共通位相原点を平均と全共分散の双方へ適用すると、真原点oracleに比べheld-out Gaussian log densityがどう変わるか。

比較は各pairで二本だけ：真θ・φ0=0のoracleと、同じ真θ・train OLSのφhat。5 truthは生成原因の層であり、各truthに対する5候補の勝者選びではない。noise fit、モデル選択、BMA、prior、phase周辺化、未知F0、未知q、phase sweep、速度比較、平均だけshiftした第三条件は追加しない。PML唯一baseを維持し、PML位相や自然音声音質の実装・性能を扱わない。

実行に進む前の必須解決事項は§10。提案gateを「採用したこと」にして実行しない。旧500pairはoracle成果のまま保持し、変更・再ラベル・再実行・新結果との対応差分比較をしない。

## 2. 新study・truth・独立性

提案study ID：phase-origin-fixed-truth-analytic-q-20261020-v1。旧study oracle-covariance-finite-sample-20261020 とは別研究。

L=64、K=64、N=4096、fs=16000 Hz、f0=250 Hz、H=I。t_n=n/fs、n=0,…,4095。両recordは同時刻gridで、同じ固定φ0=0を共有する。初期AR、innovation、s、jはtrain/test間、pair間で独立な生成streamを使う。同一連続ARを二分せず、train末尾をtestへcarryしない。校正器の入力はY_train、既知q、L/Nと固定solver設定だけ。truthラベル・真φ・test・scoreを渡さない。真φは生成器と評価者だけの情報とする。

旧contract.jsonのtruths値を明示的に継承する。以下は順に(a,bc,bs,σ²,τs²,τj²)：

- W = (0,0,0,0.001,0,0)
- A = (0.6,0,0,0.00064,0,0)
- V = (0,0.8,0,0.001,0,0)
- S = (0,0,0,0.0005,0.0005,0)
- J = (0,0,0,0.0005,0,0.0005)

E=0.001。理想正規化では各truthの期待平均residual energyがEで、実現noiseのenergyをEへ再正規化しない。S/Jは理想分散寄与を半々とする旧値の継承であり、新しいfit値ではない。truth順W,A,V,S,J、各pair_id=0,…,99、合計500を固定する候補。失敗分の追加生成・置換なし。

### seed候補

UTF-8のstudy IDに対するSHA-256 digestを、先頭から4 bytesずつlittle-endian uint32の8語D0,…,D7と読む。SeedSequenceの整数列を [D0,…,D7, 0x50484153, truth_id, pair_id, split_id, component_id] とし、PCG64を使う。split_idはtrain=0/test=1、component_idはinitial=0/innovation=1/amplitude=2/tangent=3。科学用stream以外を流用しない。worker ID、開始時刻、完了順はseedに入れない。bootstrap用streamは作らない。

旧mappingの整数列と新mappingは長さ・domainが異なる。これは旧seed入力の再利用を避けるdomain separationであり、hash衝突やPRNG出力streamの数学的非重複の証明ではない。準備時に全新streamのseed入力と旧stream入力の非一致、新study名の未使用、予定初期状態の重複なしを静的manifestで確認する設計とする。digest/seed計算自体を本稿では実行していない。重複が判明したらrun前に別版契約へ戻し、都合のよいseedを探さない。

## 3. 平均正本(b)：実数モデルと丸め評価器を分ける

x=2πuとして、実数解析モデルを

    raw(u)=sin⁴(πu)[1+(3/10)cos(2πu)]
    c=160/√4081
    q(u)=[48−59cos x+8cos(2x)+3cos(3x)]/√4081
    c_d=2π√(1909/4081)
    g(u)=q(u), h(u)=−q′(u)/c_d
         =[−59sin x+16sin(2x)+9sin(3x)]/√1909

と定義する。上式は紙上の展開であり数値実験ではない。rawのFourier係数は(48,−59,8,3)/160で、二乗平均は[48²+(59²+8²+3²)/2]/160²=4081/25600。q′の係数は(2π/√4081)(59,−16,−9)で、二乗平均は(2π)²(59²+16²+9²)/(2×4081)=(2π)²1909/4081となる。したがってcはrawの64点二乗平均の逆平方根、c_dはq′の64点二乗平均の平方根と一致する理想定数。q′はcycle微分。qは次数3、q²および(q′)²は次数6なので、任意φの64点平均でM_g=M_h=1、Σgh=0が実数モデルでは成立する。

評価器候補はこのsymbolic定義を80 decimal digitsで近似評価し、その80dps近似値を明示されたround-to-nearest-ties-to-evenでbinary64配列へ落とす。これは近似値に対する変換規則であり、真の解析値からbinary64へのcorrect roundingを保証しない。二重丸めや中点近傍も含む解析値との誤差仕様は準備段階の未確定点とする。生成、oracle score、推定位相scoreは同じ正本・同じ評価規則・同じ定数manifestを使う。校正の50/80dps係数構築も同じsymbolic定義から独立に行う。旧float q、旧c/c_d、旧scoreとのbit一致は要求・主張しない。binary64生成標本が理想連続Gaussianを厳密に実現するとも主張しない。

保存するのはsymbolic式、評価精度・丸め規則、定数の評価文字列とbinary値、実際のq/g/h/v配列。丸め配列の二乗平均を厳密1と断言せず、その値を記録する。理想定数の丸め誤差を消す目的の再RMS化やtruth分散補正は禁止。評価器版・精度・ライブラリが未固定なので、現時点の契約は実行不可。

## 4. 位相対応Gaussian分布

任意候補φについてz_n=n/L+φ、u_n=z_n−floor(z_n)∈[0,1)、c_n=floor(z_n)。m_n=q(u_n)。観測された周期ラベルCφの各cに対して(U_s)nc=g(u_n)1[c_n=c]、(U_j)nc=h(u_n)1[c_n=c]とする。端の部分周期も通常のτ²を持つ独立係数。先頭と末尾を共有せず、部分周期ごとのnorm/分散補正をしない。

    w_n=exp[bc cos(2πu_n)+bs sin(2πu_n)]
    Zφ=L⁻¹Σ_(l=0)^63 w_l,  v_n=σ²w_n/Zφ
    P_−1=Σ_(i=0)^63 a^(2i)v_(−1−i)/(1−a^128)
    P_n=a²P_(n−1)+v_n
    K_r[n,m]=a^(n−m)P_m (n≥m)
    Σφ=K_r+τs² U_s U_sᵀ+τj² U_j U_jᵀ

vは全整数へ64周期延長する。ZφをZ0や連続積分へ置換しない。a=0のi=0項は1倍。生成はr_−1をこの周期定常lawから引き、r_n=a r_(n−1)+√v_n ε_nとする。観測0の分散はP0。ARの周期境界resetは禁止。今回Aは定数vで位相非依存だが、一般定義を破る根拠にしない。

実装準備時のfloor対策候補：80dps解を小数点以下40桁へ一回だけ最近接丸めしたφ_eval∈[0,1)を、正確な有理数文字列として固定し、floorはn/64+φ_evalの有理数比較で決める。0へのtruth-directed snappingは禁止。φ_rootとφ_evalを両方保存する。80dps近似解からの丸め誤差は最大0.5×10⁻⁴⁰ cycle（円周距離）であり、真の極小点からの誤差上界ではない。この運用点のscoreであることを明示し、理想極小点と完全同一とは呼ばない。二精度のrootが異なる周期membershipを生む／boundaryからの距離が二精度差の10倍以下なら、非zero推定をoracle境界へ寄せず境界未決定として失敗。最小案ではφ_eval=0へ丸められる例、その他の厳密sample周期境界に乗る例も失敗として保持し、厳密boundary rootの成功証明や例外救済は追加しない。この保守的失敗規則の正式採否と診断の完全指定は準備段階で固定する。

## 5. 共通OLSとnoncertified運用gate候補

    F(φ)=Σ_n [Y_train,n−q(n/64+φ)]²

q²和が不変なのでφ依存部分は次数3の三角多項式。x=2πφ、F′_x=Σ_(h=1)^3 h[−A_h sin(hx)+B_h cos(hx)]。z=e^(ix)としてz³F′_xを次数最大6の多項式へ変換し、全複素根を求め、円周上の全停留候補を元のFで比較する。gridや局所optimiserの単一解をglobal解と呼ばない。校正法は全truth共通で、noise候補ごとのGLS/MLではない。

このFは入力binary64 Yを正確な実数として固定し、理想解析qを代入したOLSである。多精度係数とrootはその問題の近似解を狙う。一方、各φのqをbinary64へ丸めてから残差を作る数値関数は同じ有限次数三角多項式ではなく、その関数の厳密なglobal optimizerを求めたとは呼ばない。生成・score用の丸め評価器と校正対象の理想関数の区別を来歴に残し、その近似誤差をどう評価・許容するかはsource準備の未確定点とする。

以下は**固定する候補値**。精度・根数・順位の一致はnoncertifiedな運用gateであり、真の全根捕捉・global minimizerの認証ではない。データを見て閾値を調整しない。

1. 50dpsと80dpsの二つを最初から必須とする。入力binary64 Yは正確な二進有理数として読ませ、各精度で係数を別々に構築する。一方の失敗後に精度を追加・拡張しない。各solver呼出しは一回、固定最大反復1000を候補とする。solver名・版・内部追加精度・初期化・収束条件は未凍結で、ここが実行阻止点。
2. H=max_h(|A_h|,|B_h|)、B=max(1,Σ|Y_train,n|)。H=0はflat、H/B≤10⁻²⁵はnear-flat失敗。最高調波の相対振幅≤10⁻²⁵はdegree不確定として失敗する保守案。真の低次数への次数落としは別の証明仕様なしに行わない。
3. 採用degree dについて両精度ともd個の有限な複素根を重複度込みで返すこと。正規化多項式残差 |P(z)|/Σ_k|p_k||z|^k≤10⁻³⁰、元三角式の相対停留残差≤10⁻³⁰を円周候補に要求する。分母zeroは失敗。
4. 全複素根を円周距離でなく複素平面の相対距離で一対一対応づけ、50/80一致≤10⁻²⁵。係数全体の再構成（根の積から係数比）も相対10⁻²⁵以内。根数は円周上が常に6とは限らない。単位円外の根も保存し、捨てたことを記録する。
5. ||z|−1|≤10⁻²⁵なら円周候補、≥10⁻¹⁵なら円周外、それらの間は分類未決定で失敗。両精度で同じ分類・同じ候補数、少なくとも最大・最小に対応する2候補を要求。候補φで元三角式も検査する。
6. 任意の別根の相対距離≤10⁻¹⁵、または円周候補の角距離≤10⁻¹⁵ radを近接/重根失敗とする。最小候補の|F″_x|/H≤10⁻²⁰も平坦/重根疑いで失敗。整数差だけは同じ位相代表元に統合し、±φを同値扱いしない。
7. Fの共通巨大定数を除いたφ依存項の値で順位を比較し、元Fも保存する。最良と次善の差/H≤10⁻²⁰なら非同値tie/順位未決定失敗。両精度で最良候補が対応し、その値/Hの差≤10⁻²⁵であること。oracle近傍の選好、truth参照、test参照は禁止。
8. φ_evalへの丸め後も相対停留残差≤10⁻³⁰、元Fの順位が同じであることを要求する。§4のmembership未決定も失敗。解なし・solver未収束・非有限・根数不足・残差不合格は個別statusを残す。

10⁻³⁰～10⁻¹⁵の幅は、50dpsでの単純丸めより十分緩い検査域と、近接/分類曖昧の保守的拒否域を分けるための提案であり、誤り確率・score誤差・成功率を保証する根拠ではない。実データを走らせて成功するよう調整しない。全根数一致と再構成が共通の係数誤りを検出できるとは限らない。認証が科学上必須ならこの案は不適格で、区間証明などの別契約が必要。本稿はそれを実装・実行しない。

## 6. 二本のscore・保存項目・集計

    ℓ0=log N(Y_test; m(0),Σ(0,θ_truth))
    ℓhat=log N(Y_test; m(φ_eval),Σ(φ_eval,θ_truth))
    Δ=ℓhat−ℓ0

全N=4096元sample座標の正規化joint log density、単位nats/record。定数−N log(2π)/2、logdet、周期定常初期lawを含める。Nで割る場合は追加表示nats/sampleと明示し、主値は変えない。θをrotate/refitせず、bc/bsも同値変換しない。Δの正はそのtest実現で校正側のscoreが大きいこと。有限実現のΔ>0を不正としない。各train条件付きの理想test期待差は−KL(p0||phat)≤0だが、これは閾値・追加実測条件ではない。

φ誤差はe_cycle=wrap_[−1/2,1/2)(φ_eval−φ0)、e_rad=2πe_cycle。φ_root、φ_eval、二精度候補全根・分類・係数・目的値・残差・根間距離・順位gap・boundary診断、真θ、両密度、両logdet/二次形式、Δ、全statusをpair台帳へ保存する。成功でもrawを破棄しない。

全500行を先に固定し、各truth100の予定数、開始/未開始、生成成功、校正成功、score両側有限、各失敗理由を出す。片側だけのoracle値も消さず、校正失敗のΔは欠測理由付きとし0や−∞で埋めない。集計はtruth別に固定：有効数、非有限数、各score/Δ/eのmin・max・算術平均、eの平均絶対値とRMS。割合は必ず予定100を分母とする。全500有限なら500についても固定truth等重みの記述値を併記できるが、truth混合の一般母集団へ外挿しない。

失敗が一つでもあれば成功subsetの数値は「成功条件付き・参考」とラベルし、500全体の平均差は未確定とする。範囲は観測min/maxであって事前のGaussian有界範囲ではない。今回CI、検定、bootstrap、優越/同等性判定、局所1/2 nats基準、勝者表は不要。100/truthの記述実現を報告するだけで、母期待差の精密推定や音質改善の主張をしない。

## 7. 数値密度評価の最小実装対象（将来の仕様、実装しない）

密な4096²行列およびdense Choleskyは作らない。Wは対角、Aは定常ARの初期項込みinnovation式（精度行列の三重対角式）、Vは位相別vの対角、S/Jはfloorで区切った各観測周期のσ²I+τ²ffᵀをrank-one公式で評価する。部分周期にはその実際のf長さ/normを使い、旧64点固有値の流用は禁止。zero-norm blockは白色へ正確に退化させ、normで0除算しない。これは同じ数学的密度の評価法であって追加モデル比較ではない。旧oracleの全パラメータ探索・fit sourceは再利用しない。

小差の二次形式は減算キャンセルを避ける分解を仕様にし、logdet/二次形式それぞれを保存する。丸め誤差の受入基準、固定評価精度、補償和の順序、非正の分散の失敗処理をsource reviewで固定する。未固定のため今は実行不可。一般の混合a/V/S/J fitを実装して仕事を拡大しない。

## 8. 来歴・全配列・資源・終端処理

最大3 workers。各wall900秒、science840秒、RAM512 MiB、output64 MiB、BLAS1 thread、一回のみの候補。global_id=100×truth_id+pair_id、owner=global_id mod3で固定し、worker内は昇順。予定所有数167/167/166。worker数を変える場合も実行前の版改訂とし、負荷に応じた再割当・work stealing・重複試行をしない。停止workerのpairを別workerで救済再試行しない。

全生成一次配列を保存する：各recordのstandard innovation ε、AR r_n、合成residual、Y、standard s/jとscaled係数、initial standard drawとscaled r_−1、生成q/g/h/v・P初期・membership。生成済みだがτ=0の係数も保存する。一時的な演算bufferまで複製保存する意味ではないが、省略する一次配列をseedだけで代替しない。周期配列は64点と反復規則の可逆表現、membershipは連続run表現等を許す。score時の両residual、両phase geometry、phi来歴も保存する。denseΣは生成しない。

静的概算：4個のN点float64生成配列/record×2×167pair=約41.75 MiB/worker。test両score residualを別保存すると約10.44 MiB、合計約52.19 MiB。残り約11.8 MiBに係数、64点geometry、root診断、台帳、metadata、source、receiptを収める必要がある。これはサイズ公式による紙上見積りで実測ではない。NaNや圧縮困難なnoiseを圧縮できる前提にしない。binary型、文字列最大長、保存形式のoverhead、失敗raw最大量を含む厳密上限を準備時に積み上げ、64 MiB未満かつ終端receipt領域を確保できなければ紙上へ戻す。全3 workersで最大192 MiBであり、成果のLibrary保存方式・上限も事前確認する。単一32 MiB転送等を仮定して黙って欠落させない。

逐次pair処理なら配列working setは小さいが、多精度solver/runtimeのRAM・時間は未実測。900秒枠で終わるとも3 workersが必要とも主張しない。source/inputの静的レビューでループ回数、最大root反復、メモリ・保存上限、時間上限の監視仕様を確認する。予算を実際に超えたら予算超過として終了し、精度削減・配列削除・追走・枠拡大しない。

実行前にcontract、source全文、dependency lock/version、OS/CPU/BLAS/thread環境、seed manifest、候補軸（5truth×100pair×train/test、score2本だけ）、source/input hash、時刻・executor・worker所有表を保存する。旧sourceは参照としてhashで区別し編集しない。新study sourceの最終hash凍結前に生成開始しない。

将来の終端要件：science840秒で新処理を止め、残り60秒はraw・失敗status・未開始一覧・receiptの保存に専用化。親はworkerのexit code/signal、開始終了時刻、timeoutとkillの有無、全PIDのreapを記録する。ファイルは一時名→flush/fsync→atomic rename、directory fsyncを経てmanifest化し、hash検証する。wall900秒で終端未完なら未確定artifactとして記録し成功とは呼ばない。Library保存は全chunk・manifest・hash・開けることを確認して完了扱いとする。upload失敗は科学runの再実行理由にせず、rawを保持して保存だけの再開可否を別に扱う。本作業はuploadもrunも行わない。

### 将来の報告範囲

将来HTML等へ報告する場合も、主結果は全500台帳・truth別の固定記述要約・失敗/来歴とする。参考音声はW/A/V/S/Jそれぞれpair_id=0のtest入力、計5本を今の時点で固定しておく案とする。これは新しい人工観測の入力音声であり、新vocoder出力や品質改善例ではない。実測後の聴き比べ・好み選別・clip別正規化は行わない。該当pairが生成/保存失敗なら欠落理由を載せ、別pairに置き換えない。

元float64科学配列は不変。音声化は別の表示工程とし、全5本共通の表示gain、音声format、clip処理方針と由来を別の報告契約で事前固定する。表示設定が未定でも科学runの条件を増やさない。今回は音声生成・書出し・HTML作成を行わない。

## 9. 五仮想役・二round（critic1を含む）

役は scientific_scope、analytic_model、numerics、operations、critic1。以下は仮想的な論点整理。

### Round 1：最小化

1. scientific_scope「5候補をfitして識別率を出す」→critic1「校正とfitの影響が交絡する」→真θの二本だけに縮小。問いに必要な最小比較はこれ。
2. analytic_model「旧qに近い解析qなら旧pairを使える」→critic1「平均正本差を純粋校正損失と呼べない」→新study(b)、旧500不変。理想c/c_dと丸めを分離。
3. numerics「50/80一致ならglobal解保証」→critic1「共通失敗や近接根を排除できない」→noncertified gate、全複素根と残差の保存、失敗保持へ修正。
4. operations「3 workersなら900秒に収まる」→critic1「未実測、全配列保存が64 MiBを圧迫」→静的上限レビューを開始前必須とし、余裕未確認では停止。
5. critic1「φ0=0に寄せれば境界を安定化できる」→analytic_model「真値漏洩になる」→有理代表元とfloor規約、曖昧boundary失敗。oracle近傍選択禁止。

### Round 2：反例と最終判定

1. scientific_scope「平均Δが正なら校正がoracleに勝った」→critic1「有限test実現差と期待KLを混同」→記述結果だけ、音質・母平均優越へ拡張しない。
2. analytic_model「VのZはq同様shift不変」→numerics「exp包絡は無限Fourier次数」→位相別Z、初期law、部分周期membershipを双方の密度へ適用。
3. numerics「失敗だけ80→120dpsで救済」→critic1「追加精度を事後選択すると一回の契約を破る」→最初から50/80の二評価だけ、失敗pairは全台帳に保持、再試行なし。
4. operations「成功subsetでsummaryしrawを消して枠を守る」→critic1「選択biasと保存契約違反」→固定500分母、subset参考ラベル、raw保持、超過なら中止。
5. critic1「案が具体化したので実行可か」→全役「不可。数学的比較は最小だが、solver完全指定、誤差基準、boundary証拠、保存/資源上限の未確定を残す」。紙上で止める。

## 10. 未確定点と推奨停止線

1. root solver名・版・内部精度/初期化/最大反復の完全仕様、gate候補値を採否する根拠。数値global認証は提供しないという研究上の受容判断。
2. 理想解析qのOLS近似と、丸めた数値関数のoptimizerを区別したsource仕様。80dps近似値→binary64の変換規則と真の解析値のcorrect rounding保証を分けた誤差仕様、同一定義の生成/scoreへの接続、密度数値誤差の事前受入基準。境界未決定・0への丸め・厳密sample周期境界例は失敗として残す最小案の正式採否と診断完全指定。境界例の成功証明を新たに作ることは要求しない。
3. 全配列の保存schema、厳密byte上限、source/input・dependency固定、Libraryへの可逆保存手段、3 workers/一回枠の静的適合。静的確認は本稿に未実施の実装が必要なため今はできない。
4. 現段階の許可は設計だけ。実装・tests・新データ生成へ進むには次段階の明示された作業範囲が必要。

**推奨：この文書を実行前契約の候補として保存し、紙上で停止。** 学術上の問いを回答する比較条件は最小まで削減できたが、実行可能な凍結契約とはまだ呼ばない。上記が解決しても過去データへ遡って条件やseedを選び直さない。

## 読取出典と確認範囲

- train-only-phase-origin-contract-review-20261020.md（修正後§2/§5のM_g/M_h区別を含む）
- train-only-phase-origin-contract-independent-review-20261020.md（修正指摘解消まで）
- phase-calibration-mean-provenance-decision-20261020.md
- phase-uncertainty-control-20261020.md
- oracle-noise-source-20261020/contract.json、model_math.py（読取のみ）

これらのローカル一次資料からtruth値・旧生成規約を確認した。旧sourceをimport/実行せず、コード実装・tests・データ生成・Git操作を行っていない。新しい外部文献の検証やPML sourceの再監査も行っていない。
