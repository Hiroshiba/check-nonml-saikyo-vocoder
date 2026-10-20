# 保存oracle evidence回収adapter：静的受入チェックリスト

2026-10-20 UTC。run-001の既計算結果を不変に保ち、未成功slotだけを回収するための実装前契約。対象スキーマは evidence-source-review-v3-20261020/oracle-evidence-preparation のworker.py、report.py、input_index.py、core.Integral/derive。これはadapter実装そのものの合格証ではなく、後続の静的審査条件である。

## 0. 受領事実と未確認の境界

親から受領したrun-001結果:
- 元source manifest SHA256: 1b54832860d9744576e071d36cc70256291c145571bc3f372b1cbeefa17e0cec
- 元results.json SHA256: 7b819eb2308e1310c636c5ce6f76f3313f25814653d058bc7417978aa2140e3d
- 5000必要積分slot中、392成功、96未収束（V予算92＋その他診断4）、早期停止2、未試行4510。
- pairは49partial、451未処理、BMA成功0。旧scoreは500pair×5=2500。
- 入力indexの固定SHA256: 79c47c6b1926359d636d63eca6b6bab161e2b2d5f28015bc16d5209a100350d2。

06:04 UTC追記: 親が正式に取得・展開した /workspace/shared/evidence-run-001-review-20261020/run-001/results.json を標準ライブラリで読取り、1172818 bytes、上記SHA一致を確認。top-level/provenance/各row/積分slotを静的検査し、500rows、2500旧score、392converged、96not_converged、2time_budget_exhausted、4510missing、49partial/451time_budget_exhausted、input/source SHAとnats/recordを確認した。科学codeの実行/importはしていない。adapterはこれとは別に開始時の実体照合を必須とする。

重要な訂正: 後続の親説明「392成功は全W/A/S/J」は実resultsと一致しない。392成功は非V390＋train/V2である。
- A-001/train/V: log_i=-2855.072870914435、evaluations=1938790、Cartesian24/48差約4.01e-8、converged。
- W-004/train/V: log_i=-2847.130321633916、evaluations=1963750、Cartesian24/48差約2.40e-8、converged。
- 早期停止はS-009/joint/SとS-009/joint/J。ともにlog_i=null、levels=[]、evaluations=1、time_budget_exhausted。
- 成功内訳: train W/A/S/J各49、joint W/A各49・S/J各48、train V2、joint V0。

旧successful Vが実在するという発見を親へ即時報告済み。06:06 UTC、親から数理レビューが旧V2件の再利用を受理したとの連絡を受領。同一入力/model/prior、旧source/gate来歴を明示する条件で392件の一部として再利用可。旧meshは取得不可で、新solver/gateに再合格したとの主張は不可。失敗96件がVであることと、V成功が0であることは同義ではない。

392+96+2+4510=5000、49+451=500の恒等式だけでは、重複slot/欠落IDや分類誤りは検出できない。exact集合の検査は引き続きadapter受入条件とする。

## 1. 実行前の凍結と拒否条件

[ ] 回収契約、新source manifest SHA、元results SHA/bytes、旧source manifest SHA、input-index SHA/bytes、許可する旧source→新source互換性を明示。ソース自体のSHAを独立引数で固定し、self-assertionだけで受け入れない。
[ ] 主入力は明示絶対path。globで最新resultsを選ばない。元run-001はread-only、新規存在しない別出力dirのみ。既存run出力の上書き/resumeをしない。
[ ] 元results内provenance.source_manifest_sha256/input_index_sha256、実manifest/配布file、score_units=nats/recordを照合。model setと順序W/A/V/S/J、N4096、K=L64、geometry/shape/norm、train0/test1、residual data_kindを照合。
[ ] 最小V修正が数値アルゴリズムのみで、likelihood/scale measure/prior/支持/定数/入力/shape定義/gateを変えないことを差分で確認。変える場合、392件を無条件に混ぜない。互換性の新たな科学審査が必要。
[ ] 旧V成功2件（A-001/train/V、W-004/train/V）は親通知の数理レビュー受理条件（同一入力/model/prior、旧source/gate来歴、新gate合格の主張なし）を回収契約へ明記して再利用する。想定外の別V成功があれば実体/source/集合不一致として停止。旧Vを無来歴で再利用、またはVだから一律再計算する双方を禁止。
[ ] V修正が旧成功の信頼性も崩す数学的バグ修正なら、旧成功をimmutableに残すことと「現在の結果に再利用できる」ことは別。元を保存した上で回収方針を再審査し、黙って旧成功を破棄/再計算しない。
[ ] SHA不一致、unknown schema/version、source/input/units不一致、unexpected model/split、同一ID重複、truth/pair_id不整合、契約互換性不明なら、科学計算前に拒否してpreflight receiptを残す。期待集合が不一致なのに都合のよい部分集合だけを採用しない。

