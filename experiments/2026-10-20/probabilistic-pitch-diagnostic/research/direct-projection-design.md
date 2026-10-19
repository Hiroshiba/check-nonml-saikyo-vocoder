# 固定格子harmonic射影による代替経路の実現性

2026-10-19 UTC。調査・数式設計のみ。実装、依存導入、推定器実行、音声処理、速度測定、試験、Git変更は行っていない。ローカル既存計画と監査、fresh著者classを読み、同じ固定commitの著者helper・wrapper・LICENSEと原著を新たに読んだ。

## 結論

**NumPy/SciPyで、固定格子の通常のharmonic最小二乗射影を用いる一つの代替案は成立する。** 置換するのは著者fast Toeplitz/Hankel再帰によるJ計算だけ。g-prior/Laplaceの局所log Bayes factor、H0比較、時間filterと再有声化記憶は同じ宣言式を維持する。これは「著者MATLABを実行した結果」「bit一致移植」と呼べない。元計画は無断の即席移植を禁じているので、採用前に経路変更を明示する必要がある。

提案は、最大次数の二つのCholesky分解をF0ごとに事前計算し、一回のFFTから全次数のJを求める方法。全次数・全F0のinverseを保存する必要も、毎frameで行列分解する必要もない。数学的には実装対象が小さく、5入力一回という用途ではcredibleなfallback。実際の数値状態・既存NumPy/SciPy/BLASの利用可否・30分以内の完走は未確認。

## 1. 変更境界と固定事項

- 16 kHz、N=400、hop=160、矩形窓、FFT長F=16384、DC列なし、epsilon=0。
- q=ceil(16384×50/16000)…floor(16384×500/16000)=52…512。P=461、実格子は50.78125…500 Hz、間隔0.9765625 Hz。50 Hzのセルが存在するという記述は避ける。
- K=1…10。全harmonic binはNyquistより小さく、矩形461×10が有効。
- 5入力の元保存配列、全中心、両端zero-padding、記録項目、local/baseとlocal/log-Hz再重み付けは既存計画を維持する。5入力最大2614frame。
- fresh wrapperでは目標RMSが sqrt(3.1623e-5)、scale=同値/録音全体RMSであることを確認。全zero録音は除算前に別扱い。frame正規化やDC除去を足さない。
- 著者wrapperは先頭paddingのみで末尾に窓が収まるframe数を採用する。既存診断計画の全中心・末尾paddingはそのwrapperと同一でない。正規化係数を借りることと全wrapper再現を区別する。
- varSpeech=5e-6、δ=3、初期voiced=0.7、F0×K一様、F0遷移SD=2 Hz、K遷移SD=1、C=[[.7,.3],[.4,.6]]を固定。新しいtracker、調整探索、追加音質gateは足さない。

## 2. 射影の設計と同値性

ここは原著式(27)(28)と著者helperの構造からの線形代数的導出であり、実行比較結果ではない。

時刻 t_n=n−(N−1)/2、n=0…399。F0=q/F cycles/sampleとして、C[n,h]=cos(2πhqt_n/F)、S[n,h]=sin(2πhqt_n/F)、h=1…10とする。観測値を平均中心化する意味ではなく、**基底の時刻原点**を中心に置く。対称支持なのでCᵀS=0が厳密算術で成立する。

F0ごとにG_c=CᵀC、G_s=SᵀSを作る。cos/sinを直接評価して小行列を積算すればよい。著者のDirichlet/Toeplitz/Hankel再帰を翻訳する必要はない。各GをG=L Lᵀに分解してLだけを保持する。明示的inverseは推奨しない。

frameごとにX=FFT(x,F)を一度計算。D_h=X[hq] exp(+i 2πhq(N−1)/(2F))。b_c=Re(D)、b_s=−Im(D)。著者helperはIm(D)を使用するが、全sin列の符号を反転した基底であり、二次形式Jは同じになる。FFTの正規化は通常の前向き無正規化で、NやFを余分に掛けない。

L_c y_c=b_c、L_s y_s=b_sを最大次数10まで解く。lower triangularの先頭K行は先頭K要素だけに依存し、leading principal blockのCholeskyが同じLの先頭K×Kになるため、

J(q,K)=sum_{h=1..K} y_c[h]^2 + sum_{h=1..K} y_s[h]^2。

したがって一つのsolveと累積和から全Kが得られる。これは全Kを別々に射影した bᵀG⁻¹b と厳密算術では同じ。基底の順序は両ブロックともharmonic昇順を固定する。各frameで2×461回のPython関数呼出しをする設計ではなく、F0方向にベクトル化した10段のforward substitutionなどで実装できるが、API・性能は未確認。

この同値性はepsilon=0・DCなし・矩形観測・固定gridに限定する。Gram ridgeを入れた場合、Jは元の直交射影でなくなり、g-priorの対応も再検討が必要。varSpeechはGramのridgeではない。

## 3. 局所logBFとH0の維持

