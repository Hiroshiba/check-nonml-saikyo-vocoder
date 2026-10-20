# 固定候補stage2 source v1：実行境界の差分再レビュー

2026-10-20 UTC。対象 `pitch-stage2-source-review-v1-20261020/package`。v0との差分・全source読取、bytes/SHA・ASTのみ。candidate import/実行/tests/smoke、科学算術・BF・gate再評価なし。

## 判定

**前回B1/B2を解消。本担当のsource静的レビューは通過、新blocking issueなし。** ただし入力manifestは意図的に未完成であり、現時点は起動禁止。独立owner成果物監査、完成input manifestのpins/selector/prefixレビュー、科学pointer担当の通過、環境割当と別開始指示が必要。

## B1：partial receipt・最終保存

`output.write` は新規 `.partial` へ全bytes書込み・flush/fsync後に最終名へrenameし、directory fsyncする。既存targetは拒否、途中temporaryは保持、出力quotaはtemporaryを含める。workerの240秒killが途中に入っても、完成していない最終名を通常publishしない。

`run.py` はreceiptのread/load/schema検査をtryで保護する。欠落・partial・不正JSON・object以外・字段不足/型不正・非finite時計を捕捉し、worker_receipt_state/error/reason/tracebackを残して最終receipt/manifest保存へ進む。未知状態を算術成功へ昇格しない。

成功にはvalidated receipt、stage1_all_owners_adopted true、arithmetic_dps80、4180unique/309frameを明示要求し、従来のcode0/reap/無signal/300秒未満条件を維持する。worker未reapのprogress snapshot/unknownとexitcode nullも維持。最終fsync後のclock/サイズ判定と親の実waitを必要とする設計は不変。

atomic publishとreader保護の両方により、前回指摘したparse例外が最終終了証拠保存を飛ばす経路を解消している。ディスク全体障害などで保存自体が不能な場合の完全保証は行わず、親のstdout/stderr/wait証拠回収は引き続き必要。

## B2：未知eventと順序

`adopt.py` はpoint eventを point_start/stage_start/quadrature_progress/value/point_done の5種類だけに限定する。eventがobjectでない場合、unique_id付き未知type、owner/type不一致を拒否する。

control順序はworker_started→dependency_verified→worker_finishedで固定。pointは前2control後・finished前だけ、finishedは全owner point採用後だけ。各pointは単一昇順attempt、50/80桁それぞれprimary→quadrature→laplace、stage_start後の対応value一つ、Q progressは該当Q stage内でextension0から連番。6stage/value完了前point_doneとstage重なりを拒否する。

承認済stage1 kernelが保存するprogressは0から拡張ごとの連番であり、今回の制約は数理分岐・gate変更ではなく保存event整合検査である。未知eventを黙って無視する前回経路はない。

前回記載したcounter整数/範囲/非減少、他owner zero counter、内部外部PID相互照合等の追加防御は今回変更されていない。これらを含む原owner成果物の独立監査と固定pinsを前提に採用する。今回すべての追加防御をsourceへ実装したと解釈しない。

## 最小性・pin

- SOURCE-MANIFEST SHA `04a747adcb6e57258d2b2d7e594b1d60e53186354e4b99850ca0af52b5cd5cb7` は親指定値一致。掲載22filesと自己manifestの集合、全bytes/SHA一致。
- 全8 Python sourceをAST解析成功。candidate importなし。
- code変更はoutput.py/run.py/adopt.pyとarithmetic.pyのpointer field修正のみ。
- worker.py、inputs.py、archive.py、dependency.py、DEPENDENCIES.json、SCHEMA.jsonはv0とbyte同一。
- arithmetic.pyの変更はA/static保存pointerへ `values.` prefixを付ける箇所だけ。数値式・precision・差・LSEの変更なし。pointerの元入力との全件整合は別担当の結論に合わせる。
- 300秒総wall、240秒科学deadline、250秒reap目標、worker512MiB、64MiB出力、末尾4MiB/claim4096bytes予約、一回claim、自動retryなしは不変。
- ZIP56332bytes/SHA `f4f8dd44492548ea9941786e8094c0b020156af0ce037e210eb8ff81a66cf923` は親の正式転送確認に依拠。

## 停止線

INPUT-MANIFEST.templateはUNRESOLVED_TEMPLATE_DO_NOT_RUNのまま。claim前拒否は継続。入力結果を推測で補完しない。各owner全完了と外部stdout/親実waitをpinし、selectorの意味・stdout hash結付けを独立確認する。正常stage2完了と科学的精度保証を混同しない。現source通過だけで計測開始しない。
