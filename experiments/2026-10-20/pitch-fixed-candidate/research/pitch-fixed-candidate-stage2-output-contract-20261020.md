# 固定候補 stage2：保存値集約の出力契約案

2026-10-20。紙上schema提案。実装・実行・import・tests、BF/r/exp/odds計算は行っていない。stage2開始指示ではない。資源上限・実行環境・sourceは後続レビューで固定する。

## 0. 要旨

出力を **unique評価単位** と **元参照・frame・prior条件単位** に分ける。

- S=旧保存logBF、L=stage1のL80、E=stage1のA80。
- 標準表示・要約は **L−S / E−L / E−S** に統一する。
- 全6方向はtarget−sourceを明記したlong-formとして保存し、逆方向を別実験や追加標本に数えない。
- frameの比較は全20セルのstage1成功を要求。prior zeroを理由に失敗セルを除外しない。
- missing、数学的zero、±∞、未定義を別表現にし、数値0へ置換しない。
- static / 旧A予測prior / 旧B log priorは別条件。旧B履歴を固定した反実仮想であり、新BFによる再追跡ではない。
- 対象は選択された人工309frame。母集団CI、独立標本を仮定した検定、有効標本数推定を出さない。

## 1. 読取根拠と入力軸

凍結計画 `pitch-fixed-candidate-frozen-plan-20261020.md` と、次のindexディレクトリを参照した：

`pitch-fixed-candidate-source-review-20261020/pitch-fixed-bf-index-20261020/`

実際に読めた先頭recordのschema：

- `unique.json`：unique_id、K、r_bits、r_hex、ratio、owner、reference_ids、saved_logBF_bits。
- `references.json`：condition、frame_id、f_index、K、reference_id、unique_id、owner、A_selected_line_1based、B_selected_line_1based、static_A_selected_line_1based。
- `frames.json`：frame_index/B_frame_index、condition/frame_id、時刻・support、cleanラベル、energy、旧H0記録、observation hash、原本参照、reference_ids、prior source等。
- `audit.json`：4180 unique、6180参照、309frame、owner件数1394/1393/1393、単独2180・二重2000、旧S衝突0、旧1080支持との交差0を報告する。

旧scalar保存形式の `stages["50"/"80"].A/Q/L.logBF`、details、元delta字段、status、counts、event journalを参照する。stage1新adapterの最終schemaは別レビュー対象なので、これらへの具体的member/key mappingをstage2入力manifestに固定する。

この文書はindex全件の再監査や実stage1結果の検証を代替しない。元NPZ未添付という入力来歴の留保も維持する。

## 2. 入力pinと採用

必須manifest：

- v1 ZIPのLibrary ID/version/file ID、bytes/SHA256。
- index/source/dependency/各stage1 owner結果のbytes/SHA256とreceipt参照。
- 旧S・各priorの原ファイル/member/lineへの参照。
- unique_id→owner→採用rowの唯一対応。
- stage2算術設定、schema version、出力ファイルのkey/単位/方向定義。

唯一ownerはunique_id mod3。別owner、重複attempt、未知pin、index不整合はfail-closed。値の大小による採用元選択をしない。

成功はstage1の `matched_noncertified` の保存判定を使用し、六値・status・diagnosticsのjournal整合を読取確認する。新BF・新gate判定は行わない。既存partial値はraw履歴に保存してもL/Eの採用値にしない。

Sはv1の保存binary64を正とする。unique indexのsaved_logBF_bitsとの一致を確認し、参照ごとの旧Sの来歴を残す。同keyで一致するscalar差を共有しても、priorや周辺化結果は共有しない。

## 3. 数値表現と80桁算術

### 入力

- A50/A80/Q50/Q80/L50/L80等の元数値文字列を無変更で保持する。
- Sと保存通常prior、保存B log priorはbinary64 bits/hex/整数比を保持し、整数比から多倍長へliftする。
- rは入力識別に使用するだけ。J/energyから再算出しない。
- B log priorはlog値としてliftし、通常確率へのexp→log往復をしない。

### 算術

提案する固定精度は凍結計画どおり80 decimal digits。許可演算は保存値の加減算、正priorのlog、安定化LSEで必要なexp/log/log1p、条件付き正規化等のみ。BF特殊関数、級数・不完全beta・求積・Laplace再評価、r再算出、状態再帰は禁止。

LSEは有限最大項を差し引く等の安定化方法をsourceレビューで固定する。全項−∞を通常式へ投入せず、支持判定で分岐する。負のprior、非finiteな本来有限入力、未知タグは停止する。

出力の導出値は80桁精度の結果を復元可能な十進文字列で保存し、float/binary64へ短縮してからcanonical保存しない。表示用短縮文字列は別字段とする。sourceの丸めモード・桁数・シリアライズ設定をmanifestへ明記する。

80桁算術は真値精度・保証区間を意味しない。特に有限精度LSEで極小寄与が消えることと、数学的prior zeroを区別する。新しい許容誤差を結果に応じて導入しない。後段演算の丸めとoddsの誤差解析は別担当・別文書の対象。

