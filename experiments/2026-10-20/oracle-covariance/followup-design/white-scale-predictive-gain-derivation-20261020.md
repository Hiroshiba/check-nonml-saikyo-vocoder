# Wのみの未知scale：posterior predictiveとMLE plug-inの期待score差

2026-10-20。独立した紙上導出。コード・数値実行・import・tests・新実験・Git変更を行わず、既存500組BMAも変更しない。

## 0. 結論

train/testがそれぞれN標本、平均0既知、独立white Gaussian、真の共通分散E₀>0という限定条件で、h=N/2、N>2とすると、

 Δ_mean
 =logΓ(N)−logΓ(h)−h log h
  +N[ψ(h)−ψ(N)]+h²/(h−1)。

これは提示された式と一致する。ここでΔは「W-only Bayes posterior predictiveのtest全体のlog score − train MLE分散plug-inのtest全体のlog score」。trainとtestの両方を真の分布で平均する。logは自然対数であり、per-sample scoreではない。

N→∞でtrain長とtest長を同じに保つと

 Δ_mean→(1−log 2)/2>0。

従って、noise familyを一つも追加しなくても、未知分散をplug-inせず積分することだけで、この漸近的な期待score差が生じる。これを実測BMA−Wの改善量に等置したり、実測の原因・寄与率を証明したものと読んだりしてはいけない。

## 1. 限定モデルと観測

train x∈R^n、test y∈R^mについて

 x_i,y_j | E₀ ∼ N(0,E₀)

がすべて独立とする。平均は既知の0で、trainから平均・F0・harmonic係数をfitしない。E₀は反復実験で固定された真の値であり、期待値を取るためにimproper priorから生成しない。

Q=xᵀx、R=yᵀy、h=n/2、k=m/2と置く。このとき

 U=Q/E₀∼χ²_n、V=R/E₀∼χ²_m

は独立。まず一般のn,mで導出し、最後にn=m=Nを代入する。

Bayes側だけで未知Eに共通のscale測度dE/Eを用いる。MLE側の分散はÊ=Q/n。既知平均なので分母はnであり、n−1ではない。

## 2. train posteriorとtest predictive

trainを観測した後のEの密度は

 p(E|x)=[(Q/2)^h/Γ(h)]E^(−h−1)exp[−Q/(2E)]。

Q>0、n>0ならproperなinverse-gamma posteriorである。連続GaussianモデルではQ=0は確率0。量子化された全零trainなどは本導出の対象外で、勝手にfloorを足さない。

test likelihood (2πE)^−k exp[−R/(2E)] を積分すると

 p_B(y|x)
 =[Γ(h+k)/Γ(h)]π^−k Q^h/(Q+R)^(h+k)。

これは固定xに条件付けたR^m上のproper predictive density。trainのraw prior predictiveがproperであるという意味ではない。dE/E自体はimproperだが、properなtrain posteriorからの予測混合は正規化される。

MLE plug-in predictiveは

 p_M(y|x)=(2πQ/n)^−k exp[−nR/(2Q)]。

どちらも同じtestベクトルに対するjoint density。Bayes側では共通Eを積分した結果、test各標本は予測上独立ではない。標本ごとのmarginal predictiveを独立に掛けたscoreへすり替えない。

## 3. realized score差

同じtrain/testについてlog比を取ると

 D(Q,R)
 =logΓ(h+k)−logΓ(h)−k log h
  +(h+k)log[Q/(Q+R)]+h R/Q。

E₀は比から消える。これは個々のrealizationの差であり、常に正という主張ではない。testの実現によってplug-inが高いscoreを取る場合もある。

特にR/Qを変数とすれば、最後の2項の微分は

 −(h+k)/(1+R/Q)+h

となり、R/Q=k/hで極小になる。parameter integrationがすべてのtestに一様に利益を与えるわけではないことと、平均scoreの比較は両立する。

## 4. 期待値の閉形式

Gamma変数のlog期待値から

 E[log Q]=log(2E₀)+ψ(h),
 E[log(Q+R)]=log(2E₀)+ψ(h+k)。

同じscaleを持つ独立Gamma変数なのでQ+Rのshapeはh+k。さらにn>2、すなわちh>1なら

 E[R/Q]=E[R]E[1/Q]=k/(h−1)。

従って

 Δ(n,m)=E[D]
 =logΓ(h+k)−logΓ(h)−k log h
  +(h+k)[ψ(h)−ψ(h+k)]
  +hk/(h−1)。

n=m=Nではk=h、h+k=Nなので

 Δ(N,N)
 =logΓ(N)−logΓ(h)−h log h
  +N[ψ(h)−ψ(N)]+h²/(h−1)。

親の暫定式を独立に再現した。期待値はE₀に依存せず、単にscale不変性によるもので、色付きnoiseや未知平均にも不変という意味ではない。

### N>2という条件

log項の期待値は正の自由度で有限だが、E[1/Q]にはn>2が必要。0<n≤2、m>0ではplug-inの期待test log scoreが−∞になり、この比較の期待差は+∞となる。これは小さいtrainエネルギーに対するplug-inの脆弱性によるもので、有限な改善値ではない。今回の通常の大きなNとは区別する。

