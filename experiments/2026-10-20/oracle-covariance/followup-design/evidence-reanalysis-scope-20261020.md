# 保存 oracle 残差の予測混合解析：実施範囲案

2026-10-20 UTC。親側の工程・表示契約案。数理レビューと求積計画の確定前であり、実装・実行・採用は未実施。

## 問いと境界

既存 W/A/V/S/J の五つの共分散 family について、train のみから構造の重みを求め、独立 test の raw 残差に proper な予測分布を出す。候補の最高 test score を事後選択する方法とは異なる。既存 oracle 結果を見て設計した記述的再解析であり、独立な確認実験ではない。

既知 q、既知 phase、H=I、平均推定なし、固定 500 train/test pair、各 record 4096 samples、64 cycles を保持する。元の 1000 残差、2500 MLE・score、初回失敗と回収記録は変更しない。再生成、新しい truth、追加 family、parameter の truth による調整、聴取評価を行わない。自然音声、発声の原因確率、VUV calibration、音質改善、新 base 採用を主張しない。PML が現在の base、RAW_FULL の PR67 は Draft のまま。

## 推論の参照仕様候補

共通総分散 E と shape を用いる。共通 dE/E は improper な reference measure と明記し、raw marginal density が proper であるとは言わない。train 方向の proper evidence と等しい比をモデル重みの根拠とする。train posterior の propriety を確認した上で、raw test の proper posterior predictive を計算する。

model prior は五候補各 1/5。shape prior は A: a∈[−.8,.8] の一様、V: 半径 1.5 円板の面積一様、S/J: α∈[0,1) の一様。これらは参照測度であり唯一の無情報 prior でも生理学的頻度でもない。test を見て prior を調整しない。

train と test は同じ parameter を共有し、初期状態と残差は独立。joint covariance は C⊕C とし、AR を record 境界で接続しない。N 対 2N の Γ・π 定数を保持する。BMA は log-sum-exp で予測密度を混合し、log score の加重平均とはしない。

## 保存と表示

各 pair について、全五モデルの train log evidence（共通因子を何を除いたか明記）、正規化 weight、entropy、五つの raw posterior predictive log density、BMA raw log density、既存五つの MLE raw score を保存する。単位は nats/record を正本、表示は必要に応じ 64 で除した nats/cycle。joint evidence が 128 cycles でも、評価対象 test は 64 cycles である。

主比較は BMA と各五つの既存 plug-in 予測の paired score 差。五 truth ごとに 100 pair の分布・平均・成功分母を示す。test を見た最大 score は実用可能な比較予測器ではないため主 baseline にしない。W の旧 73 件を新しい train-only 選択の改善率へ変換しない。重みを閾値で hard classification へ変換しない。posterior shape の quantile は今回の最小解析には必須としない。

CI を計算する場合は独立 pair ごとの paired bootstrap 10000 回、percentile 法（2.5% と 97.5%、NumPy linear quantile）、pointwise 95% と明示する。乱数は root 20261020 の新 namespace 2 とし、旧 namespace 0/1 と分離する。truth と comparator ごとに固定 stream を使う。多重比較を調整した優位性、同等性、採用判定は行わない。

一つでも必要な積分が診断 gate を通らなければ、その pair の五モデル BMA は未確定とする。通ったモデルだけで重みを再正規化しない。既存 MLE score と各モデルの成功した派生結果は保存し、失敗を欠測として明示する。numerical error estimate を certified bound と呼ばない。欠測のある truth で成功 subset のみの平均・CI を示す場合は、計算成功条件付きの記述と明記し、元の 100 pair 全体の平均・CI は未確定とする。

## 計算工程

1. 元入力 hash と保存 score の来歴を照合する。
2. 読み取り専用で sufficient statistics を算出する。S/J の直交 energy は大きい energy 同士の差ではなく直交残差から直接求める。実方向 norm を保存する。
3. 数理式、全 shape 支持、prior の Jacobian、失敗条件、定数、ログ、resource limit を実行前に凍結する。静的レビューが未完なら実行しない。
4. 科学的な integration refinement と全支持・tail の診断を実施する。新しい unit test / smoke / regression suite は作成しない。
5. Cloud の 1 worker、BLAS 1 thread、最大 30 分、1 GiB、128 MiB 派生成果物を候補予算とする。実装前の見通しに基づく予算で、完走保証ではない。低トークンで固定処理に限定する。
6. 結果は別の日本語 HTML と研究記録にし、既存レポートを上書きしない。未採用の実装は Git へ入れない。公開前に実際の図・相対リンク・manifest・CI を確認する。

本書だけでは実行可能な求積契約は完成していない。独立数理レビューと求積計画で残る条件を解決してから版を凍結する。
