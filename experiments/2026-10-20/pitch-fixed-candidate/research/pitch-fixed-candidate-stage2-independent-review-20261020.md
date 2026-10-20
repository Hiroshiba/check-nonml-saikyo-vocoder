# 固定候補stage2：出力契約と安定性メモの横断レビュー

2026-10-20。対象：

- `/workspace/shared/pitch-fixed-candidate-stage2-output-contract-20261020.md`
- `/workspace/shared/pitch-fixed-candidate-odds-stability-20261020.md`

固定計画、stage1 source/index契約との関係も既存読取内容に基づき確認した。stage1は未実行。新BF/log/exp/odds計算、候補実行/import、tests、実装は行っていない。

## 0. 判定

**数理定義・dedup・支持zero・missing・全20セル完備の扱いに阻害的な矛盾は見つからない。** 出力schemaと異常時採用規則に残っていた三つの選択肢は、レビュー中に受けた親方針を第3節へ反映して固定した。この修正版をsource準備前の最小契約とする。source・資源・実行環境と実行開始は別レビュー・判断を要する。

本レビューで固定した事項は次の三点：

1. undefined/not_applicableの表現を一つにする。
2. 新しいstage2算術事故を既存stage1欠測と分離し、処理方針を固定する。
3. stage1のpointラベルだけでなく、owner成果物・journal・外部終了証拠を含めた採用規則を明記する。

出力は標準3方向をcanonicalにし、逆3方向はdata dictionaryの定義だけで十分。全表のJSON/CSV二重化、K分布の差、追加確率表示、closure等を必須化しない縮約案を第5節に示す。

## 1. 確認できた数学的整合

### S/L/Eと三差

Sは旧binary64 logBF、Lは保存L80、Eは保存A80。L−S、E−L、E−Sを分ける定義は両文書で一致する。

- L−S：同じLaplace式の高精度評価と旧実装保存値の差。
- E−L：exact式参照とLaplace式参照の差。
- E−S：置換総差。

S/L/Eは保存値であって理想真値ではない。安定性メモがη_L/η_Eを分離し、数値再現差や積分近似差に参照評価誤差が残ると明記するのは適切。

ただし旧kernelのdelta_A80が厳密に「保存L80文字列−保存A80文字列」と一致するとは限らない。kernelは内部値で減算して別に直列化し、後段は直列化されたL/Eを読み直すためである。出力契約にはこの注意があるが、安定性メモ第2節の「delta_A80=−i」は式・方向として読む旨を一文補うとよい。raw deltaは原文字列のまま保持し、後段差へ一致を強制しない。

### LSEの界

正prior支持Iが非空で、同じpriorを固定した二評価のセル差δについて

    min_I δ ≤ ΔG ≤ max_I δ

は正しい。pairでは

    m_1−M_2 ≤ ΔD ≤ M_1−m_2

となる。δの単純平均ではなくlog-weighted exponential平均であり、S→LとL→Eでは基準K重みが変わるという注意も適切。

K条件付きlog分布は正支持のKについてΔlog w_k=δ_k−ΔG。prior zeroのKの−∞同士を減算しない必要があるが、メモ第6節がこれを明示している。

全20セル共通offsetと周波数別offsetの区別、logisticの1/4上界も紙上の性質として正しい。ただしこの確率上界やK成分差を実際のstage2出力へ追加する必要はない。

### min/max界の実装時の意味

数学的界は、保存S/L/Eを実数として解釈し、その差とLSEを厳密演算した場合の恒等的な範囲である。80桁で差・端点・LSEを別々に評価した値には丸めが残る。

したがって、わずかなenvelope逸脱をBF失敗へ再判定したり、端点へclipして一致させたりしない。厳密認証区間と表示せず、計算結果の代数的診断としてのみ使う。1e−9のstage1 gateから真値誤差boundを作らない点は両文書で整合している。

## 2. 三prior・zero・missingの整合

- static：同conditionのframe0保存initial値を固定する。後続帳簿zeroを使わない。
- A：当該frameの保存prediction_prior。通常確率zeroを維持する。
- B：当該frameの保存log_priorをそのまま固定し、exp→logで支持を失わせない。

これらは同じpriorの別表現ではなく、別の固定条件である。Bを用いることをAのzero修復やexact時系列再追跡と呼ばない。

全20参照のstage1成功をframe比較の条件にする点も一致する。数学的にprior zeroのKがLSEへ寄与しなくても、失敗Kを除外してcompleteへ昇格しない。

full20_complete=falseでは、Sだけ計算可能でも比較tripletとK分布比較をmissingにする。完了セルのpoint差は別に残せる。この非対称を明示すれば矛盾はない。

