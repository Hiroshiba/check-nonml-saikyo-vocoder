# 固定候補 BF 第1段 adapter：未実行 source 契約

本成果物は独立 source/index レビュー用。数値実行の開始許可ではない。親の環境割当・独立レビュー・別開始指示が揃うまで external.py を実行しない。tests/smoke、candidate import は未実施。

## 固定範囲

入力Library libfile_d1835dacce008191a65d4eb28ac5c680 v1 / file_0000000003b481fda7569d6cffbf34d4、1213332 bytes、SHA256 2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d。既存rawとZIPは変更しない。data indexのinput-pins.jsonに17ファイル全てのbytes/SHA、origin-*に元source/config/artifact参照を保存。

6180参照→4180 unique。keyは(K整数, cod bitsのunsigned big-endian整数)、辞書順unique_id0..4179、owner=id mod3、1394/1393/1393。各owner昇順、1 attempt/key、担当外評価なし、retryなし。input/domain/owner不整合は評価前停止。保存codをbitsから復元しexact整数比へ変換するだけでJ/energyからrを再算出しない。非finite、r<0、r>=1は停止しclip/floorしない。

数理原本numerics.pyは8188 bytes、SHA256 0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065。旧packageの運用contract/support生成器は使用しない。N400/δ3/K1..10、50/80桁A/Q/L、gate1e−9、point累計series100000/quad200000、整数比lift、分岐・fallback・定数・診断・拡張はbyte不変kernel通り。1 attemptは50/80桁A/Q/L一式。成功matched_noncertifiedは厳密誤差保証ではない。

## 実行入口と所有権

将来の入口はsource/external.pyのみ。必須引数は --authorized-owner-once {0,1,2} --output 新規絶対path --index 展開index --input-zip 元v1ZIP --claims-dir 同一ホスト共通path --expected-manifest-sha256 独立承認済source manifest SHA。引数例は未実行。

source/index全ファイル集合と期待SHA、入力ZIP、依存87 Python source hashを検査する。source SHAはCLIから、index SHAはCONFIG固定、input SHAはindexに固定。数値workerが512MiB RLIMIT_AS設定後に再検査し、実際にimportしたmpmath1.3.0のversion/__file__/__spec__/__path__/所有submoduleを検査する。準備時はmetadata/spec/hashのみでimportしていない。実行環境変更時も同じpin検査を通す。依存不一致時に自動導入・更新しない。

同parent input ZIP SHA+ownerのclaimを排他的新規作成・fsyncする。claimは消さず、失敗でも消費済み。全launchは同一ホストで同claims-dirを使用する必要がある。別ホストの重複防止、最大3同時、合計45 worker-minutesは親の割当台帳で管理する。ファイルclaimだけで跨ホスト一回性を保証したとは言わない。

## 時計・プロセス・保存

external.py開始直後のmonotonicを900秒の起点とする。起動・全pin検査・保存・実waitを含む。supervise.pyの内部開始時計も別記録。親が外から観測する最終process waitも900秒以内であることを最終採用条件とする。

数値workerは各shard1。単体RLIMIT_AS512MiB、子process生成コードなし。内部coordinatorと外部supervisorのRSSは別記録。process tree合算512MiBのOS保証ではない。

科学deadlineは外部開始+840秒。新key開始・kernel Budgetチェック・外部coordinatorの監督で停止する。末尾60秒を停止/reap/保存に予約。内部は840秒でworkerをkill/reap（目標850秒以前）。独立externalは890秒でcoordinator process groupをkill、895秒をreap目標とする。起動が遅くてもdeadline延長しない。

全raw eventはworker→coordinatorのack式。append-only journalをfsyncしてからack。stage_start、50/80桁A/Q/Lの元文字列、各求積拡張diagnostics、point_done、失敗tracebackを保持。現在key/stageと累計series/quadはshared countersおよび各eventへ保存。raw文字列をfloatへ短縮しない。

