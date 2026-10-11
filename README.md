# 非MLボコーダーの比較と開発

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

まず既存の比較対象と比較方法を実装しました。独自の高品質ボコーダーが完成した段階ではありません。

- [初回比較結果HTML](experiments/2026-10-11/comparison-workbench/results/run-001/index.html) と [全数値JSON](experiments/2026-10-11/comparison-workbench/results/run-001/results.json)
- [現在のbase情報](BASELINE.json)：初代は未選定。差分表示の比較基準はWORLD DIOで、品質最良の認定ではありません。
- [進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[次の作業](docs/STATUS.md)
- [5人の議論](experiments/2026-10-11/comparison-workbench/reviews/discussion.md)、[参考資料と確認範囲](research/reference-survey/README.md)

[GitHub Pagesの実験一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/) から日付・テーマ別に閲覧できます（初回の公開設定とデプロイ完了後）。[記録の構成](experiments/README.md) と [公開・ローカル確認の手順](docs/PUBLISHING.md) を参照してください。

## 比較対象

| ID | 構成 | 役割 |
|---|---|---|
| `world_dio` | DIO + StoneMask / CheapTrick / D4C / WORLD合成 | 固定した差分表示の比較基準 |
| `world_harvest` | Harvest / CheapTrick / D4C / WORLD合成 | 同じ合成器で解析器の影響を比較 |
| `llsm_world_dio` | WORLD DIOのF0を渡すLLSM2 layer 0 | 調波位相・雑音表現の異なる解析合成系を比較 |
| `identity` | 元波形コピー | 測定器の検査専用。ボコーダーでも候補でもない |

LLSMは無加工再合成だけを実装しています。WORLDには物理量によるpitch/gain/duration編集と、パラメータの保存・読込があります。知覚語による制御や「似た音声の近い表現」は未検証です。

## 再実行

検証環境はLinux x86_64、Python 3.12、GCC/G++ 13。必要なものはPython、git、C/C++コンパイラ、自然音声のFLAC展開用FFmpegです。初回は依存ソースと音声を取得するネットワーク接続が必要です。学習済みモデルは使いません。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m vocoderbench.build_world
python -m vocoderbench.build_llsm
python scripts/fetch_data.py
python -m unittest discover -s tests -v
python -m vocoderbench.run --output runs/local-comparison
```

`runs/local-comparison/index.html` を開いてください。依存ソースはcommit固定、WORLDはソースファイルhashも検査します。音声は固定URL・FLAC hash・復号PCM hashで確認します。キャッシュ、native共有ライブラリ、取得音声はGit管理外です。

自然音声を取得せずに動作を確認する場合は、`--no-natural --sample-rates 16000` を指定できます。LLSMを省く場合は `--no-llsm` を指定してください。省略した条件の評価を行ったことにはなりません。

比較基盤に処理エラーや長さ不一致があっても、失敗を含むHTML/JSONを生成してから終了コード1を返します。正常終了は品質合格を意味しません。STFT誤差、音高欠測、無音への雑音付加などを結果内で確認してください。

## 依存と音声の帰属

WORLDはBSD-3-Clause、LLSM2と直接結合するアダプターはGPL-3.0-or-laterです。詳細は [依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) を参照してください。音声はリポジトリに再配布せず、取得方法と条件を記録しています。
