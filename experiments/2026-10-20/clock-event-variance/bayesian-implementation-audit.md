# Bayesian harmonic pitch tracker：静的実装監査の要約

2026-10-19 UTC（2026-10-20 JST）。公開ソースの読取りに基づく。ビルド・実行・速度・音質・校正の確認ではない。

固定対象：

- [LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model、ad9a3fc](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/tree/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697)
- [jkjaer/fastF0Nls、5047004](https://github.com/jkjaer/fastF0Nls/tree/5047004bc2e1fb1a141da5ec5be0d09e5965a2bc)

## 取得量の契約

| 対象 | 得られる量 | 注意 |
|---|---|---|
| Bayesian MATLAB `estimate` | joint MAPのF0、K、voicing | Kを周辺化したF0 MAPとは限らない |
| `computeCostFunctions` | J(K,f)とgrid | Jは確率ではない。gridはcycles/sample |
| `scaled_alpha_buffer` | P×Kのfiltered PMF | 外部読取り可能。和はvoiced質量。毎frame履歴は別途記録 |
| `unvoicing_scaled_alpha_buffer` | noise-only状態の質量 | 生理的無声、無音、モデル不適合と同一ではない |
| `scaled_alpha_buffer2` | 最後のvoiced条件付き記憶 | 現時刻分布やsmootherではない |
| `pitchLogLikelihood` | estimate内部の局所周辺尤度比 | ローカル変数で、通常戻り値・propertyに保存されない |
| 基盤fastF0Nls MATLAB | K条件付きF0密度と次数PMF | Bayesian PMFとはmeasureが違う。通常第3出力は振幅係数 |
| Bayesian C++ `costFunctionMatrix` | compute後はJ、est_fast後は局所log尤度比 | 同配列の意味が処理段階で変わる。filtered PMFはprivateでgetterなし |

根拠：[Bayesian MATLAB class](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m)、[基盤MATLAB class](https://github.com/jkjaer/fastF0Nls/blob/5047004bc2e1fb1a141da5ec5be0d09e5965a2bc/matlab/fastF0Nls/fastF0Nls.m)、[C++ header](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_CPP/src/single_pitch.hpp)。

Bayesian PMFはKを周辺化し、モード内セルを合計して質量を得る。Δfを再度掛けない。基盤の密度は積分し、Hzへの座標変換では密度に1/fsが掛かる。`computePitchLogLikelihood`の`tauVar`はg-prior積分のLaplace近似に使う量で、F0分散ではない。[該当関数](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/computePitchLogLikelihood.m)

## 無音・時刻・前処理

主MATLAB版は低energyでF0=NaN、K=0、voicing=0を返すが、この早期returnでbufferを更新しない。外部から取得する分布にはtimestampと更新有無が必要で、前時刻のbufferを現在posteriorとして描かない。

[外側wrapper](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/BF0NLS.m)は標準25 ms／10 ms hop、16 kHzへの変換、先頭半窓padding、全録音RMS正規化を持つ。コアがforward filteringでも、wrapper全体が厳密因果とはいえない。full-sequence smootherの出力は確認できない。

重複窓全体から毎回尤度を作る処理で、重複サンプルをinnovationへ置換する処理は確認できない。情報重複による過信は検査すべき懸念であり、発生量を測定した結果ではない。hopを変えるとF0だけでなく物理時間当たりのK・voicing遷移も考慮する必要がある。

colored経路のMMSE noise PSD推定→AR whiteningは、PSD／係数推定の不確実性をF0 posteriorへ完全に積分する処理ではない。前処理後の尤度を元波形の尤度と混ぜない。合成で保持すべきaspiration/fricationを除去してよい根拠にもならない。

## C++をそのまま採用しない理由

以下は固定ソースの静的不整合・危険箇所で、実行再現済みの不具合一覧ではない。

- `-DLIB`経路が旧constructor・旧est_fast signatureを呼ぶため、現在宣言との不整合がある。
- KごとのNyquist制限で短く確保した行を全Pで走査する条件がある。標準L=10の設定と、高Kで顕在化する条件を分ける。
- demoは確保配列の手前へpaddingを書き込む構造を持つ。
- `est_fast`の局所次数変数とmember getterの更新が一致しない。
- 旧API経路の範囲外参照、配列解放・再確保、同梱バイナリと現sourceの対応にも点検が必要。

根拠：[C++本体](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_CPP/src/single_pitch.cpp)、[demo](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_CPP/main/fastNLS.cpp)、[library Makefile](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_CPP/lib/Makefile)。

数学的モデルの研究価値と、ライブラリの採用可能性は別判断である。C++全修理を科学的小試験の前提にしない。

## 非ML、資源、帯域

確認したコアと現在のMMSE前処理経路は学習済み分類器を必要としない。ただし固定prior・遷移・SNR依存regularizationがあり、無調整や自然音で校正済みとはいえない。同梱の古いNMF/codebook経路を含めて全repositoryを無条件に非学習と認定しない。

配列形状からの見積もりでは、dense予測はO(P²K+PK²)、posterior1枚はO(PK)、F0遷移行列はO(P²)。16 kHz、70–400 Hz、FFT長16384ならP=338、doubleのposteriorはK=10で27,040 bytes。10 ms hopの全履歴は約162.24 MB/分で、作業配列・局所尤度・メタデータ等を含まない。これはRTF実測ではない。

低rateのF0支流と元48 kHzの別経路を接続する設計は可能だが未実装。同じFFT長で48 kHzへ上げるとHz格子が粗くなるため、同等条件の高速化とは呼ばない。whiteningの固定2048 FFT、LP次数30、regularization、時刻対応も別に検証する。

## 利用時の確認事項

root表示はBayesian側GPL-2.0、基盤側BSD-3-Clause。VOICEBOX由来処理とFFTW依存は個別に確認する。これは表示の静的確認で、特定配布形態への法的適合判断ではない。[Bayesian license](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/LICENSE)、[基盤license](https://github.com/jkjaer/fastF0Nls/blob/5047004bc2e1fb1a141da5ec5be0d09e5965a2bc/license.txt)、[FFTW公式FAQ](https://www.fftw.org/faq/section1.html)。

候補選別の診断が必要になった場合、MATLABの分布構造と必要bufferだけを参照する小さい取得処理が第一候補。実行環境がなければ、既に利用可能なpYIN/Praatの公開候補をscoreとして用いる入口はあるが、Bayesian local／filtered比較を実施したことにはしない。

未確認：ビルド、実行速度、48 kHz動作、数値正規化、モード安定性、信用区間包含率、自然音校正、本repositoryの品質効果。
