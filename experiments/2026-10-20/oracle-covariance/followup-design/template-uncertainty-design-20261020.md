# 未知周期平均テンプレートの推定誤差：oracle 限界の解析

作成日：2026-10-20。対象：Hiroshiba/check-nonml-saikyo-vocoder。

## 0. 結論と範囲

既知 phase、固定周期長 L=64、train K=64 周期を保ち、未知の共通周期平均 q を train の単純周期平均で推定する場合を独立導出した。test 周期数は M と記し、既存設計では M=64 とする。

- W/V/S/J の独立同分布周期 block では、同周期 train 残差 covariance は (63/64)C、異周期は −C/64。独立 test は train も反復した周辺 covariance として、同周期 (65/64)C、異周期 +C/64 になる。
- test 全周期に共有されるテンプレート誤差項は (1_M 1_Mᵀ)⊗(C/64)。全窓 rank は高々 L=64 であり、独立 S/J の I_M⊗(τ²ddᵀ) とは cycle 方向が異なる。後者の全窓 rank は非零なら M である。「周期内 rank1」と「全窓 low-rank」を混同しない。
- train を固定すると推定誤差は一定の平均ずれであり、独立 test の条件付き covariance は元の covariance のまま。共有誤差を covariance と呼べるのは train 反復まで含めた周辺量である。
- A は周期を跨ぐ相関があるため、C/64 と一律の63/64補正を使えない。有限窓 covariance の全 block を使った式が必要である。
- S/J の direction まで推定 q とその微分から作れば、候補 covariance 自体がランダムな plug-in になる。既知 direction の oracle 結果を、そのまま未知 q の成績として扱えない。

これは解析文書のみである。コード実行、データ生成、実験、新規 tests/smoke、Git 操作は行っていない。資料読取と本 Markdown の保存のみ行った。既存500pairの成果・品質結果・評価条件は変更しない。新たな nuisance model や実験の採用も決定しない。

## 1. 出典と固定する前提

参照した既存設計：

- `/workspace/shared/cyclic_noise_identification_design_20261020.md`
- `/workspace/shared/phase-uncertainty-control-20261020.md`

以下はこれらのモデル定義に対する代数的導出であり、新しい文献の実証結果ではない。過去資料中の実行状況の記述は現在の進捗を示すものとして流用しない。

各周期を L 次元 column vector とし、

    Y_a^tr = q + X_a,  a=1,…,K,
    Y_i^te = q + Z_i,  i=1,…,M,
    E[X_a]=E[Z_i]=0,
    q_hat = K^−1 Σ_a Y_a^tr = q + e,
    e = K^−1 Σ_a X_a,
    R_a = Y_a^tr−q_hat = X_a−e,
    T_i = Y_i^te−q_hat = Z_i−e.

q は固定未知の共通平均であり、周期ごとの random q や prior は追加しない。平均を推定する段階では q_hat を再正規化、平滑化、位相合わせ、端点補正しない。これらをすると以下の単純平均の式とは別推定器になる。truth の S/J direction は当面、固定真値 g/h とする。q と direction の統計的結び付きを解くのは後述の別論点である。

まず train/test は原設計どおり独立 record とする。A も各 record の内部では連続 AR だが、record 間の初期状態・innovation は独立。一本の連続 AR の前半と後半を split した場合は第5節に分ける。

## 2. 独立周期 block：W/V/S/J の厳密式

固定 q、固定真の direction、固定 noise parameter の下で、X_a は周期間 iid、Cov(X_a)=C、Z_i も同じ C の iid、train と test は独立とする。原設計では

    W: C = σ² I_L,
    V: C = diag(v_0,…,v_(L−1)),
    S: C = σ² I_L + τ_s² ggᵀ,
    J: C = σ² I_L + τ_j² hhᵀ.

v は全周期で同じ既知位相に対応する。σ²>0 なので C は正定値。

### 2.1 train

    Cov(e)=C/K,   Cov(X_a,e)=C/K,
    Cov(R_a,R_b)=δ_ab C−C/K.

対角 block は (1−1/K)C、異周期 block は −C/K。stacked covariance は

    Cov(R) = H_K⊗C,
    H_K = I_K−1_K1_Kᵀ/K.

