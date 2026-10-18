# 編集差の補助診断

固定120録音の既存主評価を使う事後集約。結果はindex.html、元精度と入力SHAはscalar-results.json。

aggregate.pyは音声・モデル・候補実装を読みません。公開された10 checkpointとordinary-summary、およびPML評価のinput-manifestだけを使います。

再現時は、リポジトリをvocoder-candidate-pr-20261017という名前のディレクトリへ配置し、その親にediting-contrast-diagnostic-20261018ディレクトリを作成して、このフォルダのPLAN-ja.md・aggregate.py・render.pyを入れてください。親ディレクトリからPythonでaggregate.py、その後render.pyを実行します。numpyが必要です。元の実行では入力SHAを照合し、結果をresults.jsonへ新規保存しています。既存results.jsonを上書きしません。

これは旧Cartesian候補の診断であり、boundary-hold候補の新計測ではありません。正式な主評価の順位は変えず、音声例は元のordinary/ordinary.htmlを参照します。独立した追加録音や新規人間評定ではありません。
