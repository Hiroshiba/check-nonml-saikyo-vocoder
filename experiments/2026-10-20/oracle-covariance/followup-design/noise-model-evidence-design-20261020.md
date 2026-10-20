# 固定oracle雑音研究：勝者を原因確定にしない evidence 設計

2026-10-20。設計・文献調査・代数検討のみ。実装、追加計測、音声生成、Git変更、tests/smokeは行っていない。

## 1. 結論と現在の結果の読み方

最優先は既存5 familyを増減せず、既存結果の解釈を修正すること。新しい判定閾値を作ってWの結果を「直す」ことではない。親から受領した全2500 fit/test scoreの回収結果では、A/V/S/J truthは各100/100で同familyが最高held-out score、W truthはW単独3、Wを含むtie24、他構造単独73。一方で平均held-out scoreはWが全他候補より高い。これは矛盾しない。

採否は次のとおり。

- 共通総分散Eとshapeへの書換え：採用可能。同じ観測分布familyの再パラメータ化であり、モデル変更ではない。
- properなshape priorで低次元積分：設計として採用候補。ML winnerと異なる問いを扱うため、旧結果の置換・訂正とはしない。
- 共通p(E)∝1/E：条件付きで利用可能。ただし積分結果は元の残差空間上のproper marginal densityではない。「定数が消えるから常に安全」は棄却する。
- 重みの明示的根拠：同じscale群に対する残差方向のproper evidence。後述する球面上の密度は厳密に正規化され、親案のBayes factorと一致する。これは重みの根拠であり、既存raw test scoreを方向scoreに置換する提案ではない。
- 全振幅を含むproper evidenceが必要なら共通proper E priorを用いる。現時点ではそのhyperparameterを正当化する外部根拠は未確定。E=.001の固定truthから都合よく決めない。このproper E代替は保留案とする。
- posterior weightをcalibrated biological VUV、aspiration確率、真の原因の確定確率とは呼ばない。

一つの推奨候補は「共通reference scale priorによるtrain-onlyのformal posterior model weightを表示し、raw独立test上のproper BMA predictiveを旧plug-in予測と比較する保存入力再解析」。まだ採用・実行決定ではない。評価対象は指定5 family内の構造不確かさと将来のraw残差予測であり、振幅のprior predictive妥当性や生理的原因ではない。方向predictiveへの契約変更は推奨しない。

## 2. 勝率、平均score、確率は違う

各pair rのtrainで得たMLEをθ̂_m,r、test scoreをs_m,r=log p_m(y_test,r|θ̂_m,r)とする。勝者集合はargmax_m s_m,r。これは未来のtestを既に見た後の記述であり、trainだけで使える選択器の正答率ではない。

対比較Δ_m,r=s_W,r−s_m,rについて、P(Δ_m,r>0)とE[Δ_m,r]は異なる量。さらに「Wが4候補全部を上回る確率」はそれぞれの対比較確率とも異なる。少量の負差が多数、少数の大きな正差がある場合や、pairごとに異なる競合が勝つ場合、Wの単独勝率が低くても全対比較の平均差が正になり得る。この説明は実データの差の分布形を断定するものではない。

log scoreは予測密度全体を評価し、真の分布Pに対しE_P[log p−log q]=KL(P||Q)という関係を持つ。有限trainのplug-in候補では双方の推定誤差も入る。期待scoreの優位は各実現での優位を要求しない。Gneiting–Raftery [R1]はproper scoringの一般的根拠。既存の平均差・点別区間・tiesをそのまま主表示し、winnerは補助表示へ下げる。

α=0のS/JはWと同じ分布であり、MLEが境界へ落ちたときの同点は実装上も共通white経路になっている。これを「SとWの生理的原因を同時発見」と解釈しない。数値tieを新たな実用同等性閾値へすり替えない。

## 3. 同一familyを共通総分散で表す

以降x=y−qは保存済みoracle残差。平均を新たに推定しない。N=KL、L=64、K=64、N=4096、H=I。E=tr(Σ)/N>0、Σ=E C_η、tr(C_η)=N。

