# 保存posterior解析の親側静的確認

2026-10-19。数式と保存schemaの読取りのみ。推定・解析実行・試験なし。

- 同じ保存logBFから一様Hz/localとlog-Hz感度をlogsumexpで再計算し、時間filterは再実行しない。
- 領域oddsは同一local/base watershedの領域に固定し、priorで重み付けした尤度和を使う。平均logBFとの差で置換していない。
- H0を含めた正規化と保存posteriorの正logセル更新式を照合し、零支持・underflowを別記する。
- energy floorを含む欠測のNaNとvalidの有限値を区別し、未処理を埋めない。
- 録音内の有効frame平均と録音等重み平均の分母を残す。5録音のavailable平均を5録音完了と取り違えない。
- 凍結package SHA、入力SHA、receipt ID、frame数、固定gridと時間支持、chunk SHA/相対パスを確認する。
- rho=E/(N varSpeech)、cod=fit*rho/(1+rho)は代表候補の保存値だけを照合し、全grid Jを逆算したとはしない。
- 公開用rendererへ渡す配列はF0周辺質量であり、私有の全jointを直接公開しない。

初回Cloud解析は NumPy bool のJSON変換漏れにより保存段階で停止。cleanのNumPy scalar対象へnp.bool_だけを追加したv2で、同じ実測結果を別出力へ再解析する。数式やF0推定は変更せず、旧失敗出力・ログを保持する。構文ASTは更新後も確認した。結果の数値整合と図の視認性は、この静的記録では未確認。
