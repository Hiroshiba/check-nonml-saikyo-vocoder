# 固定二候補log oddsとK正規化の安定性：紙上設計メモ

2026-10-20。f*/2f*、K=1,…,10、三prior条件をそれぞれ固定した後段診断だけを対象とする。新BF評価、数値実験、tests、実装、ログへの算術適用は行っていない。stage2の実行開始を指示する文書ではない。

## 1. 結論と前提

同じprior・同じ有限支持の下で、K周辺化後の変化はセルlog値の変化のmin/max内に入る。二周波数のlog odds変化は、各群のmin/maxを交差して差し引いた区間に入る。全セル共通offsetは相殺するが、周波数別offsetはoddsには残る。

これは保存値間の代数的性質であり、A80/Q80の非認証一致から理想真値の誤差区間を得るものではない。missing、支持zero、未定義の∞差を「小さい誤差」へ置き換えない。

frozen planの定義・三prior・全20セル完備規則を変更せず、以下では両周波数群に正のprior支持がある有限値ケースをまず扱う。

## 2. S / L / Eと差の向き

各セルについて、

- S：旧保存binary64 logBFを正確な保存実数として扱った値。
- L_ref=L80：同じ理想log-g Laplace式を高精度評価した保存値。
- E_ref=A80：exact hyper-g式の高精度参照保存値。
- L_*、E_*：数学的な理想Laplace式・exact積分の値。保存値とは区別する。

計画の略記L/EはL_ref/E_refを意味する。L80を無限精度の理想値と呼ばない。

保存値間の差は

 n=L_ref−S：numerical_reproduction_gap,
 i=E_ref−L_ref：integration_approximation_gap,
 t=E_ref−S：total_replacement_gap。

実数算術ではt=n+i。旧kernelのdelta_A80=L_ref−E_refは−iなので符号を反転して読む。元字段を改名・上書きしない。

理想参照との差をη_L=L_ref−L_*、η_E=E_ref−E_*とすると、

 n=(L_*−S)+η_L,
 i=(E_*−L_*)+(η_E−η_L),
 t=(E_*−S)+η_E。

従ってnは旧実装・保存との差を診断するが、そのまま厳密な旧実装誤差とは言えない。iも理想的な積分近似差に参照評価誤差が乗る。今回ηの保証boundはない。

## 3. 有限KのLSEはsup normで1-Lipschitz

固定frame・固定prior条件・一つの周波数群について、x_k=b_k+s_k、G(x)=log∑exp(x_k)とする。正のprior支持だけを数学的な和の支持Iとし、Iは空でないとする。

別評価でx_kがx_k+δ_kへ動いたとき、元のK条件付き重みw_k=exp(x_k−G)を使うと

 ΔG=G(x+δ)−G(x)=log∑_{k∈I} w_k exp(δ_k)。

ゆえに

 min_I δ_k ≤ ΔG ≤ max_I δ_k,
 |ΔG|≤max_I|δ_k|。

これが有限LSEの1-Lipschitz性。Kが10だから誤差を10倍したり、独立性を仮定して√10で割ったりする必要はない。

ΔGはセル差の単純平均ではない。小さい摂動なら重み付き平均が1次項になるが、exactには上のlog平均である。特にS→LとL→Eでは基準のK重みも異なる。

## 4. 二周波数log oddsへの伝播

群a=1,2についてm_a=min δ_ak、M_a=max δ_ak、D=G_1−G_2と置くと

 m_1−M_2 ≤ ΔD ≤ M_1−m_2。

群ごとのuniform bound |δ_ak|≤ε_a があるなら

 |ΔD|≤ε_1+ε_2。

全セル共通εなら2ε。これはdeterministic boundであり、参照の重複や誤差の相関があっても成立する。一方、真値に対するεとして使うには、各セルに本物の真値誤差boundが必要。

