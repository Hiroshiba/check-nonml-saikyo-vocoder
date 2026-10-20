# 固定 harmonic mean と W/A noise の方向 evidence：独立導出

2026-10-20。紙上の導出であり、新モデル・priorの採用ではない。F0・harmonic次数は固定する。数値コード実行、実装、計測、tests、Git操作、H0/F0探索、既存500 pairの変更は行わない。文書読取り・一次本文の確認・本書の保存だけを行った。

## 0. 結論

提示された B、det B、Q、および dE/E 積分の係数は、正規化された conditional g-prior を使う限り正しい。指数は N/2 のままであり、「平均が未知なら必ず N−d」ではない。

ただし raw y の proper prior predictive は dE/E から作れない。同じ非零の元観測 y から作る方向 u=y/||y|| の proper 密度なら、W/A 比を厳密に定義できる。この比は共通の形式的 scale 積分比と一致する。これを元波形の振幅まで含む正規化された evidence と呼んではならない。

必要な追加契約は、βの正規化測度と C 依存の意味、同一観測・初期状態、g と a の proper 混合測度、方向観測を採用するか proper scale prior にするか、H0にも同じnoise候補を与えること、退化ケースの扱いである。proper π(g) はほとんど至る所で十分だが、完全 harmonic fit の点では尾部モーメント条件が別に要る。

## 1. 観測と測度を固定する

- 元観測 y∈R^N。N、サンプル順、窓、既知の前処理は全候補に共通。候補別の fit 残差を観測として置き換えない。
- 固定F0・固定次数 K=d/2 による実数デザイン Z∈R^(N×d)。まず full column rank、d≤N とする。DC列・中心化は勝手に足さない。
- H1: y|β,E,a ∼ N(Zβ, E C(a))。
- C(a)_ij=a^|i−j|、a∈[−0.8,0.8]。Wは a=0、C(0)=I。Aはこの定常AR(1) correlation family。
- G(a)=Zᵀ C(a)⁻¹ Z。
- g>0 に対し β|E,g,a ∼ N(0,gE G(a)⁻¹)。g は無次元。π_g は (0,∞) 上の proper probability measure とだけ置き、分布形・値は選ばない。
- scaleの形式測度は共通の dE/E、E>0。

単位の明確化：trace C=N で covariance=EC と書くと、E=tr(Σ)/N は平均周辺分散であり、noiseの期待二乗ノルム（窓全体のtrace）は NE。元設計の「総分散」は、一標本当たりに各noise成分を合算した平均雑音分散を意味しており、本書でモデルの数式を変更したのではない。窓全体のtraceと取り違えないよう表記を明確にする。もし将来窓全体のtraceをscale変数にするならN倍の変数変換になる。共通NのdE/Eでは形式比は変わらないが、proper scale priorの単位は合わせる必要がある。

N≥2 に対して |C(a)|=(1−a²)^(N−1)。C⁻¹ は 1/(1−a²) 倍の三重対角行列で、両端の対角は1、内部対角は1+a²、隣接非対角は−a。これは有限窓の定常初期分布を含む。noise ε_1∼N(0,E)、ε_t=a ε_(t−1)+η_t、η_t∼N(0,E(1−a²)) と定義すれば得られる。初期サンプルを条件付けして捨てる条件付きAR尤度、zero padding、循環ARとは別である。N=1なら C=[1] で a は識別できない。

## 2. β積分：正規化定数を保持する

conditional priorの密度は

 p(β|E,g,a)=(2πgE)^(−d/2)|G(a)|^(1/2)
   × exp{−βᵀG(a)β/(2gE)}。

この |G|^(1/2) と E^(−d/2) を落とすと別の測度になる。尤度と掛け、βをLebesgue測度で積分する。平方完成したβ積分は E^(d/2) を供給するがprior側の E^(−d/2) と相殺する。したがって結果のscale冪は E^(−N/2) のままである。

