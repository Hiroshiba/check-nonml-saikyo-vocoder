# 回収shard実行契約の独立静的レビュー v1

2026-10-20 06:16 UTC。対象: oracle-evidence-preparation の recovery.py、recovery_validation.py、worker.py、run_reanalysis.py、runtime.py、report.py、RECOVERY-ja.md、CHANGES-ja.md相当の変更文書。親確認済みsource manifest SHA256: 11b308a02d96cd3e55ef407006131a7677ff57604185f3ca83fb93660ea094ad。親確認済み配布ZIP SHA256: 3fbd1bbf607a76e746cfb8fa5c3c1f1c6b7ac3d14939dcbdb1ba295ef63409fc。

## 判定

固定run-001を親とする今回3shardの実行経路について、条件付き静的通過。担当範囲に実行を妨げる重大blockerは認めない。旧392成功（非V390＋旧V2）/旧2500scoreの不変再利用、非成功slotのみの計算、入力/source/単位pin、shard外と停止の区別、部分保存の主要経路は契約に適合する。

条件は次の通り。
1. V新求積の数理/数値差分は別担当の静的審査を通す。このレビューだけでV修正を承認しない。
2. 親の実行launcherは今回の3範囲0–32/33–65/66–99、各1worker/30分/worker RLIMIT_AS1GiB/128MiB、最大3同時・今回合計90worker-minutes/384MiBを固定。CLIが受け付ける0–99全件モードを今回は使わず、追加再runを自動起動しない。
3. 各shard終了後はimmutable成果物snapshot・bytes/SHA・receiptを外側で確定し、unionへ渡す。unionは未実装であり、別途5分/128MiB/積分なしの契約に照らした審査が必要。
4. 実入力・実runtime・資源制約の実動作・回収adapter実動作・収束率/精度は未検証という留保を維持する。

## 1. rootの実schemaと再利用検証

recovery.py:21–45は固定514502byte ZIP、archive SHA、results SHA、入力SHA、同梱legacy manifestと旧契約SHAを照合。旧manifestのembedded正本とruntime/source/unitsも55–59行で一致を要求する。固定500rowsのexact round-robin順、truth/ID、旧score model setと型を照合。core.py/quadrature_1d.py/input_index.py/pyproject.tomlのmanifest entriesが旧版と一致することを要求し、独立新manifestのdeliverable検査も従来の起動時に行う。

固定root SHAなので、392成功のexact構成は変更できない。success数392と旧V exact2キーも追加確認。旧V2件A-001/train/V、W-004/train/Vは旧gate/provenanceで受理し、新small分類や新64/96の再合格を主張しない。数学的互換性の親レビュー受理が文書とprovenanceに明示されている。

recovery_validation.numberはtype(int,float)かつfiniteでbool/文字列を拒否。必須Integral field集合、levels最低3・最終log_iとの一致、旧refinement/alternate/omitted、evaluation/time、train/joint r、正のT、各モデル旧必須diagnosticsを検査する。失敗記録の'NaN'等を成功値として流用しない。旧Vは保存されたCartesian24/48/risk/omittedと旧gateだけを検査。

実root JSON（SHA 7b819e…、1172818byte）を標準ライブラリで読む追加確認で、旧成功のlevels[-1]==log_i、A診断非空、S/J cut<modeの保存フィールドにこのadapterとの明白な不一致は認めなかった。validator自身は実行/importしていない。全validatorがruntimeで通ると実証したものではない。

## 2. 392成功/2500scoreの保持と非成功のみ計算

recovery.py:49–53で元resultsとearly-stop/execution/auditを元UTF-8内容として新出力へ保存。rootはread-only。seed:91–109は旧scoreと成功Integral全entryをdeepcopyし、来歴をentry外slot_provenanceに置く。旧elapsed/evaluations/levels等を新実行値へ置換しない。旧失敗はroot JSONのpointerに保持する。

worker:126–131で全500rowsをseed/persistし、各rowはtrain5/joint5の全slotを持つ。旧scoreは先行保存し、132–148行で現input-indexのmerged scoreと完全一致を確認。不一致は計測前に停止。全参照hash/geometry検証も実施する。

worker:189–190はconvergedをsolver呼出し前にskipする。旧successはvalidationでfinite/診断整合済みなのでpersistのfail-closedにより通常変更される経路を認めない。新規計算はseedでnot_attemptedとなった所有slotだけ。旧Vを含む392の再求積、旧scoreの再fit、残差再生成なし。

root後の任意回収を汎用的にresumeする実装ではない。固定root ZIPだけを受理する点は今回3shard用途には適切。別世代回収は別契約/adapterが必要。

