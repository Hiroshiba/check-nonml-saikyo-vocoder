# 着色noiseとF0を同時に扱う次段階の条件付きレビュー

2026-10-19 UTC。一次論文・著者コードの読取り調査。現在の固定5入力white posterior診断は変更しない。新しい推定実装、音声処理、テスト、install、Git変更は行っていない。

## 結論

次に検討する価値があるのは、**harmonic成分と低次数AR残差を同じ観測に対して競合させる生成モデル**。ただし、既成の高速joint MLコードを現在のBayes factorへ差し込むことではない。

- 学習済みモデルを要しない直接の実装参考はQuinn–Nielsen–Christensen (Signal Processing 180, 2021), Fast algorithms for fundamental frequency estimation in autoregressive noise。joint ML＋次数BICであり、校正されたF0/H0 posteriorを返す研究ではない。
- Esquivel Jaramilloら (ICASSP 2020) は反復的approximate ML/LCMV。掲載実験のnoise初期化には学習dictionaryを使うparametric NMFがある。反復法やAR一般が学習を必須とする、という意味ではない。
- 本当にBayesianな先行例はGodsill–Davy (ICASSP 2002) およびDavy–Godsill (2003) のharmonic＋AR residualモデル。prior、周辺化、variable-dimension MCMCを持つ。音楽向け・固定AR次数の例であり、25 ms音声用の即時置換実装ではない。

現結果を待つ理由は、現在の異常に見える集中がnoise色ではなくenergy regularizer、時間prior、支持端、K上限等でも起こるため。既存のlocal/予測prior/filtered、fit/cod/energyの分解を先に読む。そこでnoise色が原因と証明できるわけでもない。

## 1. 一次研究・公式コードの位置づけ

### A. 高速joint ML

[著者accepted manuscript](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/paper/acceptedManuscript.pdf) のモデルは、harmonicな決定論的平均＋AR残差。候補F0を固定すると、過去観測の列とsin/cos列を組み合わせた線形回帰になり、ARとharmonic係数を同時にprofileできる。Eはautocorrelation法のゼロ外挿・padding目的関数に対してexactであり、有限窓の厳密な定常Gaussian周辺尤度という意味のexactではない（§3、公式classの注意）。

論文Table 1の1 segment計算量。FはDFT長、Pは最大AR次数、Qは最大harmonic次数:

- E: O(F log₂ F)＋O(F P(P＋Q))
- A1: O(F log₂ F)＋O(F P²)
- A2: O(F log₂ F)＋O(F P Q)

