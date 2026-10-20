# Wの共通未知位相：一周積分によるposterior predictive参照

2026-10-20。対象：Hiroshiba/check-nonml-saikyo-vocoder。**紙上導出のみ。現在studyへの条件追加も将来の採用も未決定で、ここから実行を開始しない。** 親からの最新状況では、新study `phase-origin-fixed-truth-analytic-q-20261020-v1` は真θ固定・既知解析q・既知250 Hz・同始点独立train/testのoracle位相とtrain-only OLS位相によるtest Gaussian score二本だけで開始指示済みである。以下を第三条件として追加しない。

## 1. Wだけのモデルとproper prior

N=4096、L=64、K=64、fs=16000 Hz、f0=250 Hzを保ち、t_n=n/fs、n=0,…,N−1とする。既知の白色分散を s=σ²=0.001>0 と書く。θの推定・周辺化はしない。

    m_n(φ)=q(n/L+φ),  φ∈R/Z,
    q(u)=a_0+Σ_(h=1)^3 a_h cos(2πhu),
    (a_0,a_1,a_2,a_3)=(48,−59,8,3)/√4081,
    Y_train,Y_test | φ は独立な N_N(m(φ),sI).

train/testが共有する未知位相は一つだけ。priorは円周の規格化Haar測度 π(dφ)=dφ、φ∈[0,1) とする。全質量1のproper priorであり、実直線上の不適切一様priorではない。追加の幅・集中度等のprior parameterは置かない。x=2πφを使うなら測度はdx/(2π)である。

これは予測規則を定義するためのpriorである。現在studyの固定truth φ0=0を、実際に一様抽選したtruthへ変更する指示ではない。

## 2. log尤度の位相依存は厳密に次数3

q²の最高調波は6。完全なL=64点の等間隔gridでは、1≤|h|≤6の各調波和が任意のshiftで0となるため、理想実数モデルで

    Σ_n m_n(φ)²
      = N[a_0²+(a_1²+a_2²+a_3²)/2]=N

が全φで一定である。各record D∈{train,test}の観測ベクトルy_Dについて

    C_(D,h)=Σ_n y_(D,n) cos(2πhn/L),
    S_(D,h)=Σ_n y_(D,n) sin(2πhn/L),
    A_(D,h)=a_h C_(D,h)/s,  B_(D,h)=−a_h S_(D,h)/s,
    T_D(φ)=Σ_(h=1)^3 [A_(D,h) cos(2πhφ)+B_(D,h) sin(2πhφ)],
    κ_D=−(N/2)log(2πs)−[||y_D||²+N−2a_0Σ_n y_(D,n)]/(2s)

と置けば、正規化Gaussian likelihoodは

    p(y_D|φ)=exp[κ_D+T_D(φ)]

となる。sin側の負号はcos(α+β)=cosα cosβ−sinα sinβから来る。**次数3なのはlog尤度の位相依存部T_Dであり、尤度exp(T_D)自体が次数3の三角多項式なのではない。** 後者には一般に高次のFourier成分もある。

この性質は理想解析qと完全周期gridについてのもの。各φでqをbinary64へ丸めた数値関数が同じ次数3であるとは主張しない。

## 3. 六係数から定義する一次元の厳密積分

六係数ベクトルをt_D=(A_(D,1),B_(D,1),…,A_(D,3),B_(D,3))とし、

    J(t)=∫_0^1 exp{Σ_(h=1)^3[A_h cos(2πhφ)+B_h sin(2πhφ)]} dφ
        =(1/2π)∫_0^(2π) exp{Σ_(h=1)^3[A_h cos(hx)+B_h sin(hx)]} dx

を定義する。これは全円周の一次元積分による解析的表示であり、数値積分を行ったという意味ではない。初等関数での閉形式を仮定する必要もない。

同じφを共有するevidenceとposteriorは

    Z(train)=∫ p(y_train|φ)dφ=exp(κ_train)J(t_train),
    Z(train,test)=∫ p(y_train|φ)p(y_test|φ)dφ
                 =exp(κ_train+κ_test)J(t_train+t_test),
    π(φ|y_train)=exp[T_train(φ)]/J(t_train).

従って求める正規化joint predictive densityは

    p_PP(y_test|y_train)
      = Z(train,test)/Z(train)
      = exp(κ_test) J(t_train+t_test)/J(t_train),
    log p_PP = κ_test+log J(t_train+t_test)−log J(t_train).