## 2. 全500ID/5000slot inventory

[ ] 固定全500IDを実indexと照合し、truth各100、pair_id0..99の重複なし。slotキーは(pair_idを含む完全ID, train|joint, W|A|V|S|J)。test単独積分とjointを混同しない。
[ ] 元392成功slotのexactキー集合を凍結。96未収束・2早期停止・4510未試行のexact集合も保存し、互いに排反で全5000を覆う。
[ ] 実JSONに未試行model keyが無い場合はmissing slotとして台帳へ明示し、架空のconverged/zeroを埋めない。元entryのないslotと実行して失敗したslotを区別。
[ ] pair-level partial/time_budget_exhausted/unresolvedだけで全slotを失敗/未試行に分類しない。各modelの既存statusを優先し、pairの古い集計状態は履歴として残す。
[ ] 392成功を単に49×8から生成しない。親集計と実recordのキー/状態を独立照合。
[ ] 回収対象集合は5000−有効に受理した成功slot。最初の回収では報告値が実証されれば4608slot。Vだけでなく未試行W/A/S/Jも対象。旧successを再fit/再積分しない。

## 3. 旧2500scoreと392成功積分のexact保持

[ ] 旧scoreはInputs.scoresでmerged_pair_jsonから独立に読んで個別SHA検証し、元resultsのold_plugin_scoresと500×5全件で一致確認。行内とderived内の旧score重複があるなら両者も一致。不一致時はどちらかを勝手に正とせず拒否。
[ ] 元2500scoreを計算し直さず、丸め・nats/cycle換算・再正規化せず保存。canonical正本はnats/record。
[ ] 元resultsをbyte不変の参照成果物として保持し、そのSHAを各回収出力へ記録。392成功entryはキー/値/levels/alternate/omitted_ratio/diagnosticsを含めdeep equalityで不変。元elapsed_seconds/evaluationsに回収所要を加算しない。
[ ] JSONを再serializeした全fileのbytesが一致するとは要求しない。元fileは元bytesを保存し、再利用entryは型・数値・全field一致を保証。数値は元float64のexact値を維持し、許容誤差比較で改変を隠さない。
[ ] 新旧来歴は成功entryの中へ上書きせず、外側のslot_provenance等に追加。元entryのhashを使う場合はcanonicalization方法も明示し、元results全体SHA+JSON pointerも必ず保持。
[ ] 失敗entryも元artifactに不変保存。新entryで置換するのは新merged viewだけとし、history/attemptsへ旧結果と新結果の参照を残す。

## 4. JSON→Integral adapterの厳密な境界

現workerは全modelを無条件計算し、core.deriveとreport.preserve_derivedはIntegralの属性を要求する。保存JSONは辞書なので、元resultsを直接rowへ足すだけでは動作しない。

[ ] 旧成功entryのstatus='converged'に加え、log_i/alternate/omitted_ratio/levelsの必須型・有限性、levels最低3要素、diagnostics型・必須gate情報を検査。booleanを数値として受理しない。
[ ] numeric_tree_finiteは文字列を有限と扱うので、旧JSONの'NaN'/'Infinity'/'-Infinity'文字列を成功値として受け入れる検証に流用しない。必須数値は明示型検証。旧失敗診断の非有限文字列は記録として保存してよいが成功認定に使わない。
[ ] 再利用は元契約で成功した結果の互換性を確認するもの。新しい閾値をtest結果に合わせて緩めて成功化しない。元source hashと成功gate/十分な診断を確認する。
[ ] acceptedな成功entryだけをIntegralへ復元し、元payloadは独立保持。未知/欠落必須fieldは黙ってdefault補完しない。科学gateを再計算する必要があるなら読取・再集計と新積分を区別し、範囲を凍結。
[ ] 失敗/未試行のplaceholderはnot_converged等でlog_i=Noneとする場合も、それが回収計算済みとの誤解を生まないようattempt_stateを別保持。
[ ] 再利用slotにsolver関数を呼ばない条件分岐がtrain/joint/model各loopの最初にある。旧成功を新persistの汎用finite処理で書換えず、preflightで拒否か明示受理かを決める。

