# 固定100組・履歴対比 実行成果物の独立監査

## 結論
承認 source v1 による内部実行・保存、外側実 wait、100組の台帳、原 canonical/CSV/件数、予算は PASS。科学的差分の再計算は行わず、数理側の採用判断は別監査とする。

最終判定：実行契約 PASS、実行証拠面から採用可能。CONTRACT-ja.md 第31行が要求するのは科学 supervisor の末尾保存後60秒以内と、親の外側実 process wait 60秒以内、post-fsync stdout・原receiptの保持である。科学 supervisor の post-fsync 3.0423108200193383秒、外側実wait 3.5037792939983774秒、正常終了・reap は原保存物で確認済みであり、この条件を満たす。外側監査wrapper自身の最終record保存後時計は同条の追加必須条件ではないため、その未同梱は採用blockingではない。

証拠の限界：外側wrapper最終fsync後3.505678279994754秒（丸め3.506秒）は、childが当時の functions.write_stdin session29025 / chunk24900f のtool応答から引用した二次的報告である。親からその旨を受領したが、本監査者はそのtool応答原物を直接検証していない。wrapper stdout原ファイルは未保存のため、ZIP原物による一次監査は不可。3.506秒をZIP確認済みとは記載しない。「追加転送で補完可能」「補足待ち」という先の記述は撤回する。科学処理・wrapperの再実行、receipt再構成は不要かつ行わない。

## 方法と固定
対象 `pitch-history-contrast-results-review-20261020/package`。独自の標準ライブラリ読取で JSON/hash/整数件数/台帳・CSV の原文字列一致を照合し、outer_wait.py は読取のみ。候補実行/import/tests、X/I の減算再実行、BF/exp/log 等は行っていない。

- ARTIFACT-MANIFEST の22 entries と manifest自身の全23ファイル、bytes/SHA/file set が一致。
- OUTPUT-MANIFEST の9 entries と自身の全10出力が一致。部分ファイルや失敗ファイルの余剰なし。
- provenance の CONTRACT、SOURCE-MANIFEST、INPUT-MANIFEST、PAIRS は承認 v1 package と byte identical。
- 承認 source SHA `2913969218f72c840f6083268533c531029f01fd2066095c754ab39f59fdbe4b`、input SHA `bbd2f6b8764fffb09c5b1f6e65d331526200ce2832caa31e7b95275894d6b22a` が command/lineage/receipt/pins と一致。
- pins.json の inputs 全オブジェクトは承認 INPUT-MANIFEST と一致。原入力ZIP自体は本bundleに複写されず、既承認 source の runtime全hash/member検証の正常終了証拠と固定pinsを利用する。

## 一回性・時刻・終了
command は承認 v1 run.py、-B、--authorized-once、承認 source SHA、新規output、固定claims-dir を指定。claim の source/output は command に一致し、原claimパスは stage2 ZIP SHA `1caa151838a24d9c15326c455ff1d174e9d44514c0f8b22a6448c70520b694e5` に基づく固定名。LINEAGE は scientific_attempts=1、automatic_retry=false。保存された claim は1個であり、他ホストも含めた不存在の証明ではなく、親の一回運用管理と合わせて採用する。

- outer started 2026-10-20T10:33:05.262703+00:00、wait_finished 10:33:08.766416+00:00。
- outer pid 15876、exitcode 0、reaped true、signals []、overall_success true、elapsed 3.5037792939983774秒。
- worker pid 15878、exitcode 0、reaped true、termination_unknown false、signals []。
- worker receipt complete true、pairs100、progress [2,99,100]、progress_complete true、worker_receipt_state validated。
- 内部 actual_wait_seconds 2.9107141680142377、elapsed_after_wait 3.036301786021795秒。
- stdout は1行 interaction_post_fsync、success true、elapsed 3.0423108200193383秒。outer-end の保存 observation と一致し、stdout/stderr SHAも原bytesと一致。stderr 0 bytes。
- 承認実装の worker128MiB RLIMIT、science50秒、wall60秒、停止/reap、fsync 経路で正常終了している。実worker RSS42860KiB、supervisor RSS15488KiB。tree合算制限の主張ではない。
- 出力10ファイル計1,016,083 bytes＋claim195 bytes＝1,016,278 bytes、8MiB未満。

outer_wait.py は Popen→wait→stdout/stderr fsync→outer-end file/directory fsync→最終elapsed判定の順を持つ。ただし最終elapsedはprintにのみ記録するため、当該print原ファイルは未保存であり、外側wrapper最終保存後時計の一次監査はできない。これは科学supervisorのpost-fsync原stdoutが保存されていることとは区別する。

## 全台帳・正本・転記
- initial/final ledger は各100行、固定pair ID0..99で欠落・重複なし。initialは全unattempted、finalは全record_saved。
- canonical100行の pair オブジェクトは承認 PAIRS と全件一致。各 full20_complete true、missing_keys 左右空、identity_checks passed。
- canonical 100×3prior×6値＝1800値。タグ件数はfinite1476、undefined324、missing0。undefinedを成功finiteやzeroへ置換していない。
- CSV1800行は canonical の pair/group/stratum/frame/prior/quantity/direction/kind/decimal/reason と全件原文字列一致。
- summary counts は canonical の整数タグ件数と全一致。72groups の finite/undefined/missing件数とfinite符号計数の総数が一致。各保存min/maxの各pair_idが指すcanonical decimal文字列は保存極値文字列と一致。
- 極値の大小順位、全同値ID網羅性、符号分類の科学的正否はこの実行監査では再計算しない。completed_pairs100、noncertified true、independent_samples falseを確認。

## 採用範囲
内部実行成功と保存完全性の証拠に不整合なし。元80桁の精度・符号保証、因果効果、品質改善、独立反復へ拡張しない。実行証拠面は採用可能。科学値の採用には別数理監査を用い、外側wrapper最終保存後時間の一次監査不可という限定を保持する。