保存値間のn/i/tをδとして用いれば、それぞれの周辺化後寄与に対する代数的なmin/max envelopeとなる。ただしstage2で有限精度計算したenvelopeには、その後段算術の丸めも残る。これを厳密認証区間と表示しない。

有限なDでは固定pair条件付き確率P_1=1/(1+exp(−D))の導関数は最大1/4。従って真に保証された|ΔD| boundがあれば|ΔP_1|≤|ΔD|/4が従う。これは全gridのP(f*)やH0/VUVの確率ではない。

## 5. K正規化とoffsetの相殺

各群のK条件付きlog確率ℓ_k=x_k−Gに対し、

 Δℓ_k=δ_k−ΔG,
 δ_k−M ≤ Δℓ_k ≤ δ_k−m。

従って全Kで|Δℓ_k|≤M−m≤2 max|δ|。特にK_i/K_jのlog odds変化は正確にδ_i−δ_jであり、正規化分母は消える。

共通offsetには二種類ある。

1. 全20セルに同じα：両Gがαだけ動く。pairのDと各群K分布は不変。
2. 群a内だけ共通α_a：その群のK分布は不変だが、Dはα_1−α_2だけ動く。

そのため大きなセル差があってもodds差が小さい場合があり、小さな群内ばらつきだけではpair oddsの安定性は保証できない。共通offsetの相殺を説明するために、保存値を勝手にcenterして元差を消さない。

## 6. zero / missing / ±∞の境界

- prior zeroはb=−∞という支持の除外。有限BFを変更しても支持は復活しない。zeroにfloorを加えない。
- zeroのKは数学的にはLSEへ寄与しないが、frozen planの全20セル完備要件は別の監査契約。prior zeroのセルを未評価・失敗除外してframeをcompleteにしてはいけない。
- missing BFは支持zeroではない。missingを−∞や0へ置き換えたり、成功Kだけで再正規化したりしない。
- 群の全priorがzeroならG=−∞で、その群のK条件付き分布は未定義。片側だけならpair oddsは±∞、両側ならpair自体が未定義。
- 同じ±∞ oddsを二方式で得ても、その差は0ではなくnot_applicable。∞−∞の通常の差・Lipschitz評価を行わない。
- individual zero-prior Kのlog確率は−∞だが、方式間の−∞−(−∞)は数値0にしない。両方式とも支持zeroという状態を保存する。
- 本条件の正常なr<1と有限支持で理想BFは有限。BF字段の±∞やNaNが現れた場合は、数学的prior zeroとは分けて異常・欠測理由を処理する。
- 有限log priorをexpした表示値がunderflowして0になっても、数学的支持zeroとは異なる。B条件の有限log priorはそのまま使い、exp→logで支持を失わせない。

三priorは別の条件。AのzeroをBのfinite priorへ差し替えた結果を、BF変更がAのzeroを救った効果として扱わない。

## 7. 非認証一致と真値保証を分ける

frozen planはA/Qの50/80桁spreadとL50/L80差にgateを設け、成功をmatched_noncertifiedと呼ぶ。このラベルは適切。

A80とQ80が近くても、共通bias・共通入力/式の誤り・未制御tail等を論理的に排除したことにはならない。gateの1e−9 natsをη_Eやη_Lの厳密boundへ読み替え、前節の2ε等へ代入して「真のodds誤差保証」を作ってはいけない。

LSEの安定性は入力誤差boundを伝播する定理であって、入力誤差boundを創出する定理ではない。tinyな順位変化・符号・0に近い差はnoncertifiedとして留保する。A80/Q80を平均して新しい参照を作らない。

## 8. stage2で残すと誤解を防げるもの

既存frozen planを補助する保存字段案。実装・算術を今行う提案ではない。

