# W-only scale predictive gain：独立紙上レビュー

2026-10-20。対象：`white-scale-predictive-gain-derivation-20261020.md`。
文書読取・記号推論のみ。科学コード実行/import、数値スイープ、tests、実測ログへの適用・再集計は行っていない。

## 結論

**平均0既知、独立同分布 white Gaussian、共通の固定真分散 E₀>0 という条件下で、期待差の閉式、τ固定極限、n=m の極限 (1−log 2)/2 は正しい。修正すべき数式・条件不足は見つからなかった。**

対象は test ベクトル全体の joint log score の期待差であり、一標本当たりの差ではない。実測 BMA−W の平均・CIとの一致、原因同定、改善寄与率は導かれない。対象文書の限定は適切である。

## 1. posterior と predictive を独立に確認

h=n/2、k=m/2、Q=xᵀx、R=yᵀy とする。
train likelihood と測度 dE/E を掛けると

    p(E|x) ∝ E^(−h−1) exp[−Q/(2E)]。

Q>0、h>0 で積分は Γ(h)(Q/2)^−h となり、文書の正規化定数は正しい。

test likelihood を混合すると

    p_B(y|x)
    =(2π)^−k (Q/2)^h Γ(h+k)
      /{Γ(h)[(Q+R)/2]^(h+k)}
    =Γ(h+k) π^−k Q^h /{Γ(h)(Q+R)^(h+k)}。

これは proper な posterior に対する proper likelihood の混合なので、固定 x の下で R^m 上に正規化される。共通 E を混合するため、test joint density を各一標本 marginal の積に置換できない。

この成立は dE/E の正規化を回復しない。train の raw prior predictive/evidence は、任意な測度定数を含み、x 空間全体の proper density ではない。条件付き predictive の proper 性と矛盾しない。期待値は improper prior に対してではなく、固定 E₀ の反復 sampling 分布に対して取る。

既知平均0なので MLE は Q/n。平均推定後の残差自由度や n−1 分母へ置換すれば別問題となる。

## 2. realized log 比と期待値

plug-in density

    p_M(y|x)=(2πQ/n)^−k exp[−nR/(2Q)]

との差を直接整理すると

    D=logΓ(h+k)−logΓ(h)−k log h
      +(h+k)log[Q/(Q+R)]+hR/Q。

定数・符号とも本文と一致する。

Q/E₀ と R/E₀ は独立 χ² なので、共通 scale の Gamma モーメントから

    E log Q−E log(Q+R)=ψ(h)−ψ(h+k)、
    E(R/Q)=k/(h−1)     (h>1)。

従って有限期待差は

    Δ(n,m)=logΓ(h+k)−logΓ(h)−k log h
           +(h+k)[ψ(h)−ψ(h+k)]
           +hk/(h−1)。

E₀ は消える。n=m=N、h=k=N/2 を代入した本文の式も一致する。

0<n≤2、m>0 では log 項の期待値は有限だが E(R/Q)=∞。Bayes の期待 log score は有限、plug-in 側は −∞ なので差は +∞ であり、有限な gain の公式として扱えない。Q=0 で posterior が定義できない場合を floor で補うことも本導出に含まれない。

各 realization で D≥0 とは限らない。R/Q=s と置いた可変部分の導関数は h−(h+k)/(1+s)、二階導関数は (h+k)/(1+s)²>0 で、s=k/h が極小という本文の計算も正しい。両 predictive は正規化された異なる密度なので、条件付きの全 test 点で一方の密度が厳密に他方を上回ることはない。

## 3. τ固定極限の独立展開

τ=k/h>0 を固定し、b=1+τ とする。Stirling/digamma の記号展開から

    logΓ(bh)−logΓ(h)−τh log h
      =bh log b−τh−(1/2)log b+O(h^−1)、

    bh[ψ(h)−ψ(bh)]
      =−bh log b−τ/2+O(h^−1)、

    hk/(h−1)=τh+τ+O(h^−1)。

O(h) 項が消え、

    Δ → [τ−log(1+τ)]/2。

τ=1 で (1−log 2)/2。τ>0 で正という不等式も成立する。τ は固定の有限な正値という条件であり、test/train 比が無制限に変わる漸近へ無条件に流用しない。

n=m の次項も独立照合した。三項の 1/h 係数はそれぞれ −1/24、−1/8、+1 なので、

    Δ(N,N)=(1−log 2)/2+5/(6h)+O(h^−2)

で本文と一致する。

固定 m、n→∞ の別極限でも、固定 k に対する Gamma 比・digamma 差の展開で定数項が相殺され Δ→0 となる。したがって本文の評価長に関する注意も正しい。

## 4. 解釈の監査

- **単位**：自然対数の nats。test 全体の合計 score であり、n=m=N の一標本当たり差は Δ/N→0。
- **モデル**：W-only、平均0既知、独立 train/test、同じ E₀。未知平均、harmonic fit、色付き shape、重複窓、分布変化への一般化ではない。
- **期待値**：train と test の双方に関する sampling expectation。特定 train 条件付き期待値でも、毎回正となる realized gain でもない。
- **improper 測度**：proper test predictive は適切に示されているが、raw evidence の proper 性は主張していない。これは任意の improper prior によるモデル比較の安全性を意味しない。
- **実測**：対象文書の BMA−W 平均・CI は提供値としてのみ記載されており、本レビューでも未検証。理論式との見た目の近さは因果説明にならない。
- **算術分解**：同じ観測・同じ score 定義で W-only Bayes の中間 score が実際に得られれば、差の加法分解は恒等式として成立する。ただし独立寄与・因果寄与・両項の正値性は含意しない。

## 最終判定

本文の数式と限定を支持する。追加計算・既存 BMA の変更・W-only Bayes の実測導入を行う根拠や許可とはせず、独立紙上レビューはここで完了する。