同じ結果は独立Gaussianの和から直ちに

 y|E,g,a ∼ N(0,E B(a,g)),
 B(a,g)=C(a)+g Z G(a)⁻¹ Zᵀ

と得られる。βは未知だが、その条件付きpriorはproperであり、周辺平均が0になることと各実現のharmonic成分が0であることは別である。

X=C⁻¹/²Z、P=X(XᵀX)⁻¹Xᵀ と置くと、Pはrank dの直交射影で

 B=C^(1/2)(I+gP)C^(1/2),
 |B|=|C|(1+g)^d,
 B⁻¹=C⁻¹−[g/(1+g)] C⁻¹Z G⁻¹ ZᵀC⁻¹。

従って

 Q(a,g;y)=yᵀC⁻¹y−[g/(1+g)]yᵀC⁻¹Z G⁻¹ZᵀC⁻¹y。

T=yᵀC⁻¹y、J=yᵀC⁻¹Z G⁻¹ZᵀC⁻¹y、S=T−J と書けば

 0≤J≤T,   Q=S+J/(1+g)。

非零y・有限gでは B は正定値で Q>0。SはGLS残差二乗和だが、QはSだけではない。有限gの shrinkage と prior volume が残るので、既知qの式へ推定残差RSSを代入する手続きとは違う。

## 3. scale積分と proper な方向実験

α=N/2 として直接積分すると

 m*(y|a,g)=∫_0^∞ (2πE)^(−N/2)|B|^(−1/2)
                 exp{−Q/(2E)} dE/E
 =Γ(N/2)π^(−N/2)|C|^(−1/2)(1+g)^(−d/2)Q^(−N/2)。

これは規格化不能な共通scale測度を使った形式量である。m*(ry)=r^(−N)m*(y) なので、R^N上の積分は半径方向の ∫dr/r で発散する。「定数が相殺するからraw evidence自体がproper」とは言えない。

一方、u=y/||y||∈S^(N−1) を観測とし、通常の球面面積測度 dω(u) に対する密度を使う。任意の固定E>0について、Gaussian密度に polar Jacobian r^(N−1) を掛け、r>0 を積分すると

 p_dir(u|a,g)=Γ(N/2)/(2π^(N/2))
   × |B|^(−1/2)(uᵀB⁻¹u)^(−N/2)。

これは ∫p_dir dω=1 のproper密度で、Eに依存しない。ここでは符号付き方向を使い、uと−uを同一視していない。projective spaceを使うなら基準測度と係数を合わせる。

両者の正確な関係は

 m*(y|a,g)=2 ||y||^(−N) p_dir(u|a,g),  u=y/||y||。

したがって同一の非零元y、同じN・基準測度で比較する限り、共通半径因子は相殺する。βやaで異なる残差方向を作る必要はなく、未知βを積分した後も同じ方向実験に置ける。形式的なimproper-prior Bayes factorを無条件に正当化するのでなく、properな別の観測実験（振幅を捨てた元yの方向）のBayes factorとして根拠付ける。

y=0 は方向が未定義で形式積分も発散する。連続モデル下で確率0でも、量子化された全零窓は現実にあり得るため、別の取扱契約が必要。

## 4. g・aを積分する際の条件

記号として proper な Π_A(da) を [−0.8,0.8] 上に置く。形、連続性、端点・0での原子の有無はまだ採用しない。独立の共通π_gを仮定する場合、

 D_1W(u)=∫p_dir(u|0,g)π_g(dg),
 D_1A(u)=∫∫p_dir(u|a,g)π_g(dg)Π_A(da),
 BF_AW=D_1A(u)/D_1W(u)。

proper混合測度ならTonelliの定理から両者はproper方向密度。ただし「密度の積分が1」と「任意の観測点で有限」は別である。aまたはgを最大化して代入した値はこのevidenceではない。A/Wのposterior oddsには別にmodel prior oddsも必要。Π_A未指定の現段階ではfamily BFの数値は未定であり、固定aのkernelだけが確定する。

