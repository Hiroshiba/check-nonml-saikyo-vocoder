# Recovery source v1: V 数値部分の独立静的レビュー

2026-10-20。**数理・求積部分の静的条件通過、未実行。新しいblocking issueは見つからなかった。**

対象はoracle-evidence-preparation/quadrature_disk.py、CONTRACT-ja.md、RECOVERY-ja.mdの数値契約。比較はevidence-source-review-v3-20261020の旧ソースとevidence-v-efficiency-diagnosis-20261020.md。BudgetExceeded診断の外側保持を確認するためworker.pyの該当catchも読んだ。recovery/union/資源管理実装全体の承認は別レビュー範囲。

候補実行/import、tests/smoke、新規求積、保存残差読込、候補編集はしていない。標準ライブラリのhash/JSON/AST読取のみ使用。

## 同一性

- source-manifest SHA256: 11b308a02d96cd3e55ef407006131a7677ff57604185f3ca83fb93660ea094ad、依頼値と一致。
- 全18 deliverablesのbytes/SHA256一致、PythonのAST parse成功。
- ZIP SHA3fbd1bbf607a76e746cfb8fa5c3c1f1c6b7ac3d14939dcbdb1ba295ef63409fcの照合は親の結果に依拠。本担当ではZIP自体を再照合していない。
- core.pyは比較元と差分なし。quadrature_1d.pyもbytes同一。

## 1. 科学的積分の不変性

Vのenergy=e_l/T、保存zの実和F=rKΣz、log kernel=-h logΣ(e_l/T)e^(-b·z_l)-b·F/2-log(πR²)、R=1.5、gradient/Hessian、全円板coverage、mode/KKT、tangent support最大と面積は旧版と同じ。

polarのr Jacobian、Cartesianのb_x=R sin u・b_y=R cos u vとR²cos²u Jacobianも不変。A/S/J/W、raw predictive/BMA定数、共通scale・shape priorにも変更なし。

従って変更は同じ積分の探索・重複評価除去・収束照合のrefinementに限定される。低いweightのモデルや領域を削除する変更ではない。

## 2. small総量とactive-only refinement

classifyは個別upper/M<1e-10候補をupper順（同値はindex順）に処理し、logaddexp累積がlog1e-8以内のsubsetだけをsmallとする。溢れた候補はactiveに残る。別logsumexpによる再集計も検査し、丸め超過を例外とする。

small候補全件を機械的に免除する旧停止条件から修正されており、個別閾値・総量閾値の緩和はない。activeはsmallの補集合で、最大riskの選択もactiveに限定される。全cellは最終積分に含まれる。empty activeはfail-closed。

## 3. GL32分母と最終分類

探索時はGL16全cell massを分母とし、denominator_ruleを保存する。最終GL32算出後、GL32全cell massでclassifyを呼び直し、small候補・subset・active risk・omittedを全て更新する。最終gate前にも同じGL32分母で再分類する。

従って新smallを作ったのに旧active riskを使う穴はない。最終active riskが1e-8を超えればnot_convergedとなり、再分類による未達を成功へ通さない。旧M16比を新M32比と表示する問題も解消している。

最終再分類が未達でもangular/Cartesianを先に続ける場合があり、まだ節約可能な仕事は残るが、成功判定を弱める問題ではない。

## 4. cacheとpartition整合

- makeは同じcellのgl8/gl16を保存し、最終現存cellだけから同じlogsumexpで集計する。削除済みparentとの二重計上なし。
- GL則cacheは8/16/24/32/48/64/96の7次数に限定。finite/positive weightsを検査し、node/weight配列をread-onlyにする。座標変換は新しい配列を作るのでcacheを破壊しない。
- mass cacheは当該disk_integralのcellに限られ、他pair/train/jointへの共有なし。次数別node/weightのみ共有可能。
- 子2個のmakeが両方完了した後にparentを削除する。分割途中の予算例外で最後の完全partitionの要約を保持する。
- 4096 cells上限の未達終了は維持。境界欠落/重複を新設する変更なし。

## 5. Cartesian24/48、必要時64/96

固定列24,48,64,96を順に評価し、2段揃うまではbreakしないため24/48は必須。最新2次数差≤2e-7かつ最新値対polar GL32差≤5e-7を満たした時のみ打切る。96未達なら最終gateでnot_converged。128等への無制限延長なし。

全済次数・値・実点数はfinal_checksに保存。有限性検査を維持し、古い都合の良い2次数を任意選択する経路はない。最終判定でも最新2段を再検査する。polar GL8/16/32、angular別則、partition history、risk/omittedなどの既存gateも残る。

旧24/48必須合格から固定階層最新2段への手順変更はCONTRACT-ja.mdに明記されている。2e-7/5e-7等の閾値自体は不変。この変更が過去の失敗を遡及成功へ変えることはない。

## 6. 予算と例外診断

reserve_stageはGL32・angular別則の正確な必要点数、Cartesianは実際のu/v区間構造から算出した必要点数を残予算と比較する。不足時は評価前にBudgetExceeded。評価中は従来のbudget.tickが点数/時間/メモリを確認する。cache再利用を新規評価へ水増ししない。

最大Cartesian点数は契約記載どおり全4次数582,912。cache後でも全件が200万点に収まる保証はない。不足したstageが未達となるのが正しい。

BudgetExceededにstateを添付し、stage、最後の完全mesh要約、完了済み照合値を保持する。initial_mesh途中ではlast_mesh=Noneとinitial_cells_completedを残し、全支持完了とは偽らない。workerのBudgetExceeded catchはerror.diagnosticsをIntegralへ転記し、reason/evaluations/timeを付加することを確認した。

注意点:

- 全meshを保存する実装ではない。要約からcell単位再検証はできない。
- initial/refinementのtickは呼出前に加算するので、その例外時evaluation数はattempted点を含み得る。事前reserve拒否の場合は未実施stage点数を加算しない。stage_points_requiredと区別して読む。
- stateの詳細添付はBudgetExceededに限定される。一般のArithmeticError等は外側で理由を保存するが同じ途中stateを必ず保存するわけではない。今回要求した予算例外diagnostic改善は満たす。
- polarのfinish条件だけが失敗した場合、reasonが明示されないことはあり得るが、not_convergedとlevels/alternate自体は保持される。追加説明改善の候補であり、偽成功ではない。

## 7. 旧V成功2件のreuseとの整合

A-001/train/VとW-004/train/Vは旧gateの保存診断を満たし、omitted比約1.26e-9/1.34e-9、Cartesian24/48差約4.01e-8/2.40e-8。これらの値は前レビューで実results.jsonから確認済み。

同じ科学的積分の推定値であり、今回のcache/探索変更は旧成功を数学的に無効化しない。新Cartesian法でも24/48が合格なら追加しない設計に整合する。

ただし新分類を旧meshへ実適用したわけではない。RECOVERY-ja.mdは原値/旧gate/旧sourceを保持し新gate適用済みとしない旨を明記しており、このreuse方針は妥当。入力・旧結果・slot来歴の実装上の厳密照合についてはrecovery担当の確認を要する。

## 8. 承認の範囲

本担当は同一integrandの数値設計と変更差分について静的条件通過とする。科学run開始許可、全件収束、並列実行の資源保証、recovery/union全体の承認は含まない。実際のruntime・改善率・最終誤差は未検証。upper/risk/refinementは非certifiedな診断という限定も維持する。
