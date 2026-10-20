# 新 phase control 実行前契約案：独立運用レビュー

2026-10-20。文書読取と保存サイズの整数算術だけ。新生成、候補実行/import、tests/smoke、seed/PRNG初期状態の生成、数値solver/score計算は行っていない。

## 結論と阻害事項
現案は **実行不可**。5truth×100新pair・二score・旧500不変という範囲と失敗保持の方向は適切だが、以下は未凍結である。

1. solver/evaluator・精度/gate・boundary失敗契約。未指定solverの回数/内部精度/時間/保存診断量の上限は証明できない。
2. 全raw、root診断、途中ファイル、receiptsを含む保存schemaと64MiB厳密上限。52MiB概算だけでは適合認定できない。
3. 840秒以後の進行中処理停止、worker kill/reap、保存完了、外側実waitを900秒以内に収める具体的時刻表と責任分離。
4. 一回claim、全500事前台帳、原配列の逐次保存、失敗/未着手/不明の区別と、成果chunkの可逆転送契約。

次段階を認めるとしても、親が明示する **source準備と静的レビューだけ**。開始許可・科学生成・依存importによるsmoke・試運転を含めない。未決定科学仕様は勝手に実装既定値へ落とさない。

## 読取資料と対象
- phase-origin-fixed-truth-score-plan-20261020.md（本監査時に保存されていた案）
- train-only-phase-origin-contract-review-20261020.md
- phase-calibration-mean-provenance-decision-20261020.md

(b)新規解析qモデルという来歴判断を前提に運用だけを監査した。解析式・gateの科学的十分性、Libraryサービスの現行上限は本監査で新規検証していない。authorの追記は最終凍結版で再照合が必要。

## サイズ境界
167pair ownerの主要配列は、生成4×2recordとtest score residual2本を各4096×8bytesで保存すると、

`167 × 10 × 4096 × 8 = 54,722,560 bytes = 52.1875 MiB`

64MiBとの差は12,386,304bytes=11.8125MiB。これは係数、初期draw、geometry、membership、二精度の全根・残差・目的値・順位・境界診断、全台帳、source/環境/manifest、失敗、claim、終端保存をまだ含まない。166pair ownerでも167pairの上限を適用すればよい。

上限表をsource前に作る。各項に型/endianness/shape/件数/最大文字数/最大UTF-8bytes/ヘッダ/ファイル名長を指定し、固定分＋167×最大pair分＋終端予約＋最大同時partialを合算する。浮動小数配列をJSON十進配列で保存するとこの52MiB式は使えない。binary64生bytes等を使う場合もヘッダとindexを計上する。精度桁数だけで数値文字列上限は決まらず、指数・符号・非有限タグ・エラー文も境界が必要。

例として終端4MiB、その他固定1MiBを予約すると、残る追加pair枠は1pair当たり最大42,774bytesにすぎない。この数値は配分提案の例であり採用値ではない。全根の最終診断と1000反復の全履歴は別物で、後者を無制限に保存する仕様は認めない。科学的に必須の診断が枠に収まらなければ、実測前の契約改訂へ戻す。実行後にraw/診断を削って帳尻を合わせない。

原配列の64周期表現、membership run表現、同一不変geometryの参照共有は、dtype・長さ・繰返し/添字規則を固定し原bytesを一意復元できる場合だけ利用する。丸め後配列を式やseedから再計算する代替は不可。train/testやoracle/estimatedの実際に異なる値を共有扱いしない。

通常出力は終端予約を侵食しないguard、各write前の最大追加量予約、超過時の明示失敗を要求する。atomic rename自体はbytes複写を要しないが、既存finalと新partial、残存partial、CSV重複、stdout/stderr、ZIP作成の一時複写は同時ピークに計上する。成功時だけでなく、任意pair途中停止とserialization失敗時の最大量で検証する。disk空き不足/ENOSPCでは保存成功を偽称せず外側ログに残す。