- W：C=I、shapeなし。
- A：C_nm=a^|n−m|、a∈[−.8,.8]。stationary初期状態を含み、innovation variance v=E(1−a²)。周期resetしない。
- V：Cは対角、C_nn=exp(b_c cosφ_n+b_s sinφ_n)/Z(b)、Zは既存L点平均。||b||≤1.5。全周期が整数なのでtrace=N。
- S/J：C=(1−α)I+α U Uᵀ、α∈[0,1)。Uは周期ごとのgまたはhを一列ずつ配置し、各列の二乗normはL、列間はsupportが異なり直交。元の白色分散v=E(1−α)、周期係数分散τ²=Eα。α=0でW、α→1でrank Kへの特異極限。α=1は元のv>0 familyに含まれない。

既存仕様のaとbの支持を保持し、αに新しい上限を置かない。実数数学上の離散RMS1と保存float64のnorm²の丸め差は区別する。原codeは実際のdirection norm² dを使用する。同一familyを厳密に保つならE=v+τ²d/L、α=(τ²d/L)/E、U*=sqrt(L/d)Uと表せる。保存データを再正規化せず、この表現変換の来歴を残す。丸め差を新しい物理効果としない。

## 4. scale積分と、その「proper」の範囲

Q_η=xᵀC_η^−1x>0とすると

p(x|E,η)=(2π)^−N/2 E^−N/2 |C_η|^−1/2 exp[−Q_η/(2E)]。

同じc dE/Eを全モデルへ使う形式積分は

m*(x|η)=c Γ(N/2) π^−N/2 |C_η|^−1/2 Q_η^−N/2。

導出はt=Q/(2E)の置換だけであり、MLE近似でもBICでもない。shape prior π_m(η)をproperにしてZ*_m(x)=∫m*(x|η)π_m(η)dη。全モデルでcが同じなら比から消える。

しかしm*(rx)=r^−N m*(x)なので、極座標の半径積分は∫_0^∞dr/rとなり発散する。shape priorがproperでも元データx上のm*はproper prior predictiveではない。Q=0の全ゼロ残差も対象外。共通improper priorの許容はモデル選択一般の自動的な性質ではなく、共通パラメータ・測度・不変性を吟味する必要がある。[R2,R3]

### 本件では方向データによる厳密な根拠がある

u=x/||x||∈S^(N−1)について、Gaussianの半径を実際に積分すると球面面積測度に関する密度は

f(u|η)=Γ(N/2)/(2π^(N/2)) |C_η|^−1/2 (uᵀC_η^−1u)^−N/2。

これは任意のE>0について同じで、球面上で積分1。既知meanを除いた共通scale群の最大不変量uを使うangular central Gaussianに対応する。式はここで直接導出したものであり、Tyler [R4]の方向分布という位置付けとも整合する。

m*(x|η)=2c||x||^−N f(u|η)。従ってproper shape priorを積分したf_m(u)同士のBayes factorはZ*_m(x)/Z*_j(x)と一致する。これなら「残差方向uの、指定shape priorに基づくproper evidence」と正確に言える。元のGaussian familyは変えないが、振幅を捨てた統計量への推論であり、全残差のproper evidenceと同義ではない。uへの正規化は推論上の変換であって、元実験の生成や保存残差を実現ごとに再正規化する指示ではない。

この説明で暗黙のimproper定数問題を避けられる範囲は、同一x・同一N・既知共通q・共通振幅変換・同一データ測度・scaleと独立なproper shape priorがある場合。モデルごとに異なるmean処理、切り出し長、noise floor、scale支持、変換、潜在初期状態の扱いを使うと本証明を再利用できない。

## 5. Jacobian、単位、priorの選択

Aのinnovation varianceをvと書くとv=E(1−a²)。変換(E,a)↔(v,a)のJacobianはdv da=(1−a²)dE da。従ってπ(a)dE/Eはπ(a)dv/vに一致する。「同じ1/v」はこの特定のscale measureでは整合する。innovation標準偏差σ_innovならv=σ_innov²なのでdv/v=2dσ_innov/σ_innov。モデルごとにvarianceとSDの表記を混ぜ、比例定数2を一部だけ捨ててはいけない。正しく同じmeasureをpush-forwardすればBayes factorは変わらない。

proper E priorではπ_E(E)dE=π_E(v/(1−a²))dv/(1−a²)。各モデルで独立に同じproper innovation priorを置くことは共通E priorではなく、別の科学的仮定である。

S/Jの(v,t)=(E(1−α),Eα)、t=τ²のJacobianはdv dt=E dE dα。従ってπ(α)dE dα/Eはπ(t/(v+t))dv dt/(v+t)²になる。独立な1/vと1/tを置く提案とは異なり、後者はゼロ分散境界で問題を生む。標準偏差でuniformにする場合も変換が必要。

