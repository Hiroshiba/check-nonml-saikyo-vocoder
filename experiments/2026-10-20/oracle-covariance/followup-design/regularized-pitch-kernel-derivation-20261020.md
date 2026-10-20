# Regularized pitch kernel の共通 scale 測度による形式的解釈

2026-10-20。紙上の独立導出。prior の採用、実装、コード実行、tests/smoke、数値 run、Git 変更、既存 500 pair 再解析の変更は行っていない。文書読取り、原著の一次本文確認、本書の保存のみ。

## 0. 判定

提示された仮説は、以下の限定された意味で成立する。

1. 正規化された conditional g-prior と共通の非確率測度
   μλ(dE)=E⁻¹ exp[−λ/(2E)]dE、λ>0
   を使うと、固定 C の H1/H0 の形式比は既存 regularized cod の g-kernel と一致する。
2. proper hyper-g を記号 δ>2 で置けば、前文書の ₂F₁ 式に R²λ=J/(T+λ) を入れた式が厳密に得られる。δ の値は選ばない。
3. λ>0 により、完全 fit と全零観測も含め、固定の正定値 C に対する proper g 混合および通常の posterior の正規化が可能になる。
4. 全モデルに同じ proper scale prior の近似列を使えば、上側切断 U→∞ と IG(ν,λ/2), ν↓0 の両方で、proper Bayes factor がこの形式比へ収束する。

ただし μλ は E→∞ で発散する improper 測度である。上記は「proper raw prior predictive がこの密度へ収束する」「一般に improper prior の比較は安全」「原実装全体を再現した」という意味ではない。固定 λ の形式比は振幅に依存し、前文書の proper angular evidence による正当化は使えない。

## 1. 前提と単位

同じ元観測 y∈Rᴺ、同じ N>0、同じ窓・サンプル順・前処理を全候補で使う。Z∈Rᴺˣᵈ は固定 F0・固定 harmonic 次数に対応する full column rank のデザイン、0≤d≤N。DC 列や中心化を新たに加えない。

H1:

 y | β,E,C ∼ N(Zβ, EC),
 β | E,g,C ∼ N(0, gE G⁻¹),
 G=ZᵀC⁻¹Z,  g>0.

H0:

 y | E,C ∼ N(0, EC).

C は無次元の対称正定値行列で、shape を比較するなら tr C=N に統一する。このとき E は一標本当たりの平均周辺雑音分散、窓全体の期待雑音二乗ノルムは NE である。E を「窓全体の energy」と呼ばない。

 T=yᵀC⁻¹y,
 J=yᵀC⁻¹Z G⁻¹ZᵀC⁻¹y,
 S=T−J≥0,
 α=N/2,
 λ=N varSpeech>0.

y の振幅単位を A とすると E、T、J、λ はいずれも A² の次元を持つ。T、J、λ がサンプル数分の和として現れることと、物理次元が A² であることは両立する。g、C、R²λ は無次元。今回の既存 white 診断との代数対応では varSpeech=5e−6 をそのまま用いるが、別の振幅単位へ無変換で持ち込めない。

λ は既知で y や候補に依存しないものとする。λ=N varSpeech は N に依存する prior 測度の族を定める。固定 N の候補比較の解釈であって、異なる窓長を同じ prior で比較したことにも、長い窓と短い窓の周辺分布が整合する一つの process prior を与えたことにもならない。

将来 train/test の joint/train 比を同一 prior からの posterior predictive として扱う場合は、λ を同じ prior 定数として joint でも固定する必要があり、joint の観測次元が 2N になったことを理由に λ を 2 倍する処理はその同一 prior の posterior predictive ではない。

μλ は E=0 付近では可積分だが、∞ 側で ∫dE/E の発散を残す。IG(0,λ/2) を proper 分布名として用いない。共通の任意乗数 k>0 を付けることはできるが、その k を候補ごとに変える自由はモデル比に残ってしまう。

## 2. β と E の積分

正規化された係数 prior の密度は

 (2πgE)⁻ᵈ⁄² |G|¹⁄² exp[−βᵀGβ/(2gE)].

