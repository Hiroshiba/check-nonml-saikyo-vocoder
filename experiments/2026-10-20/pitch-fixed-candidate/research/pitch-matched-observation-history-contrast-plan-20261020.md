# 同一保存観測の条件間対比：次の最小保存値診断計画

2026-10-20。紙上設計のみ。実集計、差分計算、BF/r/exp/log、再追跡、candidate実行/import/testsは行っていない。実施には別途のsource・input・算術契約と開始判断が必要。

## 1. 最小の新しい問いと既存結果

**同じ現在観測・同じ候補BFに対して、異なる旧履歴の凍結priorが作るpair log oddsの差は、S→Lの数値再現変更とL→Eの積分変更でどう変わるか。**

旧history報告はU-U/E-Uの共通後半49完全窓における旧A/BのMAP不一致・一致を既に調べている。同じ「履歴依存が存在するか」だけを再集計しない。新しい対象は、保存済みS/L/Eにおける **条件間log odds差と、その差の変化** である。

読んだstage2 schema/summaryにはframe内・prior別のDとL−S/E−L/E−Sがあるが、以下の100対応ペアをjoinした条件間差の表は確認できなかった。現時点で同じ問いが完全に解かれているとは判断しない。Cloud補足の符号反転件数とは重複させず、先にその成果範囲を照合してから実施する。

## 2. 条件記号と固定100ペアの異なる役割

原history契約ではUは倍音{2,3,4}、Eは{2,4,6}の人工ブロック。U/Eは有声/無声の略ではない。clean最小周期F0はUがf*=97.65625 Hz、Eが2f*。各条件は前半8192標本／後半8192標本、共通雑音と共通scaleを使用し、同じ初期状態から独立に処理する。

### H群：履歴の違いを読む50ペア

固定orientationを **E-U minus U-U**、frame53..102とする。

- 現在は同じ後半U観測。E-Uは前半E、U-Uは前半Uなので、それ以前の観測履歴が異なる。
- frame53..101の49件はsecond_complete。102はpadding。
- これは同一現在観測を条件に、保存された旧履歴由来priorの違いを読む比較。
- 102も事前固定集合に残すが、clean正誤ラベルを付けない。

### C群：因果順序の対照50ペア

固定orientationを **E-U minus E-E**、frame0..49とする。

- 前半E、共有雑音、初期状態、当該時点までの観測履歴が同じ。異なるのは未観測の後半U/Eだけ。
- frame2..49の48件はfirst_complete。0/1はpadding。
- 因果的なforward処理なら、将来ブロックの違いだけでこのprefixのpriorや出力は変わらないはず、というnegative control。
- この50件を「異なる履歴効果の追加50反復」と呼ばない。

以上の100ペアを固定し、効果の大きいframe、符号反転frame、有限Aだけ等へ選別して置き換えない。主要履歴比較はH49（53..101）、主要negative controlはC48（2..49）とし、padding3ペアは別枠で全100件の台帳に残す。窓が重なり共通雑音を使うため、100独立反復ではない。

## 3. 使う保存字段と同一性の停止条件

stage2 `frame-results.jsonl` の実schema：

- frame_index、condition、frame_id、support_class、time_seconds、observation_sha256。
- reference_ids、full20_complete、missing_keys、index_pointer。
- priors[static_frame0 / A_prediction_frozen / B_log_prediction_frozen]。
- 各priorのinput_pointers、support_masks/counts。
- evaluations[S/L/E].D、G、K_log_distribution。
- differences[L_minus_S / E_minus_L / E_minus_S]。

unique-resultsとindex/referenceを辿って、同ペア20候補のunique_id、K/r bits、旧S bitsの同一性を確認できる。重複監査はH群50frameとC群50frameについて全20セルのcod/J/fit/S一致を報告している。元NPZ未添付の留保は維持する。

実施前の読取検査：

1. 固定100pair IDを生成し、各条件・frameが一度だけ対応すること。
2. 対応観測hashをpinned frames原字段まで辿り、hash対象範囲・dtype等の定義を固定する。全20参照の候補軸（f_index48/148、各K1..10）とunique_id、K/cod bits、旧S bitsを比較する。条件別reference_idそのものの一致は要求しない。特に旧公開報告の49完全窓だけでpadding102の観測同一性まで独立確認済みとしない。
3. static frame0 priorが対応条件間で同じ保存値であること。frame1以降のinitial帳簿zeroは使用しない。
4. C群のA/B priorは元input pointerから保存bitsの同一性を確認する。stage2数値の差だけで元priorの一致を代用しない。
5. stage2/output/index/v1/sourceのpinsと完了receiptの確認。

不一致なら黙ってそのpairを除かず、固定台帳に理由を残し、当該群の意図した解釈を停止する。C群の不一致は未来情報漏洩の即断ではなく、join、保存来歴、初期状態、演算順・処理条件等の調査が必要という反証警告にする。

