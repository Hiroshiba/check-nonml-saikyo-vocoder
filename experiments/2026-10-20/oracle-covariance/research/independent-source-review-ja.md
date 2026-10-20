# 独立静的ソースレビュー v1

2026-10-20。対象source-manifest SHA256: b233953f72cbce72fc66c81c60ef7c83f6e91072b873dcce9dcf9d1ac44cd2de。
対象は親がbyte/SHA照合済みとして渡したmodel_math.py、fitting.py、reporting.py、run.py、storage.py、contract.json、CONTRACT-ja.md。全対象を文字列として通読した。研究コードの実行、import、tests、smoke、予行計測、数値一致試験は一切行っていない。

## 結論

数式・生成・train/test分離・境界同点・失敗分母・bootstrap設計について、以下の報告単位の不足を除き、この固定5候補研究を阻止する静的な問題は見つからなかった。これは数値動作、完走、科学的結果の認定ではない。修正後の差分とmanifestを再確認するまで、最終レビュー済みSHAを確定しない。

## 実行前に直す仕様との差

### R1: nats/cycleのpaired差・区間がない

reporting.py 54, 66–69は真model−競合の差・平均・CIをnats per whole test recordだけで保存する。CONTRACT-ja.md 13もrecord単位だけである。元設計の必須観測はnats/cycleでのpaired差と95%区間なので、raw test_log_densityはrecord単位のまま保持し、paired差・平均・CIをcycles=64で割ったnats/cycleとして保存する。record単位も併記するなら両方に明確な名前を付ける。bootstrap標本を追加したり異なるseedを使う必要はなく、固定正定数の除算は同じbootstrap分布を単位変換するだけである。

## 確認できた事項

### 1. geometry・生成

- model_math.py 13–23: qの64点RMS正規化、解析微分の−.6π項、hの符号とRMS、cos/sin phase designが正しい。
- 31–49: phase varianceはexpを正規化したvarianceとして用い、innovationへsqrtを掛ける。periodic stationary r[-1]を積分する生成法はAのstationary initialを正しく与え、ARは周期でresetされない。
- qを足して引かず直接residualを生成するのは、既知meanのtranslationを省く正当な同値表現。testからmean推定はしていない。
- 26–28,40–47: 固定PCG64/SeedSequenceでtruth/pair/split/componentが分離されている。無効componentも独立streamなので失敗やmodel順により後続pairの乱数はずれない。
- run.py 94–95,111,123: trainとtestを別splitで生成し、全候補に同じtrainとtestを渡す。fitにはtrainのみ、log_densityにはtrain fitted parametersとtestを渡す。

### 2. W/A

- W: model_math.py 97–98、90–91は二乗平均MLEと全N点Gaussian density。
- A: fitting.py 17–21のtotal=C、adjacent=隣接積和、interior=内部二乗和に対応する三次係数は正しい。私の事前checklistのB/Dの名前と逆でも内容は一致している。
- fitting.py 25–51: 全rootsを走査し実数・残差・範囲を記録、端点と全許容停留点をprofile目的で比較。Qの評価は正の二乗和を使う。
- model_math.py 75–78: initial項(1−a²)x₀²と−log(1−a²)を保持し、conditional AR尤度へ置換していない。
- a端点はモデルで認めた境界であり、numerical boundaryとして記録することとfit failureを混同していない。

### 3. VとKKT

- fitting.py 60–71: phase energyはtrainの64cycle合計。logsumexp profileの.5係数、勾配−.5 weighted zは正しい。gridのmean zは実数算術で0であり、有限浮動小数点の微小非零を無視する差はこの1e−8 KKT toleranceを覆す構造的な誤りではない。
- 72–92: ||b||≤1.5の円板、SLSQP0開始、固定maxiter/ftol、success flagとは独立に可行性とprojected-gradientをチェックする。
- 79–82のmapping b−Π_C(b−grad f(b))は、可行点では0⇔−grad f(b)∈N_C(b)であり、凸目的・凸円板のKKT/大域最適条件と同値。境界で誤った法線方向のgradientを通す検査ではない。
- 可行性は83,91で独立に1e−10以内を要求。わずかな外側点を許す数値許容差であり、variance floorではない。実測精度の保証はしない。
- 93–96: Z(b)を含むinnovation σ²復元が正しい。model_math.py 79–83はそのtrain parameterによる正規化済み全test密度であり、testをprofileし直さない。

### 4. S/J

- model_math.py 55–67: 実際のdirection norm²を用いたunit方向と直交射影。T−Pを直接差し引かず直交residualの二乗和を使う。
- fitting.py 107–113: along=P/K、across=(T−P)/[K(L−1)]。非負spike制約のclosed-form MLEが正しい。
- boundaryではwhite_mle(x)とtau2=0を用い、model_math.py 73–74でWと完全に同じscore経路へ渡す。独立呼出しでも同一input・同一演算であり、異なる代数式の丸め差で数学的同点を破らない。
- model_math.py 85–89: logdetとquadraticにK、L−1、方向norm²が正しく入り、latent coefficientをfixed effectとして差し引いた尤度ではない。

