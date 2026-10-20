# 自然音声の短期予測比較：独立した数式・公平性レビュー

2026-10-21（日本時間）。設計文書の審査であり、実装、import、テスト、科学数値計算、音声取得、GitHub変更は行っていない。

## 判定

以下の明確化を計画へ取り込むことを条件に、**観測だけを用いる限定的な比較の設計として承認**する。実行やPMLからの採用変更を承認するものではない。現行 `USER_INSTRUCTIONS.md` と proper-scale 文書の第9・12節を確認した。現在のbase、旧500例、旧F0結果を今回の性能根拠へ流用しない。

最終照合：対応する `natural-heldout-predictive-plan-20261021.md` に、安定式、条件付き正規化、gridとsingle選択の意味、全尺度共通支持、欠落話者の扱い、stack trace付きログ、両方式でのb・σ²の積分が反映された。**設計上の必須修正は残っていない。** 実入力の所在・SHA確認と開始判断は未実施の別工程である。

## 1. 固定する観測と問い

- 固定120録音、16 kHz。560標本の非重複tileごとにT=先頭400標本、H=直後160標本。時刻はTで0..399、Hで400..559とし、同じ係数bを共有する。H側で位相を0へ戻さない。
- B=floor(録音標本数/560)。B<12なら全tile、B>=12なら floor(j(B−1)/11), j=0..11。端数は使わない。信号値・Hの得点による窓選別、再選択をしない。
- H0と、q=52..512、f=16000q/16384 Hz、K=1..10のH1を用いる。X,Wは各時刻のcos/sinの2K列。π0=0.3、各H1のπ=0.7/4610。これは生理的VUV率の推定ではない。
- c∈{0.1,1,10}をすべて報告し、Hで選ばない。時間filter、有色雑音、quadrature、波形合成・音質判定へ広げない。

目的は「同一component family内で離散modelの不確実性を残す予測」と「Tだけで最大重みの1 modelへ潰す予測」の比較である。single側も係数・雑音分散の不確実性を積分する。

## 2. 正規化された予測密度の完全な式

IGを p(s)=β0^α0/Γ(α0) · s^(−α0−1) exp(−β0/s), s>0 と定義する。TのRMSをr>0とし、y=T/r、z=H/rへ変換する。正規化座標でα0=3、β0=2c、b|s~N(0,s I/K)。元座標ではβ0=2c mean(T²)、priorのs平均はc mean(T²)である。

K>0について、p=2K、X∈R^(400×p)、W∈R^(160×p)と置く。

    A = K I + XᵀX
    μ = solve(A, Xᵀy)
    α = 3 + 400/2 = 203
    β = 2c + (||y−Xμ||² + K||μ||²)/2

trainingのplug-in log evidenceは

    ℓm = logΓ(203) − logΓ(3) + 3log(2c) − 203logβ
         − 200log(2π) + KlogK − log|A|/2.

元座標で同じplug-in値を表すなら−400logrを加えるが、model間で共通なので重みでは相殺する。rがT依存である以上、この式をT上で正規化された密度の変数変換と説明してはならない。

次に

    D = A + WᵀW
    e = z − Wμ
    δ = solve(D, Wᵀe)
    Q = ||e−Wδ||² + δᵀAδ
    log|S| = log|D| − log|A|,
    S = I160 + W A⁻¹ Wᵀ

とすれば、元観測HのLebesgue測度に関する密度は

    log p(H|T,m,c)
      = logΓ(283) − logΓ(203) − 80log(2πβ)
        − (log|D|−log|A|)/2
        − 283log1p(Q/(2β)) − 160logr.

これは自由度406、scale行列(β/203)Sの多変量Student-tである。scale行列をcovarianceと呼ばない。Tを固定すればrは定数であり、H側の−160logrは正当なJacobianである。

H0は別枝にし、β=2c+||y||²/2、trainingのKlogK・logdet項=0、予測のQ=||z||²、logdet差=0とする。K=0をKlogKや空行列の未定義操作へ渡さない。

A,DはK>0で正定値、β>0、Q≥0である。Qの式は eᵀe−(Wᵀe)ᵀD⁻¹(Wᵀe) と等価だが、非負項の和なので桁落ちを避けやすい。同様にβで yᵀy−(Xᵀy)ᵀA⁻¹(Xᵀy) の差を使わない。δᵀAδはCholesky因子による二乗normで計算できる。

