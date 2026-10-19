# v3：局在noiseと周期noiseの結合を、global二値flagだけで比較する

2026-10-19 UTC。**未実装・実行前の固定仕様**。新しいコード、run、音声測定、Git操作は行っていない。v2のmean/gainを細分化せず、残るC4の局在×周期分散相互作用だけを一変更として加える。

## 1. 変更理由と範囲

根拠は `clock-event-mean-gain-results-v2-received-20261019/results/results.json` と `clock-event-mean-gain-v2-result-analysis-20261019.md`。v2は全24 encode／96 decode成功。C5全4例でgain選択・q0・eventなし、背景σ²比0.976〜1.028、平均target KLは約0.928339→0.00560181へ改善した。C0〜C4全20例はnull gainで、保存分布と出力はv1と同じ。次にC5の微小残差を詰めない。

C4は全体KLが約0.0019でも、真event内は約0.031。局在varianceと周期varianceを加算する仮定が残る。**v3は両者の結合の有無だけを比較する。** mean8係数・gain prepass／2 branch・q25候補・event579群・強度比{1,4,16}・最大2段greedy・24入力・target120/140 Hz・尺度・RNGを変えない。

## 2. 唯一の追加：global η∈{0,1}

meanの共通gainをG(t)、局在variance包絡をe_j(t)と区別する。既存の周期分散r_qと局在包絡e_jを使い、

`s_η(t)=r_q(t)+Σ_j c_j e_j(t)[(1−η)+ηr_q(t)]`

`Var ε(t)=σ²s_η(t)`

とする。

- **η=0**：v2の加算モデル `r_q+Σ_j c_j e_j`。
- **η=1**：結合モデル `r_q(1+Σ_j c_j e_j)`。
- ηは発話区間全体で一つ。eventごとの別flag、連続η、ηの時変軌跡は追加しない。
- r_q≥0.1、c_j≥0、e_j≥0なので、両モデルとも正の分散を保つ。
- mean/gainの**仕様と予算**は固定するが、各variance候補に条件付けたmean8係数・σ²の再fitは必要。v2のfit値へ後からη1を貼る方式ではない。

### 非同定な重複のcanonical化

q=(0,0)またはevent数J=0ならη0とη1は同じ分布なので、**罰則・tie判定の前にη0へcanonical化**する。重複を別候補の成功・証拠として数えない。

今回C0/C1/C5のeventなし、C2のq0ではη識別を採点しない。構造の識別対象はC3（加算）とC4（乗算）の各4入力。非同定条件でη0と出るのは正規化規則であり、結合が物理的にないと推定した結果ではない。

## 3. encoderと固定モデル選択

1. v2と同じgain prepassを一度行う。定常gainと最良非定常gainの2 branchを保持する。
2. 各gain／q／ηでs_ηを作り、**1/s_ηのWLS、σ²=max(mean(d²/s_η),floor)**、eventの0／1／2候補探索をそれぞれ行う。log variance項と直接残差確認は既存どおり。
3. η0は従来の探索全体。η1はq非0・J≥1だけ独立探索し、共通のJ0解は再利用する。η1の最良第1eventと第2eventはη0の選択と一致する必要はなく、ηごとのgreedyを行う。
4. 最終scoreは次とする。

   `L_v3=L_Gaussian + Jλ_event + I(nonnull gain)λ_gain + I(η=1)log2`

   λ_event、λ_gainはv2から不変。η1への追加は**log2≈0.693147 natsを一回だけ**。event数倍にはしない。
5. 最終同点ならη0を優先し、その後は既存v2のtie規則に従う。canonical化を後回しにして罰則だけで重複を潰さない。

### log2の意味

これは変更の小さい基準η0を優先する、**実行前固定のスコア上の事前選好**。2:1の優先比の負log差に相当するが、profile likelihood、greedy、既存の記述長型罰則を含む全手順をBayes posteriorとは呼ばない。η0/η1でflagの実保存量は同じなので、「η1だけ1 bit増える厳密MDL」でもない。結果を見て0、BIC、別の係数へ調整しない。

η別の最良解について、`B_η=Gaussian NLL+Jλ_event+I(nonnull gain)λ_gain` と、`B_η+ηlog2` を両方保存する。外すのは新しいη罰則だけであり、既存のevent/gain罰則を外して枝を選び直さない。Gaussian fit項・event/gain罰則も区別して残す。短いevent内でlikelihood差が弱い場合、固定選好でη0になったことを識別成功に読み替えない。

## 4. 復号と局在powerの定義

周期noiseは従来どおり、target位相のr_qへ置き換える。各局在noiseの分散は、