## 3. 全体coverageと停止状態

固定3範囲をworker/監督双方で検査。owner外pairはoutside_shard、owner外非成功slotもoutside_shard。owner外でもroot成功はreused/convergedのまま。所有pairの順序は元round-robinを保持する。root全500/旧score全2500を欠落させない。

owner内の停止はparent_explicit_early_stop/time_budget_exhausted/external_stop_signalを分離。元runのtime_budget_exhaustedラベルを上書きせず、原early-stop/execution記録と親停止の解釈を別来歴として保存する。27分前のtime-budget requestは不正として未検証理由を残す。根拠requestなしのSIGUSR1はexternal_stop_signalにとどめる。

現runtime.ledgerは500pairの簡易摘要であり、単一のledger.jsonに全5000slotを格納してはいない。全5000slot台帳の実体はseed済pairs/*.jsonと通常終端results.jsonのtrain/jointである。部分終了時のunion/exportはledger.jsonだけを使わず、各pair checkpoint・root copy・receiptを合わせて確定snapshotを作る必要がある。seed前/seed途中の異常では初期500ID台帳とroot copyを未完の証拠にし、未保存slotを成功と推測しない。この保存形態は情報欠落ではなく、後工程が守るべき読取契約。

## 4. source/provenanceと部分成果物

各slotにorigin、旧sourceまたは新source SHA、input SHA、root results SHA/JSON pointer、旧statusを記録。新attemptにはstarted/ended/result_status/evaluations/elapsedを記録。preflight、pair例外、停止、保存上限等は従来のworker finallyと外部監督receiptによりpartialとして保全し、元結果を変更しない。

preflight失敗やSIGKILL/OS/I/O故障に対して最終全成果物を書けるとは保証していない。科学import前初期台帳と監督receiptを残す設計を保持する。usageのrename競合対策、非有限診断の文字列化、正常派生値の部分保持は後退していない。

注意事項（今回のshard開始blockerにはしない）:
- slot_provenance.new_output_manifest_sha256の値は実際には新source manifest SHAである。名称が紛らわしい。unionはこれを成果物output-manifest SHAとして使用せず、別の実artifact SHAをpinする。
- worker:217でresult_statusを記録後、220–222行のfinite検査がresult.statusをnot_convergedへ変更し得る。その場合slot provenanceのresult_statusが古くなる。最終成功判定は必ずIntegral.status/実値を正本にし、将来の整備では降格後のstatusを同期するのが望ましい。現new Vを含む通常finite resultでは不一致は生じないが、異常時にprovenanceだけからsuccess認定してはならない。
- deadline/stopの判定がsolver開始前に発火したslotではorigin=pendingのままended/result_statusが付くことがある。これは未試行の停止でありnew成功ではない。mergeはattempted=true/startedと実statusを合わせて解釈する。
- 各shard固有attempt ID/成果物SHAはこのsource内だけでは完結せず、output directory/外部execution manifest/終了snapshotで補完する。rootを共有する3shardの独立originをunionで取り違えない。

## 5. shard集計と資源契約

is_shardではderiveを実行せず、各pairの10積分状態だけをcomplete/partialへ集計する。reportはaggregation=unintegrated_shard、summary={}、比較/CIなしを明示し、最終bootstrapを行わない。workerのshard_complete_unintegrated/exit0は「担当slot完了」であり、全500BMA/25CI完了ではない。監督のgeneric completedだけを最終科学解析完成と紹介してはならない。

監督のchild限定RLIMIT_AS/CPU、BLAS環境、27分停止→TERM/KILL、stdout/stderr/log上限、通常116MiB+終端予約を維持。receiptへshard range/recovery ZIPを追加。RECOVERY文書は今回の3shard各30分・1GiBworker・128MiB、最大3同時・90worker-minutes/384MiB、union別5分/128MiB/積分なしを明示する。集約同時数/累積予算はlaunch管理で担保する必要があるが、各sourceが共有台帳を持たないこと自体はこの固定3run運用のblockerではない。

unionは文章契約のみで未実装。全5000slotのunique merge、root392のexact一致、new slotのowner一意、旧2500不変、旧新来歴、unionからderive/25bootstrap一回の確認は後続レビュー対象。各shardが終了しただけでunion実行を許可したとは扱わない。

## 作業範囲

ソース/文書の静的読取と前版diff、保存済root JSONの標準ライブラリによる一部field照合、本レビュー文書作成のみ。候補/recovery validatorの実行/import、tests/smoke、科学run、ソース編集、Git/GitHub、資源設定変更はしていない。AST/cached Ruff通過はDの報告であり本担当による追加試運転はない。
