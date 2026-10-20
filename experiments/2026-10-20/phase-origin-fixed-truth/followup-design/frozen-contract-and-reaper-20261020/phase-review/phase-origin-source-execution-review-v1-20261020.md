# Phase source v1：実行契約の差分静的レビュー

## 結論
**未通過。起動不可。** v0の主要な実行境界阻害は修正されたが、owner-ledgerのファイル選択不具合が残り、未起動失敗成果の保存移送経路と非例外異常のstack記録も閉じる必要がある。科学source実行/import、PRNG初期化、tests/smokeは行っていない。

対象 `phase-origin-source-review-v1-20261020/package`。V1-REVIEW-RESPONSE、CONTRACT、14sourceを読取。49manifest entries＋自身の全50filesのbytes/SHA/集合一致、14source AST通過、assert文0を独立確認。
source SHA `237b2ff1ec1e2f4c51f78f4b79ebecc8047f9d28b0edd4fe71946b8166d1ced7`。
input SHA `b60194d8460f6499dfd7fc9549707b688587ef35c835074837232c0f06b523e4`。

## 新たに検出した阻害
### B1：root JSONをpair台帳として読む
`supervise.py:40–47` のglob `pair-*.json` は `pair-000-roots50.json`、`pair-000-roots80.json`も含む。一方 `storage.py:Pair.roots` が保存するroot recordは `calibration.py:60–73` のdps/A/B/H等で、row/status/inflightを持たない。root JSONが一つでも保存される通常経路で `d['row']` がKeyErrorとなり、supervisorがfailedに移る。これはv0由来だが今回の読取で検出した。

最小修正：承認INPUTのowner行を使い、各 `pair-{global_id:03d}.json`だけを列挙して存在・row一致を検証する。rootを削除・失敗を握りつぶす修正は不可。存在しないpairは未開始/未観測として全予定台帳と合わせて保持する。

### B2：安全に終了した未起動失敗成果が規定packing不能
`delivery_gate.records` はsupervisor/worker双方のchild_spawned true、birth/exec-authorized、supervisor-receiptを一律必須とする。externalのchild_proofもsupervisorのchild_spawnedを要求する。依存検証やhandshakeに失敗してworkerを起動していない場合、他のprocessが全終了済みでもimmutable falseとなり、保存用packingが拒否される。親の追加指摘をsourceで確認した。

これは危険な成果を採用しない点ではfail-closedだが、「失敗も保存」の移送契約として未完。通常成功gateを緩めず、(a) spawn未試行/未成立と既起動全PID終端をtyped証拠で確認する失敗専用分岐、または(b) 科学採用禁止・不明状態保持の独立した親側証拠保存工程を明記する。start前失敗でout自体がない場合も、原claim/外側tool stderr・実waitを対象にする。再実行やreceipt再構成で埋めない。

### B3：非例外の異常eventに呼出stackがない
捕捉例外のtracebackは新diagnosticsで実装済み。一方 `processes.py` の期限TERM/KILL、worker failover、log_overflowはevent/countだけで、非例外異常の呼出stackを記録しない。親から追加された「警告/異常にも呼出stack」要件に照らし不足。

最小修正：異常を検知した位置のframe/stack情報をboundedに確保し、kill/実wait後に整形・emitする。ログ書込失敗や上限超過で停止/reapを遅らせず、不完全記録を明示する。正常終了時に無用なstackを増やさない。

