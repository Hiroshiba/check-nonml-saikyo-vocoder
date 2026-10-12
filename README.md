# 非MLボコーダーの比較と開発

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

現在のベースは **自作HNM v3** です。雑音の音色と時間包絡の分離を保ち、PSDの台形積分とFFT端点配分を揃えました。固定120録音の5案比較から、小さな明瞭性・スペクトル誤差の悪化を許容し、帯域再現などを優先した開発上の選択です。既存比較対象は **WORLD（Harvest）**。知覚品質の優越やWORLD超えを確証したものではありません。

- [雑音合成5案の比較・音声とv3採用](experiments/2026-10-12/noise-stability/results/run-001/index.html)
- [日本語の補助比較・英語音声例と以前のv2採用](experiments/2026-10-12/jvs-supplement/results/run-001/index.html)
- [固定120音声の比較と当初の判定](experiments/2026-10-12/noise-envelope/results/run-001/index.html)
- [初代ベースの記録](experiments/2026-10-11/initial-hnm/results/run-001/index.html)
- [現在のベース](BASELINE.json)、[進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[開発とログ](docs/DEVELOPMENT.md)
- [5人の往復議論と出典](experiments/2026-10-11/initial-hnm/reviews/discussion.md)
- [GitHub Pagesの一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/)

## 現在の2方式

| 方式 | 役割・構成 |
|---|---|
| 自作HNM v3 (`hnm`) | 現在のベース。自己相関F0、調波振幅・相対位相、雑音の音色と時間包絡を解析し合成。雑音FFT端点を半重みで配分 |
| WORLD（Harvest） (`world_harvest`) | 唯一の既存比較対象。Harvest / CheapTrick / D4C / WORLD合成 |

原音は再合成の正解参照として音声を載せ、候補方式には数えません。両方式とも音高・音量・時間長を編集できます。自作方式の表現は保存・読込と、細部を持たない手作り入力からの合成に対応します。声質の知覚的距離や「息っぽさ」などの制御は未検証です。

過去のレポートは当時の比較対象・ベース・表示を保持します。今後の一覧は主要指標と比較差、短い音声例に絞り、全数値・欠測・失敗・実行条件は詳細に残します。

## 再実行

検証環境はLinux x86_64、Python 3.12、GCC/G++ 13です。必要なものはuv、git、C/C++コンパイラと、自然音声のFLACファイルを波形へ復号するFFmpegです。初回は依存ソースと音声を取得するネットワーク接続が必要です。以下はリポジトリのルートで実行します。エンコーダー・デコーダーには学習済みモデルを使いません。自動MOS評価には学習済みのUTMOSv2を使用します。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.build_world
uv run --locked python scripts/fetch_data.py
uv run --locked python -m vocoderbench.run --output runs/local-comparison
```

`runs/local-comparison/index.html` を開いてください。依存ソースは特定のcommitに固定し、WORLDはファイルの内容を照合するハッシュ値も検査します。音声は固定URLに加え、FLACファイルと復号後のPCM波形のハッシュ値で確認します。キャッシュ、C/C++からビルドした共有ライブラリ、取得音声はGit管理外です。

自然音声を取得せずに動作を確認する場合は、最後の比較コマンドに `--no-natural --sample-rates 16000` を追加できます。省略した条件の評価を行ったことにはなりません。

比較基盤に処理エラーや長さ不一致があっても、失敗を含むHTML/JSONを生成してから終了コード1を返します。正常終了は品質合格を意味しません。短い区間ごとに周波数成分を調べるSTFTの誤差、音高を測定できなかった区間、無音への雑音付加などを結果内で確認してください。指標の定義と読み方は [測定仕様](docs/EVALUATION.md) にまとめています。

## 固定120音声の比較

上の小規模実行は開発時の動作確認です。方式の採否には、[固定集合](docs/CORPUS.md)の120録音、[追加音響指標](docs/EXTENDED_METRICS.md)、[自動MOS](docs/MOS.md)を使います。音声と依存の版・ハッシュ、前処理、予定件数、失敗を保存し、候補と当時のベース、WORLD（Harvest）を同じ条件で比較します。

```sh
uv run --locked python -m vocoderbench.corpus fetch
uv run --locked python -m vocoderbench.benchmark \
  --candidate-package /absolute/path/to/candidate \
  --criteria /absolute/path/to/criteria.md \
  --output runs/fixed-comparison
```

候補はリポジトリ外のPythonパッケージとして用意し、現在のHNMと同じ解析・合成APIを持たせます。不採用の候補実装はGitに残さず、変更内容・ソースのハッシュ・全測定値を保存します。そのため不採用候補の出力を公開リポジトリだけから完全再生成することはできません。条件が一致する場合だけ中断地点から再開でき、既存の結果の条件を変えて上書きしません。

`--criteria` は今回の目的・保持条件・採否の考え方を記した文書です。次の候補へ過去の棄却条件を暗黙に引き継がないよう、実行ごとに明示します。条件を結果の後で見直す場合は、旧判定を残して事後の判断と記録します。

出力は `index.html`、`results.json`、`summary.json`、音声例です。HNMの音響指標は8種類の乱数seed、MOS・eSTOI・F0整合性はseed 0で測ります。予測MOSは人間の新規評定ではなく、今回の音声に対する独自校正も未実施です。正式集合は英語の通常発声であり、日本語やささやき・裏声への品質を保証しません。

## 依存と音声の帰属

WORLDはBSD-3-Clauseです。詳細は [依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) を参照してください。元録音全体は取得用キャッシュに置き、短い比較用音声例はレポートに同梱します。出典・利用条件・変換内容を記録しています。
