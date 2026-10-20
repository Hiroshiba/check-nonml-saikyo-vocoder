# 既存F0 kernelのlog-g Laplace近似差（2026-10-20）

[日本語報告](results/complete-001/index.html)と[配布原本の説明](results/complete-001/README-ja.md)を保存しました。固定1080点・108r・欠測0、N400・δ3・K1..10のscalar診断です。現baseはPMLを維持し、自然音声の品質・MOS・採用判断とは区別します。既存の自然120録音・PML正式評価・標準8方式への比較リンクは報告冒頭にあります。

保存されたΔ_A80=L80−A80のmin/maxと図を原bytesで保持しています。80桁参照は保証付き真誤差ではなく、固定点での符号を連続全域へ一般化しません。旧548成功と回復532、過去の失敗・終了証拠を保持しています。

Library `libfile_010e75be67408191aa9edcfc33fb99c5` v0のpublic40ファイルだけを保存。元ZIPは3537329 bytes、SHA256 `e1bc1214f52246dd993e5ffaff465acf01ffdca50e901656a3ac2ae7f4d96083`。`canonical-rows.json.gz`の解凍内容はJSON Linesで、意図的な配布名です。source・scripts・preserved・原本ZIPはGitに含めません。

Pages登録先は `research/pitch-exact-scalar-2026-10-20/index.html`。この保存工程では科学計算・tests・smoke・ビルド予行を行っていません。PRのレビュー・マージと配信確認は親の工程です。
