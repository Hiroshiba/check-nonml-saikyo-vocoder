# 開発とログの手順

本書はユーザー指示を実行に移すためのAIの運用文書であり、`USER_INSTRUCTIONS.md` が優先する。

## PythonのCLIと依存関係

Python 3.12、uv 0.12.23、Ruff 0.17.0を使用する。`pyproject.toml` と `uv.lock` で依存を固定し、`uv sync --locked` で環境を作る。NumPyとSciPyの版は従来の比較実行から変えていない。

```sh
uv sync --locked --only-dev
uv run --locked --only-dev ruff check .
uv run --locked --only-dev python scripts/check_source_size.py
```

テストコードは実装しない。名称や合否判定の有無によらず、コードが正しく動くかを確かめるためのスモーク・回帰・自己検査も追加しない。旧 `tests/` と `scripts/audit_metrics.py` に加え、2音声のスモーク経路、再decode一致・保存読込往復・固定手作り入力のAPI確認、波形を自身と比較する自己検査を削除した。再表示・保存・一覧生成のCI予行も行わない。過去のHTML・JSON・実施記録は当時の状態で残す。

研究では、固定100音声以上と自動MOSによる正式比較、既知F0信号による測定器の校正・前処理比較、位相細部・雑音成分の影響、音高・音量・時間長の操作追従を測る。人工信号は音響特性の原因分析に使い、動作確認専用のケース群やCIへ戻さない。`vocoderbench.run` の原音側の校正は既知F0との誤差だけを記録する。`vocoderbench.benchmark` も原音との自己差分・自己比較の追加指標は計算せず、原音MOSと音声保存を維持する。通常の入力検証、保存・読込API、処理失敗時のログと非ゼロ終了は維持する。

## 後から追えるログ

各CLIは `runs/logs/UTC日時-コマンド名-プロセス番号.log` と標準エラーへログを出す。ログ内の時刻もUTCで記録する。保存先は `VOCODERBENCH_LOG_DIR` で変更できる。

- Pythonの警告、処理中に捕捉した例外、未処理例外、コマンド引数の誤りを記録する。例外にはスタックトレース、検出した異常状態には呼出しスタックを付ける。
- 外部処理の標準出力・標準エラーも共通処理で保存する。正常終了した外部処理の標準エラーは警告として残す。
- Pythonから呼ぶC/C++処理で異常終了した場合に備え、`faulthandler` で取得可能なPythonスタックを残す。C/C++内部の全スタックまで保証するものではない。
- 失敗した測定はログだけでなく結果JSON・HTMLにも残す。欠測は0点や0誤差に置き換えない。

ログ初期化前のPython・uvの起動失敗や、ログ保存先そのものへ書き込めない場合は実行端末の標準エラーに出る。CIではセットアップも含めGitHub Actionsの実行ログに保存される。

## 静的解析とCI

Ruffは `.cache/ruff` を使用する。行数確認はGit管理対象と未追跡の非無視ファイルからソースを階層全体で列挙し、内容のハッシュと行数を `.cache/source-size.json` に保存する。400行を超えると分割検討の警告、1000行を超えるとエラーにする。現在の対象拡張子はPython、C/C++、JavaScript/TypeScript、Vue、CSS。ソースの種類を増やす際は一覧も更新する。

キャッシュ・外部ソース・ビルド成果物は `.gitignore` で除外する。実験の自動生成HTML・JSONはソース行数の対象外。将来、Git管理する自動生成ソースを追加する場合は、手編集できない生成物である根拠と生成手順を文書化してから例外を追加する。現在そのようなソースの例外はない。

PRとデフォルトブランチ `main` へのpushでは、開発依存だけを用意し、Ruffとソース行数の静的解析を行う。uvと静的解析のキャッシュを引き継ぎ、ログをActionsの成果物へ保存する。音声合成・モデル取得・比較CLIはCIで実行しない。静的解析の成功と、音質が優れていることは別の判断である。

Pagesの生成と内部リンク検査は `main` へのpushまたは明示的な公開実行で行い、PRの動作確認用には実行しない。本番公開のリンク検査・成果物保存・デプロイは維持する。研究実行と公開の手順は [REFERENCES.md](REFERENCES.md)、[EVALUATION.md](EVALUATION.md)、[PUBLISHING.md](PUBLISHING.md) を参照する。

## 表示と今後のGUI

現在はPythonで生成する静的な実験レポートで、GUIアプリは作成していない。表示は日本語話者向けに説明し、システム設定に従って明暗を切り替える。

GUIを作る際はユーザー指示に従い、PC上で動かす必要がある場合はElectron、それ以外はWebフロントとする。Vite、TypeScript、pnpm、Tailwind CSS、VueJS、Reka UIを使う。ユーザーが指示文から削除した要件をAI判断で復活させない。

## 参照

- [uvのGitHub Actions公式手順](https://docs.astral.sh/uv/guides/integration/github/)
- [Ruffの設定](https://docs.astral.sh/ruff/configuration/)
- [進め方と承認待ちの扱い](WORKFLOW.md)