この係数を含めて β を積分すると

 y | E,g,C ∼ N(0, EB),
 B=C+g ZG⁻¹Zᵀ,
 |B|=|C|(1+g)ᵈ,
 Q=yᵀB⁻¹y=T−[g/(1+g)]J=S+J/(1+g).

0≤Q≤T。有限 g、非零 y なら Q>0 だが、本書では Q=0 でも λ>0 がある。

μλ の乗数を全候補で 1 と固定した形式量を m*λ と書く。A_g=Q+λ と置けば

 m*λ(y|C,g,H1)
 = (2π)⁻α |B|⁻¹⁄² ∫₀∞ E⁻α⁻¹ exp[−A_g/(2E)]dE
 = Γ(α) π⁻α |C|⁻¹⁄² (1+g)⁻ᵈ⁄² (Q+λ)⁻α.

変数 t=A_g/(2E) により積分は (2/A_g)^α Γ(α)。提示仮説の π と 2 の係数も正しい。

H0 は B=C、Q=T なので

 m*λ(y|C,H0)=Γ(α)π⁻α |C|⁻¹⁄²(T+λ)⁻α.

従って、同じ C、N、λ と μλ を使う比は

 BF*₁₀(g;C)
 =(1+g)⁻ᵈ⁄² [1−{g/(1+g)}R²λ]⁻α,
 R²λ=J/(T+λ).

有限の y では 0≤R²λ<1。C=I なら T=yᵀy、J は通常の harmonic 射影量となり、λ=N varSpeech の代入で指定された regularized cod の固定 g-kernel と一致する。

これは元実装がこの prior を意図していたという歴史的主張ではない。正則化の数式に対する一つの形式的な逆解釈である。Laplace 近似の変数、Jacobian、定数、数値 clip、energy-floor、状態遷移、候補 prior、H0 posterior mass はこの導出では再現していない。

## 3. proper hyper-g の記号積分

具体値を採用せず、

 πδ(g)=(δ−2)/2 × (1+g)⁻δ⁄²,  δ>2

と仮定する。この密度の積分は 1。t=g/(1+g) と置くと

 BF*₁₀(C)
 = (δ−2)/2 ∫₀¹ (1−t)^((d+δ)/2−2)
                 (1−tR²λ)⁻α dt
 = (δ−2)/(d+δ−2)
   × ₂F₁(α,1;(d+δ)/2;R²λ).

Euler 積分の条件 (d+δ)/2>1 と R²λ<1 は満たされる。前文書の式への regularized R² の代入は、この新しい scale 測度から再導出した結果として正しい。単なる無根拠な式の差替えではない。

λ=0 の完全 fit では δ>N−d+2 が必要だったが、λ>0 を固定した本書では δ>2 だけで有限になる。ただし λ↓0 と完全 fit の極限は一様ではない。λ→0 で以前の発散が再出現し得ることは矛盾ではない。

H0 に使わない g を形式上付加しても、proper πδ を積分すれば 1 となる。H0 に余分な任意定数は持ち込まない。

### 不完全 beta による同値表示：指定された条件内だけ

この小節だけ a=N/2、c=(d+δ)/2、r=R²λ と書く。noise shape の記号 a とは別である。c>1、a−c+1>0、0<r<1 の条件を仮定する。非正規化不完全 beta を

 Bᵣ(p,q)=∫₀ʳ u^(p−1)(1−u)^(q−1)du

と定義する。正規化された regularized incomplete beta Iᵣ(p,q) ではない。Iᵣ を使う表現へ変えるなら完全 beta B(p,q) の係数も必要になる。

上記 Euler 積分で

 u=r(1−t)/(1−rt)

と置くと、t=0→u=r、t=1→u=0 で、

 1−t=u(1−r)/[r(1−u)],
 1−rt=(1−r)/(1−u),
 dt=−(1−r)/[r(1−u)²]du.

したがって直接の変数変換により

 ∫₀¹ (1−t)^(c−2)(1−rt)⁻ᵃ dt
 =r^(1−c)(1−r)^(c−a−1)
   ∫₀ʳ u^(c−2)(1−u)^(a−c)du
 =r^(1−c)(1−r)^(c−a−1) Bᵣ(c−1,a−c+1).