## 5. slotごとの来歴と繰り返し回収

[ ] 各slotへ、reused/new/unattempted、origin run ID、origin results SHAまたはcheckpoint artifact SHA、JSON pointer、origin source manifest SHA、input-index SHA、scientific compatibility version、現在のrecovery IDを記録。
[ ] 新積分には新source/contract SHA、model/kind、使用残差とgeometryのidentity、十分統計の由来、開始/終了・evaluation/stop reasonを記録。旧elapsedを新実行時間と誤記しない。
[ ] 回収runは元run-001と直前回収のimmutable chainを持つ。parent artifact SHAとroot run-001 SHA、generationを固定し、循環/欠落ancestor/他の実験の混入を拒否。
[ ] 繰り返し回収でもroot2500scoreは不変、過去に受理した成功集合は単調増加。既成功を再度計算しない。過去成功が重複して異なるpayloadを持つ場合はhighest score/latest winsで選ばず拒否。出自が一意に決まる凍結priority規則と同一性確認が必要。
[ ] 分岐回収を自動unionしない。受理した一本のparent chainだけを使うか、別途レビュー済merge規則を必要とする。
[ ] 未完回収のcheckpointを次回の親入力にする場合は、単に最新pair fileを拾わない。外部terminal receiptとoutput-manifestで確定したsnapshot/全ID台帳を作り、そのSHAを固定してから別回収として扱う。
[ ] 「もう一度」の自動連続runは禁止。前回terminal確定、許可された回収範囲・予算・新source/input pinを確認し、別新規dirで開始。中断済workerの生存不明なら同時再実行しない。

## 6. 計算順序、停止、部分成果物

[ ] pair_id第一、W/A/V/S/J truth第二の既定round-robinを維持し、各pair内train/joint・model順序を凍結。既成功はskip。test scoreやtruth別成功率を見て回収順を変更しない。
[ ] 科学計算前に全500ID・全5000slot・受理済392payload/2500scoreと来歴を新出力へ永続化する。preflight中断でも取得済/未取得/拒否を区別した台帳を残す。
[ ] 27分以後に新積分を開始しない。既成功をtime_budget_exhaustedに上書きしない。未計算slotのみ未試行/時間切れ、進行中失敗はattempt済として区別。
[ ] 早期停止2件も成功ではない。有限の中間log値や空levelsがあっても再利用successへ昇格しない。回収成功時は新結果、再停止時は前後の失敗履歴を両方保存。
[ ] 各積分完了atomic保存、全slot状態ledger、標準lib緊急receipt、監督独立receipt。実行末尾に残り451組相当を無条件completeへしない。
[ ] 現プロセス資源契約を維持: 1計算worker/BLAS1、child RLIMIT_AS1GiB、30分上限、27分新規停止、終了/集計予約、128MiB全体成果物/ログ予約。親監督RSSと外部watchdog制約の留保を維持。
[ ] usage rename競合修正、非有限診断の文字列保全、正常派生部分保持を後退させない。容量満杯・I/O故障時は既存台帳を未完証拠として扱う。
[ ] 回収用履歴を全世代丸ごと重複コピーして128MiBを際限なく消費しない。root/ancestor immutable参照と新delta/merged viewのサイズ見通しを固定し、上限を自動拡張しない。

## 7. 新旧混合の派生値・population・bootstrap

