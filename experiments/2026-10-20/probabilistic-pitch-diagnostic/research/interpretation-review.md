# F0・H0 posteriorの科学的な読み方

2026-10-19。既存の5入力診断計画と直接harmonic射影案の解釈レビュー。実装・音声処理・推定器実行・Git操作は行っていない。以下の図は予定済み保存量の再集計案であり、新しいtracker、音声実験、採用gateを追加しない。

## 結論

この診断で分かるのは、**指定したharmonic/white-noiseモデルとpriorのもとで、どの候補へ、何によって質量が移ったか**である。真の声帯振動、実際のoctave誤り率、帯域別noise電力、聴覚上のpitchの正解は同定できない。特に次の3点を図の説明に入れる。

- filteredの集中を、独立した観測証拠の増加と同一視しない。
- H0とF0の質量を合成振幅・noise率に変換しない。
- regularized codは純粋なharmonic適合度ではなく、frame energyにも依存する。

## 1. H0、無声、aperiodicityは異なる量

原著のH0は観測をnoiseだけで説明する仮説、H1はharmonic成分とnoiseの和。原著自身、無声音の着色性と白色モデルとの不一致を述べ、prewhiteningを扱っている。本診断はwhite経路に固定するので、その救済まで実行したとはいえない。[Shi et al., 式(6)–(9)・VI節](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)

本診断への解釈として、H0優勢は「この有限のharmonic候補群よりnullが相対的に支持された」。生理的無声の証明ではない。F0域外、短窓、FM/AM、K不足、非調波性でもharmonic仮説は不利になりうる。逆に着色noiseの局所的な峰がharmonic候補に適合する可能性もある。H0低下は無雑音・純粋な周期音の証明ではなく、H1自体が残差noiseを含む。