### tagged number

JSONに非標準NaN/Infinityリテラルを出さない。数値欄は次の共通型を使う：

- `kind=finite`、`decimal="..."`。
- `kind=positive_infinity` または `negative_infinity`、decimal=null。
- `kind=missing`、reason、関連unique_id一覧、decimal=null。
- `kind=undefined`、reason、decimal=null。

保存prior zeroはprior原表の `support_zero=true` とbitsで示す。対応log weightの−∞とは区別する。通常確率表示が0になっても `display_underflow=true` を付け、support_zeroに変更しない。

CSVは各量に `value_kind / value_decimal / reason` を置き、null相当の空欄を0として読むことを禁止する。

## 4. 六方向差

すべて `value = target − source` と定義する。

| direction_id | target | source | 内容 | 標準 |
|---|---|---|---|---|
| L_minus_S | L | S | 数値再現差 | yes |
| E_minus_L | E | L | 積分近似差 | yes |
| E_minus_S | E | S | 総置換差 | yes |
| S_minus_L | S | L | L_minus_Sの逆方向 | no |
| L_minus_E | L | E | E_minus_Lの逆方向 | no |
| S_minus_E | S | E | E_minus_Sの逆方向 | no |

標準3方向は指定された引数順で独立に減算する。逆3方向は対応する標準値の符号反転として保存し、`derived_as_reverse_of` を付ける案とする。後段のsourceレビューでこの規則を固定する。

stage1の保存 `delta_A80=L−E` / `delta_Q80=L−Q` は `raw_kernel_delta_*` として原名・原文字列を保持する。後段80桁で計算したL_minus_Eと、内部値から作られた元delta_A80は、表示文字列読込み丸めのため最終桁が異なり得る。原字段を上書きしたり、完全一致に強制しない。

有限値では合成残差 `(E−S)−[(L−S)+(E−L)]` を帳簿上の診断欄に保存してよい。ただし0へ強制せず、BF真値誤差や新成功gateとして使用しない。新たな閾値を本提案で選ばない。

scalar差が正ならtargetのlogBFが大きい。後段pair差が正ならtargetの方がf*/2f*のlog oddsを増す。いずれも正解・品質改善を意味しない。

## 5. 三priorとframe計算

prior_idは固定で `static_frame0`、`A_prediction_frozen`、`B_log_prediction_frozen`。

- static：同条件frame0の保存initial_prior_payload。referencesのstatic行参照から取得する。
- A：当該frame/cellの保存prediction_prior。正値ならlog、zeroなら−∞。
- B：同IDの保存log_prior。既存log状態Bの過去軌道を固定する。

各prior原表にはsource member/line、保存bits/hex、元字段名、`representation=probability|log_probability`、support_zero、派生log weightを持たせる。後続initial payloadの帳簿zeroは一切使わない。H0字段はmetadataとして保持できるが、今回の正規化へ投入しない。

frame/prior/evaluation s=S,L,Eごとに、

    G_a = LSE_K(b_ak+s_ak)
    D   = G_fstar−G_2fstar
    log w_ak = b_ak+s_ak−G_a

を定義する。必要ならpair内の周波数log確率を

    log p_a = G_a−LSE(G_fstar,G_2fstar)

として保存する。これはH1の固定20セルsubset内条件付き量であり、無条件P(f*)、全gridのP(f*|H1)、H0/VUVではない。

各frame/priorでS/L/EのDが有限な場合、六方向のpair差を同じtarget−source規則で保存する。標準表示はD_L−D_S / D_E−D_L / D_E−D_S。K分布は全10成分のlog確率を保存し、勝手なK差平均で周辺化を代用しない。K分布間の追加距離指標は本契約に含めない。

## 6. 完備・zero・欠測規則

`full20_complete` は元frameの全20参照がstage1成功keyへ結びつく場合のみtrue。20参照とunique_id一覧を保存し、同じkeyの失敗を参照ごとに変更しない。

### full20_complete=false

三priorすべてでS/L/Eの比較triplet、pair差、比較用K分布をmissingとする。Sだけなら計算できる場合でも比較表を部分成功にしない。元S・prior・完了セルのpoint差は別表に保持できる。欠測unique_id、status、owner、最終stageを記録する。

### full20_complete=true

- 両側positive支持：G/Dを有限として計算。zero priorの個別Kはlog w=−∞。
- 片側全zero：そのGは−∞、Dは向きに応じ±∞。支持側のK分布は定義可能、全zero側はundefined。
- 同一prior内でD_S/D_L/D_Eが同じ無限大となっても、差を0にせず `undefined / infinite_minus_infinite` とする。
- 両側全zero：pairはundefined。両側K分布もundefined。

欠測と支持退化は別字段に保存する。例えば `full20_complete=false` でもpriorの保存支持状態は読めるため、missing理由と `prior_support_pattern` を両方保持する。

計算中の非finite・異常終了は `stage2_arithmetic_error` としてmissingにするか、全体停止するかをsource契約で先に固定する。正常な支持zero由来の−∞と算術事故を同じタグにしない。再試行・精度変更・補修はしない。