Σ_a R_a=0 は実現ごとに厳密。したがって全窓 rank は (K−1)L であり、元の KL 次元の正定値 Gaussian density をそのまま train residual に置くことはできない。単純に full-rank covariance を当てて元の likelihood と呼ばない。contrast 座標での尤度や平均 nuisance を扱う方法は考えられるが、ここでは採用しない。

    E[K^−1 Σ_a R_a R_aᵀ]=(K−1)C/K.

この iid 条件なら分母 K−1 の標本 covariance は C に不偏。ただし64次元に対して63個の独立 contrast しかなく、実現標本 covariance の rank は高々63。高次元行列が安定に逆行列化できる、という保証にはならない。

### 2.2 独立 test と train 反復

    Cov(T_i,T_j)=δ_ij C+C/K,
    Cov(T)=I_M⊗C + (1_M1_Mᵀ)⊗(C/K).

同周期の倍率だけ見て「noise が65/64倍になった」とするのは不十分。非零の異周期 block を落とすと joint distribution が違う。

q_hat の誤差には white/V 成分も含まれる。したがって共有項は一般に rank1 ではなく、この条件では rank L。S/J では共有項 C/K の中に rank1 部分も入るが、それは全周期で同じ train 平均係数に由来する。

例として S では e = ε_bar+g s_bar、Cov(e)=σ²I/K+τ_s²ggᵀ/K。test の g 成分は g(s_i^te−s_bar)。独立な s_i^te の covariance が I_M 型、共有 s_bar の covariance が 1_M1_Mᵀ 型である。J でも g,s を h,j に置換した同じ関係が成立する。

### 2.3 条件付き平均、covariance、非中心 moment

固定された train D に条件付けると e は定数なので

    E[T_i|D]=−e,
    Cov(T_i,T_j|D)=δ_ij C,
    E[T_i T_jᵀ|D]=δ_ij C+eeᵀ.

反復 train も平均すると E[e]=0、E[eeᵀ]=C/K となり第2.2節に戻る。単一 train に対する固定 bias をゼロ平均 noise に読み替えない。Gaussian iid では R と e は無相関かつ独立だが、これは単純平均と同一 block covariance に依存する特別な事実であり、A や推定 direction に一般化しない。

## 3. 共有誤差と cycle 独立 rank1 の識別条件

### 3.1 共通 cycle mode と contrast mode

u=1_M/√M とし、U は UᵀU=I_(M−1)、Uᵀ1_M=0 を満たす任意の固定 contrast 基底とする。

    T_common=(uᵀ⊗I_L)T,
    T_contrast=(Uᵀ⊗I_L)T.

iid block 条件なら

    Cov(T_common)=(1+M/K)C,
    Cov(T_contrast)=I_(M−1)⊗C,
    Cov(T_common,T_contrast)=0.

K=M=64 なら共通 mode の covariance は2C、contrast mode はC。Gaussian では両者は独立である。共有テンプレート誤差は contrast で厳密に消えるが、独立 S/J 成分は contrast 側にも残る。このため全窓 rank の数値だけでなく cycle 方向を見る必要がある。今回 L=M=64 では共有項と S/J 独立項の rank が偶然どちらも64になり得るので、rank数だけの判別は特に無効である。

等価に、異なる周期で

    T_i−T_j=Z_i−Z_j,
    Cov(T_i−T_j)=2C.

差分・contrast は「共有誤差を消したときに何が残るか」の解析的対照である。test 平均を除去したデータを元の heldout joint density として採点することを認めるものではない。

### 3.2 必要な区別と限界

1. M≥2 で、同周期 block と異周期 block の双方を見る。M=1、対角 variance 対 phase だけ、周期内 g/h 投影 energy だけでは共有誤差と独立効果を区別できない。
2. train/test は独立、q は真に全周期共通、周期効果 s/j は独立という契約を保つ。周期相関を任意に許すと s/j に共有係数を持たせられ、テンプレート誤差との因果的区別は失われる。
3. 既知 direction の比較では g と h が非共線であることが必要。S/Jの区別には周期内 off-diagonal と方向情報も要る。未知 q の推定後に真の離散直交性を仮定しない。
4. A の cross-cycle covariance は別に差し引くか明示的に比較する。cross-cycle が非零という事実だけではテンプレート誤差の証拠ではない。
5. 周辺 covariance の検証には独立 train/test pair の反復という母集団が必要。単一pairから全 block covariance を精密推定できるとは言わない。同じ train に多数 test を付ける場合、train 推定誤差の独立反復には数えられない。

