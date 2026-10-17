# 全120件の保存済み費用観測

主評価の候補・PML・WORLDについて、固定120件の全終端記録から9438個の保存済み数値を集約した。新しい速度測定ではない。`full120-saved-cost-summary.json` に79種類の費用・容量集計を保存した。

生成記録の範囲は全120件に到達したが、候補の純粋な全解析時間、観測負荷を除いた復号時間、正式経路の独立した編集時間は未測定のままである。このため機械可読データの partial 状態は維持し、速度順位や解析＋復号の合算値を出さない。

## 代表的なRTF

各入力全抜粋の長さを分母にした録音別RTFの中央値。1未満は当該区間の経過時間が音声長より短いことを表す。候補1スレッドは作業記録の報告値で、本集約では未照合。PML/WORLDは各記録の契約で2スレッドを確認した。手法間の同一条件ベンチマークではない。

| 手法 | 条件 | 観測区間 | 支持数 | RTF中央値 |
|---|---|---|---:|---:|
| candidate | case | air_seconds | 120/120 | 5.59651 |
| candidate | case | final_fit_seconds | 120/120 | 0.61566 |
| candidate | native | render_seconds_including_profile | 117/120 | 0.22309 |
| candidate | pitch_minus3 | render_seconds_including_profile | 117/120 | 0.24757 |
| candidate | pitch_plus3 | render_seconds_including_profile | 115/120 | 0.21079 |
| pml | case | analysis_wall_seconds | 120/120 | 0.62006 |
| pml | native | decode_wall_seconds | 120/120 | 0.09931 |
| pml | pitch_minus3 | decode_wall_seconds | 120/120 | 0.08370 |
| pml | pitch_plus3 | decode_wall_seconds | 120/120 | 0.11258 |
| world_harvest | case | analysis_wall_seconds | 120/120 | 0.20713 |
| world_harvest | native | decode_wall_seconds | 120/120 | 0.01282 |

候補のair_secondsとfinal_fit_secondsは解析の部分観測であり、別途初期F0取得・I/Oなどがある。候補の復号値はprofile負荷を含む。失敗を0秒に補完せず、支持数を条件ごとに示した。編集・I/O・特徴量容量などの残りの観測はJSONを参照。

## 出典と限界

候補の終端chunk→case→保存元のSHA結合、参照の終端receipt→summary/contractおよび入力SHAを確認した。候補の元JSONがZIP内にあるものは、既存のlossless receiptに結合されたscalar投影を使用した。今回の費用集約でZIP内の全元JSONを再読み込みしたとは主張しない。

- 全9438観測を含む派生データ SHA-256: `d4e074921593f511b275382730c10f536d6ed0a9275cefbc4d65af4ab3368eb2`
- 集約プログラム SHA-256: `ddb9f3e24462a60c516c6071af89b89835b608e782787b61b33f959e4839c9e3`

全長音声、完全特徴量、候補実装、私的な保存場所はこの公開集計に含まない。
