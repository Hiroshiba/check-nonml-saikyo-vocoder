# run-001：予測混合の求積失敗と明示的早期停止

現baseはPMLです。自然音声100件以上の品質比較・MOSは未実施。BMA確定0組のため、改善結論はありません。

## 保存した結果

固定500組のうち49組が部分完了、451組は未処理です。必要な5000積分は成功392、未収束96、明示的早期停止2、未試行4510。成功内訳はW98・A98・V2・S97・J97で、V成功はA-001/trainとW-004/trainです。成功候補だけの重み再正規化は行っていません。25比較のbootstrapはすべてno_successful_pairs、実施0回、全100組の区間も未確定です。

未収束96件のうち92件は評価回数上限（alternate段階89、Cartesian段階3）。残る4件はW-000/A-000/A-004/W-007のjoint/Vで、Cartesian24/48差の条件未達です。これらのCartesian48とpartition16は約4e-12〜6e-12差ですが、真誤差保証ではありません。元結果に個別判定フラグやreasonがない項目は未保存であり、記録された値から説明した判定と区別します。small分類の潜在問題は、今回実証された失敗原因ではありません。

予算例外時の途中meshは未保存です。欠落を再計算で埋めていません。成功392積分の値・診断と旧2500スコアはresults.jsonに原bytesで保持し、CSVにも保存値を転記しました。

## 停止と時刻（UTC）

開始2026-10-20 05:42:37.235495、親の効率判断によるSIGUSR1送信05:56:05.221569、worker終了05:56:20.280966、監督終了05:56:20.489230。worker PID2429、親監督PID2428を確認してworkerだけに一度送信しました。監督実時間823.253833秒、exit 2（部分完了）。27分の時計上限には未到達です。

元statusのtime_budget_exhaustedとreasonのno_new_integrations_after_27_minutesは停止処理の共通ラベルです。このrunでは明示的早期SIGUSR1を指し、実際に27分経過したという意味ではありません。元JSONは書き換えず、report-summary.jsonとCSVのreport_status/report_interpretationで補足します。

## 来歴と制約

worker RSSは93,765,632 bytes、監督RSSは17,170,432 bytes。1 GiBはworkerのRLIMIT_ASで、全プロセス合計1 GiB保証ではありません。外部監督の子PID列挙が取得できなかった点はcompletion-audit.jsonに記録し、実PID・親子関係は停止前のpsで確認しています。

元ソース・1908参照hashと旧2500スコアは不変。入力残差・候補実装コード・画像・音声はこのreportに含めません。結果・receipt・外部来歴は原bytesで複写し、その出典SHAはreport-provenance.jsonへ記録しました。後続の修正版結果は未実行で、この記録から成功を推定しません。Git登録・PR・Pages公開は行っていません。
