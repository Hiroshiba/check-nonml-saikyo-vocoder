# 同一観測・旧履歴対比計画：独立批判レビューと最小凍結契約案

2026-10-20。対象は `pitch-matched-observation-history-contrast-plan-20261020.md`。計画と stage2 の schema、最初の原レコードの字段構造だけを読んだ。実減算、exp/log、科学値集計、candidate import/実行/tests は行っていない。

## 1. 判定

**問いと固定対象は妥当。以下の定義・タグ・算術・停止規則を反映すれば実装前契約として凍結可能。** 既存の MAP 履歴一致/不一致を再集計するのではなく、固定旧prior下でのS/L/E変更と条件差の相互作用を読む点に新規性がある。ただし「既存成果に全くない」ことは、Cloud補足の成果範囲との照合を別途完了して確定する。

重大な補正点は、数学上の差の差と、丸め済み保存文字列を主経路で引く量を厳密同一視しないことである。Decimal256はこの違いを消さず、保存値の演算だけを正確にできる。

## 2. 固定集合・同一性・解釈

- H50: E-U minus U-U、frame53..102。主要H49は53..101、padding102は別枠。
- C50: E-U minus E-E、frame0..49。主要C48は2..49、padding0/1は別枠。
- 全100を事前固定し、主要97とpadding3の区分をmetadataで維持する。効果・有限性・符号で除外や追加をしない。
- 20候補の順序は f_index48、148、それぞれK1..10。各条件のreference_idは異なり得るので、その同一性を要求しない。参照先の候補軸、unique_id、K/cod bits、旧S bitsを比較する。
- 同じJ/fit/cod/energyだけでは波形の同一性は証明できない。stage2の observation_sha256 を pinned frames 原字段まで辿り、hashの対象範囲・dtype等の定義も固定する。padding102を完全窓の既検証から外挿しない。
- staticは各条件のframe0保存priorで比較する。frame1以降のinitial帳簿zeroは使わない。CのA/Bはそれぞれ元prior bitsを比較し、AとB同士の同一性は要求しない。Bはlog(A)ではない。
- Hは旧履歴と関連する凍結prior差の対比であり、memory/transition/H0/丸め等の単一要因の因果効果ではない。
- Cは「同じprefix入力・同じ初期状態・同じ処理条件なら、将来ブロックの違いがこのprefixへ影響しない」という限定的negative control。共通scaleの生成条件も固定済みである必要がある。単なる同時点候補一致から全過去状態一致を推論しない。
- C一致は選択20候補と保存量の整合を支持するだけで、全grid・VUV・内部全状態の一致や未来情報漏洩不存在の一般証明ではない。C不一致も漏洩を即断せず、来歴・join・入力・初期状態・処理順を切り分ける警告とする。

原NPZ未添付の留保、元309frameが選択済み人工系列である限界、重複窓・共通雑音による非独立性を維持する。CI/p値/bootstrap・独立反復推論・品質や採用判定は対象外。

## 3. 正とする演算量

条件をa=E-U、b=U-U（H）またはE-E（C）と固定する。三priorは混ぜない。

`d[a,s]` を保存D文字列が表す十進数とする。条件差は

    X[s] := d[a,s] - d[b,s]      (s=S,L,E)

とする。`g[a,t]` を保存differences[t]文字列が表す十進数とし、interactionの正本を

    I[t] := g[a,t] - g[b,t]
    t = L_minus_S, E_minus_L, E_minus_S

とする。この定義は保存schemaの実字段と対応している。

数学的な理想式では I[E_minus_L]=X[E]-X[L] だが、保存Dと保存within-frame差は別々に丸め・文字列化されているため、今回の保存十進値に対して厳密な恒等式とは限らない。主表はIを採用し、Xから再合成した値・closure残差・逆方向は最小契約では計算しない。同様にI[total]=I[numerical]+I[integration]を強制しない。

表示名は「保存十進値の条件差」「保存within-frame差の条件間差」。L→EのI<0はf*/2f*の条件間対比が負側へ動くことを表すだけで、真値の符号保証・改善・因果効果とは言わない。S→Lは旧保存値との数値再現差、L→Eは既存の理想Laplace対exact式の差という来歴を保持する。新しいBF近似誤差を測定したとはしない。

## 4. 数値タグと欠測の優先順位

機械schemaは既存と同じkind/decimal/reason。`not_applicable`は表示語に限り、新しいkindとして作らない。