test の cycle 平均を引いた標本 covariance は、元の Z の標本 covariance と実現ごとに同一。この性質は useful diagnostic だが、共有誤差そのものを消すので、それだけで共有誤差の存在・大きさを推定したことにはならない。非中心 moment、平均、contrast を別々に記録する概念が必要である。

## 4. A：周期間相関を保持する一般式

train の block covariance を Γ_ab=Cov(X_a,X_b)、test を Ω_ij=Cov(Z_i,Z_j) とする。

    Q=Cov(e)=K^−2 Σ_aΣ_b Γ_ab,
    D_a=Cov(X_a,e)=K^−1 Σ_b Γ_ab.

独立 train/test の場合、厳密に

    Cov(R_a,R_b)=Γ_ab−D_a−D_bᵀ+Q,
    Cov(T_i,T_j)=Ω_ij+Q.

stacked 記法では B=(1_Kᵀ/K)⊗I_L、P=H_K⊗I_L、F=1_M⊗I_L とおくと

    Q=B Σ_tr Bᵀ,
    Cov(R)=P Σ_tr Pᵀ,
    Cov(T)=Σ_te+FQFᵀ.

共有追加項 FQFᵀ は正半定値、rank≤L。ただし元の Σ_te 自体が cross-cycle を持つ。A を周期 reset した I⊗C に置換しない。

原設計 A は b=0 の定常 AR(1) なので、c=σ²/(1−a²)、周期内添字 l,m=0,…,L−1、周期番号 r,s に対して

    (Γ_(r,s))_(l,m)=c a^|(r−s)L+l−m|.

底の a は AR 係数であり、周期番号ではない。負の AR 係数でも整数べきとして同じ式が使える。

Γ_d=Cov(X_(r+d),X_r) と置くと

    Q = K^−2 [KΓ_0 + Σ_(d=1)^(K−1)(K−d)(Γ_d+Γ_dᵀ)].

従って Γ_0/K だけではない。たとえば隣接周期の末尾と先頭は時間差1であり、a^Lが小さいことだけを理由に全異周期 block を無視してはいけない。有限窓の D_a は端部と中央で異なり得る。train の各対角 block が同じ倍率で縮むとは限らない。

より明示的に、原設計の marginal variance を E とすると Cov(r_(kL+L−1),r_((k+1)L))=Ea。上の Γ_d=Cov(X_(r+d),X_r) の向きで d≥1 なら Γ_d=a^((d−1)L)Γ_1 だが、Γ_1 自体にはこの強い境界 covariance がある。a=0 では独立 block の式へ戻る。親からの境界に関する注意とも一致する。

    E[K^−1 Σ_a R_a R_aᵀ] = K^−1 Σ_a Γ_aa−Q.

定常なら Γ_0−Q。K/(K−1) 倍するだけでは一般に Γ_0 の不偏推定にならない。また Cov(R_a,e)=D_a−Q は一般に非零で、独立 test との Cov(R_a,T_i)=Q−D_a も一般に非零。train residual と推定 q の独立性を A に流用しない。

contrast は A でも共有 e を実現ごとに消すが、残る covariance は (Uᵀ⊗I)Σ_te(U⊗I) であって iid C ではない。遠隔 block の AR 減衰と共有 Q の全周期共通構造は母 covariance 上の区別に役立つが、未計測の閾値や有限標本の分離保証にはしない。

## 5. 同一連続 record の train/test split は別問題

C_i=Cov(Z_i,e) が非零なら、周辺 covariance は

    Cov(T_i,T_j)=Ω_ij−C_i−C_jᵀ+Q.

この場合「元 covariance に正半定値 rank≤L項を足す」だけではない。独立 record の式を連続 AR の heldout 区間へ流用しない。

Gaussian の連続 record で全 train を条件とする場合、test の条件付き平均・covariance は通常の joint Gaussian 条件付けで変わる。Σ_te,tr を record 間 covariance とすると

    E[T|Y_tr]=Σ_te,tr Σ_tr^−1 X−F e,
    Cov(T|Y_tr)=Σ_te−Σ_te,tr Σ_tr^−1 Σ_tr,te.

ここでは固定真値 q,θ の理論式として X=Y_tr−1_K⊗q と書いた。未知 q の実用予測器をこれで実装できたとは言わない。原設計は独立 record のまま維持し、この連続 split を追加条件にしない。

## 6. 推定 q/q′ による S/J direction は別の plug-in 問題

