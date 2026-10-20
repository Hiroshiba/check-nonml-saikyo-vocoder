# 雑音 covariance と確率的 F0/H0 を接続する条件

2026-10-20。資料読取りと数理上の境界整理のみ。実装・コード実行・計測・tests/smoke・Git変更・prior採用は行っていない。既存500 pairの再解析仕様もPML baseも変更しない。

## 結論

既知qのoracle covariance evidenceを、未知平均・未知F0・未知harmonic次数のevidenceへそのまま移せない。接続に必要なのは、同じ元観測に対して平均と共分散を同時に定義し、H0にも比較可能な雑音仮説を与えた周辺尤度である。現在のnoise weightとF0/H0 weightを掛け合わせても、その共同モデルにはならない。

以下で「確認事実」は今回読んだ資料の記述、「独立推論」はその記述からの数学的考察である。後者を既報の実験結果とはしない。

## 1. 既存F0/H0が実際に扱うもの：確認事実

### 原著

Shi et al. (2019) の本文式(6)–(14)、(23)–(29)を確認した。H1は y=Z(f,K)β+v、H0は y=v、vはwhite Gaussian、covarianceはσ²Iである。βは未知であり、条件付きGaussian g-prior（covariance gσ²(ZᵀZ)⁻¹）、gのhyperprior、noise scaleの1/σ²を用いて周辺化する。F0・K・有声状態を離散状態として共同で正規化し、時間遷移を持たせる。§VIにはprewhiteningがあるが、それは任意の未知colored covarianceを共同で積分する式ではない。[一次本文](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)

### このリポジトリの固定診断

- main READMEは25 ms、16 kHz、K≤10、50.78125–500 Hzの有限診断と宣言。H0はharmonic/white候補内の相対支持であり、生理的VUVや雑音電力ではない。
- implementation-contractはwhite経路、DC列なし、観測平均の中心化なし。各(f,K)の射影量Jを計算し、r=J/(yᵀy+N varSpeech)、varSpeech=5e−6を用いたg積分のLaplace局所log比を使う。βを既知qで置き換えたモデルではない。H0のlog比は0で、全候補と一緒に正規化する。
- このregularized codは原著の非regularized説明比と同一ではない。Kは単に最大次数を選ぶのではなく、候補質量・次数prior・遷移の対象。window overlapや時間priorによる集中を独立証拠増加とは読まない。

出典：[README](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/README.md)、[実装契約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/implementation-contract.md)、[直接射影設計](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/direct-projection-design.md)、[解釈レビュー](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/interpretation-review.md)。今回確認したREADME blob SHAは5c0525e13f6a53c4b16cd8fc55248e0153185a9c、実装契約はe3e9a012fb6412265e900ac62fb214476494a701。main URLは可変。

## 2. Colored-noise一次研究から言える範囲

