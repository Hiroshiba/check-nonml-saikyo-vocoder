# 開発とログの手順

本書はユーザー指示を実行に移すためのAIの運用文書であり、`USER_INSTRUCTIONS.md` が優先する。

## PythonのCLIと依存関係

Python 3.12、uv 0.12.23、Ruff 0.17.0を使用する。`pyproject.toml` と `uv.lock` で依存を固定する。開発時の確認は開発用依存だけを用意して静的解析を行い、音声処理を起動しない。

```sh
uv sync --locked --only-dev
uv run --locked --only-dev ruff check .
uv run --locked --only-dev python scripts/check_source_size.py
```

本来の音声比較を行う際の環境構築・測定コマンドは [既存方式比較](REFERENCES.md) とルートのREADMEを参照する。依存のNumPyとSciPyの版は従来の比較実行から変えていない。

テストコードは実装しない。アサーションや合否判定の有無にかかわらず、コードを実行して正常性を確かめる処理はテストとして扱う。「比較」「診断」「校正」「実行確認」と呼び替えたり、結果をJSON・HTMLに保存したりしても例外にしない。

旧 `tests/`、`scripts/audit_metrics.py` に加え、人工信号による `vocoderbench.run`、`fixtures.py`、`hnm_diagnostics.py`、`calibrate_pitch.py` と、既存方式の `--smoke` / `--no-mos` 経路を削除した。CIのWORLDビルド・小規模比較・既存方式の推論・HTML再表示・実験一覧登録による動作確認も削除した。これらをローカルや別workflowへ移して残さない。

固定コーパスで実際の音質・方式差を測る研究処理と、保存済み結果を実際に公開する処理は残す。それらを変更確認のために起動しない。通常の入力検証、処理失敗時の非ゼロ終了、スタックトレース付きログは本処理の一部として維持する。過去の実験結果JSON・HTMLと当時の記録は書き換えない。

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

PRとデフォルトブランチ `main` へのpushでは、開発用依存の準備、キャッシュ付きRuff・ソース行数の静的解析だけを行う。失敗時も静的解析のログをActionsの成果物へ保存する。モデル取得・音声合成・品質測定・公開の予行実行は行わない。Pagesの生成とデプロイは `main` へのpushまたは `main` を対象にした手動実行による本番公開だけで行い、PRでは起動しない。静的解析の成功は音質の優位を意味しない。

## 表示と今後のGUI

現在はPythonで生成する静的な実験レポートで、GUIアプリは作成していない。表示は日本語話者向けに説明し、システム設定に従って明暗を切り替える。

GUIを作る際はユーザー指示に従い、PC上で動かす必要がある場合はElectron、それ以外はWebフロントとする。Vite、TypeScript、pnpm、Tailwind CSS、VueJS、Reka UIを使う。ユーザーが指示文から削除した要件をAI判断で復活させない。

## 参照

- [uvのGitHub Actions公式手順](https://docs.astral.sh/uv/guides/integration/github/)
- [Ruffの設定](https://docs.astral.sh/ruff/configuration/)
- [進め方と承認待ちの扱い](WORKFLOW.md)
