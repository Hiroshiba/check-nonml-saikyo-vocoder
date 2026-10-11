# GitHub Pagesで結果を見る

公開先は https://hiroshiba.github.io/check-nonml-saikyo-vocoder/ です。公開設定と最初のデプロイが完了してから閲覧できます。

## 初回のリポジトリ設定

リポジトリの **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選びます。この設定にはリポジトリの管理権限が必要です。ソースを変更するPRだけでは、この管理設定は変更されません。

`main` へのマージで `Publish experiment archive` ワークフローが動きます。初回設定を後で行った場合は、Actionsから同ワークフローの **Run workflow** を実行してください。公開URLはデプロイジョブの環境リンクでも確認できます。

PRではサイトの生成・リンク検査だけを行い、公開しません。公開対象は検査済みの結果・資料HTMLとJSON、一覧ページです。入力音声、キャッシュ、共有ライブラリ、Git管理外の実験結果は含めません。

## ローカルで確認する

```sh
python scripts/build_site.py
python -m http.server --directory _site 8000
```

ブラウザで http://localhost:8000/ を開きます。ビルドにはPythonの標準ライブラリだけを使い、音声処理のビルド・再測定・ネットワーク取得は不要です。`_site/` は公開用の一時生成物で、Git管理しません。

日付・テーマ別の構成と追加手順は [記録の構成](../experiments/README.md) を参照してください。Markdown文書はGitHubの読みやすい表示へリンクします。結果HTMLと参考資料HTMLはPages内で直接閲覧できます。

## 過去のURLと測定値

旧 `reports/initial-comparison/index.html` と旧 `docs/research/research_index_ja.html` には、公開サイト内で新しい場所への案内ページを生成します。測定JSONは新しい実行フォルダに集約します。

移設時に測定値・ハッシュ・当時のコマンドを書き換えません。結果HTMLを表示変更のため再生成した場合も、測定JSONの来歴は測定時点の情報です。

## 参照した公式仕様

- [GitHub Pagesのカスタムワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [公開元の設定](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

Pagesへの書き込み権限とOIDCのトークン権限は公開ジョブだけに付けます。公開対象は `main` に限定します。
