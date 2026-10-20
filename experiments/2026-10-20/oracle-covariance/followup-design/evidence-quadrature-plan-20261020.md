# 保存500 pair の evidence / raw posterior predictive：実装前の数値設計

2026-10-20。入力文書 `/workspace/shared/noise-model-evidence-design-20261020.md` を読んだ上での独立した代数・計算計画。コード実装、保存データの読み取り・計測、tests/smoke、Git 操作は実施していない。以下の計算量は見積もりであり、実測値・30分以内の保証ではない。

## 1. 推奨と凍結する契約

採用候補は W 解析式、A 全停留点で区切る1次元求積、V log-concavity を利用した全円板適応求積、S/J の t 変換と log t 上の1次元求積。主目的は保存500 pair の train-only 重みと、同じ raw test に対する proper posterior predictive の派生再解析に限定する。別の unit / smoke / regression suite は作らず、段階的積分 refinement・座標照合はこの研究計測そのものの収束診断として保存する。

実行承認時には次を先に固定する。

- A: a∈[−0.8,0.8] の da 一様、V: 半径 R=1.5 の円板面積一様、S/J: α∈[0,1) の dα 一様、model prior 各1/5。
- 共通 scale 測度 dE/E。重みの proper な解釈は方向 evidence。raw prior predictive が proper だとは言わない。proper 総分散 prior の未決定 hyperparameter を今回追加しない。
- 全500 pair、5モデル、train と joint を評価。joint は独立な2 record の block diagonal covariance、共有 E と共有 shape。連結 AR として扱わない。
- 既存 truth、test score、W の勝敗を prior・支持・計算許容差の調整に使わない。truth は集計ラベルにのみ使う。
- log integral の計算上の収束目標は 1e−6 nats。判定の同等性幅や確率 cutoff ではない。丸めを含む certified error とは呼ばない。未達結果は未達のまま表示し、30分を超えて全件完了したように見せない。

## 2. 共通式と、残す定数

record 数を r=1 (train) または r=2 (joint)、総次元 d=rN、方向数 k=rK、h=d/2、j=k/2 とする。N=4096、K=64、L=64。T_D=Σ_records ||x||²、Q_D=Σ_records xᵀC⁻¹x。

I_D,m=∫ π_m(η) |C(η)|^(−r/2) Q_D(η)^(−d/2) dη。

log Z*_D,m = log c + log Γ(d/2) −(d/2)log π + log I_D,m。

train weight は log π_model,m + log I_train,m の log-sum-exp でよい。方向 evidence の絶対値を出す場合には log Γ(N/2)−log2−(N/2)logπ + N log||x_train|| を log I_train に加える。

log p_m(test|train) = log Γ(N)−log Γ(N/2)−(N/2)logπ + log I_joint,m−log I_train,m。

log p_BMA = logsumexp_m(log w_train,m + log p_m)。同値な実装内の代数表現は、上記共通定数 + logsumexp_m(logπ_model,m+logI_joint,m) − logsumexp_m(logπ_model,m+logI_train,m)。後者との照合は新しい test suite でなく同じ報告値の計算診断としてよい。Σw logp を BMA score にしない。

数値的には T_D で energy を割り、log I_D,m=−h log T_D+log J_D,m と分離する。T_D=0 は失敗扱い。全モデルで同じ T_D を使う。この無次元化は観測データや prior を変更しない。W は J=1、shape 求積なし。大きい定数は最後に logΓ で加え、profile likelihood の最大値で積分を代用しない。

## 3. 最初の十分統計量処理

pair ごとに train/test を一度読み、以下だけ保持する。joint 統計量は train+test の和で得る。元 geometry と保存 float64 direction norm の契約を保持する。

- W: T。
- A: T、B=Σ_records Σ_{i=2}^N x_i x_{i−1}、D=Σ_records Σ_{i=2}^{N−1}x_i²、および正の二乗和評価用の各 record の端点情報。異なる record の境界積 x_train,N x_test,1 は入れない。
- V: 位相別 energy e_l=Σ_records,cycles x_{cycle,l}²、l=0,…,L−1。保存 geometry の f_l=(cosφ_l,sinφ_l) と F_D=Σ_all_samples f_l も保持する。丸めた三角関数の和を根拠なく厳密0へ上書きしない。
- S/J: unit direction への射影 energy P、直交残差を直接作って得る energy O。O=T−P の減算で作らない。実際の norm² d_dir から unit direction を定義し、C=(1−α)I+α U*U*ᵀ、各列 norm²=L という元文書の再パラメータ化を使う。保存 residual を変更しない。

ペア・モデル・record種別、入力 hash/既存ID、十分統計量と provenance を残す。T、O、P の非有限値、O≤0、O+P と T の想定外の不整合を floor で隠さない。実装時の浮動小数点集計差は明示し、結果に合わせて基準を変えない。

