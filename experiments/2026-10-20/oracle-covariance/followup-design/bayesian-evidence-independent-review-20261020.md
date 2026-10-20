# 共通 scale evidence と raw BMA predictive の独立数理レビュー

2026-10-20。対象は noise-model-evidence-design-20261020.md と cyclic_noise_identification_design_20261020.md。本文の式を独立に導出して検討した。実装、計算コードの実行、新規 tests/smoke、データ生成、Git 変更は行っていない。保存済み500 pair・2500 scoreの完成状況は依頼元の情報であり、本レビューで再計測した結果ではない。

## 1. 結論

候補の数理的中心は成立する。共通 dE/E の形式 evidence 比は、指定された共通 scale 群に対する球面方向の proper evidence 比と厳密に一致する。train posterior が proper なら、同じ形式 prior に由来する raw heldout posterior predictive と BMA は正規化された密度になる。N と 2N の Gamma・π定数も対象文書の式で正しい。

ただし、これは「raw 残差について proper joint prior predictive が存在する」「生理的原因の確率が校正済み」「既存 plug-in より必ず良い」を意味しない。設計候補としては支持できるが、実装採用・追加解析の開始を推奨または許可したレビューではない。

実施を阻む未凍結事項は次のとおり。

1. shape/model prior と formal scale 経路を研究上の参照仮定として採択するかが未決定。proper E prior の仮定と混在させない。
2. train と joint の両方に対する posterior propriety・数値誤差 gate が未完成。特に S/J joint の tail bound と、絶対積分誤差から log evidence 誤差への換算を追加する必要がある。
3. 保存 float64 geometry の実 norm に従う E・α・prior の定義、再解析入力の同一性、失敗時の比較母集団を固定する必要がある。
4. 10^-6 nats の計算目標と predictive/BMA score の誤差上限を区別する必要がある。現時点で certified accuracy を主張できない。

根本的な反例で候補全体が不成立という結論ではなく、科学的意味と数値契約を凍結しないまま実行すると意味が変わり得る、という blocking issues である。

## 2. 共通 improper prior と球面 evidence

残差 x∈R^N、既知共通 mean、Σ=EC_η、tr(C_η)=N、E>0 とし、Q=xᵀC_η^-1x と置く。x≠0 で C_η が正定値なら Q>0。

∫ p(x|E,η)c dE/E
= c Γ(N/2) π^(-N/2)|C_η|^(-1/2)Q^(-N/2)
= m*(x|η)。

t=Q/(2E) と置けば直ちに得られる。m*(rx)=r^-N m*(x) であり、半径積分は ∫dr/r。したがって raw 空間上の proper density ではない。全候補で同じ文字 E を使うだけでは未知の比例定数 c を共通化できる根拠にならない。

しかし、u=x/||x|| とし、Gaussian density を実際の半径要素 r^(N-1)dr で積分すると、球面面積測度に関して

f(u|η)=Γ(N/2)/(2π^(N/2)) |C_η|^(-1/2)(uᵀC_η^-1u)^(-N/2)。

E は厳密に消え、積分1である。従って m*(x|η)=2c||x||^-N f(u|η)。proper な π_m(η) を掛けて積分してもこの関係は保たれ、同じ x に対する比は一致する。この特殊化を根拠にするのが妥当であり、「improper nuisance は共通ならいつでも安全」という一般化は不要かつ不適切である。

成立条件は、同じ N・残差座標・既知 mean・測度・正の全体 scale 変換、scale と独立な proper shape prior。同一 q を使っていても、モデルごとにデータを投影する、mean を推定して自由度を減らす、候補別に初期サンプルを落とす等では同じ証明にならない。今回の球面は S^(N-1) であり、mean 未知の場合の residual sphere へ勝手に読み替えない。

符号反転まで商空間化する必要はない。正の scale 群の最大不変量は符号を含む u であり、Gaussian により f(u)=f(-u) となるだけである。球面一様確率測度を基準とする表現なら面積定数が変わるが、共通なら BF は不変。raw predictive と混ぜない。

## 3. raw posterior predictive の整合性

train に対し E|η,x_tr ~ IG(N/2,Q_tr/2)。shape posterior は π_m(η)|C_η|^-1/2 Q_tr^-N/2 に比例する。これが積分可能であれば、条件付き test Gaussian を proper posterior で積分した密度は必ず積分1になる。