π_g(dg|a) とする別モデルも定義できるが、それは追加の共同prior契約であって暗黙に導入しない。WとAで異なるπ_gを使えば、noise shapeだけでなくsignal priorの差も比に入る。

### g積分の点ごとの有限性

1. y∉col(Z) なら S(a)>0。g→∞でも Q≥S(a)、(1+g)^(−d/2)≤1 なので、任意のproper π_gで積分は有限。g→0では有限なH0 kernelに連続に近づくので追加の負モーメント条件はない。
2. 非零 y∈col(Z) なら S(a)=0、J=T>0。integrandは正の有限係数を除いて (1+g)^((N−d)/2)。このとき ∫(1+g)^((N−d)/2)π_g(dg)<∞ が必要十分。単にproperという条件では保証されない。
3. d<Nではcol(Z)の球面部分は面積測度0なので、この点で密度が無限でもproper混合密度との矛盾はない。ただしその点では通常の密度によるgのposterior正規化が不能になり、形式的な(β,E,g) posteriorもimproperになり得る。確率0の点における条件付き分布は一般に一意には定まらないので、通常の公式でposteriorが得られたとは主張しない。その点で∞/∞のBFを出してはいけない。近傍では非常に鋭い密度にもなり得る。pure harmonic入力に無断でfloorを足して回避しない。
4. d=NならP=I、B=(1+g)Cとなり、方向密度はgに依存しない。すべてのproper π_gで有限で、同じCのH0と方向実験では識別できない。
5. compactなa範囲は±1から離れ、C(a)とG(a)は連続で一様に非退化である。固定の y∉col(Z) についてS(a)も正の下限を持つので、proper Π_Aによる混合で新たな発散は生じない。完全fitなら上の同じgモーメント条件が支配する。

g=0を含める場合、βの通常のGaussian密度式は使えず、β=0の点質量として極限を定義する。g=∞をpriorの原子として置くことは本契約には含めない。

### 解析上の補足：記号的hyper-gの場合

一般のπ_gを主契約としたまま、原著との数式上の関係だけを確認できる。仮に π(g)=(δ−2)/2 × (1+g)^(−δ/2)、δ>2 と書くと、下節の固定CのH1/H0比のg積分は、t=g/(1+g)により

 [(δ−2)/2]∫_0^1 (1−t)^((d+δ)/2−2)(1−t R_C²)^(−N/2) dt
 =[(δ−2)/(d+δ−2)] ₂F₁(N/2,1;(d+δ)/2;R_C²)。

最初の積分から直接、R_C²=1で有限となる条件は δ>N−d+2 と分かる。等号では対数発散する。これは前述の正モーメント条件と一致する。δの具体値は未選択で、このpriorの採用・実装を決めたものではない。既存regularized codやLaplace近似を使った結果とも別である。超幾何関数表示はEuler積分の記号的書換えであり、数値評価はしていない。

## 5. H0とg=0

H0は y|E,a,H0∼N(0,E C(a))。βを持たない。方向kernelは上式のB=C、すなわちg=0極限と一致する。

H0にも W と A を用意し、D_0W(u)=p_dir(u|C=I)、D_0A(u)=∫p_dir(u|C(a))Π_A(da) とするのが公平なnoise候補の比較に必要。H1だけにAを許すと、colored noiseを説明できること自体がH1側の支持になり得る。H0/H1で同じnoise priorを使うか、異なる科学的理由を明示するかも契約事項である。これはH0探索を実施する提案ではなく、将来比較する際の必要条件の列挙。

固定C・固定gのH1/H0比は

 (1+g)^(−d/2) [1−{g/(1+g)} R_C²]^(−N/2),
 R_C²=J/T。

これは同じ元yに対する式である。aを混合する場合はそれぞれのevidenceを積分してから割るので、固定aの比を無条件に平均してよいわけではない。

「g=0でkernelがH0と同じ」と「H0モデルのposterior massがある」は違う。連続π_gの一点g=0には質量がない。H0には離散model priorが必要で、H1内にg=0の原子も持たせるなら同じ分布を表すラベルの重複とmass配分を明示する。有限g>0でβのprior平均が0であるだけではH0ではない。