1. **出所とstatus**：frame/prior条件/周波数/K/unique_id/owner、input/source/result pins、全20セルcomplete判定とmissing理由。重複keyの全参照を維持。
2. **支持**：三priorそれぞれの保存元、正支持mask、群別支持数、全zero、表示underflowとの区別。static初期payloadと後続帳簿zeroを混同しない。
3. **元値**：S bitsとexact lift情報、L80/A80/Q80等の元文字列、gate/status、元delta字段。後段表示用に短縮した値だけを残さない。
4. **セル差の向き**：L−S、E−L、E−Sを別字段。E−S−[(L−S)+(E−L)]という算術closure residualも、強制的に0へ書き換えず残す。
5. **群とpair**：S/L/E各G_1/G_2/D、各群K log分布、三種類のΔD。有限・missing・not_applicableを分離し、∞差の文字列やnull理由を明示。
6. **摂動の形**：各遷移S→L/L→E/S→Eについて支持上のm_a/M_a、群shiftΔG_a、odds envelope[m_1−M_2,M_1−m_2]、K log分布の変化。これは保存値変化のenvelopeであり真値certified intervalではないというlabelを付す。
7. **算術監査**：80桁等の後段精度、処理規則、log/exp/LSE経路、closure/envelope照合の差を保存。許容幅を後から調整してgate通過としない。
8. **報告の分母**：完了frame数と欠測/非対称支持数を三prior別に示す。309frame、6180参照、4180keyを独立な標本数としてCIへ流用しない。

周辺化後もD_E−D_S=(D_L−D_S)+(D_E−D_L)は実数算術で恒等的。しかしセル差の平均による分解ではない。後段算術のclosure residualを参照評価の真値誤差と混同しない。

## 9. 五仮想役の短い反復検討

一人の紙上レビューを五観点で確認したもので、五人の独立実測ではない。

### 第一往復

1. **数理役**：「Kが10なら誤差を10倍か。」→ sup normに対してLSEは1-Lipschitz。pairでは二群のboundを足す。
2. **支持役**：「prior zeroの失敗Kは落とせるか。」→ 数学上のzeroと全20セル完備の監査条件は別。missingを支持zeroにしない。
3. **数値役**：「A80/Q80差を真値boundに使うか。」→ 不可。経路一致は非認証で、LSEは保証を新たに作らない。
4. **解釈役**：「E−SだけでLaplace誤差を語れるか。」→ 不可。L−SとE−Lを分離し、旧deltaの逆符号も保持。
5. **批判役**：「pair順位が変わればF0改善か。」→ 固定二候補・凍結priorの条件付き結果に限る。全grid・時間再帰・品質の改善ではない。

### 第二往復

1. **数理役**：「大きな共通差は必ずoddsに効くか。」→ 全群共通なら消える。群別offsetの差は残る。
2. **支持役**：「∞ oddsが同じなので変化0か。」→ ∞−∞はnot_applicable。支持状態が同じという記述に留める。
3. **数値役**：「後段80桁なら保存真値と同一か。」→ 追加算術も有限精度。rawとclosure residualを保存し、厳密認証へ昇格させない。
4. **解釈役**：「B priorでfiniteになればA zeroを救ったか。」→ 別prior条件への変更。近似差とは分ける。
5. **批判役**：「未達frameを落として全体傾向を報告できるか。」→ 完了subsetとして件数を明記。全支持への外挿をしない。

## 10. 参照・停止範囲

全文読取りした文書：

- pitch-fixed-candidate-frozen-plan-20261020.md。
- pitch-exact-scalar-saved-result-audit-20261020.json：旧初回の548 matched、1 interrupted、531 unattemptedという段階監査。
- pitch-scalar-union-independent-audit-20261020.json：後段unionのcanonical 1080、親再利用548、owner採用532、delta basisはsaved A80という監査報告。
- pitch-scalar-report-independent-audit-20261020.json：公開報告の整合監査。candidate_executed=false。

初回partial監査と後段union監査を矛盾や新しい4180keyの実行結果として扱わない。今回監査JSONを読んだのであって、raw全件・ソース・外部リンクを再監査したわけではない。

新しいBF・odds・K分布は計算していない。保存値の摂動伝播、欠測・支持境界、後段保存字段の提案までで停止する。
