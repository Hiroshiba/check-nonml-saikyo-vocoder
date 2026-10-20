# 履歴対比 source v1 実行境界・限定差分レビュー

## 結論
静的 PASS。今回の変更に起因する blocking は認めない。これは実行許可や実測成功の認定ではない。入力・科学側レビューと親の別途開始指示を前提とし、一回実行後は外側の実 wait、終了 code、reap、post-fsync 証拠を別に監査する。

## 対象・方法
対象は `pitch-history-contrast-source-review-v1-20261020/package`。v0 との byte 差分、全 manifest の bytes/SHA/file set、source 6 ファイルの AST、変更箇所と終了経路を読取確認した。候補 import/実行、tests/smoke、科学値の再計算は一切行っていない。

SOURCE-MANIFEST SHA256 は `2913969218f72c840f6083268533c531029f01fd2066095c754ab39f59fdbe4b`。23 entries と manifest 自身の全24ファイルを照合済み。INPUT-MANIFEST SHA256 は従来の `bbd2f6b8764fffb09c5b1f6e65d331526200ce2832caa31e7b95275894d6b22a` のまま。

## 差分と影響
- `source/run.py`、`storage.py`、`contrast.py`、`inputs.py`、PAIRS、INPUT-MANIFEST は v0 と byte identical。確定 design、UPSTREAM-PINS、PREPARATION-AUDIT も差分なし。
- runtime 差分は summary.py 追加と worker.py の import、summary 辞書生成、observe 呼出し、summary 出力 fields の追加だけ。別 process、再試行、外部 command、追加依存はない。
- summary.py は canonical X/I タグを既存 validate で検証し、finite の符号・大小比較と整数計数だけを行う。保存十進文字列を min/max にそのまま転記し、同値の全 pair_id を入力順で保持する。finite なしは null。減算、丸め、BF、exp/log/LSE、元 D の符号反転集計、tests は追加されていない。
- observe は各 CSV 保存後、completed-pair counter 加算前に呼ばれる。異常タグ・比較例外なら worker の既存例外経路で失敗し、当該 pair は完了 counter に含まれない。正本行や CSV の部分保存は保持され、成功と偽装しない。summary 保存失敗でも worker-receipt complete true に到達しない。
- summary の処理は同一 worker 内、既存 Decimal context 内で行われる。worker 128 MiB、science 50 秒、supervisor 60 秒、50 秒停止・54 秒 reap 目標は不変。比較処理に専用 deadline check はないが、外側 supervisor の同じ 50 秒 kill 対象であり、無制限の別作業経路は追加されていない。
- summary は既存の atomic write、fsync、rename、directory fsync、8 MiB guard を利用する。通常出力用の 1 MiB 終端予約と claim 用 4096 bytes 予約も不変。末尾保存後の elapsed < 60、worker exit 0/reaped/no signal、100 completed-pair の成功条件も変更なし。
- persistent exclusive claim と package/input/output 分離は不変。ホストをまたぐ一回性は従来どおり親の管理も必要。

## 原 producer 証拠と範囲
追加 evidence 4 ファイルは source manifest で固定され、EVIDENCE-MANIFEST は出所・bytes/SHA と読取目的を記載する。runtime source の import/call に evidence は接続されていない。source 検証による bytes/hash 読取のみで、同梱 producer/model を実行する経路はない。今回の限定監査はそれらの producer 意味論・独立原本一致の科学側確認を代替しない。

CONTRACT は canonical X/I の比較集計と原証拠の非実行を明記し、予算・一回性・非保証の制限を緩めていない。追加ファイルの hash 検証時間も supervisor 入口からの同じ wall budget に含まれる。

## 実測時の継続条件
元の静的レビューの条件を維持する。実行成功は保証しない。保存遅延・OS I/O・kill/reap の不成立は外側の時計と実 wait/終了証拠で fail-closed に扱い、失敗や部分出力を消さず、自動再実行しない。採用には post-fsync stdout、内部 receipt、外側終了 code/reap と 60 秒未満・8 MiB以内の一致が必要。
