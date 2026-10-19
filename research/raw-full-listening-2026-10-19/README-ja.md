# RAW_FULL / PML：固定5録音の短い比較音声

最終HTMLへ展開する前の保存物です。既存の固定5録音について、原音5本とPML / RAW_FULL × 音高0・−3・+3 × 2 seedの60本、計65 WAV・30比較群を収録しています。65の独立録音ではありません。帰属HTMLと変換manifest・completionを含め全68ファイルです。品質優越や採用判断を示しません。

既存NPYの先頭から最大5秒を、16 kHz・mono PCM16へ `rint(x * 32768)`（ties-to-even）で変換しました。範囲検査を行い、gain変更・normalize・clip・dither・resample・整列はしていません。最大絶対量子化誤差は `1.52587890625e-05 FS`。再合成・品質再計測はありません。

- ZIP：7,479,864 bytes
- ZIP SHA256：`0faf765e5de75252275be5ec7cb172e4672d6a9d8271b8d789e1ba1b256fe447`
- `clip-completion.json` SHA256：`8393f3eb6955049357a372d05e5bf785fb09ec0438af3134ab984912d6c01d48`

`audio-credits.html` に帰属、`clip-manifest.json` に元NPYと切出し・量子化後の識別子、`clip-completion.json` に67 memberのbytes・SHAを記録しています。元NPY、private audit、モデルは含みません。最終品質レポートとのjoin・renderer manifest・Pages登録は別工程です。
