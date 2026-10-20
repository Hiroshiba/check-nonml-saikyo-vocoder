# 位相原点対照 source v2 の開始前判断

2026-10-20 12:27 UTC。source v0/v1 の未通過履歴を維持し、v2 を今回の限定実験の候補として静的に受け入れる。開始指示と唯一owner割当は別記録で行う。この文書だけでは実行しない。

## 固定物
- Library libfile_f2e185d9cdc081918f65c5c3dcb9a0ac version 2、file_0000000096d8822fab07b003b2cb5943。
- ZIP 1,063,233 bytes、SHA256 270f33db7f574167620b756b4d4446664c54199c55d0ebf53643b2ea71ec4955。
- source manifest ad683e29f1d2ac1bc7200bfa6308e3875e20a45558f6b6947ef728d27d419842。全52 entriesとmanifest自身の53 filesを親で照合。
- input manifest b60194d8460f6499dfd7fc9549707b688587ef35c835074837232c0f06b523e4。

## 判断
v1の数理・入力レビューと、v2の実行・入力差分レビューを確認。v2の変更は4本の実行/診断sourceと説明・schema等に限り、model/calibration/worker/storage、入力・seed・依存はv1とbyte不変。v0の非有限値変換、片側得点保存、最適化で消える確認、例外時停止をv1で修正し、v1のroot JSON混入台帳と異常stack不足をv2で修正した。起動前失敗は通常packing gateを緩めず、科学採用不可の別証拠保全として扱う。

今回受け入れるのは、保存binary64観測・固定80dps由来の丸めgeometryを使う数値的な二得点の対照である。理想解析OLSと有限精度手続を区別し、50/80根一致・60/90密度一致はnoncertified診断とする。全根/真値精度の認証、丸め生成法則での理想期待恒等式、自然音声の品質向上は主張しない。Wの局所−1/2 nats参照を合否gateにしない。

新studyの5truth×100独立train/test pair、真θ固定・既知q/F0、oracleとtrain-only OLSの二得点だけ。旧500やPMLは不変。実行後に閾値・精度・seed・科学sourceを変えず、失敗も予定500分母へ残す。各owner一回、167/167/166、同時最大3。各900秒wall・840秒science・worker512MiB・科学output64MiB。時間/RAM/収束/診断容量の完走は未実測で保証しない。

## 開始前の残作業
3環境の正式配置、source/出力/claims/親tool証拠/転送の絶対path分離、依存pin一致、既存claimなしと科学processなしを確認し、親の唯一owner台帳を固定する。その後だけ各ownerへ別の一回開始指示を送る。summary入口は隔離のまま、保存結果監査後の別source/レビュー/指示を要する。転送や保全の失敗で科学を再実行しない。
