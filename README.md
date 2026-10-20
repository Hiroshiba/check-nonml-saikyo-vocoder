# ボコーダーの比較と開発

本変更では、限定16 kHz・今回評価した0/±3半音の研究baseとして **RAW_FULL（family/packageキー `pml`、version `raw-full-fwcep60-v1`）を選択します**。比較相手は前base PML / `pml-lowband-fwcep60-v1` です。固定120録音・40話者・2seedの既存結果に基づく事後の工学的選択であり、統計的な採用証明・普遍的最良ではありません。

**ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。** 以下の文書・コード・解釈はAI作成物です。

## 研究ベース：RAW_FULL

[採用判断・厳密値・比較音声](research/raw-full-adoption-selection-2026-10-20/index.html) ／ [全120録音の保存比較・順位](research/raw-full-full120-comparison-2026-10-19/index.html) ／ [純解析・復号RTF](research/raw-full-pure-rtf-2026-10-19/index.html) ／ [APIと実行手順](docs/PML.md)。

予測MOS平均差+0.07676と小さいnative忠実度・話者類似度の利得を、MOS負差195/720・警告22/720、編集有声取りこぼし+0.1545ポイント・警告28/480、GT付き55録音のCER/WERの不利、保存約17.1%増・純復号wall RTF約5.24%増と交換します。単回・固定順の速度測定を普遍的性能比とはせず、新統合packageを計時済みとはしません。

RAWのgain追従性能、A/Lを含む全特徴の距離・補間・因子分離、任意target音高、native 48 kHzは未測定・未達のままです。確率的F0/VUVと生物・音響モデルの研究課題も解決済みとはしません。

公開save/loadは `parameters.pml` と `raw.npz` を含むdirectoryへ変更します。旧単体PMLからの自動変換・旧独立復号は提供しません。新実装、consumer、保存/API文書と今回判断を同じ変更に含め、過去の方式ラベル・測定値・`adoption_evaluation_complete=false` は保持します。

## 以前の固定120録音・全8方式比較

[音声付きの全指標・順位表をGitHub Pagesで開く](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/all-method-final-2026-10-15/index.html) ／ [保存値・来歴・限界](research/all-method-final-2026-10-15/README.md)。2026年10月15日集計、主120録音40話者の予定工程は終端しています。元ASV105件・VCTK126件は未完で、取得可能な別補助群と区別します。当時の開発ベースはHNM v3であり、指標別順位と対応差を示し、総合勝者は選びません。

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

登録済み方式の一覧は、音声処理や通信をせずに表示できます。

```sh
uv run --locked python -m vocoderbench.reference --list-methods
```

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

`BASELINE.json`で本変更が選択する研究ベースは **RAW_FULL / raw-full-fwcep60-v1** です。前base PMLの測定・採用記録は[旧評価記録](docs/PML_EVALUATION_PLAN.md)に保持します。以下のHNMの歴史的結果は当時の値を保持し、旧実装と旧専用計算CLIは削除しました。再現が必要な場合は変更前commit `bbab81f` を使います。

- [雑音合成5案の比較・音声とv3採用](experiments/2026-10-12/noise-stability/results/run-001/index.html)
- [日本語の補助比較・英語音声例とv2採用](experiments/2026-10-12/jvs-supplement/results/run-001/index.html)
- [固定120音声の比較と当初の判定](experiments/2026-10-12/noise-envelope/results/run-001/index.html)
- [初代ベースの記録](experiments/2026-10-11/initial-hnm/results/run-001/index.html)
- [5人の往復議論と出典](experiments/2026-10-11/initial-hnm/reviews/discussion.md)
- [GitHub Pagesの一覧](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/)

RAW_FULLとWORLDの人工信号による音響特性・操作追従と、固定自然音声2区間の補助測定は次のコマンドで記録します。正式な品質採否は上記の固定120音声比較で行います。実行環境はLinux x86_64、Python 3.12、GCC/G++ 13。uv、git、C/C++コンパイラ、自然音声復号用FFmpegが必要です。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.build_world
uv run --locked python scripts/fetch_data.py
uv run --locked python -m vocoderbench.run --sample-rates 16000 --output runs/local-comparison
```

人工信号だけの原因分析では `--no-natural`、対象帯域の指定には `--sample-rates` を使います。同一出力の再decode照合、保存読込往復、固定手作り入力のAPI確認、原音波形の自己比較は行いません。既知F0に対する校正と、位相細部・雑音成分・操作追従の研究測定は保持します。

RAW_FULLはdirectoryへの保存・読込と実験的な±3半音・音量編集APIを維持します。RAWのgain追従性能は未測定です。時間長編集は未対応として記録し、品質を保証しません。WORLDの既存操作は維持します。過去の全8方式・197指標アダプターはHNM固定研究の履歴です。選択baseの標準再合成比較は `reference --include-current-base` から実施し、過去全指標をRAW_FULLへ測定済みとは扱いません。

開発候補の採否比較は、上の既存方式の準備を済ませてから実行します。

```sh
uv run --locked python -m vocoderbench.benchmark \
  --candidate-package /absolute/path/to/candidate \
  --criteria /absolute/path/to/criteria.md \
  --output runs/fixed-comparison
```

候補は選択baseと同じ解析・合成API（パッケージ内 `pml.py`）を持つリポジトリ外のPythonパッケージです。採否条件を毎回 `--criteria` で明示し、条件を事後変更した場合は旧判定を残します。旧3方式だけの経路は `--legacy-three-methods` で明示的に選びます。これは標準の既存方式比較の完了とは区別します。

自作・候補の音響指標は8乱数seed、MOS・eSTOI・F0整合性はseed 0です。追加の既存方式はseed 0の結果を併記し、8反復済みとは扱いません。不採用候補コードはGitに残さず、文章・ソースハッシュ・全測定値を保持します。そのため不採用候補の出力を公開リポジトリだけから完全再生成することはできません。

最終目標は48 kHzへの適用も含みます。正式集合は16 kHzの英語通常発声であり、低帯域モデルのアップサンプリングだけで48 kHz対応を達成したとは扱いません。日本語・ささやき・裏声の少数補助測定は別に記録しています。

## 文書と帰属

開発時のCIはキャッシュ付きRuff・ソース行数の静的解析だけを行います。2音声のスモーク経路と、音声合成・レポート保存・Pages生成の動作確認CIは削除しました。Pagesの本番生成・内部リンク検査・公開は `main` への反映後に行います。過去に保存したHTML・JSONは変更しません。

[既存方式比較](docs/REFERENCES.md)、[進め方](docs/WORKFLOW.md)、[測定仕様](docs/EVALUATION.md)、[開発・ログ](docs/DEVELOPMENT.md)、[現在の状態](docs/STATUS.md)、[公開方法](docs/PUBLISHING.md) を参照してください。

WORLDはBSD-3-Clause。追加方式はそれぞれのコード・重み・依存の利用条件を保持します。上流ソース・重みはGit管理外のキャッシュへ取得します。[依存情報](docs/THIRD_PARTY.md) と [音声の帰属](data/ATTRIBUTION.md) に既存の帰属を記録し、新方式については [REFERENCES.md](docs/REFERENCES.md) にまとめています。JVSの原音・加工音をこの追加で自動公開しません。