Euler 積分の係数 c−1 を戻せば、依頼された恒等式

 ₂F₁(a,1;c;r)
 =(c−1)r^(1−c)(1−r)^(c−a−1)
   Bᵣ(c−1,a−c+1)

が成立する。従って hyper-g を積分した BF は

 BF*₁₀
 =(δ−2)/2 × r^(1−c)(1−r)^(c−a−1)
   Bᵣ(c−1,a−c+1).

r↓0 では Bᵣ(c−1,a−c+1)∼r^(c−1)/(c−1) であり、

 BF*₁₀ → (δ−2)/[2(c−1)]
        = (δ−2)/(d+δ−2).

r=0 そのものには、個別に発散・消失する因子の積を直接代入せず、この有限極限または元の積分を用いる。

指定条件内では全因子が正なので、形式的には

 log BF*₁₀
 =log[(δ−2)/2]+(1−c)log r
  +(c−a−1)log(1−r)
  +log Bᵣ(c−1,a−c+1)

とも書ける。これは exact g 積分を対数領域で扱う将来の候補となる恒等式であり、数値アルゴリズムの安定性の証明ではない。不完全 beta の計算、極小 r での相殺、underflow、ライブラリの log 関数対応などは一切検証していない。a−c+1≤0 など指定条件を満たさない場合へは本小節の主張を拡張しない。prior の具体値選択・採用、実装、計測は行わない。

## 4. 完全 fit・全零窓・posterior

### 任意の proper g prior での有限性

固定 C について全 g>0 で

 0<m*λ(y|C,g,H1)
 ≤Γ(α)π⁻α |C|⁻¹⁄² λ⁻α.

従って任意の proper probability measure Πg による積分は有限かつ正。g の正モーメント条件は不要である。g=∞ の原子はこの契約に含めない。g=0 の原子を追加するなら、係数 prior は β=0 の点質量として定義する。

非零の完全 fit y∈col(Z) でも Q=T/(1+g) であり、g→∞ の integrand は定数倍の (1+g)⁻ᵈ⁄² へ移る。非正則化の場合の (1+g)^((N−d)/2) の成長は消える。

y=0 なら T=J=Q=0。m*λ は有限であり、

 BF*₁₀(0;C)=∫(1+g)⁻ᵈ⁄² Πg(dg).

hyper-g なら (δ−2)/(d+δ−2)。d>0 で g>0 に確率 1 を置くなら 1 未満で、d=0 なら 1。これは H0 の posterior probability そのものではない。離散 model prior と他候補の evidence が別に必要。

d=N の場合、非正則化の方向比は 1 だったが、本書の raw 形式比は一般に 1 ではない。振幅情報と λ という固定 scale があるためである。

### E と β の posterior propriety

β 積分後、固定 g,C の通常の正規化式は

 E | y,g,C,H1 ∼ IG(α,(Q+λ)/2).

H0 は IG(α,(T+λ)/2)。α>0 と λ>0 により、y=0 を含めて proper である。ここで IG(a,b) の密度は bᵃ/Γ(a) E⁻ᵃ⁻¹ exp(−b/E)。

また β|E,g,y,C は平均 [g/(1+g)]G⁻¹ZᵀC⁻¹y、covariance E[g/(1+g)]G⁻¹ の proper Gaussian である。上の g evidence の有限性と合わせ、固定 C、proper Πg に対する joint (β,E,g) posterior も proper になる。posterior が proper であることは prior predictive を proper にしない。また proper であることは任意の posterior moment の存在を意味しない。

y=0 では E posterior は IG(α,λ/2) となり g に依存せず、g posterior は Πg(dg) を (1+g)⁻ᵈ⁄² で tilt したものになる。

### shape を混合する条件

例えば C(a)ᵢⱼ=a^|i−j|、a∈[−0.8,0.8] といった compact な非退化 family では determinant に正の一様下限がある。proper shape prior との混合でも上の有界性が成立する。

