# 通常確率A / log状態B：支持と旧履歴研究の棚卸し

2026-10-20。静的sourceと過去監査・報告の読取のみ。新しい算術・import・tests・追跡・波形測定は行わない。

## 1. 判断

**この支持表現分岐は、今回の目的に対していったん閉じる。A/B全grid追跡や今回の固定候補対比を再実験する価値は示されていない。**

未解決の因果帰属は残るが、未解決であること自体を追加実験の理由にしない。既存sourceで支持消失の候補箇所は説明でき、Bの有限log保存と今回の対比可読性も確認済みである。次の科学判断を変える未済の最小問いを、この手元証拠だけから新規に選定する根拠はない。

これは「underflowの影響がない」「Bやexact方式に価値がない」という結論ではない。支持表現の既存比較を繰り返さず、原因未同定・品質未回答という限界を残して閉じる判断である。

## 2. 既に説明・確認できたこと

### Aの通常確率計算

原model.pyではGaussian遷移をexpして行正規化し、状態Q・H0・memory Rを通常確率として保持する。priorは `0.7 Aᵀ Q B + 0.4 h R`、観測更新後のmassはlog正規化後にexpして保存する。memory更新はmass/(1−h)。非常に小さい遷移・posteriorが表現上zeroになる経路を持ち、そのzeroは次の計算の入力になる。

ただしsourceコメントの「zeroはIEEE underflow」は、個々の保存zeroの発生履歴を監査した証明ではない。各zeroが当該演算で初めて生まれたのか、上流zeroを継承したのかは別である。

今回の有限全grid・正のGaussian kernel・正の初期分布・有限logBFという実数モデルでは、数学的な厳密zeroはモデルに意図された支持制約ではない。これと、A/B間の軌道差がunderflowだけで説明されるという主張は同じではない。

凍結priorの候補がzeroなら、有限BFを差し替えてもその条件付き評価の支持は戻らない。この限定事実がAのundefinedを読むうえで重要である。ただし「一度zeroになった候補は将来永遠にzero」という一般主張は誤りであり、次時刻の遷移・memory再注入で正の質量を受ける可能性は別にある。

### Bの既存log-state計算

log_filter.pyはGaussianのlog kernelを直接作りlogsumexpで行正規化する。通常確率へexpしてからlogへ戻す実装ではない。F0とKのsource和はAᵀQBと同じ向きで、targetのchunk分割は候補削除ではない。

同じ旧保存logBFを入力に、prior・H0・posterior・memoryをlog状態で再帰保持する。初期化、memory更新のh<0.5条件、skipの保持を対応させている。run.pyは各条件を新しいLogFilterから開始し、log MAPと表示用exp後MAPを分離する。表示expがzeroでも内部log支持が消えたとは扱わない。

既存A/B全grid追跡診断のstandalone原レポートを今回直接読んだ。手元run.pyは既存309frameを対象に、log MAP・表示MAP・baseline MAP、H0、zero件数、raw半L1距離、遷移・memory・状態等を保存する設計で、原レポートは以下を既に報告している。数値は既報の転記であり、全grid原配列を今回再集計したものではない。

- 3条件各103窓の全309でA/Bのjoint MAPは不変。
- U-U/E-U共通後半49窓のMAP差は両版とも53–55の3窓に残り、56–101の46窓は一致。
- U-U/E-UのB表示jointは60–101でbyte一致するが、log jointは69–101でbyte一致。MAP一致、表示一致、log状態一致は異なる。
- E-U frame55のf*全K posterior質量はAの4.60395191298e−10からBの0.000304994747447へ変化するが、joint MAPは両版とも195.3125 Hz/K2。
- **支持zeroの帳簿上の初出も既報**。E-Uのf*全Kで、再注入Rはframe24、filteredは45、T/priorは46。frame53ではpriorが1.432e−278の正値へ戻り、53–55はT支配。したがって、その3窓のMAP差を「その窓のpriorがzeroだから」だけでは説明できない。

以上を未実施の問いとして再提案しない。A/B raw半L1はclip・再正規化なしの保存配列差で、厳密正規化分布のTVという保証はない。

### 今回増えた限定的成果

固定選択入力監査ではBの6180 log priorと309 H0値がすべて有限で、元候補ID・bits・表現の内部整合が確認された。Bはlog(A prior)の逆生成ではなく、同じ旧BFを用いた別の既存軌道である。

履歴対比の保存成果物監査はPASS。主要H49でAのX/Iは全undefined、staticは全finite zero。BのX[S/L/E]とI[E−L/E−S]は負8・zero41。**I[L−S]は負4・zero41・正4であり、「Bの全interactionが負8」とは要約しない。** C48はstatic/Bがfinite zero、Aは44finite zero・4undefined。paddingは別枠。

これにより、旧prior固定のもとで「保存E−L差の条件間差Iが全てzero」ではないこと、Aでは同じ有限対比を定義できないことが明らかになった。旧MAP履歴依存の再発見ではなく、BF変更への保存対比の感度という別の狭い結果である。