## 4. A：ピーク探索を粗い格子だけに依存させない

stationary AR の Q_D=R_a/(1−a²)、R_a=T−2aB+a²D。det(C)=(1−a²)^(N−1) より

log kernel_A(a)=(r/2)log(1−a²)−h log R_a。

この式は独立2 record にもそのまま成立する。π_A=1/1.6 を含める。R_a/T を使い無次元評価する。|a|≤0.8 のため 1−a² は特異にならない。R_a の通常評価と、必要箇所の stationary 初期項・innovation の正の二乗和に基づく評価を照合できる。

内部停留点は次の三次多項式の実根に含まれる。

dB −(dD+rT)a +(2r−d)Ba² +(d−r)Da³=0。

区間内の全実根と両端で区間を分け、根の残差と微分符号を確認した上で shifted adaptive Gauss–Kronrod 等で積分する。重根・次数退化時には微分区間探索を併用して「optimizer が一つ返したから十分」としない。曲率に基づくピーク幅で追加分割し、独立の高次数 Gauss–Legendre 細分化で log integral を照合する。全停留点を区切ることと積分収束は別々に記録する。

## 5. V：Z の相殺、log-concavity、見落とし防止

S_D(b)=Σ_l e_l exp(−b⋅f_l)。元の C_ll=exp(b⋅f_l)/Z(b) から Q_D=Z S_D、det(C)^(-r/2)=Z^(d/2) exp(−b⋅F_D/2)。したがって Z は正確に相殺し、

ell_V(b)=−h log S_D(b)−b⋅F_D/2、 ||b||≤R。

無次元版では e_l/T を使う。prior は面積で 1/(πR²)。極座標では r_rad dr_rad dθ/(πR²) であり、r_rad 一様 prior ではない。記号 r_rad は record 数 r と区別する。

p_l(b)∝e_l exp(−b⋅f_l) と置くと、gradient=h E_p[f]−F_D/2、Hessian=−h Cov_p(f)。従って ell は円板上で concave、通常の正 energy と異なる位相があれば strictly concave。別々に離れた局所ピークの見落としはこの構造から排除できるが、幅の狭い単一ピークを粗い求積格子が拾わない危険は残る。

### 全支持を覆う主求積

1. 全円板を、中心から境界まで欠けのない極座標 sector に分割する。各 cell 面積は (r1²−r0²)(θ1−θ0)/2 を解析的に持つ。原点の Jacobian は0であって特異密度ではない。
2. 制約付き凹最大化で mode を求める。内部 gradient、境界 KKT 条件、mode の位置と局所 Hessian 固有値を保存する。mode は shift と重点分割に使い、最適化成功を積分成功に読み替えない。
3. 全 cell に評価点 c を置く。凹性により ell(b)≤ell(c)+g(c)⋅(b−c)。sector 上の g⋅b の最大は角度端・g方向が sector 内ならその角度、および半径端から解析的に得られる。U_cell=area_cell exp(max_tangent) は mass の保守的な上側 envelope になる。prior 係数も同じく適用し、総和は log 領域で行う。
4. 上側 envelope が大きい cell を優先分割し、mode とその曲率幅を含む cell は強制 refinement。小さい積分値しか得られなくても U_cell が大きければ捨てない。これが「両方の粗い求積がピークを外し一致した」ケースを防ぐ主仕掛けになる。
5. 積分値は cell 内の radial Gauss–Legendre × angular 高次数則で求める。たとえば 8×8 と16×16、必要時32×32、さらに cell 二分という固定階層を用い、weight・r_rad・面積係数を正確に反映する。採用する具体次数は実装前に固定し、結果の勝敗で変更しない。
6. 未評価・省略候補 cell の U 総和が、既に得た正の積分 mass に対して例えば 1e−8 以下になるまで広域探索を打ち切らない。この比は探索漏れの診断であり、残った active cell の求積誤差は別に判定する。上界と数値下限の丸めまで保証しない限り certified bound と書かない。

全領域に毎回極細 uniform grid を敷く必要はない。真に重要な cell だけ高次数評価する。mode が円板境界や原点付近でも上記 coverage は変わらない。θ periodic seam をまたぐ mode は隣接両 cell を同時に細分化する。

### 低コスト化に使える追加 envelope

理論上 |f_l|=1、||b||≤R なら p_l(b)/p_l(0)≥exp(−2R)。保存 float64 geometry に対しては F_max=max_l ||f_l|| を実際に用い、以下の exp(−2R) を exp(−2RF_max) に置き換える。分散を「定数について最小化した二乗偏差」で表すと Cov_p(b)≽exp(−2RF_max) Cov_p(0)。したがって μ=h exp(−2RF_max) λ_min(Cov_p(0)) が正なら