未知平均の推定誤差を調べるだけなら、真の g/h を候補 covariance に与えた「平均だけ非oracle」の対照が数学的に可能。しかしそれは direction oracle を残しており、未知 q の完全な解除ではない。

候補で例えば g_hat=q_hat/√mean(q_hat²)、h_hat=−D q_hat/√mean((D q_hat)²) と定めるなら、D はあらかじめ定義する周期微分演算子でなければならない。64個の未知 q 値から解析微分 q′ は一意に定まらない。補間・周波数打切り・平滑化・周期端点・ゼロ微分時の失敗契約が未定のまま h_hat を定義済みとしない。

固定された D なら、正規化前の誤差は D e、covariance は DQDᵀ、q 誤差との cross-covariance は QDᵀ。微分による誤差増幅を無視できない。正規化も含めると方向は非線形なランダム量になる。正規化写像 n(x)=√L x/||x|| の局所微分は

    dn_x[v] = (√L/||x||)(I−xxᵀ/||x||²)v,

なので q_hat の振幅・直交方向誤差の扱いは区別される。これは局所感度式であり、全誤差の線形近似精度を保証しない。

S/J の候補は

    C_hat_S(D_train)=σ_hat²I+τ_hat_s² g_hat g_hatᵀ,
    C_hat_J(D_train)=σ_hat²I+τ_hat_j² h_hat h_hatᵀ

となる。direction と平均は同じ train に依存し、noise parameter も同じ train で推定され得る。既知 direction の rank1 KL、直交性、score 損失式をそのまま代入できない。

重要な区別：真の生成 covariance は固定真値 q の C(q) のままである。q_hat を計算しただけで truth が C(q_hat) に変わるわけではない。第2節の周辺 covariance は真の C(q) を用いれば依然成立するが、候補の予測 covariance C_hat はそれと別物。

train を条件とすれば g_hat/h_hat と候補 parameter は固定なので、test を見ずに固定した正定値候補は正規化された plug-in predictive density を作れる。ただし真の conditional density、oracle density、posterior predictive と同一視しない。反復 train を周辺化した plug-in 分布は一般には混合分布であり、単一 Gaussian とは限らない。独立 test を保つことは test 漏洩を防ぐが、direction 推定誤差を消すことではない。

## 7. score と covariance 補正の意味

既知真の Σ_te を固定して、平均だけ q_hat に置換した Gaussian score と oracle score の NLL 差は

    ΔNLL = (1/2)eᵀFᵀΣ_te^−1F e − eᵀFᵀΣ_te^−1Z.

独立 train/test では期待値

    E[ΔNLL]=(1/2)tr(Σ_te^−1 FQFᵀ).

iid block の Q=C/K、Σ_te=I_M⊗C なら

    E[ΔNLL]=ML/(2K).

M=K=L=64 では32 nats/record、0.5 nats/cycle。これは未知平均64自由度の単純平均に伴う、固定真 covariance・固定 direction の期待値であり、位相原点1係数の既存補足の0.5 nats/recordと単位・推定次元が違う。個々の実現差は交差項のため負にもなる。

A では trace 式を使い、一律32としない。noise parameter や direction まで推定した5モデル再適合の差、勝者表、品質・自然さを予告する値ではない。許容差・同等性幅として採用しない。

Σ_te+FQFᵀ は、指定した推定器による反復 residual の周辺 covariance である。それを N(F q_hat, Σ_te+FQFᵀ) の予測分布に使うことは形式上可能だが、固定未知 q の真の test conditional covariance が増えたという意味ではない。posterior predictive と呼ぶには prior、train likelihood、q と S/J covariance の連動、parameter の扱いを別途指定する必要がある。今回、その新しい推論モデルは採用しない。

### 7.1 追加の理論対照：既知 C、平均だけ未知の flat-prior predictive

親から提示された比較候補を独立導出した。ここだけは既知の正定値 C が q に依存しないという制約を置く。train K、test M 周期は iid block、q∈R^L は制約なし、両 record は固定 q を共有する。C は推定しない。S/Jの真のdirectionとqの連動まで表す階層モデルではなく、mean-only対照である。

形式的に Lebesgue 測度に対する flat prior π(q)∝1 を用いると、これは improper prior だが、K≥1、C正定値なら posterior は proper で

    q|Y_tr ~ N(q_hat,C/K).

