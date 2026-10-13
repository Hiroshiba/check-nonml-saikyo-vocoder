# 既存6方式の追加と音声付きHTMLの保存確認

2026-10-13（日本時間）。この文書はAIによる実装・確認記録であり、独立した第三者の査読ではない。新しい音声生成方式の仮説や品質採用を提案した記録ではない。

## 今回の変更

標準はWORLDとFACodec v1、HiFi-Glot、GOLF-ff、SiFi-GAN、LLSM2 Layer 0、MagPhaseの7方式。DACは準備・実行の両方で `--include-dac` を明示した場合のみ。閉じたPR #26の固定実装を引き継ぎ、欠けていた結果HTMLのGit保存・実験一覧登録を補った。指示変更はPR #28へ分離し、PR #29ではUSER_INSTRUCTIONS.md・BASELINE.json・HNM本体・過去の公開済み結果を変更しない。

## 結果の所在と出典

[音声付きHTML](../../experiments/2026-10-12/reference-methods/results/run-001/index.html)、[全測定値](../../experiments/2026-10-12/reference-methods/results/run-001/results.json)、[復元元と照合ハッシュ](../../experiments/2026-10-12/reference-methods/results/run-001/publication.json)。音声はJSONにも保存し、原音全体・全長生成波形・学習済み重みを公開ディレクトリへ入れていない。

復元元は[前回のActions実行38243678340](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/actions/runs/38243678340)の成果物11743843750。元の実装headは `3d69b1f6e6fe19554083b7fb4ae72f30636a2b63`、測定時のcheckoutは元結果のexecution.jsonに残る。ZIPのSHA-256は `26331062196fb72cbc60010ed0f6ebd52994e1476ad496be11d477f975c4cb68`。

HTML・results.json・summary.json・audio_samples.json・条件JSONを変更せず保存した。元の生成日時は2026-10-12T11:39:13.503994+00:00（日本時間20:39）であり、復元日時と別に保持した。復元によって新しい推論・MOS・反復速度試験を行ったとは数えない。

## 復元時に確認したこと

2音声×標準7方式の14行が再合成・評価完了、失敗0であることを元JSONから確認した。14本の全長npyを記録されたSHA-256と照合し、サンプル数一致・有限値・非無音を確認した。16個の短い音声例（原音2＋再合成14）を実際に復号し、標本化周波数・長さ・モノラルを照合した。結果HTMLのプレーヤーは代表1音声の原音＋7方式の8個で、両音声の例はaudio_samples.jsonに残る。

復元処理の初回は、浮動小数点WAVをPCM専用のPython標準waveで読んだため `unknown format: 3` で停止した。保存音声を加工して通すのではなく、検査側をsoundfileの復号へ修正した。同じZIPの照合・復号・保存をやり直し、[復元commit](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/commit/1bdf0edf42c339473363edc783bae2eb6d409ee1)へ保存した。Ruffとサイト生成が成功し、7グループ・162件の内部リンクを確認した。

恒久的には `python -m vocoderbench.references.publish` で、保存済み結果を実験フォルダへコピー・登録できるようにした。過去runの上書き・同じ測定結果の重複登録・選択方式と記録の不一致は拒否する。失敗が記録された比較は失敗を隠さず保存する。通常のCIにも、学習済みモデルによる再合成からHTML保存・一覧生成までを追加した。復元用の一時ワークフローは最終差分から削除する。

## 解釈の限界

MOSは全方式とも未測定のままで、0点や合格へ置き換えていない。出力長の不一致も残し、共通先頭区間の補助指標と全長を混同しない。RTFはこの2音声の単回処理であり、前回別実験のウォームアップ付き5反復測定とは別物である。

このPRは比較対象と保存・公開経路の追加であり、固定120音声の品質比較、MOS校正、48 kHz高域への対応、表現の近さ・制御性、下流学習の確認ではない。既存方式への品質採用もHNMの再採用も行っていない。正式比較は別の新規runとして記録する。

PRだけでは本番Pagesは更新されない。mainへのマージ後、公開ワークフローが成功すると保存した実験のHTML・音声・測定JSONが一覧に載る。今回の2件は依頼どおりPR提出にとどめ、セルフマージしない。