E=xᵀx、r=J/(E+N×5e-6)。著者classと同じregularized codを使う。原著の非regularized説明比と完全一致するBayes factorと称さず、「著者実装のregularized codを用いたLaplace局所log比」と記録する。

fresh computePitchLogLikelihood.mの式は、v=1、w=(N−2K−δ)/2、u=N/2、a=(1−r)(v+w−u)、b=(u−v)r+2v+w−u、D=b²−4avとして、

- g=(b+sqrt(D))/(−2a)
- τ=1/[g(1−r)u/(1+g(1−r))² − gw/(1+g)²]
- ℓ=log(g(δ−2)/2)+w log(1+g)−u log(1+g(1−r))+.5 log(2πτ)

H0のlog比は0。δ=3、K≥1、0≤r<1ではa<0。b<0のときg=2v/(sqrt(D)−b)を使えば、同じ正根を桁落ちを抑えて評価できる。log1pも利用候補。これは数学的同値な安定化であり浮動小数点の元コード完全再現ではない。τの逆数の差が不安定な場合は、値を丸めて正にせず失敗扱いにする。2F1で置き換える案は今回追加しない。

local/baseは0.7/(P×10)とH0=.3でlog-sum-exp正規化。log-Hz感度は同じℓの1/f再重み付けのみ。filteredは以下の著者更新を維持する。Qは前回voiced joint PMF、p0は前回H0、Rは最後にp0<.5だった時のvoiced条件付きPMF。

- voiced予測 U=.7 Aᵀ Q B + .4 p0 R
- H0予測 u0=.3(1−p0)+.6 p0
- U×exp(ℓ)とu0を一緒にlog域正規化
- 更新後p0<.5のときだけR=Q/(1−p0)を更新し、元frame IDを記録

A/Bの行正規化、配列向き、初回は遷移せず初期priorから更新することまで保つ。Rの条件分岐は新しい品質判定でなく著者動作。filteredをfull-sequence posteriorや校正済みconfidenceと呼ばない。60%重複窓の情報重複に関する元計画の留保を維持する。

## 4. 特異性・数値失敗・無音

理想算術では各qの±harmonic周波数は相異なりNyquist未満、N≥20なので基底はfull column rank。ただしこの事実からfloat64の条件数やCholesky残差が良好だったと主張しない。

固定grid前計算時に、Gramの非有限値・対称性誤差・分解失敗・条件数と分解残差を記録する。誤差評価はfloat64の丸め・行列サイズ・条件数を根拠とする数値計算上の整合性であり、音質の採否閾値ではない。条件数だけを根拠に任意に候補を消さない。数値信頼性を確保できなければ固定支持の前提を満たせないblockerとして止める。pinv、rank切捨て、ridge追加、窓延長、F0除外への自動救済はしない。

frameでは入力/E/J/r/g/τ/ℓと正規化の有限性を確認する。射影は0≤J≤E、従って0≤r≤E/(E+.002)<1を満たす必要がある。丸め逸脱に対して無条件clipをしない。残差・誤差上界と生値を記録し、矛盾が解消できなければそのframeをnumerical_failureとし、posteriorを捏造せず当該入力のfilter進行を停止する。後続frameは未処理と明記する。数値失敗セルを−infにして他の候補やH0へ質量を移すのは、今回の完全な矩形支持では許容しない。元classのNaN→−inf処理との相違として明示する。

E/N<1e-10は別のenergy_floor。著者と同じく内部stateを更新しない。local/filteredはmissing、state_updated=false、最後の更新frameとskip数を保存する。返り値voicing=0をH0 posterior=1へ読み替えない。録音全体zero、padding、弱いframe、非有限入力、数値失敗は別理由。録音間はresetするが、同じ録音の無音中にstateをresetしたり時間遷移を進めたりしない。

## 5. 資源見積もりと上限

配列形状と算術量からの概算でありbenchmarkではない。

- 2×P×10×10のfloat64 Cholesky保管は737,600 bytes、約0.74 MB。Gramを両方保管しても計約1.48 MB。
- 基底を全F0分保管すると2×461×400×10×8=29.5 MB。前計算をF0単位にすれば不要で、基底一組は64 kB程度。
- FFT作業配列はF個complex128なら約0.26 MB。各frameのb/Jは小さい。
- 全2614frameのprojection solveは概算O(2TPKmax²)、2.41×10^8程度のスカラー項を保守的目安とする。累積和とFFT等は別。各Kごとの独立solveより小さい。
- 時間更新はO(T(P²K+PK²))、約5.68×10^9積和項が支配。BLASやスレッド設定次第なので秒数には換算しない。Gaussian遷移のband打切りやsparse近似は足さない。
- 全frame joint配列一種類約96.4 MB、log比/予測prior/filteredの三種類約289.2 MB。二つのlocal PMFまで全保存するなら追加約192.8 MB。元のℓから再計算できるものは重複保存せず、chunk書込みを基本とする。CSVは全grid全値を素朴に文字列化すると1 GiBを超えうるので、全grid正本はbinary、frame要約をCSVとする出力仕様の明記が必要。

