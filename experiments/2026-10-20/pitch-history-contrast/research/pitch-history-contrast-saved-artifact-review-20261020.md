# 固定100履歴対比・保存数値成果物の独立監査

## 判定

**保存値・出典・summary 整合の監査通過。不整合0。** 全100 canonical、1800 CSVデータ行、72 summary群を確認した。採用は外側実行証跡レビューの通過を別条件とする。今回の監査は JSON/hash、保存十進文字列の Decimal 比較、整数計数のみ。減算を再実行せず、候補 import/実行/tests、BF/LSE/exp/log/closure を行っていない。

対象: `pitch-history-contrast-results-review-20261020/package`。原 stage2 は `pitch-stage2-results-review-20261020/package`、固定 source/input は `pitch-history-contrast-source-review-v1-20261020/package`。

## 出典・構造

- 全100 pair metadata は承認 PAIRS と完全一致し、固定順、H50/C50、main97/padding3を保持。
- 全両側 frame pointer の archive/member/member SHA/line を原 stage2 に照合。元 frame SHA は `b5b5199bb71001106c9d65bc9c8637c4c2ce81a98ec1a0f03b7473ac5c2f57a6`。condition/frame/index、観測 hash、support class、full20、missing_keys も一致。
- 全3 prior の original_D[S/L/E]、original_g[3方向]、support_masks は指された原 frame と完全一致。支持・タグ一致 bool も保存値から照合。prior の元 input_pointers はこの原 frame pointer を通して回復できる。canonical に独立 prior pointer の複写はないため、その存在を誤認しない。
- X方向3、I方向3の集合、finite/undefined/missing の要求条件、reason、非適用 source_fields を全件確認。有限タグの十進値は全て finite。欠測は0。A の infinity を finite zero にしていない。
- ARTIFACT-MANIFEST の列挙ファイル bytes/SHA は全一致。provenance の SOURCE-MANIFEST、INPUT-MANIFEST、CONTRACT、PAIRS は承認 v1 と byte 同一。
- CSV 全1800行は canonical の対応 field と文字列一致。summary の全72群について3 kind 件数、有限の負/零/正件数、min/max、同値の全 pair_id を canonical から比較・整数計数して照合。finite 0件の extrema は null。旧 Counter の全件数と completed_pairs=100 も一致。

## 保存結果の限定的な読み取り

- H static は main49、padding1とも X/I 全6値が有限zero。
- C static/B は main48、padding2とも X/I 全6値が有限zero。
- C A は main48中44有限zero、4 undefined、padding2は2有限zero。undefined をzeroや有限分母へ加えていない。
- H A は main49全件、padding1全件の全X/Iが undefined。有限符号件数は全0、min/max はnull。「履歴差が0」とは解釈できない。

### H49 B の保存 range と符号

以下は保存値の表示上の短縮であり、新たな差の計算ではない。厳密な全文字列・全極値 ID は併存 audit JSON に保存。

| quantity | 保存 min〜max（概略） | 負/零/正 | min pair_id |
|---|---|---|---|
| X[S] | −1526.55477952138525〜0 | 8/41/0 | 0 |
| X[L] | −1526.55477952138525〜0 | 8/41/0 | 0 |
| X[E] | −1526.55478041535748〜0 | 8/41/0 | 0 |
| I[L−S] | −4.6191904161e−16〜8.3481445402e−16 | 4/41/4 | 0 |
| I[E−L] | −7.84744264752e−5〜0 | 8/41/0 | 3 |
| I[E−S] | −7.84744264745e−5〜0 | 8/41/0 | 3 |

X三値と I[E−L/E−S] の最大zeroの全IDは8..48。I[L−S] の最大IDは1。pair0はframe53、pair3はframe56。これは同一保存観測・凍結旧priorにおける条件差と保存within-frame差の条件間差であり、品質改善や単一履歴機構の因果効果を示さない。

## 留保

今回確認したのは保存結果の出典・タグ・記述要約の整合であり、X/I が元値の正しい減算であることを再計算して検証していない。実減算の定義は承認 source の静的レビューに依存する。元80桁値の真誤差や符号保証へ昇格せず noncertified を維持する。Cの保存zeroは選択候補・保存量の整合に限り、全gridや一般的な未来漏洩不存在を証明しない。人工選択系列、重複窓・共有雑音の非独立性も維持し、CI/p値・音質・採用改善を主張しない。

機械可読監査記録: `/workspace/shared/pitch-history-contrast-saved-artifact-audit-20261020.json`。
