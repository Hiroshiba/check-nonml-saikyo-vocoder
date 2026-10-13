# WORLD＋6方式：解析・再合成と音声出力の確認

WORLDを含む既存方式の再合成比較。7方式・2音声、再合成・評価完了14/14件。少数音声の動作確認であり、品質の採用判定ではありません。

結果は [run-001](results/run-001/index.html) にあります。HTML内に音声を埋め込み、全測定値・条件・ワーカーログは隣のJSONに保存しています。

これは既存方式の比較であり、自作ベースの測定・選定はしません。DACは明示選択時だけ追加し、未選択なら欠落や失敗には数えません。

## 記録と公開

ローカルの比較結果を保存しただけではGitHub Pagesには出ません。このフォルダとexperiment.jsonをPRへ含め、mainへマージした後、Pagesの公開処理が成功すると一覧と音声付きHTMLが公開されます。

コピー元とファイルのSHA-256はpublication.jsonに記録しています。復元・HTMLの保存を新規の計測と数えません。少数音声の確認では、固定120音声の品質比較や自動MOS測定を完了したとは扱いません。

## 音声の出典

正式集合の音声は [コーパスの説明](../../../docs/CORPUS.md) を参照してください。動作確認の2音声は [LLSM2の固定版README](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/README.md) のTest Soundsに由来します。[CMU ARCTIC](http://festvox.org/cmu_arctic/) のarctic_a0001.wavと、[unfaのAre you ready?](https://freesound.org/people/unfa/sounds/258342/)です。比較用に先頭最大5秒を使用し、公開音声例は原音・再合成の先頭最大2秒です。再合成には各方式の標本化周波数への変換が含まれ、音量合わせはしていません。
