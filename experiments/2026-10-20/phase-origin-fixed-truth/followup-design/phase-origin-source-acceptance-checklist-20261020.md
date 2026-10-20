# 位相原点対照：source 受入れ確認票

2026-10-20。準備物の静的審査用。実行許可でも実行結果でもない。

## 変更しない対象

新 study の 5 truth × 100 pair、真 θ 固定、既知解析 q と既知 F0、同始点の独立 train/test。比較は oracle 位相と train-only OLS 位相の test Gaussian log density 2 本。旧 500 pair と PML base は変更しない。追加の KL 列・品質評価・再生成・smoke/test は行わない。

## 受入れ時に残す証拠

1. Library 原本 ID・version・ZIP bytes/SHA と全 member manifest の照合。未採用 source は Git に載せない。
2. 数学レビュー：q と q′、OLS 多項式の係数・次数、全返却根の分類、50/80 dps の対応、非認証性、40桁有理位相への写像、floor と境界規則。truth/test を校正へ渡さないことを呼出し経路で確認する。
3. 密度レビュー：W/V の対角、A の定常初期項、S/J の実際の部分周期。有限位相に oracle 完全 block の局所式を使わない。二精度 60/90 dps の比較と失敗時の片側値保持。
4. 生成レビュー：新 seed mapping、独立 train/test、raw の dtype/shape、逐次保存と lossless 参照復元、共通 q と異なる残差の取り違えがないこと。
5. 実行レビュー：全 500 の事前台帳、167/167/166 の一意 owner、exclusive claim、起動失敗も一回扱い、親による全ホスト割当。各 owner 900 秒・science 840 秒・worker 512 MiB・科学出力 64 MiB の具体的管理。
6. 保存レビュー：各 write の最大 bytes、同時 partial、stdout/stderr、終端予約を含む厳密上限。圧縮率を仮定しない。全返却根は保存し、NoConvergence が返さない内部根や反復回数は unknown とする。
7. 停止レビュー：独立監督の期限、進行中処理の停止、kill/reap、未 reaped 時の unknown、最終 fsync 後の時計、外側実 wait の一次記録。receipt を後から実測記録のように作らない。
8. 静的確認：AST・cached Ruff・依存 metadata・hash に限定。候補 import、PRNG 初期化、根計算、密度計算、テストは source 準備に含めない。
9. 転送レビュー：科学時間と別の immutable 転送工程、各 chunk の上限・offset・bytes・SHA・復元順序。転送不成功で科学を再実行しない。

独立レビューで阻害事項が残る場合は source 修正のみ。全項目確認後に別途開始判断と一回性台帳を作る。局所 Fisher の紙上参照と参考音声の表示契約は、この受入れを代替しない。