積分内で足すのはtrain/testの六係数であり、φを二つに増やさない。test係数が分子に現れるのは、固定した予測密度をそのtest観測値で評価しているからである。testでpriorや予測手順を選ぶこと、testにfitした位相へ置換することとは異なる。score単位は元のN sample座標のnats/record。p_PPは一般にGaussianではないので「第三のGaussian score」と呼ばない。

### 有限性・正規化

有限次元の有限実数データ、有限のq係数、既知s>0なら全係数は有限である。R(t)=Σ_(h=1)^3√(A_h²+B_h²)とおけば |T(φ)|≤R(t) から

    0<exp[−R(t)]≤J(t)≤exp[R(t)]<∞.

よって全evidenceは正かつ有限、posteriorと比は定義される。Gaussian密度の規格化と非負積分の交換から ∫_(R^N) p_PP(y_test|y_train)dy_test=1 となる。多峰性・flat likelihoodでも積分自体は存在する。これは浮動小数点でのoverflow/underflowや積分誤差の解決を保証しない。s=0の退化分布、非有限入力、不適切priorはこの結論の対象外である。

## 4. 別の独立φ積分、OLS plug-inとの違い

もしφ_trainとφ_testを独立にpriorから引く別モデルなら、joint evidenceはZ(train)Z(test)となり、

    p_ind(y_test|y_train)=Z(test)=exp(κ_test)J(t_test).

trainの位相情報がtest予測に入らない。これは今回の共有clockのposterior predictiveではない。両者が特殊なデータで一致する可能性は、モデルの同一性を意味しない。

Wの理想既知sでは、global OLS解はGaussian ML解であり、一様priorのposterior modeでもある。ただしmode集合から一つを選ぶ問題と、全円周を積分する問題は別である。

    φ_hat∈argmin_φ ||y_train−m(φ)||²=argmax_φ T_train(φ),
    p_plug(y_test|y_train)=exp[κ_test+T_test(φ_hat)],
    log p_PP−log p_plug
      =log J(t_train+t_test)−log J(t_train)−T_test(φ_hat).

最後の差は個々のtrain/test実現で一定符号ではない。posterior平均したlog likelihoodと、posterior平均したdensityのlogも別物である。Jensenの不等式は後者が前者以上であることを示すが、posterior modeでのtest log densityとの順序を与えない。

厳密predictiveは円周上のGaussian mixtureであり、

    E[Y_test|train]=E_post[m(φ)],
    Cov(Y_test|train)=sI+Cov_post[m(φ)]

が成り立つ。ただしこの二momentだけを用いた単一Gaussianへの置換は厳密ではない。位相による平均変動は六つのsin/cos方向に入るので、追加共分散のrankは高々6だが、一般にrank1ではない。局所chart内でm≈m_bar+dδ、posteriorがGaussianという追加近似のときに限り、sI+d Var_post(δ)dᵀ型のGaussian近似が得られる。frequentistなOLSの標準誤差をそのままposterior varianceと呼ばず、局所Gaussian近似やLaplace近似を上記full-circle積分と混同しない。

## 5. fixed truthの反復riskとBayes最適性

任意の正規化予測規則g(y_test|y_train)について、固定真値φ0の反復riskを

    R_(φ0)(g)=E_(train,test|φ0)[−log g(Y_test|Y_train)]

と定義する。現在studyが固定φ0=0で観測する反復と、このprior平均risk ∫_0^1 R_φ(g)dφ は別の評価対象である。prior平均の式を使うために現在データのφを再抽選・再評価することはしない。

真の階層モデルでも共有φ∼Uniform(R/Z)とするBayes評価では、有限な期待値の下で任意のgに対し

    E_(φ,train,test)[log p_PP−log g]
      =E_train[KL(p_PP(·|train)||g(·|train))]≥0.

従ってp_PPはこのprior平均log-score riskを最小化する。ここでの「BMA」は連続位相のposterior混合を指し、W/A/V/S/Jのモデル選択や平均化ではない。

**このBayes恒等式だけから、BMAが各固定truth・各train条件・各test実現で必ずOLSより良いとは言わない。** 特定の理想Wで対称性・equivarianceを別途証明すれば固定φ反復riskへ結論を移せる可能性はあるが、それは追加の論証であり、丸め・失敗選択・実装されたOLSへ自動適用しない。本稿はその優越主張を採用しない。

