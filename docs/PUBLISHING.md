# GitHub Pagesで結果を見る

公開先は https://hiroshiba.github.io/check-nonml-saikyo-vocoder/ です。公開済みです。

## 初回のリポジトリ設定

リポジトリの **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選びます。この設定にはリポジトリの管理権限が必要です。ソースを変更するPRだけでは、この管理設定は変更されません。

`main` へのマージで `実験記録の公開` ワークフローが動きます。初回設定を後で行った場合は、Actionsから同ワークフローの **Run workflow** を実行してください。公開URLはデプロイジョブの環境リンクでも確認できます。

PRでは静的解析だけを行い、サイト生成の予行はしません。サイト生成・内部リンク検査は `main` へのpushと明示的な公開実行で行います。公開対象は保存済みの結果・資料HTMLとJSON、一覧ページです。元録音全体、キャッシュ、共有ライブラリ、Git管理外の実験結果は含めません。比較用の短い原音・合成音声は、出典を明記して結果JSONとHTMLに同梱します。

## ローカルで確認する

```sh
uv run --locked python scripts/build_site.py
uv run --locked python -m http.server --directory _site 8000
```

ブラウザで http://localhost:8000/ を開きます。サイト生成にはPythonの標準ライブラリだけを使い、音声処理のビルドや再測定は不要です。uv環境の初回作成には依存パッケージの取得が必要です。`_site/` は公開用の一時生成物で、Git管理しません。

グループの構成と追加手順は [記録の構成](../experiments/README.md) を参照してください。Markdown文書はGitHubの読みやすい表示へリンクします。結果HTMLと参考資料HTMLはPages内で直接閲覧できます。

## 過去のURLと測定値

### 圧縮・分割済みの確定レポート

従来の `experiments/*/*/experiment.json` はそのまま使います。異なる集計形式の確定成果は `research/pages-reports.json` へ別に登録し、旧 `resynthesis` 形式へ変換しません。登録には公開相対パス、元集計の記録日時、比較先・一覧に出す既存指標、許諾確認済み短例、成果物manifest自身のSHA256・サイズ・総ファイル数を記録します。

`scripts/site_preserved_reports.py` はmanifestで指定したHTML・JSON・gzipだけを同じ相対構造へコピーします。全ファイルのサイズ・SHAをコピー前後に照合し、単体10 MiB以上・重複・公開先衝突を拒否します。ディレクトリの丸ごとコピーは行わず、ソース付録、全長音声、モデル、私有保全情報をこの経路へ追加しません。既存15成果物のbyte・HTML・測定値は変更しません。

一覧は元の集計日時と既存レポート日時を合わせて新しい順に表示します。主比較の保存済み平均・順位・HNM対応差の表示と既存短例の引用だけを行い、統計の再計算や音声再生成はしません。全表・95%区間・欠測理由と帰属表示へリンクします。成果物内の公開前状態は当時の記録であり、科学的な未完状態とは区別します。

PR段階では静的解析・保存SHAの確認までです。`main` の公開ワークフローによる実ビルド・リンク検査の後、本番の一覧、指標表、短音声、圧縮・分割ファイルのリンクを確認します。

旧 `reports/initial-comparison/index.html` と旧 `docs/research/research_index_ja.html` には、公開サイト内で新しい場所への案内ページを生成します。測定JSONは新しい実行フォルダに集約します。

移設時に測定値・ハッシュ・当時のコマンドを書き換えません。過去の結果HTMLも表示変更のために再生成せず、当時の状態で保持します。一覧の並び順・日時表示は保存済みの記録日時から生成します。

## 参照した公式仕様

- [GitHub Pagesのカスタムワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [公開元の設定](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

Pagesへの書き込み権限とOIDCのトークン権限は公開ジョブだけに付けます。公開対象は `main` に限定します。
