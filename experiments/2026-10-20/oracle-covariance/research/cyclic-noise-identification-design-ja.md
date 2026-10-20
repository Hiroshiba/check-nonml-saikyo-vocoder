# 周期同期雑音・着色雑音・周期摂動の識別：固定最小設計

作成日：2026-10-20。対象：Hiroshiba/check-nonml-saikyo-vocoder。これは研究仕様であり、実装、音声生成、試聴、新規 tests/smoke、GitHub 変更、実験実行を行っていない。PML を唯一の base とする。別作業の確率的 F0/H0 履歴問題・log 算術による原因分離は扱わない。

## 0. 結論と採否

一つに絞る候補は「既知の平均周期波形に、AR(1) innovation の位相依存分散と、周期ごとの振幅・時刻接線ランダム効果を加える有限窓 Gaussian モデル」である。これは複数の無関係な noise 実装の比較ではなく、共通生成モデルの制約部分モデル比較である。

ただし、現段階で vocoder へ組み込まない。まず oracle 共分散の構造識別を解析する（第8節に実施済みの判断を追記）。PML の位相出力契約が未確定でも、この oracle 理論は止めず、estimated-phase 側だけを未対応として切り分ける。提案する人工実験は次段階の予算案であり、今回は実行しない。oracle 条件で原因を区別できることと、自然音声から生理的 aspiration を同定できることは別問題である。後者への採用根拠にはしない。

## 1. 一次資料が示す範囲

