# 局所線形W：predictiveの期待score参照

2026-10-20。紙上・記号式のみ。既存 `phase-origin-local-score-reference-20261020.md` はplug-inの局所損失を扱うが、以下の線形Gaussian predictiveの厳密比較は未収録だったため別紙にする。現500の二score、source、データ、gate、実験は変更しない。

## 1. 結論とモデルの区別

**同じ情報量の独立train/testを持つ1次元線形Gaussian参照モデルでは、全固定truthについて**

    E[log p_oracle−log p_plug] = 1/2,
    E[log p_oracle−log p_pred] = (log 2)/2,
    E[log p_pred−log p_plug] = (1−log 2)/2.

単位はnats/test record。これは以下の線形モデルでは厳密な有限標本式である。一方、元の非線形な円周位相モデルへの局所・漸近解釈は追加条件を要する。proper一様円周priorの有限標本定理でも、実500の改善保証でもない。

## 2. 固定truthでの厳密な線形参照

既知μ、既知d≠0、既知s>0を固定し、

    Y=μ+dθ0+ε,   Z=μ+dθ0+ε′,
    ε,ε′ は独立 N_N(0,sI),   θ0∈R は任意の固定値,
    I=dᵀd/s>0

とする。θは円周ではなく実直線の平均パラメータである。μ+dθはこの参照モデルでは全θで厳密な平均であり、μをデータからfitしない。

train MLは

    θ_hat=dᵀ(Y−μ)/(dᵀd),
    U=√I(θ_hat−θ0) ∼ N(0,1).

θについて不適切平坦測度dθを用いると、尤度をθで規格化したposteriorは N(θ_hat,I^−1) というproper分布になる。このposteriorをtest likelihoodに混合した条件付きpredictiveは

    p_pred(·|Y)=N_N(μ+dθ_hat, sI+ddᵀ/I).

これは各Yに対して正規化された密度である。ただしdθはproper priorではなく、raw evidenceやprior平均riskの確率モデルをこれで定義したとは言わない。以下は固定truth lawで直接計算するため、proper priorからtruthを引く必要はない。

oracleはN_N(μ+dθ0,sI)、plug-inはN_N(μ+dθ_hat,sI)。e=d/||d||方向だけが異なり、直交補空間の密度は三者で共通なのでscore差で消える。e方向を√sで標準化すると、

    X=eᵀ(Z−μ−dθ0)/√s ∼ N(0,1),  X ⟂ U,
    oracle: N(0,1),  plug-in: N(U,1),  predictive: N(U,2).

predictiveの増加共分散ddᵀ/I=s eeᵀはrank1である。

## 3. 条件付きと反復期待を別々に導出

実現score差は上の1次元Gaussianから

    log p_plug−log p_oracle = UX−U²/2,
    log p_pred−log p_oracle
      =−(log 2)/2−(X−U)²/4+X²/2,
    log p_pred−log p_plug
      =−(log 2)/2+(X−U)²/4.

trainを固定してXだけを平均すると

    E_test[log p_plug−log p_oracle | Y] =−U²/2,
    E_test[log p_pred−log p_oracle | Y]
      =−(log 2)/2+(1−U²)/4,
    E_test[log p_pred−log p_plug | Y]
      =(1+U²)/4−(log 2)/2.

従ってpredictive対plug-inの条件付き期待は、U²が2log 2−1より小さいと負、大きいと正。2log 2−1>0なので両方のtrain領域は固定truthの下で正確率を持つ。特にU=0ではplug-inがoracleになり、分散を広げるpredictiveは不利になる。predictive対oracleの条件付き期待は常に負であり、oracleを超える期待scoreではない。

さらにtrainを平均してE U²=1を代入すると§1の三式を得る。これは無選択の反復期待であり、各実現や有限反復平均の符号を固定しない。例えば最後の実現差は(X−U)²に依存し、各trainでもtest実現によって両符号を取る。

## 4. 同じ情報量という条件

線形Gaussianのままtrain情報量をI_tr>0、test情報量をI_te>0とし、ρ=I_te/I_trと置けば、同じ1方向への射影でtestの標準化平均誤差は√ρ U、predictive分散は1+ρとなる。その固定truth反復期待は

    plug-inのoracle比損失 = ρ/2,
    predictiveのoracle比損失 = log(1+ρ)/2,
    predictive対plug-in利得 = [ρ−log(1+ρ)]/2.

