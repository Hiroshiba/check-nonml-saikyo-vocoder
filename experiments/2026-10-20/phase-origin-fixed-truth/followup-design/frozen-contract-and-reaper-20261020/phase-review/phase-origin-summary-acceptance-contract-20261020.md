# phase-origin 後段記述集計の最小採用契約

2026-10-20。計測前の紙上契約。source v1の隔離summary prototypeは承認済み集計器ではなく、v2実行境界は修正中、科学実行0。計測後に保存証拠を監査し、別source・別レビュー・別の一回指示で集計する。今回、実装/import/計測/tests/Git操作は行わない。

根拠：source v1 `CONTRACT.md`、`deferred/summarize-prototype.py.txt`、`phase-origin-saved-artifact-audit-plan-20261020.md`。監査計画中のv0/v1未確定箇所は最終承認版のschemaと終端selectorへ更新してから使う。版名が同じことをbytes同一の根拠にしない。

## 1. 入力採用gate
1. **版固定**：開始を許可されたstudy/source/input/schema/contract/dependencyの期待SHA、owner割当、開始指示、集計sourceと集計入力manifestを固定。全ownerで同一契約・同一500予定台帳。科学import前のpin検査と実runtime照合証拠を確認する。
2. **owner一意性**：global_id=100×truth_id+pair_id、owner=global_id mod3、W/A/V/S/J各100、計500、owner167/167/166。authoritative claimとRUN、host/output/実processの結合、各担当pair最大1attemptを照合。重複owner・重複ID・別claims-dirによる不明重複は黙って選ばず拒否/保留。
3. **終端の実証拠**：typedな親tool終端proof＋原文全bytes、outerによるsupervisor実wait、supervisorによるworker実wait/reap、durable birth/ack/execのPID/start_ticks、元owner/runを結ぶ。最終manifest/fsync後観測と契約時計を確認。正常採用は最終承認契約のwait0・reap・期限・保存条件を満たすこと。存在だけのparent-tool-wait、self completed、PID不在では不可。終了unknown/矛盾はそのownerの科学採用を保留し、complete行だけ抜き取らない。
4. **immutable配送**：PARTS-MANIFESTのpart順/offset/長さ、ZIP/member SHA、連結stream、原file inventoryと全bytes/SHA、親proof/rawまで照合。重複/欠落/余分・範囲重複・転送不完を拒否または保留。immutable原本を集計器が編集しない。
5. **行の完全性**：completeは必要条件に過ぎない。最終schemaのstage別保存物、raw descriptor `<f8`/shape/offset/長さ/SHA、許可alias、root50/80とoracle/estimated60/90、保存gate/threshold/status、90桁以内の原十進token、位相誤差を照合する。保存診断と閾値の整合検査だけで、root/密度/score差/位相誤差を再計算して科学gateを再評価しない。

booleanと整数、数値stringと数値型、非有限値を混同しない明示検査とする。必須gateをassertやファイル存在だけに依存させない。独立監査通過は保存証拠の採用可能性であって、noncertified数値法の真値誤差保証ではない。

## 2. 全500台帳と状態
全予定IDを必ず残し、owner未配送・起動前失敗でも行を削らない。各行は科学状態とprocess/証拠状態を別字段で保存する。
- 科学complete採用、numerical_failure（stage/理由・返却済oracle等保持）。
- 実終端証拠のある中断、開始なしを証拠で確認した未着手。
- 終端unknown、原本破損/配送欠落、起動前失敗・科学未開始を別分類。
metadata不在から未着手や科学失敗を創作しない。全ownerが正常終了しても全500科学成功とは限らない。

終了済failed ownerの保存物や、通常packingが拒否する起動前失敗は、別の証拠保全契約で扱う。科学採用可能な通常deliveryへ見せかけず、再起動・再生成・欠測補完をしない。failed owner内completeの自動救済も今回認めない。未知ownerは保留を残し、集計一回を開始するには、3ownerの採用/保留区分と固定証拠snapshotを先に凍結する。

## 3. 記述集計の範囲
各truthの予定分母は100固定。採用gateを満たす科学completeの同一subsetを、次の5字段すべてに共通使用する。
- 保存90dpsの oracle score、estimated score、Δ=estimated−oracle（nats/record）。Δは保存tokenを使用し再差分しない。
- 保存phase errorのcycles、radians。誤差の符号/円周定義は最終schemaの保存規約を継承し、再wrapや別定義を導入しない。

この5字段ごとにcount/min/max/meanだけ。加えて**cyclesの保存誤差だけ**にphase MAE（絶対値平均）とRMSを記述する。radians版MAE/RMS、truth間プール、新しい分位点・標準偏差・検定・CI・bootstrap・順位等は追加しない。

count=0ならmin/max/mean/MAE/RMSはnull。0<n<100なら成功subsetの条件付き参考として明示し、全100平均はnull。n=100のときだけ全100平均を表示可。既定のall100_delta_meanはn=100だけ保存Δの平均、その他はnull。phase MAE/RMSや他字段のmeanも、全100量として掲げるなら100件揃うことが必要。欠測を0で埋めたり、subset meanを100で割って全体平均と呼ばない。

planned=100、採用complete数、理由別の状態件数、生成train/test双方の確認件数、保存calibration_passed数、明示されたnonfinite失敗数を併記する。prototypeの「test/Y存在だけで双方生成」やerror文字列の曖昧な部分一致を確定証拠にしない。全IDの理由を保存し、分類合計と分母の整合を確認する。

## 4. 精度・原値・集計保存
原90桁tokenと元raw/source/owner/file/pointerを原bytesまたは固定参照で保持する。記述集計ではprototype相当のbinary64変換・math.fsum・sqrtを用いることを別契約で固定し、出力を「保存高精度値をbinary64化した記述値」と表示する。float表示が原90桁値を置換した、または90桁精度の平均を与えたとは称さない。

原tokenの有限性を先に確認し、float変換overflow/非有限や集計算術の非有限は**集計工程失敗**として停止・保存する。科学失敗へ再分類したり、当該行を落としてsubsetを都合よく変えない。二進丸めによる微小量のzero等も原tokenとの区別を維持する。表示桁数・runtime・変換規約を記録する。

集計出力は別directoryに、全500台帳・各採否/理由・全入力SHA/pointer・subset ID一覧・分母・既定統計・集計source/runtime・実終端receiptを保存する。元owner receipt/raw/90桁値は不変。集計の予算・停止時checkpoint・外部終了証拠・出力上限は別の集計実装レビューで固定し、その前にprototypeを実行しない。
