# 初回3録音：既存PMLは成功、候補L/Fは合成前に失敗

既存PMLは3/3成功、局所選択Lと二段系列選択Fは各0/3で、候補6枝がすべて失敗しました。候補はPMLParametersの構築時に停止し、合成前のため候補音声は未生成です。聴き比べ音声・MOS・品質順位はありません。全120録音の評価と標準比較器による比較も未実施です。

## raw正値は範囲内だが、解析後の20フレームが50 Hz以下だった

[保存結果の診断](pml-native-first-failure-diagnosis-20261021-ja.md)と[詳細JSON](pml-native-first-failure-diagnosis-20261021.json)では、L/Fの解析後F0（post F0）の50 Hz以下が計20フレーム、最小が24.277110099326237 Hz、700 Hz以上が0と記録されています。推定直後のraw F0の正値はすべて50 Hzを超えています。

既存の補間・65〜700 Hzへのclampの後にかかるIIR平滑化の下振れと、保存値・例外の位置は整合しています。ただしfilter replayは未実施で、保存されていないclamp直後の配列も再構成していません。今回の診断だけでフィルター応答を独立に再測定したとは扱いません。

## 保存選択の一致と、科学処理の成功を分ける

[保存L/F選択の照合記録](actual-saved-selection-verdict.json)では、path・offset・objectiveの独立算術が全フレーム一致しました。保存された選択の整合性に限る確認であり、元のnative科学処理の成功や品質承認ではありません。

[実起動記録](actual-native-invocation.json)は実終了コード2、86.123181257秒です。[3録音の到達点](actual-native-speaker.json)と[親の受領記録](parent-materialized-receipt.json)を併せて保存しています。Library保存と親受領は成功し、受領記録では外側6ファイル・内側211ファイルの全bytes・hash一致が記録されています。これは今回の13メンバーを照合した作業とは別の受領証拠です。

6件の例外tracebackは録音・枝別の `*_failure.json` に原文のまま収録しています。ソース固定情報に残る「実行未開始」のmetadataは準備当時の記録であり、実起動・終了記録とは時点を分けて読みます。

## 品質評価と残り117録音への展開を停止する

品質評価の段階Bと残り117録音への展開は停止中です。追加clip・修復・再実行は行っていません。PMLを正式baseとして維持し、失敗を成功runや品質順位へ置き換えません。

今回のdelivery成功は、旧自然音声予測3 ZIPのhelper初期接続HTTP403や、旧人工500組・MOCHAの保留条件を解決したことにはなりません。旧成果の再試行・別経路転送は行っていません。

## 原文13メンバーを研究記録として保持する

Library `libfile_41cad63a06fc81918bc662c753bd54da` version 0の13メンバーを原bytesで保存しました。[MANIFEST](MANIFEST.json)は自身を除く12件の容量・SHA256を記録しています。波形・候補コード・監査コードは含めていません。natural-japanese quickは新README・案内・公開要約・STATUS・PR本文に適用し、原文13メンバーと旧設計原文7件・旧MANIFESTは改稿していません。今回の保存では測定・再解析・import・help・テスト・smoke・ビルド予行は行っていません。