片側全zero時のDは±∞として定義できるが、方式差は∞−∞なので適用不可。全zero側のK分布は未定義、支持側は定義可能。両側全zeroならpairそのものが未定義。missingと支持zeroは別字段として残す。

## 3. 親方針を反映した固定事項

### 3.1 undefinedとnot_applicableの統一

出力契約のtagged numberはfinite/±infinity/missing/undefined。一方、安定性メモと凍結計画は∞−∞をnot_applicableと呼ぶ。数学的矛盾ではないが、schema未固定だと条件ごとにタグが変わる。

固定する機械表現：

- number.kindはfinite / positive_infinity / negative_infinity / missing / undefinedの5種。
- ∞−∞はkind=undefined、reason=infinite_minus_infinite。
- 全zero群のK分布はkind=undefined、reason=zero_support_group。
- stage1失敗はkind=missing、reason=stage1_incomplete等。

not_applicableという別kindやapplicability字段は追加しない。表示だけ「比較対象外」とし、機械字段はundefinedとreasonへ統一する。数値0は代用品にしない。

### 3.2 stage2新規算術事故

出力契約第6節は「missingにするか全体停止するかをsourceで固定」と未決定。ここは結果後に選べない。

親方針により、未知タグ・負prior・本来有限の入力異常・owner/journal/pin不一致・予期しない算術非finiteは**即時に全体停止**する。既存stage1欠測だけは既定のmissingとして通常出力できる。

停止前のstage2 partial出力・例外・処理位置は保存し、正常完了receiptを出さない。既知の−∞支持分岐は事故ではない。精度変更・自動retry・一部再正規化で続行しない。

### 3.3 stage1成果物の採用層

出力契約はmatched_noncertifiedをpoint成功として使う一方、stage1実行契約には外部実wait、reap、上限内終了等のrun採用条件もある。point_doneだけで外部終了証拠を無視してはいけない。

stage2入力manifestで少なくとも次を分ける必要がある。

- artifact整合性：唯一owner、pin、journal、台帳、raw参照が一致し、外部process終了が確認されているか。
- run状態：全owner成功か、予算・例外によるpartialか。
- point状態：そのkeyの完全なA/Q/L一式と保存成功ラベルがあるか。

今回の第一候補は、全完了成功のowner成果物だけを採用する条件とする。不完全owner中のmatched pointは自動救済しない。

不完全ownerを扱う場合は、外部終了・reap・最終保存・journal整合を別途監査し、その監査で明示的に許可されたsnapshotだけをstage2入力manifestに列挙する。snapshotはowner、package/member/hash、監査receipt、採用可能なpoint集合と状態を固定する。実行中ファイルや「最新」pathを参照しない。

unknownの残るownerをpointラベルだけで成功数へ混ぜない。許可snapshotがない場合はstage2の採用対象外とし、通常のBF missingに黙って読み替えない。sourceは入力manifestの許可集合を検証するだけで、実行中に救済可否を判断しない。既存raw・失敗履歴は採否に関係なく保存する。

## 4. 過剰または任意の出力

### 六方向

逆方向は独立の診断ではない。canonicalに標準3方向を保存し、逆方向はdata dictionaryで「対応標準値の符号反転」と定義すれば十分。逆方向の行を保存しないことは情報損失ではない。raw kernel deltaは別の来歴としてそのまま参照保持する。

### JSON/CSV全表二重化

8種の表を両形式で持つ必要はない。canonical JSONLを正とし、主要なpoint/pair結果だけCSVに出す。CSVは派生表示であり、canonicalと別計算しない。

### 追加指標

次は初回の最小実装では不要：

- K分布間の距離、全K成分の方式差、K_i/K_j全組odds。
- pair通常確率・通常oddsの追加exp表示。
- 全逆方向のmin/max、件数。
- point/pairのclosure residualの必須保存。
- 多数のcondition×support×K交差表。
- logistic上界を実データへ適用した追加保証表。

S/L/EのG/D/K log分布と標準三差を保持すれば、必要性が後で明確になった追加診断はrawを失わず定義できる。今は追加研究範囲へ広げない。

closure residualやenvelopeは有用だが成功gateではない。最小契約ではclosureを任意の開発監査情報に留め、envelopeを出す場合も標準三方向の群min/maxとpair端点だけに絞る。

## 5. 実装へ進める最小契約案

以下を第3節の固定採用・事故規則と合わせた最小source準備契約とする。実行指示ではない。

### canonical 1：unique-results.jsonl

1行/unique_id、全4180行を保持する。

- key/K/r bits、owner、stage1 status。
- S bitsと元入力参照。
- 採用L80/A80の元文字列、stage1 raw package/member/event pointer。
- L−S/E−L/E−Sの3値またはmissing。
- 元reference_idsまたは固定reference indexへの解決可能なpointer。

