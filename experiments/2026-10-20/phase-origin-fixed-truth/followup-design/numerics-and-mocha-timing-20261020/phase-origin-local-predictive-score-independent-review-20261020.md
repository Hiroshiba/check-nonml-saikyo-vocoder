# 局所線形predictive期待score：独立紙上レビュー

2026-10-20。対象は `phase-origin-local-predictive-score-reference-20261020.md`。比較のため `phase-origin-local-score-reference-20261020.md` も読んだ。原文は変更していない。Gaussian密度の代数による紙上検算のみであり、数値計算、実装、テスト、データ取得、Cloud、Git、Library操作は行っていない。

## 結論

**必須の数学修正は見つからない。** 同情報量・独立train/test・既知分散・1次元の厳密線形平均という参照モデルの下で、全ての固定truthに対するoracle比期待損失はplug-inが1/2、predictiveが(log 2)/2であり、predictive対plug-inの期待利得は(1−log 2)/2となる。train条件付きでは利得の符号が変わること、不適切priorとproper posteriorの区別、proper円周有限標本・現500・品質保証への非外挿も適切に記載されている。

## 1. 独立導出

I=dᵀd/s、e=d/||d||とすると、train MLの誤差はθ_hat−θ0=dᵀε/(dᵀd)である。従ってU=√I(θ_hat−θ0)は標準正規であり、独立testの標準化誤差Xとも独立である。

posterior分散I^−1をtest平均へ伝播した追加共分散は

    ddᵀ/I = s eeᵀ。

e方向のpredictive分散だけがsから2sへ変わる。直交補空間は三分布で一致するため、score差はoracle N(0,1)、plug-in N(U,1)、predictive N(U,2)の比較に厳密に帰着する。

Gaussian log densityの差から

    log p_plug−log p_oracle = UX−U²/2,
    log p_pred−log p_oracle = −(log 2)/2−(X−U)²/4+X²/2,
    log p_pred−log p_plug = −(log 2)/2+(X−U)²/4。

独立性、E X²=E U²=1、E XU=0からE(X−U)²=2となる。よって反復期待はそれぞれ−1/2、−(log 2)/2、(1−log 2)/2であり、本文§1と一致する。truthの値がこの計算へ残らないのは、厳密線形の位置モデルだからである。

## 2. 条件付きの符号

trainを固定したときE_test(X−U)²=1+U²であるため、本文の条件付き三式は全て正しい。特に

    E_test[log p_pred−log p_plug | Y]
      = (1+U²)/4−(log 2)/2

はU²=2 log 2−1でzeroとなり、その下で負、上で正となる。log 2=∫_1^2 dt/t>1/2より閾値は正であり、連続な標準正規train lawの下で両領域は正確率を持つ。

またpredictive対oracleの条件付き期待は

    −(log 2)/2+(1−U²)/4
    ≤ −(log 2)/2+1/4 < 0。

従って条件付きにもoracleを上回らない。これと「個別のtest実現ではoracleより高いscoreを取り得る」は両立する。predictive対plug-inの実現差は各固定trainでXの連続な全実数supportにより正負両方を取り得る。

異情報量では、test方向の誤差が√ρ U、predictive分散が1+ρになる。E(X−√ρ U)²=1+ρから、本文§4の三式ρ/2、log(1+ρ)/2、[ρ−log(1+ρ)]/2も一致する。従って同情報量の定数を任意のtest長へ流用できないとの注意は必要かつ正しい。

## 3. priorと適用域

- 平坦dθは実直線上の確率priorではない。一方、d≠0、s>0のため、尤度をθで規格化したposteriorはproper Gaussianになり、その混合predictiveも各Yでproper密度となる。この構成でraw evidenceやprior平均riskを定義しないという本文の区別は正しい。
- 固定truthの頻度論的反復期待は、truthをproper priorから引くことを必要としない。従って上の厳密定数とpriorの不適切性は矛盾しない。
- proper Gaussian priorでは通常縮小とtruth依存のbiasが生じ、同じ全固定truth定数にはならない。proper円周priorの非線形混合にも有限標本の厳密定数を移していない。
- 局所Gaussian近似だけで期待log score極限まで保証できない点について、本文は同一枝への集中、非局所mode、ML tail、mean剰余、期待の一様可積分性等の追加制御を明示し、元モデルでの定理を証明したとは述べていない。
- rank1は線形参照の性質であり、1変数の非線形混合一般の性質ではない。full-circleのrank高々6は、元モデルのmean曲線が6次元以下の固定線形spanに入るというモデル前提による上限として読むべきであり、位相が1変数であることだけからは導けない。本文はこの誤推論をしていない。本レビューでは元の6次元基底定義を別途再導出していない。
- 既存局所参照のWの近似−1/2と、今回の厳密線形参照の−1/2は適用域が区別されている。gate、成功subset、丸めlaw、非線形OLS、現500の有限平均、合否閾値や自然音声品質へ定数を拡張した箇所は見つからない。

## 判定

紙上参照として整合する。修正待ちの必須指摘はなく、現500・source・score・方式採用を変更する根拠を追加したものでもない。本レビューの保存で依頼範囲を完了する。