条件付き独立は E・η に条件付けた独立であり、parameter を積分した後の train/test 独立ではない。両 record は同じ E・η を共有し、AR 初期状態・innovation・周期 random effects は別に引く。そのため joint shape covariance は C_η⊕C_η。AR に record 境界を跨ぐ一つの innovation を追加しない。S/J の周期係数を対応する train/test 周期間で共有しない。

J_m,n(D)=∫π_m(η)|C_D(η)|^-1/2 Q_D(η)^(-n/2)dη と定義すると、

p_m(x_te|x_tr)=Γ(N)/[Γ(N/2)π^(N/2)] · J_m,2N(tr,te)/J_m,N(tr)。

joint 側は |C_D|^-1/2=|C_η|^-1、Q_D=Q_tr+Q_te。共有 scale を一回だけ積分するので指数は -N。二つの独立 scale を積分した積ではない。

重み w_m=π_m J_m,N/Σ_jπ_jJ_j,N を使うと、BMA はさらに

p_BMA=Γ(N)/[Γ(N/2)π^(N/2)] · [Σ_mπ_m J_m,2N]/[Σ_mπ_m J_m,N]。

この表現は cancellation と error propagation の確認にも有用。shape ごとの predictive を prior 平均するのではなく train shape posterior で平均する。model 重みを test で更新してから同じ test の predictive を評価してはいけない。評価量は log Σ_m w_m p_m であり Σ_m w_m log p_m ではない。

これは formal joint measure の ratio として首尾一貫した一般化 Bayes predictive である。一方で適切な raw joint prior predictive や、その母集団での無条件 calibration が自動的に存在するわけではない。direction evidence は raw 予測を正規化するための必要条件ではないが、このケースで model weights を解釈する明確な根拠になる。

## 4. 保存 sufficient statistics で計算できる式

以下は保存 raw 残差・geometry から計算可能な統計量の列挙であり、既存ファイルにこれらの全統計量が既に保存されていることは本レビューでは確認していない。2500個の最終 plug-in score と MLE だけでは、連続 shape 積分を一般には復元できない。

### W

T=Σ_n x_n²。Q=T、log|C|=0。shape 積分不要。raw predictive は

Γ(N)/[Γ(N/2)π^(N/2)] · T_tr^(N/2)/(T_tr+T_te)^N。

これは constants と dimensions の解析的な照合対象になる。新規 test の実施指示ではない。

### A

T=Σ_n x_n²、H=x_1²+x_N²、R=Σ_(n=2)^N x_n x_(n-1)。stationary correlation C_ij=a^|i-j| に対して

Q(a)=[(1+a²)T-a²H-2aR]/(1-a²)、
log|C(a)|=(N-1)log(1-a²)。

数学的に同じ正の二乗和は Q=x_1²+Σ_(n=2)^N(x_n-a x_(n-1))²/(1-a²)。前者は十分統計量表示、後者は cancellation の検査に使える表示であり、同じ数値安定性を保証するものではない。joint は二つの Q と log determinant を足す。H は両 record の端点四つの和、R に record 境界の積を加えない。

### V

z_l=(cosφ_l,sinφ_l)、T_l=Σ_(k=1)^K x_(kl)²、Z(b)=L^-1Σ_l exp(b·z_l)。

Q(b)=Z(b)Σ_l T_l exp(-b·z_l)、
log|C(b)|=KΣ_l b·z_l-N log Z(b)。

理想的な等間隔 grid では Σ_l z_l=0 なので後式は -N log Z。保存浮動小数点 geometry で厳密な零を仮定するか実和を使うかを固定し、黙って変えない。joint は phase energy を足し、各位相の反復数を 2K とする。円板 prior を極座標で求積する場合、r dr dθ の r を必要とする。

### S/J

保存 direction g または h を v_dir と書き、d=||v_dir||²>0、e=v_dir/√d。A=Σ_k(eᵀx_k)²、B=Σ_k||x_k-e(eᵀx_k)||²。数学上 T=A+B。数値上の B を T-A の大きな差し引きだけで作らない。

原 covariance vI+t U Uᵀ に対し c_d=d/L、E=v+c_dt、α=c_dt/E。U*=U/√c_d とすれば

