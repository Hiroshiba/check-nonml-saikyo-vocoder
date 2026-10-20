# oracle位相を外す前の最小コントロール：共通clock誤差と独立周期摂動

作成日：2026-10-20。対象：Hiroshiba/check-nonml-saikyo-vocoder。

## 0. 判断と今回の範囲

**今回は解析だけを完了させ、進行中のoracle研究へ条件を追加しない。** 親からの最新状況ではCloud Aが固定5 truth ×100独立train/test pairsを実行中である。原設計内の「100 pairsは未確定」という過去の記述は、この最新実行状況を覆さない。本資料は成績・勝者・計測完了を予想または認定しない。

将来実施するとして候補は一つだけ：**既知人工q・既知一定周波数を維持し、共通位相原点だけをtrainで校正してtestへ固定する読出し**。oracle F0とoracle位相原点を同時に外さない。この候補も今回は実行しない。誤差幅を人工的に注入する水準、frequency揺らぎ、追加truth、tracker、PML変更、自然音声、HITLを導入しない。

理由は、現在の問いがまずoracle下の原因識別であり、推定位相へ進むには「同じclockを共有する独立record」「予測対象時刻」「clockを変えたときの全共分散」の契約が別に必要だからである。これは新しいユーザー承認待ちを作る判断ではない。実装・計測・Git変更・tests/smokeを本作業で一切行わない。

## 1. 確認済み資料と推論の区別

この作業で内容を読んだ一次的な設計資料：

- `/workspace/shared/cyclic_noise_identification_design_20261020.md`。既知q、L=64、K=64、H=I、5制約モデル、独立record、PML出力契約の報告、既知clockでの共分散構造が記載されている。
- `/workspace/shared/cyclic-noise-state-likelihood-20261020.md`。既知clockでの3状態表現、周期境界でのAR carryと周期効果reset、有限窓初期分布が記載されている。