単位をx′=c_x xへ変えればE′=c_x²E、dE′/E′=dE/E、同じNの全m*に|c_x|^−Nが掛かり比は不変。proper priorならhyperparameterも同じ単位変換を行う。dataだけをPCM gain変換してE priorを据え置かない。

### proper shape priorの一つの参照仕様

新結果へ適合させない参照測度として、Aはda上の一様1/1.6、Vは円板db_c db_s上の一様1/(π·1.5²)、S/Jはdα上の一様1を候補とする。これは既存支持しか使わず、積分はproper。ただし「情報がない唯一のprior」「生理学的に正しいprior」ではない。

Vの極座標b=(r cosθ,r sinθ)では密度r/(π·1.5²) dr dθ。r一様では円板一様と違う。S/Jでα一様はvariance ratio t/v=α/(1−α)に密度1/(1+t/v)²を誘導する。α→1も全許容familyに含め、数値都合で切り捨てたpriorへ変更しない。

モデルprior p(M=m)も別途必要。π_m=1/5は参照仕様であり、実際の原因頻度を示さない。Wにpoint massを持たせ、他familyの連続shape priorはW境界にatomを持たないため、exact Wの確率はWラベルに割り当てられる。ほぼwhiteのA/V/S/Jを除外したことにはならない。familyを複製すれば重みが変わるので、五候補という集合自体にも依存する。

### 全振幅のproper代替

E~Inverse-Gamma(ν,β)、ν>0、β>0を全候補で同じ総分散単位に置けば

m(x|η)=(2π)^−N/2 |C_η|^−1/2 [β^ν Γ(ν+N/2)/Γ(ν)] [β+Q_η/2]^−(ν+N/2)。

これをproper shape priorで積分すれば、x上のproper marginal likelihoodとなる。ν,βを既存test性能やtruth Eへ合わせない。共通有限区間のlog-uniform Eもproper代替だが、区間端を科学的に正当化する必要がある。proper priorの「非常に広い」極限は一般に無害と保証できない。今回は方向evidenceをformal model weightの根拠に使い、raw posterior predictiveを評価する一案を推奨候補とする。proper総分散priorの値は未決定として残す。複数priorを回して一番望ましい結果だけ選ぶ案は実施しない。

## 6. ML profile、evidence、posterior predictive

固定shapeのMLEはÊ=Q/Nなので

sup_E p(x|E,η)=(2π)^−N/2 |C|^−1/2 (Q/N)^−N/2 exp(−N/2)。

今回のscale-invariant m*とprofile likelihoodのshape依存部分は偶然同じで、共通Nでは比例定数だけ違う。だからshapeを最大化した値を使ってもevidenceになった、とは言えない。必要なのは全shape支持上のprior平均であり、最大点やその周辺の高さだけでなく幅とprior volumeが入る。Eをproperにすればこの比例自体も一般に消える。

方向evidenceに基づく重みはw_m(u_train)=π_m f_m(u_train)/Σ_j π_j f_j(u_train)。これは指定モデル集合・prior・oracle条件の下での方向データに条件付けたposterior model probabilityである。posterior oddsとBayes factorはprior oddsが等しいときだけ一致する。softmax(test ML score)、exp(−BIC/2)をそのままこのwと呼ばない。

予測が目的ならモデル選択argmax wではなく、パラメータを積分した予測をさらに平均するBMAを候補とする：[R5]。

p_BMA(x_test|x_train)=Σ_m w_m(x_train)∫p_m(x_test|E,η)p_m(E,η|x_train)dE dη。

ここでimproper scale経路を使う場合、train posteriorがproperであることを先に確認する。E|η,x_train~IG(N/2,Q_train/2)、shape posterior∝π_m(η)|C|^−1/2Q_train^−N/2。wは上記方向evidenceと一致する形式Bayes更新を用いる。これは共通scaleの形式priorによるproper posterior predictiveとして明示し、properなjoint prior predictiveと呼ばない。proper E経路なら通常の全データevidenceによるwを用いる。

train/testは同じθを共有するが、初期状態・innovations・周期効果は独立という元契約を保持。m(x_train,x_test)/m(x_train)を使う場合のjoint covarianceはblock diagonal C⊕Cであり、二つをつないだ長いAR列ではない。shared Eの積分は一回、Qは両recordの和、sample dimensionは2N。shape積分の比と、shapeごとの比のprior平均は交換できない。

