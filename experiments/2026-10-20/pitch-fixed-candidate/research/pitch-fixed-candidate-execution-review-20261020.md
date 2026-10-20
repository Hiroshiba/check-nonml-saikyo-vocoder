# 固定候補BF stage1 adapter：実行境界・保存契約の静的レビュー

2026-10-20 UTC。対象 `pitch-fixed-candidate-source-review-20261020/pitch-fixed-bf-adapter-20261020` と固定index。凍結計画を読み、source読取・SHA/bytes・AST・保存indexの型/件数/表現変換だけを検査した。候補コード実行/import/tests/smoke、BF・特殊関数・支持生成はしていない。数理gate詳細・元入力6180行の独立再構成は別担当の範囲。

## 判定：未通過（阻害問題1件）

正常経路の一回性・pin・資源・最終保存後の成功判定は概ね凍結計画に沿う。ただし **worker未reap時のcounter確定性と外部終了不明の保存** が不十分。修正版を静的に再確認するまで起動不可。現在の実測未開始状態を維持する。

### B1：未reapでも通常final counterを出し、fallbackが補足しない

該当箇所：

- `source/supervise.py:114–120`：kill、最大5秒join後にworker_exitcode/worker_reapedを記録するが、未reapでも先へ進む。
- 同 `123–127`：全rowの共有counterを読み、未完rowをinterruptedにする。この時点でworker未reapなら、counterが最終確定したとは限らない。通常のledger-final字段に確定性の印が付かない。
- 同 `134–135`：そのままstop-record/ledger-finalを保存。
- `source/failure.py:9–10`：ledger-finalがあるだけで即return。未reap・不確定counterを外部fallbackの `counters_complete=false` 契約へ補足しない。
- `source/external.py:91–104`：coordinator groupへSIGKILLを送って実waitする対象はcoordinatorのみ。coordinatorが先に失われた場合、worker終了/reapの独立確認は得られないが、worker終了状態をunknownとする外部字段がない。

正常成功への誤昇格は `worker_ok` と外部signal/exit gateで抑止されている。しかし今回の契約は、未解決時に「最後の観測下限」と「確定消費」を区別し、終了不明を明示して次の再実行判断へ誤用させないことも要求する。OSがSIGKILL後直ちに終了しない、coordinatorが先に失われるなど、まさに異常時の保存が対象である。成功gateの不具合と混同しない。

**最小修正案（数値kernel/owner/評価数/gateは変更しない）：**

1. coordinatorがworker未reapの場合、当該未完attemptのcounterに `counters_complete=false`、観測時刻、`snapshot_lower_bound; final counts unknown` 等の意味を付す。reap済みの場合だけ確定とする。未試行/完了ack済みを一律に未知化する必要はない。
2. receiptに `worker_termination_unknown` または明確な等価字段を残す。SIGKILL送信済みと実終了確認を分離する。
3. 外部はworker PIDの保存済み証拠があれば保持し、internal receipt欠落/worker未reapの場合は worker_exitcode=null、worker_reaped=falseまたはunknown、証拠不足の理由を明記する。非子workerへのkillpg成功をwait/reap成功と見なさない。OS上の再確認ができない場合、unknownのまま成功false・retry禁止にする。
4. fallbackのledger-final存在時も上記不確定性を検査するか、coordinator側ledger自体が明示済みであることを保証する。既存rawは上書き補修せず補足receiptでもよい。

## 通過した静的確認

### 固定source/kernel/index

