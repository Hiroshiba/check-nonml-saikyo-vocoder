# F0の履歴と数値表現：固定3入力の研究記録

公開準備UTC：2026-10-20T04:15:12.887016+00:00。現在baseはPML（pml-lowband-fwcep60-v1）を維持。

[統合レポート](results/run-001/index.html) / [Pages](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/pitch-history-log-2026-10-20/) / [出典](results/run-001/audio-credits.html)

## 比較範囲と完了した実行

通常確率で状態を保持する元版A、保存帳簿分解、同一実数モデルの完全log領域版Bを同じテーマにまとめる。正弦波と固定乱数のみの3入力、各103窓。録音・個人情報は含まない。元科学値・音声・図はbyte不変で、公開登録用manifest・出典・準備時刻だけを別追加した。

Aは2026-10-19 23:46:22.133743–23:46:27.873159 UTC、exit0、計測内wall5.134498487秒、RSS65,921,024bytes、出力51,042,182bytes。Bは2026-10-20 04:01:24.420167–04:01:43.982846 UTC、exit0、wall19.562750834秒、RSS69,136,384bytes、出力66,335,086bytes。外側プロセスの開始/終了は[来歴](research/execution-provenance.json)に別記する。

309窓すべてjoint MAPはA/Bで不変。U-U/E-Uの共通後半49窓は観測とlogBFがbyte一致し、両版とも53–55でMAPが異なり、56–101で一致。Bの表示jointのbyte一致は60から、log jointは69から。E-U frame55のf*全K質量はAの4.603951912981988e-10からBの0.00030499474744655224へ変わるがMAPは195.3125Hz/K2のまま。raw半L1は厳密に正規化された分布のTVとは限らず、clip/再正規化していない。

同じMAPは同じ分布を意味しない。丸め・演算順の影響を含みunderflow単独原因を断定しない。49窓は依存窓で独立49反復ではない。E-Eのclean最小周期195.3125Hzを尊重し、潜在97.65625Hzへの回復を正解としない。校正・自然音声の真F0/VUV・音質・採用は評価していない。PMLおよび既存方式の品質比較は未実施で、冒頭に既公開PSHF/PML/RAW_FULLの機構診断・比較音声への案内を置く。

## 文書の時点と来歴

研究文書の「未実行」は執筆時点の記録としてそのまま保持した。後続のAとBは上記時刻にそれぞれ一度完了し、保存値だけの帳簿分解と報告作成を行った。保留案のreset/heavy-tail/温度・窓変更は実行していない。文書中のローカルパスは当時の実行契約上の位置であり、公開環境から取得できるリンクではない。

- [3入力提案](research/history-proposal-ja.md) / [当初実行契約](research/history-execution-contract-ja.md)
- [識別設計・仮想5役2往復](research/DESIGN-ja.md)
- [回復機構の文献レビュー](research/recovery-methods-review-ja.md)
- [重複窓の校正問題](research/overlapping-window-review-ja.md)
- [独立静的レビュー](research/log-arithmetic-static-review-ja.md)
- [log実行契約](research/log-execution-contract-ja.md)
- [ソースSHA・receipt・実行来歴](research/execution-provenance.json)
- [A結果](research/history-result.json) / [B結果](research/log-execution-result.json) / [B集計](research/log-summary.json)
- [入力条件・窓一致](research/history-inputs.json) / [人工音来歴](research/audio-provenance.json)

提供された3つの研究文書は内容を保持し、通信上のHTML entity（&lt;、&gt;）のみ文字に戻した。文書の一次資料確認は各担当の記録であり、本保存工程で追試したものではない。

## 保存・公開範囲

未採用推定器の実装、full joint配列、privateログ、他の自然音声はGitへ追加しない。研究文書はGitで、列挙したHTML/CSV/JSON/人工WAVは既存Pages経路で保存する。研究ソースそのものは非掲載だがSHAを保持する。USER_INSTRUCTIONS.md、base、PR67には変更なし。Libraryの承認を公開許可に読み替えず、別途指示されたリポジトリ保存・公開工程として扱う。

PR段階は差分・manifest・リンクの静的確認とキャッシュ付き解析のみ。サイト予行・tests/smoke・再計測は行わず、mainへのマージ後に既存Pagesの配信を確認する。