## 3. 依然として未回答のこと

- **underflow単独の因果効果**：Bはexpの回避だけでなく、和の順序、H1和と1−hの使い分け、memory正規化の丸めも変える。memory更新閾値に近い場合は分岐も軌道へ影響し得る。A/B差を一要因へ割り当てる介入実験ではない。
- **演算レベルでの唯一原因**：候補群のR/filtered/T/priorのzero初出は既に報告済み。それでも各演算の丸め・上流zero伝播・その後の非線形更新を一要因だけへ割り当てる因果証明ではない。既報の帳簿初出を未解決と呼び直さない。
- **zero41の状態同一性**：保存D/gの一致から全prior・内部履歴・理想真値の一致は逆算できない。保存Iは保存gの差で、別に丸めた保存Dからの差の差と厳密同一視しない。
- **品質・exact再帰への意味**：今回Bは旧BFの軌道のまま凍結されている。exact方式で再帰更新した結果、全grid順位、VUV、自然音声・音質、採用利益は未回答。

これらを一括して「次にA/B再実験が必要」とはしない。

## 4. 最小問いを選ばない理由と停止条件

「保存された最初のzeroを項別に特定する」は既存帳簿分解と重複するため採択しない。より細かな高精度介入・演算単位の因果分離は別の追加研究であり、現在の意思決定に直結する価値が示されていない。今回のH49 A全undefinedと、既報のE-U frame53で正のpriorが復帰する事実は矛盾しない。前者は両条件・両周波数を必要とする条件差全体の可否であり、E-Uのf*群単独の支持状態ではない。

旧overlap/recovery監査も読んだ。重複窓による確信・校正、独立reset、heavy-tailは数値表現と異なる未解決仮説として保留されていた。今回の結果はそれらの採用根拠にならず、hop・temperature・hazard・遷移幅を追加変更する提案へ拡張しない。

停止条件は、本棚卸しで既知・未同定・品質未回答の境界を記録し、同じA/B全grid診断や固定100組の再計算を開始せずに完了すること。既存成果の新しい原報告が後から提示されれば、記述の重複・誤りだけを読取訂正する。別の目的が明示されない限り、新しい数値作業は起こさない。

## 5. 五仮想役・二往復

一人による机上点検であり独立五名の実査ではない。

### 第一往復

1. 数理役「正の実数モデルでzeroはない」→批評役「モデル上の非zeroと、軌道差のunderflow単独帰属を分ける」。
2. 実装役「Bはlog化だけか」→数理役「sumQ対1−h、memory正規化、集約順序も変わる」。
3. 来歴役「H A undefinedは失敗か」→実装役「契約どおりの非有限対比。missingやzero効果ではない」。
4. 評価役「B finiteなら改善か」→批評役「診断の可読性であり、精度・F0・品質改善ではない」。
5. 批評役「全gridで確認し直そう」→来歴役「既存A/B追跡は済んでいる。再実験提案は重複」。

### 第二往復

1. 数理役「zero支持は永久に失われるか」→実装役「凍結prior内では戻らないが、将来遷移・再注入は別」。
2. 実装役「最初のzeroを追えば因果分離できるか」→批評役「直接発生演算の特定と、その後の軌道差の唯一原因の証明は別」。
3. 来歴役「負8zero41で全Iを要約」→評価役「L−Sは負4zero41正4。量ごとの定義を保つ」。
4. 評価役「非ゼロIを根拠にexact再追跡を推す」→数理役「同じ状態表現での別の科学問。今回の支持棚卸しから自動開始しない」。
5. 批評役「未解決なら続行すべき」→全役「未解決は残してよい。意思決定を変える未済問が選定できないこの分岐は閉じる」。

## 読取資料

- `pitch-log-static-review-20261020/log_filter.py`、`run.py`、`arithmetic-review-ja.md`。
- `pitch-history-contrast-source-review-v1-20261020/package/evidence/model.py`。
- `pitch-bf-b-prior-input-audit-20261020.md`、selected v1の `B-ADDENDUM-ja.md`。
- `pitch-history-contrast-saved-artifact-review-20261020.md`。
- `pitch-history-contrast-result-interpretation-20261020.md`、`pitch-history-contrast-interpretation-independent-review-20261020.md`。暫定解釈の監査待ちは後続保存成果物監査PASSで更新して扱った。
- `/workspace/scratch/71b268329986/delivered-history-report/pitch-history-log-report-standalone.html`。本文の既報結果・帳簿分解を直接読取。埋込原配列の再集計や表示用スクリプト実行は行っていない。
- `pitch-overlap-review-20261020/review-ja.md`、`pitch-recovery-review-20261020/review.md`。旧計画と未解決仮説を読取。

Git最新STATUSは未取得。既存全grid報告の本文は読んだが、数値の再計算による独立監査ではない。