## 3. 重みと比較の必須明確化

    wm(T,c) = exp(logπm + ℓm − logsumexp_j(logπj + ℓj))
    m* = argmax_m wm(T,c)
    p_mix(H|T,c) = Σm wm(T,c) p(H|T,m,c)
    p_single(H|T,c) = p(H|T,m*,c).

tie処理はmodelの固定順などで事前に定める。wm、c、grid、prior、窓選択をHから変えない。

- β0がT依存なので、wmは**経験ベイズplug-in evidenceを正規化したアルゴリズム上の重み**であり、独立priorから得た厳密なモデル事後確率・Bayes factorとは呼ばない。ただし各Tを固定したcomponent密度とその混合はH上で正規化される。
- 一般にはTだけでproper prior・model集合・重みを決めても条件付き正規化は保たれるが、今回の固定設計を事後変更してよいという意味ではない。同じHからc・model・scale・重みを選んでそのHを採点する操作は一般に正規化を保たず、評価リークになる。正しい条件付き密度の逐次積で元のjointを表す操作とは区別する。
- 同じV0=I/KとT由来scaleをT・joint・Hで保持する。joint側でdesign依存priorやRMSを作り直してはならない。
- Hの160点はb,sを積分した後は独立ではない。160個の一変量周辺t密度を掛ける代用は不可。
- singleは4611個の離散modelの最大重み選択であり、H0/H1を先に選ぶ方式ではない。H1総重みが高くてもsingleがH0になり得る。grid細分化はH1各点の重みとsingleの意味を変える。線形Hzでの一様priorは対数F0で一様ではない。
- 各supported窓で Δ=log p_mix−log p_single ≥ log w_m* ≥ −log4611。これは記号的な下界であり、混合が必ず勝つ保証でも、品質の保証でもない。

## 4. 有限精度・除外・集約の停止条件

- 二乗和のunderflowを避けるscale-safe RMSを用い、元Tが厳密な全零かを先に区別する。r=0のTは全model・全c共通の `calibration_zero` とし、床値を入れない。非零Tの計算underflowを全零と偽装しない。
- float64、Cholesky、triangular solve、logΓ、log1p、logsumexpを用いる。逆行列を明示形成しない。小行列A,Dの因子は同じdesignで共有できる。隠れたjitter、clip、floor、失敗componentの黙った削除・再正規化をしない。
- 非有限値、Cholesky失敗、normのoverflow、負のQ等は録音・tile・q・K・c・演算箇所とstack traceを残す。数学的unsupportedと計算失敗を分ける。Hに依存した計算失敗を除外して、完全な120録音比較が成立したように報告しない。
- 各録音内で共通supported窓のΔ/160を平均し、次に話者内で録音平均、最後に固定40話者を等重みで平均する。長い録音や窓数が多い録音へ暗黙に大きな重みを与えない。話者対応と不足時の集約規則を事前固定する。
- cごとに録音・話者・窓の予定数、成功数、全零除外数、計算失敗数を報告する。窓が0の録音・話者を0点で埋めない。固定対象に欠落があれば、その欠落と比較可能範囲を主結果に併記する。母集団推論やbootstrapへ広げず、固定資料上の記述結果とする。

## 5. 許される結論

これは35msを通じて同じf,b,sが続く、条件付き白色誤差モデルによる次10msのforecastである。実音声の有色残差、周波数変化、振幅変化、発声境界はモデル違反となり得る。非重複tileでも、同一録音・同一話者の結果が独立になるわけではない。

得点改善が示すのは、この固定family・prior・grid・観測区間における分布保持の予測上の価値だけである。正しいF0・VUVの同定、生理的確率校正、合成品質、現baseより良いvocoderを示さない。広いparameter不確実性には密度の正規化項による罰則もあるが、モデル違反を分布の広がりで吸収して得点が上がる可能性は残る。

### 確認したリポジトリ資料

- [現行ユーザー指示](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/418fb5f029b7e43e58665df4be958f1125416318/USER_INSTRUCTIONS.md)（blob 7d367de8f14555b64ee530e71a5a56af0596c073）
- [proper-scale導出](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/418fb5f029b7e43e58665df4be958f1125416318/experiments/2026-10-20/pitch-history-contrast/research/proper-scale-colored-harmonic-evidence-20261020.md)（blob 32ce460fa6282a6f714943f05d3fe2978ee5f6a4、第9・12節）
