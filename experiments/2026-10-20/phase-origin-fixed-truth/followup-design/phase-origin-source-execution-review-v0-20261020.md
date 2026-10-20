# Phase source v0：実行境界・保存契約の独立静的監査

## 判定
**未通過、起動不可。** 正常経路の予算・逐次raw保存は具体化されているが、例外時の子process停止保証、出力分離、最適化時のpins検証、後段採用gateに阻害事項がある。以下を修正し再静的レビューする。科学式・gateの適切性は別担当。

候補の実行/import、PRNG初期化、tests/smoke、数値計算は行っていない。文書とsource10本の読取、AST、hash、整数サイズ算術のみ。対象は `phase-origin-source-review-v0-20261020/package`。

## 確認済み固定
SOURCE-MANIFEST SHA256 `19def7ce47119e65677f7feb2d96d5a87b5f9fbe06a3721ea5d9d335cbaaf585`。35 entries とmanifest自身の全36filesの集合/bytes/SHA一致、source10本AST通過。

INPUTの500行はglobal_id0..499、truth_id=id//100、pair_id=id%100、owner=id%3が全件一致。所有数167/167/166。source/input期待SHAの外部指定、O_EXCL claim+file/directory fsync、一回owner昇順、別precision retry禁止の方針は確認した。cross-host一回性は親のauthoritative claims管理が必要。

## B1：Popen後の異常出口でworkerが残り得る（blocking）
`processes.py:29–50` はPopen後のselector/identity/log初期化がtry外。`50–143` の監視中の読取・write/fsync等の例外でもfinallyはpipe/log closeとsyncdirだけで、子groupのkill・bounded wait・unknown証拠保存を保証しない。

`supervise.py` はrun例外をcatchしてfailed receiptを作って終了する。一方workerは `start_new_session=True` の別groupであり、supervisor終了/そのgroup killではworkerは停止しない。outerは `/proc/supervisor/task/.../children` をpollして発見した子だけをfailover対象とする。発見前にsupervisorが例外終了した場合や、outer自身の監視が例外終了した場合、workerの独立wall-stopが失われ得る。CPU840秒はsleep/I/Oを含むwall840秒の代替ではない。

最小修正：Popen直後から全例外を管理し、取得したPID/group/starttimeをdurable保存する。例外経路にも期限内kill/waitと終了不明記録を実装する。outerがworker identityを確実に受領するhandshake、または親死亡時も停止できる別の明示機構を用意し、単なるpoll発見に依存しない。OSがreap不能な場合はunknown/nullとし、停止済み・manifest不変を保証しない。ファイルI/O異常でも可能な停止処理を先に行い、証拠書込失敗がcleanupを飛ばさない構造にする。

通常経路の838TERM/840KILL/845reap、outer865TERM/870KILL/880reap、supervisor860・outer890成功限界は妥当な余裕を設けているが、B1解消前には異常経路にも適用されるとは認定できない。`processes.py:87–99` のfailover signal記録は同PIDへ反復追記される。送信済みを記録し、不要な重複によるreceipt cap超過を避けることを推奨する。starttime解析はcomm内空白に依存しない `/proc/stat` 分割を用いること。

## B2：source/input/claims/output分離が不十分（blocking）
`external.py:26–70` はsymlink ancestryとmkdir新規性だけで、outがsource/claims配下またはその祖先でないことを検証していない。claimsがsource配下であることも禁止しない。claim生成後にsource file-setが変わって検証失敗する構成を作れてしまい、科学開始前でも固定sourceを汚染する。

最小修正：claimより前にresolveしたsource・claims・outを包含関係も含めて検証し、互いに必要なdisjoint性を強制する。入力原本が出力/転送先に含まれないことも検証する。`package_saved.py:20–26` の転送outも原ownerの内外包含を拒否し、原本不変を保証する。文字数ではなく実serialized bytesでclaim/path上限を事前検証する。

## B3：assert依存のpins検証が最適化で消える（blocking）
`preflight.py:25–50` のsource file-set/hash、Python/dependency版・hash・所属、thread環境等はassertに依存。起動は-Bであり-Oを拒否せず、PYTHONOPTIMIZEを無効化/検査していない。親外側を最適化モードで起動すると、検証が無効化され得る。

最小修正：セキュリティ/採用境界のassertを明示if→raiseへ置換する。少なくとも外側最初に `sys.flags.optimize != 0` を明示的例外で拒否し、子の最適化環境も禁止する。後段package/summarizeの採用assertにも同じ条件を適用する。actual module所属はworkerで追加照合しているが、assert消失問題の代替にならない。