任意の非compact family、特異 C に近付く family まで λ>0 だけで保証することはできない。|C|⁻¹⁄² が発散し得るからである。その場合は shape 積分と正規化を別途証明する必要がある。rank 欠損 Z も G⁻¹ の前提を破るため、擬似逆と旧 d を無断で使わない。

## 5. 共通 proper 上側切断 prior による比の極限

全候補に同じ U>0 を用い、

 pU(E)=1{0<E<U} E⁻¹ exp[−λ/(2E)] / ZU,
 ZU=∫₀ᵁ E⁻¹ exp[−λ/(2E)]dE
   =Γ(0,λ/(2U))

と置く。Γ(s,x)=∫ₓ∞ t^(s−1)e⁻ᵗdt は上側不完全 Gamma 関数。λ>0 なので有限 U で ZU は有限かつ正。この prior と normalized conditional g-prior は proper であり、任意の有限 U の raw prior predictive（事前予測密度）も proper。

固定 g の prior predictive（事前予測密度）は正確に

 mU(y|C,g)
 =π⁻α |B|⁻¹⁄² (Q+λ)⁻α
   Γ(α,(Q+λ)/(2U)) / ZU.

ZU→∞ だが、

 ZU mU(y|C,g) → m*λ(y|C,g).

非負 integrand の単調収束を、共通の proper g・shape 測度にも適用できる。従って両モデルの形式量が正かつ有限なら

 mU(y|M1)/mU(y|M0) → m*λ(y|M1)/m*λ(y|M0).

有限 U の比には不完全 Gamma の因子が残り、一般に正則化 kernel と完全一致しない。一致はこの指定の共通極限である。

注意すべき点は prior predictive mU(y|M) 自体は各固定 y で 0 に収束すること。m*λ は normalized prior predictive の点wise極限ではなく、発散する共通 ZU を掛け戻した形式量である。確率質量が無限遠へ逃げるため、点wise 0 と各 U で積分 1 は矛盾しない。これは事前予測密度についての主張であり、観測から学習した後の posterior predictive（事後予測密度）が 0 に収束するという主張ではない。

## 6. 共通 IG(ν,λ/2), ν↓0 による比の極限

ν>0、b=λ/2 を全候補で共通にし、

 pν(E)=b^ν/Γ(ν) E⁻ν⁻¹ exp(−b/E)

を使う。有限 ν では proper。固定 g の prior predictive（事前予測密度）は

 mν(y|C,g)
 = Γ(α+ν)/Γ(ν) × π⁻α λ^ν
   |B|⁻¹⁄² (Q+λ)⁻(α+ν).

Γ(ν)ν→1 より

 mν(y|C,g)/ν → m*λ(y|C,g).

同じ C の有限 ν の H1/H0 比は

 (1+g)⁻ᵈ⁄²
 [1−{g/(1+g)}R²λ]⁻(α+ν),

となり、ν↓0 で所望の式に戻る。proper hyper-g 積分なら ₂F₁ の第1引数が α+ν であり、極限で α に戻る。

g 混合との極限交換も正当化できる。0<ν≤ν0 に対し λ^ν(Q+λ)⁻ν≤1、Γ(α+ν)/(νΓ(ν)) は有界、(1+g)⁻ᵈ⁄²≤1 である。従って先の λ⁻α と determinant の bound による支配収束が使える。compact 非退化 shape 混合も同様。

よって proper BF の極限は上側切断と同じ。ただしこちらも prior predictive mν→0 であり、ν を割った形式量だけが m*λ へ収束する。この 0 への収束も事前予測密度の話で、学習後の posterior predictive についての結論ではない。μλ を proper prior の弱極限の probability measure と呼べない。λ→0 はこの検討とは別の極限である。

## 7. 「共通 improper 測度なら合法」の正確な範囲と反例

本書で認められるのは、指定した共同モデル・共通近似列からの model odds の極限、またはその極限と一致する generalized Bayes の形式比という限定的な解釈である。必要条件は少なくとも次の通り。

