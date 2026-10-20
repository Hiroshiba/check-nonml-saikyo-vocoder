# 履歴対比 HTML v0・保存値限定静的監査

## 結論

**既知の「次の検討」文言の訂正を条件に、他の blocking 不整合はない。** 最終節は prior/支持消失の整理を今後の作業としているが、既報棚卸しで閉じた最新状態へ変更予定と親から通知されている。その更新後の bytes/manifest は別途確認が必要。

対象: `pitch-history-contrast-report-review-20261020/package/public`。照合先は監査済み `pitch-history-contrast-results-review-20261020/package`。HTML・JSON・CSV・gzip展開bytes・hashを読み、表示と保存値を比較した。候補実行/import、tests/build、BF/減算/LSE/exp/log/closure の再計算はしていない。独自の読取監査は文字列照合・hash・整数件数に限った。

## 完全性と出典

- public は35ファイル。artifact-manifest.json は自己を除く34ファイルを過不足なく列挙し、全bytes/SHA一致。
- byte-preservation.json の22対応は全て原結果に一致。非gzipは bytes 同一、gzipは展開後 bytes 同一。元bytes数・元SHA・保存SHAも一致。
- 公開集合に .py や .zip はない。元 manifest 内で非公開実装名が出現しても、実装本体の公開とは混同しない。
- contrasts.json.gz の内容は100行のJSON Linesであり、単一JSON配列ではない。本文のリンク名と audit.html はJSON Linesと明示する。stdout/stderr の .json.gz も audit.html で「原テキスト」と明示し、JSONであるとは称さない。stderr の実内容は展開後0 bytes。さらに「stderrは空」と表示すれば親切だが、現説明は虚偽ではなく blocker ではない。
- 原結果 manifest は原ファイル名と原bytesの証跡、公開manifestは配布時のファイル名と圧縮bytesの証跡として区別され、対応表で接続できる。

## 表・表示と全分母

- data-main 6行と data-range 6行の計12行が display-source-map の cells と完全一致。別に固定範囲表2行がある。
- main表の source indices、kind 件数、X[S] とI[E−L] の負/零/正を原 summary へ照合。H主要49、C主要48を混ぜない。A は H finite0/undefined49、C finite44/undefined4を明示し、0／0／0を有限zero件数の増加と誤読させない説明がある。
- display-ranges.csv の6行の raw min/max は原summaryの文字列と完全一致し、符号件数も一致。HTMLの表示値は同CSVに一致。保存十進文字列と表示6有効桁を分離し、表示が同じでも原値の同一性を意味しないと説明する。6有効桁の表示は原文字列の桁を目視確認し、再丸め計算は実施していない。
- 全72群のkind件数の整数和は有限1476、undefined324、missing0。本文は1800「値」であって100「組」ではないと明示している。
- H50=53..102、H49=53..101、C50=0..49、C48=2..49、padding H102/C0/C1が契約と一致。padding を主要群へ混入しない。H padding はstatic/B有限zero、A undefined、C padding は全prior有限zeroとの記述が保存結果と一致。
- H static と C の有限 X/I は保存zeroという説明に一致。H B の X負8/zero41、I[E−L]負8/zero41、I[L−S]負4/zero41/正4とrangeは原summaryと整合する。

## 解釈とリンク

- X は保存Dの条件差、Iは保存gの条件差と分け、別丸めのため I を X から再構成しないことを明示。Xの負をD自体の負と混同しない。
- 条件Eと積分評価E、A80と履歴A、刺激U/Eと有声/無声を区別。Aの非有限をBで補修しない。
- 非独立人工系列、原波形再測定なし、非certified、因果単一要因・品質・一般的未来漏洩不存在を主張しない範囲は適切。PML維持を明示し、新音声・MOSなし。
- index/audit の全ローカル href は実在するpublicファイルへ到達。外部既報URLのHTTP稼働・公開到達性は今回の保存ファイル限定監査では未確認。
- 実行時間の同梱一次証拠と、未同梱外側最終stdoutにのみある時刻をauditで分離している。本レビューは実行証跡の再承認ではなく、既監査の限界がHTMLで消えていないことを確認した。

既知文言修正以外に新しい科学値・計画の追加は不要。修正後もraw22ファイルは変更せず、HTML/manifestの変更範囲のみ確認すればよい。