[ ] derivedとsummaryを旧runから成功判定として再利用しない。受理した全slotの現在状態から新しく計算する。旧derivedは履歴として保存。BMA0だったことを回収後も固定しない。
[ ] per-model predictiveは当該train/joint両方成功時のみ。train weights/entropyはtrain5成功時のみ。BMAは全10成功時のみ。成功候補だけで再正規化しない。数理定数/Gamma/pi/nats/recordを旧契約どおり維持。
[ ] pair statusを現slot coverageから再構成。既に全10成功のpairならdeadlineだけを理由に不完全へ落とさず、積分なしで派生集計可能。一部成功はpartial、未試行/停止原因はslot単位で別保存。
[ ] 新旧solverでlevelsの「同じ段階」が同じ求積則を意味しない場合、core.deriveのrefinement_bma[-3:]は混合段階の記述であることを明記。新旧混合値を同一refinement系列の独立検証や誤差保証と呼ばない。最終log_iによるBMAと混同しない。
[ ] 集計対象は回収で触れたpairだけでなく、常に元500ID/各truth100全体。reused/newの二重カウントなし。元100件全差列をID付きで保持し、未確定差はnull。
[ ] 主平均/CIは各truth100件BMA成功時のみ。欠測時は主平均/CI=null、成功subset条件付き平均/CIと成功ID/分母を別欄にする。数値回収成功の偏りはランダム欠測とは言えない。
[ ] bootstrapは25比較、paired差、10000反復、PCG64/SeedSequence([20261020,2,ti,0,0,ci])、linear percentile95%、pointwise。成功集合やscore差が変化したら旧CIを持ち越さず同じ固定streamから再集計する。旧bootstrap反復と新しいpopulationの反復を連結しない。
[ ] requested_replicatesとcompleted_replicatesを分離。10000計算・finite/quantile gate成功だけcomplete。時間切れはCI=null、完了した別比較は保存。0成功ならno_successful_pairs/0反復であり、CI=[0,0]にしない。
[ ] 全5000積分成功だけでexit0にせず、全500pair派生成功・必要25CI完了・最終保存成功を含むcomplete条件を明示。数値失敗/時間切れ/保存失敗はpartial/非ゼロとして残す。

## 8. 最終receiptで照合すべき不変条件

[ ] root旧score 2500件完全一致、root392成功entry完全一致、旧artifact SHA不変。
[ ] 元成功集合⊆merged成功集合、merged成功=reused成功+new成功（排反）。
[ ] reused成功+new成功+今回失敗+今回未試行等の終端分類で5000slot全体を一意に覆う。歴史上の試行回数はslot数に加算しない。
[ ] truth別pair coverageは常に100、全体500。full BMA数は全10積分成功して有限派生値が揃ったpair数と一致。
[ ] 回収対象slot以外にsolver呼出し/元結果書換えがないことをソースの条件分岐と出力来歴で照合。
[ ] 新merged results/receipt/必要checkpointのSHA・bytesをoutput-manifestとして外部監督または保存終了工程で固定。部分writeを成果物完成と見なさない。
[ ] 科学的表現は既使用入力の記述的再解析のまま。PML維持、PR67 Draft維持、音質/calibration/生理的確率の主張なし。

## 本チェックリスト作成の作業範囲

現保存ソースの静的読取、正式取得済results.jsonの標準ライブラリによるSHA/JSON読取と集計、設計検討のみ。候補codeの実行/import、tests/smoke、科学run、元resultsの再計算、Git/GitHub操作、資源・権限設定変更は行っていない。Dの修正版Vや回収adapterは未受領なので、その実装の適合は別途静的レビューで判断する。


## 9. 提案された3shard回収と一回のunion集計契約（06:06 UTC追記）

この節は既存の単一chain規則に対する、明示的にレビューする並列分岐mergeの限定例外。各shardは同じrun-001 rootを使い、任意の異なる回収branchを勝手にunionする許可ではない。実装/実行はまだ行っていない。

### 9.1 所有範囲と全体台帳

[ ] shard計画IDとexact範囲を事前固定する。S0=pair_id 0..32、S1=33..65、S2=66..99。各範囲は全5truthを含み、所有pairは165/165/170、slotは1650/1650/1700。範囲は排反で0..99を完全被覆する。
[ ] 数値部分だけを所有範囲で処理し、各shardの保存台帳は全500ID/5000slotを持つ。旧2500scoreと共通392成功entryは全shardで同一のroot正本と一致し、範囲外でも削除しない。
[ ] 今回の392成功pairはpair_id0..9にあるため、全てS0の所有範囲に入る。ただし各shardへ共通参照として保存する。新規対象はS0=1258、S1=1650、S2=1700、合計4608slotとなる。これは実rootのexact成功集合検査で再確認し、整数だけをhardcodeしてskip判定しない。
[ ] 各slotはorigin/compute_state/ownershipを区別する。root成功はreused_converged、所有範囲内の未処理はassigned_not_started、非所有の未成功はoutside_shard。outside_shardをtime_budget_exhausted/not_convergedへ書換えない。
[ ] 親rootの失敗statusは履歴として残し、現在のshardで未着手であることと別のfieldにする。owner外slotへsolverを呼ぶ経路があれば静的拒否。
[ ] 新規積分・十分統計量の処理順は所有pair内の既定round-robin、train/joint/model順を維持。分割境界や優先順位をtest score/収束結果から変更しない。