50/80桁A/Q/L、raw delta、spread、counts、diagnosticsはpin済みstage1 journalへの完全なpointerで保持できる。全文を全表へ複製する必要はない。pointerに対応するraw packageを保存し続け、解決可能性を確認する。

### canonical 2：frame-results.jsonl

1行/frame、全309行を保持する。

- 元frame ID/support/時刻/hash、20参照とindex pin。
- full20_complete、missing key/status一覧。
- static/A/Bの三つの独立したnested record。
- priorの元表現・支持mask・群支持数・入力pointer。
- completeならS/L/E各G_1/G_2/D、各群10成分のK log分布。
- 標準3方向のpair差と数値タグ・理由。

missing時は全評価tripletがmissingとなるgroup-levelタグを使ってよい。data dictionaryに「全S/L/E、両群、全10Kへ同じmissing状態が適用される」と固定し、行欠落や部分正規化を意味しないようにする。全zero側のK分布もgroup-level undefinedと展開規則で表せる。

priorの全bitsを三表へ複製する代わりに、pin済みv1とreference indexの行pointerを保持する。staticはframe0行、A/Bは当該行。完全復元性を落とさない。

### 任意の小さい診断block

envelopeを初回に残すなら、frame/prior/標準方向につき正支持上のm_a/M_a、ΔG_a、pair envelopeの端点だけをnested保存する。追加K差は不要。full20 missing、空支持、∞差では適用不可の理由を記す。計算結果の厳密保証や新gateにしない。

### 表示・来歴

- point-summary.csv：unique単位のstatusと標準三差。rawへのID/pointerを保持。
- pair-summary.csv：frame/prior、complete/support、S/L/EのD、標準三差、tag/reason。
- READMEとschema/data dictionary、input/source/result pins、precision/serialisation設定、実行receipt、output manifest。

canonical JSONLの十進値は文字列。非標準NaN/Infinityは禁止。CSVもkind/reasonを保持し、空欄を0へ解釈させない。全表CSVの複製や通常確率表示は省く。

## 6. 精度と数値主張の最小条件

後段80桁、整数比からのbinary64 lift、保存十進文字列の読込、LSE安定化手順、丸めモード、結果文字列の復元仕様をsource/dependency manifestに固定する。

「80桁で計算」と「80桁が正しい」は違う。1e−9 gateは参照間一致の基準であり、真値誤差上界ではない。min/max界に代入して真のodds保証を作らない。

三差は指定した引数順で独立に計算し、総差を他の二差の和へ強制置換しない。逆方向を必要とする表示は符号反転と定義し、raw deltaとの最終桁差を矛盾にしない。

極小差の符号は保存有限精度値の符号に限る。「ほぼzero」閾値を事後に導入せず、非認証の留保を付す。丸めによる表示underflowは数学的支持zeroではない。通常確率表示を省けばこの誤用経路自体を減らせる。

## 7. 報告の最小範囲

最初にuniqueの成功/未達、全20成功frame数、prior別支持状態、finite/undefined/missingの件数を示す。標準三方向のmin/maxと正負zero件数、該当IDまでを主要記述とする。

unique単位と6180参照単位を混ぜない。condition/support等の補助内訳が必要でも、group間重複があり件数を単純加算できないことを明記する。

対象309frameは選択人工系列、重なり窓と条件間共有を含む。独立標本としてCI/p値/有効標本数を出さない。complete subsetの結果を全309frameへ外挿しない。全grid MAP、VUV、clean正答率、音質、exact時間再追跡、採用判断は出さない。

stage2が全入力と欠測を処理して正常終了することと、全stage1 keyが成功することは別。両者をreceipt/READMEで分ける。

## 8. 結論と停止点

両文書の数学と科学的留保は支持する。最小実装は標準3差、三prior、S/L/EのG/D/K log分布、支持・欠測状態、raw/index pinsを中心に絞れる。逆方向や全表CSVを省いても情報の復元性は失わない。

undefined/reasonの共通schema、算術事故での即時全体停止、全完了owner優先・別途許可snapshot限定の採用条件は親方針で確定した。資源上限・source/indexレビューを通してから別の開始判断へ進む。今回、文書のレビューと保存以外の数値処理・実装は行っていない。

### 親方針反映記録

2026-10-20、初回レビュー後に第0・3・5・8節を更新。数値kindはundefinedに統一し表示だけ「比較対象外」、算術事故は原出力保存のうえ即時全体停止・精度変更と自動retryなし、ownerは全完了成功を第一候補として不完全ownerの自動救済を禁止した。別途監査済み・入力manifest許可済みsnapshotだけを例外的な入力とする。数学的定義・三差・支持/missing・全20セル完備規則は変更していない。