1. どちらかのframeがfull20_completeでなければ、全prior・全X/Iを `missing`。missing_keysと両原pointerを残す。zero支持のKでも完了規則から免除しない。
2. Xは両元Dがfiniteのときだけ減算する。片方でもmissingならmissing、undefinedならundefined、±infinityなら `undefined/nonfinite_condition_contrast`。元タグ・支持maskを保持する。数学的に拡張実数差を定義できる場合も、この限定診断では有限対比を計算しないという意図的規則である。
3. I[t]には、その方向に必要な両評価のXがfiniteであり、両条件の保存g[t]もfiniteであることを要求する。必要入力がmissingならmissingを優先し、それ以外の非finiteはundefined。理由に不足元字段を記録する。
4. 同じ∞同士を0にせず、Cやstaticでは「支持・元タグ一致」として記録する。Aのzeroを補修せずBへの置換も禁止する。

これにより、元計画の「Xまたはwithin-frame差が非適用ならIも非適用」の適用範囲が明確になる。入力scalarの欠測と、新しい算術障害を混同しない。

## 5. Decimal契約

親提案の **stdlib Decimal、precision=256、ROUND_HALF_EVEN** は採用可能。ただし「256桁なら全入力に必ず十分」とは保証しない。90有効桁の入力でも指数差が大きければ減算の必要桁数は増える。

- finite入力は保存十進文字列から直接、exactにDecimal構築する。floatを経由しない。元文字列は変更しない。
- contextは新規に明示生成して固定する。Emin/Emaxも固定値をsource/contractに明記する。既定の継承に頼らない。
- Inexact **とRoundedの両方** をtrapにする。Roundedだけの発生も拒否する。さらにInvalidOperation、DivisionByZero、Overflow、Underflow、Subnormal、Clamped、FloatOperationをtrapにし、特殊値の混入を拒否する。
- 許可算術は上記X/Iの有限Decimal減算だけ。構文・型・hash・bits・集合・順序・件数・符号・大小の照合は許可する。BF/r/LSE/exp/log、新精度評価、再追跡は禁止。
- 出力Decimalをfloatへ変換せず、contextを伴う再丸め・quantize・normalizeをしない。ゼロの表示規則は固定し、元文字列はpointerで復元可能にする。
- trap、不正finite、入力不整合、予算切れは即全体停止し、原入力pinと完了行・停止理由を保存する。精度自動増加、自動retry、失敗行除外による完了扱いは禁止。

成功時に言えるのは「この固定contextで丸めを発生させず、保存十進値を減算できた」ことであり、元80桁BF・LSE・priorの誤差が消えたことではない。noncertifiedを維持する。

## 6. 最小成果物・予算・完了条件

過剰なJSON/CSV二重全表は不要。canonical JSONLを100pairの固定順、各record内に3priorのX三値・I三値とタグを持つ形にする。入力pointer、原D/gの参照、同一性検査、support_class、missing理由を含める。主要CSVはcanonicalの必要列を転記する一つに絞る。G/K分布の大量複写、KL/TV、逆方向・closure・追加符号反転集計は不要。

主要H49/C48とpadding3を明示し、固定件数・finite/undefined/missing件数だけを基本要約とする。range/符号別IDは必要なら同じ正本からの比較・整数計数に限定し、効果の大きな行だけで結論を作らない。

予算は **一回60秒、数値worker単体128MiB、出力8MiB**。workerは子processを作らず、supervisorは別計測。tree全体のOS保証とは称さない。60秒には停止・保存余裕を含め、算術締切を例えば50秒、残りを停止・保存に予約する値を実装前に固定する。全原データの巨大複写や全journalのメモリ常駐を要求せず、必要memberを逐次読取する。予算に収まることは本机上レビューでは実証していない。

同一性不一致は静かにpairを落とさず、固定台帳に全予定IDと停止/未着手状態を残し、群の意図した解釈を停止する。予期したmissing/undefinedは通常出力、予期しない算術trapはrun failureと分ける。完了条件は全固定100pairの検査と規則どおりのX/Iまたは欠測理由の保存、pin/receiptの整合。数理・入力・sourceレビューと別開始指示後の一回枠に限る。

## 7. 批判的再検討

- 数理視点: 差の差の符号方向は整合。ただし保存差とD再合成の丸め差を区別しない定義は修正が必要。
- 来歴視点: 候補重複は観測hashの代用でなく、元prior bitsとpointerの照合も必要。全gridへの外挿は禁止。
- 因果視点: Cはprefix因果順序の限定対照、Hは凍結prior全体の関連対比であり、いずれも機構別因果推定ではない。
- 数値視点: Decimal256 trap方式は追加の丸めを拒否できる。元保存誤差の証明や精度自動救済には使えない。
- 批評視点: 固定97主要+3padding、欠測を残す台帳、CIなしは妥当。大きな効果の事後抜粋、Cの「漏洩ゼロ証明」、再実行での都合のよい成功取得を禁止する。

以上を反映した契約は、追加測定を伴わず新しい限定的問いを実装可能な形にする。現時点では結果の符号・値・一致を新たに計算していない。
