# 既存方式の比較

## 対象と目的

WORLD（Harvest）に加え、FACodec v1、HiFi-Glot、GOLF-ff、SiFi-GAN、LLSM2 Layer 0、MagPhaseを標準の既存比較対象にする。DACはオプショナルで、`--include-dac` を指定したときだけコード・重みの取得と計測を行う。原音は正解参照であり方式数に含めない。自作ベースを良いものと前提にせず、既存方式への全置換も検討できる比較にする。

指示変更はPR #28、実装と結果保存はPR #29。USER_INSTRUCTIONS.mdの変更は実装PRに含めない。既存のBASELINE.json・自作実装・過去の結果は今回変更しない。閉じたPR #26から実装を引き継ぎ、保存されていなかった音声付き結果を補った。

## 実行

検証対象はLinux x86_64、Ubuntu 24.04、CPU。uv、Python 3.12（本体）、Python 3.10（uvが隔離環境へ取得）、git、gcc/g++、make、CMake、SPTK 3.9が必要。初回取得時は通信する。実際の推論はHugging Face/Transformersをオフライン設定にし、未取得のモデルを推論中に探しに行かない。

```sh
uv sync --locked
sudo apt-get install build-essential cmake sptk
bash scripts/setup_references.sh
uv run --locked python -m vocoderbench.corpus fetch
uv run --locked python -m vocoderbench.reference --output runs/references-120
```

候補を指定しない `python -m vocoderbench.benchmark --output runs/references-120` も同じ入口。自作の開発候補を従来どおり `--candidate-package /absolute/package --criteria /criteria.md` で指定すると、自作・候補・WORLDの比較に6方式を加える。`--reference-cache` でその実行の推論環境を指定できる。`--legacy-three-methods` は旧3方式だけの実行経路を残すための指定で、標準比較の完了とは表示しない。

DACを含めるには準備と計測の両方に指定する。DACが失敗しても他方式の結果を残すが、明示選択された方式の失敗なので終了コードは非0となる。

```sh
bash scripts/setup_references.sh --include-dac
uv run --locked python -m vocoderbench.reference --include-dac --output runs/references-with-dac
```

部分実行では `--methods facodec golf` のように指定する。選択しなかった方式を完了件数に含めない。登録の一覧は `--list-methods` で通信せず表示できる。隔離環境の場所は準備・実行とも `--runtime-cache /absolute/cache` で合わせる。

2音声でコードを動かす `--smoke` と、動作確認専用の `--no-mos` は削除した。CI用の音声読込・推論経路も残さない。比較は100音声以上と自動MOSを前提にし、音声はコーパス取得コマンドで先に準備する。推論と評価は別環境で実行するため、本体のtorchやnumpyを旧版へ下げない。

## 保存・再開・失敗

`contract.json` に入力PCM、実装、重み、依存版、選択方式、帯域、seed、スレッド数、評価方法を固定する。同じ出力先で条件が変わっていれば拒否する。成功した合成は再開時にスキップし、`--retry-failed` で元の失敗JSONを履歴へ保存して失敗だけ再試行する。評価の部分記録も `evaluation_partial.json` に逐次保存する。

`--stage acoustic` は合成・音響診断、`--stage mos` は保存波形の評価、`--stage report` は保存結果の再表示。未計測のMOSを0点にはしない。全体は `--stage all`（既定）。1方式の準備・推論失敗で他方式を消さず、スタックトレースをログへ保存する。`--timeout` は方式のワーカー全体の上限秒数。長い集合には増やす。初期値は3600秒。

`native/方式/` に未調整の全長生成波形（npy）、出力ハッシュ、解析秒数・合成秒数・出力長差・ピークを残す。`logs/` にワーカーとネイティブ警告を残す。`results.json`、`summary.json`、`index.html`、`audio_samples.json` が比較の結果。表のRTFは単回推論の集計で、前回のウォームアップ付き5反復速度試験そのものではない。

### Git・Pagesへの保存

`runs/` に出力しただけではGitにもPagesにも残らない。結果を比較PRへ含めるには、次を実行する。

```sh
uv run --locked python -m vocoderbench.references.publish \
  --source runs/references-120 --topic reference-methods \
  --title '既存7方式の固定120音声比較'
uv run --locked python scripts/build_site.py
```

保存先は測定開始日（日本時間）の `experiments/YYYY-MM-DD/reference-methods/results/run-NNN/`。元のHTML・JSONはバイト列を変えずコピーし、`publication.json` に各SHA-256と保存日時を記録する。`experiment.json` の一覧登録日時は元の `generated_at` を保持し、過去の測定を新規実験に見せない。既存のrunを上書きせず、同一の測定結果を重複登録しない。過去のCIから復元する場合は `--provenance 出典.json` で元の実行ID・成果物ID等を追加できる。

