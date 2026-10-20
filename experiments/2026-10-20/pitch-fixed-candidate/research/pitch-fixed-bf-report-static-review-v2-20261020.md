# 固定二候補BF報告v2：最終限定差分レビュー

2026-10-20 UTC。結論：**公開用静的レビュー通過。前回の停止線は解消、新blockerなし。** builder実行・描画・live確認は未実施で、マージ後の別工程とする。

v0 public95filesから、変更はindex.html/listing.jsonだけ、追加はartifact-manifest.jsonだけ。他93filesは全件byte同一。したがって前回確認した87原bytes/gzip対応、表12行・行列9組・SVG3レンジ・ローカルリンクの数値部分は不変。

- publicは自己manifest含め96files。manifestのfilesはname/bytes/sha256のlist、自己除外95entriesで、public実file集合と完全一致。
- 各entryの実bytes/SHA全件一致、許可suffix `.html/.json/.json.gz/.svg/.wav/.md/.csv/.png/.css` に適合、全file10MiB未満。科学source/ZIPの新規混入なし。
- manifest15664bytes、SHA `2868c71bc7c6e24bd2c18b3c99f9333e6df62e5f33b45998c8d31df6281b35c2` は親指定値一致。
- 「進行中の500組BMA」を削除し、既存BMA報告とは別検証と記載。A/B正負件数は有限な符号行列内に限定した文言へ修正。
- publication_pendingを削除し、created_at=`2026-10-20T10:13:09.662393+00:00`。測定/初回公開時刻ではなく一覧作成時刻という意味を明記。footerの将来公開状態断定も削除。

候補source実行/import/tests、新BF/LSE/統計・科学再計算、builder実行なし。source・原データの変更や数値再評価を伴わない限定差分として確認した。