## B4：後段summaryが終了不明ownerを採用し得る（blocking、または明示的に今回範囲から隔離）
`summarize.py:24–40` はexternal-wait.reaped、outer時刻、parent-tool-wait.txt存在だけで採用する。supervisor exitcode/signal、worker wait/reap/unknown、source/claim/owner一回性、artifact/原raw hashesを照合しない。supervisorだけreapedでworker未reapのownerでも、completeと書かれたpairを正常有効数へ入れ得る。parent-tool-waitの存在は実wait0/900秒以内の証明ではない。

最小修正：source/契約/claimとimmutable成果をpinし、外側実waitとworker/supervisor双方の終了証拠をtyped validationする。異常ownerを一律捨てる必要はないが、終了不明/変動可能な原本の値を通常validへ昇格しない。安全なpartial採用条件を別に定義する。今回は後段を実行禁止・未承認として切り離し、将来source/input/実保存値の独立レビューを必須とする方法もある。

## 保存上限：算術は一致、全運用込み証明には留保
独立整数算術では生成rawの完全量334,896bytes/pair、raw cap334,960、root2×12,288、metadata16,384、pair合計375,920は一致する。167pair=62,778,640。固定1,048,576＋終端2,097,152＋通常partial16,384を足した65,940,752bytes、64MiBとの差1,168,112bytesも一致。snapshot4files実合計199,019bytesは524,288cap内。

`storage.py` はserialized bytes cap、通常62MiB guard、終端64MiB guardを持つ。rawはappend前にperpair capを確認し、intent metadata→raw fsync→完成descriptor fsyncの順。数学上返却されない中間根は保存対象とせず、返却済rootは各precision fileに更新保存する。通常workerは逐次で同時partial最大16KiB、root partial12KiBはその内側。各log最大135,168bytesで4本、超過は失敗・非保持bytesを記録する。

ただし65,940,752は以下を満たす運用上限であって、現実装全経路を無条件に覆う証明ではない。
- 原claims fileはoutput外。claim-copyは4096capだが元claimはwrite前のcap検証がない。両者を予算に含める範囲を明示する。
- 後から置くparent-tool-wait.txtの4096capは検証していない。元tool出力が4096超の場合、切捨てず拒否/別枠保存とし、契約を固定する。
- 新規未使用outだけを許し、symlink/source/claims混在をB2で拒否する。
- B1により未reap workerが残る場合、終端manifestと並行して原本が変化し得る。raw容量capだけでimmutable完了を保証しない。
- bounded serializationを超えたときに数値値を切り詰めない方針はよい。ただし科学完走を保証しない。12KiB/16KiB診断に収まらないpairはCapacity owner停止となる。

I/O失敗時にpartialを残す構成はあるが、atomicは同名.partialをwbで開くので、同パスへの再呼出しで前partialを破壊しないことが必要。科学run再開は認めず、運用上この再書込を失敗証拠回復の代用にしない。

## 欠測・成功条件・資源
全500planned台帳は科学前に保存する。各ownerはnonownerを実行せず、Gate失敗はnumerical_failureとして次pair、Capacity/I/O/MemoryError/未知例外はowner停止。oracle片側値・生成済raw・intentを残す構造はある。owner-ledgerは存在するpairのみの索引で、全500planned台帳との突合が必要。startedのままのpairを成功扱いせず、未着手と開始観測不明も区別する。

worker RLIMIT_AS512MiB/CPU840sはsupervisorのpreexec_fnで設定。supervisor/outerは別枠であり、3worker合計512MiBとは言わない。BLAS5環境変数1とpure-python mpmath設定はimport前。時間/RAM完走保証や実スレッド本数の実測はない。

external最終観測はmanifest fsync後のelapsedを保持し、その後自身のatomic/fsyncを完了して890秒未満でexit0とする。最後のfileは前のmanifest対象外で、delivery manifestに含める説明は整合。親がouter自身の実wait0/reaped/900秒未満を原tool evidenceとして固定することが必要。

## Library転送
`package_saved.py` はscienceを再実行せず、ソートした原file byte streamを31MiB payload単位の独立ZIP_STOREDにする。file offset/length/SHA、part payload/ZIP SHAと順序を持ち、復元streamの各file hashを確認する。圧縮率依存なしという点はよい。

ただし実サービス上限は未確認のままなので、31/32MiBをLibrary保証とは扱わない。転送前に正式経路の制限を確認する。原本保持、part生成disk、uploadと取得検証は科学900秒/64MiBと別工程として固定する。失敗は同じimmutable bytesの保存再開だけで、科学再実行理由にしない。原ownerがreapedでimmutableであることと原manifestの一致をpacking前に確認し、親tool-wait存在のみで代替しない。B2の出力分離、B3のassert対策も適用する。

## 再レビュー条件
B1–B3はrun前必須。B4は修正か後段隔離を明文化。bytes対象境界とparent-tool-wait上限を閉じ、source manifest更新と科学kernel不変差分を提出する。数理担当の指摘も別に解消し、なお別開始指示が出るまで実行不可。
