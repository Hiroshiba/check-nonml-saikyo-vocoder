# 音量・noise prior校正の一次資料確認

2026-10-20。PMLを唯一のbaseとして維持する。文書・著者コードの読取りのみで、実装、アルゴリズム実行、科学数値計算、実験、Git変更、prior値選択は行っていない。対象は以下の2論文とその著者配布コードに限定した。

## 結論

今回の固定proper IG(α,β)＋hyper-gは、Shiの「noise variance priorをそのままproper化しただけ」ではない。著者実装のvarSpeechは、音量正規化後の座標に置かれた経験的正則化である。AR-MLのnoise varianceも、同じ観測窓をfitしたexcitation varianceの推定値であり、外部校正されたproper variance priorではない。

この2系統から、未知raw音声用のα・β・δ・noise-shape priorを決める直接の校正規約は得られない。原著のF0性能を今回のraw evidenceやVUV確率の性能に転用しない。

## 1. Shi et al. (2019)：本文で分かること

[著者accepted manuscript](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)、[DOI](https://doi.org/10.1109/TASLP.2019.2930917)。

- §III、式(5)–(9)：H0/H1ともwhite noise分散σ_n²を用いる。
- §IV-A、式(11)：IGは p(σ_n²|σ_{n−1}²)=IG(c,dσ_{n−1}²) という時間遷移の候補。未知の前時刻分散へ条件付くので、固定外部βのpriorとは違う。この経路は追求せず、式(12)の独立Jeffreys priorへ簡略化する。
- §V、式(25)–(28)：係数・分散を積分し、R²の分母はy_nᵀy_n。ここにvarSpeechはない。
- §VI：colored noiseにはnoisy signalからMMSEでnoise PSDを推定し、フレームごとにLP prewhiteningする。

したがって、本文の採用モデルにproper固定IGのα・β校正は「ない」。今回のH0/H1共通colored covariance priorの校正も、この導出には「ない」。文献全体に先行例が存在しないという意味ではない。

## 2. Shi著者コード：いつ、何のデータを使うか

確認版：LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model、commit `ad9a3fcfe60d2e97a635a92c2076ff1978ae3697`。以下はMATLAB経路であり、C++・リアルタイムdemoの全経路同等性は未確認。

### 音量基準は入力全体から作る

[private/BF0NLS.m L56–92](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/BF0NLS.m#L56-L92)

16 kHzへresample後、フレーム分割前に入力全体のRMSを求め、平均二乗が3.1623e-5になるよう倍率を掛ける。コードのコメントは「−45 dB loudness」だが、処理は波形のRMS正規化であり、物理音圧や知覚ラウドネスの校正を確認したわけではない。白色・coloredの配布exampleはいずれも加算後のNoisySignalをこの入口へ渡す。

この経路の尺度はclean speechだけからでも独立学習データからでもなく、入力された録音全体から求まる。フレームに対して未来のサンプルも含み得る。一方、クラスを直接使う場合には入口のこの正規化が自動で行われるとは言えない。

同じprefixでも後続ブロックによって全体RMSが変わり得るので、この入口について「同じprefixなら同じ正規化観測」とは一般に言えない。これは原著全体のstreaming/causal性を断定するものではない。今回の人工C対照で事前に共通理論scaleを使う設計は、この全録音RMS処理の再現ではない。この対照設計は依頼の既存文脈であり、今回実験を再確認・再計算した事実ではない。

### varSpeechはnoise分散推定ではない

[BayesianfastF0NLS.m L40–52、L290–294](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m#L40-L52)

コメントは入力SNRに応じる正則化と説明し、高SNRでは大きい値が経験上よいとする。コードでは固定値5e-6を持ち、codの分母を xᵀx＋N varSpeech とする。調べた経路には、この値を現在フレームから推定・更新する処理はない。gPriorParamの既定値もあるが、これらは著者実装の事実であり、今回のprior値への採用提案ではない。

SNRから値を決める定量的規則、校正データと評価データの分離、未知raw録音のgainへ移す規則は確認できなかった。値の単位は式から振幅二乗相当と読めるが、noise-only varianceとしての統計的意味は与えられていない。

### noise PSD推定と正則化を分ける

[同クラス L252–263](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m#L252-L263)は、現在フレームのFFT powerをstate付きnoise estimatorへ渡し、推定PSDからLP filterを作る。filter後には元フレームと同じノルムへ戻す。したがって、PSD推定とvarSpeechは別物である。

[同梱estnoiseg_orig.m L122–134](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/estnoiseg_orig.m#L122-L134)は初回入力のpowerから初期化し、現在powerを使って更新してからnoise推定を返す。この呼出側は1フレームずつ渡すため、初回もその1フレームに依存する。以後は過去state＋現在フレームに依存する。外部noise校正を読み込む経路ではない。一般的な関数コメントの初期区間長を、この呼出側が将来64 msを待つ証拠にはできない。

## 3. Quinn / Nielsen / Christensen (2021)：AR-ML

[出版社記録](https://www.sciencedirect.com/science/article/pii/S0165168420304047)、[著者がアップロードした本文](https://www.researchgate.net/publication/347434657_Fast_algorithms_for_fundamental_frequency_estimation_in_autoregressive_noise)、[著者コード](https://github.com/jkjaer/fastF0ArMl)。

本文§2、式(2)のσ_u²はAR excitationの分散。§3、式(8)–(9)では同じ観測区間からAR係数・sinusoid係数をfitし、残差二乗和を元の標本数Tで割る。窓外をzeroとするautocorrelation methodであり、今回の定常初期分布込みAR covarianceとは異なる。式(10)–(11)は次数選択のBIC系であり、proper IGとnoise-shape priorを積分した比較ではない。

著者コードの確認版はcommit `27ec2ba9c56b1c862d4fb876c734d2240477a614`。

- [estimate.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/estimate.m)：入力窓を保存し、末尾に最大AR次数分のzeroを追加してobjective・次数・parameterを推定する。ここにRMS正規化はない。
- [computeObjectiveNaively.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/computeObjectiveNaively.m)：同じdataVectorからdata powerと線形fitの差を作る。返値を[estimatePitchArParameters.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/estimatePitchArParameters.m)がestExVarとして返す。
- [pitchArBicModelComparison.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/pitchArBicModelComparison.m)：pitch次数0を含め各AR次数を走査する。変数名bayesFactorでも、実体は最小excitation varianceと次数penaltyから作るBIC型scoreを正規化したもの。名前だけでproper raw evidence・校正済確率とは呼べない。

H0にもAR候補を許すという構造上の参考はある。しかしH0/H1で同一のproper noise-shape priorをどう学習・校正するかは、確認した採用推定器には「ない」。各実験スクリプトの前処理全件や、他版の実装差は「未確認」。

取得経路の限界：GitHub配布PDFはwebのcontent-type制約、大学のpreprintリンクは403で取得できなかった。これを根拠に本文未確認とはせず、著者名付きで公開されたResearchGate本文の§2–3を確認した。拒否された経路への再試行はしていない。

## 4. 今回の固定契約に必要なもの

以下は原著の提案ではなく、既存proper-scale導出を保つための整理である。

1. 観測の単位・録音gain・前処理を固定する。βは振幅二乗単位。単位変更 y′=cy に伴う β′=c²β と、βを固定した物理gain変更は別。全録音RMS正規化はさらに別のデータ依存変換で、raw振幅の証拠を保持する契約とは違う。
2. Eを平均周辺noise分散とするかexcitation varianceとするか固定する。今回のAR(1)では後者はE(1−a²)。AR-MLの推定値をEやβへそのまま代入できない。
3. α・β・δ・Πの出所と情報利用時点を固定する。独立校正データを使うなら対象録音・個体・機器・gainとの適用範囲、学習/校正/評価の分割と凍結時点を記す。過去情報を使うなら予測時点までの条件付けとして記す。どちらもまだ選ばない。
4. βを同じ評価窓から選び、それを固定proper prior predictiveと称さない。正規化証明は固定priorについてであり、β(y)への置換を含まない。著者の実用的前処理がこの置換を正当化するわけではない。
5. H0/H1で共通にするnoise family・scale/shape prior・初期状態と、C依存g-priorの意味を明記する。priorを同じにすることと、同じ窓からそれぞれ最適fitすることを混同しない。

## 停止線

先行実装との関係を確認する問いはここで閉じる。未知raw音声に対する数値prior、経験的gain基準、校正データの代用を選ばない。新しい仮説・実験提案は追加しないため、仮想役による追加hypothesis議論は行わない。外部校正情報や評価対象の仕様がないまま、実装・比較・PMLからの採用変更へ進めない。