Quinn, Nielsen & Christensen (2021), “Fast algorithms for fundamental frequency estimation in autoregressive noise”, DOI 10.1016/j.sigpro.2020.107860について、出版社の抄録・highlights・導入公開部分と著者大学記録を確認した。harmonic regressionのF0とARパラメータのjoint ML、harmonic/AR両次数のBIC型選択、exactまたは漸近的に同等な高速計算法を扱う。これをF0/H0の厳密なBayesian周辺posteriorと呼ぶ根拠にはならない。[出版社](https://www.sciencedirect.com/science/article/pii/S0165168420304047)、[著者大学記録](https://researchers.mq.edu.au/en/publications/fast-algorithms-for-fundamental-frequency-estimation-in-autoregre/)

今回は論文全文を取得していない。既存レビューの[著者accepted manuscriptリンク](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/paper/acceptedManuscript.pdf)は今回のWeb取得でInternal Errorとなった。したがって初期状態、有限窓、padding、exactの厳密な対象を今回は独立再検証していない。

リポジトリの[colored-noiseレビュー](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/2026-10-20/probabilistic-pitch-diagnostic/research/colored-noise-future-review.md)は、標準著者helperがF0でprofileした分散からBIC由来の次数重みを作ること、およびexactが定常Gaussianの厳密有限窓周辺尤度を意味しないことを既確認として記録している。本書ではこれを既存レビューの報告として引用し、新たな全文確認と混同しない。同レビューが挙げるGodsill–DavyのBayesian AR先行例は参考位置付けに留め、今回は周辺文献の網羅探索や追加方式選定を行わない。

## 3. Oracle dE/Eを移せない理由：独立推論

記号を分離する。ここでEはnoise総分散、x=y−qは既知qを引いた残差、Kはharmonic次数とする。pitch契約のE=yᵀyやnoise実験の周期数Kとは別。

### 3.1 共通の残差方向が失われる

既存noise設計は同一q、同一N、同一残差xに対しΣ=E Cηを比較する。形式積分は

  m*(x|η) ∝ |Cη|⁻¹/² (xᵀCη⁻¹x)⁻ᴺ/²。

共通の半径因子を除けば、u=x/||x||という一つの観測のproperな球面密度に対応する。ただし元x空間のproper prior predictiveではない。

未知qを候補ごとにfitするとx(f,K,η)=y−Z(f,K)β̂となり、異なる候補が異なる残差方向・半径を作る。以前の共通半径因子は相殺できず、fit残差の密度は元yのevidenceではない。固定線形fitでも残差covarianceはRΣRᵀへ射影され、一般にrankが落ちる。F0や次数を同じyから選べば、その選択も追加される。これは「推定が禁止」という意味ではなく、観測と周辺化の再定義が必要という意味である。

### 3.2 未知meanを積分すると次数依存の項が出る

説明用にCを既知、Zをfull rank、d=rank Zとする。flatなβ測度でGaussianを積分した形式式は、S=(y−Zβ̂)ᵀC⁻¹(y−Zβ̂)として

  |C|⁻¹/² |ZᵀC⁻¹Z|⁻¹/² E⁻⁽ᴺ⁻ᵈ⁾/² exp[−S/(2E)]

に比例する。dE/Eも積分すればSの指数は−(N−d)/2になる。元の−N/2へRSSを差すだけでは足りない。しかもflat βの任意定数はdが違うモデル間で自動的には相殺せず、この形式式を次数比較の推奨priorにはしない。既存pitchのproper conditional g-priorはこのflat測度とは別物である。

一方、適切に正規化したscale連動β priorならN/2の形が残る場合もある。したがって「未知meanならdE/Eが常に禁止」も誤り。必要なのはβ・scale・shapeの共同測度を定め直し、H0との定数・proper性を確認することである。本書ではpriorを選ばない。

### 3.3 qはmeanだけでなくnoise geometryにも入る

S/Jはg=q、h∝−q′の方向を使い、Vは周期位相を使う。未知q/F0なら平均とcovarianceが同じ未知量に依存するため、独立の二つのevidenceとして掛けられない。H0にはharmonic meanのqや有声clockが存在しないので、S/J/VをそのままH0へ移す意味も未定義。H0に便宜的clockを与えるなら、それ自体が別のlatent構造と測度を要する。

### 3.4 比較のための最低限の契約

同じ元サンプル、窓・padding・初期状態の定義を保持し、Gaussianのlog determinantとquadratic formを両方含める。未知meanとcovarianceの依存、F0・K・H0の支持と正規化、noise scaleの単位・測度を明示する。ARならH0側のAR-onlyも公平な比較対象にする。Wを含めるだけでは既存regularized cod＋Laplace式の回収は保証されない。固定varSpeechの扱いも一致が必要である。

H0質量、F0不確かさ、noise family重みは異なる対象であり、どれもaspiration率・合成noise電力への直接変換ではない。oracle成功は自然音声や未知位相での識別成立を含意しない。

## 4. 最小次段階の問いは一つだけ

**「F0とharmonic次数をまだ固定し、mean係数βだけを未知にしたとき、WとAを同じ元観測上で比較する正規化された周辺尤度には、既知qの方向evidenceから何が追加で必要になるか？」**

これは接続可能性を紙上で点検するための一問であり、新モデルの採用や実装計画ではない。β prior・scale priorの値は選ばず、必要な測度・正規化項・white極限・初期状態条件を列挙できたところを停止点とする。F0/K探索、S/J/Vの未知clock化、既存500 pair再計算、PML変更へは進まない。

## 参照した既存設計

- cyclic_noise_identification_design_20261020.md：既知平均・共通oracle clock、S/J方向、有限窓共分散、PMLの測定phase原点未定義という境界。
- noise-model-evidence-design-20261020.md：共通E、dE/Eの形式積分とproper方向evidenceの区別、共通q・同一測度という適用条件、未採用の参照priorと500 pair再解析案。

上記二文書は本書の前提であり、内容を変更していない。新しい計算結果・校正結果・採用判断は追加していない。
