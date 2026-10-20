# 雑音推定の不確かさ：予測混合と未知テンプレートの設計

2026-10-20。設計・独立数理レビューの記録です。新しい実装・計測結果ではありません。現在の base は PML。RAW_FULL の PR67 は Draft のままで、採用は変更しません。

## 既存結果との関係

[既知人工信号の実験報告](../results/run-002/index.html)は、500 組・2500 対数予測密度を完了しています。PR69 は main `b388a52e037953fc74a6b29582d1d7f62b55a3fd` へマージ済み。main CI 39372604363、Pages 39372604377 が成功し、配信21ファイルのサイズ・SHA256、19相対参照、一覧掲載を確認しました。[公開ページ](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/oracle-covariance-2026-10-20/index.html)。4図は直接確認済みですが、ブラウザでのページ描画・音声再生は未確認です。

生成条件が白色の場合、W は平均対数予測密度では競合を上回っても、組ごとの評価用データを見た首位は多くで他候補でした。これを原因確率や生理的な識別の成功・失敗へ直接読み替えません。以下は、候補を一つに断定せず予測に不確かさを残すための次の設計です。既存の数値・図・音声を変更しません。

## 保存した5文書

- [根拠、参照 prior、方向 evidence と raw predictive](noise-model-evidence-design-20261020.md)
- [独立数理レビュー、十分統計量、誤差伝播](bayesian-evidence-independent-review-20261020.md)
- [全支持を保持する数値求積計画](evidence-quadrature-plan-20261020.md)
- [記述的再解析の範囲・比較・失敗時の扱い](evidence-reanalysis-scope-20261020.md)
- [未知の周期平均テンプレートを推定した場合の限界](template-uncertainty-design-20261020.md)

文書は執筆時の状態を原文で保持します。「採用候補」「未決定」はその段階の記録です。後続の設計判断は次節のとおりで、実験結果が出たという意味ではありません。

## 現時点の判断

次の記述的再解析の参照仮定として、五候補の prior 各1/5、A の区間一様、V の円板面積一様、S/J の α 一様、共通 scale の dE/E を選びました。唯一の無情報 prior や発声原因の頻度とはしません。dE/E を積分した量は proper な raw marginal density ではなく、共通条件下での方向 evidence 比として根拠付けます。train posterior の propriety を満たす場合の raw posterior predictive は別途、正規化された密度になります。

計画は既存500組の保存入力に対する事後設計の記述的再解析であり、新しい独立確認実験ではありません。全5候補の必要積分が通らない組は BMA を未確定とし、成功候補だけで再正規化しません。数値求積の収束診断を certified error と呼びません。実行契約の詳細とソースの静的確認が済むまで計測しません。コード準備・科学 run はまだ未開始です。

未知テンプレートの文書は別の理論上の限界整理です。今回の500組へ未知平均、推定位相、推定direction、新しい音声を追加しません。既知 covariance・独立周期・平均のみ未知の限定条件で、単純な推定平均と不確かさを積分した予測の期待損失を解析しました。自然音声や五候補 BMA の改善保証ではありません。

新規テスト・スモーク・回帰試験、品質計測、ソースの Git 登録はありません。未採用実装はこの記録に含めません。

## 追加の境界整理（2026-10-20 05:33 UTC）

- [雑音推論と既存の確率的F0/H0を接続する条件](noise-pitch-integration-boundary-20261020.md)：既知qの残差evidenceを候補別fit残差へ直接代入できない理由と一次資料の確認範囲。
- [固定F0・次数で平均係数だけ未知にしたW/Aの独立導出](colored-harmonic-evidence-derivation-20261020.md)：conditional g-priorの正規化、同じ元観測の方向密度、完全harmonic入力での例外、H0との比較条件。priorの具体値・新方式は採用していません。
- [予測混合再解析の表示・解釈計画](evidence-report-interpretation-plan-20261020.md)：パラメータ積分とモデル平均の効果を混同せず、モデル重みを雑音の物理的電力比にしないための実測前整理。

E は元設計どおり tr(Σ)/N、すなわち一標本当たりに各成分を合算した平均雑音分散です。窓全体の trace=NE と区別する表記上の明確化で、モデル変更ではありません。