- SOURCE-MANIFEST SHA `2a9f8d7e59d283831acff16cd5d3d63bc7a6094005148a6d13bc42e0402b2ec9`、掲載11filesの集合・bytes/SHA一致。
- INDEX-MANIFEST SHA `da1c9a665be12767773bcef15c1376cdea780f82ad4b0135065338c99edf600d`、掲載12filesの集合・bytes/SHA一致。CONFIGとPACKAGE-PINSからの参照も一致。
- REVIEW-MANIFEST SHA `25a2ecacce11fdd9965d2a0d7c5175b25a42f12c8eec3d3798a3db88d41dba55`、掲載17filesの集合・bytes/SHA一致。
- 数値 `numerics.py` は8188bytes、SHA `0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065`。旧scalar v2のローカル原本とbyte同一。数学的式・50/80桁・gate・Budgetの変更なし。
- 新旧を含む7 Python sourceをAST解析成功。候補をimportしていない。
- 提供unique index4180行はID0..4179、owner=id mod3、1394/1393/1393、各K418key。K/bits辞書順unique、保存r_bitsをbinary64へ読取復元したfinite/0≤r<1/hex/exact整数比は全件一致。
- 参照6180、frame309、uniqueへのreference_id/owner対応一致。1参照key2180、2参照key2000。元selected rawまでの全再構成を本レビューで完了したとはしない。

### 一回性と独立pin

外部入口は独立期待source manifest SHAをCLIで受け、全source集合を検査。CONFIG固定index SHA、input-pins固定ZIPサイズ/SHAを検査し、workerでも再検査する。Python3.12、mpmath1.3.0のdistribution-owned Python source inventory/hash、find_spec origin、実import version/file/spec/path/submodule所属を検査。不一致時の自動インストール・代替なし。

親input ZIP SHA+ownerのclaimを排他新規作成しfsync、失敗時にも削除しない。workerは担当ownerの昇順rowだけを一度ループ、supervisorは重複/重なったpoint_startとowner外eventを拒否する。既存1080支持生成器を呼ばず、結果を混合しない。跨ホスト一回性、同一ホストの共通claims-dir使用、最大3同時/合計45 worker-minutesは親の起動台帳に依存することを契約が正しく明示する。

### 時計・資源

外部入口開始直後のmonotonicを共有。科学deadline840秒、内部kill/join目標850秒、外部group kill890秒、coordinator reap目標895秒、最終成功900秒未満。preflightや起動で消費した時間を延長しない。数値worker単体RLIMIT_AS512MiB、子process生成コードなし。supervisorのRSSは別記録でtree合算保証とはしていない。

workerのBudgetは各unique_idの共有counterに対応し、50/80桁・求積拡張間でresetしない。series100000/quad200000は旧kernel byte不変。mpmath内部beta反復をこのcounterで完全計測するという主張はなく、wall監督で制限する。

### raw先行保存と終了

全4180初期台帳をworker開始前に保存。外部にも簡略全台帳がある。workerはevent送信後にack待ちし、coordinatorはraw文字列をallow_nan=falseでjournalへfsyncしてからackする。値/診断/point_doneをfloatへ短縮しない。point_done保存前の失敗は成功行へ昇格しない。

通常出力は64MiBから末尾4MiBとclaim4096bytesを予約し、event最大64KiB、空き容量・既存容量を検査。出力予算で未保存eventはstop-recordへ保持。最終ledgerと全6180参照statusへmissingを伝播する。元入力巨大ZIPを複製しない。

正常終了はworker code0/reap/無kill/全owner matchedと内部最終fsync後観測、外部coordinator実wait/code0/無kill、外部最終manifest/receipt保存後clock/サイズ検査を併用する。export失敗、deadline超過は非0。external-finalの途中success字段だけを採用せず、最終stdout `external_post_fsync` と親からの実process wait<900を必須とする。

## 実行前に維持する運用条件・留保

- B1解消・再レビュー、親の環境割当と別開始指示までclaims作成・実行をしない。
- 外部入口自身を親が監視し、stdout/stderr・実wait/code・外側clockを保存する。入口preflight/claim/output初期化は主要try節以前にも失敗し得るため、output内receiptだけを唯一の証拠としない。
- 512MiB/64MiB内の実完了や全owner成功を静的sourceから予告しない。ディスク停止・OS障害・外部killによる完全保存不能はunknown/partialのまま保持する。
- stage2コードはなく自動開始しない。matched_noncertifiedは厳密誤差保証や音声品質成功ではない。
