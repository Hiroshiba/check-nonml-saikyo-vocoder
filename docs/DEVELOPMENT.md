# 開発とログの手順

本書はユーザー指示を実行に移すためのAIの運用文書であり、`USER_INSTRUCTIONS.md` が優先する。

## PythonのCLIと依存関係

Python 3.12、uv 0.12.23、Ruff 0.17.0を使用する。`pyproject.toml` と `uv.lock` で依存を固定し、`uv sync --locked` で環境を作る。NumPyとSciPyの版は従来の比較実行から変えていない。

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked python scripts/check_source_size.py
uv run --locked python -m vocoderbench.build_world
uv run --locked python -m vocoderbench.run --no-natural --sample-rates 16000 --output runs/local-comparison
uv run --locked python scripts/build_site.py
```

テストコードは実装しない。旧 `tests/` と、合否を判定していた `scripts/audit_metrics.py` は削除した。過去の実験記録は残し、現在の手順と区別する。比較・校正CLIは音響測定値と欠測を保存する研究用の実行であり、品質を合否判定するテストへ置き換えない。通常の入力検証と、処理失敗時の非ゼロ終了は維持する。

比較処理やCIに埋め込んだテストも同じ扱いとする。同じ入力・同じ条件での再デコード一致検査、保存・読込後の一致検査、CIでのDAC未取得アサーションは削除した。合否を返さず結果を診断値として保存する形でも、これらの自己検査を再実装しない。音響特性の比較・校正、通常の入力検証、ログ収集は残す。過去の結果JSON・HTMLは書き換えない。

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

PRとデフォルトブランチ `main` へのpushで、依存環境の構築、静的解析、WORLDのビルド、小規模比較、Pagesの生成を行う。uvと静的解析のキャッシュを引き継ぐ。失敗時も比較出力とログをActionsの成果物へ保存する。静的解析の成功と、音質が優れていることは別の判断である。

## 表示と今後のGUI

現在はPythonで生成する静的な実験レポートで、GUIアプリは作成していない。表示は日本語話者向けに説明し、システム設定に従って明暗を切り替える。

GUIを作る際はユーザー指示に従い、PC上で動かす必要がある場合はElectron、それ以外はWebフロントとする。Vite、TypeScript、pnpm、Tailwind CSS、VueJS、Reka UIを使う。ユーザーが指示文から削除した要件をAI判断で復活させない。

## 参照

- [uvのGitHub Actions公式手順](https://docs.astral.sh/uv/guides/integration/github/)
- [Ruffの設定](https://docs.astral.sh/ruff/configuration/)
- [進め方と承認待ちの扱い](WORKFLOW.md)