C=(1-α)I+αU*U*ᵀ、ε=1-α、λ=L-(L-1)ε、
Q=B/ε+A/λ、log|C|=(N-K)log ε+K log λ。

同一 d が全周期に使われる元設計で成立する。周期ごとに方向が異なる場合の一般式に自動的には拡張できない。

uniform α と dE/E を原 (v,t) で書くと

dE dα/E = c_d dv dt/(v+c_dt)²。

従って d=L とした 1/(v+t)² の式は名目上の単位 RMS に限る。実 norm と整合する prior を固定すべきであり、保存 direction の再正規化や生成 data の修正は不要。実 norm 補正が微小であっても、この点は「完全に同じ prior」の定義上重要である。

全候補の統計量は record ごとに保持し、joint では足し合わせるだけでよい。500 pair を一つの parameter に pool する指示ではない。

## 5. S/J 特異端：train と joint の両方の上界

r 本の独立 record が同一 E・α を共有すると、n=rN、k=rK、A_r=Σ A_i、B_r=Σ B_i。scale 積分の shape kernel は

k_r(ε)=ε^(rK/2) λ^(-rK/2)[B_r+ε A_r/λ]^(-rN/2)。

これは determinant と Q の発散を解析的に相殺した表示である。B_r>0 なら ε→0 で ε^(rK/2) の次数で消える。uniform α prior で 0<δ≤1、λ≥1 より

∫_0^δ k_r(ε)dε ≤ B_r^(-rN/2) δ^(rK/2+1)/(rK/2+1)。

さらに λ≥L-(L-1)δ を使えば、この右辺に [L-(L-1)δ]^(-rK/2) を掛けたより強い上界になる。

train は r=1、joint は r=2。対象文書の train bound は正しい。joint の tail は ε^K、B_2^-N、分母 K+1 とする別の bound が必要。train の cutoff と error estimate をそのまま流用してはならない。

B=0、A>0 なら k_1 は ε^(-(N-K)/2) に比例し、uniform α prior 下では N-K≥2 で発散する。今回 N-K=4032 なので posterior は improper。確率零という理由で実データの gate を省略しない。x=0 は全候補の scale posterior も improper。B が正でも極端に小さい場合は、数学的 propriety と数値可解性が別問題になる。floor、恣意的 α 上限、候補削除で隠さない。

## 6. 数値 error budget の必須修正

対象文書の 10^-6 nats/log evidence は計算精度の目標であって科学的差の閾値ではない。この区別は妥当。ただし三つの補足が必要。

第一に、tail の絶対積分上界だけでは log error の予算に対応しない。非 tail 部分の厳密な正の下界 L_int>0 と、求積・tail を含む総絶対誤差 U_err があれば、比 U_err/L_int から log error を評価する。例えば exact truncated integral J_0 に tail T≤U_tail なら、log(J_0+T)-log J_0≤log(1+U_tail/J_0)。実際には J_0 自体の求積誤差も入れ、区間 [J_low,J_high] で log(J_high/J_low) を管理する。log shift は必須だが、relative error の証明の代わりにはならない。

第二に、train/joint の各 log J が絶対誤差 δ 以内なら、per-model predictive log ratio は 2δ 以内。二つの予測 score の差は保守的に 4δ。BMA を第3節の ratio-of-sums で計算すれば log-sum-exp の最大ノルム Lipschitz 性から BMA log predictive も 2δ 以内であり、別途 numerical constants の誤差を加える。2δ 以内という BF 誤差だけを predictive 全体の誤差と混同しない。

第三に、Γ(N)、Γ(N/2)、π 定数の log 評価、統計量の演算、log determinant/Q の演算、prior 正規化、log-sum-exp 自体の誤差を予算へ含める。巨大な log J を個別に計算して差を取ると cancellation がある。既存 MLE solver の成功、求積 library の error estimate、二つの精度設定の一致だけでは certified bound を保証しない。検証できる範囲を「収束診断」と「保証付き bound」に分ける。

weight について |δ log J_m|≤δ なら ŵ_m/w_m∈[exp(-2δ),exp(2δ)]。対象文書の保守的 absolute bound exp(2δ)-1 は妥当。ただし model probability が数値的に精密でも、prior 仮定の正確さや確率 calibration は保証されない。

## 7. 五つの truth point と calibration

