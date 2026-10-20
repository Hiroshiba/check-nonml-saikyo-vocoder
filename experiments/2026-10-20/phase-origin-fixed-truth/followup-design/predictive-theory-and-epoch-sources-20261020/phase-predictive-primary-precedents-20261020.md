# 位相posterior predictiveの一次資料による位置づけ

2026-10-20。本文を確認した一次資料は以下の2点に限定した。これは紙上参照資料であり、現在の500pair・oracle/OLS二score契約を変更せず、posterior predictiveの採用も決めない。

## 1. Gaussian観測から共通位相を積分する先例

**G. Larry Bretthorst (1992), “Estimating the Ratio of Two Amplitudes in Nuclear Magnetic Resonance Data,” Maximum Entropy and Bayesian Methods, Seattle, 1991, pp. 67–77.**

- 著者公開原文：https://bayes.wustl.edu/glb/me91.pdf
- 書誌確認用の著者一覧：https://bayes.wustl.edu/glb/bib.html （項目18）

**原典で確認したこと。** §2、式(2), (4), (6), (7)は、周波数・減衰率の異なる二つの減衰sinusoidを実部・虚部のquadratureで観測するモデルで、両成分が同じ加算位相θを持つ。§3、式(19)–(21)は共通分散σ²のGaussian noise/likelihoodを置く。§3は位相を含む一様priorの範囲・定数を比例定数に吸収し、§4、式(34)–(37)はθを積分して、残る積分の被積分関数に

    I₀(AY/σ²),
    Y = √[(R₁+rR₂)² + (I₁+rI₂)²]

を得る。従って、**Gaussian spectral inferenceで未知位相を積分消去する先例は確認できた**。この論文の目的は振幅比の周辺posteriorであり、今回のtrain/test posterior predictiveではない。さらに周波数・減衰率の積分は同節で近似を要するとされており、全計算が厳密閉形式という意味ではない。

**今回と同一視しない点。** 原典は各成分に同じθを加えるquadratureモデルである。今回の既知実波形qの時間原点はh次調波にhφとして入り、log likelihoodは共通の一変数φに関する次数3の三角多項式になる。原典の単一I₀も、単一sinusoidでのI₀公式も、今回のJを調波ごとのI₀の積へ置換する根拠ではない。原典は規格化済み円周priorによる今回のevidence比も提示していない。

## 2. log scoreのpropernessとBayes最適性

**Tilmann Gneiting and Adrian E. Raftery (2007), “Strictly Proper Scoring Rules, Prediction, and Estimation,” JASA 102(477), 359–378.**

- 著者公開原文：https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
- 出版社DOI：https://doi.org/10.1198/016214506000001437

**原典で確認したこと。** §2.1、式(1)（p.360）は真の分布での期待scoreを最大化するpropernessを定義する。§2.2、式(7)（p.361）はscore差による非負divergenceを定義する。§4.1、式(19)と直後（p.365）はlog p(ω)のstrict propernessおよび対応するKL divergenceを明記する。§7.1、式(52)の直後の無番号式（p.372）は、過去データに条件づけた予測分布をlikelihoodのposterior混合として記載する。

**今回への適用としての推論。** この一般的性質に、共有φとproper uniform circle priorを持つ今回の階層モデルを代入する。train=Y、test=Zと書き、Q_Y=p_PP(·|Y)とすれば、有限な期待値の下で

    E[log p_PP(Z|Y) − log g(Z|Y)]
      = E_Y[KL(Q_Y || g(·|Y))] ≥ 0.

これはpriorからφを引く階層モデルの期待値であり、同じpriorに関するposterior predictiveのBayes最適性を与える。原典に今回のq・3調波・N=4096の式があるわけではなく、**既存のpropernessを条件付き分布へ適用した本ノート側の特殊化**である。式(52)の周辺で述べられるprequential scoreの漸近同値性も、今回の有限標本での改善保証ではない。

## 3. 既存ノートに帰属させる部分と停止線

- 共通位相を一度だけ積分するJ、六係数の加算、`exp(κ_test) J(t_train+t_test)/J(t_train)`、有限性・正規化の具体的証明は、既存のpredictive-integralノートの導出である。
- 連続直交群T_δ、厳密global OLSのa.s.一意性・equivariance、riskのφ非依存性、そこから全固定φの反復期待riskへ移す厳密優越は、既存のequivariance-riskノートの追加論証である。確認した2原典がこの特殊定理を直接証明したとは記さない。
- 原典の先例・一般定理は、実500の改善、各train条件付き・各test実現の優越、binary64・位相丸め・数値gate・成功subsetへの移植、W以外への拡張を保証しない。

確認範囲は両原典の上記箇所。Bretthorst (1988)の書籍PDFは取得がtimeoutとなり、本文未読のため根拠に採用しない。Aitchison (1975)は出版社の要旨のみを確認したが、本文の定理・条件は未確認であり、その主張を根拠に補充しない。調査はここで止めた。

既存ノートの読取り、公開論文の閲覧、この文書の保存だけを行った。コード・モデル・データの取得や実行、数値積分、実験・再評価、申請、Git変更は行っていない。
