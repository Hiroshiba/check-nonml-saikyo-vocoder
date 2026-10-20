# scale校正一次資料棚卸し：独立レビュー

2026-10-20。対象は `pitch-scale-calibration-primary-evidence-20261020.md`。論文・コードの静的確認だけを対象とし、新計算、実装、import、tests、実験、prior採用は行わない。

## 結論

論文・固定commitコードの核心と、今回の固定proper IGモデルへの過剰な同一視を避ける結論は妥当。「採用モデルにない」と「未確認」の射程も概ね適切である。修正必須の誤読は見つからなかった。下記の限定解釈を維持する。

## 一次本文で再確認した点

- [Shi accepted manuscript](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf) §IV-A式(11)–(12)：IGは前時刻分散に条件付く遷移案で、本文はその経路を追わず、時刻間独立の逆分散priorを採用する。固定外部βのproper IGを採用したという解釈は不可。
- 同§V式(27)の分母は観測二乗ノルムであり、varSpeech項ではない。同§VIはnoisy signalからのMMSE PSD推定と各フレームのLP prewhitening。これらを固定colored covariance priorの積分と同一視していない点は正しい。
- 同§V末尾は未来データを使うViterbiと、対象とするonline trackingを区別する。入口の全録音RMS依存がコードで確認されたとしても、それだけで本文の状態更新・全実装・原著全体を非因果と呼んではならない。元ノートはこの限定を明示している。
- [AR-ML著者公開本文](https://www.researchgate.net/publication/347434657_Fast_algorithms_for_fundamental_frequency_estimation_in_autoregressive_noise) §2式(2)、§3式(8)–(11)：励振分散、窓外zero拡張、残差二乗和/T、BIC型次数選択を再確認した。定常有限窓の初期分布込み共分散、proper scale/shape priorの積分とは別の構成である。

## 論理・射程の点検

1. 「ない」は、確認した採用prior・目的関数に特定の校正規約が含まれないという局所命題に限定する。SNR依存の定量規則、校正データ分割、他版・全実験スクリプトについては「確認できなかった／未確認」が正しい。原ノートはこの区別を維持している。
2. 全録音RMSは物理音圧校正や知覚ラウドネス校正の証明ではない。観測全体から尺度を作る前処理を、独立校正したβやraw振幅のproper prior predictiveと呼ばない結論は妥当。
3. varSpeechの単位を振幅二乗相当と読むことと、それをnoise varianceの推定値やIGのβと同定することは別。仮に分母の形が似ても、それだけではpriorの正規化定数、指数、観測依存性まで一致しない。
4. AR excitation varianceと平均周辺分散の区別は正しい。定常AR(1)で前者がE(1−a²)という関係は、AR係数・初期状態の契約を含めて使うものであり、AR-MLのfit値をβへ代入する校正手続きにはならない。
5. BICはBayesianな漸近的動機を持ち得るが、変数名や正規化だけで今回の指定proper prior下の厳密raw evidenceにはならない。「BICには一切Bayesian解釈がない」とまで拡張しない。
6. 元ノートの「今回の固定proper IG＋hyper-gは単なるproper化ではない」は、colored covariance、尺度の扱い、校正規約まで含む今回の全モデルについて読む。white・固定候補の尤度とconditional g-priorをそのまま残し、JeffreysだけをIGに置き換える数学的拡張自体が不可能という意味ではない。

## コード再確認の状態

元ノートの固定版はShi `ad9a3fcfe60d2e97a635a92c2076ff1978ae3697`、AR-ML `27ec2ba9c56b1c862d4fb876c734d2240477a614`。webのraw/blob取得はInternal Errorとなったが、公開GitHub connectorの読取りで同じ固定commitの以下7ファイルを独立取得した。コードの実行ではない。

- [BF0NLS.m](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/BF0NLS.m)：resample後、分割前の入力全体RMS正規化を確認。blob `856344e46b749bac85c87a803b9231c21e88dc34`。
- [BayesianfastF0NLS.m](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/BayesianfastF0NLS.m)：varSpeechの説明、5e−6、cod分母、現在FFT powerの入力、state保存、filter後のノルム復元を確認。blob `8f705773dc09b4dcf8bacfa518557ec30cb8c1d3`。
- [estnoiseg_orig.m](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/blob/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697/BF0NLS_MATLAB/private/estnoiseg_orig.m)：初期化は渡された行数までに制限され、現在行で更新後に出力する。呼出側は1行なので、一般コメントの64 msから未来複数フレーム参照を推論できない。blob `6c5bc5ec08e8a3abf6c419dfceb19bd441409206`。
- AR-ML [estimate.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/estimate.m)、[estimatePitchArParameters.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/estimatePitchArParameters.m)、[computeObjectiveNaively.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/computeObjectiveNaively.m)、[pitchArBicModelComparison.m](https://github.com/jkjaer/fastF0ArMl/blob/27ec2ba9c56b1c862d4fb876c734d2240477a614/code/estimator/@FastF0ArMl/private/pitchArBicModelComparison.m)：入力保存・zero拡張、objectiveからestExVarへの接続、data powerからfit項を引く構成、BIC型score正規化を確認。blobは順に `21e2d45311bdd100a2e5977512ff89ec099e7654`、`cfaf705c6d72810bbe1332cc996214a46761c767`、`3b411c88d843a09f2be6ee88940080ed0ac4d80c`、`f44625ef0e8eb954245236525ee30227116a418b`。

厳密にはBIC helperは渡されたvalidPitchOrdersを走査し、0が含まれるとno-pitch分岐を使う。H0を扱える構造の確認と、すべての呼出側設定で必ずH0を含めるという保証は分ける。今回、配布exampleのNoisySignal接続全件、他言語版、全実験スクリプトは再取得していない。

## 停止線

論文・コード核心に修正必須の誤読は見つからなかった。上記確認範囲を超えず、未知raw音声の数値prior選択、実験提案、校正データの代用、PMLからの変更には進まない。
