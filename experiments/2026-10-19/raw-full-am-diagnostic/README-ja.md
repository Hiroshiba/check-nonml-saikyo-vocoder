# 高域電力のAM観測：議論用の軽量資料

科学的run完了後の保存値だけから作った日本語HTMLです。index.htmlを開くと、PML対RAW_FULLの全窓・参考枠・非交差の差、比と絶対量、周期保留の誤差利益、全固定条件、実際の保存包絡図を確認できます。図と数値はローカルでも表示でき、音声の再生だけ既存公開URLへ接続します。公開・Git登録はこの資料生成では行っていません。

## 含むもの
- index.html：全180群と保留集計への入口
- all-groups.csv：全180群の保存集計、原音・PML・RAW_FULL、符号付き対差
- holdout-groups.csv / holdout-per-window.csv：保存済み予測の群・窓別集計
- summary.json：保存集計の全指標、欠測理由、支持・相関、固定感度比較。rawパスと重複結論文を除いた公開用コピー
- highband-power-hp1500.png / highband-power-hp3000.png：既存全波形の保存高域電力を描いた図
- completion-receipt.json：実際の科学的完了原本。列挙されたrawファイルは本資料に非同梱
- source-verification.json：raw保存成果の既存SHA照合記録
- provenance.json / figure-provenance.json / audio-manifest.json / artifact-manifest.json：出典とファイル同一性

## 読み方
全窓の基本条件ではsource追加比の対差は平均・中央値とも8群すべて正。参考枠交差では7/8群で負です。局所結果を全体へ一般化しません。0半音の2時計量は識別不能です。保留予測の負の利益は誤差増加を意味します。重複窓・foldは独立標本ではなく、品質順位・p値・母集団信頼区間はありません。小さい比や予測利益からAM不存在を結論しません。

## 範囲
35,505観測行、304,473保留記録の科学的観測は2026-10-19 10:43:44 UTC完了。約744 MiBのraw成果は別途非公開で保持し、本資料へ全量掲載していません。HTML作成時に波形処理・F0推定・合成・回帰・SVD・新規科学測定・テスト・ブラウザ・Git作業を行っていません。

音声はLibriSpeech © 2014 Vassil Panayotovほか、CC BY 4.0。完全な帰属と既存加工説明はHTMLの出典欄を参照してください。