同一 q を test 全周期に共有させて積分すると、正規化された proper posterior predictive は

    Y_te|Y_tr ~ N(F q_hat, A),
    A=[I_M+(1_M1_Mᵀ/K)]⊗C.

prior 自体を proper と呼ばない。この improper prior の任意の規格化定数を含む marginal evidence を使って noise model 比較が正当化されたとも言わない。ここで追加したのは解析上の比較対象であり、実験への prior 採用ではない。

r=M/K と置く。oracle は真の固定 q と Σ=I_M⊗C による density。両 NLL の差 Δ_pred は

    Δ_pred = (1/2)log(det A/det Σ)
             +(1/2)(Z−Fe)ᵀA^−1(Z−Fe)
             −(1/2)ZᵀΣ^−1Z.

共通 cycle mode の covariance倍率は1+r、その他は1なので

    log(det A/det Σ)=L log(1+r),
    tr(A^−1Σ)=(M−1)L+L/(1+r),
    FᵀA^−1F = [M/(1+r)] C^−1.

固定 train、すなわち固定 e=q_hat−q に条件付け、真の独立testについて平均すると

    E_test[Δ_pred|Y_tr]
      = (L/2)log(1+r)
        + [M eᵀC^−1e−Lr]/[2(1+r)].

従って各固定 train が同じ損失を持つわけではない。これは真の固定 q の test law と候補 predictive の KL なので非負である。e=0 の場合にも分散を広げることによる正の損失が残る。個々の test の実現差自体には非負制約はない。

さらに train 反復について E[eᵀC^−1e]=L/K を使うと、後半の項が厳密に相殺し

    E_train,test[Δ_pred]=(L/2)log(1+M/K).

先述の fixed q_hat plug-in は同じ条件で

    E_test[Δ_plugin|Y_tr]=(M/2)eᵀC^−1e,
    E_train,test[Δ_plugin]=ML/(2K).

K=M=L=64 では、plug-in は32 nats/record、flat-prior predictive は32 log 2 nats/record。r>0で log(1+r)<r のため反復平均上は後者の oracle 比損失が小さい。ただし、固定 train ごと・test実現ごとに後者が優れるという意味ではない。q_hatが真値に非常に近いtrainでは固定平均plug-inの方がよいこともある。

この導出は未知noise parameter、推定direction、q依存 C、Aの周期相関、未知phase、非定常q、prior制約を含まない。proper scoringでの限定的な平均予測改善であり、5原因のnoise evidence、識別勝率、品質の改善保証ではない。Aへは単純平均がGLS推定と一致する保証もなく、同じ flat-prior posterior の式を流用できない。

## 8. 次に必要な最小対照と前提

将来判断のための案だけを残し、今回の500pairへ計測や集計を追加しない。

1. 最小の解析対照は「q既知」と「train単純平均、directionは真値固定」の平均のみの差。前者との比較で推定平均の効果を切り分けられるが、後者を未知 q 全体の解決と呼ばない。
2. 同周期・異周期 block、common/contrast mode を区別する。test centering は診断上の消去対照に限り、元座標の heldout joint density を置換しない。
3. direction まで外す前に、q の推定対象を64離散値とするか滑らかな関数とするか、微分・正規化・失敗規則を明示する。単純平均の結論を別の smoothing estimator に引き継がない。
4. 独立 record か連続 split か、q が train/test で不変か、対象が接線 J か非線形 pulse jitter かを固定する。非線形 jitter の場合、単純平均は基礎 pulse ではなく摂動平均のぼけた波形を推定し得るため、q=E[Y_cycle] と基礎 pulse のどちらを指すかの再定義が要る。
5. 新たに実施する場合だけ、parameter fitting、Gaussian densityの対象、推定誤差の不確かさ評価、独立反復単位を事前に定める。現在は新しい nuisance variance、prior、独立校正 split、誤差幅 sweep を自動追加しない。

自然音声には未知 filter、非定常 q、未知 phase/F0、cycle 境界・補間、source と観測の区別が残る。本解析の成功を aspiration や生理的 jitter の同定へ拡張しない。

## 9. 仮想5役による2往復の議論

以下は一人の設計者が5観点を用いた仮想レビューであり、実在5人の査読や追加測定ではない。

### 第1往復：提案 → 他役の批評 → 応答