selected20値の一致は観測hashの代用でも、全grid・全過去状態の一致証明でもない。Cの因果順序は元刺激契約の共通scale・prefix入力と同じ初期状態・処理条件を根拠とし、同時点の候補一致から推論しない。C一致も選択20候補・保存量の整合に限定し、全grid/VUV/内部全状態の一致や一般的な未来漏洩不存在を証明しない。

## 4. 向きを事前固定した対比

D_x^(c,s)を、条件x・同frame・prior c・評価sに保存された **log(f*/2f*) odds** とする。cはstatic/A/B、sはS/L/E。三priorを混合しない。

H群の条件差：

    H_s^c = D_E-U^(c,s) − D_U-U^(c,s)。

H<0ならE-Uの方が同じ現在観測に対して2f*側へ相対的に寄る。正解率・改善の意味ではない。

C群の条件差：

    C_s^c = D_E-U^(c,s) − D_E-E^(c,s)。

以下では各群の条件差をX_s^cと書く。Dは保存十進文字列が表す値として減算する。保存within-frame差 `differences[t]` の十進値をg_x^(c,t)と定義し、interactionの正本は次だけとする：

    I_t^c = g_E-U^(c,t) − g_b^(c,t)
    b = U-U（H群）またはE-E（C群）
    t = L_minus_S / E_minus_L / E_minus_S。

標準表示は順にnumerical / integration / total interactionとする。数学的な理想式では、例えば積分interactionはX_E−X_Lである。しかし保存Dと保存within-frame差は別々に丸め・文字列化されているため、保存十進値について厳密な恒等式とは限らない。今回は **保存gの条件間減算のみ** をIの正本とし、Dからの再合成、closure残差、逆方向は計算しない。I_total=I_numerical+I_integrationも強制しない。

表示名はXを「保存十進値の条件差」、Iを「保存within-frame差の条件間差」とする。S→Lは旧保存値との数値再現差、L→Eは既存の理想Laplace対exact式の差という来歴を保持し、新しいBF評価は行わない。

interaction<0ならL→Eによって条件間のf*/2f*対比がさらに負方向へ動く、>0なら正方向へ動く。これは純粋な「履歴効果量の因果推定」ではなく、**凍結された旧priorとBF変更の条件付き相互作用を表す算術対比**。履歴差をtransition・memory・H0・丸め等へ因果分解しない。

staticは同じ観測・同じ保存priorなら両群でX=0となる整合性対照。C群はA/Bも履歴同一ならX=0が期待される。いずれも今回実測で0を確認したとは主張しない。

## 5. zero・∞・欠測

- 対応する両frameのfull20_completeがtrueでなければ、全priorの比較をmissing。完了Kだけの再正規化は禁止。
- Dが有限同士の場合のみ条件差Xを有限減算する。
- 機械schemaは既存kind/decimal/reasonを使う。必要入力にmissingがあればmissingを優先し、undefinedならundefined。どちらかのDが±∞なら元Dタグと支持maskを保持し、条件差は `kind=undefined, reason=nonfinite_condition_contrast`。同じ∞同士を0にしない。拡張実数で差を定義できる場合も、本診断では有限対比だけに限定する。
- I[t]には、その方向に必要な両評価のXがfiniteであり、両条件の保存g[t]もfiniteであることを要求する。必要入力にmissingがあればmissingを優先し、それ以外の非finiteはundefinedとし、不足元字段をreasonに残す。AのzeroをBで補修しない。入力欠測と算術trapによるrun failureは区別する。
- C群で同じzero mask・同じ±∞が確認されても、「finite差が0」とは書かず「支持・タグ一致」とする。
- Aの有限pairが少なくても、後から対象frameを増減しない。有限/非適用/欠測の分母を群・prior別に示す。

同じK/rのscalar差は共有済みでも、K重みが異なるため周辺化後のE−Lは条件ごとに異なり得る。必要なK分布は既存 `K_log_distribution` へのpointerを残すだけとし、新KL/TV・exp・距離指標を追加しない。

## 6. 最小成果物・不要な計算・停止

将来実施する場合の正本は固定順100pairのcanonical JSONL。各recordに3priorのX三値・I三値とタグを持たせ、必要列だけをlong-form `(pair_id,group,frame_id,prior,evaluation/direction)` の単一CSVへ転記する。全表の二重複写やG/K分布の大量複写は不要。

字段は両入力pointer、観測・候補・prior一致検査、support_class、full20、元D/tag、X/tag、標準3interaction/tag、zero/missing理由。C群の不一致とstatic不一致は例外表に全件残す。原値は変更しない。

要約は群・prior別の固定件数、finite/nonfinite/missing、保存値の符号・range・該当ID程度。時間順の全行を残し、都合のよいframeだけを引用しない。母集団CI、p値、bootstrap、独立標本推論、効果割合は出さない。符号反転の集計はCloud補足と重複実施しない。

**不要**：新BF/精度gate、r再算出、exp/log/LSEの再計算、候補追加、H0/VUV正規化、波形・音声生成、filter再追跡、prior交換実験。