上記の「コード準備未開始」は前の記録時点です。その後、準備版ソースを受領して独立静的レビューを実施しました。非有限診断、細分化上限、途中終了時の全件台帳と旧結果保存、資源制限、bootstrap集計を修正した版を再レビュー中です。科学 run・新しい計測値はまだありません。未採用ソースはGitへ登録していません。

## 正則化した F0 kernel の追加理論と再解析の経過（2026-10-20 06:07 UTC）

[共通 scale 測度による regularized pitch kernel の独立導出](regularized-pitch-kernel-derivation-20261020.md)を追加しました。固定 λ>0 の非確率測度 E⁻¹ exp(−λ/(2E))dE から、既存 regularized cod の固定 g-kernel と一致する形式比を導出しています。共通の proper prior 近似による比の極限と、hyper-g の不完全 beta 表現を整理しました。raw prior predictive 自体の proper 性、元実装全体の再現、数値安定性や品質改善は主張しません。新 prior の採用・新実装・計測はありません。既存500組の再解析条件は変更しません。

予測混合の初回 run-001 は 05:42:37 UTC に開始し、親の効率判断による明示的早期停止後、05:56:20 UTC に部分完了で終了しました。27分上限への到達ではありません。500組中49組が部分完了、451組が未処理、BMA確定は0組です。5000積分のうち392成功、96未収束、2早期停止、4510未試行。成功392には旧基準を通ったVの2積分を含みます。旧2500スコアと全入力は保持しています。

未収束96のうち92は評価点上限（alternate照合中89、Cartesian照合中3）、残る4はCartesian24/48差の基準未達でした。現在は重複計算を減らし、同じ精度閾値・評価点上限のもとで必要時の追加refinementと成功値再利用を準備しています。修正版の結果はまだありません。初回 results.json のSHA256は `7b819eb2308e1310c636c5ce6f76f3313f25814653d058bc7417978aa2140e3d`。失敗を含む詳細記録は別途整理中です。改善・品質・生理的識別の結論は出していません。

## 既存 hyper-g prior と Laplace 近似の境界（2026-10-20 06:22 UTC）

- [現行設定と log-g Laplace の対応](pitch-hyperg-laplace-correspondence-20261020.md)：δ=3は既存契約・固定著者classの値であり、新たなprior選択ではありません。Jacobian dg=g dz、mode、曲率を含めた式の対応を確認しました。
- [両端で残る近似差の紙上導出](pitch-logg-laplace-endpoints-20261020.md)：r=0およびr→1の極限では、Laplace/exact比に次数K依存が残り、H0とのoddsや次数比較で一般に相殺しません。指定条件での比の符号と単調性を解析しました。
- [独立数理レビュー](pitch-logg-laplace-independent-review-20261020.md)：式と解釈の範囲を確認。λ>0の正則化には、λ=0のproper方向evidenceによる根拠付けをそのまま移せません。

数値評価、全r領域の誤差保証、実装変更、現在のF0誤りとの因果関係、自然音声品質の改善は未確認です。端点解析を根拠に方式を採用していません。既存500組のBMA再解析とは別の紙上検討で、PML base・PR67 Draft・BMAの科学条件は不変です。

## 内部領域の解析と独立確認（2026-10-20 07:31 UTC）

- [内部 r の偏りについて証明できた範囲](pitch-logg-laplace-interior-bias-analysis-20261020.md)：mode の一変数簡約、全域の粗い上下界、r=0 における log 比の一次微分0と負の二次微分を導出しました。
- [新式と本文の独立レビュー](pitch-logg-laplace-interior-independent-review-20261020.md)：局所式と適用範囲を独立確認しました。

指定条件では両端の近傍で近似値が厳密値より小さく、r=0 の右近傍では比がさらに下がります。しかし連続全領域の過小評価は未証明で、反例を得たという意味でもありません。有限支持の数値照合は別途準備済み・未実行です。品質改善、実装採用、既存 F0 誤りの原因を結論していません。

既存500組の予測混合は別の再解析です。初代3分割回収の統合では成功3675/5000積分、BMA確定36/500組（W22・A14）で、全100組の平均・CIは未確定です。成功済み値を保持する次段階の3分割計測を依頼していますが、結果は未受領です。PML base と PR67 Draft は維持します。