定数を落とさない具体式として、I_n(D)=∫π_m(η)|C_D(η)|^−1/2 Q_D(η)^−n/2 dη とおけば、

p_m(x_test|x_train)=Γ(N)/[Γ(N/2)π^(N/2)] · I_2N(train,test)/I_N(train)。

jointでは|C_D|^−1/2=|C|^−1、Q_D=Q_train+Q_test。model比較だけでは共通Γ/πを省略できても、Nと2Nを比較するpredictive ratioでは省略できない。共通improper定数cのみ消える。この密度はraw x_testのLebesgue測度に関して積分1であり、旧Gaussian plug-in log densityと同じ観測・nats/recordで評価できる。

対してf_m(u_train)やf_m(u_test)のlog値は球面密度のscoreであり、raw scoreと同じ観測・単位として比較しない。仮にdirection predictiveを作るなら∫f(u_train|η)f(u_test|η)π_m(η)dη / f_m(u_train)になるが、各recordを別々に単位norm化した観測契約である。これは共通Eを一回積分したraw joint2Nの式とは異なる。今回はその課題へ切り替えない。

評価するのはlog p_BMA(test|train)であり、Σ_m w_m log p_m(test|train)ではない。model posteriorが高いことと、未来log scoreが常に最高であることは別。BMAも指定集合外を救済せず、既存MLEより必ず良くなる保証はない。

## 7. 数値積分設計：次元、特異端、error budget

Wはshape積分なし。Aは1次元区間、Vは2次元円板、S/Jは各1次元。full covarianceのN×N dense積分やMCMCは不要。shape prior込みのlog integrandを最大値でshiftし、log-sum-exp形式の決定論的適応求積を第一候補とする。Aはstationary precisionの正の二乗和、Vはphase energyとlog-sum-exp、S/Jは方向・直交補空間の二乗和を使う。元codeの安定な計算契約を継ぐが、既存MLE solver成功を積分精度の証明に流用しない。

S/Jについてε=1−α、λ=1+(L−1)α=L−(L−1)ε、A_x=Σ_k(u_dirᵀx_k)²、B_x=Σ_k||x_k−u_dir u_dirᵀx_k||²とする。u_dirは各周期方向のunit vector。

log|C|=(N−K)log ε+K log λ、Q=B_x/ε+A_x/λ。

scale積分のkernelは代数的に

k(ε)=ε^(K/2) λ^(−K/2) [B_x+ε A_x/λ]^(−N/2)。

この形なら∞−∞を作らずα→1を扱える。B_x>0ならk(ε)はε^(K/2)で0へ向かう。uniform α priorで0<δ≤1の省略tailは

∫_0^δ k(ε)dε ≤ B_x^(−N/2) δ^(K/2+1)/(K/2+1)。

Γ等の共通係数は同じように掛ける。boundはlooseでも正しく、log領域で計算する。勝手なα=1−10^−k cutoffでfamilyを変更せず、tail boundが数値誤差予算へ収まることを要求する。α=0も含めて求積し、logit変換ならdαのJacobianを忘れない。Vを極座標化する場合もr因子が必須。

B_x=0の例外では特異端のintegralが発散し得る。Gaussianの非退化familyでは確率ゼロだが、丸め・量子化・人工入力で起こり得る。floorで隠さず、posterior propriety gate失敗として報告する。B_xを全energy−A_xの差で作らず、直交残差の二乗から直接得る。全ゼロxも失敗扱い。

数値精度の事前目標案は各log evidenceの絶対誤差≤10^−6 nats/record。科学的同等性幅・採用閾値ではなく計算上の目標。内訳は丸め・統計量評価2×10^−7、内部求積6×10^−7、未積分tail2×10^−7。二モデルのlog BF誤差は和で≤2×10^−6。全log evidence誤差がδ以内なら正規化weightの誤差も保守的にe^(2δ)−1以下と評価できる。proper E経路ではそのintegrandに対応するtail boundを別途導出する。

求積ライブラリのerror estimateは数学的保証ではない。段階的細分化と異なる座標・求積則による照合、解析tail bound、必要なら区間演算/高精度照合を設計に含める。これらを実施したとは言わない。丸め上界を検証できなければ「収束診断上の精度」でありcertified errorではない。目標を満たさないpairは不確かなevidenceとして残し、winnerへ丸めない。積分許容誤差を結果都合で緩めない。