`B_j,target(t)=σ²c_je_j(t)[(1−η)+ηr_q(φ_target(t))]`

となる。

- 新しいiid Gaussian streamへ **√B_j,target** を掛ける。独立noise同士を掛ける非Gaussian生成にはしない。
- event開始τ_j・持続T_jは絶対時刻のまま。η1ではevent内の期待分散形・重心・積分powerがtarget周期で変わり得る。これを誤った時刻移動と同一視しない。
- 時刻・幅の保持とevent音量不変は別の契約。**eventごとのエネルギー再正規化は追加しない。** 既存のC4 target truthに対して比較し、一般的な音量制御の優位を主張しない。
- `σ²c_j` はη1では基準分散scaleで、**実際のpeak分散ではない**。peakはe_j×r_qの最大値に依存する。
- `localized_hat`、積分power、支持外／開始前power、重心は、上の**実際の局在増分**から計算する。旧η0のσ²cgをそのまま診断へ流用しない。
- source側の推定分布にも同じη規約を使う。C4 truth targetは既に `σ²r_q(target)(1+cg)` なので、truthをv3へ合わせて変更しない。
- η0は既存の演算経路・seed規約を保つ。η1でもRNG domainやstream数・対応を変えず、分散包絡だけが異なる。

## 5. 保存と計算の追加予算

### 保存

global ηを1個追加。情報量としては1 bitだが、今回のpacked予算では**1 byte**とする。v2の最大core48→49 bytes／256 ms、source clock込み56→57 bytes。既存JSON約606〜646 bytesの実ファイル増分は別に測る。η1でも波形、残差、追加のq/event係数は保存しない。

### 計算

gain2 branchは維持。各branchで、η0のq25全探索と、η1のq24・event1/2探索を行う。上限概算は

`2 × {25×[1+2×1737] + 24×[2×1737]} = 340,502候補／入力`

で、24入力で約817万比較。非重複event制限等により実数は減る。v2上限約17.4万／入力のおおむね2倍。gain prepass1746 fit／入力は増やさず、各WLSも8×8のまま。

η1の候補追加によるsの変化も局在支持内だけなので、既存の十分統計・局所差分更新をそのまま利用できる。η0もfrom-scratchで計算し、総RTF・候補数を報告する。v2平均encode約2.33秒という保存値から、新実装の実時間を保証しない。

## 6. 新runと比較対象を増やさない

**v3候補の24 encode／96 decodeのみ。** 元24入力配列・SHA、6条件、2 target、seed namespace、生成尺度、truthは固定。v2の保存結果を出典付き比較対象にし、PML／WORLDは初回参照の引用契約を維持する。参照を新たに再計測したことにしない。

見る量は既存のmean/variance条件付きKL、q・event帰属、局在power診断、gain選択、σ²比、payload、RTFにηの選択差を足すだけ。追加の全自然音や全metricsを今回のgateにしない。

- **C4**：event内／外と全体のnative・target KL、局在power・形状、η別score差を報告。全体平均の小ささで局所誤差を隠さない。
- **C3**：加算truthを誤って結合し、局在内のtarget分布を損なわないか。C4改善だけでは判断しない。
- **C0/C1/C2/C5**：η識別率は出さず、q/event/gainの新しい誤帰属、σ²・KLの悪化を監査。C5のmean改善を壊していないかも保持する。
- 2 decode seedは、解析的分布KLの独立反復には数えない。

全4seedでη正解を必須とする新基準は作らない。η選択、分布適合、罰則に対する証拠の強さを分ける。C4で改善せずC3等を系統的に損なうなら、二値結合モデルまたは有限探索の不足として保留する。物理的な結合がないという反証にはしない。

**この相互作用の比較後、6人工条件の辞書・gain・ηを延々と細分化しない。** 既知F0／既知filter／独立区間という未検証前提から、次に外すものを一つ選ぶ。v3成功でも自然/b/品質の証拠にはならない。

## 7. 批評2巡で固定した点

**第1巡**：global二値flag、各ηでの独立fit、非同定分布の罰則前canonical化、log2を保存bit由来の厳密MDLにしないこと、最終同点のη0優先を確認した。

**第2巡**：η1をnoise同士の積で作らず、決定的分散の平方根×iid Gaussianとすること、localized診断を結合後の増分へ変更すること、σ²cをpeakと呼ばないこと、η別scoreの追加罰則前後を残すこと、非同定C0/C1/C2/C5をη成功数に含めないことを確認した。条件・辞書・penaltyの結果後調整は行わない。