ell(b)≤ell(c)+g(c)⋅(b−c)−(μ/2)||b−c||²。

sector の一次式最大と c から sector までの距離下限を用い、接線 envelope より小さい upper envelope を得られる。これは optional acceleration であり、μ が小さい/丸めで不安定なときは0として接線に戻す。境界 mode で gradient を勝手に0にしない。mode 周辺 Gaussian/Laplace 近似は初期分割に限り、最終積分の置換には使わない。

### 収束照合

全 V 積分に対し、最終 cell partition で異なる次数と angular node offset を用いた再評価を行う。少なくとも最後の2 refinement 差、別 node 則との差、未探索 envelope 比、評価点数を記録する。異座標の照合は、境界 mode、最狭曲率、最大 refinement、低 weight を含む事前指定された診断ケースと全未達ケースに行う。

異座標例は b_x=R sin u、b_y=R cos u·v、u∈[−π/2,π/2]、v∈[−1,1]、Jacobian=R²cos²u。こちらも mode に対応した位置で分割して内外1次元積分を行う。必要なら全件へ拡張するが、その追加時間も30分枠に含める。別座標側が鋭い mode を外してゼロになったものを成功照合に数えない。

## 6. S/J：独立代数確認と α→1 tail

ε=1−α、λ=L−(L−1)ε。直交 energy O、射影 energy P に対し、

|C_D|^(−1/2)Q_D^(−h)=ε^j λ^(−j) [O+εP/λ]^(−h)。

t=ε/λ と置けば ε=Lt/[1+(L−1)t]、dε=L/[1+(L−1)t]²dt、t∈[0,1]。

よって、**kernel 自体は t^j(O+tP)^(−h)**、dα 一様 prior の積分 integrand は

F(t)=L t^j (O+tP)^(−h)/[1+(L−1)t]²。

親からの代数ヒントと一致する。Jacobian を落として t 一様 prior に変更してはいけない。joint では h=N、j=K とし O/P を2 record で加算するだけであり、各 record の scale を別々に積分しない。

推奨積分座標 x=log t≤0、c=L−1 とすると、

ell_x(x)=log L +(j+1)x −h log(O+P exp x) −2log(1+c exp x)。

ell_x′=(j+1)−h P exp x/(O+P exp x)−2c exp x/(1+c exp x)。

ell_x″=−h OP exp x/(O+P exp x)²−2c exp x/(1+c exp x)²≤0。

従って x 上も log-concave。ell_x′(0)≥0 なら mode は x=0、そうでなければ単調微分の root を bracket で一つ求める。P=0 でも式は扱え、O=0 は propriety gate で止める。log(O+P exp x) は logaddexp(log O,log P+x)、log(1+c exp x) は log1p 等で安定に求める。α を浮動小数点で 1−ε として再構成する必要はない。

### tail は prior cutoff にしない

t≤δ の mass は、O>0 のとき

∫_0^δ F(t)dt ≤ L O^(−h) δ^(j+1)/(j+1)。

また x_c<mode、ell_x′(x_c)>0 なら凹性の接線から、

∫_{−∞}^{x_c} exp ell_x(x)dx ≤ exp ell_x(x_c)/ell_x′(x_c)。

両者の小さい方を log 領域で採用できる。正の本体積分を得てから tail/main 比を評価し、数値目標の配分（例 1e−8）に入るまで x_c を左へ延ばす。端を固定した α_max prior は作らない。upper bound の丸め検証までは行っていないので、これは解析式を用いた数値 tail 診断と表示する。

mode からの曲率幅で区間を分割し、shifted 1D 求積を refinement する。独立照合は t 座標の mode-aware 分割求積でよい。極端に小さい t_mode では t/t_mode の rescale を使い、粗い t 格子だけで照合しない。α の posterior 概要を出す場合も log ε=logL+x−log1p(c expx) を保持し、α が丸めで1となったことを特異点 mass と誤解しない。

## 7. log integral の収束診断と伝播

各 model×pair×train/joint に保存する最低項目：

- 最終 logI、直近3段階の logI、段階差2つ、異なる求積則/座標との logI 差。
- ライブラリ誤差推定（補助）、解析 envelope/tail の相対 mass、mode、評価点数、経過秒、propriety/finite gate。
- converged / not_converged / invalid_input / time_budget_exhausted。未達を converged にまとめない。

具体的な gate 候補は「直近2差それぞれ≤2e−7、別則差≤5e−7、未探索/tail mass 比≤1e−8、finite gate 合格」。これは1e−6目標に対する保守的な運用診断であり、真の誤差≤1e−6の証明ではない。float64 の統計量誤差を2e−7以下と証明したとは言わず、安定な集計と代数表現の照合で記録する。どれかを結果都合で緩めない。

