# 費用集計の準備成果物

公開入口は derive_cost_report.py と COST-DEFINITIONS-ja.md。全120件未完の入力では部分観測として保存し、最終全体値や速度順位は出しません。

実行例（既存のJSONだけを読む。出力名は未使用名にする）:

    python derive_cost_report.py --candidate-root <候補結果root> --reference-summary <PML attemptのsummary.json> --reference-summary <WORLD attemptのsummary.json> --output <新規出力.json>

現実の保存済み入力だけで派生集約を実行。科学的再測定・人工入力試験なし。AST構文静的解析済み。公開位置では固定Ruff 0.17.0をキャッシュ付きで実行し成功しました。再開費用 previous_encode_costs は今回の入力に実例がないため独立レビューでの静的確認のみ。

候補の原費用JSONをZIPから新たに読み直していない。終端chunk receiptに結合されたscalar投影と保存済みlossless receiptの同一性を根拠にする。原byte再検証が必要な用途では別途、保存済みZIP内の対象JSONだけを読んでSHA照合する工程が必要。
