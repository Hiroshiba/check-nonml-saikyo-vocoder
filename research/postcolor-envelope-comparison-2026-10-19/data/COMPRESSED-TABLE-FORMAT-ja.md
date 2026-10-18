# 全値を保つ圧縮表の形式

大きい詳細表だけをgzip圧縮JSONで配布し、通常の比較表・小さいCSVはそのまま残す。読む際はgzipを展開してUTF-8のJSONを開く。表計算ソフトへ直接CSVとして開くより一工程増えるが、列名・列順・行順・全セルを元の文字列のまま保持する。

- `schema`: `lossless-csv-string-table-v1`。
- `source_csv`: 元CSVのファイル名、bytes、SHA-256、UTF-8。
- `column_order`: 元ヘッダーの全列名を元の順で保持。
- `data_row_count`: ヘッダーを除く全行数。
- `rows`: 行ごとの文字列配列。全要素がJSON文字列であり、数値への変換・丸め・欠測補完はしない。空欄は空文字列。大文字小文字や指数表記もそのまま。
- `csv_dialect`: カンマ区切り、二重引用符、引用符の二重化、必要時のみ引用、CRLF行末。

CSVへ戻す場合、`column_order`を最初の行、次に`rows`をその順で、このCSV方言に従ってUTF-8出力する。今回の3表は、元CSVへの戻し処理でファイルbytesとSHA-256まで完全一致した。圧縮自体はgzip level 9、mtime 0を使用し、時刻依存の出力差を作らない。

| 圧縮表 | 全行数 | 列数 | 元CSV bytes | gzip JSON bytes |
|---|---:|---:|---:|---:|
| all-periodic-knots.json.gz | 62,784 | 17 | 11,119,564 | 2,599,558 |
| all-periodic-paired-knots.json.gz | 47,088 | 14 | 6,947,499 | 1,408,185 |
| all-coverage-regions.json.gz | 648 | 20 | 604,729 | 25,001 |

全値は欠測・非定常フラグ・無介入・負の変化を含めて保持する。観測器の再計算はしていない。元CSVは元分析成果として不変保持し、元のSHAと圧縮表SHAを公開来歴に併記する。
