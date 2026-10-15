# GOLF-ff・SiFi-GANの短い研究比較音声の掲載判断

## 今回の対象

2026年10月15日、既存の研究比較レポートの試聴対象へ、GOLF-ffとSiFi-GANの4例を追加します。対象は固定LibriSpeech test-cleanの `1089-134686-0008` と `1188-133604-0003`、各方式の保存済み・パラメーター未編集の再合成音声の先頭2秒だけです。原音と全8方式の計18例になり、全長音声やモデルは配布しません。

これは今回の研究比較に限った掲載判断であり、法的保証、モデルの商用利用の許諾、モデル再配布の可否を示すものではありません。音声を短くしたこと自体を利用根拠とはしていません。

## 掲載判断と根拠

GOLF-ffは、対象checkpointの公式リポジトリ同梱配布、追加時点のMITライセンス、および当時のGitHub規約を確認し、今回の研究比較音声の掲載に必要な利用根拠があると判断しました。SiFi-GANは、外部配布モデル固有のライセンスの明記は確認できていませんが、公式の配布・推論案内と今回の研究比較用途を踏まえ、短い解析・再合成音声を掲載します。NUS-48Eには研究用途限定の条件があります。その条件がモデルや出力へ自動的に適用されると判断したものではありません。本判断は今回のLibriSpeech入力による短い比較音声に限定し、モデルの商用利用・再配布の可否を示すものではありません。

### GOLF-ff

- 実行時のコード版は `dfe4f4628b8d59d05c9988ae9341a544b1ff30c4`。[固定版README](https://github.com/iamycy/golf/blob/dfe4f4628b8d59d05c9988ae9341a544b1ff30c4/README.md)と[LICENSE](https://github.com/iamycy/golf/blob/dfe4f4628b8d59d05c9988ae9341a544b1ff30c4/LICENSE)を参照します。
- checkpointは `epoch=539-step=996840-val_loss=3.073.ckpt`。保存SHA-256は `1eba39620c64d1c59b0a6acb4149200c4791f8e22ec0435bf13bfe5fd86468ab` です。
- [重み追加commit](https://github.com/iamycy/golf/commit/5737a8b784d9db8a8a1f720ba5c1e6e0b4f96736)、[追加前から存在するMITライセンス](https://github.com/iamycy/golf/blob/5b924ce32ab9503fc52b002704f98132fd099125/LICENSE)、[当時のGitHub規約D.6](https://github.com/github/site-policy/blob/673c01e2bed86d4e1f62f10f1d4d00a4c4cdd867/Policies/github-terms/github-terms-of-service.md)を併せて確認しました。
- これらを今回の用途の判断材料とし、生成音声にMITライセンスを表示したり、重み固有の独立した許諾文があると断定したりはしません。

### SiFi-GANとNUS-48E

- 実行時のコード版は `cdb20daeb4da4a126077819091706ee90522c7a8`。[固定版README](https://github.com/chomeyama/SiFiGAN/blob/cdb20daeb4da4a126077819091706ee90522c7a8/README.md)にモデルの配布と解析・再合成の案内があります。
- checkpointは `sifigan_libritts-r-clean+nus-48e_checkpoint-1000000steps.pkl`。保存SHA-256は `2d673e3cee10b4e88dd69b344443b38e0ef0d48f15f1ee5b417c66c0544e5df6` です。
- 外部配布archive内にモデル固有のLICENSE/NOTICEは確認できていません。[リポジトリのコード側のMITライセンス](https://github.com/chomeyama/SiFiGAN/blob/cdb20daeb4da4a126077819091706ee90522c7a8/LICENSE)を、外部配布モデルや出力音声へそのまま当てはめません。
- [NUS公式データセット案内](https://smcnus.comp.nus.edu.sg/)およびそこから案内される[公式README](https://drive.google.com/file/d/1dO5Zo8qsMM2NdnNr1RfvrLThs-2kBYjO/view)には研究用途限定の条件があります。学習データの条件がモデルやその出力へ自動的に伝わると判断したものでも、NUSの研究条件だけで出力の公開許可が確定すると判断したものでもありません。
- 今回入力したのはLibriSpeechの2録音です。NUS-48Eの録音自体は公開していません。

NUS-48Eの資料が求める引用：Zhiyan Duan, Haotian Fang, Bo Li, Khe Chai Sim, and Ye Wang. “The NUS Sung and Spoken Lyrics Corpus: A Quantitative Comparison of Singing and Speech.” APSIPA, 2013. [公式論文PDF](https://smcnus.comp.nus.edu.sg/archive/pdf/2012-2013/2013_05-Pub-NUS-48E.pdf)

## 入力音声の帰属と改変表示

LibriSpeech (c) 2014 by Vassil Panayotov。[OpenSLR SLR12](https://www.openslr.org/12)で配布されたLibriSpeech test-cleanを用いています。原録音の配布条件は[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)です。LibriVox・Project Gutenbergに由来する既存の説明と原配布noticeは[帰属HTML](../../research/all-method-final-2026-10-15/audio_credits.html)に保持しています。

追加例は固定版ボコーダーによる解析・再合成後、保存済みnative波形の先頭48,000標本を切り出し、24 kHz・モノラルのIEEE float32 WAVにしています。公開書出しでは音量正規化・クリッピング・再標本化・無音除去・位置合わせを行っていません。新しい推論や指標評価も行っていません。入力時の再標本化を含む方式の処理と、今回の公開書出しを区別します。

入力FLAC、元の復号PCM、測定入力NPY、native波形、native記録、合成契約、コード版、checkpoint、公開WAVの各識別子と改変内容は[音声JSON](../../research/all-method-final-2026-10-15/audio_samples.json)に記録しています。提供元・著作者・話者による本比較の推奨を意味しません。

## 科学的結果と履歴の保持

- この変更は `cbd5febddc1be66689c2911afb3a75afa7c98b2c` の掲載版を基準にしています。一覧の42指標の設定はそのまま保持し、成果物manifestへのサイズ・SHA-256の固定値だけを更新します。
- 成果物は15ファイルのままです。変更するのは音声JSON、帰属HTML、詳細HTMLの音声欄、およびそれらのhashを記録するmanifestです。測定JSON・raw値・来歴・出典一覧と量子化補助の11ファイルはbyte単位で保持します。
- 詳細HTMLの数値・順位・比較対象・母数・HNMとの差・95%区間はそのままです。モデルの再推論、測定、集計、全体HTMLの再生成は行っていません。
- 既存14例の音声bytesは保持します。一覧の原音・HNM・WORLD Harvestの3試聴例も変えません。詳細への試聴例数の表示は14から18になります。
- 元の出典一覧とexporter識別子は元の書出しの履歴です。旧exporterが追加4例を生成したという主張へ書き換えません。音声JSONの `research_publication_addendum` へ今回の範囲・判断・書出し方法を追記し、元のterms/exporter hashの適用範囲を明記します。
- 旧版で音声の公開を保留した履歴を、測定失敗またはゼロ誤差へ置き換えません。今回の掲載判断も、数値の品質合格や総合勝者の選択を意味しません。
