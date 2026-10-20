# PML 一次差分後処理の追加設計レビュー

2026-10-21 JST。元の `pml-nonringing-f0-hypothesis-review-20261021.md` は変更しない。本稿はその後に追加された D1 案と親の比較範囲を、改めて五仮想役・二巡で検討した補遺である。実装・計測・科学 launch の許可ではない。

## 結論

**線形 Hz 上の一次差分 penalized least squares を明示的な別モデルとして固定し、未採用 Library source の静的準備に進むことは合理的である。** ρ の選定を実音質へ適応させず、正式 PML と旧失敗を変更せず、後述の薄い adapter と provenance を守ることが条件となる。最終採用、科学 launch、旧 phase B、残117件展開を承認したという意味ではない。

元報告が提案した人工 clock や新しい音響誤差予算を、静的 source 準備や自然音声の開発比較の必須条件にはしない。今回の目的は固定100件以上の自然音声・自動MOSを含む開発比較であり、test/smoke用の人工定数・step・rampを新設しない。帯域差と精度の限界は評価結果の解釈として残し、実用差の根拠がないことを理由に探索的な source 準備そのものを止めない。

## 1 固定する新しい推定量

既存の補間・65..700 Hz clamp 後、同じ内部 grid 上の m 点列を y とする。D は `(m−1)×m`、`(Dz)_i=z_(i+1)−z_i` の隣接一次差分で、Δtで割らない。周期接続・固定端点・外部 padding を加えず、有限 path の自然端点を使う。

`z = argmin_z { ||z−y||² + ρ||Dz||² }`

`A z = y, A = I + ρDᵀD, ρ = 1/(2−sqrt(2))`

ρ は新しい平滑化係数であり、既存 F 選択器の `λ=1 nat/半音` とは別の記号・別の量である。線形 Hz の一回の solve とし、log-F0化、差分次数変更、残差依存の重み、反復 robust 化、ρ 探索、候補格子変更を同時に入れない。これは3tap FIRではなく、有限区間全体を使い、一般には全入力点に正の重みを持つ非因果的な平滑化である。元報告の有限支持局所平均とは別系統で、同じ支持幅、低遅延、局所生体モデルを主張しない。元filtfiltもofflineであるため、今回の開発比較ではofflineという性質自体を障害とはしない。

