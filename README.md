# ボコーダーの比較と開発

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

## 標準の既存方式比較

**WORLDに加えて、FACodec・HiFi-Glot・GOLF-ff・SiFi-GAN・LLSM2 Layer 0・MagPhaseを標準比較対象にします。DACは `--include-dac` 指定時のみ追加します。** 自作ベースとの近さや、改良に使えるかを選定理由にはしません。既存方式への全置換も候補です。指示変更は [PR #28](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/pull/28)、実装と結果保存は [PR #29](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/pull/29) に分けています。

**保存済みの比較：[WORLD＋6方式の音声付きHTML](experiments/2026-10-12/reference-methods/results/run-001/index.html)** ／ [全測定値](experiments/2026-10-12/reference-methods/results/run-001/results.json) ／ [確認範囲と復元元](docs/reviews/2026-10-13-reference-publication.md)。これは2026年10月12日の2音声・14再合成の動作確認です。固定120音声の品質比較・MOS測定・方式の採用判定を済ませたものではありません。HTMLと音声JSONはこのリポジトリに保存し、mainへのマージ後にPagesで公開します。

```sh
uv sync --locked
# Ubuntu 24.04。C/C++・CMake・makeと、MagPhase用SPTK 3.9が必要
sudo apt-get install build-essential cmake sptk
bash scripts/setup_references.sh
uv run --locked python -m vocoderbench.corpus fetch
uv run --locked python -m vocoderbench.reference --output runs/references-120
```

DACの準備・計測は両方とも明示的に指定します。未選択ならDACのコード・重みを取得せず、推論もしません。

```sh
bash scripts/setup_references.sh --include-dac
uv run --locked python -m vocoderbench.reference --include-dac --output runs/references-with-dac
```

`python -m vocoderbench.benchmark --output ...`（開発候補なし）も同じ入口です。自作ベースはこの比較の測定・選定基準に含めません。開発候補を `--candidate-package` と `--criteria` で渡す従来コマンドは、当時の開発ベース・候補・WORLDに上記6方式を追加します。

推論依存は `.cache/references/env` のPython 3.10へ隔離し、本体のPython 3.12・MOS評価器と混在させません。コードのcommitと重みのSHA-256を固定し、未取得・失敗を黙って除外しません。対応帯域・利用条件・出力長・部分実行・再開方法は [既存方式比較](docs/REFERENCES.md) を参照してください。

正式比較は [固定集合](docs/CORPUS.md) の120録音、[追加指標](docs/EXTENDED_METRICS.md)、[自動MOS](docs/MOS.md) を使います。出力は `index.html`、`results.json`、`summary.json`、音声例、未調整の全長波形、条件記録、失敗ログです。異なる出力長を強制的に合わせず、全長の不一致と共通区間の補助指標を分けます。予測MOSは新規の人間評定ではありません。

動作確認専用の `--smoke` と `--no-mos` は削除しました。CIは静的解析だけを行い、比較・再合成・推論をコードの動作確認として実行しません。上のコマンドは本来の品質測定を行うためのものです。

### 結果をGit・Pagesへ残す

`runs/` はGit管理外です。計測後は次のコマンドでHTML・短い音声JSON・測定条件・ログを実験フォルダへコピーし、`experiment.json` に登録します。元のHTML・測定値を変更せず、SHA-256と元の記録日時を保持します。出力された実験フォルダ一式を比較のPRに含めます。

```sh
uv run --locked python -m vocoderbench.references.publish \
  --source runs/references-120 --topic reference-methods \
  --title '既存7方式の固定120音声比較'
uv run --locked python scripts/build_site.py
```

上のコマンドは結果を公開用に保存する操作であり、GitへのcommitやPagesのデプロイはしません。実験フォルダをmainへ反映した後、[公開ワークフロー](docs/PUBLISHING.md)が成功すると、一覧から音声付きHTMLを開けます。CIの期限付き成果物だけを結果の保存先にはしません。

## 自作開発経路と過去の記録

`BASELINE.json`上の現在の開発ベースは **自作HNM v3** です。固定120録音の雑音合成5案比較から選んだもので、既存方式への品質優位を確証したものではありません。この追加ではベース実装・採用状態・過去結果を変更しません。

- [雑音合成5案の比較・音声とv3採用](experiments/2026-10-12/noise-stability/results/run-001/index.html)
- [日本語の補助比較・英語音声例とv2採用](experiments/2026-10-12/jvs-supplement/results/run-001/index.html)
- [固定120音声の比較と当初の判定](experiments/2026-10-12/noise-envelope/results/run-001/index.html)
- [初代ベースの記録](experiments/2026-10-11/initial-hnm/results/run-001/index.html)
- [5人の往復議論と出典](experiments/2026-10-11/initial-hnm/reviews/discussion.md)
- [GitHub Pagesの一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/)

人工信号や少数音声でコードを動かす旧 `vocoderbench.run`、専用の信号生成・HNM診断・F0校正CLIは削除しました。過去の結果と当時の説明は記録として残しますが、その再実行を開発の確認手順にはしません。開発時の静的解析は [開発・ログ](docs/DEVELOPMENT.md) を参照してください。

自作HNMとWORLDは音高・音量・時間長を編集できます。自作表現は保存・読込と手作り入力からの合成に対応しますが、声質の知覚距離や息っぽさ等の制御は未検証です。今回追加する6方式の共通入口は再合成比較であり、属性操作・下流学習の比較は未実装です。

開発候補の採否比較は、上の既存方式の準備を済ませてから実行します。

```sh
uv run --locked python -m vocoderbench.benchmark \
  --candidate-package /absolute/path/to/candidate \
  --criteria /absolute/path/to/criteria.md \
  --output runs/fixed-comparison
```

候補はHNMと同じ解析・合成APIを持つリポジトリ外のPythonパッケージです。採否条件を毎回 `--criteria` で明示し、条件を事後変更した場合は旧判定を残します。旧3方式だけの経路は `--legacy-three-methods` で明示的に選びます。これは標準の既存方式比較の完了とは区別します。

自作・候補の音響指標は8乱数seed、MOS・eSTOI・F0整合性はseed 0です。追加の既存方式はseed 0の結果を併記し、8反復済みとは扱いません。不採用候補コードはGitに残さず、文章・ソースハッシュ・全測定値を保持します。そのため不採用候補の出力を公開リポジトリだけから完全再生成することはできません。

最終目標は48 kHzへの適用も含みます。正式集合は16 kHzの英語通常発声であり、低帯域モデルのアップサンプリングだけで48 kHz対応を達成したとは扱いません。日本語・ささやき・裏声の少数補助測定は別に記録しています。

## 文書と帰属

[既存方式比較](docs/REFERENCES.md)、[進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[開発・ログ](docs/DEVELOPMENT.md)、[現在の状態](docs/STATUS.md)、[公開方法](docs/PUBLISHING.md) を参照してください。

WORLDはBSD-3-Clause。追加方式はそれぞれのコード・重み・依存の利用条件を保持します。上流ソース・重みはGit管理外のキャッシュへ取得します。[依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) に既存の帰属を記録し、新方式については [REFERENCES.md](docs/REFERENCES.md) にまとめています。JVSの原音・加工音をこの追加で自動公開しません。
