# 非MLボコーダーの比較と開発

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

まず既存の比較対象と比較方法を実装しました。独自の高品質ボコーダーが完成した段階ではありません。

- [現在のベースとの比較・音声例](experiments/2026-10-11/world-harvest-base/results/run-001/index.html)
- [比較基盤の初回記録HTML](experiments/2026-10-11/comparison-workbench/results/run-001/index.html) と [全数値JSON](experiments/2026-10-11/comparison-workbench/results/run-001/results.json)
- [現在のベース手法の情報](BASELINE.json)：現在はユーザー指定のWORLD Harvestです。WORLDの解析・合成と組み合わせ、今後の改善を比較する正式な基準にします。実験から品質最良と認定したという意味ではありません。
- [進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[次の作業](docs/STATUS.md)、[開発とログ](docs/DEVELOPMENT.md)
- [5人の議論](experiments/2026-10-11/comparison-workbench/reviews/discussion.md)、[参考資料と確認範囲](research/reference-survey/README.md)

[GitHub Pagesの実験一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/) からグループごとに閲覧できます。[記録の構成](experiments/README.md) と [公開・ローカル確認の手順](docs/PUBLISHING.md) を参照してください。

## 比較対象

| ID | 構成 | 役割 |
|---|---|---|
| `world_dio` | DIO + StoneMask / CheapTrick / D4C / WORLD合成 | 既存の比較対象 |
| `world_harvest` | Harvest / CheapTrick / D4C / WORLD合成 | 現在の正式ベース。自己比較の差分も表示 |
| `llsm_world_dio` | WORLD DIOの基本周波数（F0）を渡すLLSM2の層0（layer 0） | 調波の位相と雑音の表現が異なる解析合成系を比較 |
| `identity` | 元波形コピー | 測定器の検査専用。ボコーダーでも候補でもない |

無加工再合成は、原音を特徴量へ変換し、意図的な編集をせずに音声へ戻す試験です。LLSMはこの試験だけを実装しています。WORLDには音高（pitch）・音量（gain）・時間長（duration）の編集と、パラメータの保存・読込があります。F0は声の周期性を表す基本周波数で、音高の測定に用います。「息っぽさ」などの知覚語による制御や、「似た音声が近い特徴量になること」は未検証です。

## 再実行

検証環境はLinux x86_64、Python 3.12、GCC/G++ 13です。必要なものはuv、git、C/C++コンパイラと、自然音声のFLACファイルを波形へ復号するFFmpegです。初回は依存ソースと音声を取得するネットワーク接続が必要です。以下はリポジトリのルートで実行します。学習済みモデルは使いません。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.build_world
uv run --locked python -m vocoderbench.build_llsm
uv run --locked python scripts/fetch_data.py
uv run --locked python -m vocoderbench.run --output runs/local-comparison
```

`runs/local-comparison/index.html` を開いてください。依存ソースは特定のcommitに固定し、WORLDはファイルの内容を照合するハッシュ値も検査します。音声は固定URLに加え、FLACファイルと復号後のPCM波形のハッシュ値で確認します。キャッシュ、C/C++からビルドした共有ライブラリ、取得音声はGit管理外です。

自然音声を取得せずに動作を確認する場合は、最後の比較コマンドに `--no-natural --sample-rates 16000` を追加できます。LLSMを省く場合は `--no-llsm` を追加してください。省略した条件の評価を行ったことにはなりません。

比較基盤に処理エラーや長さ不一致があっても、失敗を含むHTML/JSONを生成してから終了コード1を返します。正常終了は品質合格を意味しません。短い区間ごとに周波数成分を調べるSTFTの誤差、音高を測定できなかった区間、無音への雑音付加などを結果内で確認してください。指標の定義と読み方は [測定仕様](docs/EVALUATION.md) にまとめています。

## 依存と音声の帰属

WORLDはBSD-3-Clause、LLSM2と直接結合するアダプターはGPL-3.0-or-laterです。詳細は [依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) を参照してください。元録音全体は取得用キャッシュに置き、短い比較用音声例はレポートに同梱します。出典・利用条件・変換内容を記録しています。