- Gardner (1986), “The spectral correlation theory of cyclostationary time-series”: 周期変調・周期時変フィルタと spectral correlation の理論。周期統計を検出する枠組みであり、声門の生理的原因を決める理論ではない。[出版社](https://www.sciencedirect.com/science/article/pii/0165168486900927)、[著者所属大学公開本文](https://faculty.engineering.ucdavis.edu/gardner/wp-content/uploads/sites/146/2013/02/The_Spectral_Correlation_Theory_of_Cyclostationary_Time-Series.pdf)。
- Gobl (2006), “Modelling aspiration noise during phonation using the LF voice source model”: LF 波形の形状から aspiration noise の全体強度・パルス内変調を制御する生成法を提案する。提示される自然さの証拠は informal listening tests。未知単一波形における aspiration・jitter の識別保証ではない。[ISCA の著者・抄録](https://www.isca-archive.org/interspeech_2006/gobl06_interspeech.html)。本文 PDF は今回の取得では利用不可だったため、細部の式を検証済みと扱わない。
- Ghosh and Narayanan (2011), “Joint source-filter optimization for robust glottal source estimation in the presence of shimmer and jitter”: LF source と AR vocal-tract filter、周期ごとの振幅等を共同推定する方法。source/filter の役割を明示する参考であって、本設計の covariance 分解の一意性の証明ではない。[出版社 DOI](https://doi.org/10.1016/j.specom.2010.07.004)。公開抄録・導入・式抜粋を確認した。
- Quinn, Nielsen and Christensen (2021), “Fast algorithms for fundamental frequency estimation in autoregressive noise”: harmonic regression と AR noise の joint ML、次数には BIC 型手順。posterior の計算ではない。[出版社](https://www.sciencedirect.com/science/article/pii/S0165168420304047)、[著者大学記録](https://researchers.mq.edu.au/en/publications/fast-algorithms-for-fundamental-frequency-estimation-in-autoregre/)、[著者コード](https://github.com/jkjaer/fastF0ArMl/blob/master/README.md)。既存 noise 実装を採用する根拠として引用しない。
- Kreiman and Gerratt (2003), “Jitter, shimmer, and noise in pathological voice quality perception”: その課題・刺激群で spectrally-shaped additive noise が重要だったという知覚実験。知覚上の重要性と原因推定精度は違う。[ISCA 本文](https://www.isca-archive.org/voqual_2003/kreiman03_voqual.pdf)。本研究では聴取評価をしない。

以下のモデル、設計値、識別基準は本提案の推論であり、上記論文の既報結果ではない。

## 2. 観測と位相を固定する

初段は声門流／音圧の生理的解釈を捨てた source-domain 数列とし、声道・放射・マイクの伝達を H=I に固定する。サンプル数 L=64/周期、K=64 周期、N=4096 とする。物理時間に換算するなら fs=16 kHz、F0=250 Hz。周波数、母音、SNR、フィルタ、窓長の sweep はしない。

位相 φ_n=2πn/L、周期番号 k=floor(n/L)、位相内 u=(n mod L)/L。位相の原点は平均波形の定義で固定する。oracle phase は「摂動前の共通 clock」であって、摂動した各パルスの時刻に追従して residual を消す clock ではない。

一つの平均テンプレートを q(u)=c sin^4(πu)[1+0.3 cos(2πu)] (0≤u≤1) とする。c は L 点で mean(q²)=1 とする定数。端点で q と q′ がゼロの滑らかなパルスであり、LF や真の声門流を再現したとは主張しない。q′ は u に関する解析微分。g=q、h=-q′/sqrt(mean(q′²)) を同じ L 点で評価し、両者の二乗平均を1にする。記号 h は接線であり、声道フィルタ H と別物である。連続周期積分では ∫qq′du=0。離散内積は実際に確認し、勝手に直交と仮定しない。

平均 m_n=q(u_n) は既知、全モデル共通、同じ実現から再推定しない。これは未知平均波形の吸収問題を除いた best-case 識別試験であり、実音声への適用条件ではない。平均を test record から推定・除去してしまうと covariance が射影されるので禁止する。

## 3. 採用候補となる単一モデル

観測は次とする。

  y_n = m_n + r_n + g(u_n) s_k + h(u_n) j_k
  r_n = a r_(n-1) + sqrt(v_n) ε_n
  v_n = σ² exp[b_c cos(φ_n)+b_s sin(φ_n)] / Z(b)
  Z(b) = L^(-1) Σ_(l=0)^(L-1) exp[b_c cos(2πl/L)+b_s sin(2πl/L)]

ε_n は独立 N(0,1)。s_k~N(0,τ_s²)、j_k~N(0,τ_j²) は周期間、互いに、r と独立とする。b は全周期で共有。a、σ²、τ_s²、τ_j² も record 内で共有する。周期ごとに分散関数・AR・平均形状を自由にしない。

AR は1次だけ。|a|≤0.8、||b||≤1.5、σ²>0、τ_s²,τ_j²≥0。AR の符号をデータ都合で限定しない。有限の数値探索範囲・σ²下限が必要になった場合、全モデル共通で事前固定し、その境界に解が到達したら適合失敗として報告する。結果を見て探索範囲を拡張して成功扱いしない。

重要な順序：位相変調は AR の innovation にかかる。D^(1/2)A^(-1)ε と A^(-1)D^(1/2)ε は同じではない。本仕様は後者であり、「着色した雑音を後から振幅変調する」別モデルへ暗黙に変更しない。

### 接線モデルと真の jitter の違い

(1+s_k)q(u-δ_k) ≈ q(u)+s_kq(u)-δ_kq′(u)。この一次展開から rank≤2 の周期内 covariance が現れる。h の正規化から δ_k=j_k/sqrt(mean(q′²)) である。

本 Gaussian 仕様で j は「局所的パルス時刻接線摂動」。独立な周期長 jitter そのものではない。絶対パルス位置が kL+Lδ_k なら周期長偏差は L(δ_(k+1)-δ_k) となり、隣接周期間に負の相関を持つ。独立な周期長誤差を累積した phase random walk と同一視しない。また時刻ずれによる support の移動、二次項、sδ の積は一次モデル外である。

物理的 jitter という名称で将来評価するには、正確な非線形 pulse timing 生成規則を別途固定し、同じ δ の定義、境界パルス、二次項の平均シフトを確認する必要がある。二次 Taylor remainder は少なくとも 0.5 δ² sup|q″| による上界、交差項は |sδ| sup|q′| で事前評価する。Gaussian は非有界なので「全実現で微小」とは主張せず、例えば事前固定した99.9%範囲と尾確率を併記する。これが許容誤差を超えるなら、接線試験の成功を物理モデル成功へ昇格しない。

## 4. 有限窓・初期状態・尤度

AR を各周期で reset しない。初期 r_(-1) は無限過去から同じ周期分散で駆動された周期定常分布から marginalize する。

  P_(-1) = [Σ_(i=0)^(L-1) a^(2i) v_(-1-i)] / [1-a^(2L)]

v の添字は周期延長する。r_(-1)~N(0,P_(-1))。P_n=a²P_(n-1)+v_n なので Cov(r_n,r_m)=a^(n-m)P_m (n≥m)。これで有限 N×N 共分散 K_r が決まる。有限窓の最初のサンプルから同じ定義を使い、真の初期値を推定器だけに与えたり、最初の p 点を候補ごとに落としたりしない。

U_s、U_j は各周期の g、h を対応する列へ入れる N×K のブロック行列。

  Σ = K_r + τ_s² U_s U_sᵀ + τ_j² U_j U_jᵀ
  -2 log p(y|θ,φ,q) = N log(2π) + log det Σ + (y-m)ᵀΣ^(-1)(y-m)

s,j は latent な実現を最適化して取り除くのではなく積分する。周期ごとの係数を自由な fixed effects として fitting して residual energy だけで比較すると、本比較ではなくなる。σ²、分散包絡、a の推定に log det Σ は不可欠。

U=[U_s,U_j]、G=diag(τ_s²I,τ_j²I) と置くと、境界 τ=0 でも使える形は

  log det Σ = log det K_r + log det[I+G^(1/2) UᵀK_r^(-1)U G^(1/2)]。

初期状態を積分した K_r について log det K_r=log P_0+Σ_(n=1)^(N-1)log v_n。P_0=a²P_(-1)+v_0。単に Σ log v_n を使う式は初期値条件付きの別尤度である。full Σ の determinant にこの式だけを使って low-rank 項を忘れない。

H≠I を将来導入する場合、known invertible finite H なら Σ_y=HΣHᵀ、det の増分2log|det H|。未知 H、窓外状態、切断 convolution、観測雑音があればこの簡略化をそのまま使えない。周期循環 convolution とゼロ初期 causal convolution も交換しない。今回はこれらを追加しない。

## 5. 比較する5つの制約部分モデル

全て同じ Gaussian 尤度、q、N、位相、initial law を用いる。

- W：a=0、b=0、τ_s=τ_j=0。自由度は σ² の1個。
- A：b=0、τ_s=τ_j=0。a、σ² の2個。
- V：a=0、τ_s=τ_j=0。b_c、b_s、σ² の3個。
- S：a=0、b=0、τ_j=0。σ²、τ_s² の2個。
- J：a=0、b=0、τ_s=0。σ²、τ_j² の2個。

全部入り F（6個：a,σ²,b_c,b_s,τ_s²,τ_j²）は予測勝者の候補に追加しない。識別の ridge や境界を調べる数学上の包絡モデルである。正則性が破れる τ=0 境界があるため、通常の χ² 尤度比検定を無批判に使わない。自由度を無理に揃える代わりに、同じ train/test と proper held-out log density で汎化比較する。BIC の勝利を posterior probability と呼ばない。

## 6. 最小人工設計：5原因、1水準、同一実現の2読出し

residual の期待平均二乗を全て E=10^(-3) とする。これは signal RMS=1 に対して -30 dB の数理検査水準で、聴覚上の適切さの主張ではない。

1. W truth：σ²=E。
2. A truth：a=0.6、σ²=E(1-a²)。周期定常 marginal variance は E。
3. V truth：b_c=0.8、b_s=0、σ²=E。平均 innovation variance は E。
4. S truth：σ²=E/2、τ_s²=E/2。
5. J truth：σ²=E/2、τ_j²=E/2。

その他の成分はゼロ。g,h の二乗平均が1なので全条件の期待 residual energy が一致する。実現ごとの energy 再正規化は禁止。再正規化は生成分布を変える。

これは原因数5であって、AR次数×変調深度×jitter×SNR の12cell以上の sweep ではない。混合原因を発見したとは言えない。単独原因を区別できないなら混合条件の大規模探索に進まない。

将来計算する場合の反復単位は独立な train/test record pair とする。各 record は64周期、初期状態・innovation・周期効果は独立に引き、全候補へ同じ pair を入力する。R=100 pairs/原因は次段階の予算候補に留め、現在の固定実行計画ではない。最初に100 pairs×5原因×5適合を開始しない。先に第8節の構造識別判断を行い、有限標本で知りたい効果差・区間精度と計算費用から実施規模を別途決める。モデル間差の区間が広い場合は「結論不足」と報告し、その場で反復を増やして有意化しない。frameや個々のサンプルを独立反復として数えない。周期も AR が跨ぐので、record bootstrap を基本とする。

初段から q の形状、F0、E の複数水準を追加しない。成功の外挿範囲はこの一つの設定に限定される。

## 7. oracle と estimated phase を混ぜない

同じ train/test pair について次の二読出しだけを作る。データ生成の追加cellではない。

O：oracle 共通clock、既知 q で fitting / test scoring。
E：train record だけから PML を使って共通clock（F0、位相原点）を得る。その clock を test 時刻へ外挿し、test 波形を見ず固定する。推定された clock で平均・covariance を構成して、元の test サンプル座標上で log density を計算する。oracle と同じ q shape を使う。

このEは「独立 calibration 後の位相誤差伝播」であって、通常の online phase tracker 全体の再現ではない。時刻原点、F0単位、補間、window offset、phase unwrap を確認するまでEは実行できない。PML を新方式へ変更しない。

**PML契約の確認済み制約（親担当のmainソース確認、2026-10-20）：** PMLParametersは正の合成clock F0、FWCEP60、noise_maskを保存し、独立に測定されたphase原点を保存しない。無声区間にも補間F0があり、全未検出の場合は65 Hzを用いる。pml_synthesis.pyの103–111行はts=[0.0]から始め、ts_next=ts+1/interpF0で合成pulse時計を作る。pml_pdd.pyのpitchsyncもts0固定である。したがって合成pulse_timesは測定されたglottal phaseではない。Eに必要な独立phase原点校正は現時点で未定義であり、Eは未対応とする。これはoracle理論を止める理由ではない。F0を積分して0始点の時計を作るだけの比較は、測定phase推定器を評価したことにはならない。

出典：[PML README](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/vocoderbench/pml/README.md)、[合成時計のコード](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/vocoderbench/pml/pml_synthesis.py#L103-L111)。親確認時の対象file blob SHA：966ffa84578ad365a7062c04d70582976d64ac4a。mainリンクは可変なので、この確認時点の内容として扱う。

test 自身から推定した細かい phase に plug-in した density を、無条件 predictive likelihood と呼んではならない。特に per-cycle alignment は真の timing perturbation 自身を取り除き、J の検出を不当に不利にする。将来この self-alignment を調べる場合は、oracle residualを元座標で残す別の診断として扱い、変換の Jacobian・推定選択効果を無視した likelihood 比較には混ぜない。

E−O の paired 差と、既知真値に対する wrapped phase error、F0 error、test 内で蓄積した位相 drift を記録する。O で失敗なら原因モデル／観測情報の問題、O 成功・E 失敗なら位相校正問題、両者成功でも未知filterや生理的同定の証拠にはならない。

## 8. 何が何を否定するか

### 必須観測

(a) trainで fitting し、test 全 record の log density 差を記録する。候補間 paired 差を nats/cycle に換算、record単位95%区間を出す。最大値だけでなく5×5の原因・勝者表と差の区間を提示する。

(b) oracle residual を周期内位置へ整理し、二次統計を確認する。V は a=0 なら diagonal で位置依存、A は stationary lag covariance、S/J はそれぞれ ggᵀ/hhᵀ の off-diagonal rank1構造。variance 対 phase だけを見ると S のg²、Jのh²も周期分散なので V と混同する。off-diagonal covariance が必要。

(c) g,h 部分空間への射影 energy と直交補空間 energy、lag covarianceの位相依存、各モデルの予測 covariance との Frobenius discrepancy を記録する。有限sample covarianceのrankを生理的rankと解釈しない。標準化 residual の周期分散／相関が残るかを見る。

(d) fitting が外した原因のパラメータへ代償吸収されるかを、数学上の F の profile/ridge で調べる。ただし最初の大規模追加 fitting は要求しない。理論 covariance Jacobian の確認を先行させる。

### 識別可能性を実行前に調べる式

各パラメータの covariance 接線 Σ_i=∂Σ/∂θ_i を、σ²のscale方向を含めて比較する。Gaussian Fisher 行列は I_ij=0.5 tr(Σ^(-1)Σ_iΣ^(-1)Σ_j)。σ²など共通 nuisance の方向を除いた後に特異なら局所構造識別不能。境界では接錐として読み、通常の両側正則性を仮定しない。

正規化した whitened 接線間のcosineがほぼ1、最小固有値が小さい、または profileが平坦なら有限標本で弱識別。条件数だけの普遍的閾値を捏造せず、parameter scaling、演算精度、実験のlog-score差と併記する。

二候補の分布そのものの差には Gaussian KL を使う。

  KL(P||Q)=0.5[tr(Σ_Q^(-1)Σ_P)+(μ_Q−μ_P)ᵀΣ_Q^(-1)(μ_Q−μ_P)−N+log(detΣ_Q/detΣ_P)]。

相手モデルの自由パラメータで最小化した KL=0 ならその条件で observational equivalence。正なら理論的差はあるが64周期で回収できる保証ではない。単なる固定パラメータ間のKLが大きいだけでは、競合が最適化して近づく交絡を否定できない。

### 決定の語彙と停止条件

- 「構造識別不能」：異なる原因の同一分布を式で示した、または識別方向の正確な退化を示した場合。
- 「この予算では実用的に未分離」：oracle下で正しい単独原因対競合のheld-out score差の95%区間が0を跨ぎ、covariance signatureも安定に分離しない場合。単に非有意だから同一とは結論しない。
- 「実用上ほぼ同等」は現段階では判定しない。目的上意味のあるequivalence幅の根拠が未確定なので、score効果差と区間をそのまま報告する。恣意的なnats/cycle閾値や非有意差を同等性の根拠にしない。
- 「平均／位相の misspecification」：residual平均の位相依存、Eでのphase drift、同じg/h方向への系統的残差が出る場合。VやARで吸収できても雑音原因の証明ではない。
- 「限定された識別成立」：oracle下で各非null truthの正しい候補が全競合より正のscore差を持ち、方向別covarianceも一致する。W truthではWに対する過剰モデルの明確な優位がないことを確認する。Wと境界で一致する拡張モデルの同点は誤検出と扱わない。

多比較を通過した強い主張をする場合は、事前指定した全対比較に対応した同時区間またはHolm補正を使う。小さな未補正p値の個別列挙で採用を決めない。実行前に区間構成法まで固定する必要がある。

### 実行前に行った oracle 共分散の構造識別（解析のみ）

ここでは母共分散が分かる理想極限を扱う。有限recordから正確に推定できるとは仮定しない。H=I、既知q、L=64、K≥2、σ²>0、独立cycle effect、同じ位相gridが前提である。以下の「同値」は平均が同じときのGaussian観測分布の完全一致を指す。

**Aと他候補：周期境界をまたぐ相関が識別子になる。** AではP=σ²/(1−a²)>0で、境界の直前・直後の共分散はaP。a≠0なら非零。他のW,V,S,Jでは異なる周期間の共分散は厳密に0なので、これだけでAを区別できる。負のaでも非零であり結論は同じ。a=0になるとAはWに退化する。σ²=0まで許すならA成分そのものが消えるが、本仕様はこれを除く。K=1、境界を跨ぐ相関を捨てた統計、cycle resetするARではこの証明が使えない。|a|が微小なら理論上異なっても有限標本では弱識別になる。

**VとW：対角の位相変動。** Vは対角共分散diag(v_l)で、Wとの同値は全lでv_lが同じ場合に限る。64点gridの定数・cos・sinは線形独立で、指数は単調なので、本仕様ではb_c=b_s=0が必要十分。このときZ=1でWへ退化する。少なすぎる位相点、特定位相だけの観測、phase平均して対角を潰す観測では別のaliasが生じ得る。

**S/JとV：周期内off-diagonalが識別子になる。** Sの一周期blockはσ²I+τ_s²ggᵀ、Jはσ²I+τ_j²hhᵀ。τ>0かつ対応ベクトルに少なくとも2個の非零成分があれば、いずれかのoff-diagonalが非零で、どの対角Vとも同値ではない。本仕様のg,hはこの条件を満たす。τ=0ならWへ退化する。ベクトルが零ならその効果は不可観測。1点だけ非零ならrank1効果も対角になり、このoff-diagonal証明は失われる。その場合でも今回の一次Fourier log-variance Vと完全同値とは限らず、対角形状が実際にVの族に入るかを別途調べる必要がある。

**SとJ：異なる白色scaleを許しても、通常は同値にならない。** 同値の条件は

  (σ_S²−σ_J²)I = τ_j²hhᵀ−τ_s²ggᵀ。

右辺のrankは高々2。L=64>2なので左辺が非零のfull-rank行列になることはなく、σ_S²=σ_J²が必要。両効果が正でg,hが非零なら、さらにh=cgとτ_s²=c²τ_j²が必要十分。両τ=0ならWとして同値。一方だけτ=0で他方のベクトルが非零・τ>0なら同値ではない。L≤2や一部の投影だけを観測する場合にはこのrank証明を流用しない。

今回のqではu=1/2でg>0かつh=0、別の内部位相ではh≠0なのでgとhは比例しない。したがって正のS/Jは観測同値ではない。これは離散内積が厳密に0であることを要せず、ベクトルが非比例であることによる。variance対phaseだけを観測する場合はggᵀとhhᵀの符号・off-diagonal情報を失うので、完全波形の結論をその統計へ自動的に移せない。

**σ²scaleの交絡。** S/Jではrank1摂動に直交するL−1方向の固有値がσ²であり、全blockを観測する理想条件ならσ²とτ²は分かれる。一方、平均residual energyしか測らないなら、g,hの二乗平均が1なのでσ²+τ_s²+τ_j²しか分からず、完全に交絡する。g/h方向だけに投影した観測でもwhiteとcycle効果の分離情報を失う。qのscaleを未知にするとq→cq、τ_s²→τ_s²/c²等の再パラメータ化が生じるため、既知q・単位RMS規約が必要である。

VではZを用いたmean(v)=σ²という規約がglobal scaleを固定する。もしlog vに自由な定数項と別のσ²を重ねれば、それらは完全交絡する。今回のb_c,b_sには定数項がない。Aで対角varianceだけを見ればσ²/(1−a²)しか分からないが、lag共分散を含めればa=Cov(r_n,r_(n−1))/Pからaとinnovation σ²を分離できる。

**全部入りFについても、この人工gridでの識別情報は消えていない。** a≠0なら、cycle効果がゼロとなる異周期間の共分散だけから、固定mと別周期に属する連続n,n+1についてCov(y_(n+1),y_m)/Cov(y_n,y_m)=aを得る。続いてCov(y_n,y_m)/a^(n−m)=P_mを得て、同じ周期位相を繰り返し観測することとP_l=a²P_(l−1)+v_lからv_lを復元できる。periodic initial lawがここで必要になる。vからmean(v)=σ²、log vのcos/sin係数からbが得られる。K_rを引いたblockはτ_s²ggᵀ+τ_j²hhᵀとなる。

a=0なら異周期間相関は全て0となる。今回のgridにはmidpointが含まれ、h_mid=0、g_mid>0なので、midpointと他の非零g位相のoff-diagonalからτ_s²を直接得る。次いでhが非零な2点のoff-diagonalからτ_j²を得る。両rank1項を引いた対角がvであり、σ²とbを復元できる。これらは理想的な母共分散の代数的識別で、sample covarianceの不安定な割算を推奨する推定アルゴリズムではない。

**数学上の判断。** 指定した人工条件では、5つの単独原因はWへ退化する境界を除いて構造識別可能。したがって「そもそも同じ共分散なのにcause分類を要求している」という欠陥は、この限定設定ではない。反対に、この証明は有限64周期での検出力、未知q/filter、一般的period jitter、aspirationの生理的同定を保証しない。最初の数学判断はここまでで完了し、PML phaseの有無に依存しない。次に必要なのは有限標本で得たい精度・計算予算の判断であり、固定100pair計算を自動的に開始することではない。

## 9. 残る交絡と本設計が否定できないこと

1. 未知filter：観測の色はsource雑音と声道filterの双方で生じる。Hとsource covarianceの再配分が可能で、単一waveformのみから一般には一意でない。H=Iでの成功はこの問題を解いていない。
2. 未知q：harmonic不足、位相ずれ、周期形状変化はAR、分散包絡、接線効果へ吸収され得る。既知q試験はその交絡を意図的に遮断する。
3. サンプル数と位相平滑化：cycle平均・resampling・windowingにより新たな相関が生じる。初段では生の固定grid、矩形有限窓だけ。
4. V の限界：一次のcos/sin log-varianceに限定するので、任意の周期分散の否定にはならない。S/Jの対角だけを近似できてもoff-diagonalが違う、という反証を使う。
5. J の限界：局所time-shift tangentと独立period jitterは別。F0ランダムウォークや周期長相関を後から同じ仕様に読み替えない。
6. Gaussian 限界：共分散が同じならこの尤度では原因を分けられない。非Gaussian高次統計で分離できる可能性は本試験の範囲外。
7. 生理学：phase varianceだけで「aspiration」「turbulence」を同定しない。将来の生理的主張には独立なflow/EGG等の観測とmeasurement model、または独立操作による介入が必要で、何でもEGGを足せば解決するわけではない。

## 10. 仮想5役による2往復の設計批評

以下は一人の設計者が5つの観点を用いた仮想レビューであり、実際に5名の専門家が審査した記録ではない。

### 第1往復：提案 → 指摘 → 修正

- 生成モデル担当：「AR、位相分散、jitter/shimmerを一つの共分散モデルに含める」。批評家：「jitterをq′と置くだけではperiod jitterとは違う」。修正：timing tangentと命名し、絶対時刻offsetと周期長差の関係、Taylor remainderを明記。
- 統計担当：「候補のresidual energyを比較する」。批評家：「分散の増加とlatent係数の自由化に常に有利」。修正：latent効果を積分し、log determinantを含むheld-out densityに限定。
- 音声物理担当：「LF由来の位相包絡ならaspiration」。批評家：「生理的原因の逆同定にはならない」。修正：人工q、source-domain H=Iとし、意味はcovariance classに限定。
- 位相担当：「各周期を推定位相にalignする」。批評家：「真のJ成分まで消える」。修正：oracleを摂動前clockとし、推定位相は独立trainからtestへ凍結。
- 批評家自身：「12cell sweepで一般化を確認しよう」。他4役：「まず単独原因の最小反証で十分。識別限界をsweepで隠さない」。修正：5原因×1水準、共通実現2読出し。

### 第2往復：反例 → 再修正 → 残る棄却条件

- 生成モデル担当：「AR初期値0で容易に比較できる」。統計・批評家：「初期transientが周期包絡に見える」。再修正：周期定常初期分布を積分し、周期reset禁止。棄却条件：initial law不一致。
- 統計担当：「Oで候補が勝てば識別成功」。批評家：「競合を最適化したKLが0なら勝率は偶然」。再修正：接線Fisher・最小KLを先行。棄却条件：共分散同値、ridge、境界依存。
- 音声物理担当：「unknown vocal tractも同時推定すれば現実的」。他役：「source noiseの色とfilterが再配分される」。再修正：初段ではH=I。棄却条件：source-domainの結果をそのまま実音声へ外挿すること。
- 位相担当：「testからPML phaseを得た方が通常使用に近い」。統計・批評家：「同一data適合のplug-in scoreはpredictive密度ではない」。再修正：独立calibration限定とし、通常online推定は別課題として明記。棄却条件：PML phase契約未定、test漏洩。
- 批評家：「全部入りFの適合でcause posteriorを出そう」。他4役：「joint MLはposteriorではなく、variance成分境界と単一設定の弱識別が残る」。再修正：Fは数学的診断だけ、原因のposterior表現禁止。棄却条件：自然さ、aspiration、実装採用への飛躍。

## 11. 次に必要なものと今回の停止点

今すぐ必要なのは新しい音声やsmoke、あるいはユーザーへの新たな許可依頼ではなく、研究責任者による次の段階判断である。

1. 第8節の解析では、oracle・既知q・H=Iの5原因は退化境界を除いて構造識別可能と判断した。この数学判断は完了しており、phase実装を待たない。
2. timing tangentを対象とし、独立period jitterは未検証とする。物理的jitterへの拡張前に非線形誤差と境界規則を確認する。
3. PMLを変更せず取り出せるF0・位相原点の定義と、独立train→test clock外挿の契約を確認する。未対応ならEだけ保留し、oracle研究まで停止しない。
4. 有限窓・初期状態・log determinantの仕様に従い、有限標本で知りたい効果差と区間精度を定義する。根拠のない同等性幅は置かず、100pairは予算候補として再検討する。
5. 進行中の3入力・完全log算術による履歴原因分離を妨げず、既存研究との重複を照合する。本資料は次の物理モデル設計として保持し、別研究の途中で新しい全計算を開始しない。

noise機能の統合判断は、この構造識別の成功とは分ける。将来の計算から最初に許される結論は「固定された人工source-domainで、指定された二次統計の原因クラスが有限標本でどこまで分かれるか」だけである。PML baseの置換、既存noise採用、F0/H0履歴問題の再調査、HITLへの自動移行は本計画に含めない。

## 12. 最終解析：大規模Monte Carloの前に分布間の難易度を調べる

以下は実験・計測・コード実行なしの代数チェックである。親レビューで提示された式を独立に導出し直した。数値は式の評価値として記載するもので、実験で得た推定値ではない。

### rank1原因対最良whiteのKL

一周期のtruthをΣ_g=E[(1−α)I+αggᵀ]、||g||²=L、0≤α<1とする。平均は既知かつ共通。これは平均residual variance Eのうちαを周期rank1効果へ配分したモデルである。候補whiteはwI。

Gaussian KLをwで最小化するとw=tr(Σ_g)/L=E。Σ_g/Eの固有値は、g方向に1−α+αL、直交するL−1方向に1−αなので、trace項が相殺して

  min_w KL[N(m,Σ_g)||N(m,wI)]
  = −0.5 log det(Σ_g/E)
  = 0.5[−(L−1)log(1−α)−log(1−α+αL)]。

親提示の式は正しい。L=64、α=0.5では20.09351614297043 nats/cycle。S/J truthの独立な64周期については1285.9850331501075 nats/recordとなる。独立blockなのでKLが加算できるが、同じ加算則をARの相関recordへ無条件に転用しない。

ここでEは消える。既知平均を正確に除いたoracle問題では、信号に対するresidualの−30 dBという小ささは、この分布間の識別困難性を意味しない。今回α=0.5では最大固有値が32.5E、残りが0.5Eであり、whiteの全方向Eとはかなり異なる。したがってS/J単独原因は非常に容易なbest-caseとなる可能性があり、最初から大量反復する意義を吟味する必要がある。

### S対J：直交を仮定しない固定parameter KL

比較するΣ_h=E[(1−α)I+αhhᵀ]も||h||²=Lとし、d=gᵀh、ρ=d/L、c=1−αと置く。両行列は同じ固有値、同じdeterminantを持つ。Sherman–Morrison公式から

  (Σ_h/E)^(-1)=c^(-1)I−α hhᵀ/[c(c+αL)]。

したがって

  KL[N(m,Σ_g)||N(m,Σ_h)]
  = α²(L²−d²)/[2(1−α)(1−α+αL)]
  = α²L²(1−ρ²)/[2(1−α)(1−α+αL)]。

α=0.5なら(L²−d²)/[2(L+1)]。直交d=0、L=64なら31.50769230769231 nats/cycleで、親提示値は正しい。|ρ|=1なら同じrank1方向なのでKL=0。これは同一E、同一αの固定parameter比較であり、競合Jを最適化した後の距離ではない。

今回のqはq(1−u)=q(u)、q′(1−u)=−q′(u)を満たす。64点gridでlと64−lの内積項は相殺し、l=0ではg=h=0、l=32ではh=0。よって解析的な実数演算ではd=0と示せる。これは単に連続積分の直交性を離散gridへ仮定したものではない。将来の数値計算では丸め誤差があり得るが、今回は計測していない。異なるq、grid、window、filterにこの直交性を一般化しない。

### 競合Jのscaleとrank1強度を自由にした場合

固定parameter KLの過大解釈を避けるため、候補をΣ_J=βI+γhhᵀ、β>0、γ≥0として最適化する場合も解析する。h方向とその直交補空間へのtruthの平均分散はそれぞれ

  t_parallel=E[c+αLρ²]、
  t_perp=E[c+αL(1−ρ²)/(L−1)]。

候補の対応固有値はλ_parallel=β+γL≥β=λ_perp。制約なしの最適値はλ_parallel=t_parallel、λ_perp=t_perp。ρ²≥1/Lなら制約を満たす。ρ²<1/Lではtruthの分散はh方向の方が小さく、非負rank1追加では再現できないため、最適解はγ=0、β=E、つまりwhiteになる。α=0の場合は全てwhiteであり区別しない。

特に今回の直交条件では、最適化後のJに対するKLは31.5077ではなく、whiteに対する20.0935 nats/cycleと等しい。親の固定parameter式は誤りではないが、最適化後の競合との差として使うと過大になる。

一般にρ²≥1/Lの場合の最適KLは

  0.5[(L−1)log(t_perp)+log(t_parallel)−log det(Σ_g)]。

最適点でtrace項がLになり、これが残る。ρ²<1/Lの場合は先述のwhite KL。これは平均既知、h方向固定、βとγに追加上限のない場合の解析である。trainから有限標本推定したモデルのtest性能・信頼区間を直接保証するものではない。

### 次段階の判断

最初に行うべきなのは、このような解析的な最良競合距離・退化条件・有効方向の確認であり、100pair×5原因×5適合の開始ではない。今回のS/J水準は少なくともwhite/Jまたはwhite/Sとの比較で大きなoracle KLを持つため、大規模Monte Carloで「分離できた」ことだけを再確認しても限定的な価値しかない。他候補A/Vに対する最適化後の距離や、実際に知りたい有限標本精度については、この値だけから結論しない。

この数値を見て、結果を面白くする目的でαを都合よく変更しない。α=0.5は元のbest-case仕様として保持する。別の難易度を研究する必要が生じた場合は、先にその科学的目的、比較対象、必要精度を明記した別設計として扱い、元設計の事後調整を隠さない。数値の成功・失敗に応じた同等性幅の設定や反復数の増量も行わない。
