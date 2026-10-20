# 固定二候補レポート：公開ブラウザー確認

確認時刻：2026-10-20 10:34–10:36 UTC。
環境：dotのクラウドChrome。PC幅1173pxのみ。親からPages run39408455442成功、deploy完了10:33:35Zの確認を受領してから実施。

対象：
- https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/pitch-fixed-candidate-2026-10-20/index.html
- https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/pitch-fixed-candidate-2026-10-20/audit.html
- https://hiroshiba.github.io/check-nonml-saikyo-vocoder/

結論：確認したPC表示に重大な崩れ・欠落・重なりなし。

本文：
- 大見出し、日本語本文、数式D = G(f*) − G(2f*)、指数表記が読みやすく表示。
- 冒頭にPML維持、品質/MOS/採用未評価、固定二候補のみ、積分参照は非保証の限定がある。
- 冒頭のPML既存評価・自然120比較・標準8方式比較の3リンクは全て期待する公開ページに到達。
- 309窓・6180参照・重複除外4180件の区別を明記。4180件を独立音声標本とは扱わない。
- SVGのstatic/A/Bの3レンジは各線・端点・ラベル・負軸・単位が明瞭。最小最大でありCIではない旨と、A有限104/static・B各309窓の母数が直下にある。
- static/A/Bの3行列群、それぞれS→L/L→E/S→Eの3表が横並びで収まり、行列ラベル・件数・符号反転0件に重なりなし。
- Aの205窓は非有限Dで、差はundefined、欠測でも差0でもないと明記。+∞141/−∞64が各遷移で表示。
- CSV/JSONとauditへの導線を確認。データはダウンロードしていない。

audit：
- 「保存原本と終了証拠」ページは正常表示。報告への戻りリンク、owner0/1/2、sign、stage2、evidence、pinsの見出し別リンク群が存在。
- gzip可逆、journal/canonicalは展開後JSON Lines、ログ/stdout/stderrは元テキストという区別を冒頭で明示。
- 親が96公開filesを別途照合するため、全ファイルのダウンロードやbytes監査は重複実施していない。

ルート一覧：
- 最新「固定二候補への積分近似の影響」が先頭。対象index.htmlへリンク。
- 案内作成2026年10月20日19:24（日本時間）、測定時刻とは別と表示。
- 次はscalar1080報告。最新カードの説明に4180/6180/309とA205非有限の限定、音質/全候補探索/exact再追跡ではない旨がある。
- 本件は初回公開日時欄ではなく案内作成日時欄で表示。既存一覧説明は公開日時未登録項目に作成日時を使うことを明示しており、この表示と矛盾しない。

範囲と制限：PC目視のみ。狭幅・mobile未確認。viewport変更やハックなし。編集、科学処理、数値再計算、tests、build、smokeなし。スクリーンショットはブラウザー出力で確認、ローカル画像保存なし。