むしろ固定φ0では、各train条件付きにoracle p_(φ0)を基準として

    E_(test|φ0)[log g−log p_(φ0) | train]
      =−KL(p_(φ0)||g(·|train))≤0

が成立する。gがp_PPでもplug-inでも同じで、両者間の順序を与えるものではない。test実現の差が正でも矛盾しない。有限標本の優越、全truthへの一般化、局所「1/2 nats」を実測合否閾値にする主張はしない。

## 6. 将来もし比較する場合の別契約

採用を決めるなら、現在の二score研究とは分離して少なくとも次を先に固定する。本稿では具体的な実行値・手法を選ばない。

- W・既知s・既知q/F0・共有φ・同始点独立recordと、円周上の一様proper priorを明示。固定φ0の反復評価かprior平均評価かを区別し、位相sweepやtruth抽選を暗黙に追加しない。
- oracle、train-only OLS plug-in、full-circle posterior predictiveのどれを比較するか、scoreと集計・失敗の扱いを別研究として事前固定。現在の500pairの事後的な第三score追加・再ラベル・再評価はしない。
- 理想解析likelihoodと丸め生成/評価lawの関係、積分対象、正規化定数、評価精度・誤差管理・非有限処理・検証方法を固定。局所近似での代用は別の方法として明示する。
- 新studyのデータ来歴・seed・反復数・資源上限・保存物・停止条件・報告範囲を別に定める。prior parameterの探索、都合のよいtest結果による手法選択、noise再fitを混ぜない。

## 7. 五仮想役・二roundの反論応答

一人による机上の論点整理であり、五名の独立査読ではない。役は「生成モデル」「Fourier解析」「予測分布」「意思決定」「critic」の五つ。

### Round 1：定義と積分

1. 生成モデル「train/testでそれぞれφを積分する」→critic「共有clockが消える」→同じ一変数の積分Z(train,test)/Z(train)に修正。
2. Fourier解析「尤度はtrig3」→予測分布「指数を取れば有限次数ではない」→trig3はlog尤度の位相依存部と限定し、q²norm一定の根拠を記載。
3. 予測分布「積分すればGaussianに分散を足せる」→critic「円周の多峰性と非線形平均は残る」→厳密mixtureと局所Gaussian近似を分離。
4. 意思決定「一様priorは不適切では」→生成モデル「実直線ではなく円周上の全質量1」→dφとdx/(2π)の規格化を明示。
5. critic「分子にtestが入るのは漏洩」→予測分布「固定predictiveをtest観測で評価するため」→testでprior・手順・modeを選び直す行為と区別。

### Round 2：優越と運用への誤用

1. 生成モデル「現在の固定0 truthもprior draw扱いでよい」→意思決定「生成契約と評価母集団が変わる」→固定riskとprior平均riskを別記し、現在studyを不変にする。
2. Fourier解析「この式を丸めqへそのまま実装できる」→critic「φ依存丸めはtrig3を壊す」→理想式と有限精度の保証を別契約とする。
3. 予測分布「posterior modeより混合が各実現で必ず高score」→意思決定「Bayes最適性は期待riskの話」→Jensenの比較対象も明示し、点ごとの優越を棄却。
4. 意思決定「prior平均優越から固定φ優越へ進める」→critic「追加の対称性等の証明なしには飛躍」→別論証の可能性と、その未採用を明記。
5. critic「一次元なら今すぐquadして第三条件へ」→全役「現在契約は二scoreのみ」→解析表示と有限性の確認で停止し、実装・積分計算・再評価をしない。

## 8. 読取資料と実施範囲

参照した既存資料：`phase-origin-fixed-truth-score-plan-20261020.md`、`phase-uncertainty-control-20261020.md`（特に6.2）、`phase-origin-local-score-reference-20261020.md`。親から伝えられた現在studyの開始状況を、これら文書の古い未開始記述より優先した。

既存文書の読取り、紙上代数、このノートの保存だけを行った。数値実装、quadrature計算、データ取得・再評価、追加prior parameter、コード、Git変更、tests/smoke、実験開始は一切行っていない。**現在studyへの追加も将来比較の採用も未決定のまま。**
