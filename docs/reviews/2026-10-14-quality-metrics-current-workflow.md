# 既存方式の保存出力と品質証跡への調整

2026-10-14（日本時間）。PR #27の調整記録。新しい指標や合成手法の提案・測定記録ではありません。
当初の [実装確認](2026-10-12-quality-metrics.md) は当時の記録として変更しません。

## 比較対象と変更範囲

- 元のPR #27 head: `28a01f63578814f65f552f8dc8609bf8cb78df37`。
- 取り込んだmain: `9957ccc6fc3342f75e1f23765526979847feecb4`。
- 現行AGENTS・USER_INSTRUCTIONS・WORKFLOW・DEVELOPMENT・EVALUATION、実際のreference入力保存・worker出力・results作成コードを読み、現在の運用へ合わせた。
- `USER_INSTRUCTIONS.md` はmainの内容をそのまま継承し、独自差分は作っていない。依存・ワークフロー・過去のHTML/JSONは変更していない。旧ブランチに元々あったワークフローを今回の新設や再導入と扱わない。

## 指摘と反映

1. 原音自己比較: `identity` の行は非参照UTMOSv2だけに限定した。参照型指標の原音対原音の行は自動生成せず、原音を通常の参照として使う他方式の評価は維持した。
2. 現行入力: `--reference-run` でschema_version 5の結果と契約、`inputs.json`、`native/<method>/<case>.json`・`.npy` を読む。実際の保存形式に存在しない `status.json`/出力WAVを仮定しない。予定方式とケースは元契約から取得し、欠落・失敗を除外しない。
3. 帯域・長さ: paired指標は無調整全長同士の同一標本化周波数・同一長を要求し、不一致はnull。共通区間の値は転記しない。非参照UTMOSv2は参照を読まず出力固有の全長・標本化周波数で測る。評価器固有の内部前処理は既存来歴のまま。
4. 比較の意味: 元の `comparison_reference` と `formal_base` を区別して保存・表示し、現在のBASELINE.jsonで当時の指定を置き換えない。モデル・入力・元ソース・seed・元方式の記録も保持する。
5. PR #30への受け渡し: `quality-evidence-index.json` から同階層の `quality-evidence-<digest>.json` を発見できる。digestはcase・methodのJSONから作り、任意IDをファイル名に直結しない。UTMOSv2とECAPAだけを所定の2フィールドへ対応させ、measuredだけok、他は元状態とnullにする。
6. 評価器同一性: 設定・実モデル来歴・実装hash・環境・反復プロトコルからconfiguration_sha256を作る。実モデル未取得時は来歴nullと失敗状態を保持する。初期化、初回、各反復を混ぜず、初回採点・方向・集約は変えない。
7. 公開: 品質証跡はPagesの平坦なHTML/JSON制約に合わせた。公開は新しいsupplementへ必要ファイルだけを保存し、work・ログ・モデル・全長音声を丸ごとコピーしない。旧結果と主比較の平均を書き換えない。

## 静的確認

Python 3.12.14、uvの固定依存、Ruff 0.17.0。共有の書き込み可能なuvキャッシュを指定し、Ruffはリポジトリ設定の `.cache/ruff`、行数確認は `.cache/source-size.json` を利用した。

```sh
export UV_CACHE_DIR=/workspace/scratch/71b268329986/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/scratch/71b268329986/.cache/uv-python
uv sync --locked --only-dev
uv run --locked --only-dev ruff check .
uv run --locked --only-dev python scripts/check_source_size.py
git diff --check
git diff origin/main -- USER_INSTRUCTIONS.md
```

Ruffの初回で既存の `del backend` と遅延lambda参照に対してF821が出たため、同じ呼び出しを `functools.partial` に置き換えた。最終静的確認はRuff・ソース行数・差分空白検査が成功し、USER_INSTRUCTIONSのmainとの差分は空。

テスト・スモーク・CLI help・人工波形・音声処理・モデル推論・新しい測定・Pages生成は実行していない。実資産推論、数値の正しさ、native保存出力からの追加評価、PR #30との実行時接続は未検証。静的解析合格を実測成功や品質優越として扱わない。

独立レビューで、品質曲線へ編集点を渡せる手順とHTMLの「無編集再合成のみ」の表現が一致しない点を指摘された。保存音声を対象に、参照距離は無編集比較、編集点は適用条件内の非参照MOSと固定参照の話者類似度と書き分けた。評価式・値の方向・集約・参照型の同一長／標本化周波数の条件は変更していない。
