# 共通三原子 AR1 + D1 source の独立静的レビュー

2026-10-21。判定は **静的・数学的範囲で合格、blocking 指摘なし**。対象は pml-ar3-d1-native-v1-20261021 の未実行 source であり、実行・品質・採用の承認ではない。

## 確認した数学

- atom = −0.8, 0, 0.8、各 1/3 を H0/H1 と全 q,K に共通の有限離散 prior として実装している。連続 prior の求積ではない。候補ごとの atom 選択・失敗 atom の削除・再正規化はない。
- whitening は先頭行 identity、以後 (v[t]−a v[t−1])/sqrt((1−a)(1+a))。負の a の符号を保持する。log det C = 399(log1p(−a)+log1p(a)) を各 atom の evidence 内へ −1/2 倍で含めるため、混合前に相殺していない。
- A = K I + (WX)ᵀWX、二つの Cholesky 三角 solve、R = ||Wx−WXμ||² + K||μ||² を使う。I/K、IG(3,2)、c = 1、指数 203、K log K と determinant 項は紙上式と整合する。近接する二次形式の差、擬似逆、jitter、local clipping、white fallback はない。
- 各物理 400 標本窓に元 safeRMS を一回だけ使う。重複窓 mapping、exact-zero 欠測、未計算 mask、B ≤ 32 は旧 dense 契約を維持する。
- 各モデルの atom 昇順 logaddexp → −log 3 → 候補 prior → contiguous K 昇順 logsumexp → q 昇順 logsumexp → H0/H1 logaddexp の順が明示され、コードとも一致する。log BF の平均ではない。
- H0 診断は log m0、H1 診断は q,K 周辺化後の log mean m1。gate prior .3/.7 と atom prior を含めず、責任度は別々に 3 atom 間で正規化する。selected-q や真の noise posterior とはしていない。
- a = 0 は数学的な white 参照である。旧保存値との IEEE 一致を測定済みとも実行の追加 gate ともしていない。

## 既存処理・データ由来

selector.py、first_difference_post.py、archive_io.py、requirements、入力 manifest、dependency manifest は指定元と byte 一致。safeRMS、_stage、_readonly、save_selection、validate_input、check_grid、D1 analyze/encode の function source と AST も一致した。native adapter の差分は新 L/F 枝の許容・由来表示・timing 文言に限定され、D1 数値処理、seed 0、backend、save/load/decode は保持される。vendor 13 file の SHA と git blob、および旧 white/D1 source の完全 inventory を確認した。

新規は全 first3 の L_ar3_d1/F_ar3_d1、計 6 枝だけ。旧 pml/R_d1/L_d1/F_d1 は再計算せず、実 prior delivery の 6 outer member と 204 native member（203 FILES rows + FILES.json）を byte 検証した。参照は三層 ZIP locator であり、旧 native が新しい同名 path に生成されたとの主張はない。numeric load allowlist は同じ first3 の input.npy だけである。

例外の q/K/atom/stage、batch と物理窓対応、完全 traceback、warning を保存する経路がある。予算超過時に切り詰め・row drop・atom drop せず失敗させ、外部の完全 stream と実 exit/reap 記録を別要件とする設計を保持する。

## 最終封印の照合

- ZIP: pml-ar3-d1-native-source-20261021.zip
- 414,072 bytes
- SHA-256: a4b4f84d1e913a34439a14cacd335d1a24ad11a64d990a9bab45878662c5c469
- SOURCE_MANIFEST SHA-256: 20937857f1bd6422b9ef6d84c5e572f3331540d79c0b8649e4030fc076648494
- source 40 file を全 byte・manifest・ZIP/tree で照合。全 Python を AST parse、全 JSON を厳密 parse。新 top-level module 最大 361 行、すべて 400 行以下。
- 機械可読結果: pml-ar3-d1-native-independent-static-review-20261021.json

## 残る未確認範囲

候補/vendor import、test、help、smoke、数値 probe、人工信号、NPY decode、配列演算、likelihood、DP、D1、PML、品質計算は行っていない。Cloud/Git/upload/install も行っていない。したがって pinned runtime での実完走、IEEE 誤差、実 RSS・時間、合成音、品質、外部の実 exit/reap、実 Library 保存は未確認である。

この静的合格は、F0/VUV/noise posterior の校正、品質改善、独立 validation、全 120 件完了、PML からの採用変更を証明しない。実 source 保存と別途の exact-source launch 判断は親の担当範囲として残る。