各shardの管理出力上限64MiB。入力はhash/path参照のみで大きな元ZIP/selectedを結果へ複製しない。通常保存は末尾4MiBとclaim用4096 bytesを先に予約。1event最大64KiB、先行容量チェック、空きディスク余裕確認、追加評価前・stage保存前に停止。末尾は全4180台帳・6180参照status・receipt・manifest用。ledgerに元数値全文を重複させずjournalを参照。容量不足のeventはstop-recordに残す。raw切捨てによる成功昇格なし。

出力はpackage/index/claimsと互いに包含しない新規directory。既存結果の上書きなし。旧failureは元入力/来歴に留め、新失敗は新directoryのappend journal/stop-record/外部failureへ保存する。既存1080支持・既存結果の成功点を再評価・混合しない。

## 終了と欠測

全4180 initial ledgerを数値worker開始前に保存。各shardの他owner行はunattempted/not_this_owner。terminal statusはmatched_noncertified、mismatch、point_budget、global_budget、error、interrupted、unattempted。失敗keyは全対応referenceへ同じmissingを伝播。partial値はjournalに保持するが成功に繰り上げない。

内部receiptの成功だけでは採用不可。worker exit0/reaped/無kill、全owner matched、内部最終fsync後のclock観測、外部実wait、外部manifest/receipt fsync後の観測、外部exit0、900秒以内、64MiB内のすべてを要求する。deadlineを超えたcleanupは失敗証拠として残り、成功にはしない。親も外側process終了時刻を確認する。

異常終了でfinal ledger未保存ならexternalがjournalから全4180行を復元し別名failure ledgerへ保存する。未完pointのcounterは最後にfsyncされた観測値の下限としてcounters_complete=false、真の最終counter不明と明記。失われたcounterをzeroや確定値にしない。OS kill/ハード障害で保存・reapそのものが不可能な場合の完全性は保証せず、成功不成立・再起動なし。

## 第2段（文章契約のみ）

実装なし・自動起動なし。別source/indexレビュー・予算・開始指示が必要。保存A80/L80を参照しQ80を検証証拠として保持、A/Q平均なし。80桁の保存値join、差・和・log/exp/log1p/LSE/条件付き正規化だけを将来許可。新BF特殊関数、級数/beta/求積/Laplace再評価、r再算出、元時系列再追跡は禁止。

S旧logBF、L高精度同Laplace、E=A80：L−S/E−L/E−Sを区別。staticは同condition frame0初期payloadのみ、A prediction_priorは保存通常zeroを維持、B log_priorは別履歴の保存log値そのもの（exp→log再変換なし）。全20セル成功をframe比較条件とし欠測K除外再正規化なし。∞−∞はnot_applicable、支持zeroとmissingを区別。全grid/VUV/音質/新tracker改善は主張しない。

## B1 修正（source version 1）

内部kill/join後、未reapの未完attemptだけをcounters_complete=falseとし、snapshot開始/終了monotonic・UTC、snapshot_lower_bound / final_counts_unknownを記録する。完了point_done保存済みと未試行は不必要に未知化しない。receiptのworker_termination_unknownはsignal記録とは独立し、未reapのexitcodeはnullとする。

externalは保存journal/内部receiptのworker PID証拠を保持する。自身が実waitしたのはcoordinatorであり、killpg成功は非子workerのreap証拠ではない。内部supervision receipt欠落・未reap・PID証拠不整合ならworker_reaped=false、worker_exitcode=null、worker_termination_unknown=true、理由、retry禁止を保存しsuccess=false。内部の子wait receiptが唯一のworker終了確認根拠となる。

fallbackはledger-finalがある場合もexternal-counter-uncertainty.jsonを別途保存し、未完attemptのcounter意味を補足する。元raw/ledgerを上書き修復しない。保存point_doneと未試行はそのまま。元snapshot時刻が不明ならnullとし、補足receipt作成時刻をsnapshot時刻へ代用しない。journal経由fallbackの時刻はcoordinatorがeventを受信した観測時刻である。

本修正は終了確認と不確定counter記録だけ。numerics.py、CONFIG、固定index、元入力、gate、owner、全資源上限に変更なし。AST/cached Ruffのみで確認し、再レビューまで実行しない。
