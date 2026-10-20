# phase-origin source v2：入力不変・owner ledger差分レビュー

2026-10-20。v1/v2 packageの保存bytes・JSONとsupervise.py/SCHEMA差分だけを静的確認。候補import・実行・PRNG初期化・科学数値計算・testsなし。

**担当範囲PASS。新たな阻害なし。実行許可や科学成功判定ではない。**

- INPUT-MANIFEST、SEED-OWNER-MANIFEST、DEPENDENCIES、model.py、calibration.py、worker.py、storage.pyはv1とbyte同一。source変更はdiagnostics/lifecycle/processes/superviseの4ファイルだけ。入力・truth・生成・校正・score・raw保存手続きは不変。
- v2 SOURCE-MANIFEST SHAは `ad683e29f1d2ac1bc7200bfa6308e3875e20a45558f6b6947ef728d27d419842`。本レビューの追加確認は上記不変性とledgerに限定し、他担当の全manifest監査を代替しない。
- superviseはpinned INPUTから全500予定行にstatus/attemptsを付けた正本とplanned-ledgerを完全照合してから、自owner行を選ぶ。INPUT ownersと各行のowner件数は167/167/166で一致。予定行順に全自owner行を処理し、存在するmetadataだけを分母にしない。
- 読取対象は各global_idの厳密な `pair-XXX.json`。旧 `pair-*.json` globを使わず、roots50/80 JSONが混入しない。rowのtruth/pair/owner等も正本と照合する。
- metadata未存在は `metadata_state=missing/status=start_unconfirmed`。未着手と断定せず、partialの存在を別字段に記録する。読取不能・不正はinvalid/unknown。started、またはterminalを名乗っていてもinflightが残る場合はincompleteとなる。
- complete/numerical_failureかつinflight=nullだけがterminal_metadata。ownerのledger_completeは全自owner行がterminal_metadataの場合のみ。さらに実run_ok、returncode0、reaped、signal/overflowなし、診断保存完備、worker receipt completedを必要としてprocess completedを判定する。missing/invalid/incompleteをprocess成功へ昇格させない。
- SCHEMA注記のfixed planned source、exact filename、metadata states、start_unconfirmed、not_scientific_acceptanceは上記実装に整合。失敗時の別保全もimmutable完了/科学採用と区別する。

## 結果監査での注意

terminal_metadataは構造上の工程終端であり、配列SHA・全必須字段・gateを検証した科学成功ではない。数値失敗を含むownerもprocess completedになり得る。inflightありの場合にstatusの元文字列がcompleteでもmetadata_state=incompleteを優先し、status単独で採用しない。

rawだけ残ったケース等もstart_unconfirmedのままであり、積極的証拠がなければ「未着手」に変換しない。全500予定分母、原partial、実wait証拠、科学/工程成功の別軸は[保存成果物監査計画](phase-origin-saved-artifact-audit-plan-20261020.md)どおり維持する。