## v0阻害の修正確認
- **例外時停止**：Popen後の初期化もtry内。finally冒頭でcleanupを試み、後からselector/log fsync/closeを実施。捕捉時はsys.exc_info参照だけを保持し、整形はcleanup後。cleanup失敗にもgroup KILL/実wait fallbackがある。
- **孤児防止**：Linux parent-death SIGKILL＋親PID再確認、subreaper、durable birth→parent ack→worker outer ack→exec許可を追加。科学exec前にouterがworker identityを保持するため、従来のpoll発見だけのraceを改善。通常親終了にもcleanupがdirect/adopted childを実waitし、pending/unknown/errorsを成功から除外する。OS上の停止不能I/Oを保証するものではない。
- **同一性**：PIDとstart_ticks、PPID、comm空白対応のstat parsingを使用。failover送信はPID/start/signal単位で重複防止。
- **path**：externalはsource/claims/outをresolve後包含も拒否、symlink ancestry拒否、新規out、claims既存dir。claim serialized4096bytesを作成前検査しO_EXCL/O_NOFOLLOW。
- **最適化**：全CLIでsys.flags.optimize/PYTHONOPTIMIZEを明示検査。preflightのpinsはcheck→raiseでassert非依存。
- **summary**：入口が必ず拒否し、prototypeを非実行textへ隔離。今回計測後に無承認で集計へ進まない。
- **片側保存**：estimated60/90は各density返却直後にpersist、oracle residualはcalibration前。運用として返却済証拠を保持する改善を確認。式の正否は数理担当へ委ねる。

## tracebackとログの確認範囲
diagnostics.captureは例外参照のみ、emitはtraceback.format_exceptionとstderr原bytes書込。131072bytes/process、truncated/write_errors/completeを保持し、例外中ログが失敗しても再raiseしない。Gateの診断不完全はowner停止。worker/supervisor stream各stdout/stderr135168bytes captureとseen/retained計数は維持。outer stderrは親tool原文へ保持する別証拠。

stack要件は親から届いた最新指示を適用。手元にあるUSER_INSTRUCTIONS.md:118のstack trace要件も読取したが、そのローカルcopyを最新repo版と認定したわけではない。最新docs再取得やrepo変更は行っていない。

## 時計・資源・終端
838TERM、840KILL、845worker reap、865/870supervisor TERM/KILL、880reap、supervisor860・outer890の成功exit上限は維持。各時計はouter originを共有し、握手の待機はmin(origin+838, now+30)。workerは512MiB RLIMIT_ASとCPU840、別枠supervisor/outer。親の実outer wait900秒未満が採用に必要。

cleanup未知ならrun_ok false。externalは子双方のcleanup証拠を要求してmanifest immutableを決め、保存末尾のouter-last後もfsyncしてexit時時計を検査する。原manifestの自己hashと後続観測は後段deliveryで固定する。未reap状態でのsnapshotはimmutable採用しない。

## 65,940,752 bytes の積算
pair/raw capは不変：334960＋2×12288＋16384＝375920、167pair＝62778640。固定1048576＋終端2097152＋通常partial16384を足し65940752、64MiBまで1168112bytes。機械可読の固定caps合計937984、終端caps合計1503232とも整数算術で一致。

v1は原claim/copy/RUN計12288を固定枠へ、handshake7files×4096とprotocol partial8192、終端partial327680を予約へ計上。最悪worker/supervisor/outerの同時partialを扱う余裕が増えた。通常raw/metadata/root byte guardは維持。parent-tool原文は無理に4096へ切らず、科学output外の別証拠・別転送disk予算に明示移動した。

これは論理file bytesの上限であり、filesystem allocation・disk空き、数値診断のcap内完走は保証しない。長いroot recordや例外診断によるCapacity停止を成功へ変えず、生成済rawを削らない。半端なpartialと原logも保持する。

## Packing
原owner/out/承認source/claimsの分離、typed親wait returncode/reaped/有限elapsed、元tool原文のbytes/SHA、PID/starttime/原manifest集合hashを確認する。通常のreaped成果についてv0より厳格である。process_successとscientific_acceptanceを別に保持し、失敗exit2もimmutable証明があれば移送候補となる。ただし未起動失敗はB2のとおり現状未対応。

31MiB payloadを各独立ZIP_STOREDへ、全part/payload/SHAと復元各file SHAをstream確認。原tool全文も含む実長から必要partsとstaging diskを予約し、末尾原本hashを再照合する。実Library上限は別途確認し、科学再実行で転送問題を解消しない。

## 次版への条件
B1を必ず修正。B2の失敗証拠移送とB3の非例外異常stack契約を閉じる。source/manifest更新後に限定差分を再レビューし、数理レビューも別途通過させる。科学runの開始指示はまだない。
