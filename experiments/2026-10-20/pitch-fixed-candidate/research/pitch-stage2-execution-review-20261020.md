# 固定候補stage2 source v0：実行境界・owner採用の静的レビュー

2026-10-20 UTC。対象 `pitch-stage2-source-review-20261020/package`。最小契約 `pitch-fixed-candidate-stage2-independent-review-20261020.md` とsource/契約を読取。候補import/実行/tests/smoke、科学算術・BF・gate再評価なし。数理演算の詳細は別担当。

## 判定：未通過、阻害2点

未確定input templateによる意図的停止とは別に、下記2点をsource修正・再レビューする必要がある。全owner結果、外側実wait、完成input manifest、環境と開始指示は引き続き未確定であり、現状起動不可。

### B1：240秒killによるpartial worker receiptが最終証拠保存を中断する

`output.py:38–45` のwriteは最終pathへ直接xb書込みする。supervisorは240秒でworkerをkillできるため、worker-receipt.jsonの存在とJSON完全性は同義でない。`run.py:89–90` はfinally内で無防備にread_text/json.loadsし、破損・部分JSONなら例外が `receipt.json` / OUTPUT-MANIFEST保存（96行以降）を飛ばす。すでに収集したworker exit/reap、progress_snapshot、unknown状態が失われる。成功への誤昇格ではなく、契約上必要な異常終了証拠の保存漏れ。

最小修正：worker receiptの読取・JSON/schema検査を独立tryで囲み、欠落/部分/不正ならstateを空にしてcomplete=false、理由/tracebackをreceiptへ記録し、最終receipt/manifest保存を継続する。partialファイルは消さない。atomic temp+fsync+renameによるreceipt生成も有用だが、それだけに依存せずreaderをfail-closedにする。kill/reap後に例外が出ても最終証拠保存へ進める構造にする。kernelや算術精度の変更は不要。

### B2：unique_id付き未知journal eventを黙って受理する

`adopt.py:74–78` はcontrol eventのwhitelistを持つが、`82–108` のpoint eventにはない。実行中unique_idを持つ未知typeはattempt境界だけを通り、stage/value/doneのどれにも入らず無視される。CONTRACTの「未知event、欠測raw、矛盾は全体停止」に反する。将来入力は独立監査・hash固定されるものの、adoption層自体が明記した厳格条件を満たしていない。

最小修正：point eventは `point_start / stage_start / value / quadrature_progress / point_done` のみ許可し、その他は停止。controlは重複だけでなく開始・依存確認・正常終了の順序とpoint処理境界も明確に検査する。求積progressをraw参照へ残すことと未知typeを許容することを分離する。

同じadoption層の追加堅牢化として、累積counterの整数/非負/上限・時系列非減少、他ownerのzero counter、internal/outer PID相互一致の検査も推奨する。現v0は主にledgerとpoint_doneの数値同値を検査しており、これらすべてを独立に検証したとは言わない。科学gateの再評価は不要。

## 確認済みの適切な境界

### source/pin・未確定template

SOURCE-MANIFEST SHA `d57ca7f2f163ad3583a2b01303c42e52d3bb42da3275ec5b5f681db4df28d41e` は親指定値一致。掲載20filesの集合・bytes/SHA全件一致。全8 Python sourceのAST解析成功。

manifest関数はstate=frozen_reviewedとadoption=all_owners_complete_onlyを必須とする。現templateのUNRESOLVED_TEMPLATE_DO_NOT_RUNはclaims作成前に拒否される。owner0/1/2の集合、全ZIP/stdout/parent_waitの絶対path/bytes/SHA、外部manifest SHA、親wait selectorを要求する。null placeholderを推測で埋めない。

保存入力ZIP/indexZIP/stage1 sourceZIPはcode固定hash。stage1数値sourceをimport・実行する経路なし。ZIPは展開せず、重複member・unsafe path/symlink・展開後80MiB超過を拒否し、各manifest memberをbytes/hash照合する。依存mpmath1.3.0はworker512MiB設定後、87 source inventory/hashと実version/origin/path/submodule所属を検査する。

### stage1 owner採用

現sourceは全owner全完了だけを採用し、partial/unknown owner snapshot救済は実装していない。これは最小契約の第一候補に沿う。全4180 adopted keyを要求し、owner間重複・欠落を拒否する。

外部/内部receiptのowner、worker exit0/reap/termination_known/無signal、coordinator exit0/reap、internal_success/all_owned_matched/worker_okを要求。内部post-final-fsync、別pinされたexternal.py最終stdout、別pinされた親の実waitとstdout SHA結付け、各900秒未満を確認する。source/index/input来歴とcounter-uncertainty補足も要求する。

journalはowner・昇順単一attempt、stage_start順序、50/80桁A/Q/Lの6値一意性、point_done matched、ledger状態/attempt/counter一致を検査する。control依存確認のPID・actual_import_verified/version/RLIMIT_AS・owner_exhaustedを照合する。ただしB2の未知type/順序の穴を修正する必要がある。

rawの完全な数値/diagnostics/deltaはarchive SHA/member SHA/行範囲pointerで保持。L/Aの保存文字列以外を新参照へ作り替えず、stage1 gateを再評価しない。完成input manifestレビューでは、外部wait selectorが本当に対象processの実waitを指すこと、prefix/member解決、raw保存継続を独立確認すること。

### 資源・時計・一回性

run入口直後のmonotonicを基準とし、240秒でworker停止、250秒をreap目標、300秒未満の最終保存後成功判定。末尾60秒を停止・保存に残し、準備時間を延長しない。worker1、RLIMIT_AS512MiB、子processなし。supervisor RSSは別でtree合算保証ではない。

未reapはworker exitcode=null、termination_unknown、progress_complete=false/snapshot下限で成功不可。source上ではkill/join後保存するがB1のreceipt読取例外によりその保存が妨げられる場合がある。

管理出力64MiB、通常出力に末尾4MiB/claim4096bytesを予約、行ごとにguard/fsync。出力新規作成・失敗claim保持・自動retryなし。共通claims-dirと跨ホスト一回性は親管理。stage1のclaim/processには触れない。

成功はworker code0/reap/無signal、worker complete、unique4180/frame309、receipt/manifest最終fsync後300秒未満と総サイズ条件、さらに親の実process wait確認が必要。内部receiptのcompleteだけで採用不可。run自体のpreflight/IO停止を止める外側clock/kill・stdout/stderr回収は親の実行契約として必須であり、source単体がOS障害下のhard upper boundを保証するものではない。

## その他の留保

partial canonical JSONL/CSV末尾は保持し、正常完了行数と混同しない。新しい算術事故で全体停止し、精度変更/retryをしない経路を確認。保存入力未確定であるため、現時点で採用可能なowner bundleが存在することは主張しない。科学算術の精度・schema整合は別担当の結論と合わせる。
