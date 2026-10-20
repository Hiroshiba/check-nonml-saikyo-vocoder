# 周期的な残差の原因をどこまで区別できるか

PMLを現在のbaseとして維持します。これは既知の人工波形 q・位相・H=I を与えた5観測モデル（W/A/V/S/J）の有限標本研究です。自然音声のボコーダー品質・全120録音の品質比較や生理原因の同定を示すものではありません。

[結果HTML](results/run-002/index.html)に保存スコア、4図、5人工短音声、科学条件と実行履歴をまとめています。[全120録音の既存比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html)とは別の研究です。

## 実行結果と限界

各真値100対、計500対・2500スコア。初回はVの388推定が独立KKT条件を満たさず失敗し、2112件のみ成功しました。初回の条件付き集計は変更せず保存しています。独立レビュー後の回復v2では保存入力・初期値から388件だけを回復し、既存成功2112件を保持しました。回復は全件Newton 1ステップ、最終KKT最大2.368348580689925e-14です。初回・回復の時刻、ソースmanifest SHA、所要時間は[provenance](results/run-002/provenance.json)に残しています。

構造ありのA/V/S/J真値では各100対すべて対応モデルが勝ちましたが、有限標本・固定条件での結果です。W真値では単独勝者W3/A27/V23/S9/J14、同率24。Wの平均スコアの優位と対ごとの選択は別で、柔軟なモデルの有限標本選択や密度の適合を因果・発声生理の識別に読み替えません。

5短音声は保存済みpair 0の人工test信号を共通gain 0.1、PCM16で提示した各0.256秒の例です。生成・変換の来歴は[audio-provenance](results/run-002/audio-provenance.json)に保持します。自然音声や新しい品質評価ではありません。

## 研究文書と時系列

次の7文書は受領した原bytesを維持しています。文書内の「未実行」はその文書作成時点の記録であり、上記の初回・回復完了によって履歴を書き換えていません。位相不確実性と完全混合Kalmanの扱いは理論上の設計で、今回の実装・測定対象ではありません。

- [cyclic-noise-identification-design-ja.md](research/cyclic-noise-identification-design-ja.md)
- [cyclic-noise-state-likelihood-ja.md](research/cyclic-noise-state-likelihood-ja.md)
- [phase-uncertainty-control-ja.md](research/phase-uncertainty-control-ja.md)
- [interpretation-plan-ja.md](research/interpretation-plan-ja.md)
- [independent-source-review-ja.md](research/independent-source-review-ja.md)
- [recovery-math-review-ja.md](research/recovery-math-review-ja.md)
- [recovery-source-review-ja.md](research/recovery-source-review-ja.md)

[文書manifest](research/DOCUMENT-MANIFEST.json)は全7件のサイズ・SHA256を保持します。受領ZIPは50,431 bytes、SHA256 `55d4fd23139dcf990b2273b16fa6ec67b624d8795dfb78a8e2cb6f20ad3a9f7b`。初版の結果20ファイルを保持して掲載した後、親側の図レビューに基づき4図とHTMLの表示だけを修正しました。保存CSV/JSON/WAVと科学契約のbytesは不変です。図の旧SHA・新SHA・描画日時・変更理由は[表示修正の来歴](results/run-002/rendering-provenance.json)に記録し、manifestを更新しています。候補ソース・NPYは掲載しません。

次は親側で4図と説明の品質確認を行い、承認後に公開へ進みます。このDraftでは追加計測・再推定・テスト・サイト生成予行を行っていません。