PMLの制約は上記資料と親の確認報告を出典とする。本作業でリポジトリを再取得・再検証してはいない。保存対象は正の合成F0 clockで、測定位相原点はない。pulse生成はts0固定である。したがって保存F0の積分や合成pulse列を測定GCI、真のglottal phase、独立phase校正と呼ばない。元資料の参照先は [PML README](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/vocoderbench/pml/README.md) と [合成時計](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/vocoderbench/pml/pml_synthesis.py#L103-L111)。可変mainリンクは現在の再検証を意味しない。

以下の式・提案・識別判断は本資料の代数的推論であり、上記文献の実証結果でも、PMLが実装済みの機能でもない。新しい外部文献の検証は行っていない。

## 2. clock・単位・独立性の契約

位相はradではなくcycle単位で書く。基準時刻t_refを固定し、連続位相を

    u(t;η)=φ+f(t−t_ref),    η=(φ,f),    m_n(η)=q(u(t_n;η) mod 1)

とする。φはcycle、fはHz、tは秒である。radの原点誤差を使うならδ_rad/(2π)へ変換する。qは原設計の滑らかな周期延長で、q′はcycle位相微分である。

一つのpair内では同一の潜在clock ηをtrain/testが共有する。しかし条件付きresidual、AR初期状態、全innovation、周期効果s,jはrecord間で独立に引く。従って

    Y_train ⟂ Y_test | η,θ

である。ηを確率変数として周辺化すると通常は独立ではなくなる。固定未知ηの場合は条件付きモデルのパラメータであり、勝手にrandom drawへ変更しない。

**最小候補で採る時刻契約：同じ時刻gridを持つ二つの独立反復record。** 両方がt_n=n/fs、n=0,…,N−1を観測する。train全体を使い、その別反復testの同じ時刻へclockを適用する。これは独立校正・反復予測であって、時系列の未来予測、因果的online trackerではない。trainにtestより後の同名時刻が含まれても、別反復という契約ではtestデータ漏洩ではないが、「リアルタイム推定」とは呼べない。

連続時間外挿は別契約である。例えばtrainが[0,T)、testが[T+gap,T+gap+T)なら、その絶対時刻を使って位相を外挿し、test開始を無断でφ=0へ戻さない。独立residualを維持するならtestのARは、その絶対位相に対応する新しい無条件初期分布から引く。真に一本の連続ARを観測するならtrain/test residualは条件付きでも相関し、train末尾のAR事後をtestへcarryする別予測問題になる。この二つを混ぜない。

## 3. 小さいclock誤差は平均のglobal rank≤2方向

真値から推定値への誤差では符号が反転するため、ここでは明確に

    e=(δ,Δf)=(φ_true−φ_hat, f_true−f_hat)
    ε_n=δ+(t_n−t_ref)Δf
    d_n=q′(u(t_n;η_hat)),    X=[d, (t−t_ref)⊙d]

と定義する。校正平均を引いたtest残差z=Y_test−m(η_hat)について

    m(η_true)−m(η_hat)=Xe+R,
    |R_n|≤(M_2/2)|ε_n|²,    M_2=sup_u |q″(u)|.

従って一次の平均ずれはglobalにrank≤2。δだけなら、q′を全周期へ同符号で繰り返したrank1方向である。Δfには周期内時刻も含むt q′が必要で、「周期番号×q′」だけへの置換は近似になる。

**固定eに対してXeは共分散ではなく平均バイアスである。** residualの真の共分散をΣとすれば、Rを無視した非中心二次momentは

    E[zzᵀ | e]=Σ+X e eᵀ Xᵀ.

同じeで繰り返し、ensemble平均を正しく引けばclock項は共分散から消える。逆に異なるtrain校正を繰り返してeが変わる場合、平均b_e、共分散C_eを用いて、Σがeに依存しない一次近似なら

    E[z]=Xb_e,
    Cov(z)=Σ+XC_eXᵀ,
    E[zzᵀ]=Σ+X(C_e+b_e b_eᵀ)Xᵀ.

これらの反復moment式のXは共通の固定基準clockで評価した一次線形化行列として読む。各反復のη_hatで評価したX自体の変動まで残すなら、Xとeの積の期待値を取り直す必要があり、上記の簡単な分解は厳密ではない。これは校正誤差の反復分布を定義したときの式である。単一recordの固定clock偏差を、根拠なく平均0 Gaussian noiseへ読み替えることはできない。

clockとresidualの独立性はtrainとtestを分ける理由でもある。trainの校正誤差はtrain residualと一般に相関する。train上のresidualに上のtest独立式をそのまま適用しない。

## 4. 独立timing tangentとの二次統計上の違い

原設計の規格化をc_d²=L^−1Σ_l d_l²、h_l=−d_l/c_d、D=Σ_l d_l²と書く。真の基準clock近傍の固定周期gridで、各周期blockの残差z_kから

    a_k = dᵀ z_k / D

を作る。ここでa_kはAR係数aとは別の「周期別接線係数」である。混乱を避け、以下の行列ではベクトルA_tan=(a_0,…,a_(K−1))ᵀとする。

周期開始t_k、周期内時刻s_lについて、一次近似は

    a_k = δ+Δf(t_k−t_ref+s_bar_d) − j_k/c_d + ξ_k,
    s_bar_d=Σ_l s_l d_l² / D,
    ξ_k=dᵀ r_k / D.

元qと64点gridではdᵀg=0が対称性から成り立つため、振幅効果s_kはこの投影に直接入らない。異なるq/grid、誤った位相での投影、filter付き観測でこの直交を仮定しない。

Bの第k行を[1,t_k−t_ref+s_bar_d]とすると、校正反復または局所Gaussian clock周辺化の下で

    Cov(A_tan) ≈ B C_e Bᵀ + (τ_j²/c_d²)I_K + C_AR,
    (C_AR)_(k,l)=dᵀ(K_r)_(k,l)d / D².

固定eなら第1項を共分散へ入れず、平均Beを残し、非中心momentにB e eᵀBᵀを入れる。

区別に必要なのは以下である。

1. **異なる周期間、特に遠隔周期間の接線cross-moment。** 共通δは全周期の同方向coherence、Δfは周期時刻に沿う低rank構造を作る。独立j_kはoff-block共分散を作らない。δとΔfの共分散によりclock項の符号も変わり得るので「すべて正相関」は一般則でない。
2. **元座標での平均と非中心momentを分けて保持。** 固定clockバイアスを推定したensemble平均とともに示す。周期平均や線形trendを各recordから除去してから比較すると、検出したいclock方向を消す。自己alignmentにも同じ問題がある。
3. **位相内off-diagonal covarianceと異周期blockを同時に使う。** 1周期だけでは、global δのrank1方向はその周期のJ方向と同じであり区別できない。variance対phaseだけでもd²とh²は比例していて区別できない。
4. **ARを別に扱う。** Aの異周期共分散もゼロではない。既知有限窓K_rの予測を使い、clockの全窓coherenceとARのlag依存を比較する。|a|<1のARは長lagで減衰するが、有限sampleで無視できると未計測のまま決めない。白色、V、独立S/Jだけなら異周期residual covarianceは0である。

これは母momentが既知の理想構造の議論で、64周期一つからK×K共分散を安定推定できるという主張ではない。反復pairがあっても、現在のoracle研究へ未登録のestimated-phase集計を追加しない。

さらに「j_kも任意に周期間相関してよい」とモデルを広げれば、Cov(j)にclockと同じlow-rank成分を入れられる。この場合は二次統計だけで物理原因を区別できない。今回の区別は独立j_kという原設計の制約に依存する。

## 5. 位相誤差を追加noiseとして扱うと何を誤認するか

- Jへの吸収：周期内h方向のenergyだけならglobal phase biasを独立timing varianceとして過大推定する。全窓では共通係数なのにK個の独立係数を使うため、遠隔周期のjoint densityが誤る。
- Vへの吸収：対角だけを使うとδ²q′²などの位相依存energyがinnovation variance包絡に見える。ただし原設計Vのcos/sin log-varianceは任意のq′²形状を厳密に表せない。
- Aへの吸収：滑らかな平均ずれをserial correlationとして吸収し得る。ただしglobal低rank構造とAR共分散が同じという意味ではない。
- Wへの吸収：σ²に平均誤差energyが加わり、真のresidual innovation強度と解釈できなくなる。
- Sへの吸収：今回の離散直交性では純粋な一次位相ずれは直接g方向にないが、二次項q″、誤ったgrid、未知波形は振幅方向にも漏れ得る。

誤指定平均を使い、共分散だけを学習すると一般に非中心momentを共分散の代用として近似する。その予測成績が良くても、音声の雑音発生原因がそのモデルだったとは言えない。

## 6. conditional predictive scoreと周辺predictive density

### 6.1 点校正

trainだけからη_hat、θ_hatを決め、test波形を見ず固定すれば

    log p(Y_test | η_hat(Y_train), θ_hat(Y_train))

は正規化されたplug-in予測分布のheld-out log scoreである。禁止すべきなのはこれを「clock不確かさを積分済み」「真のclockに条件付けたoracle score」と呼ぶこと。testを同じデータで合わせ直したplug-in densityとは違い、独立testの予測評価としては有効である。

θも有限trainから推定する以上、ηだけ周辺化しても全parameter uncertaintyを統合したことにはならない。

### 6.2 clock周辺化

適切に指定したclock prior、train likelihood、θの扱いの下で

    p(Y_test | Y_train)
      = ∫ p(Y_test | η,θ) p(η,θ | Y_train) dη dθ

を定義する。同じηをtrain/test間で共有することが必須である。testのclockを新規に独立drawした積分は別問題になる。点校正のη_hat近傍で、平均が線形・Σが固定・clock posteriorがGaussian N(η_bar,C)なら

    Y_test | Y_train ≈ N(m(η_bar), Σ+X C Xᵀ).

これは局所近似であり、非線形qやphase wrapping、複数frequency mode、clock依存Σがある一般の場合の厳密Gaussianではない。全共分散公式は

    Cov(Y_test | Y_train)
      = E[Σ(η,θ)|Y_train] + Cov(m(η)|Y_train)

であり、平均の不確かさだけを足す式は第1項の変動を固定した近似である。

frequentistなη_hatの標準誤差行列をそのままposterior Cと名付けない。尤度曲率の逆行列も、境界・複数mode・有限標本で正当なposteriorを保証しない。現在はpriorも不確かさ法も固定していないため、周辺密度を新たな比較条件にしない。

### 6.3 観測座標・先読み

どちらも元のN test samples上のjoint densityを採る。resampling・alignment後の数値をJacobianなしに同じdensityと扱わない。test前半でclockを更新して後半を予測するなら、更新前の逐次条件付き密度を掛けるprequential設計へ変更する必要がある。test全体で更新したclockを全testへ遡及適用することは不可。

## 7. 平均だけのrank≤2で全clock誤差を説明しない

元のΣはclockに依存する。vのphase、g/hの値、cycle membership、境界でのs/j reset、AR初期分布も変わる。

- 平均に対するrank≤2は正しいが、Σ(η)−Σ(η_hat)までrank≤2とは限らない。
- 周期原点の小変更でsampleがcycle境界を跨ぐと、s/jのblock所属が変わる。qとq′が端点0なので一部の項が小さくなっても、境界規則を省略する理由にはならない。
- f=f0=fs/Lを固定した位相原点校正なら、v_nは依然L-sample周期である。各原点候補に対応するZ、P初期、g/h、境界を明示すれば原設計の有限窓構成を使用できる。原点不明なのにoracle境界だけ保持してはならない。
- fも未知にすると一般の候補ではsample上の周期長は整数Lでない。元のL周期幾何和P_(−1)をそのまま使えない。無限過去clockが既知ならP_n=Σ_(i≥0)a^(2i)v_(n−i)という一般形を考えられるが、これは新しいモデル契約を必要とする。frequencyまで外すと最小変更を超える理由である。

既知clockでの3状態表現は、固定されたclock候補ごとの適切な境界・初期分布の下なら利用可能な数学的表現である。clockを周辺化したら3状態の線形Gaussian filterだけで厳密に済む、とは言えない。平均だけの局所線形・固定Σならglobal2係数を加える表現は考えられるが、今回は実装しない。

## 8. Taylor誤差と不確かさの範囲

任意に「δは何度まで」「Δfは何Hzまで」と選ばない。train校正から得る誤差分布または正当に構成した不確かさ集合Eが先に必要である。集合が与えられた場合にだけ

    ρ=max_(e∈E,n∈test) |δ+(t_n−t_ref)Δf|,
    ||R||₂ ≤ (M_2/2) [Σ_n ε_n⁴]^(1/2)
             ≤ (M_2/2) sqrt(N) ρ²

を評価する。たとえば事前に妥当性を確立した楕円集合(e−b)ᵀC^−1(e−b)≤cなら、各時刻x_n=(1,t_n−t_ref)ᵀについて

    max |x_nᵀe| = |x_nᵀb| + sqrt(c x_nᵀ C x_n)

となる。ただしcをχ²分位点とするには対応する分布近似・coverage根拠が要る。ここではcやcoverage水準を都合よく設定しない。Gaussianは非有界なので「全実現で小さい」と保証しない。

固定Σ下で平均の一次近似により生じるGaussian KLは、正確な残差Rに対し(1/2)RᵀΣ^−1Rである。||R||²だけでなくnoiseスケールと方向で評価すべきで、低residual水準では小さい波形誤差もscoreへ効き得る。合否閾値は研究目的から別に事前固定するもので、本資料は作らない。

frequency誤差は観測・外挿時刻とともに蓄積する。train中心をt_refにしてδとΔfの数値相関を減らせても、test遠方の実際の位相不確かさは消えない。大きなdrift、phase slip、複数modeでは局所線形式を棄却し、正確な周期モデルが必要になる。clock依存Σの近似誤差はこの平均Rの上界では制御されない。

## 9. 将来の最小候補を一つに絞る

候補名：**train-only共通位相原点校正（既知q・既知f0・同始点独立反復）**。

1. 新たな誤差を注入せず、固定人工qとf0は与え、位相原点のみ推定器へ渡さない。元のtruth原点を評価者が知っていることと、推定器が使うことを分離する。
2. 全noise候補に共通の、trainだけを使う非機械学習校正を採る。最小案はφ∈[0,1)でΣ_n[Y_train,n−q(φ+f0 t_n)]²を最小化する既知template fitting。これはAR/V/S/J全ての下で正確な最尤推定だとは主張しない。目的関数、円周上の同値解、tie規則、探索・失敗契約を実施前に固定する。
3. 得たφ_hatを全候補で共有し、trainでnoise parameterを適合、独立testで固定する。校正もnoise適合もtrain利用でよいが、train residualとφ_hatの独立性は仮定しない。test側だけが校正誤差と条件付き独立になる。
4. 平均だけでなく候補ごとの全Σをφ_hatに対応させる。oracleのcycle boundaryやv phaseを密かに残すなら、それは「平均位相だけの感度分析」であり、本候補ではない。
5. 評価対象は独立testのplug-in densityとoracleとの差、真値に対するwrapped原点誤差、接線平均・異周期cross-momentの整合性。これをPMLのphase性能、未知F0性能、posterior predictive、自然音声の生理的同定と呼ばない。

原点truthは原設計の固定0から動かさない。したがってこの候補が成功しても、任意のsampleに対するsub-sample原点や異なるfrequencyで成功した証拠にはならない。位相水準sweepを後付けして一般性を補わない。

**現時点の停止点：解析完了。** oracle結果未確定、全clock共分散の校正仕様未実装、校正の不確かさ・数値解の契約未固定という留保を保持する。これらを根拠なく埋めて追加条件を開始せず、進行中5×100の結果を待つ。その結果で本資料の式が変わるわけではなく、別段階の実施価値を判断できるようになる。

## 10. 仮想5役・2往復の批評

これは一人の設計者が5つの観点で行った仮想レビューであり、実在5人の査読や追加実験ではない。

### 第1往復：提案 → 批評 → 応答

1. 生成モデル役：「global clockに2次元Gaussian noiseを足す」。批評：「固定未知clock誤差は平均ではないか」。応答：固定eの平均Xeと、校正反復・posterior周辺化によるXC_eXᵀを分離した。
2. 統計役：「q′方向の分散でJを判定する」。批評：「global phaseも同じ方向である」。応答：周期間cross-moment、平均、AR予測を併用し、1周期・対角のみでは区別不能と明記した。
3. 時刻契約役：「trainでF0を取りtestへ外挿する」。批評：「同始点反復か連続ARかで条件付き予測が違う」。応答：最小候補は同始点独立反復、連続時間は別契約とした。
4. 数値・近似役：「rank2だけ追加すれば全て済む」。批評：「clockはvとcycle境界も動かす」。応答：rank2は平均の一次式に限定し、clock依存Σ・初期law・境界を別に明示した。
5. 批評家役：「今すぐfrequency幅を数水準試せばよい」。他役：「進行中oracle研究の事後拡張になる」。応答：今回は解析のみ、将来候補も原点校正一つ、frequency既知のままとした。

### 第2往復：反例 → 再応答 → 棄却条件

1. 生成モデル役：「周辺化するとtrain/testは独立でなくなる」。再応答：条件付き独立だけを仮定し、同じlatent ηを共有したposterior predictiveを定義した。棄却条件：test clockの独立再抽選、または連続ARを独立record扱いすること。
2. 統計役：「各recordの平均・trendを除いてcross-covarianceを安定化したい」。再応答：それはclock方向を消すため、既知template残差の平均と非中心momentを残す。棄却条件：self-alignment後のJ減少を原因識別成功とすること。
3. 時刻契約役：「PMLの0始点pulseでφ_hatを代用できる」。再応答：合成clockの原点規約であって測定原点ではない。既知q fittingは別の人工非機械学習校正である。棄却条件：PML測定GCI・自然音声phase推定への読み替え。
4. 数値・近似役：「小さい標準誤差ならTaylor近似は十分」。再応答：外挿期間、尾確率、q″上界、Σ^−1尺度のscore誤差、clock依存Σの誤差を別々に確認する必要がある。棄却条件：根拠のないδ/Δf幅、Gaussianの全実現微小性、sample周期Lの無断流用。
5. 批評家役：「原点候補の成功ならoracle仮定を外せたと言える」。再応答：外せるのは既知q・既知一定f0・同始点反復での原点供与だけ。棄却条件：未知波形、未知filter、未知frequency、通常online tracking、aspirationの同定まで成功を拡張すること。

## 11. 解析的補足：独立反復における原点1係数のplug-in予測損失

追記日：2026-10-20。親から提示された式を独立に導出した。以下は局所線形Gaussianモデルの代数であり、追加計測、コード実行、新条件の開始、実装成績ではない。

### 11.1 仮定を固定する

同一の時刻grid、既知f、既知qの形、既知の正定値共分散Σを持つ独立train/testを考える。dは全recordにわたる固定の平均位相微分であり、各周期のq′を反復したN次元ベクトルである。D=dᵀd>0と置く。clockによるΣの変化や周期境界移動は、この補足では明示的に凍結する。

    Y_train=q0+dδ0+r_train,
    Y_test =q0+dδ0+r_test,
    E[r_train]=E[r_test]=0,
    Cov(r_train)=Cov(r_test)=Σ,
    r_train ⟂ r_test.

これは真の非線形qを一次展開したモデルに限る。真値を局所原点に置けばδ0=0である。一般のδ0を残す場合、OLS推定値とその誤差は

    δ_hat=dᵀ(Y_train−q0)/D,
    e=δ_hat−δ0=dᵀr_train/D,
    E[e]=0,
    Var(e)=dᵀΣd/D².

したがって「δ_hat=dᵀr_train/D」はδ0=0の場合、またはδ_hatを推定誤差の略記として用いる場合の式である。

### 11.2 実現損失と期待損失

testを正しい固定Σ、plug-in平均q0+dδ_hatでscoreし、同じΣ・真の平均を使うoracle NLLとの差をΔNLLとする。determinant項と定数項は同じなので厳密に

    ΔNLL
      = (1/2)(r_test−de)ᵀΣ^−1(r_test−de)
        −(1/2)r_testᵀΣ^−1r_test
      = (1/2)e² I − e dᵀΣ^−1r_test,
    I=dᵀΣ^−1d.

固定されたtrainに条件付けると、test residualの条件付き平均は0であり、

    E_test[ΔNLL | train]=(1/2)e² I.

さらにtrain反復について平均すると

    E_train,test[ΔNLL]
      = (1/2) I Var(e)
      = (1/2)(dᵀΣ^−1d)(dᵀΣd)/(dᵀd)².

期待値はnats/recordである。個別testの実現差は交差項のため負にもなり得る。各recordが必ず1/2以上を失うという主張ではない。推定にbiasがある別手法ではVar(e)ではなくE[e²]=Var(e)+(E[e])²が入る。

### 11.3 下限と等号条件

Σ^(1/2)dとΣ^(−1/2)dへCauchy–Schwarzを適用すると

    (dᵀd)² ≤ (dᵀΣd)(dᵀΣ^−1d).

従って、上の不偏OLSでは

    E[ΔNLL] ≥ 1/2 nats/record.

等号は二つのベクトルが比例するとき、すなわちΣd=λdとなる正のλが存在するときに限る。これはdがΣの固有方向であるという条件である。共分散の全方向がwhiteである必要はない。

この1/2は「未知原点を推定するあらゆる方法」の普遍的下限ではない。ここで指定したOLSの式と、その後述のGLS比較についての結果である。真値を知った定数推定、biasやpriorを伴う縮小推定、異なるtrain長などへ無条件に一般化しない。

### 11.4 GLSなら任意の正定値Σで1/2

既知ΣによるGLSでは

    δ_hat_GLS=I^−1 dᵀΣ^−1(Y_train−q0),
    e_GLS=I^−1 dᵀΣ^−1r_train,
    Var(e_GLS)=I^−1.

同じgrid・同じΣの独立testに対する期待損失は

    E[ΔNLL_GLS]=(1/2) I I^−1=1/2 nats/record.

同じgrid・同じΣという条件が重要である。異なるtest gridや共分散を持つ線形問題なら、GLSの期待損失は(1/2)I_test/I_trainとなり、1/2とは限らない。これは連続時間外挿やfrequency不確かさを本補足で解決したという意味ではない。

### 11.5 原設計W/S/JとV/Aへの適用

原設計の同じgridで、1周期微分をd_cycle、h=−d_cycle/c_d、||h||²=Lとする。global dはd_cycleをK回並べたベクトルである。

- W：Σ=σ²IなのでΣd=σ²d。OLSの期待損失は1/2。
- S：Σ=σ²I+τ_s²U_sU_sᵀ。各blockでgᵀd_cycle=0なのでU_sᵀd=0、従ってΣd=σ²d。OLSの期待損失は1/2。直交は原設計のqと64点gridの対称性に依存する。
- J：Σ=σ²I+τ_j²U_jU_jᵀ。各blockでhhᵀd_cycle=Ld_cycleなのでΣd=(σ²+Lτ_j²)d。OLSの期待損失は1/2。Jが独立周期効果であっても、その共通固有値を持つ各block方向を反復したglobal dは固有方向になる。
- V：Σ=diag(v_n)。等号にはd_n≠0の全位置でv_nが同じであることが必要である。一般の非定数位相分散では成立せず、OLSの期待損失は1/2より大きい。vが定数へ退化する等の例外を含めて「必ず厳密不等号」とはしない。
- A：Σ=K_r。有限窓AR共分散の固有方向とglobal周期微分dが一致する保証はなく、一般には等号でない。a=0などの退化では等号になり得る。有限窓・境界を無視した循環Fourier対角化を根拠にdを固有方向と認定しない。

W/S/Jで同じ1/2になることは、位相推定精度が同じという意味ではない。固有値λに応じてOLSのVar(e)=λ/Dは異なるが、test scoreの平均方向の曲率I=D/λとの積が1になるためである。Jで位相誤差が大きくても、その方向の予測分散も大きいという相殺が、この限定された期待scoreに現れる。

### 11.6 この補足で言えること・言えないこと

恣意的なphase誤差幅や追加500pair条件を作らなくても、固定Σ・局所線形平均・同始点独立反復という理想条件では、原点1係数のOLS/GLS校正がもたらす平均的なplug-in NLL損失を解析できる。比較の単位はrecordであり、既存のK周期で表示するなら期待損失をKで割るだけである。

一方、これはnoise parameterの推定、誤指定Σ、clock依存Σ、phase-dependent cycle membership、非線形Taylor remainder、円周上の多峰性、frequency推定、train/test残差の連続性、posterior周辺化を含まない。5モデルを再適合した勝者表、全phase校正後のscore差、PMLの性能を予告するものでもない。1/2を許容差・同等性幅・追加実験の採否閾値として流用しない。

**追記後も判断は変わらない：解析のみ完了。進行中oracle研究の条件・反復数・集計は変更しない。**