1. 同一の観測空間、同じ元 y と N、同じ基準測度 dy。候補ごとの fit 残差を新しい観測に置換しない。
2. E の物理的意味と単位、λ、scale 測度の乗数および近似規則を H0、H1、全 shape で共通に固定する。
3. β prior は各候補で正規化され、g・shape・離散候補の prior は proper である。異なる d の flat β prior の任意定数を相殺したことにはならない。
4. 比の分子・分母の形式積分が正かつ有限。shape 混合や無限候補数では追加の積分可能性が必要。
5. λ や prior cutoff を観測した y に合わせて最適化してから、通常の事前分布による BF と呼ばない。data-dependent 設計は別途扱う。
6. finite-prior predictive とその比、形式量、posterior probability を区別する。model prior odds は別に必要。

同じ λ を使うだけでは十分でない。例えば基準単位 Eref を固定し、モデルごとに

 UM=Eref (U/Eref)^cM, cM>0

という異なる cutoff 列を使えば、ZU,M の発散率は cM に比例する。このとき proper predictive の比の極限は

 (c0/c1) × m*λ(y|M1)/m*λ(y|M0)

となる。各候補で「同じ improper kernel に近付く」と言えても、正規化の近付き方を共有しなければ任意因子が残る。IG 列でもモデルごとに νM=cMν とすると同様に比へ c1/c0 が入る。

この反例は「すべての proper 近似で同じ BF に決まる」という主張を否定する。本書の二つの共通列が一致することは有用だが、improper prior 一般の安全証明ではない。

### shape 間で落としてはいけない項

同じ C の H1/H0 比では |C|⁻¹⁄² と (T+λ)⁻α が相殺する。異なる C、または shape mixture 同士では相殺しない。shape を混合するなら各モデルの m*λ を proper shape prior で積分した後に割る。固定 shape の BF を shape prior で単純平均するのは一般に誤り。

H0 にも noise shape の候補とその prior を定義する。H1 だけに colored covariance を許すことは比較の科学的意味を変える。H0/H1 の shape prior が異なる場合も数学的な共同モデルは作れるが、その差を明記しなければならず、「同じ noise 不確かさを公平に扱った」とは言えない。

## 8. raw density、方向 evidence、振幅変換

各 g で、非負積分の順序交換により

 ∫Rᴺ m*λ(y|C,g)dy
 =∫₀∞ μλ(dE)
 =∞.

λ は原点付近を有限化するが、遠方の半径方向の対数発散は消さない。したがって finite-prior predictive は proper であっても、再スケールされた形式量 m*λ は raw y 上の probability density ではない。共通 E の定数が比で消えることと、raw density の積分が 1 になることは別である。

振幅を y→cy に変え、λ を固定すると

 R²λ(cy)=c²J/(c²T+λ)

なので比は一般に変わる。前文書の m*(y)=2||y||⁻ᴺ pdir(y/||y||) という共通半径分離は成立しない。

より強く、どの proper scale prior を使っても、固定 B の Gaussian scale mixture の方向密度は元の angular Gaussian 密度のままである。E は半径だけを変えるためである。従って今回の proper 近似列から方向だけを観測すれば、得られるのは非regularized の方向比であり、R²λ を使う比ではない。本書の解釈は方向 evidence で救済できない。

物理的な単位変更として y→cy、E→c²E、λ→c²λ を一緒に変えれば BF は不変になる。これは λ を固定した signal gain 変化への不変性とは違う。E の代りに窓全体の scale F=NE を用いるなら、exp[−Nλ/(2F)]dF/F と正しく変数変換する必要がある。

## 9. C の正規化と C 依存の β prior

C→cC と E→E/c は同じ covariance を表す。しかし fixed λ の μλ はこの再パラメータ化に対して形をそのまま保たず、λ→λ/c が必要になる。λ=0 の dE/E と違い、shape の任意の scale を無視できない。tr C=N を全候補に強制するのは E と λ の意味を揃えるためである。

conditional g-prior の C 依存は単なる数値上の whitening ではない。

 E[(Zβ)ᵀC⁻¹(Zβ)|E,g,C]=gEd

という whitened signal energy の校正を仮定している。元座標での β covariance は gE(ZᵀC⁻¹Z)⁻¹ なので、noise shape を変えれば信号 prior も変わる。元座標の期待 signal energy gE tr(ZG⁻¹Zᵀ) も一般に C 依存である。