## 6. 不変性・極限・モデル仮定

### C依存g-priorの意味

これは単なる計算上のwhiteningではなく、noise仮説が変わると元座標でのβ priorも変わる共同モデルである。whitened signal Xβ のprior covarianceは gE P。従ってE[(Zβ)ᵀC⁻¹(Zβ)|E,g,a]=gEdで、whitened signal energyをnoise幾何で校正している。元座標の Euclidean signal energy の期待値 gE tr(ZG⁻¹Zᵀ) は一般にa依存。W/A比較を「同じβ priorを保った純粋なnoise covariance比較」と呼べない。

もしβ prior covarianceをCから独立な別行列に固定すれば別のBが生じ、一般に |C|(1+g)^d という簡約は失われる。どちらが適切かの採用は本書では行わない。

### white極限

a→0で C→I、G→ZᵀZ、Q→yᵀy−[g/(1+g)]yᵀZ(ZᵀZ)⁻¹Zᵀy。固定gのkernelは通常のwhite g-prior形へ連続に戻る。g混合の極限交換は非完全fitなら上記の一様有界性、完全fitなら必要モーメントなどの支配条件の下で行える。

これは既存regularized cod＋Laplace実装の回収を証明しない。既存の yᵀy+N varSpeech という固定正則化、g hyperprior、近似とその定数、候補prior・遷移まで一致させる別の検討が必要。本式に無断でvarSpeechを挿入して同一式だと主張しない。

### Zのbasis変換

任意の可逆d×d行列Rで Z'=ZR とすると G'=RᵀGR、Z'G'⁻¹Z'ᵀ=ZG⁻¹Zᵀ。β'=R⁻¹βの密度Jacobianも含めた正規化priorなら、B・Q・方向evidenceは不変。列の単なる単位変更やsin/cosの可逆な位相basis変更でevidenceが変わってはいけない。

rank欠損ならG⁻¹は存在せず、提示されたd次元proper priorは未定義。擬似逆行列と旧dをそのまま代入してはいけない。rank rの独立basisで同じsignal subspaceをモデル化し直すなら指数はr、係数測度もr次元にする。元の冗長係数を残すならnull方向を含むpriorの新契約が必要。近いrank欠損への数値閾値も実装段階の別契約。

### なぜN−dではないのか

flat β priorの形式積分ではE^(d/2)が残り、scale積分のRSS指数が−(N−d)/2になる。一方本書のnormalized conditional priorはE^(−d/2)を既に含むため、残る指数は−N/2。g→∞でnormalized priorを保ったまま極限を取ることは、flat β測度を採用することと同じでない。定数を捨ててこの二つを混同できない。

## 7. 5仮想役・2往復の点検

以下は一人の導出を5つの観点で点検した仮想レビューであり、5人の独立研究者・5エージェントの検証ではない。

### 第1往復：各役の反論 → 導出側の応答

1. 測度担当：「dE/Eの発散を消しただけではproper evidenceではない。」→ raw量はm*と表記し、球面面積測度上のp_dirを半径積分から独立に導いた。両者の係数2||y||^−Nを明示した。
2. 線形代数担当：「det Gが消えるのはprior正規化を忘れたのではないか。」→ conditional densityの|G|^(1/2)を明示し、whitened rank-d射影からdet Bを導出した。basis不変性でも整合した。
3. AR境界担当：「trace正規化とinnovation varianceを取り違えていないか。」→ Eはmarginal variance、innovation varianceはE(1−a²)、初期状態も定常とした。総分散NEとN=1の例外を明記した。
4. モデル比較担当：「H1にだけcoloredを与えればH0不利になる。」→ H0×W/Aの定義を必要条件として追加し、g=0 kernelとH0 labelの質量を分けた。
5. 批評家：「properπ_gなら何でも安全という主張は完全fitで破れないか。」→ S=0のときの正確な正モーメント条件を導出し、proper密度と点ごとの有限性を分けた。

