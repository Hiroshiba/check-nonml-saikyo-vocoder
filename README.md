# 非MLボコーダーの比較と開発

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

自作の調波・雑音方式を最初のベースとして実装し、既存比較対象の **WORLD（Harvest）** と同じ入力で測定します。HarvestはWORLDの基本周波数（F0）抽出方法です。初代は改善の出発点であり、WORLDより高品質との認定ではありません。

- [自作ベースの比較と音声](experiments/2026-10-11/initial-hnm/results/run-001/index.html)
- [現在のベース](BASELINE.json)、[進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[開発とログ](docs/DEVELOPMENT.md)
- [5人の往復議論と出典](experiments/2026-10-11/initial-hnm/reviews/discussion.md)
- [GitHub Pagesの一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/)

## 現在の2方式

| 方式 | 役割・構成 |
|---|---|
| 自作HNM (`hnm`) | 初代ベース。自己相関F0、調波振幅・相対位相、時間別の雑音パワーを解析し合成 |
| WORLD（Harvest） (`world_harvest`) | 唯一の既存比較対象。Harvest / CheapTrick / D4C / WORLD合成 |

原音は再合成の正解参照として音声を載せ、候補方式には数えません。両方式とも音高・音量・時間長を編集できます。自作方式の表現は保存・読込と、細部を持たない手作り入力からの合成に対応します。声質の知覚的距離や「息っぽさ」などの制御は未検証です。

過去のレポートは当時の比較対象・ベース・表示を保持します。今後の一覧は主要指標と比較差、短い音声例に絞り、全数値・欠測・失敗・実行条件は詳細に残します。

## 再実行

検証環境はLinux x86_64、Python 3.12、GCC/G++ 13です。必要なものはuv、git、C/C++コンパイラと、自然音声のFLACファイルを波形へ復号するFFmpegです。初回は依存ソースと音声を取得するネットワーク接続が必要です。以下はリポジトリのルートで実行します。学習済みモデルは使いません。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.build_world
uv run --locked python scripts/fetch_data.py
uv run --locked python -m vocoderbench.run --output runs/local-comparison
```

`runs/local-comparison/index.html` を開いてください。依存ソースは特定のcommitに固定し、WORLDはファイルの内容を照合するハッシュ値も検査します。音声は固定URLに加え、FLACファイルと復号後のPCM波形のハッシュ値で確認します。キャッシュ、C/C++からビルドした共有ライブラリ、取得音声はGit管理外です。

自然音声を取得せずに動作を確認する場合は、最後の比較コマンドに `--no-natural --sample-rates 16000` を追加できます。省略した条件の評価を行ったことにはなりません。

比較基盤に処理エラーや長さ不一致があっても、失敗を含むHTML/JSONを生成してから終了コード1を返します。正常終了は品質合格を意味しません。短い区間ごとに周波数成分を調べるSTFTの誤差、音高を測定できなかった区間、無音への雑音付加などを結果内で確認してください。指標の定義と読み方は [測定仕様](docs/EVALUATION.md) にまとめています。

## 依存と音声の帰属

WORLDはBSD-3-Clauseです。詳細は [依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) を参照してください。元録音全体は取得用キャッシュに置き、短い比較用音声例はレポートに同梱します。出典・利用条件・変換内容を記録しています。