### 5. 失敗・勝者・bootstrap

- run.py 97–129: 数値fit/score失敗はtraceback/diagnosticsを残す。W置換、scoreの0埋め、追加生成、適応的反復数変更はない。
- run.py 131–136: 5候補loopを終えた後だけwinnerを定義し、完全一致score全てを集合として保持。top−second marginは同点0になる。
- reporting.py 25–47: winner分母は完全5-score pair、fit失敗分母はfit試行数、score失敗/境界率の分母はfit成功数。planned/attempted/generation failureを分離する。
- reporting.py 50–71: 真候補と当該競合の両score成功pairだけで差を計算し、pair_idと有効分母を残す。complete-case winner分母をpairwise contrastに流用しない。
- bootstrapは有効pair差を同じ長さで復元抽出、10000回の平均。namespace=1、truth/competitorでstream分離。pointwise percentile95%、linear quantile、n<2でCIなしがcontractと一致する。
- 「both scores availableに条件付け」「no multiplicity adjustment」を明示し、全100pairへの無条件推論としない。

### 6. 資源・実行ゲート（親によるrunner並行審査あり）

- run.py 40–51: 指定manifest SHAと全listed file bytes/SHA、single-thread環境を開始前に検査する。明示execute flagが必要。
- storage.py 24–47: wall/RSS guard、atomic write時の既存fileと新partialの両方の一時peakを出力容量へ数える。正規出力は1MiB emergency reserveを残す。
- run.py 64–81: alarm、RLIMIT_AS、NumPy/SciPyの固定version検査。RLIMIT_ASはvirtual address上限でRSSより保守的というcontract説明は正しい。
- 中断時はinterrupted pair、receipt、manifestへ保存する設計で、completed_with_failuresとresource_stoppedをcompletedから分ける。OS killや深刻なメモリ枯渇で最後の保存が不可能なことはcontractで明示されている。
- denseΣ、full mixture、Kalman、実装一致専用test/smokeはない。

## 非blockingの注意・未確認点

1. fitting.py 36–37の相対多項式残差scaleは、adjacentが厳密に0でroot=0のとき0になる。その数学的に正当なstationary根はValueErrorでfit failureになる。連続Gaussianの固定500pairでは確率0の厳密退化caseであり、現固定研究のblocking issueとはしない。一般用途化する場合は0/0残差の定義を見直す。失敗をW代替していないので誤成功にはならない。
2. model_math.py directionalはtestの直交energy0にも正値性を要求し、正定値候補に対して有限密度を持つ厳密な方向上recordをscore failureとする。これも本生成分布では測度0であり、汎用density APIの完全性と本研究の実効範囲を分ける。
3. Vの1e−8 projected gradient gateで実際に何pairが成功するか、NumPy/SciPy importが1GiB RLIMIT_AS内か、30分内完走するかは未計測。成功保証しない。事後に閾値や予算を緩めて同じ事前固定run成功扱いにしない。
4. partial resource stopではsummary自体がない可能性があり、pair/checkpoint/receiptから未完了を判定する。必要なら別の静的結果読取りで集計できるが、追加fitや反復を意味しない。
5. 失敗の各候補共通/片側件数はsummaryに専用欄はないが、pair_idと全pair fit/score statusが保存されるため復元可能。対比較valid分母と条件付き解釈は明示されており、失敗を隠してはいない。
6. phase covariance診断やFのridge解析は今回コードに含まれない。本runを元設計の全診断完了または自然音声品質/生理的原因同定と呼ばない。

## 次の確認

R1修正後にreporting.pyとCONTRACT-ja.mdおよびmanifestの変更箇所を再読する。数値動作確認runは要求しない。親がrunner並行審査で追加指摘を得た場合は、それらの修正も静的に再確認する。

## 親の報告方針を受けた判定更新（2026-10-20 04:25 UTC）

親は原scoreとbootstrapをwhole-record単位で保持し、最終HTMLの主表示では保存済み差・平均・bootstrap端点を固定cycles=64で割ってnats/cycleを追加する方針を明示した。この同値な後処理は新しい科学計測、再fit、追加bootstrapを要しない。従ってR1を「科学実行前の修正要求」から「最終報告時の必須単位換算」へ変更する。実装凍結SHAを変更する必要はない。上記『修正後にmanifestを再確認するまで確定しない』という留保は、このR1だけを理由としては適用しない。

現SHA b233953f72cbce72fc66c81c60ef7c83f6e91072b873dcce9dcf9d1ac44cd2de について、固定500pair/2500fitの一度の科学runへ進むことを阻止する静的問題は見つからなかった。静的レビュー通過とするが、実行・import・tests未実施であり、数値動作・成功率・資源内完走・科学的結論は未確認である。

親による追加留保: Storeが計数する出力128MiBはmanaged artifactの上限で、外部stderrログを含むhard filesystem quotaではない。運用上の全出力範囲を別途説明する。数理推定の不整合ではない。