## 8. train/test、calibration、唯一の追加解析案

既存100pair×5truthは固定された5点のconditional performance評価である。prior predictiveに従うmodel/shape/scaleの母集団ではない。既にtest結果を見て今回の考察を始めたため、次の解析は事後設計であり、新規独立confirmatory testとは表現しない。各pairの推論入力はtrainのみ、既存testは評価のみ。100trainを同じθの一つの長いtrainへpoolしない。truth labelをpriorやposteriorの入力にしない。

追加提案は一つだけ：「保存済み500pairに対する、事前凍結した方向evidence重みと形式共通scale posterior predictive/BMAの記述的再解析」。再生成・追加pairs・新truth・新shape familyなし。目的は勝者だけで捨てていた不確かさを表示し、旧MLE予測と新しい平均予測のscoreを同じtestで併記すること。今回これを実行しない。実行前に参照shape/model prior、積分gate、表示方法、失敗の扱いを凍結する。priorを結果へtuneしない。旧2500fitと旧scoreを削除・再定義せず、派生解析として別保存する。特にWの73件はtestを見た後のargmaxであり、train-only posteriorの分類失敗率と同じ比較基準ではない。「73件がBayesで何件改善した」という主評価は禁止する。重み全5成分、model entropy、shape posteriorの範囲、予測score差を表示し、confidence cutoffを作らない。

この一案には既存saved float64残差とgeometryだけで足りる。ただし「確率calibrationが実証された」とする目的には足りない。properなjoint priorに基づきM~π、η~π_M、E~π_E、x~p_Mを生成した別データが必要である。方向posteriorだけのcalibrationならEは方向分布から消えるため固定でもよいが、Mとshapeは宣言したpriorから生成する必要がある。こうしたprior predictive実験は今回の追加提案に含めない。[R6]のSBCは計算検証の枠組みであり、生物学的妥当性の認証ではない。

厳密なBayes条件下では E[1{M=m}|w_m(X)]=w_m(X) がjoint prior predictive平均で成り立つ。これは反復条件付き期待値の法則による数学的関係で、固定truth5点の100/100からは導けない。prior-onlyな報告が無条件calibrationを満たす場合さえあるため、calibrationだけでも識別・有用性の証明にならない。

## 9. 5仮想役による2往復

実在の5名による査読ではなく、設計者が五つの視点から反論を構成したもの。

### 第1往復：提案、反論、修正

1. 生成担当：「Eとshapeで全familyを揃える」。批評家：「innovation scaleを同じにするとAだけ総分散が違う」。修正：E=trΣ/Nを共通定義し、AのJacobianとstationary初期分布を保持。
2. 統計担当：「1/Eを積分しproper evidenceにする」。批評家：「元空間では半径積分が発散する」。修正：formal scale evidenceとproper方向evidenceを分け、proper E prior代替も示す。
3. 数値担当：「αを.999で切れば安定」。生成・批評家：「元familyとpriorを変更する」。修正：ε表現と解析tail bound、未達gateを採用。
4. 音声・観測担当：「A/V/S/Jが100/100なら原因確定」。統計担当：「oracle covariance familyの固定5点だけ」。修正：未知q、phase、H、生理学と切り分ける。
5. 批評家：「Wだけthresholdで救う」。他4役：「見た結果に合わせた判定器になる」。修正：平均scoreとmaximum winnerの対象差を説明し、閾値追加なし。

### 第2往復：反例、再修正、未解決

1. 生成担当：「dE/Eなら全parameterizationで同じ」。統計・批評家：「測度のpush-forwardが必要。SD/varianceの定数も揃える」。再修正：AとS/JのJacobianを明記。未解決：proper E hyperparameterの外部根拠。
2. 統計担当：「重みを出せばcalibrated」。音声・批評家：「固定truthでposterior calibrationを証明できない」。再修正：joint prior predictive条件を明示。未解決：集合外誤指定下の信頼性。
3. 数値担当：「adaptive quadratureのsuccessがあれば十分」。批評家：「鋭いpeakとα端の見落としがある」。再修正：別座標照合、tail bound、丸め予算。未解決：実装前なので達成精度は未確認。
4. 音声・観測担当：「test phaseを合わせてscoreを改善」。生成・統計担当：「J自身を吸収し、予測条件を変更する」。再修正：保存oracle座標を保持。未解決：PMLが測定phase原点を提供しない。
5. 批評家：「モデルを追加すれば全不確かさを表せる」。他4役：「混合・filter・未知meanを今追加すると元研究の問いが変わる」。再修正：5モデル条件付き不確かさだけを表示。未解決：自然音声と混合原因は対象外。

