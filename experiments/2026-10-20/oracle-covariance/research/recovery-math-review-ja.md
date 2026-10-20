# V失敗fit回収の独立数理・静的レビュー方針

2026-10-20。既存 fitting.py/model_math.py/contract.json、source-review-v1.md を文字列として読んだ。研究コードの実行、import、tests、smoke、数値実験は行っていない。以下は数学的提案であり、新コードの合格や回収成功を認定しない。

## 固定するもの

初回500pairのsaved train/test、既存2112成功fit/score、半径R=1.5、既存モデル・profile σ²・seed・α、feasibility≤1e−10 と projected-gradient KKT≤1e−8 を保持する。失敗V388件だけを保存bから精密化し、旧結果は上書きしない。再生成、成功fitの再計測、結果に応じた条件探索や追加科学testを行わない。失敗を成功へ読み替えず、回収失敗を保存する。

## 導関数と大域性

phase energy e_j≥0、a_j=log(e_j)−z_jᵀb とし、w=softmax(a)。

f(b)=0.5 logsumexp(a)
g(b)=−0.5 Σ_j w_j z_j
H(b)=0.5 Σ_j w_j (z_j−μ)(z_j−μ)ᵀ, μ=Σ_j w_j z_j

Hは半正定値。実際の全正phase energyと円周designでは正定値であり、円板は凸なのでKKTは大域最適性を与える。Hは差 E[zzᵀ]−μμᵀ より中心化した和で計算すると丸めに強い。退化/非有限Hの場合は成功扱いせず、safeguarded gradient等の既定代替または明示失敗へ進む。Hに数値regularizationを使う場合も目的関数・gate・最終σ²を変えず、step計算だけに限定する。

## 内部と境界

内部候補は H d=−g のNewton step。全stepの可行性を保ち、必要なら円板との交点または投影を使った減衰を行う。単にnormが境界に近いだけで境界最適解とは判断しない。

境界b=R u、t=(-u₂,u₁)、u,tが単位ベクトルとすると、制約を (||b||²−R²)/2≤0 と置いたKKTは g+λb=0、λ≥0。

- 接線残差は tᵀg。
- λ=−bᵀg/R²。最適な境界解では bᵀg≤0。
- bᵀg>0なら内向きに下がるので、円周上の接線stationarityだけでは不合格。境界から内部へ戻す経路を残す。
- 円周 b(θ)=R(cosθ,sinθ) の一次微分は R tᵀg、二次微分は R²tᵀHt−bᵀg。後者の−bᵀg項を落とさない。最適な境界ではR²tᵀ(H+λI)t。
- θNewtonは有限・正曲率でのみ安全に使い、円周上line searchと法線符号検査を併用する。円周への再正規化だけで最適性は成立しない。

境界KKTの連立Newtonを使うなら (H+λI)d+b δλ=−(g+λb)、bᵀd=−(||b||²−R²)/2。λ≥0、実際の可行性、元projected-gradientを独立に確認する。負λを単に0へ切って境界解を受理してはいけない。

## 丸めに強い精密化

今回の失敗KKTは約1e−8～5e−7であり、Newtonのobjective改善はgradientの二乗のオーダーになるため、fの直接差ではdouble丸めに埋もれ得る。SLSQP ftolを厳しくするだけ、objective変化が0だから終了、success flagだけで受理、はいずれも不十分。

既存fの値に通常のArmijoを適用し、丸め域では可行性・有限性・明確なKKT残差改善を伴うstepを認める既定規則が妥当。微小非改善を無制限に認めず、iteration cap・line-search cap・stagnation診断を固定する。停止は元独立gateを必ず再評価する。追加の内部目標（例1e−11）はgateの厳格化として使えるが、1e−8を超すfitを受け入れない。

必要なら同一点で正規化したwを用いて差を
Δf=0.5 log(Σ w_j exp(−z_jᵀd))
=0.5 log1p(Σ w_j expm1(−z_jᵀd))
で計算できる。wの総和を明示正規化し、log1p引数の領域と有限性を検査する。大stepでは安定logsumexpへ戻す。この差の式は同じprofile目的であり別モデルではない。丸め余裕を設ける場合はobjectiveスケールと機械精度を根拠に固定し、実測結果から調整しない。

## 最終独立gate

bに対しgを再計算し、p=b−gを円板へユークリッド投影、kkt=||b−p||を既存式で評価する。feasibility=max(0,||b||−R)も別途確認。NaN/Inf、σ²復元の非正値・非有限、score非有限は失敗。補助optimizerのsuccess flagは証拠の一部であり、gateを代替しない。逆に独自Newtonの収束は独自成功条件として明記し、旧SLSQPのflagを書き換えて偽装しない。

σ²は元の log σ²=logsumexp(zb)−log L+logsumexp(log e−zb)−log N をそのまま使う。testは最終合格fitのscoreだけに用い、最適化・選択・line search・停止には使わない。

## 修正sourceを受け取った後の確認項目

1. 保存済み失敗Vだけを識別し、旧bと同じtrainへ結び付ける。truth/pair/model IDの誤対応がない。
2. 回収入力manifest/hashを検証し、元契約・旧成功fit/score・train/test bytesを保持する。
3. Newton/Hessian、円板の接線・法線・λ符号、丸め域line searchが上記と整合する。
4. 各診断が旧結果と回収結果を区別し、回収失敗の最終bと理由を保持する。
5. 合格した回収Vだけをscoreし、旧成功2112件を再fit/re-scoreしない。
6. mergeは旧有効結果+回収成功のみ。winner/paired validset/失敗分母を更新し、旧結果も別成果物として残す。
7. bootstrap既定stream・10000・既定αで新validsetに実施。モデル変更やpair増加はしない。
8. wall30m/RAM1GiB/output128MiBのguard、停止receipt、immutable入力と別出力先を保つ。

## 現状

修正sourceは未受領。現時点では数理方針のみレビュー済みであり、修正コードの静的承認・数値動作の承認ではない。

## 対象限定の簡潔な回収を優先

親の追加方針（2026-10-20 04:30 UTC）を受けた補足。保存bの境界距離をtrain由来fit diagnosticsだけで確認し、全対象がstrict interiorなら、固定上限の解析Newton精密化に限定してよい。candidateが円板外、Hが不安定、line searchが成立しない、または元gateを満たさないときは回収失敗のまま保持する。万能な境界solverの追加は必須ではない。上の境界数理は実装する場合の審査条件であり、機能拡張の要求ではない。solver選択・停止規則の決定にtest scoreや分類結果は使わない。