従って W/A 比は「共通の β prior を固定した純粋な noise covariance 比」ではなく、この条件付き prior を含む共同モデルの比である。元座標で C 非依存の β prior を希望すれば、別の B と determinant が必要で、本書の簡約をそのまま移せない。

Z の可逆な basis 変換では、正規化 prior と係数の Jacobian を保てば ZG⁻¹Zᵀ は不変。rank が変わる場合は別で、独立な rank-r basis と r 次元の prior を定義し直す必要がある。

## 10. 5仮想役・2往復

以下は一人の導出を五つの視点で点検した仮想レビューであり、独立した五人・五エージェントが検証したという主張ではない。

### 第1往復：異議 → 応答

1. 測度担当：「λ>0 なら IG prior で proper ではないか。」→ shape=0 では ∞ 側が発散する。μλ は非確率測度であり、finite ν>0 の IG と区別した。
2. 線形代数担当：「β を積分したのに指数 N/2 が残るのは誤りでは。」→ normalized g-prior の E⁻ᵈ⁄² が Gaussian 積分の Eᵈ⁄² と相殺する。det B と Q から係数も確認した。
3. 極限担当：「proper truncated prior から形式密度に収束するのか。」→ raw predictive 自体は 0 に収束する。共通正規化を掛け戻した量と比だけが非零の極限を持つ。
4. 退化担当：「完全 fit で hyper-g の尾部条件が必要なはず。」→ λ=0 では必要。本書では Q+λ≥λ による一様 bound があり、任意の proper Πg で有限。λ↓0 は非一様。
5. 批評家：「以前の angular evidence と同じ正当化で済むか。」→ 不可。fixed λ は振幅 scale を導入し、方向だけの実験なら元の非regularized 比に戻る。

### 第2往復：再異議 → 判定・留保

1. 測度担当：「共通 improper kernel なら近似列の選択はどうでもよいか。」→ 不可。モデルごとの cutoff 発散率と IG shape 接近率の反例を示した。共通の物理 scale と正規化列が必要。
2. 線形代数担当：「C は好きな定数倍にしても同じ noise では。」→ covariance を保つ E 変換とともに λ も変換しなければ別 prior になる。trace 正規化を明記した。
3. 極限担当：「g や shape の積分と ν→0 を勝手に交換していないか。」→ λ>0 の bound と compact 非退化 C で支配収束を示した。一般の特異 shape family には主張しない。
4. 退化担当：「posterior が proper なら evidence も proper か。」→ 不可。joint posterior の正規化は各 y の有限性、prior predictive の proper性は y 全空間の積分 1 であり、後者は発散する。
5. 批評家：「kernel の一致で既存 white 診断を Bayesian に完全回収したと言えるか。」→ 不可。形式的な固定観測 kernel の対応だけ。Laplace、energy-floor、遷移、候補 prior、実装上の clipping と近似精度は未検証で、採用判断もしない。

## 11. 確認資料と停止点

前提として以下の二文書を全文読取りした。

- noise-pitch-integration-boundary-20261020.md
- colored-harmonic-evidence-derivation-20261020.md

既存 white 診断の varSpeech、DC 列なし、regularized cod、Laplace の記述は、前者が確認した実装契約に基づく。本書ではリポジトリコードの追加照合・実行は行っていない。

一次本文は Shi et al. (2019), “Robust Bayesian Pitch Tracking Based on the Harmonic Model” の著者 accepted manuscript、式 (11)–(14) を再確認した。式 (12) の inverse-scale 測度、式 (13) の normalized Gaussian g-prior、式 (14) の hyper-g が参照対象である。本書の λ>0 測度と二つの共通 proper 近似列による解釈は独立導出であり、同論文の提案として帰属させない。

[一次本文](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)
／[DOI](https://doi.org/10.1109/TASLP.2019.2930917)
／[既存実装契約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/implementation-contract.md)

本書の停止点は、形式 kernel の一致、指定した二つの共通 proper 近似による比の極限、posterior の正規化条件、単位・shape・比較上の留保の列挙である。新 prior の採用、最適 δ の選択、実験仕様の変更、性能・校正の主張へは進まない。