### 9.2 shard入力と成果物のpin

[ ] 全shardは同一root results SHA、root source SHA、input-index SHA、geometry/残差identity、旧score正本、同一回収科学契約を使う。各shardへplan ID、shard ID、所有範囲、root成功集合hash/正本参照、新source manifest SHAを保存する。
[ ] 新数値sourceは原則同一manifest。同一でない場合は静的に承認された厳密な数理/数値契約互換性対応表を必要とし、ファイル名や「同じv1」だけで受理しない。旧sourceと新sourceの混合があることはslot来歴で常に明示。
[ ] 各shardは独立した新規dir、監督receipt、全ID台帳、output-manifest/各artifact SHAを持つ。merge開始前に全worker terminal/停止を確認し、書換え中のlive directoryをsnapshotとして読まない。
[ ] 正規merge入力は固定した3組のartifact SHA/manifest/receiptのリスト。glob/latestで探索しない。root/resultsの種類を取り違えない。部分終了ならpartialのまま受理可能な形式を明示するが、未知sourceやhash不一致はpartialで許さず拒否。

### 9.3 union規則と競合拒否

[ ] mergeは固定5000キーから構築し、各shardのpair配列を単純連結しない。root392successをまず1回だけ登録する。
[ ] 共通reused slotは全shardで元root entryとのexact JSON値/型一致と、origin run/source/result SHA・JSON pointer一致を必要とする。複数参照は1slotと数える。elapsed/evaluationsも元のまま。不一致は停止し、近い値を平均しない。
[ ] root成功slotにnew attemptがあれば不正な再計算として拒否。new slotは定義されたownerからのみ取得。非ownerがconvergedを含むnew attemptを提出したら拒否し、値が同じでも自動採用しない。
[ ] 同一new slotの重複提出は原則拒否。例外は明示的に許可された同一immutable artifact/同一attempt IDの二重転送だけで、source/input/result SHA・pointer・attempt provenanceとpayloadが完全一致し、単なるduplicate referenceとして1回だけ数える場合。独立2runの偶然同値はidentical provenanceではない。
[ ] owner成果物がmissing/partialなら当該slotは未確定。別shardのoutside_shardを失敗として採用したり、非ownerの古いroot失敗を新attemptの結果として優先しない。初回全体mergeで3shardが揃わない場合はmissing_shardを明示したpartial unionに限定し、completeを禁止。
[ ] 新旧いずれのconvergedも契約適合・finite/必須field・originを確認。failed entryのfinite中間値をsuccessへ昇格しない。新成功集合はowner割当と一致する。
[ ] conflict resolutionでscore最大、最新time、最小error estimate、任意順最後winsを使わない。重複/不一致は静的拒否事項。
[ ] 元rootと各shard artifactは不変。merged viewは別新規出力、union slotごとに採用originとdiscardなし/重複参照を記録。

### 9.4 派生値とbootstrapはunionから一回だけ

[ ] 各shardのderived/summary/CIはmergeの正本にしない。必要なら現地診断として保存するが最終集計へ連結・平均・重み付けしない。posterior weights、model predictive、BMA、entropyもshard間で平均しない。
[ ] union成功slotから各pairの全train/jointを構成し、core.derive相当を1回行う。モデル間・train/joint間でorigin sourceが違えば明示。全10gateと有限性を維持する。
[ ] pairの現statusはunion coverageから再計算。全shardでoutside_shardだったという誤った台帳構造がないか確認。ownerの早期停止は実行失敗、ownerが存在しないことは計画/入力欠陥として区別する。
[ ] 真の母集団は各truth100/全500。shardごとの33/33/34pair平均やCIを平均して100pairの結果にしない。旧scoreはroot2500正本から同じpair差を作る。
[ ] 最終25比較bootstrapをunionのvalid pair集合から一度だけ、元固定namespace2/PCG64/10000/linear percentileで計算。各shard CI/反復数は最終回数に加算しない。shard進捗の途中bootstrapを継続しない。
[ ] unionに欠測があれば主mean/CI=nullと条件付きsubset分離を維持。各truthのvalid ID/全100差列、requested/completed replicatesと終了状態を保存する。
[ ] mixed refinement_bmaの段階来歴は本書7節を適用。旧V2件は旧gate成功であり、新mesh/新gate結果とは主張しない。

### 9.5 反復回収と未処理の運用hazard

