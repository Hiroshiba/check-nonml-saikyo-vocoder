# 固定100組の履歴対比：実行境界・保存契約の静的レビュー

2026-10-20 UTC。対象 `pitch-history-contrast-source-review-20261020/package`。CONTRACT、designの計画/独立レビュー、run/storage/workerおよび入力・算術moduleを読取。候補import/実行/tests/smoke、実減算・BF・log/exp/LSE・科学集計は行っていない。ASTとfile読取/bytes/hash/固定IDの照合のみ。

## 結論

**本担当の実行境界・保存契約レビューは通過。blocking issueなし。** 入力同一性・Decimal算術の別担当レビュー、親の環境割当と一回の別開始指示が揃うまで起動しない。実時間/128MiB内の完走を静的レビューだけで保証しない。

## pin・固定台帳

SOURCE-MANIFEST SHA `33f28af383b1c9f4f212bdc31af518a893f6cdcadf48cfa3f5c7bf18dd50cb66`。掲載16files＋自己manifestの集合、全bytes/SHA一致。全5 Python sourceをAST解析成功。

INPUT-MANIFEST SHA `bbd2f6b8764fffb09c5b1f6e65d331526200ce2832caa31e7b95275894d6b22a`。stage2 ZIP4786179bytes/26members、selected ZIP1213332bytes/17members、index ZIP462946bytes/13membersを固定するschema。source期待SHAは外部引数から照合し、inputとPAIRSの原bytesはsource manifestへ含まれる。

PAIRSのSHAはinput記載値一致。保存された100件はpair_id0..99、H50=E-U−U-U/frame53..102、C50=E-U−E-E/frame0..49。H49 main/C48 main、padding H1/C2の計3を除外せず保持する。今回保存済IDを読む確認であり、候補コードによる支持列挙生成はしていない。

runtime Readerは入力ZIP絶対path/bytes/SHA、全member集合/bytes/SHA、重複/危険path/symlinkを検査。元inputを展開・書換えず、hashはstream、JSONLは行ごと読取。stage2/memberの実値由来・観測hash/元prior同一性の全件独立監査は別担当の結果と合わせる。

## 一回性・出力分離

同stage2原ZIP SHA単位のclaimを排他新規作成・fsyncし、失敗時も消さない。新規outputのみを使い、package/claimsとの包含を拒否、入力ZIPがoutput内に入ることも拒否する。stage1/2原結果の上書き・自動最新path探索・再実行経路なし。跨ホスト一回性と共通claims-dirは親台帳で制御する。

全100予定ledgerをworker開始前に保存。成功/失敗の値を見たpair選別や、failed行を落とした完了判定はない。

## 時計・worker・終了証拠

入口最初のmonotonicを共通起点とし、preflight/入力確認/起動を含める。算術deadline50秒、新pairの前・入力行読取等にcheck。supervisorは同50秒で残存workerをkillし、最大3秒join、54秒をreap目標とする。残り10秒を停止・保存に含め、追加枠として延長しない。

worker1、RLIMIT_AS128MiB、RLIMIT_CORE0、子process生成なし。supervisor RSSは別保存。tree合算128MiB保証や外部RSS測定とは称さない。

worker未reapならexitcode null、termination_unknown、progress_complete=falseで成功不可。progress snapshotは確定終了後と未確認時を区別する。親はrun入口そのものの外側clockと実wait/code、stdout/stderrを保存し、60秒以内を最終採用条件にする必要がある。source内supervisorだけで、OS I/O停止下の絶対hard boundまで保証するものではない。

正常完了はworker exit0/reap/無signal、supervisor例外なし、検証済worker receipt complete/pairs100、保存progress100が必要。receipt/manifestの最終fsync後にelapsed<60とoutput+claim≤8MiBを再判定し、stdout interaction_post_fsyncと最終非0/0を出す。途中receipt.completeだけで採用しない。

## 不完全出力・失敗保存

構造化JSONは.partialへの新規書込み・fsync後rename・directory fsync。中断temporaryを削除しない。JSONL/CSVは追記fsync。worker receiptの欠落/partial/不正JSON/schemaを捕捉し、未知状態で最終ledger/receipt保存へ進む。前回stage2で問題となった無防備なreceipt parseは再導入されていない。

progress[2]はcanonical一行とそのCSV投影が保存された後だけ増える。最終ledgerはこの完了数と現在pair_idからrecord_saved/interrupted_or_failed/unattemptedを記録する。canonicalが先に保存されCSV途中で失敗した行は完成数へ加算せず、partialを保持する。worker未reap時のprogress/ledgerはsnapshot留保とreceiptを一緒に読む。

worker例外はphase/pair_id/traceback/retry_forbiddenを保存し再raise。全体失敗として止まり、precision変更・失敗除外・自動retryなし。rawや失敗fileのdestructive cleanupなし。I/O/空きdisk枯渇そのもので失敗receipt保存不能な場合は外側stderr/waitと残存partialを回収する。

通常出力は8MiBから末尾1MiBとclaim4096bytesを予約してguard。terminal ledger/receipt/manifest用の余裕を確保し、temporaryも容量計数へ含む。これは管理出力容量の予約であり、filesystem全体の空き領域をOSに確保する機構ではない。物理disk不足時の保存完全性は保証しない。

## 許可計算・入力採用の境界

source importsは標準ライブラリと同梱moduleだけ。科学library/kernelのimport、BF/特殊関数/r再算出、log/exp/LSE、時系列再追跡、tests/smoke/fixture実行、subprocessによる追加計算経路なし。stdlib Decimalの有限X/g減算とschema/文字列/bits/ID/hash/件数照合だけが算術対象。summaryは固定分類の件数のみでrangeや符号反転追加統計を生成しない。

Decimalは固定prec256・ROUND_HALF_EVEN、指定trap群を使い、事故時に精度増加しない。結果をfloat/normalize/quantizeへ回さず、元D/gタグとpointerを保持。数理定義・missing優先・undefined規則の詳細は別担当レビューに委ねる。

stage2全完了・外側post-fsync/wait・source pinを採用前に照合し、固定原ZIP hashにより実際の証拠を限定する。一般化した任意receiptに対する完全型検証と同一視しない。既監査原結果への固定入力レビューが前提。

## 起動前・実行後の条件

入力/算術レビューと親の別開始指示後に同claim域で1回だけ起動する。親外側monitorはrunの実終了・reap・60秒・post-fsync原stdoutを保存する。実行後、100台帳・canonical/CSV・分類件数・input/source pins・partial有無と最終outputサイズを独立監査する。成功時の主張は「保存十進減算で契約の追加丸めtrapが発生せず完了」に限定し、元80桁真値精度・F0/VUV/音声品質・因果効果や漏洩不存在の証明に広げない。
