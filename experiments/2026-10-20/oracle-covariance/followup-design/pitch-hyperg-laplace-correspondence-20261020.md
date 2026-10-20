# 現行 pitch の hyper-g と log-g Laplace：対応範囲

2026-10-20。文書・ソースの読取りと代数照合のみ。候補コードの実行・import、tests、数値計算、Git変更はしていない。新prior・新F0モデルを採用せず、BMA条件も変更しない。

## 結論

**新導出の記号δは、既存設定のδ=3に新しいprior選択なしで対応付けられる。現行式は g の積分を z=log g に変数変換し、Jacobian dg=g dz を含めた一次元Laplace近似である。**

ただし、exact hyper-g積分と現行の近似値は同一ではない。新導出の μλ(dE)=E⁻¹exp[−λ/(2E)]dE はregularized codの形式的逆解釈であり、著者がこのscale priorを指定したと確認できたわけではない。

## 1. 確認した一次資料・現行契約

1. [Shi et al. 著者本文](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)：式(12)はnoise varianceのinverse-scale prior、式(13)は β|E,g ∼ N(0,gE(ZᵀZ)⁻¹)、式(14)はπδ(g)=(δ−2)/2 (1+g)⁻δ/²。式(24)は係数・scale・gの周辺化、式(25)は₂F₁表現、式(26)は共通null量、式(29)はH0を含む状態正規化。Laplace代替は式(28)後の本文で説明される。
2. [固定著者class](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m)：gPriorParam=3、varSpeech=5e−6。cod=costs/(xᵀx+N varSpeech)をhelperへ渡す。varSpeechのコメントはregularization parameterと説明し、μλのpriorとしては説明していない。blob SHA 8f705773dc09b4dcf8bacfa518557ec30cb8c1d3。
3. [固定著者helper](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/computePitchLogLikelihood.m)：v=1、w=(N−2K−δ)/2、u=N/2を渡し、log[ĝ(δ−2)/2]+w log(1+ĝ)−u log[1+ĝ(1−r)]+½log(2πτ)を返す。blob SHA 90ec7bf3297f5769a92aba72cc7ad279dba78d91。最初にprivateなしのpathを読んだ際は404だったが、上記の実pathは取得できた。
4. [現行main実装契約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/implementation-contract.md)：N=400、K=1..10、DCなし、white、δ=3、λ=N varSpeech=.002。同じhelper式を安定正根・log1p等で評価する契約。blob SHA e3e9a012fb6412265e900ac62fb214476494a701。これはGit公開契約の確認であり、非公開の実行package全ソースを今回再監査したという意味ではない。
5. ローカル pitch-log-static-review-20261020 のreview・runnerを読んだ。このrunnerは保存済みlogBFを読むだけで、g積分を再計算しない。そこでδやLaplaceを新たに決めているわけではない。

## 2. 新導出との代数照合：独立推論

regularized-pitch-kernel-derivation-20261020.mdを全文読取りした。C=I、d=2K、T=yᵀy、r=J/(T+λ)、u=N/2と置く。そのexact形式BFは

 B(r)=kδ ∫₀∞ (1+g)^w [1+(1−r)g]⁻ᵘ dg,
 kδ=(δ−2)/2,  w=(N−d−δ)/2。

z=log g、dg=eᶻ dzに変換すると

 B(r)=∫ℝ exp[h(z)]dz,
 h(z)=log kδ+z+w log(1+eᶻ)−u log[1+(1−r)eᶻ]。

従ってh′=0は

 1+w g/(1+g)−u(1−r)g/[1+(1−r)g]=0。

分母を払えば a g²+b g+1=0、

 a=(1−r)(1+w−u),
 b=(u−1)r+2+w−u。

これはhelperのv=1に一致する。さらに

 −h″(ẑ)=u(1−r)ĝ/[1+(1−r)ĝ]²−w ĝ/(1+ĝ)²=τ⁻¹。