近似2方式は有限長で分解能の代償がある。これは全候補次数の残差評価の計算量であり、Bayes積分・時間filter込みの予算ではない。現在のF=16384、K=10設定での実測時間やRAMを保証しない。[論文・公式案内](https://github.com/jkjaer/fastF0ArMl)

[公式LICENSE](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/LICENSE) はBSD-3-Clause（2020 Jesper Kjær Nielsen）。現在確認したtree SHAは27ec2ba9c56b1c862d4fb876c734d2240477a614。ライセンスが明瞭な参考実装だが、今回はコピー・導入・実行しない。

### B. 反復prewhitening

[ICASSP 2020 accepted manuscript](https://vbn.aau.dk/ws/portalfiles/portal/321346849/icassp2020AAJM_accepted.pdf) の二方式は、推定した周期成分を引いた残差からARを再推定し、再びprewhitenしてF0を更新する。LCMV版は推定harmonicを歪めない制約を使う。K=0なら全観測を残差とし、次もK=0ならそのsegmentの反復を停止する。これはposterior samplingではない。

同論文§3の実験は8 kHz、26.5 ms、AR次数25、NMF dictionaryによる初期noise PSDを使用する。**この設定を非学習の純粋なAR推定と表現しない。** [大学公式ページ](https://vbn.aau.dk/en/publications/robust-fundamental-frequency-estimation-in-coloured-noise/) が案内するコードは、現在[alfredoejtecmty/iterativeF0Ar_NLS](https://github.com/alfredoejtecmty/iterativeF0Ar_NLS)へredirectする。tree SHA f04dd905ba4127eb872bd42c608385da88ad5cb4の全pathにLICENSE/COPYINGは見つからず、READMEにも包括licenseを確認できなかった。公開されていることから再配布許諾を推測しない。

これと既存Shiコードのflag=1は別。固定著者classにはestnoiseg_orig→noise PSDのIFFT→Levinson次数30→filterという経路がある。2020 NMF学習dictionary経路をそのまま使うわけではない。現在のflag=0ではこの経路を通らない。[既存著者class](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m)

### C. Bayesianな先行例

2002 ICASSP先行研究は2021論文の文献[24]として特定した。さらに[2003論文本文](https://www-labs.iro.umontreal.ca/~pift6080/H08/documents/papers/davy_bayes_extraction.pdf) §2.3–3でAR residual、AR係数・分散等のprior、線形パラメータの周辺化、variable-dimension MCMCを確認した。[出版社の書誌](https://academic.oup.com/book/54032/chapter-abstract/422207997)と対応する。

AR次数は当時の実装で固定。harmonic数・F0等の不確実性を扱うためのモデルで、ML点推定を指数化したものではない。AR residualは外来雑音だけでなく息成分やモデル誤差も含む。公式の現行実行コードと利用licenseは今回確認できず、実装候補としての準備完了とはしない。

## 2. bayesFactorという変数名を信用しない

以下は[標準estimateModelOrders](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/estimateModelOrders.m) と[実際に呼ぶBIC helper](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/pitchArBicModelComparison.m)の読取りからの解釈。

- 各(p,K)でF0方向の残差分散を最小化する。
- log weight = −N log(σ̂²)/2 − (K＋p/2) log N。
- expして全(p,K)で総和1にし、その最大値を採る。

従ってこのbayesFactorはBIC由来の**次数重み**。F0全候補の周辺posteriorでも、noise-onlyに対する厳密BFでもない。元論文はharmonic周波数推定の特殊な漸近penaltyも論じるが、実際のhelperは上記式である。特にK=0比較で、K>0内でのみ共通な定数が勝手に相殺するとは考えない。

別の[pitchArModelComparison](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/pitchArModelComparison.m)はLaplace型式とF0のtrapz積分を含むが、標準callerではコメントアウトされている。これを有効化する提案はしない。ARの安定性prior、初期状態、F0密度の正規化、次数prior、データ由来のlagged design、K=0との尺度整合性を監査する前に「完成済みjoint Bayes」と扱えない。

## 3. 識別不能・交絡の整理

ここからは上記モデルに対する数学的・音声学的な推論であり、5入力についての実験結果ではない。

1. **ARがharmonicを吸う。** 単一正弦は2次の線形漸化式を満たす。高次数ARや単位円近傍のpoleは狭いスペクトル峰を説明しうる。有限短窓ではharmonic成分と確率的共振を区別しにくい。安定性、次数制約、priorは必要だが、選べば自動で真の声帯周期が判明するわけではない。
2. **vocal tractとnoise spectrumは別の対象。** 決定論的harmonic振幅にもformant包絡がある。混合観測全体からLPCを作ると、noiseだけでなく声道由来の包絡や周期性を学ぶ場合がある。固定LTI whiteningは定常sinusoidの周波数を通常変えないが、振幅・SNR・有限窓端・過渡を変える。dataとbasisの両方を同じoperatorで扱い、消した成分を雑音と決めつけない。
3. **残差の二重利用。** 同じ観測でF0を選び、その残差でARを選び、選んだARを既知として同じ観測からposteriorを出すと、AR選択の不確実性を無視する。反復ML自体が不正という意味ではない。joint likelihoodにおけるprofile推定としては可能だが、それを独立な追加証拠として掛け合わせない。
4. **無声・破裂・雑音イベント。** 着色Gaussian H0は摩擦音等の一部をwhite H0より表現しやすい可能性がある。しかし破裂の立上りや振幅の非定常性、impulsive noise、混合話者はstationary ARでも不適合となる。K=0は生理的無声ラベルではない。AR導入でH0が増えても改善率とは呼ばない。
5. **短窓の構造的限界。** 25 msで50 Hzは1.25周期。AR追加は失われた周期数を作れない。H0/弱いharmonic/低周波noise間の競合が増えることもある。曖昧さを正しく残すこととposteriorを尖らせることを分ける。

## 4. posterior evidenceの正規化を保持する設計条件

Gaussian residual covarianceをΣθとするなら、元観測の尤度には少なくとも

log p(x|f,K,θ,β) = −N log(2π)/2 − log|Σθ|/2 − (x−Zβ)ᵀΣθ⁻¹(x−Zβ)/2

がある。whitened RSSだけを比較してlog determinant・初期状態の扱いを落とさない。conditional ARとstationary ARのどちらを選ぶか、切捨てsampleとpadding、innovation分散をどこで積分するかまで固定する。異なる候補ごとのwhitening後energyを自由に再正規化すると共通観測のevidenceでなくなる。

本当にBayesで進めるなら、H0にもARを認め、H1にも同じ定義・支持・priorを置く。概念上はm0(x)=Σp π(p|H0)∫p(x|θp,H0)π(θp|H0)dθp、m1(x|f,K)=Σp π(p|H1)∫p(x|f,K,β,θp)π(β,θp|f,K,H1)dβdθp。F0とKのpriorを掛け、H0と**一緒に**正規化する。候補gridのセル幅とHz/log-Hzのmeasureも明示する。

p=0を含めればwhiteへの包含は作れるが、現在のregularized cod＋Laplace式と数値的に同一になるとは限らない。prior、scale regularization、観測支持まで一致が必要。profile exp(−cost)、BIC重み、conditional empirical-Bayes近似は、それぞれその名で報告する。いずれも自然音声でのcalibrationを保証しない。

## 5. 現結果を受けて進む場合の具体的な次の一手

**今は実装せず、次の生成モデル仕様を1つだけ決める段階に留める。**

- 現診断でprior odds/energy/cod/K・F0支持の説明が主なら、先にその解釈を完了。noiseモデル変更を解決策として決め打ちしない。
- それらでは説明しきれないlocalのH0/harmonic競合があり、着色残差が合理的な仮説として残る場合に限り、同じ観測支持上の「harmonic＋低次数stable AR」と「AR-only」を対等に比較する仕様を作る。
- 仕様で先に決めるもの: AR次数の固定/周辺化、安定性prior、有限窓初期状態、harmonic振幅prior、noise分散prior、evidence計算法、p=0との整合性、数値失敗と欠測の扱い。AR次数値や新しいthresholdを今は発明しない。
- 参考はjoint MLの線形代数と真のBayesian文献のprior/積分構造。新tracker、NMF導入、反復prewhiteningの並走、MCMC全面移植を同時に始めない。
- 保存済みwhite posteriorだけでは残差の色を測れない場合は、その限界を報告。新しいresidual評価を実施したことにしない。必要な追加観測・計算は次段階の明示スコープにする。

到達目標は「noise色の仮説を、H0を保った比較可能なモデルとして定義できるか」。F0正解率、無声音判定、aperiodicityや合成品質の改善は別の検証対象。

## 6. 5つの仮想役割、2ラウンド

独立5人の実験・査読ではなく、本仮説の机上検討である。

### Round 1
1. 数理担当: 同じframeのF0とARをjointに扱えば残差fitの循環依存をモデルとして書ける。
2. 音声担当: ARは外来noise、息、声道包絡、未モデル化harmonicsを混同しうる。
3. 推論担当: nuisance最大化を周辺化と呼ばず、H0側のARも必要。
4. 計算担当: fast exact目的関数は参考になるが、posterior計算量は表のML計算量では見積もれない。
5. 批判担当: 結果未見で「着色noiseが原因」と決めるのは早い。高次数ARは正しいpitchまで消しうる。

### Round 2
1. 数理担当→批判: 原因の断定を撤回し、既存診断の分解で残った仮説にのみ適用する。
2. 音声担当→推論: H0に生理的意味を付けず、破裂・摩擦・低energyを区別して説明する。
3. 推論担当→数理: stable AR prior、初期状態、log determinantまで仕様化できなければBayes案を止める。
4. 計算担当→全員: 公式コードのBSDと実行可能性を混同しない。無license反復codeや未検証Bayes helperを即採用しない。
5. 批判担当→全員: posteriorが広がる結果も成功しうる。「峰が鋭い」「H0が増えた」を採用gateにしない。今回は調査で終了し固定white結果を待つ。