## 10. 実施しない案と停止点

- score winnerを原因存在の確定とする、softmax scoreやBIC指数をcalibrated cause posteriorと呼ぶ。
- Wの既知結果から閾値、prior、α支持、反復数を調整する。
- 全部入りF、新しい混合family、unknown mean/filter/phase、PML変更、自然音声や音質評価を今回追加する。
- testを見て最良priorを選び、そのtest scoreを未使用データでの汎化性能と呼ぶ。
- posteriorにおけるα>0の確率をS/J原因存在確率と同一視する。continuous S/J slab内ではα=0の確率が0なのはprior設計の結果でもある。
- improper scale evidenceをx上のproper prior predictiveと呼ぶ、またはproper priorが不要だと一般化する。
- 通常χ²や正則BICをゼロ分散境界へ無検証で使う。境界の漸近理論は一般に非正則 [R7]。
- 新規calibration Monte Carlo、追加計測、tests/smoke、実装、Git変更。

現時点で完了したのは、同一familyの不確かさ解釈と計算法の設計。未解決は参照priorを科学的にどう説明するか、proper E priorを要するか、実際の求積誤差の検証、集合外・未知mean/phaseへの外挿である。参照priorは物理的正解でなく、選んだ仮定を見える形にするための候補として扱う。

## 一次資料と確認範囲

以下の数学的特殊化・tail bound・Jacobian・球面密度導出は本設計の解析であり、文献がこのvocoder実験を検証したという主張ではない。

- [R1] Gneiting & Raftery (2007), Strictly Proper Scoring Rules, Prediction, and Estimation. 著者大学公開PDF本文を確認。proper log scoreの一般原理に使用。https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
- [R2] Kass & Raftery (1995), Bayes Factors. 著者サイト検索取得本文・書誌を確認。PDFの直接取得はtimeout、大学mirrorは404。Bayes factorがprior平均であること、BICは近似であることの範囲に引用し、未取得の節を精読済みとはしない。https://www.stat.cmu.edu/~kass/papers/bayesfactors.pdf
- [R3] Berger, Pericchi & Varshavsky (1998), Bayes Factors and Marginal Distributions in Invariant Situations. 著者大学の研究抄録を確認。同一群構造に関する不変モデルでformal marginalを扱う背景。一般定理を本件へ無検証で援用せず、球面密度を直接導出。https://www2.stat.duke.edu/~berger/papers/ibfmarg.html
- [R4] Tyler (1987), Statistical analysis for the angular central Gaussian distribution on the sphere, Biometrika 74(3), 579–589. 出版社の書誌・抄録を確認し、方向分布の位置付けを確認。全文は今回未取得なので、式の根拠は本書内の独立導出とする。https://doi.org/10.1093/biomet/74.3.579
- [R5] Hoeting, Madigan, Raftery & Volinsky (1999), Bayesian Model Averaging: A Tutorial. 出版社抄録と著者大学の訂正版案内を確認。モデルを一つに固定することがmodel uncertaintyを捨てるという位置付けに使用。https://doi.org/10.1214/ss/1009212519 ; 訂正版案内 https://sites.stat.washington.edu/raftery/Research/bma.html
- [R6] Talts, Betancourt, Simpson, Vehtari & Gelman (2018), Validating Bayesian Inference Algorithms with Simulation-Based Calibration. 著者論文arXiv抄録・本文案内を確認。SBCをBayesian計算検証として区別。https://arxiv.org/abs/1804.06788
- [R7] Self & Liang (1987), Asymptotic Properties of Maximum Likelihood Estimators and Likelihood Ratio Tests under Nonstandard Conditions. 境界の非正則性に関する原論文。大学公開PDFの検索取得本文・抄録を確認。本件の具体的混合χ²分布を引用・断定しない。https://www.stat.cmu.edu/~brian/763-2015/week06/papers/self-liang-1987.pdf

内部参照：cyclic_noise_identification_design_20261020.md、oracle-noise-interpretation-plan-20261020.md、oracle-noise-source-20261020/CONTRACT-ja.md、model_math.pyを読み、既存の平均・初期状態・train/test・direction norm・white境界経路の契約を確認した。新しい計測結果は本書に追加していない。