もし各 logI の真の誤差が δ 以下なら、model predictive log score の誤差は高々2δ、logBF は2δ。logsumexp は最大ノルムに関して1-Lipschitzなので、BMA の joint/train logsumexp 差も高々2δ。これは仮定付きの誤差伝播であり、収束差を真の誤差へ昇格させる理由ではない。

より実務的には refinement 各段階の全 logI から weight と BMA score を再計算し、派生量自体の変化も示す。未達モデルを除外して再正規化しない。依存する pair の重み/BMA を未確定として残し、旧 score はそのまま表示する。省略 envelope と求積結果の関係が矛盾した場合は数値不具合として停止し、平均値に混ぜない。

## 8. 30分・1 GiB・1 worker の見通し

shape 積分は A/V/S/J 各1000個 (500 pair×train/joint)、W1000個は解析式。N×N 行列、MCMC、保存500 pair の全 shape-node×N tensor は不要。

- residual 全体を float64 で持っても 500×2×4096×8=32,768,000 bytes、約31.25 MiB。実際は pair 単位 streaming でさらに減る。geometry・十分統計量・出力は小さい。
- V の1 node は64 phase の指数・和と必要なら gradient/Hessian。4096 node chunk でも主要64×4096 float64 配列は2 MiB。temporary を複数持っても、chunk 上限と cell queue 上限を設定すれば1 GiBから十分余裕を取れる。巨大な全node cache は禁止する。
- A/S/J は十分統計量以降 O(1)/node。通常は各積分数百〜数千評価を想定するが、これは実測前の見積もり。V が支配的で、適応後1積分10³〜10⁴ nodeなら全 V で10⁶〜10⁷ node、約6.4×10⁷〜6.4×10⁸ phase 項評価。多階層照合もこれに加わる。
- 64 phase 演算を compiled/vectorized 数値処理にまとめ、Python の node×phase 二重 loop を避ける。BLAS/OpenMP 等の thread 数を1に固定し、worker は1。1000個の V 全件を無条件に巨大な一様格子へ載せる設計は採らない。
- この規模なら30分内を狙う現実的な設計だが、利用CPU、ライブラリ、境界集中、要求精度次第。実データを見ない段階で達成率や時間の数値保証はしない。

実行するなら最初の固定順序の小 batch も正式500 pair の一部として計算・保存する。これは別 smoke ではない。経過時間・評価数から全体所要時間を更新し、既計算結果は捨てず再利用する。batch は score/truth勝敗で選ばない。V の worst-case refinement を予測に反映し、単純な最初数件平均のみで「収まる」と断定しない。

全体 wall-clock 30分に近づいたら新規積分を止め、予約した出力時間で完了分・未達分を保存する。例えば27分を新規計算開始の停止点、残り3分を進行中の安全終了・集計・出力に充てる。ただし単一ライブラリ呼出しの長時間化もあるため、呼出しごとの evaluation 上限と checkpoint を設ける。30分内全件完了できなければ「部分完了」と報告し、許容差の事後緩和・prior変更・未達除外で完了扱いにしない。再開が許されるかは別途の実行条件に従う。

## 9. 保存する研究結果と解釈

既存2500 fit/test score は削除も変更もせず、同じ pair ID に新しい全5重み、entropy、各モデル proper raw posterior predictive、BMA、旧 plug-in score との差を併記する。score は nats/record、元 raw residual の Lebesgue 密度。方向 log evidence と raw score を直接差し引かない。

truth 別平均差、全pairの差分布、数値未達件数を主表示とし、train-only 重みと test argmax の異なる問いを混同しない。既存のW73件を「Bayesで救済した数」として主評価しない。500 pair は既使用testの記述的再解析であり、新しい確認実験・生理学的確率calibration・未知音声への検証ではない。

shape posterior の範囲が必要なら同じ積分 node と重みから marginal CDF/quantile を追加集計できるが、点数の乏しい適応meshを単純な標本と扱わない。CDF 積分の refinement が30分枠に収まらない場合は、この追加要約を未確定とし、evidence/predictive の主計算を優先する。

## 10. 実装前の結論

V の円板全域 coverage と接線 mass envelope、S/J の log t 凹 integrand と解析 tail、A の全停留点分割を組み合わせれば、単に粗い grid の値が一致しただけの「収束」を避けられる。train/joint に同じ方法を適用し、scale積分定数を保持すれば、元Gaussian plug-in scoreと同じraw観測のproper posterior predictiveを計算できる。

未解決なのは実測 runtime、浮動小数点誤差を含む実際の到達精度、全500 pair の収束率。ここは実装前計画であり、達成済みとも certified error とも表現しない。新しい prior の探索や新しい実験を追加せず、固定目的の積分 refinement と未達の正直な報告に限定する。