## 保存値の識別可能性と予測利得の基準（2026-10-20 08:16 UTC）

- [log-g Laplace の逆写像と丸めの限界](pitch-laplace-inverse-identifiability-20261020.md)、[独立レビュー](pitch-laplace-inverse-independent-review-20261020.md)：指定条件の解析式は r に対して厳密単調増加ですが、helper 内部誤差や clip が不明なら丸め済みログから元 r の保証付き復元はできません。既存ログへの逆変換は実施していません。
- [W-only の scale 積分による期待予測利得](white-scale-predictive-gain-derivation-20261020.md)、[独立レビュー](white-scale-predictive-gain-independent-review-20261020.md)：平均既知の白色 Gaussian と共通未知分散という限定条件で、train/test 長への依存を閉形式で導出しました。BMA の実測利得をモデル混合だけに帰属させないための理論的な対照であり、実測の寄与分解や音質改善の証明ではありません。
- [固定2周波数・全次数の反事実比較計画](pitch-fixed-candidate-counterfactual-plan-20261020.md)：保存済み固定候補だけで BF 差や旧 prior 凍結下の条件付き odds を調べる計画です。全 grid MAP、VUV、exact 再追跡は対象外です。
- [選択入力の読取監査](pitch-bf-selected-input-audit-20261020.md)：309 frame・6180固定候補の保存字段を確認しました。prediction_prior は旧 A の更新前 H1 joint 質量で2056セルに保存zeroがあります。後続 frame の initial_prior_payload のzeroは帳簿用であり、これとは別です。計画適用時はこの監査の限定を優先し、zeroをfloorで補いません。

上記は紙上導出・保存値の読取・計画で、309 frame に新しい BF を適用していません。数値 kernel の固定1080点診断は別工程で、原成功548点と回収532点の保存照合が済み、専用集約を準備しています。有限支持の照合を全領域誤差保証やF0品質改善とはしません。PML base、PR67 Draft、既存比較結果は維持します。

## 弱信号極限と固定候補計画の監査記録（2026-10-20）

次の8文書を原文のまま保存しました。紙上導出・計画・静的監査の記録であり、固定候補のBF計算を実行した結果ではありません。「未開始」「未実行」などは各文書の執筆時点の状態です。実行の成功や品質改善を示すものではなく、PML baseと既存の比較結果は変更しません。

- [弱信号極限の導出](pitch-weak-signal-laplace-limit-20261020.md)と[独立レビュー](pitch-weak-signal-laplace-independent-review-20261020.md)：弱信号スケーリングで残るLaplace近似差と、証明の適用範囲。
- [Bの保存priorの入力監査](pitch-bf-b-prior-input-audit-20261020.md)と[保存候補の重複構造監査](pitch-bf-selected-deduplication-audit-20261020.md)：保存入力の対応と、同一ビット列の入力だけを共有する条件。
- [固定候補の凍結計画](pitch-fixed-candidate-frozen-plan-20261020.md)と[独立レビュー](pitch-fixed-candidate-plan-independent-review-20261020.md)：固定2候補の比較範囲、priorの扱い、実行前に確認すべき条件。
- [stage1のindex照合](pitch-fixed-candidate-stage1-index-review-20261020.md)と[数値呼出しの静的レビュー](pitch-fixed-bf-stage1-numerical-review-20261020.md)：保存入力との対応と呼出し条件の確認。実測一致や実行全体の承認とは区別します。

保存元はLibrary `libfile_9692652c9d848191a7aeca16c48125f8` v0の `pitch-reviewed-followup-docs-20261020.zip`（40587 bytes、SHA256 `0f2788ea9675c0b9dce0b1d19b76319ebbd915871407f9c8b39867969bd07f75`）です。8文書のサイズとSHAを同梱MANIFESTに照合しました。科学コードとZIP原本はGitに含めていません。

## 雑音尺度の校正とPMLの位相契約（2026-10-20）

[一次資料確認・独立レビュー・PML契約監査の3文書](calibration-and-base-contract/README.md)を保存しました。著者実装の正規化・正則化と外部校正するpriorを区別し、既知q・一定F0で学習側だけから位相原点を校正するための残る契約を検討しています。実装・数値prior選択・測定・採用は未決定で、PMLを維持します。
