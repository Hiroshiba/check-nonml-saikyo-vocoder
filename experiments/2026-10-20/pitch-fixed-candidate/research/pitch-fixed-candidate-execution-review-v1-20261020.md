# 固定候補BF stage1 adapter v1：B1差分再レビュー

2026-10-20 UTC。対象 `pitch-fixed-candidate-source-review-v1-20261020/pitch-fixed-bf-adapter-v1-20261020`。旧v0と全文差分、bytes/SHA、ASTを静的確認。候補実行/import/tests/smoke、BF・特殊関数・gate再評価なし。

## 結論

**B1解消。本担当の実行境界・未解決時保存レビューは通過。新たな阻害問題なし。** 数理・index担当の通過、親の環境割当、独立期待manifestと共通claims-dirの固定、別途のowner一回起動指示が揃った場合に限り開始可能。本レビュー自体は開始指示ではない。

## B1修正確認

- `supervise.py` はkill/join後にworker_termination_unknownと理由を保存。未reapのworker exitcodeはnullとする。
- 各rowの共有counter読取開始/終了monotonic・UTCを保存。未reapかつ実行中attemptだけ `counters_complete=false`、`snapshot_lower_bound; final_counts_unknown` と明記し、その後interruptedへ移す。完了point_done済み、未試行、実reap後のcounterを不要にunknown化しない。
- 全eventにsupervisor観測時刻を追加し、journalからの最終観測下限にも時刻を残せる。
- `failure.py` のledger-final存在時の無条件returnを解消。原ledgerを書き換えず、未確認workerかつ未完attemptのcounterに `external-counter-uncertainty.json` を付ける。point_done済み/未試行は維持する。
- final ledgerがない経路は従来どおり全4180台帳・全referenceの欠測状態を復元し、未完counterは最後のfsync観測下限としてunknownを保持。終了証拠もfailure recordへ残す。
- `termination_evidence` はjournalのworker PIDと内部child-wait receiptを照合し、receipt欠落/終了未確認/矛盾はworker_exitcode=null、worker_reaped=false、worker_termination_unknown=true、理由・retry_forbiddenを保存。externalがworkerを直接waitしたとはせず、SIGKILL group送信を終了確認としない。
- 外部成功条件にworker_reaped trueかつworker_termination_unknown falseを追加。従来のcoordinator実wait/code0、signalなし、内部成功、最終保存後clock条件も維持。

これにより、前回問題にした「未reapのsnapshotを通常最終counterのまま利用する」「final ledgerがあれば不確定性補足を飛ばす」「coordinator終了とworker終了不明を区別しない」の3面が解消された。

## 差分の最小性・不変性

実装変更は `external.py`、`supervise.py`、`failure.py` の3filesのみ。CONTRACTとSOURCE-MANIFESTを対応更新。以下はv0とbyte同一：

- numerics.py（8188bytes、SHA `0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065`）
- worker.py、storage.py、preflight.py
- CONFIG.json、DEPENDENCIES.json、UPSTREAM-PINS.json

CONFIGのindex manifest SHAは `da1c9a665be12767773bcef15c1376cdea780f82ad4b0135065338c99edf600d` のまま。今回index差し替えなし。4180unique/6180参照、owner=id mod3、1394/1393/1393、50/80桁、gate、perpoint累積100000/200000、worker512MiB、output64MiB、840/890/895/900秒、one-attemptとclaim規則は不変。

stage2、科学fallback、再評価・自動retryは追加されていない。追加時刻・不確定性字段は出力を増やすが、既存quota guardと最終サイズ/clock判定内に入り、上限を拡張しない。完走は実行前に保証しない。

## pin・構文

- SOURCE-MANIFEST SHA `035680bb789c45729d6cf54aa0d2cf491cf438f517ea2f8550e0b9a3a6f11197` は親指定値一致。掲載file集合・全bytes/SHA一致。
- REVIEW-MANIFEST SHA `fe9602635c147146c49535df6b9e047289144233a17bcf1e9610fea79263a242`、掲載file集合・全bytes/SHA一致。
- 全7 Python sourceをAST解析成功。candidate importなし。
- source ZIP25829bytes/SHA `5ce790f33e180affde824cd3f7d9fa749427e392d10e763d5079a04a632ab4bb` とreview ZIP69237bytes/SHA `744f0337406c7a3a6aab119645bf552b8afac3c95b2845378aff7526a8dd0f49` は親の正式転送確認に依拠。

## 起動・採用時の条件

各ownerは親が一回だけ割当て、同一ホストの全起動で共通claims-dirを使う。跨ホスト重複や45 worker-minutes総枠は親台帳で制御する。source/index/input/dependency照合不成立時は自動修復・再起動しない。

親はexternal入口自身のstdout/stderrと実process wait/code/外側clockを取得し、最終external_post_fsync成功・終了900秒以内・worker実終了/保存証拠を併せて採用する。内部receipt単独のsuccessでは採用しない。入口preflight失敗、I/O障害、receipt破損、reap不能等で最終保存ができない場合も、外側証拠を回収してunknown/partialとして扱い、再起動しない。この修正はOS障害下での全証拠保存や終了を保証するものではない。
