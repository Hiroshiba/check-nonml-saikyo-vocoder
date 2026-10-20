# Gen2全500組：保存予測密度の比較（2026-10-20）

現baseはPMLを維持します。今回は既使用の人工残差500組についての対数予測密度の比較です。自然音声の品質・聴取・MOS評価ではなく、ボコーダ方式の採用判断でもありません。

[自然120録音のPML比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html) / [標準8方式比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/all-method-final-2026-10-15/index.html) / [初回run（部分・早期停止）](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/oracle-evidence-run-001-2026-10-20/index.html) / [世代1回収union（36組）](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/oracle-evidence-recovery-union-001-2026-10-20/index.html) / [元oracle実験・5人工音の例](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/oracle-covariance-2026-10-20/index.html)

## 全500組の結果

差はBMA − 旧plug-inモデルのtest score、単位はnats/recordです。各生成条件100組の保存平均と、保存済み10,000回paired bootstrapによるpointwise 95% percentile CI（NumPy linear）を示します。正値はこの固定人工条件でBMAの対数予測密度が高いことを意味します。25比較の同時保証・多重比較補正・外部データへの一般化・生理学的原因の確率校正を示しません。

全5000積分・500組が揃い、各truth100組、欠測0。25比較すべて保存bootstrap 10000回。以下は保存値の転記です。別表に保存平均だけから作る記述的順位を付けます。

| truth / 旧モデル | 平均差 | pointwise 95% CI |
|---|---:|---|
| W / W | 0.24584287430363475 | [0.08957988594226207, 0.42421390100235146] |
| A / A | 0.3766352084044229 | [0.16492756078671253, 0.6112916846591983] |
| V / V | 0.501062382710952 | [0.2525254155180132, 0.7684480563816127] |
| S / S | 0.15405476498821372 | [0.0013344192004501583, 0.313684556487305] |
| J / J | 0.41905396815256607 | [0.22233376192221113, 0.6355938206131457] |

全25比較は[HTML](index.html)と[CSV](comparisons.csv)、全2500対応差は[paired-differences.csv](paired-differences.csv)。

## モデル

- W：白色雑音：時間に依存しない分散。
- A：AR(1)：隣接時刻の相関を持つ残差。
- V：位相依存分散：周期内位置によって分散が変わる残差。
- S：振幅ゆらぎ（shimmer型）：周期ごとの振幅摂動に対応する共分散。
- J：時間ゆらぎ（jitter型）：周期ごとの時間摂動の線形化に対応する共分散。

モデル平均とparameter integrationの両方が変更されています。この差を「混合だけによる改善」と解釈しません。derivedにはper_model_minus_pluginやweights等もありますが、今回は新しい統計分析・寄与分解を追加せず、両効果の分離は後続の検討事項とします。新しい平均・区間・bootstrapは計算していません。

## 状態の区別

**数値の到達**：5000/5000積分・500/500組・各truth100組。全25比較のfull100平均・区間を保存済み。

**元Gen2 union**：出力容量guardによるexit 2 / unresolvedを保持。数値の欠測ではなくresults保存の容量制限。

**compact最終保存**：2026-10-20 08:10:33.940487–08:10:36.813371 UTC、2.8728917150001507秒。worker・supervisor・外部waitは0で完了。

**今回の3shard**：Gen2 A/B/Cの終了確認済み。

**祖先の終了来歴**：世代1 B（33–65）の外部終了unknownを保持。全世代終了確認済みとはしない。

**独立監査**：raw5000・全25比較summaryに加え、compact成果物も独立監査通過の報告を受領。derived500・保存2500差exact・summary原bytes・両receiptと外部wait 0を確認済み（親の監査報告、2026-10-20）。

## 再構成と未確認

元unionは容量制限でderived全項目を保存できませんでした。別のcompact工程が凍結deriveを500組に適用して再構成し、保存されていた2500個のBMA対応差とのexact一致を記録しています。これは全derived項目が失敗前の未保存値と一致したという検証ではありません。summaryは384100 bytesの原bytes再利用で、compact工程のbootstrap再実行0・新平均計算0です。本レポート作成ではderive自体も再実行していません。

raw5000・summaryとcompact成果物の独立監査通過は親の監査報告に基づきます。compactについてderived500・保存2500差exact・summary原bytes・両receiptと外部wait 0まで確認済みです。この表示修正工程で新たな科学計算を行ったという意味ではありません。bound_certified=falseを保持します。今回ブラウザー描画は未確認です。

## 配布・復元

新パス案：`research/oracle-evidence-gen2-complete-2026-10-20/index.html`。実験保存先案：`experiments/2026-10-20/oracle-evidence/results/gen2-complete-001/`。初回・世代1部分・今回を別記録として残し、親READMEに今回への逆リンクを追加する構成案です（2026-10-20作成時点）。既存report・PR77は変更していません。

rawは`raw/merged-slots.json.gz`一件だけ。mtime=0/level=9で圧縮し、解凍原bytes・SHA一致を確認しました。原raw54543195 bytes、SHA `b0167bd1a937b7dc28d1cfde99415a463023663c9240f70f205795e94122dd04`。

summaryは`original/compact/output/summary.json`に一度だけ配置。元union summary-progressとcompact summaryは同一384100 bytes、SHA `eba5228576b9f7b671825a5374416c33deaed5f879af1c1496fe313b920f2869`。再構成derived・compact results・receipt・pins・終了証拠は原bytesを保持。source manifestはhash来歴のみで実装sourceは含みません。元manifest内には省略ファイルも載るため、本配布物の実在一覧にはルートartifact-manifest.jsonを使います。

元の親merged-slots約12.5MBと空ログは重複配置せず、入力Library ZIPに復元参照を保持します。全配布ファイルは10 MiB未満で、既存navigation-only builderの許可形式（HTML/Markdown/JSON/CSV/JSON.gz）に収めます。builder変更・ビルド予行は行っていません。

新音声なし。元oracleの5人工例は今回BMAの音声ではなく、自然120比較も別物です。科学原本は不変。

## 2026-10-20 作成時点の履歴

この表示資料の作成時点ではGit/PR/公開操作を行っていません。これは作成工程の履歴であり、閲覧時点の公開状態を示すものではありません。求積・derive・新平均・CI・bootstrap・tests/smoke・候補source importも実行していません。


## 保存平均に基づく記述的順位

順位はtruthごとに保存mean(BMA−旧model)とBMA自身の差0を小さい順へ並べた、固定人工条件100組の平均log-scoreの記述的順位です。1位を事前に仮定せず保存値から決めます。同率は保存meanが完全一致するときだけで、順位は1,1,3の競技順位です（epsilon不使用）。統計的優越確率・品質順位・PMLや自然音声の順位ではありません。新しい平均・CI・BF・bootstrapは計算していません。

[ranking.csv](ranking.csv)に各truthのBMA＋旧5モデル、計30行を保存します。HTMLの5比較・25比較にもBMAと旧モデルの順位欄を追加しました。元比較CSVとsummaryはbyte不変です。
