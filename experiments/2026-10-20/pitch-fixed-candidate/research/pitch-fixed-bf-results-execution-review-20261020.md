# 固定候補BF stage1：3 owner実行・保存証拠の独立監査

2026-10-20 UTC。対象 `pitch-fixed-bf-results-review-20261020/owner0, owner1, owner2`。候補実行/import/tests・BF/特殊関数/gate再評価なし。標準ライブラリで保存JSON/JSONL、hash/bytes、型・整数counter・元保存文字列を照合。数理gateの保存値検証は別担当。

## 結論

**実行・保存証拠は通過。3 ownerはstage2の全完了owner採用条件を満たす。blockerなし。** 1394/1393/1393の一回attemptが非重複で全4180keyを被覆し、unknown counterは0。stage2の開始許可ではなく、完成input manifestと親wait/stdout結付けの固定、別担当監査・開始指示が必要。

## file/pin/claim

各bundleはartifact-manifest掲載31files＋自己manifestの集合一致、31件すべてbytes/SHA一致。EXTERNAL-MANIFESTとRESULT-MANIFESTの全掲載memberも一致。結果ZIPの正式転送SHA/bytesは親確認に依拠。

approved-source-pinsの5filesは承認source v1とbyte同一。provenanceのsource manifest `035680bb789c45729d6cf54aa0d2cf491cf438f517ea2f8550e0b9a3a6f11197`、index `da1c9a665be12767773bcef15c1376cdea780f82ad4b0135065338c99edf600d`、親入力 `2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d` は承認値一致。provenanceのsource全file一覧も承認manifestと一致。

outer commandのowner/source期待SHA/output/共通claims-dir、claimのowner/input/source/output/開始時刻が整合。全bundleに同じ3claimがbyte不変で同梱されている。ownerごとにpoint_start/doneは1回ずつ、担当外attemptなし。これにより受領された保存証拠上の一回性を確認。未提出の別ホスト起動不存在まで証明するものではなく、親の割当台帳は引き続き必要。

**履歴上の注意：** dependency-resource-report.jsonのsource manifest欄は準備時v0（2a9f…）を記す。これは承認v1での実行command/claim/provenance/approved-source-pinsおよびworker実依存確認とは別の準備履歴。実行sourceの証拠として流用しない。これを除いて実行pinがv0だったと解釈する根拠はない。

## 全4180台帳とjournal

各ownerの初期/外部初期/最終ledgerは全4180行。初期全件unattempted/attempt0/counter0。最終は担当1394または1393だけmatched_noncertified/attempt1、他ownerはunattempted/not_this_owner/attempt0/両counter0。全行counters_complete=true。

journalのcontrol順、owner=id mod3、unique_id昇順・一回性、50/80桁各primary→quadrature→laplace、stage/value対応、Q progress extension連番、6値完備→point_doneを全件独立確認。6保存値計25080は有限な保存文字列。Q最終progressのlogBF/detailsとQ valueも文字列・字段一致。ここでgateや新BFは再評価していない。

| owner | matched/start/done | stage/value各件数 | Q progress | series累計 | quad累計 |
|---|---:|---:|---:|---:|---:|
| 0 | 1394 | 8364 | 3486 | 1354 | 6275178 |
| 1 | 1393 | 8358 | 3484 | 1362 | 6273662 |
| 2 | 1393 | 8358 | 3480 | 1334 | 6267102 |

全eventのcounterは整数・非負・各point上限100000/200000以下・時系列非減少。point_doneと最終ledger counterが全件一致。全6180reference-statusは固定reference indexとID/unique_id/owner一致、当該owner成功参照だけmissing=false。他ownerを成功化しない。3owner集合の重複0・欠落0。

stop-recordのunsaved_eventは全owner null、receipt字段は最終supervisionに一致。external-counter-uncertaintyのuncertain_attemptsは空、worker termination known/reaped。旧B1の未確定counter経路は今回発生していない。

## 実wait・終了・資源

| owner | 外側実waitまで秒 | 管理出力bytes | worker peak RSS KiB |
|---|---:|---:|---:|
| 0 | 510.2745092360001 | 18843313 | 40604 |
| 1 | 507.8021681120008 | 18832703 | 40612 |
| 2 | 511.269913823 | 18825911 | 40348 |

各outer実wait returncode0/external_reaped、external coordinator exit0/reaped、internal worker exit0/reaped、無signal、deadline未到達、全owner internal_success/all_owned_matched/worker_ok。outer保存external receiptは原external-finalと型・float値込み一致。

coordinator.logのpost_final_fsyncはexternal採録と一致。external.stdoutの最終external_post_fsync success trueはouter採録と一致。内部最終保存観測、external最終保存観測、outer実waitすべて900秒未満。outer_wait.pyは実p.waitとmonotonic終了時刻を記録するsourceであり、自己申告計算秒だけに依存していない。外部stderrは全owner空。

worker PIDはjournal worker_started/dependency_verified/internal/external間で一致。mpmath1.3.0、source inventory87、actual_import_verified true、RLIMIT_AS536870912bytes。RSSはworker自己計測の保存値であり、外部独立RSS観測やprocess-tree512MiB保証とは呼ばない。supervisor/external RSSは別記録。

管理出力はEXTERNAL-MANIFEST掲載集合＋自己manifestの実bytes合計とsummary一致。各claim261bytesを加えても64MiB未満。配布用同梱資料の追加と管理出力上限の対象を区別する。

## stage2入力の残る固定作業

全完了owner条件は通過したが、既存outer-end.jsonにはstdout_sha256字段がない。stage2 templateのselectorを存在しない字段へ設定したり、元wait receiptを書換えて当時の観測と偽装しない。親提案を受けた最小修正は、stage2側で既存outer-endのexternal_post_fsync objectをselector指定し、別pinされたstdoutの厳格な単一JSON行と型・float値込みcanonical JSON同一を照合する方法。両原fileのbytes/SHAとowner ZIP内memberへの原bytes一致を完成input manifestで固定し、既存実exit/reap/elapsed<900検査を維持する。これなら後付けhash字段や過去receiptの改変は不要。修正sourceと完成input manifestを別レビューする。

数値結果はmatched_noncertifiedの運用上一致であり、保証精度・F0/VUV/MOS改善や採用判断の意味ではない。固定人工309frame/6180参照を独立標本として扱わない。

機械可読集計: `pitch-fixed-bf-results-independent-audit-20261020.json`。