### 固定算術契約と一回予算

- stdlib Decimalの新規明示contextを `precision=256, ROUND_HALF_EVEN, Emin=-999999, Emax=+999999` に固定する。finite入力は保存十進文字列からexactに構築し、floatを経由しない。原文字列は保持する。
- Inexact、Rounded、InvalidOperation、DivisionByZero、Overflow、Underflow、Subnormal、Clamped、FloatOperationをすべてtrapにする。Roundedだけの発生も拒否し、特殊値混入を拒否する。
- 許可算術は上記X/Iの有限Decimal減算だけ。構文・型・hash・bits・集合・順序・件数・符号・大小の照合は許可する。BF/r/LSE/exp/log、新精度評価、再追跡は禁止する。
- 出力はfloat変換、再丸め、quantize、normalizeを行わない。有限ゼロの出力decimalは `"0"` に統一し、入力の符号付きゼロを含む原文字列はpointerで復元可能にする。
- 256桁が全入力に十分とは事前保証しない。trap、不正finite、入力不整合、予算切れは即全体停止し、pins、完了行、停止理由と全予定IDの停止/未着手状態を保存する。精度自動増加、自動retry、失敗行除外による完了扱いは禁止する。
- 一回60秒、算術締切50秒、残りは停止・保存用。子processを作らない数値worker単体128MiB、出力8MiB。supervisorは別計測し、process tree全体のOS保証とは称さない。必要memberを逐次読み、巨大な全原データ複写を要求しない。予算内完了は机上では未実証。

成功時の主張は「固定contextで丸めを発生させず、保存十進値を減算できた」に限定する。元80桁BF・LSE・priorの真値精度や符号の保証ではなく、noncertifiedのままである。現時点ではその減算も行わない。

停止条件：入力pin/候補/観測同一性に不整合、対応不足、未承認の算術や実行環境、保存上限不足、および上記trap/締切。停止後に新BFや再追跡へ自動移行しない。予期したmissing/undefinedは通常出力でありrun failureと混同しない。全固定100pairの検査と規則どおりのX/Iまたは欠測理由、pin/receiptを保存した時点で完了し、原因探索・モデル変更へ拡張しない。source・入力・数理レビューと別開始指示を要する。

## 7. 五仮想役・二往復

一人による机上点検であり、独立五名の査読ではない。

### 第一往復

1. 入力役「100件とも履歴差か」→時系列役「prefix50は過去も同じ。H群とC群を分離」。
2. 数理役「全pair差が負なら履歴interactionも負か」→批判役「条件差の差の符号は別。事前定義して未計算とする」。
3. 状態役「BでAのzeroを回復できるか」→入力役「別prior条件。Aの∞はそのまま非適用」。
4. 評価役「共通観測なら独立paired CIか」→時系列役「重複窓・共有雑音。記述のみ」。
5. 批判役「旧historyの再報告では」→数理役「旧MAP履歴依存は再主張せず、S/L/E変更へのinteractionに限定」。

### 第二往復

1. 入力役「paddingを落とそう」→批判役「固定100から事後除外しない。別supportタグ・cleanラベルなし」。
2. 数理役「∞−∞を同じだから0にする」→状態役「支持一致と有限対比は別。undefinedとreasonを保存」。
3. 状態役「H差をmemoryの因果効果と呼ぶ」→時系列役「凍結prior全体の履歴関連差。機構別帰属は未同定」。
4. 評価役「Eで正解側へ動けば改善」→批判役「subset・人工・固定旧履歴。全grid品質ではない」。
5. 批判役「C不一致は未来漏洩の証拠」→入力役「まずjoin/pins/初期条件等を調査。不整合を特定原因へ即断しない」。

## 8. 読取資料

- `pitch-bf-selected-deduplication-audit-20261020.md`：固定100ペアの候補同一性と非独立性。
- `pitch-matched-observation-history-contrast-independent-review-20261020.md`：保存g正本、有限対比限定、Decimal trap、一回予算の指摘を反映。本文修正のみで実算術は未実施。
- stage2 `output/schema.json`、`frame-results.jsonl`のschema、`summary.json`：保存D・三差・タグの存在。新たな条件間集計は未実施。
- [history入力・観測支持契約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/5a2f4761dc9d68edefd580cdb1b3178ced53a642/experiments/2026-10-20/pitch-history-log/research/history-execution-contract-ja.md)：U/E定義、共有雑音、独立初期状態、窓支持。
- [log-state契約](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/5a2f4761dc9d68edefd580cdb1b3178ced53a642/experiments/2026-10-20/pitch-history-log/research/log-execution-contract-ja.md)：旧A BFを用いるforward B状態。
- [既存history報告](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/5a2f4761dc9d68edefd580cdb1b3178ced53a642/experiments/2026-10-20/pitch-history-log/README.md)：旧49完全窓のMAP/分布比較と限界。