aperiodicityは信号の非周期成分を記述する量であり、F0候補の選択不確実性と別問題。帯域別非周期成分を推定する方法でも、F0軌跡とaperiodicityの抽出を区別している。[Kawahara et al., 2016](https://www.isca-archive.org/ssw_2016/kawahara16_ssw.html)

図ではP(H0)、無条件F0質量、voiced条件付きF0分布を区別する。energy_floorは欠測、paddingは人工支持、numerical_failureは計算失敗であり、いずれもH0=1へ置換しない。REAPER VUVは比較軌跡であり正解ラベルにしない。

## 2. 低energyと適合度の交絡を分ける

直接射影案の保存式に基づく代数的導出。E=xᵀx、v=5e-6、N=400、有効な非zero frameで

- fit = J/E
- ρ = E/(Nv) = frame平均二乗/v
- cod = J/(E+Nv) = fit × ρ/(ρ+1)

したがって同じfitでも、低energyではcodが小さくなり局所log比が変わる。これは「harmonic構造が消えた」ことと同義ではない。全録音RMS正規化は録音間のglobal scaleを揃えるが、録音内の弱い箇所をframe正規化するものではない。ρは固定regularizerに対する比であり、推定した物理的SNRではない。

既存frame要約から、同じ候補(f,K)についてfit、cod、ρを同じ時間軸に置き、P(H0)を併記する。local/filteredの代表候補が異なる時は双方を表示し、候補を途中で無表示に切り替えない。J/Eが高いままcodとharmonic質量が下がる位置はenergy依存の寄与と整合する。J/Eも低い場合はenergyだけでは説明できない。これは実装の代数的寄与の説明であり、低energyが生理的無声の原因だという因果判断ではない。全gridのJを追加保存する必要はなく、計画済み代表modeのJがある箇所だけを使用し、欠測から推測しない。

## 3. 重複とモデル不適合の下で、狭さは正しさを保証しない

25 ms/10 ms hopは隣接窓で60%の原サンプルを共有する。現filterは共有観測から独立innovationを作らない。そのため各更新の局所尤度を独立の新証拠と読むことはできない。概念例として、同じ観測の尤度Lを独立と誤認してm回掛けるとL^mになり、峰の位置を変えずに鋭くできる。実際の動的filterがこの単純式に等しいという主張ではない。60%という割合からconfidence補正係数や有効標本数を直算することもできない。

誤指定モデルではposteriorが集中しても真値の近傍とは限らず、credible setの頻度論的coverageも保証されない。これは一般的な統計上の注意であり、本診断が何%過信しているかを計算した結果ではない。[Kleijn & van der Vaart, 2012](https://www.dare.uva.nl/id/e2802606-5e86-434a-a3ab-bb4c2bbaf774)

既存出力ではlocalとfilteredのmode質量・幅、予測priorを併記できるが、これだけでoverlapの寄与と真に持続する音響構造の寄与を一意に分離できない。entropy低下だけを改善と呼ばず、無音skip数・記憶元frame・域端・K上限も同じ図へ表示する。独立性検証や校正を済ませたとの表現は避ける。

## 4. Octave競合とmissing fundamentalを混同しない

fundamental成分のスペクトル振幅が小さい／ゼロでも、上位harmonicsからそのF0に対応するpitchが知覚されうる。この現象は実験的に調べられている。[McFadden, 1988](https://pubmed.ncbi.nlm.nih.gov/3350772/)

本harmonic基底への数学的解釈として、k=1の係数が小さくてもk=2,3,…が適合するので、fundamental成分の欠落はH0を直接意味しない。たとえば2fと3fを含む信号はf周期で、2fだけの系列では3fを表せない。一方、偶数次2f,4f,…だけなら波形の最小周期は1/(2f)であり、fモデルも偶数列だけで同じ信号を表せる。後者から、観測に現れない声帯の周期まで決定することはできない。

f/2候補はより多くの列を必要とすることがあり、K上限とmodel complexity penaltyの影響を受ける。同じ信号でも候補の必要Kが違うため、F0だけ周辺化した図に加え候補領域ごとのK分布を読む。約2倍離れた峰を見ただけで「missing fundamentalが原因」「低い枝が正解」と断定しない。保存量にharmonic係数やスペクトルがなければ、実際に第1成分が欠けているかも今回のposteriorだけでは確認できない。

## 5. Prior誘導の集中を既存出力で分解する

以下は保存済み局所log比と予測priorからの厳密な算術恒等式。状態s=(f,K)、L(s)=exp(ℓ(s))、L(H0)=1、更新前priorをu(s)、更新後をp(s)とする。同じframeの比較では候補領域A/Bを固定し、localとfilteredで別々の峰領域へ取り替えない。

U_A=Σ_A u(s)、B_A=Σ_A [u(s)/U_A]L(s) と置くと、

log[p(A)/p(B)] = log[U_A/U_B] + log[B_A/B_B]。

左から、更新後odds、予測prior odds、当該更新の有効な局所証拠である。H0との比較もB_H0=1として同じ式で読める。単純平均したℓの差は右辺にならない。領域内の予測priorが違えばB_Aも変わるので、領域版の「証拠」はpriorから完全独立ではない。完全に点同士の比なら、log[p(s)/p(r)]=log[u(s)/u(r)]+ℓ(s)−ℓ(r)。計算はlog-sum-expで扱い、zero priorは情報欠測でなく到達不能な支持として明記する。

具体的な既存出力の図・数値:

1. **全長の3段図:** local/base・予測prior・filteredの無条件F0 heatmap。同一色尺度、P(H0)、欠測、記憶元時刻を併記。sample 3だけを選ばない。
2. **Octave領域対のodds分解:** 上式3項を同一時間軸で表示。予測priorが一枝へ強く偏り、局所項が弱い／反対方向でもfilteredが残る箇所は「その更新でpriorが優勢」と説明できる。過去のpriorも過去観測を含むため「証拠が一切ない」とは言わない。
3. **Harmonic対H0のodds分解:** harmonic全域をAとして同じ3項を表示。energy/fit/codを併記し、null競合をF0競合から分ける。
4. **local/base対log-Hz:** 既定の再重み付けによる質量・順位変化を表示。固定cents幅は高いF0ほど多くの線形Hzセルを含むので、領域のセル数／幅も示す。単一セルなら1/f priorはf対2fのprior oddsを2倍にするが、領域質量へそのまま適用できるとは限らない。順位変化は座標/prior依存を示し、正解を選ぶ実験ではない。
5. **K・支持・記憶の併記:** 候補ごとのK周辺分布、K=10質量、域端、energy_floor後のskip数と記憶年齢。K上限集中などは不適合の疑いであり証明ではない。

localとfilteredの差だけで、現frameのprior寄与と局所尤度の寄与を厳密には分けられないため、2・3が特に有用。原著も過去の有声frameを再有声化priorに利用しているので、記憶元frameの来歴を読む必要がある。[Shi et al., 式(17)–(18)](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)

## 6. Posterior質量を合成振幅にしてよいか

**今回のpitch posteriorをそのまま合成振幅にする根拠はない。** p(f)は排他的な説明候補の重みであり、その周波数のエネルギー成分量ではない。二つのoctave候補を重み付きで同時に鳴らすと、不確実性の保持ではなく新しい混合信号を作る。平均Hzは支持の薄い中間pitchを作り、frameごとの抽選は軌跡の連続性を保証しない。p(H0)をnoise電力比にするのも同じ混同である。

ただし「確率が振幅推定に関与することは数学的に常に禁止」とまで言うべきではない。適切な生成モデル・推定対象・損失を決めたBayes estimatorなら、条件付き振幅推定をposteriorで平均する場合がある。例えばsignal-presence uncertaintyを扱うlog-spectral推定は、仮説ごとのgainを確率で幾何平均する。[Cohen, 2002](https://webee.technion.ac.il/Sites/People/IsraelCohen/Publications/SPL0402.pdf) これは別の目的とモデルによる導出であり、本診断のF0/H0 PMFを流用する許可ではない。

将来の合成では、選んだsource候補に条件付けた信号パラメータと、独立に指定したtarget時計を区別する。今回のframe marginalだけでjoint path・振幅・phase posteriorまで得られたと扱わない。

## 報告文の範囲

許される結論例: 「この区間ではlocalにoctave競合があり、filteredの集中には予測prior oddsが大きく寄与した」「fitが同程度でも低energyに伴いcodが低下した」「このモデルではH0が相対的に優勢だった」。

避ける結論例: 「80%正しい」「無声率／息の量が80%」「時間処理で真F0が確定した」「候補平均により音質が改善する」。新しい正解ラベル、追加試聴、parameter探索なしでは、ここから先の正しさ・校正・音質因果は識別できない。曖昧という結果自体を保存し、任意thresholdで合否へ置換しない。
