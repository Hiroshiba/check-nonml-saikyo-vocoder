# 全8方式の品質・制御・表現比較：主集合120録音の保存結果

固定LibriSpeech120録音・40話者の主比較について、保存済みの測定・集計と方式別の状態をまとめました。HNM v3、WORLD Harvest、FACodec v1、HiFi-Glot、GOLF-ff、SiFi-GAN、LLSM2 Layer0、MagPhaseの8方式を同じ条件で比較し、HNMとの差を併記します。現在の開発ベースはHNM v3のままです。総合順位・平均順位・総合勝者や新ベースの採用は決めていません。

## 結果の入口

- [日本語HTMLレポートと短い比較音声](index.html)
- [全順位表・状態・区間のJSON（gzip圧縮）](results.json.gz)
- [全保存数値の分割一覧](raw-values-manifest.json)と[分割1](raw-values.part-0001.json.gz)・[分割2](raw-values.part-0002.json.gz)
- [来歴](provenance-manifest.json)、[入力・出典の一覧](source-inventory-manifest.json)、[公開範囲と限界](publication-limitations.json)
- [量子化の共通時間窓による補助比較](quantization-common-window/index.html)
- [音声の出典・許諾・改変表示](audio_credits.html)
- [測定・集計・公開処理のソース付録](../all-method-reproduction-20261014/README.md)

HTMLは[GitHub Pages](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/all-method-final-2026-10-15/index.html)の掲載対象に登録しています。`main` の公開処理が成功すると[一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/)から開けます。ダウンロードして開く場合は関連リンクも含めてこのディレクトリ構成を保ってください。登録経路は圧縮・分割済みの15成果をbyteそのままでコピーし、旧実験形式への変換や再集計はしません。

## 完了した範囲と残る限界

主集合120録音・40話者の予定工程は終端まで処理しました。終端には成功だけでなく失敗・適用外・未対応を含み、全方式・全指標の成功や知覚品質の合格を意味しません。全18評価群×8方式の144セルと197派生軸を表示し、そのうち比較順位を付けない35軸も診断として残します。197軸を独立した197票には数えません。欠測をゼロや最下位順位に置き換えません。

元計画のASV105件・VCTK126件は未完です。取得可能なASV100件とVCTK16件の補助研究は別の集合・分母として表示し、元計画の達成や主集合への追加録音数には数えません。したがって全体の final_gate / terminal は未完のままです。48 kHzの全方式共通の品質優越や、独立した最終検証の完了も主張しません。

話者等重みの主比較、HNMとの対応差、各軸の適用範囲・母数を併読してください。単回RTFの条件混在、後から採用した補助分析、相関の条件付き解析、量子化の共通窓補助などの制約はHTMLとJSONに保持しています。

## 保存形式と公開範囲

このディレクトリの既存15成果物は、2026-10-15に確定したv4書出しのbyteをそのまま保存しています。数値・順位・区間の再計算やHTML再生成は行っていません。各成果物は10 MiB未満で、[成果物一覧](artifact-manifest.json)にSHA256・byte数・Git blob SHA1があります。manifest自身は自己参照の対象外です。

成果物内の published:false / private_draft / 公開承認待ち等は書出し時点の状態を保持する記録であり、このPRの公開可否を判定する現在のフラグではありません。科学的な terminal:false と区別してください。

試聴は固定2録音の先頭最大2秒、原音と許諾確認済み6方式の計14例だけです。GOLF-ffとSiFi-GANの音声は重み固有の明示許諾が未確認のため含めません。全長音声、モデル、元の人間評定CSVや評定者行は公開していません。数値の公開はそれらの取得権を付与しません。これは保存値の検証用資料であり、全入力を含む完全再現アーカイブではありません。

[10月14日11:00時点の途中記録](../all-method-progress-2026-10-14.md)は履歴として維持し、現在の結果は本ページを参照します。
