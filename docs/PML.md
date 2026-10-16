# PML低域拡張＋60FWCEP：現在の開発ベース

> **追加評価中のdraftです。** このPRはPMLへのベース置換案を保存するものです。既存研究の38指標だけで全評価完了とはせず、共通の全指標・制御・速度を追加測定してから採用可否を判断します。mainのHNMはまだ置き換わっていません。

機械学習を使わない解析・合成器。REAPERの連続F0をパルス時計に使い、CheapTrickの振幅包絡を60個のFWCEP係数へ変換し、位相のばらつきから求めた二値雑音マスクとともに保存する。復号では低域マスクを最初の非保護binから延長し、対数・複素領域で雑音変調したパルスを重ねる。詳細は[図解](../research/pml-fwcep-2026-10-16/mechanism.html)、[採用結果](../research/pml-fwcep-2026-10-16/index.html)、[実装の帰属](../vocoderbench/pml/README.md)を参照。

## 実行

Python 3.12 / uv、解析時はpyreaper 0.0.11・pyworld 0.3.5が必要。Linuxの初回依存ビルドにはC/C++コンパイラが必要。復号API自体はNumPyとSciPyだけを読み込むが、現在のリポジトリ環境は従来の評価用依存も含む。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.pml_cli encode input.wav features.pml --timing-json analysis.json
uv run --locked python -m vocoderbench.pml_cli decode features.pml output.wav --timing-json decode.json
uv run --locked python -m vocoderbench.pml_cli decode features.pml up3.wav --pitch-semitones 3
```

16 kHzモノラルに限定。48 kHzを黙って再標本化しない。短すぎる音声・非有限値・完全な零信号はエラー。F0未検出時は上流の65 Hz時計へのフォールバックを警告に残す。復号は元のWAVに依存しない。出力はFLOAT WAVで、正規化・クリップをしない。ピークが1を超える場合は再生系で歪む可能性がある。

解析seedの既定は20261015。復号は保存seedを使い、明示指定も可能。音高操作は累積±3半音の実験的機能。追従が観測できた区間でも、周期性の検出失敗や音量変化がある。時間長操作は未対応で例外として記録する。包絡の60係数化は低ビットレートcodecを意味せず、研究での総payloadは約805 kbpsで16 kHz/16 bit PCMより大きい。この容量は旧研究容器PMLFWC28の実測で、今回のPMLFWC01はヘッダーが異なり同じ容量値とは扱わない。

## 固定100録音以上の比較

```sh
uv run --locked python -m vocoderbench.reference --include-current-base --seed 20261015 --output runs/pml-reference-120
```

従来の参照方式準備は[手順](REFERENCES.md)を参照。この入口はPMLと標準7参照の無編集再合成を扱う。解析・復号RTFを別々に保存する。単発計測なので機械・スレッド数・処理範囲と併読する。PMLの解析では圧縮を含み、復号では包絡復元を含む。

開発候補比較の `benchmark --candidate-package` は `pml.py` にencode/decodeを持つGit外パッケージを受け取る。自作ベースと候補の音響測定8seed・MOS seed 0は従来契約を維持するため、採用研究seed 20261015とは別実験として扱う。旧HNMキャッシュを新PMLの値として読まない。

## 過去実装・測定値

旧HNM本体と専用noise/supplement計算CLIは削除。過去のHTML/JSONは測定時の方式名・版・順位を保持する。履歴の再計算には変更前commit `bbab81f60674ffe5b898ba35575defa399e21d8e` を別checkoutで使う。

`all_metrics_*` / `added_metrics_*` は過去HNMを含む全8方式研究の経路であり、PMLへ機械置換しない。保存値の集計・他参照方式は残すが、旧HNM再計算は明瞭に停止する。PML全197軸・48 kHz・時間編集は未評価。旧HNMのAPI互換を偽装しない。

## 統合の確認範囲

公開研究結果は凍結研究コードでの実測値。今回のパッケージ化はimport、表現保存、入力検証、ログ、乱数状態の局所化の整理であり、全120録音を新パッケージで再測定したという意味ではない。静的解析とソースレビューを行い、テスト・スモーク・保存往復自己検査は追加しない。Pagesの本番生成はmainマージ後に既存workflowが行う。


## 追加評価の未完項目

既存全8方式比較の18群・197派生軸とは窓・定義が異なるため、今回の38軸をそのまま転載しない。共通窓の音響・明瞭性、ECAPA話者距離、SCOREQ、ASR、実時間測定、pitch/gain操作、表現距離・readout・ABX・保存精度/補間を棚卸し、PML対応アダプターと独立runで評価する。時間操作など実装未対応は適用外・未対応として記録する。結果を揃えるまでdraftでありマージしない。

## 統合CLIによる説明用1例（2026-10-16）

LibriSpeech `1089-134686-0008` の先頭6秒を新CLIで解析・保存・復号しました。解析5.185秒、復号0.917秒（単発・冷開始、解析時は後で修正した非推奨aliasの大量警告を含む）でした。この値は速度順位に使いません。新形式payloadは603,219 bytes、出力96,000 samples、peak 0.454845、±1超過0。原音との20 ms STFT収束は0.3160、帯域エネルギーMAEは0.4390 dBでした。

これは説明用の追加生成であり、既存120録音の再測定、旧波形との一致検査、品質採用の十分条件ではありません。初回はpyreaper依存が無い環境で失敗し、既存の解析runtimeを指定して生成しました。ソースの非推奨 `row_stack` aliasは同じ `vstack` 関数へ置換し、警告を隠す処理は追加していません。

追加評価の全群・優先順・再利用条件・終了条件は [評価計画](PML_EVALUATION_PLAN.md) に記録しています。
