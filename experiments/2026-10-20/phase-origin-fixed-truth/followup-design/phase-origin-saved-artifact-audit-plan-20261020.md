# phase-origin 保存成果物の読取監査計画

2026-10-20。計測未開始・source v1修正待ちの準備文書。根拠は[入力レビューv0](phase-origin-source-input-review-v0-20261020.md)と `phase-origin-source-review-v0-20261020/package/{CONTRACT.md,SCHEMA.json}`。これは実行許可でも結果監査PASSでもない。

## 1. 受領・版固定

- 承認済みv1 source/input/schema/依存pinとそのレビュー、開始許可、study/owner割当を先に固定する。v0 package内の「v1」表記やschema IDだけで修正版と同定せず、実bytes/SHAで区別する。
- delivery/parts manifest、ZIP/member、part順・offset・長さ・SHAを照合し、連結した保存streamから原fileのpath/bytes/SHAまで確認する。重複path、欠落、余分なmember、範囲重複を記録する。原本・partial・原stdout/stderrを変更せず、監査結果は別ファイルに置く。
- v1で必須検査のassert依存が解消されていることと、実行時pin確認証拠を確認する。依存pin表の存在だけをruntime一致の証明にしない。

## 2. 全予定台帳とowner・状態

- 正本500行、truth別100、pair_id 0..99、global_id=100×truth_id+pair_id、owner=global_id mod3、owner件数167/167/166を整数照合する。各owner保存の全予定台帳は同じ500行を記録してよいが、実attemptは担当ownerだけ・各pair最大1回である。
- authoritative claim、study未使用確認、ownerとrun/outputの対応を照合する。別ホスト・別claims-dirでの重複が否定できない場合は一意性を保留する。ファイル重複を黙って一方に採用しない。
- 科学状態とprocess状態を別軸で記録する。各行は次の証拠により分類し、未着手・中断・終了不明を数値失敗へまとめない。
  - **成功候補**：complete記録、v1必須保存物、保存gateが整合。owner終端未確認なら採用保留付き。
  - **科学失敗**：numerical_failureとstage/理由。返却済片側値・rawは保持。
  - **中断**：started/inflight等が残り、実終了・killの証拠がある。
  - **未着手**：終端証拠と予定/実行ledgerから開始なしを確認できる。
  - **終了不明**：実wait/reapが未確定、または証拠矛盾で以上を確定できない。metadata不在だけで未着手としない。
- 全500予定分母を維持する。破損・転送未完は監査上の欠落として併記し、科学失敗原因を創作しない。不完全ownerからの自動救済採用はしない。

## 3. rawと参照

- descriptorのname、dtype `<f8`、整数offset、shape、bytes=8×要素数、file範囲、8byte整列、該当sliceのSHAを確認する。配列名ごとの予定長1/64/4096とv1のstage別必須集合を照合する。
- 異なる実blobの範囲は重複しないことを確認する。共有は承認済みaliasのみとし、q→g、oracle geometry→train/testの参照先とbyte同一性を確認する。64点の4096点展開は参照規則の検査にとどめ、波形再生成をしない。
- intent、完了descriptor、raw末尾、残存partialを区別する。intentだけのsliceや未完appendを保存完了配列に数えない。余分な末尾も削除せず、その来歴を保留する。
- seed入力・split/component・保存初期state/hashの対応と一意性を保存記録同士で照合する。PRNG初期化・drawは行わず、state hashの一意性を出力非重複の証明にしない。
- membershipは保存整数区間の連続性・4096点被覆・参照整合を確認するだけで、位相から再推定しない。診断residualと密度評価内の高精度差を同じ配列と呼ばない。

## 4. 各精度・失敗時保存・gate

- root50/80は返却statusに応じ、係数・返却根全体・err・分類・失敗理由を確認する。NoConvergenceで未返却の途中根/反復数を要求せず、予定maxstepsと実反復数を混同しない。
- oracle60/90とestimated60/90の各返却保存を独立に確認し、次精度や後続gateの失敗で前の返却値が消えていないか、stage/イベント証拠と突き合わせる。保存記録がない返却を推測しない。返却と永続保存の間のkillを外部証拠なしに判定できるとは主張しない。
- 保存score表の順序・精度・有限性、Q非負、単精度保存値との一致、保存relative_checksと固定threshold、passed/statusの整合を確認する。十進文字列は二進floatへ丸め直さず比較する。
- gate監査は**保存済み診断値と閾値の比較だけ**とする。scoreの減算、相対誤差、root残差、係数、密度、位相誤差を新たに計算しない。したがって「保存gate記録が整合」とだけ結論し、gate算出自体の独立数値検証・精度認証とはしない。

## 5. 終端・予算証拠

- worker receipt、supervisorの実worker wait/reap、outerの実supervisor wait、parent-tool-wait原文、manifest後fsync観測を相互照合する。PID/starttime/run/owner、returncode、reaped、elapsedの値と型・由来を確認する。
- 自己申告completed、過去PID不在、sourceの予定時刻だけではprocess成功にしない。親の実tool waitを含む証拠が欠ければ保留。成功に必要なwait0・期限・最終保存は承認済みv1契約に従う。
- 保存file/stream bytes、overflow/非保持bytes、cap、signal、資源観測を照合する。worker単体RLIMITとsupervisor等の別計測を区別し、OS全tree資源保証やログ完全性を過大表示しない。

## 6. v1到着まで未確定の項目と報告

**未確定**：estimated単精度字段と逐次保存の証拠、校正失敗時のoracle診断残差の要否、stage別必須配列集合、gate失敗前後の保存status、および修正版終端証拠の具体的selector。v0にない字段を存在すると仮定しない。v1差分レビュー後、この対応表だけ確定してから結果採用を判定する。

監査報告は版/pins、受領完全性、500行の状態・owner別件数、阻害事項、保存値/終端証拠の採否を短くまとめる。process成功と科学成功を分け、1件でも欠測なら全100平均Δを補完しない。既存summaryは対象分母・null規則だけ照合し、この監査で平均等を再算出しない。

再生成・再score・PRNG・科学import・tests・新指標・CI・bootstrap・追加精度・retry・旧500変更・コード作成は対象外。