元計画のwall 30分、RAM 2 GiB、出力1 GiBを維持。Cloud B空き23 GBは親からの現状情報であり、この調査で再確認していない。空き容量があることは性能保証でも大規模installの許可でもない。予算到達時はpartial/未処理frameを報告し、黙って別設定にしない。導入不要で既存NumPy/SciPyが利用できる場合に運用コストが小さい、という条件付き利点である。

## 6. faithful Octave案との比較

Octave調査は別担当。ここでその互換動作や導入容量を確定しない。

- Octaveが著者コードを少ない互換修正で動かせるなら、独自移植差分が小さく、元計画との連続性は強い。fast recursionを維持できる。
- 直接射影案はMATLAB class仕様・toolbox・fast recursion移植から独立でき、Jとpriorの関係が読みやすい。新規に必要な推定ロジックが限定される。
- 代償はPython translation、GramとFFTの数値差、初期化・silent-state・配列向き・正規化の再実装リスク。MATLAB reference runtime不在では数式監査以上の同一性証拠がない。
- いずれも同じlogBF近似・prior・時間更新を維持する限り、自然音声へのcalibration不明、低F0の25 ms識別力、モデル不適合は改善しない。
- 選択の順序は「Octaveの具体的導入/互換障害」と「直接射影への明示的変更許容」を比較すること。二方式を両方5入力で走らせる計画ではない。

## 7. 5つの仮想役割による2ラウンド検討

以下は本設計内で視点を分けた机上討議。独立した5人/5agentが実験・査読したという意味ではない。

### Round 1

1. 数理担当: Jはbasis-invariantな射影なのでfast recursionは確率モデルの必須要件でない。centered cos/sin二ブロックで十分。
2. 数値担当: inverse前計算よりCholesky。rを盲目的に[0,1]へclampすると誤った高confidenceを作る。
3. 計算担当: 全K別solveは不要。最大次数Lのleading principal factorが使え、累積二乗で全Kを得られる。
4. 推論来歴担当: varSpeechはGram ridgeではない。H0、R、無音skip、全録音scaleを移植時に落とすと別モデルになる。
5. 批判担当: 見た目が同じheatmapでも著者再現とはいえない。runtimeがないからと無断で書き直すことは元計画と矛盾。GPLを「数学だけだからBSD」に置き換えるのも不適切。

### Round 2

1. 数理担当→批判: 名称を「固定格子直接射影＋著者式posterior」に限定。同値性は厳密算術のJまで、浮動小数点や全wrapper再現は未確認とする。
2. 数値担当→計算: Cholesky prefix案を採るが、rank落ち時のpinv救済は採らない。正根の安定評価は式を記録する。失敗時は欠測/停止であってH0へ押し込まない。
3. 計算担当→数値: 因子は約0.74 MB、追加計算はfilterより小さい。RAM/出力上限を守るchunk設計で十分見込みはあるが、実測秒数は約束しない。
4. 推論来歴担当→数理: 元wrapperの末尾frame規則と計画のpadding差を明示。silent stale-state、local/base、filtered、log-Hz感度の区分を固定する。
5. 批判担当→全員: 条件付きfallbackとして認める。承認済み一設定の診断以外を増やさず、元コード一致・音質改善・校正済み確率を主張しない。実装着手はこの報告に含めない。

合意: credibleな一案として残す。Octave案の阻害要因を確認したうえで一経路を選び、追加tracker実験やquality gateを増やさない。

## 8. 出典とライセンス来歴

対象commitは ad9a3fcfe60d2e97a635a92c2076ff1978ae3697。今回fresh取得したhelperのblob SHAを記録する。

- computePitchLogLikelihood.m: 90ec7bf3297f5769a92aba72cc7ad279dba78d91
- computeAllCostFunctions.m: 01b1fac40045b984e589a3489945a26a43ea6779
- computeComplexHarmonicDfts.m: 04dc8537176f519b879f4e3adb3a94d2ffffb8fa
- BF0NLS.m: 856344e46b749bac85c87a803b9231c21e88dc34
- LICENSE: 8ee22d3a0dc718ffd47d1838dd534c6c4659857a

一次資料:

- [著者class](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m)
- [局所logBF](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/computePitchLogLikelihood.m)
- [NLS cost](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/computeAllCostFunctions.m)
- [harmonic FFT](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/computeComplexHarmonicDfts.m)
- [wrapper](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/BF0NLS.m)
- [GPL-2.0本文](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/LICENSE)
- [原著accepted manuscript、式(13)(14)(25)–(28)](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)

数学的導出とコード翻訳を分ける。Jを独自の一般的線形代数で書けても、著者のlogBF/filter等を参照して翻訳する本案を独立BSD実装と称さない。翻訳部分はGPL側の来歴、著作権・license・変更日・対象commitを保持する前提。基盤fastF0NlsのBSD由来部分を実際に再使用するならそのnoticeも保持する。NumPy/SciPyやBLASを含む実際の依存版・licenseは将来環境で記録し、この調査では未確認。法的な製品配布適合性の判断はしない。