現在の100 pair×5 truth は、固定 parameter の各条件での predictive performance・weight 分布・entropy・分類結果を記述できる。各 family 内の prior 全域の反復ではないので、declared posterior probability の calibration をこのデータだけで一般的に実証したとは言えない。

proper な direction generative experiment では M~π、η~π_M、u~f_M(·|η) とすれば、正確な posterior w_m について E[1{M=m}|w_m]=w_m が条件付き期待値の法則で成立する。E は方向から消えるため、この方向の検証に E の prior sampling は不要。一方 raw joint prior predictive calibration を求めるなら、proper な E prior を含む別の生成契約が必要になる。

固定五点の balanced labels で reliability plot を描くこと自体は可能でも、その対象母集団は人工的な五点混合であり、連続 shape prior の posterior の理論的 calibration と同じではない。100/100 の正解率、W の winner 割合、high posterior weight は互いに別の量である。既に test を見て提案したため、新再解析は exploratory/post hoc と明記する。今回 calibration 実験や追加生成を提案実施しない。

## 8. 最小 scientific contract

実施判断を将来する場合は、次の八項目を一枚の実行契約へ固定すればよい。

1. 対象：保存済み500 train/test pair の raw oracle residual、既知 q/phase、H=I、N=4096。追加データ・音声・family・mean/phase fitting・再正規化なし。
2. 問い：指定五 family の direction evidence による参照 posterior model weights と、formal common-scale posterior による raw BMA predictive。生理的原因確率、音質、自然音声一般化を主張しない。
3. prior：model weight、A/V/S/J shape prior、実 norm での E・α、全支持、測度と Jacobian を固定。proper E の別経路を暗黙に混在させない。test/truth で調整しない。
4. independent record：shared θ と independent latent draws、AR stationary initial law、C⊕C、joint dimensions 2N を固定。pooling なし。
5. propriety：x≠0、S/J の train B>0、有限正定値等を検査する仕様を定義。違反時に floor・prior cutoff・モデル脱落による別 BMA を成功扱いしない。
6. accuracy：train と joint の別 tail bounds、positive integral lower bound、統計量/定数/求積を含む error budget、predictive と score difference への伝播、非達成時の表示を事前固定。未検証を certified と呼ばない。
7. 比較：旧2500 plug-in scores を保持し、raw nats/record の新 per-model predictive と BMA を同じ test に対で併記。winner 修復率を主指標にせず、五重み・entropy・score 差・失敗数を示す。失敗 pair を黙って除外して平均母集団を変えない。
8. 主張と停止：固定五点の記述的再解析のみ。calibration・prior 選択の優越・音声機能採用は別判断。新規 tests/smoke、実装、Git 変更をこの設計承認と同一視しない。

この契約が未確定である限り、今回の適切な停止点は数理設計レビューの完了である。

### 追補：親側の実施範囲案と A の安定な統計量

evidence-reanalysis-scope-20261020.md も追加で確認した。五 family のいずれかが必要な積分 gate を通らない pair で BMA を欠測とし、成功候補だけで再正規化しない方針は正しい。posterior shape quantile を最小解析から外しても、model evidence と predictive の数理契約は損なわれない。

五 truth × 五 comparator の25個の pointwise 95% paired-bootstrap CI は、同時保証や多重比較調整された優越性を意味しないと明記する限り、記述目的に整合する。ただし一部 pair が欠測なら、成功 subset だけの bootstrap CI は元の100 pairについてのCIではない。失敗は parameter/record に依存し得る。元100を対象とした平均・CIは未確定とし、成功 subset の値を示す場合は別枠で「計算成功 subset の条件付き記述」と明示する。失敗分母と原因も保存する。bootstrap 回数・seedだけでなく、percentile等の区間方式を凍結する。

scope の工程番号では求積・refinement が契約凍結より先に置かれているが、実行順は逆にする。実データ上の結果に応じて scientific prior・支持・数値成功閾値を変えない。事前規定された refinement は許容し、resource limit で止まった結果は未確定とする。

A のより安定な十分統計量として、各 record の (N-1)×2 行列 X の行を (x_n,x_(n-1))、n=2,…,N とし、thin QR の上三角 R と x_1² を保存する案は正しい。XᵀX=RᵀR より

Q(a)=x_1²+||R(1,-a)ᵀ||²/(1-a²)。