1. 生成モデル役：「平均を推定すると test noise が増える」。統計役：「固定 train では平均 bias であり covariance は増えない」。応答：条件付き平均、条件付き非中心 moment、train反復を含む周辺 covariance を第2.3節で分離した。
2. 統計役：「train covariance は63/64倍で補正できる」。AR契約役：「周期を跨ぐ A は iid でない」。応答：Γ_ab、Q、D_a の一般式を導出し、Aへの一律補正を禁止した。
3. AR契約役：「heldout は train 後半の続きでも同じ」。批評家：「初期状態が独立か carry かで式が違う」。応答：独立 record を主契約とし、連続 split の C_i と条件付き Gaussian を別節に置いた。
4. direction・数値役：「q_hat の微分から h_hat を作れば oracle を外せる」。生成モデル役：「離散平均に一意の解析微分はない」。応答：微分・正規化規則を未確定の前提として残し、direction固定対照との混同を禁止した。
5. 批評家役：「全窓low-rankが出れば J と同じだ」。統計役：「cycle方向が1·1ᵀとIで違う。今回rank数は同じになり得る」。応答：common/contrast 分解と周期差分を導出し、rank数だけで判別しないとした。

### 第2往復：反例 → 再応答 → 棄却条件

1. 生成モデル役：「test平均を除けば誤差を消せるので、それでscoreすればよい」。批評家：「評価対象と密度次元を変えてしまう」。再応答：centeringは消去診断に限定。棄却条件：centered testを元の未変換joint densityとして採点すること。
2. 統計役：「C/Kを全候補へ足せば不確かさを積分済みだ」。direction役：「q依存 covariance やpriorを指定していない」。再応答：推定器反復の周辺momentとposterior predictiveを分離。棄却条件：frequentist誤差covarianceを根拠なくposteriorと呼ぶこと。
3. AR契約役：「a^64が小さいので周期はほぼ独立」。統計役：「境界の末尾と先頭のlagは1」。再応答：有限窓全blockのQを維持。棄却条件：未評価の近似を厳密な63/64補正へ置換すること。
4. direction・数値役：「元qではg⊥hなので推定後も同じ」。生成モデル役：「q_hatの雑音、微分法、正規化で変わる」。再応答：truthの直交性と推定directionの性質を区別。棄却条件：既知directionのKLや1係数位相損失をplug-in S/Jへ転用すること。
5. 批評家役：「理論が揃ったので追加条件を今すぐ実施しよう」。他役：「目的は既存成果を変えずoracle限界を整理すること」。再応答：最小対照と必要契約だけを提案し解析で停止。棄却条件：新しいnuisance model、実験、自然音声への移行、品質主張の自動採用。

## 10. 停止点

数理分析と保存を完了。未知平均を外す際の共有誤差、trainの射影、Aの相関、推定directionのplug-in化を別々に定義できた。有限標本の実証や自然音声への採用判断は未実施。既存500pairの結果・品質評価・進行条件は変更しない。

## 11. 先行研究の位置付け：平均 nuisance と error contrasts

Harville, D. A. (1974), “Bayesian inference for variance components using only error contrasts”, Biometrika 61(2), 383–385。参照先：[出版社抄録](https://academic.oup.com/biomet/article-abstract/61/2/383/268084)、[大学配布PDF](https://www.math.ntnu.no/emner/TMA4315/2020h/Harville-1974.pdf)。

親担当による一次資料の確認報告では、本文第2–3節は線形 Gaussian モデル y~N(Xβ,H_θ) において、共通で full-column-rank の設計行列 X と β の flat improper prior の下で、error contrasts の likelihood と β を積分した量が θ に依存しない係数を除いて比例することを扱っている。平均を推定した残差を「既知平均から得た生の観測」として、そのまま同じ full-dimensional likelihood に入れることとは区別される。

この文献は、本資料第2.1節の射影・特異 covariance と、将来平均 nuisance の扱いを選ぶ必要性の先行研究上の位置付けとして挙げる。PDFの数式OCRには一部崩れがあるとの確認報告を受けており、本作業で本文の全詳細式を完全検証したとはしない。本資料の未知テンプレート、cross-cycle covariance、Aのblock式、plug-in direction、期待test NLL損失は独立した代数的導出であり、Harville論文のvocoder実験・性能結果ではない。error-contrast方式を新たに実装・採用する決定も含まない。

Patterson & Thompson (1971) の原文は本作業では未取得であり、その内容の詳細を読了・検証済みとして引用しない。以上の出典追加で本資料を完成とし、追加研究・実験は行わない。