[ ] 次の回収generationは、凍結済union artifactを1つの新parentとして使う。root392＋今回新成功を単調に再利用し、残存failed/missingだけを対象にする。3shard全体の再実行で新成功を再計算しない。
[ ] 同じplanの再送と、新しいattemptを持つ再回収を区別する。新generationの同じslot計算は前世代failed/missingだけに許す。分岐unionを混ぜて同じ新successを重複採用しない。
[ ] 元契約は1計算worker。3shardというデータ分割だけでは同時3worker/合計3GiBや90分累積予算は承認されない。逐次実行か並行実行か、worker数・各run30分/1GiBと全計画の予算・停止条件を親が明示確定するまで開始しない。逐次なら1worker制約を維持できる。
[ ] 各shard128MiB上限を守っても計画全体は最大3倍＋union分になる。成果物保存の計画全体予算、参照/重複copy方針、merge用worker/時間/メモリ/終了予約を別に固定し、暗黙に上限を増やさない。
[ ] union集計は科学積分を行わないが全5000entry/JSON復元と25bootstrapを扱う。3shardのrowsを複数コピーしてメモリを浪費しない実装と、新source pin、独立receiptが必要。
[ ] あるshardだけ失敗しても他shardの既完了成果物を消さず、成功者を再実行しない。全体complete条件はslot・pair・最終25CI・保存・receiptの整合で判定する。

### 9.6 最小静的受入ゲート

次の8項目が揃えば3shard adapter/mergeの限定静的通過を検討できる。実運用成功の保証ではない。
1. exact3範囲の完全排反被覆、owner外compute禁止、全500/5000台帳。
2. 共通root392/旧2500のexact不変照合と旧V2件の受理条件。
3. source/input/科学契約の共通pin、artifact/terminal receiptの固定。
4. root reuseの一意化、新slot owner一意、duplicate/conflictのfail-closed。
5. outside_shard・未試行・失敗・停止の分離とpartial union保全。
6. unionから派生値と25bootstrapを一度だけ再計算、元100/500母集団と欠測規則。
7. slot origin/attempt/parent chainによる再回収の単調性とimmutable出力。
8. 1worker等の既存制約を無断拡大しない実行計画、各shardとmergeの資源/保存/終端契約。

## 10. 3shard資源計画の版付き決定（2026-10-20 06:10 UTC）

親から明示決定を受領した。ユーザーは最大3件のCloud計測タスクの同時実行を許可済み。初回runの1worker/30分/1GiBは親が定めた「当該run単位」の凍結契約であり、ユーザーによる全計画の1worker制限ではなかった。第9.5節の懸念は、権限欠如の断定ではなく、次版の資源計画を明記する必要性だった。この決定は次の回収契約版に適用し、初回runの契約を遡及的に書き換えない。

次版の凍結条件:
- shardは第9節の3範囲のみ。各shardは計測worker1個、wall最大30分、workerのRLIMIT_AS 1GiB、managed outputs最大128MiB。
- 同時計測workerは最大3個。各workerのBLAS1と既定の停止/終了保存予約を維持する。
- 今回3shardの累積上限は90 worker-minutes、shard成果物合計384MiB。追加回収runや自動retryでこの予算を越えない。
- unionは別枠の最大5分、managed outputs最大128MiB。unionはmerge・派生値・25bootstrap・保存のみで、積分を一切実行しない。
- 計画全体のmanaged outputsは最大512MiB（shard384MiB＋union128MiB）。元immutable入力/既存runの保存量はこの新規出力とは区別して記録し、コピーによる新規消費は適切な新規出力枠へ算入する。
- 監督プロセスのRSSはworker制限とは別。3workerのRLIMIT_ASを根拠に、システム全体が3GiBのhard memory capに収まると主張しない。
- 有料サービスの拡張を行わない。新B/C環境は現時点では入力準備のみであり、計測開始済みとは扱わない。
- 今回の3shard以降の再run/回収追加は新たな親判断なしで実施しない。

判定更新: 第9.5節/第9.6項8にあった「並行実行数・累積予算を明示確定する」という計画上の保留は、この決定によって解消した。初回runで並行3workerが認可/実施されていたという意味ではない。回収adapter、shard起動、監督、union実装がこの新契約を実際に守るかの静的レビューは引き続き必要。特にunionの5分停止/出力予約/terminal receiptと積分呼出し禁止を確認する。実装を見ずに実行通過とはしない。

この追記では文書のみを更新した。ソース編集、候補実行/import/tests、計測、資源設定の適用は行っていない。