joint は各 record の x_1² と ||R_i(1,-a)ᵀ||² を足せば十分であり、二つの R を積んで再 QR することは必須ではない。QR の数値誤差も既存の丸め予算に含める必要がある。「QRを使ったから certified」とは言わない。|a|≤0.8 は分母を0から離すが、それだけで全演算の絶対 log error 10^-6 を証明するものではない。これは数式上の安定化の選択肢であり、今回の実装指示ではない。

## 9. 根拠と確認範囲

根拠は対象二文書に提示された有限次元 Gaussian model と、ここに示した積分・固有値・Jacobian・条件付き期待値の独立導出である。文献の定理を未確認で適用して正当化してはいない。対象文書の参考文献を新たに全文精読したとも主張しない。保存データ数値、solver、source code、実際の tail tolerance 達成度は今回の確認範囲外である。

## 10. 理論補足：W 単独の unknown-scale predictive の期待 score

この節だけは W family を真値・予測モデルの双方に固定する。既知平均0、真分散 E>0、同じ長さ N の train/test は互いに独立とする。BMA の性能保証でも、保存500 pairの実測結果でもない。追加実験や数値実行をせず、反復期待値を解析する。

k=N/2、T=||x_tr||²、U=||x_te||²、X=T/E、Y=U/E と置く。X,Y は独立 χ²_N で、X+Y は χ²_(2N)。Gamma(shape, scale) 表記では X~Gamma(k,2)、X+Y~Gamma(2k,2)。従って

E[log T]=log(2E)+ψ(k)、
E[log(T+U)]=log(2E)+ψ(2k)、
E[U/T]=E[Y]E[1/X]=N/(N-2) （N>2）。

ψ は logΓ の導関数。最初の二式は Gamma 積分を shape で微分して得られ、最後は Gamma の逆一次モーメントから得られる。

共通 dE/E からの posterior predictive は第4節の W 式であり、log score は

ℓ_post=logΓ(N)-logΓ(N/2)-(N/2)logπ
       +(N/2)log T-N log(T+U)。

従って

E[ℓ_post]=logΓ(N)-logΓ(N/2)
          -(N/2)log(2πE)+(N/2)ψ(N/2)-Nψ(N)。

一方、train MLE は Ê=T/N であり、test plug-in log score は

ℓ_MLE=-(N/2)log(2πT/N)-NU/(2T)。

N>2 のとき

E[ℓ_MLE]=-(N/2)log(4πE/N)-(N/2)ψ(N/2)-N²/[2(N-2)]。

差を D=E[ℓ_post-ℓ_MLE] とすると、真 scale E が消え、

D=logΓ(N)-logΓ(N/2)
  +N[ψ(N/2)-ψ(N)]
  -(N/2)log(N/2)+N²/[2(N-2)]。

親から提示された式と一致する。有限な期待値同士の差としての適用条件 N>2 を明記する。N≤2 では MLE の逆 scale モーメントが発散し、この有限式をそのまま使えない。今回の N=4096 は条件を満たす。

### 大標本極限

k=N/2 として Stirling 展開と digamma 展開を別々に適用すると、

logΓ(2k)-logΓ(k)
=k log k+(2k-1/2)log2-k-1/(24k)+O(k^-3)、

2k[ψ(k)-ψ(2k)]
=-2k log2-1/2-1/(8k)+O(k^-3)、

k²/(k-1)=k+1+1/k+1/k²+O(k^-3)。

これらから k log k、k、2k log2 が消え、

D=(1-log2)/2+5/(6k)+1/k²+O(k^-3)
 =(1-log2)/2+5/(3N)+4/N²+O(N^-3)。

よって lim_(N→∞)D=(1-log2)/2 nats/record であり、提示された極限も正しい。これは train だけでなく評価する test record 長も N とともに増える極限である。1 sample 当たりの差 D/N は0へ収束する。有限固定長の test に対し train だけを無限に増やす別の極限と混同しない。

この結果が示すのは、W 単独で未知 scale を推定する場合、parameter uncertainty を積分することには train/test 反復期待値上の効果がある、という限定された性質である。個々の保存 pair で posterior predictive が必ず勝つこと、五 family の BMA が W predictive または既存全 plug-in に勝つこと、posterior model weights が calibration 済みであることは導けない。N=4096 での数値評価は今回行っていない。