ゆえにlog B≈h(ẑ)+½log(2πτ)が現行式そのものになる。τはlog-g座標の局所曲率逆数であって、g座標のvarianceそのものではない。ĝもdgに関するg posteriorのmodeとは限らない。Jacobianなしでgのmodeと曲率を求めるLaplace近似は別の近似になる。

δ=3の既存値を代入するとπ(g)=½(1+g)⁻³/²、kδ=½、d=2Kなのでexact積分は

 B_exact(r)=1/(2K+1) × ₂F₁(N/2,1;K+3/2;r)。

これは「既存prior値に対応したexact参照式」であり、実装変更の提案ではない。新導出の記号δの自由度を既存結果に合わせて最適化したものでもない。

## 3. 一致を限定する定数・測度・状態

- **hyperprior正規化**：½はH1側にだけ現れるため、H0とのoddsでは落とせない。log gは変数変換のJacobianであって、余計なg priorではない。
- **Laplace補正**：½log(2π)と½log τも保持する。Kやrに依存する曲率を省いたprofile値はevidenceではない。exact積分への置換は近似誤差を変えるので、同じ保存ellの算術比較でもなくなる。
- **scale・null量**：固定C,N,λでは Γ(N/2)π⁻ᴺ/²|C|⁻¹/²(T+λ)⁻ᴺ/² が共通で、BFのH0を1にできる。異なるCの比較・shape周辺化ではこの因子は一般に共通でなく、先に捨てられない。原著のλ=0尺度と新導出のλ>0尺度は別である。
- **係数priorの正規化**：normalized g-priorがGram determinant・E次元の相殺を担う。未知βをprofileしたRSSへの置換や次元ごとのflat priorでは同じ式にならない。δ=3の一致だけでcolored Cへの新prior採用は正当化されない。
- **離散状態**：現行初期質量はH1各セル .7/(461×10)、H0=.3。BFにこれらのpriorを掛け、H0と全(f,K)セルを同時に正規化して初めてposteriorになる。H1内だけのsoftmaxではない。有限grid PMFへΔHzを追加しない。
- **時間状態**：予測U=.7 AᵀQB+.4p0R、u0=.3(1−p0)+.6p0、行正規化A/B、H0<.5時のみR更新という機構は、単一frameのexact BF導出には含まれない。過去posterior依存も含めて同一条件にしなければfiltered出力は一致しない。
- **観測・失敗条件**：global RMS処理・窓とpaddingを同じにする必要がある。全零でも新導出のBFは定義できるが、現行はenergy/400<1e−10を欠測skipする。これをH0 posteriorへ置換しない。著者NaN→−∞と現行の停止契約にも差がある。現行はclipやridgeを許していない。

結局、①既存δ値、②固定white regularized g-kernel、③log-g Laplace式の代数的一致は確認できる。一方、exact積分値、浮動小数点同一性、全frame状態列、proper raw evidence、自然音声calibrationまでの一致は確認していない。

## 4. 5仮想視点による確認と批評

以下は机上の五視点であり、独立五名の査読・実測ではない。

1. **出典担当**：「δを今決めたのでは？」→ main契約と固定著者classの両方に3がある。今回行うのは既存値の照合のみ。
2. **測度担当**：「helperのg係数は別priorでは？」→ dg=g dzのJacobianで再現される。π(g)dgとπ(eᶻ)eᶻdzを混同しない。
3. **近似担当**：「ĝがあるならgを最大化しただけでは？」→ log-g曲率補正を持つLaplace積分近似である。ただしexact ₂F₁値との誤差は未測定。
4. **状態担当**：「BFが一致すればposteriorも一致する？」→ 同じprior・全状態正規化・遷移・skipと記憶が必要。保存logBF runnerはこの後段の算術比較である。
5. **批評家**：「μλ解釈で現行が完全にBayesianと証明された？」→ 否。正則化kernelを説明する形式的共同測度の一つであり、原著の意図、proper prior predictive、colored extension、calibrationの証明ではない。参照式の一致を新方式採用やBMA条件変更に昇格させない。

停止点：δ=3の来歴とlog-g Laplace測度、保持すべき定数・状態契約を特定した。実装・数値精度評価・prior採用は別の未実施事項として残す。