## 時間・停止・保存
- 時計の起点を各owner supervisor入口に一本化する。source/input検証、起動、通常保存も900秒に含める。science840秒を、単なる次pair開始停止ではなく進行中solver/生成/scoreにも及ぶ停止境界として定義する。
- rawは生成直後に段階的にfsync保存する。『最後60秒で全rawを保存』ではhard kill時に一次配列を失う。開始前にpair最大出力を予約し、生成完了/保存完了を別statusとする。未保存生成値がある状態でkillされたら欠落を明記し、全配列保存成功としない。
- 独立supervisorがworkerを監視し、840秒以後にworkerをどう停止するか、SIGTERMの猶予を設けるならその時刻、SIGKILL期限、join/reap期限、最終保存期限、外側group killと実wait期限を絶対経過時刻で固定する。deadlineを各処理段階から再起算しない。
- workerが未reapならexitcodeはunknown/null、進捗は観測時刻付きsnapshotでありfinal確定値としない。workerだけでなくsupervisorと外側processのPID/終了signal/実wait/reapも保持する。
- atomic receipt、壊れた/欠けたworker receipt読取をguardした終端経路、通常経路から独立した失敗receiptを必要とする。最後のfsyncとサイズ確認後の時計が900秒未満で、worker/supervisor正常終了・reapedでなければrun成功にしない。外側実waitも900秒未満を一次証拠で残す。
- scientific rowの失敗とprocess全体の失敗を分ける。予定された数値gate不合格はfailure rowを保存し続行可能か、予算/I/O/未知例外はownerを停止するかを固定する。どちらも成功subsetへ改名しない。

## 一回性・台帳・来歴
固定500行を全owner起動前に保存し、owner=id mod3、各167/167/166、owner内昇順をpinする。claimはstudy/version＋ownerに対しexclusive作成・fsyncし、未完・失敗でも削除しない。claim作成後の起動失敗も既定の試行状態として保存し、別環境への自動retry/replacementは禁止。異なるclaims-dirで二重起動できるため、親が全ホストの唯一owner割当を管理する。

source manifestの期待SHAを外側から固定し、runtime source/input/契約/依存版と実import所属を照合する。BLAS1 threadはimport前の環境と実確認を記録。512MiBがworker単体RLIMIT_ASかRSSか、supervisor分と3worker合計を含むかを明記し、未実測のRAM/時間保証はしない。

台帳は未開始、開始、生成済/保存済、50dps/80dps校正段階、各score、完了/失敗/中断/終了不明を区別し、attemptは各owner各pair最大1。oracle片側値、生成済raw、各精度の返却済根や診断を保持。killでsolver未返却の内部根は保存済と呼ばない。失敗時にも全500予定分母を保持し、追加pair・別精度・seed再選択・欠測zero補完をしない。

## Library転送：source準備時の最小契約
64MiBのowner成果を圧縮して32MiB未満になるとは仮定しない。準備時に使う正式Library入出力経路の実上限と原本の保持場所を確認し、その上限以下の固定最大chunk長（安全余白込み）を選ぶ。未確認の上限を新しい数値として決めない。

推奨は、immutable成果のファイル/member一覧を固定し、サイズが収まる独立archive群、または明示したraw byte分割のどちらかを一つに決める。前者は同名衝突なしの全member集合、後者は元ファイル名・総bytes/SHA・chunk番号/offset/bytes/SHA・結合順序を記録し、全chunk揃わなければ完了としない。分割ZIPと称して任意byte分割を通常ZIPとして扱わない。

転送用圧縮/分割作業の空間と時間を科学output64MiB/900秒に含めるか、完了後の別の保存工程にするかを事前定義する。後者でも科学成功のclockを転送終了で上書きせず、転送は未完として独立statusにする。圧縮は容量節約保証ではなく、元bytes復元/hash照合が要件。アップロード再開は同じimmutable bytesだけに限定し、科学claimを再使用しない。全chunkの取得・復元・hash確認が済むまでLibrary保存完了としない。

## source準備のみへ移る最小条件
1. 明示的に準備のみを許可し、run/import/tests/smoke/PRNG初期状態生成を除外する。seed非重複の静的schema確認と、将来実行で初期状態を生成検査する工程を区別する。
2. solver/evaluator/gateの採否を決定するか、未決定箇所を実行拒否するtemplateとして実装するかを親が選ぶ。暗黙の仮設定で動くcandidateを作らない。
3. 保存schema・厳密上限・終端予約・転送方式・状態遷移・時計とkill/reap時刻表を文書として固定する。
4. sourceを静的レビューし、完全source/input/dependency pins・実行環境・unique owner claimsを確定してから、別途一回開始判断をする。

以上が未了なら紙上契約の追記まで。旧500、PML唯一base、科学比較二本の範囲は維持する。