## 7. 複製可能な出力ファイル

JSONをcanonical、CSVを同じ内容のlong-form参照表とする。配列の行順だけに依存せず、次の主キーを必須とする。

### A. `unique-points.jsonl` / `unique-points.csv`

1行/key。unique_id、K、r_bits/r_hex/ratio、owner、stage1 status、全六値のraw文字列、raw delta/spread、counts、stage1出典、reference_ids。Sも保存bitsとlift元参照を付ける。partialの履歴は採用値と別欄。

### B. `point-differences.jsonl` / `.csv`

1行/(unique_id,direction_id)。source/target、standard_display、reverse_of、tagged value、元S/L/E参照、status/reason。全6方向があり、欠測でも行を落とさない。

### C. `reference-priors.jsonl` / `.csv`

1行/(reference_id,prior_id)。元condition/frame/f_index/K、unique_id/owner、source line参照、保存prior表現/bits/hex、派生log weight、support_zero。これにより重複scalar評価を元6180参照へ戻せる。

### D. `frame-status.jsonl` / `.csv`

1行/frame。frame_index、condition/frame_id、support_class、時刻、観測hash、cleanラベルと意味、20reference_ids、全key status、full20_complete、missing key一覧。source pathは来歴であり、この環境に存在するとは主張しない。

### E. `frequency-marginals.jsonl` / `.csv`

1行/(frame,prior_id,evaluation_id,frequency_id)。G、pair条件付きlog p、10個のpriorの支持数、full20_complete、支持パターン、tag/reason、参照一覧。

### F. `pair-log-odds.jsonl` / `.csv`

1行/(frame,prior_id,evaluation_id)。D、向き `fstar_over_2fstar`、finite/±∞/undefined/missing、理由、G両側への参照。必要な通常oddsのexp表示は原則省き、log値を標準とする。

### G. `pair-differences.jsonl` / `.csv`

1行/(frame,prior_id,direction_id)。target−sourceのD差、標準/逆方向、tag/reason、入力D参照、任意の合成残差参照。無限大の差とmissingはそれぞれ明記。

### H. `conditional-K.jsonl` / `.csv`

1行/(frame,prior_id,evaluation_id,frequency_id,K)。log w、prior支持zero、G参照、数値状態。通常確率の短縮表示を付ける場合も表示underflowと数学的zeroを別字段にする。全zero側・欠測frameでも全10行を残しundefined/missingを記録。

### 共通出力

schema/data dictionary、README、実行receipt、source/input/output manifest、算術precision・表示規則、出典pointer解決方法、状態定義。CSVはUTF-8、ヘッダあり、数値文字列を自動float変換しない読み方を記載する。JSONはinteger IDと十進stringを分離し、非標準NaN/Infinityを禁止する。

元stage1 raw journalは削除・上書きせず、固定package/member/hashで辿れるようにする。全rawを複製するか参照保持にするかはstage2出力予算とともに事前固定し、複製を省いても来歴は失わない。

## 8. 要約・表示

最初に以下を報告する：

1. 入力pin、4180key/6180参照/309frame、owner別成功・未達、全20成功frame数。
2. prior別の両側positive/片側zero/両側zero、finite pair数、undefined/missing数。保存支持件数と計算完備件数を別にする。
3. 標準3方向だけのscalar差min/max・正負zero件数。unique単位を主表とし、参照数で重み付けした件数は別表と明記する。
4. prior別・標準3方向の有限pair差min/max・正負zero件数、S/L/Eの有限Dの符号変化件数。D=0、無限大、undefined、missingは別カテゴリ。
5. K別・condition別・support_class別の記述表。ただし元keyが複数conditionへ属する場合、group件数は加算可能な独立人口ではない。
6. 各極値のunique/reference/frame IDと出典、欠測・停止理由、算術設定と非保証の注記。

符号は保存有限精度値の厳密な比較結果として表記し、真値の符号証明としない。新しい「ほぼzero」の閾値を後付けしない。境界・小差への解釈留保を付ける。母集団CI、p値、bootstrap、独立標本数、有効サンプル数は出さない。

標準要約では平均を必須にしない。必要な追加平均・距離・順位指標は別の定義レビューを要し、結果を見て指標を増やさない。全grid MAP・clean正答率・VUV・自然音声品質は出さない。

## 9. 完了と非主張

stage2自体の処理完了と、stage1の全key成功を区別する。全ての入力と欠測を正しく記録できたstage2でも、科学的比較が全309frameで成立したとは限らない。

旧B条件は旧BFで作られたB履歴を凍結した反実仮想。static/A/B間の結果差を純粋なBF積分近似差と呼ばない。固定2候補への変化を全gridの再追跡、F0品質改善、採用根拠へ拡張しない。

本書は出力契約の提案であり、odds誤差の解析・数値評価、実装、stage2開始は未実施。固定resource/source/index/schemaレビューと別途開始判断まで停止する。
