# PML低域拡張＋60FWCEP：研究ベース

> 履歴文書です。PML専用CLIと実装は退役しました。下記は当時の実行手順で、再現には変更前commit `62acf3cadcd8a49f37e2e63826f2966ed2d8ce28` を使用します。

> **本変更で次の研究ベースをPMLへ更新します。** 対応可能な追加評価を終え、品質改善と制御・表現の弱点を比較した開発上の選択です。計測時の比較基準はHNM v3で、未対応と部分欠測は完了扱いせず残します。

機械学習を使わない解析・合成器。REAPERの連続F0をパルス時計に使い、CheapTrickの振幅包絡を60個のFWCEP係数へ変換し、位相のばらつきから求めた二値雑音マスクとともに保存する。復号では低域マスクを最初の非保護binから延長し、対数・複素領域で雑音変調したパルスを重ねる。詳細は[図解](../research/pml-fwcep-2026-10-16/mechanism.html)、[正式追加評価](../research/pml-package-evaluation-2026-10-16/index.html)、[当時の実装の帰属](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/62acf3cadcd8a49f37e2e63826f2966ed2d8ce28/vocoderbench/pml/README.md)を参照。

## 実行

Python 3.12 / uv、解析時はpyreaper 0.0.11・pyworld 0.3.5が必要。Linuxの初回依存ビルドにはC/C++コンパイラが必要。復号API自体はNumPyとSciPyだけを読み込むが、現在のリポジトリ環境は従来の評価用依存も含む。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.pml_cli encode input.wav features.pml --timing-json analysis.json
uv run --locked python -m vocoderbench.pml_cli decode features.pml output.wav --timing-json decode.json
uv run --locked python -m vocoderbench.pml_cli decode features.pml up3.wav --pitch-semitones 3
```

16 kHzモノラルに限定。48 kHzを黙って再標本化しない。短すぎる音声・非有限値・完全な零信号はエラー。F0未検出時は上流の65 Hz時計へのフォールバックを警告に残す。復号は元のWAVに依存しない。出力はFLOAT WAVで、正規化・クリップをしない。ピークが1を超える場合は再生系で歪む可能性がある。

encodeに `--reaper-trace-npz observations.npz` を明示すると、同じREAPER呼出しの未加工5配列だけを別ファイルへ保存します。未指定時は診断を作りません。型・単位・別時間格子・解釈の留保は[任意診断の仕様](PML_REAPER_TRACE.md)を参照してください。診断時のtiming JSONはコピー負荷を含むと明記し、ファイルI/Oは引き続き計時外です。入力・各出力の同一パスと既存出力への上書きは拒否します。

解析seedの既定は20261015。復号は保存seedを使い、明示指定も可能。音高操作は累積±3半音の実験的機能。追従が観測できた区間でも、周期性の検出失敗や音量変化がある。時間長操作は未対応で例外として記録する。包絡の60係数化は低ビットレートcodecを意味せず、研究での総payloadは約805 kbpsで16 kHz/16 bit PCMより大きい。旧研究容器PMLFWC28と新PMLFWC01は別容器です。新形式を正式120録音で測り、計61,969,776 bytes / 615.935秒、804.887 kbpsでした。

## 固定100録音以上の比較

```sh
uv run --locked python -m vocoderbench.reference --include-current-base --seed 20261015 --output runs/pml-reference-120
```

従来の参照方式準備は[手順](REFERENCES.md)を参照。この入口はPMLと標準7参照の無編集再合成を扱う。解析・復号RTFを別々に保存する。単発計測なので機械・スレッド数・処理範囲と併読する。PMLの解析では圧縮を含み、復号では包絡復元を含む。

開発候補比較の `benchmark --candidate-package` は `pml.py` にencode/decodeを持つGit外パッケージを受け取る。自作ベースと候補の音響測定8seed・MOS seed 0は従来契約を維持するため、採用研究seed 20261015とは別実験として扱う。旧HNMキャッシュを新PMLの値として読まない。

## 過去実装・測定値

旧HNM本体と専用noise/supplement計算CLIは削除。過去のHTML/JSONは測定時の方式名・版・順位を保持する。履歴の再計算には変更前commit `bbab81f60674ffe5b898ba35575defa399e21d8e` を別checkoutで使う。

`all_metrics_*` / `added_metrics_*` は過去HNMを含む全8方式研究の経路であり、PMLへ機械置換しない。保存値の集計・他参照方式は残すが、旧HNM再計算は明瞭に停止する。今回のPML追加評価は下記の別入口を使います。48 kHz・時間編集は未対応です。旧HNMのAPI互換を偽装しない。

## 正式追加評価と確認範囲

新統合パッケージの120録音をseed 0で解析・保存・復号し、共通時間窓の品質71軸と編集・量子化61群、ABX・読み出し・ASV等を測定しました。[新結果HTML](../research/pml-package-evaluation-2026-10-16/index.html)と[再現手順](../research/pml-package-evaluation-2026-10-16/REPRODUCE.md)を参照してください。旧38軸探索結果は別測定として保持します。

公開用の追加評価driverは実測後にパスを引数化した版です。静的解析・独立レビューを行いましたが、この可搬CLIで全測定を再実行したという意味ではありません。標準benchmarkだけで全追加評価を自動実行するものでもありません。合成ソースは実測版から変更していません。

未対応・部分欠測・資源不足は[評価記録](PML_EVALUATION_PLAN.md)に残しています。テスト・スモーク・保存往復自己検査は追加せず、科学的な品質・制御評価と区別します。Pagesの本番生成はmainマージ後の既存workflowで行います。

## 統合CLIによる説明用1例（2026-10-16）

LibriSpeech `1089-134686-0008` の先頭6秒を新CLIで解析・保存・復号しました。解析5.185秒、復号0.917秒（単発・冷開始、解析時は後で修正した非推奨aliasの大量警告を含む）でした。この値は速度順位に使いません。新形式payloadは603,219 bytes、出力96,000 samples、peak 0.454845、±1超過0。原音との20 ms STFT収束は0.3160、帯域エネルギーMAEは0.4390 dBでした。

これは説明用の追加生成であり、既存120録音の再測定、旧波形との一致検査、品質採用の十分条件ではありません。初回はpyreaper依存が無い環境で失敗し、既存の解析runtimeを指定して生成しました。ソースの非推奨 `row_stack` aliasは同じ `vstack` 関数へ置換し、警告を隠す処理は追加していません。

追加評価の全群・優先順・再利用条件・終了条件は [評価計画](PML_EVALUATION_PLAN.md) に記録しています。