### 第2往復：再反論 → 判定・残る契約

1. 測度担当：「方向化で何を失ったか。零窓は？」→ 振幅情報を捨てた実験である。raw amplitude evidenceが必要ならproper scale priorを別途定義する。y=0は未定義として保留。
2. 線形代数担当：「rank欠損を擬似逆で救えば十分か。」→ 旧dと係数測度を残す修正は不可。独立basisまたはnull方向priorが必要。rank選択は実施しない。
3. AR境界担当：「a→0だからA family evidenceもwhiteに一致するのか。」→ 固定a kernelの極限とΠ_Aによるfamily積分は別。Π_Aを0へ集中させること自体も新prior選択であり行わない。
4. モデル比較担当：「C依存priorはnoise比較を純粋に保つか。」→ 保たない。whitened signal energyに対する仮定であり、元係数priorがaに依存することを比較の意味に含める。
5. 批評家：「white極限が出れば既存pitchや既知q実験へ直結できるか。」→ 不可。正則化・Laplace・DC・生成平均の仕様が異なる。500 pairをwaveformへ足してそのまま転用する案は採用しない。

## 8. 一次出典と確認範囲

数学部分は上記のGaussian和・射影・scale積分・polar積分からの独立導出であり、colored化した本式を既報の結論として引用していない。

white harmonicモデルでのscale priorとconditional g-priorの対応を確認するため、Shi et al. (2019), “Robust Bayesian Pitch Tracking Based on the Harmonic Model” の著者accepted manuscript、本文式(12)–(14)を今回確認した。式(12)はscaleの逆数測度、式(13)はnoise varianceに連動したGaussian係数prior、式(14)は同論文固有のg priorである。本書は式(14)の形や値を採用していない。[一次本文](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)、[DOI](https://doi.org/10.1109/TASLP.2019.2930917)。

既存実装のDC列なし・regularized cod・varSpeechの記述、および既存文献調査の範囲は前文書 noise-pitch-integration-boundary-20261020.md の読取りに基づく。今回リポジトリの追加取得・コード検証はしていない。既知qが正DCを持つことは本依頼で与えられた前提であり、データ再計算による確認とはしない。

現段階の紙上の一問には上の一次確認で十分。既存実装との厳密一致を今後主張するなら、実装契約の固定版、原著のg積分・Laplace式、正則化の由来を追加照合する必要がある。ARの外部実装との一致を主張するなら、その論文・コードが定常初期状態込みか条件付き尤度かを確認する必要がある。今回はその作業、文献網羅探索、最適priorの調査へ進まない。

## 9. 次に必要な契約と停止点

次を決める前に実装・数値比較へ進めない。

1. 対象は同じ元yの方向evidenceか、振幅を含むraw evidenceか。後者ならproper scale priorが必要。
2. Eの単位、N、窓・前処理、AR初期状態を共通に固定する。
3. π_gの支持・分布・独立性、完全fitに対する尾部条件を定める。ここでは値を選ばない。
4. Aのproper Π_AとW/Aのmodel mass、Aが0を含む際の意味を定める。ここではpriorを採用しない。
5. C依存g-priorを科学的仮定として受け入れるかを決める。元座標で同一β priorを希望するなら別モデルを導出する。
6. H0にも同じnoise候補を与えること、g=0の原子とH0質量の重複をどう扱うかを定める。F0・次数探索は別段階。
7. y=0、完全fit、rank欠損・近いrank欠損の扱いを定める。
8. 正DCを持つ既知q実験とDC列なしの既存pitchの観測モデル差を解決する。DC追加・中心化・別のzero-DC生成meanはいずれも新契約であり、本書では採用しない。既存500 pairをwaveformへ足してそのまま転用しない。
9. 既存regularized cod＋Laplaceの回収を要求するか否かを、今回の数理的一貫性とは別の目的として定める。

以上の列挙を停止点とする。式が整合することはモデルの採用・実験の識別性能・自然音声での校正成立を意味しない。