公開物はHTML・JSONに限定し、短いWAVをJSON/HTMLに埋め込む。条件・ワーカーログ・ワーカーの測定記録もJSONとして保存する。全長npy、原音全体、学習済み重み、ネイティブライブラリは公開用フォルダへコピーしない。コマンドはGitへcommitしないため、出力した実験フォルダ一式をPRに含める。mainへのマージとPagesの公開成功後に一覧から閲覧できる。

今回の保存結果は [2音声・7方式の実測HTML](../experiments/2026-10-12/reference-methods/results/run-001/index.html)。2026年10月12日のCIから復元したもので、[復元と検証の記録](reviews/2026-10-13-reference-publication.md)を併記する。固定120録音・自動MOSはこの保存操作で測定したものではない。

## 出力長・帯域の契約

方式を同じ特徴形式へ押し込まず、公開学習済み構成のネイティブ帯域で解析・合成する。WORLD/FACodecは16 kHz、GOLF/SiFi-GAN/LLSM2は24 kHz、HiFi-Glot/DACは44.1 kHz、MagPhaseは48 kHz。48 kHzへの最終適用目標を、低帯域モデルのアップサンプリングだけで達成したとは扱わない。

推論入力は元波形からpolyphaseリサンプリングする。MagPhaseだけはREAPERのファイルAPIへPCM16を渡し、その量子化と入力SHAを記録する。その他に入力音量の正規化はしない。推論器の内部パディングは公式の経路に従う。生成結果を原音長に合わせて切り詰めたりゼロ埋めしない。

全長診断の `measurement` は長さが異なると `length_mismatch` のまま保持する。それとは別に、入力の標本化周波数へ変換した生成音と原音の共通先頭区間だけを `common_prefix` として評価し、双方のカバー率を残す。これは補助比較で、欠落した末尾を再現したという意味ではない。自動整列、DTW、ゲイン合わせをしない。

予測MOSは元音声・各方式の全長ネイティブ出力を既存UTMOSv2へ渡す。明瞭性eSTOI、STFT、帯域、F0推定整合性、包絡は共通区間で測る。新しい参考比較表では区間値と長さ差を併記する。開発候補用の従来表へは、全長が一致する指標だけを転記し、共通区間値で全長の欠測を埋めない。

## 公開物と互換修正

前回の実測（PR #24、run 38231956948）で使った公開物を `vocoderbench/references/sources.lock.json` と `requirements.txt` で固定した。学習型の5方式はstrictな学習済みstateの読込を行い、ランダム重みで代用しない。SiFi-GANは修正後の多話者音声・歌唱モデル、GOLFはgolf-ffを使う。LLSM2 Layer 1、GOLF-ss等を実行したとは扱わない。

GOLFの固定サブモジュールをHTTPSで取得し、`torch.Any`の型注釈を修正する。SiFi-GANの励振入力をfloat32にする。MagPhaseはlib2to3、Python 2の整数除算、NumPy/SciPyの廃止別名、パッケージ読込を互換修正する。変換は固定原本から行い、差分・実行ファイルのハッシュを記録する。Python 2版とのビット一致は未検証。

| 方式 | 公開実装 | 注意 |
|---|---|---|
| WORLD | https://github.com/mmorise/World | 既存world.lock.jsonの固定版、BSD-3-Clause |
| FACodec | https://github.com/lifeiteng/naturalspeech3_facodec | Amphion由来。モデルとコードの利用条件は別々に確認 |
| HiFi-Glot | https://github.com/PupuAI/HiFi-Glot | MITの公開コード。配布モデルカードも参照 |
| GOLF | https://github.com/iamycy/golf | 固定サブモジュール・依存を含め利用条件を保持 |
| SiFi-GAN | https://github.com/chomeyama/SiFiGAN | 公開多話者重みと統計量を組にして利用 |
| LLSM2 | https://github.com/Sleepwalking/libllsm2 | GPLv3・特許についての著者説明あり。製品採用とは別判断 |
| MagPhase | https://github.com/CSTR-Edinburgh/magphase | 元のLICENCE、SPTK・REAPERの条件も保持 |
| DAC（任意） | https://github.com/descriptinc/descript-audio-codec | コード・配布重みのMIT条件を保持 |

上流のコード・重み・コンパイル物はGit管理外のキャッシュに置き、ライセンス文書を削除しない。比較基盤への登録と商用再配布の承認を混同しない。

音声例は通常は正式集合の公開許諾された英語例のみを保存する。過去のCIの2音声はLLSM2のテスト素材（CMU ARCTIC、unfaのFreesound 258342）で、元実装のREADME記載の出典を保持する。JVSの音声をこの追加によって自動公開しない。

## このPRの範囲

再合成・実行時間・既存指標の比較入口を追加する。属性操作、表現保存形式の共通化、距離学習、下流TTS学習、GPU、ストリーミングを新たに実装したものではない。推論からHTMLの保存・一覧生成までを動作確認するCIは削除し、CIは静的解析だけを行う。固定120録音全体の品質比較・MOS校正・方式採否は本来の研究として記録し、コードの動作確認には転用しない。