## 5. 同じtrain/test長での漸近

数値評価ではなく、Stirling展開とdigamma展開を用いる。

 logΓ(2h)−logΓ(h)−h log h
 =(2h−1/2)log 2−h−1/(24h)+O(h^−3),

 2h[ψ(h)−ψ(2h)]
 =−2h log 2−1/2−1/(8h)+O(h^−3),

 h²/(h−1)=h+1+1/h+O(h^−2)。

主要項を足すと

 Δ(N,N)=(1−log 2)/2+5/(6h)+O(h^−2)。

特に極限は(1−log 2)/2。ここでlog 2<1なので極限は正。これはN標本のtest全体の合計log score差であり、per-sample差はΔ/N→0となる。

## 6. 評価長に依存する

train nとtest mの比τ=m/n=k/hを固定して両方を増やす場合、上の一般式から

 Δ(n,m)→[τ−log(1+τ)]/2。

τ>0ではlog(1+τ)<τなのでこの極限も正。τ=1でのみ今回の(1−log 2)/2になる。

これは「test長によらず普遍的に一定のgain」ではない。testが固定長でtrainだけ増えると、分散推定の不確かさが消え、差は0へ向かう。将来比較するときはtrain/test長、scoreの合計・平均の区別、testをjoint predictiveで評価するかを揃える必要がある。

## 7. 実測500組BMAとの接続と非接続

今回の依頼で与えられた実測要約は、

 W100のBMA−W平均：0.2458428743
 95% pointwise CI：[0.0895798859, 0.4242139010]

である。本書では保存ログ・計算経路を再読して検証しておらず、依頼で提供された値として記録する。

この実測BMAはここで導出したW-only Bayesとは同一ではない。追加noise familyの候補混合、shape parameterの積分、model weight、その他の仕様が関与し得る。そのため上の期待差を実測から差し引いて「残りがmodel averagingの寄与」とすることはできない。

仮にまったく同じ観測・score定義で中間のW-only Bayes scoreを別途得たなら、

 BMA−W_MLE
 =(BMA−W_Bayes)+(W_Bayes−W_MLE)

というscoreの算術分解は可能。しかし今回その中間値を実測していない。この等式は寄与の独立性、因果的分解、両項の正値性を保証しない。

今回の閉形式が具体化するのは、「BMA対plug-inという比較には、候補family選択だけでなく、共通scaleのparameter integrationという別の差が含まれ得る」という論点である。実測の改善がどれだけその効果なのかは未確認。

95% pointwise CIも、この期待式との同一性や寄与分解を保証しない。合計score・単位・train/test長などが揃うことを確認せず、数値を横並びの理論予測として扱わない。

## 8. 五仮想視点による過剰解釈チェック

以下は一人の紙上検討を五つの観点で点検したもので、独立五名の検証ではない。

1. **確率モデル担当**：「既存pitchの未知平均にも同じ式が適用できるか。」
   - 応答：できない。ここは平均0既知のWのみ。係数・F0・rank・covariance shapeの推定を一切含まない。
   - 再確認：train/testが独立で同じE₀という条件も必要。重複窓・分布変化にはそのまま使わない。
2. **測度担当**：「improper priorなのでpredictiveもimproperか。」
   - 応答：Q>0でtrain posteriorがproperとなり、その混合によるtest predictiveはproper。
   - 再確認：この事実はtrainのraw evidenceのproper性を回復しない。E₀をdE/Eから生成して期待値を取ったわけでもない。
3. **評価担当**：「Nが大きくても一定gainなら一標本当たり改善が残るか。」
   - 応答：残らない。ここはN標本の合計log scoreで、per-sample差は0へ向かう。
   - 再確認：test長/train長の比を変えれば合計score差の極限も変わる。毎回のrealized scoreが正とは限らない。
4. **実測担当**：「W100の改善はscale integrationで説明済みか。」
   - 応答：未確認。今回のW-only比較と実測BMA比較は異なり、中間scoreによる寄与分解も未実施。
   - 再確認：漸近式と提供された平均・CIの見た目の近さを、原因証明・校正結果・割合推定へ昇格させない。
5. **批評家**：「この結果は自然音声品質や新方式の採用を支持するか。」
   - 応答：この限定Gaussianモデルの期待log scoreを示すだけ。自然音声の知覚品質、F0精度、合成品質を評価していない。
   - 再確認：実装変更、追加実験、既存500組の条件変更を正当化する許可として扱わない。

## 9. 出典範囲と停止点

式はGaussian likelihood、inverse-gamma積分、独立χ²/Gammaのlog・逆数モーメントからの独立導出。新しい外部研究の実験的結論を引用していない。漸近も記号展開であり、小数値の評価はしていない。

実測要約は依頼で与えられた値だけを使い、再集計・再検証していない。閉形式と限定条件を確認したところで停止する。W-only Bayesの実測導入、BMA寄与分解、新実験は未実施。
