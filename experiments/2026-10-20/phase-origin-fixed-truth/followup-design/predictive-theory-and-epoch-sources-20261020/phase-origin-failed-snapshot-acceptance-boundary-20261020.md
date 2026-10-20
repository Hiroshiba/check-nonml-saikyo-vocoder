# phase-origin failed snapshot：報告可能範囲と採用停止線

2026-10-20。親の現在状況報告と `phase-origin-summary-acceptance-contract-20261020.md` に基づく紙上整理。実成果物はまだ親へ転送不可で、本担当による原本監査ではない。コード・計算・測定・Git変更なし。

## 現在報告できる事実
出典を「各ownerの保存記録・担当者報告」と明示したうえで、3 worker exit0、500行completeとの報告があること、全outer/supervisor exit2、`/proc/self/task/{PID}/children` のFileNotFoundErrorにより歴史的な全子終了がunknown・immutable=falseとなったことを報告できる。通常packingが拒否された判定は維持する。

別の失敗snapshot保全を3ownerで実施し、コピー前後の比較では原bytes/mtime/SHA不一致なしとの報告。owner1/2のmetadata/raw/保存gate読取監査は不一致0、owner0は監査中。この「コピー期間に検出された変更なし」は過去全子終了の証明ではない。

Library prepared-upload helperのtools/list HTTP403により全成果の親への転送が未完了。これは保存科学値の良否と独立した転送上の阻害。403の原因・解消・完全な受領を推測しない。

現時点で「500行completeの報告」は言えるが、「500件を正式採用」「全owner正常完了」「全子終了証明済み」「通常契約のimmutable delivery成立」「親が全原本監査済み」は言えない。unknownは生存の証拠でもなく、生きたprocessが存在したと断定しない。

## 正式集計・科学採用の停止線
**現在は採用しない。正式集計・prototype実行・summary作成を開始しない。** 原sourceのprocess失敗、immutable=false、packing拒否を後から成功へ書き換えない。

通常契約で採用するには、承認source/input/dependency/owner/claimの一致と500台帳、全raw/metadata/part inventory原hashの完全受領・独立監査に加え、契約で要求した歴史的process identity、全子の実wait/reap、outer/parentの実終端と期限・最終保存証拠の整合が必要。欠けた過去観測を現在PID不在・complete行・安定copy hashで代替しない。

さらに、全outer/supervisor exit2という既存事実は、後から追加証拠が見つかってもexit0へ変わらない。したがって通常のwait0成功gateに遡及合格したとは扱えず、通常採用へ戻すという名目で閾値や終端条件を緩和しない。履歴証拠が回収できればunknownの範囲を明確化できるが、別採用を検討する場合も以下の事後契約を先に固定する。

## 将来、別のsnapshot分析を検討するための前提
これは採用の決定・実行許可ではない。独立レビューと親の明示判断を経た、通常成功とは異なる事後分析としてのみ検討できる。

1. **目的と限定を先に固定**：特定時点の固定snapshotに記録された値を記述する目的に限定。process完全成功や元計画のprospective正常完遂を主張しない。採用条件は結果の方向・良さを見て変更せず、元gate/失敗判定を併存させる。
2. **独立に固定された入力**：全3ownerのsnapshot取得時刻、copy手順、原場所/元fileとsnapshotの対応、開始前後の検査と限界、全bytes/SHA・全inventory・原ログ/receipt/traceback/claim/予定台帳を保存。受領したarchive/partと親の独立hash監査により「このsnapshot bytes」を固定する。安定copyは証拠の一つであって、原process終了・取得中の完全なatomic性の証明とは呼ばない。
3. **集合と意味の一貫性**：固定500ID・truth各100・owner167/167/166・重複attemptなしを照合。全raw descriptor/alias/範囲・intent/partial・返却済診断・各精度・保存gateの相互整合を独立確認する。copyが安定していても壊れた/途中の値は採らない。原90桁tokenと科学値は変更しない。gate再評価・追加精度・補完・選別による救済はしない。
4. **完全な受領と監査**：owner0の未完監査、owner1/2報告の親側照合、全3ownerの完全転送を済ませる。転送不能のまま担当者の件数報告だけから集計しない。不一致・欠落・由来不明は保持し、自動で別owner/pairへ差し替えない。
5. **採用方式の明示**：新しいsnapshot-analysis source/input manifest、固定snapshot SHA、取得事由、元失敗sourceと判定、残るhistorical_children_termination_unknown、監査の限界を最上位に記録する。元receiptを書き換えず、snapshotの現在の固定性と元processの過去終了不明を別字段にする。後から証拠が増えた場合も版付き追記とする。
6. **範囲を拡張しない**：もし別途承認されても、既定truth別count/min/max/mean・cycles MAE/RMSだけ。条件付き採用subsetと全100を区別し、1件でも未採用なら全100平均null。新指標/CI/bootstrap/科学再計算/新観測は追加しない。500全再実行・別claimによる再起動を回収策として提案しない。

## 現在の判断
失敗snapshotの保全は有益だが、正式採用とは別である。今行えるのは許可された原証拠の保存・転送障害の解消検討・読取監査と、上の条件の紙上独立レビューまで。アクセス拒否を別経路で迂回せず、元保存物を保持する。転送と監査が揃っても自動で分析へ進まず、固定された別契約に対する明示判断を待つ。

## 追記：host内暫定記述案の検討と不実施決定（2026-10-20 13:23 UTC）
更新された親報告では、全3 workerの実wait0、全500行complete、各hostの保存値/raw/hash読取監査の不一致0が確認された。ただし親への完全転送・原本独立監査は未完了であり、outer/supervisor exit2、歴史的全子終了unknown、immutable=false、通常packing拒否は変わらない。上記owner0監査中という記述は当時の状態として保持する。

独立意見として、host内の固定保存値だけを対象とする事後的な暫定記述は、別契約の事前固定・静的レビュー・明示承認と限界の表示があれば検討可能とした。ただし現行の正式採用契約を満たすものではない。host別担当subsetをtruth全100と混同せず、丸め済みのhost別mean/MAE/RMSから全100統計を合成しないことが必要で、提案評価は実施許可ではない。

**親判断：host別暫定集計も実施しない。** 必要なのはtruth全100の比較であり、事後例外を増やす利益がないため、従来の完全転送・独立監査条件と採用停止線を維持する。正式集計・暫定集計・再計算・転送再試行・権限変更はいずれも行わない。既存の失敗記録と原保存物はそのまま保持し、今回はこの文書追記のみとする。現在PID不在・complete行・コピーhash安定を過去全子終了証明に置き換えず、生存processがあったとも断定しない。
