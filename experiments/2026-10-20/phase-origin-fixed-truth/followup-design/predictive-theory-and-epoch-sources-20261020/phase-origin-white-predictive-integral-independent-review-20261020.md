# W共通位相のpredictive積分：独立数学レビュー

2026-10-20。対象 `phase-origin-white-predictive-integral-reference-20261020.md`。文書読取りと紙上代数のみ。候補実行・import、数値積分、新測定、tests、現在500studyへの変更は行っていない。

## 結論

**重大な誤り・修正必須の式は見つからなかった。** proper円周priorによる共有位相のposterior predictiveとして正規化され、六係数の積分表示とriskの限定は整合する。採用未決定の理論参照に留め、現在の二score研究へ第三条件を追加しない。

## 独立確認

1. **log尤度の六係数**  
   cos(α+β)の展開からA_h=a_h C_h/s、B_h=−a_h S_h/sとなる。q²の完全周期和がNであるためκ_Dも正しい。次数3なのはlog尤度の位相依存部であり、exp(T)そのものではない。丸めqの目的へ次数保証を移していない。

2. **共有φと正規化**  
   共通未知φについてlikelihoodを掛けてから一回積分するので、joint evidenceの引数はt_train+t_test。train evidenceとの比ではκ_trainが消え、exp(κ_test)J(t_train+t_test)/J(t_train)となる。dφの全質量1、x座標でdx/(2π)、Jの正・有限上界下界、非負積分の交換によるtest密度積分1はいずれも正しい。分子のtest係数は密度の評価点であり、testによる予測手続きの選択ではない。

3. **独立φ・OLSとの差**  
   独立なφ_train、φ_testならtrainでtest位相を学べず、predictiveはZ(test)。共有clockモデルとは異なる。既知sのWでは理想global OLS=ML=一様priorのmodeだが、mode選択と全円周混合は別。実装されたnoncertified rootがこの理想modeと同一とは保証しない。Jensenが比較するのはlog平均densityと平均log densityであり、modeのtest scoreとの点ごとの順序ではない。

4. **full-circle rankと局所rank**  
   m(φ)−a0·1は、観測grid上の三調波のcos/sin計六列の張る空間に入る。したがってCov_post[m(φ)]のrank≤6。位相parameterが一次元でも曲線全体の共分散rankが1になるとは限らない。局所線形化だけなら追加共分散はd Var(δ)dᵀというrank≤1型となる。さらにpredictiveを単一Gaussianとして近似するには、局所posteriorのGaussian近似等が必要であり、moment一致だけでは厳密混合と同じ分布にならない。本文の区別は適切。

5. **riskとoracle**  
   階層的prior平均でのlog-score差はE_train KL(p_PP||g)で非負。固定φ0の各train条件付きでは、oracleに対する差が−KL(p_φ0||g)で非正。この二式は整合するが、p_PP対plug-inの各固定truth・各実現の順位をそれだけで決めない。equivariance等による追加論証を未採用とする留保も正しい。適用には正規化されたgと期待値の存在条件が必要で、本文は有限期待を条件にしている。

## 解釈上の停止線

有限・多峰・flatな理想likelihoodでも積分は存在することと、有限精度quadratureの誤差保証は別。現在の固定truth、丸め生成、運用上の失敗選択にprior平均の優越を自動適用しない。

冒頭の「開始指示済み」は過去の経緯として読む。親からの最新状況は各worker終了後、終了確認エラーについて成果保全中であり、本レビューは終了成功・科学成功を新たに認定しない。既存結果の再評価・第三score・新study採用へ進まず、理論レビューだけで終了する。