この種の penalized least squares smoother は Whittaker に由来する既存系統である。ただし確認した Eilers 論文の公開 abstract が裏付けるのはこの研究系統までで、以下のD1凸包証明やF0効用を同論文の主張として引用しない。[Eilers 2003 A perfect smoother](https://pubmed.ncbi.nlm.nih.gov/14570219/)

## 2 数学的に言えることと言えないこと

以下は本案の解析的導出であり、数値実験ではない。独立数学レビュー `pml-first-difference-smoother-math-review-20261021.md` の最終文書でも確認された。

- 非零 v に対し `vᵀAv=||v||²+ρ||Dv||²>0` なので A はSPDで、一意解がある。
- m≥2 の両端対角は1+ρ、内部対角は1+2ρ、上下対角は−ρ。最大 z 点では `y_i=z_i+ρΣ_neighbor(z_i−z_neighbor)≥z_i`、最小点では逆の不等式となる。従って厳密実数で `min(y)≤z_i≤max(y)`。
- 同じ最大原理から `A⁻¹≥0`、かつ `A1=1` なので `A⁻¹1=1`。定数保存と全入力凸包保存を得る。`D A⁻¹=(I+ρDDᵀ)⁻¹D` の右の逆行列も非負なので、単調入力は単調出力となる。任意音声の局所的な全振動を消す、という意味にはしない。
- この論証は一次差分固有で、二階以上の差分へ一般化しない。一次差分は曲率だけでなく隣接レベル差そのものを縮める。
- 既存 L/F 候補は50.78125..500 Hzなので、共通補間・clamp 後の65..500 Hzを理想演算で保つ。一方 REAPER は既存上端700 Hzを取り得るため strict `<700` の全入力保証はない。上端を縮めて救済しない。
- float64 solve、戻し補間、source dtypeへの代入については実数証明と区別する。既存の finite/正値検査と `PMLParameters` の strict `50<F0<700` を残し、失敗なら原本を保全する。min/max・線形系残差は診断として保存してよいが、通常の浮動小数点残差だけで厳密包含を証明したとはしない。再clip、jitter、別solverへの救済切替はしない。

**50 Hz以下は今回のPML保存表現の対応範囲外であって、生理的に不可能・非物理と判断したのではない。** 原候補の真のF0誤差は未測定である。範囲保存はF0精度・MOS・native完遂の改善保証ではない。旧結果で最初に保存F0のgateへ到達して止まったことから、未到達の保存・復号・品質条件まで成功認証しない。full SPEC/PDDは全dumpされていない。[既存解析と下流呼出し](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_analysis.py)、[既存保存制約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/parameters.py)

## 3 ρ を固定する理由と留保

無限等間隔 grid の内部応答は `H(ω)=1/[1+4ρsin²(ω/2)]`。既存 source の `fc=(1/step)/4`、`hshift=(1/fc)/8` から、正の mean step に対し `ωc=2πfc·hshift=π/4`。従って提案ρなら `H(π/4)=1/2` となる。名目5 ms rawでは内部400 Hz・fc50 Hzだが、この正規化の関係はREAPERにも適用できる。

これは既存 Butterworth の単方向設計点1/√2を往復した内部定常利得1/2を、**先験的な一点 anchor**にするだけである。finite自然端点には単一LTI応答を割り当てられず、全経路の有限列の50 Hz利得一致ではない。D1は低域でも二次減衰を持ち、Nyquistの利得も正であり、元8次Butterworth往復とは通過域・阻止域・端点が変わる。結果をリンギングの有無だけへ帰属しない。[SciPy 1.17 butter](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.signal.butter.html)、[SciPy 1.17 filtfilt](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.signal.filtfilt.html)

ρ は生体最適値・観測から推定したnoise比・全帯域同等性の根拠ではない。初回3件の音質は未計測であり、その品質へρを合わせたものではない。ただし失敗観察を受けて生まれた案なので、同じ3件の結果を独立検証と呼ばない。

Gaussian観測誤差とGaussian増分を仮定すれば、ρを分散比とする解釈は可能である。しかし増分priorは水準方向にimproper、観測項を加えたposteriorはproperで、その平均/MAPがzとなる、という区別が必要。実際のyはhard選択・補間・clamp後であり、そのGaussian仮定が成立したとは主張しない。priorの任意定数を放置して周辺尤度/Bayes factorへ流用しない。posterior標本の範囲まで保証するものでもない。

## 4 最小実装境界への判定

既存 `analyze` は105行で元postprocessorを必ず呼び、processed-F0を直接受ける公開APIがない。したがって、正式vendorを変えずに既存関数の後半だけを実行時に共用することはできない。**現実的な最小案は、未採用Library専用の明示named analyzerへ必要部分だけを系譜付きで転記し、既存公開helperを再利用すること**であり、codec全体を複製する必要はない。

- 旧PMLは元 `analyze` 呼出しを維持し、first3は既存nativeをbyte再利用する。新R/L/Fだけが同じ明示D1 analyzerを使う。
- `analyze` 102..126行の検証と下流処理を維持し、105行のpostprocessor呼出しだけを明示D1へ替える。`analyze_pdd`、`noise_mask`、StoneMask、CheapTrickを再利用し、StoneMaskはCheapTrickだけ、PDD/保存/合成はpost F0、SPECはsqrt(power)という区分を変えない。
- 新postprocessorは元 `f0_postprocess` 15..47行および50..78行の契約を保持し、48..49行のButterworth/filtfilt部分をD1 solveへ替える。rawの検証、非正値補間、既存clamp、内部grid、戻し補間、dtype代入、jitter判定とresampleは黙って整理・変更しない。
- `SOURCE_LINEAGE` に上記両方の転記範囲、元commit/blob/ライセンス、新関数、intentional diff、追加診断を列挙する。元bodyの参照/転記であることを明記し、無変更の実行時共用と称さない。
- RのrawにはL/F専用の `J×2`・厳密5 ms grid検証を適用しない。Rは保存されたREAPER由来rawをそのまま新postへ渡し、その後の保存post gridを既存規則で検査する。L/Fは元J/grid/値を維持する。
- 科学関数のmonkeypatch、暗黙のsolver/候補切替、D1後の元analyze再投入による二重filterは禁止する。一方、専用単一processで既存warnings/logger captureを限定scopeで使い、finallyで復元することは、全warning/error保存のため許容する。新logger機構を発明するゲートにはしない。

solverは静的sourceで一つに固定する。例えばSPD帯行列用の `solveh_banded` は構造に適合するが、帯格納、引数、ρのfloat64生成順、overwrite/finite検査を記録し、実測結果で別solverへ切り替えない。これは実装選定の候補であり、本レビューでは呼び出していない。[SciPy 1.17 solveh_banded](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.linalg.solveh_banded.html)

## 5 first3 原本再利用の可否と比較の意味

**旧原本の再利用と、新モデルによる新たな解析・合成を分離すれば妥当である。** 旧IIRの成功/失敗9枝を再実行せず、既存のR/L/F rawと既存PML nativeをbyte再利用する。新D1のR/L/Fだけを別source・別receipt・別artifactで再解析・合成する。これは元runの修復成功ではなく、新しい開発実験である。本稿はその実行を許可しない。

原本の実pathは `branches/{pml,L,F}/raw_f0.npy` で、架空の `/trace` を挿入しない。R rawのframe数1195/1196/814と、元postの1194/1195/814、L/F rawの1200/1200/818を混同しない。rawを再生成せず、受領ZIPのmember hash/shape/dtype/時刻をpreflightで識別する。元のraw/submitted/selectorの役割が異なる場合も、同じ由来と決めつけず対応を記録する。

概念上は R/L/F×IIR/D1 の6条件。ただしfirst3の旧L/F-IIRには音声がないので、全て新D1が成立した場合の品質主比較は **元PML、R_D1、L_D1、F_D1の4音声**である。

- `F_D1−L_D1`：新post下の系列選択差。
- `F_D1−R_D1`、`L_D1−R_D1`：同post下の選択器差。
- `R_D1−元PML`：同じREAPER rawに対するpost変更差。
- `F_D1−元PML`：選択器とpostを含む総合差。これだけで系列Fの優位を言わない。

R_D1だけが良い可能性、L_D1がF_D1より良い可能性、全て悪い可能性を残す。旧L/F-IIRの品質差やpost×selector交互作用は未定義のまま。新4音声の比較が終わっても、旧6セルの完全factorialを完遂したとは呼ばない。

全成功時のfirst3は4音声×3録音×4指標の48枝別raw値に、親の指定する原音3値を加える計画になり得る。これは取得保証ではなく、原音3値の指標・区間もsource/schemaで明示する。native完遂率とquality可用性を分け、指標ごとに実分母・失敗stage・未計測を表示し、失敗を0点へ変換しない。条件別成功集合の別々の平均から改善を主張しない。

first3は開発比較としてのみ扱い、採用しない。後段では固定120全件の予定分母・実成功・全失敗を報告するが、旧studyの未実行117件を黙って再開しない。新studyの段階承認が必要で、元phase B/117 gateはそのまま残る。新D1のsource準備と、旧studyのgate解除を混同しない。

## 6 五仮想専門役による追加二巡

以下は補遺だけの二巡である。五役は一人の机上検討であり、独立した五人の査読ではない。別途の独立数学レビューは上記文書を読み、主定理・ρ・有限端点・解釈限界の確認に用いた。

### 第1巡 異議

- **確率モデル役**：D1を新posteriorと称すなら、improper水準prior、人工的なGaussian観測仮定、既存局所potentialとの非同一性を説明する必要がある。selector λと平滑ρの混同を禁ずる。
- **音響役**：一点合わせは知覚最適を意味しない。低域減衰・阻止域・端点が変わるため、成功差をリンギングだけへ帰属できない。ただし独立音響誤差予算なしで静的sourceすら書けないという制約は過剰。
- **数値解析役**：自然端点、未除算D、SPD構造、solverと演算順が必要。実数凸包とfloat64厳密包含を混同せず、再clipで成功へ変えない。
- **実験計画役**：first3は既観測の開発集合。元raw・PML音声の再利用で不要な再計測を避ける一方、R_D1対照と未定義の旧品質差を明示する必要がある。
- **懐疑的批評役**：これは失敗後の新仮説であり、成功したら元候補の正しさが示されたという物語を拒否する。R_D1だけで十分という結果も受け入れる設計にする。

### 第2巡 修正後の判定

- **確率モデル役**：線形Hzの明示推定量、固定ρ、元L/Fの凍結、proper posteriorとimproper priorの区別を条件にsource準備を支持。周辺尤度やF0精度の認証には反対。
- **音響役**：既存往復設計点の先験的anchorを、非最適な工学仕様として受容。人工clock/testを新設せず自然音声を評価対象とする設計を支持。採用前のMOS・標準比較・制御確認は免除しない。
- **数値解析役**：独立レビューと最大原理を確認し、数式側にsource準備を妨げる不整合は認めない。Rの700境界、float64、後続失敗の留保を残す。
- **実験計画役**：元PML＋新3枝、原本reuse、first3開発表示、固定120の全分母/失敗報告を採用。成功例だけでのquality一般化と旧studyの暗黙再開を認めない。
- **懐疑的批評役**：系譜付き最小adapter、R別grid契約、旧analyze不変なら静的source準備には賛成。元失敗の修復・同等置換・採用・科学launchの承認にはならないという異議を維持する。

## 7 未解決事項を三段階に分ける

### source準備を止める具体的不整合

数式と設計方針に、静的source準備そのものを止める既知の不整合はない。下記はコード化時に解消すべき明確な誤実装で、候補sourceの受入れ前に静的レビューする。

- RをL/F専用fixed-J adapterへ渡すこと、誤ったartifact pathを使うこと。
- DをΔtで割る、周期/固定端点へ替える、ρとselector λを混同すること。
- 元postの前後処理を無断変更する、二重filter、monkeypatch、暗黙solver切替をすること。
- 系譜・ライセンス・intentional diffを残さず下流bodyを複製し、正式PMLと称すること。

これらを避ける具体案は本稿にあるため、人工clock・新誤差予算・新logger発明を追加のsource準備ゲートにしない。

### 実行前確認

- 新sourceの固定hash・各module400行以下・SOURCE_LINEAGE・schema・独立静的レビュー・通常のLibrary保存receiptを確認する。test/smoke/importによる試験はしない。未採用codeはGitへ移さない。
- 原本raw/nativeのmember識別とhash、元入力区間/manifest、解析/復号seed0、L/FとRの別grid契約、返却時刻・n_samples・FWCEP/NM/save/load/decode契約、例外/全warning/errorの保存を確認する。
- ρのfloat64生成と実値保存、固定solver/帯格納、観測診断、保存容量・資源・外側終了receipt・exclusiveな新artifactをsourceへ固定する。元artifactを追記更新しない。
- quality backendの公式source/重みhash、固定区間、指標方向、計画分母を確認する。51値という計画で未取得値を成功扱いしない。
- 新モデルの科学launchは親の別判断とreceiptを必要とする。source準備完了はその代わりではない。

### 採用前の品質と制御確認

- first3だけでは採用しない。固定120全件の実分母・失敗・話者内/話者間等重み・指標ごとの共通集合を報告する。自動MOS等の方向一致だけで知覚的有意差や真のF0精度を認証しない。
- 同じpostの選択器差とpost変更差を分離し、R_D1単独で十分という結果も隠さない。旧L/F-IIR品質がない限界を残す。
- 既存標準方式との条件一致比較、必要な±3半音等の制御・境界・出力長/レベル・編集後品質を確認する。native保存可能性だけでbaseを変更しない。

**最終推奨**：D1を新しい未採用モデルとして静的source準備することは妥当。現在行ってよい作業の範囲は別途の親指示による。元の科学失敗、phase B、残117件のgate、正式PML、元source/結果は変更しない。本補遺ではコード実装、数値probe、人工入力試験、再解析、再合成、品質計測、Git/Cloud/Library書込みを行っていない。