よってlog 2は「testとtrainが同じ情報量」の結果であり、任意の評価長に普遍的な定数ではない。同じNでも設計dや分散が違えば同情報量とは限らない。本節は条件依存性を示す記号補足で、別の比較実験を提案しない。

## 5. proper円周モデルとの接続には追加条件が要る

元のm(φ)を真値近傍でm(φ0+δ)≈m(φ0)+dδと書くことはできるが、その近似を全円周へ延ばしたモデルではない。円周のproper一様prior dφを、実直線の不適切dθと同じpriorとして扱わない。有限のproper Gaussian priorを線形モデルに用いても、一般にはposteriorの縮小が入り、上の全固定truthの定数式とは異なる。

円周モデルでこの参照が局所的な極限を与えるには、例えば情報増加・noise縮小の系列で、識別可能な同一局所枝へposteriorとMLが集中し、priorがその近傍で滑らかかつ正、標準化したposteriorがN(θ_hat,I^−1)に近づく条件が必要。さらに非線形meanの剰余がtest log score尺度でも消え、非局所modeの質量、MLのtail、期待log scoreの一様可積分性などを制御しなければ、分布近似から期待定数へは移れない。ここではその漸近定理を元モデルについて証明していない。

元のfull-circle predictiveは一般に非Gaussian混合で、追加共分散Cov_post[m(φ)]のrankは高々6。θが1変数でも、非線形な円周曲線上の混合全体をrank1に置換できない。今回のrank1は**厳密線形参照**または条件を満たす局所一次近似だけの性質である。

丸めgeometry、binary64生成、φ_evalの量子化、root/boundary gate、成功subsetへの条件付けは、ここで用いたUの標準正規lawと無選択の期待を保証しない。非線形OLSのbias・別mode・ランダム曲率も自動的には消えない。したがって現500への第三score追加、期待値を使った合否閾値、観測利得の原因断定、自然音声品質の保証には用いない。

## 6. 五仮想役・二往復

五役は「線形推定」「予測分布」「局所幾何」「評価設計」「批評」。一人の机上議論であり五名の独立査読ではない。

### 往復1

1. 線形推定「ML誤差分散はI^−1」→批評「非線形にも厳密か」→全θで線形な参照モデルだけの厳密式とした。
2. 予測分布「平坦priorならGaussian predictive」→評価設計「proper円周priorと同じか」→不適切測度からのproper条件付きposteriorと円周モデルを分離した。
3. 局所幾何「位相は一つなのでrank1」→批評「円周全体は曲線」→線形rank1とfull-circleの高々6次元を区別した。
4. 評価設計「利得が正なら各trainで改善」→線形推定「U²で条件付き符号が変わる」→条件付き式を先に導いた。
5. 批評「oracleよりも高scoreなのか」→予測分布「oracle比期待損失は正」→実現scoreと条件付き期待を分けた。

### 往復2

1. 線形推定「Nを増やせば必ず同じ定数」→評価設計「train/test情報量比も必要」→ρの一般式を補足した。
2. 予測分布「posteriorが局所Gaussianなら期待も収束」→批評「log tailと一様可積分性が必要」→期待極限を未証明の追加条件として残した。
3. 局所幾何「gate通過なら局所枝保証」→批評「数値成功と統計的集中は別」→実500への非適用を維持した。
4. 評価設計「期待利得を検出閾値へ」→線形推定「有限反復には揺らぎと選択がある」→閾値・実測保証へ転用しない。
5. 批評「これをsourceへ追加」→全役「今回の依頼は紙上参照のみ」→文書保存で停止し、実装・計算・新実験を開始しない。

## 7. 読取りと実施範囲

既存 `phase-origin-local-score-reference-20261020.md` を読取り、重複するplug-in局所式を参照に留め、predictiveとの厳密線形比較を追加した。導出はGaussian密度の代数と固定truth期待だけで、外部資料・新source・数値評価を必要としない。現500を再評価せず、方式・実験採用は未決定のまま。
