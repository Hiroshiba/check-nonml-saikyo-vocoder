# 既存方式の比較

現在の作業ベース「Apron」は固定LLSM2 Layer1です。比較ID `llsm2` は引き続きLayer0です。Layer1の固定120音声評価は未実施で、`--include-current-base` の正式測定は後工程です。

## 対象と目的

WORLD（Harvest）に加え、FACodec v1、HiFi-Glot、GOLF-ff、SiFi-GAN、LLSM2 Layer 0、MagPhaseを標準の既存比較対象にする。DACはオプショナルで、`--include-dac` を指定したときだけコード・重みの取得と計測を行う。原音は正解参照であり方式数に含めない。自作ベースを良いものと前提にせず、既存方式への全置換も検討できる比較にする。

この節の既存方式比較はPR #28・#29当時の経緯です。保存結果はその時点のベースと条件を保持します。

## 実行

検証対象はLinux x86_64、Ubuntu 24.04、CPU。uv、Python 3.12（本体）、Python 3.10（uvが隔離環境へ取得）、git、gcc/g++、make、CMake、SPTK 3.9が必要。初回取得時は通信する。実際の推論はHugging Face/Transformersをオフライン設定にし、未取得のモデルを推論中に探しに行かない。

```sh
uv sync --locked
sudo apt-get install build-essential cmake sptk
bash scripts/setup_references.sh
uv run --locked python -m vocoderbench.corpus fetch
uv run --locked python -m vocoderbench.reference --output runs/references-120
```

実行入口は `python -m vocoderbench.reference` です。旧PML専用の `vocoderbench.benchmark` は退役しました。現在の作業ベースを併記するときだけ `--include-current-base` を指定し、固定LLSM2キャッシュを `--runtime-cache` に渡します。

DACを含めるには準備と計測の両方に指定する。DACが失敗しても他方式の結果を残すが、明示選択された方式の失敗なので終了コードは非0となる。

```sh
bash scripts/setup_references.sh --include-dac
uv run --locked python -m vocoderbench.reference --include-dac --output runs/references-with-dac
```

部分実行では `--methods facodec golf` のように指定する。選択しなかった方式を完了件数に含めない。登録の一覧は `--list-methods` で通信せず表示できる。隔離環境の場所は準備・実行とも `--runtime-cache /absolute/cache` で合わせる。

正式比較では100音声以上と自動MOSを必須にする。2音声の動作確認専用経路と `--smoke` / `--no-mos` は削除した。CIでは推論を実行せず、キャッシュ付き静的解析を行う。音声はコーパス取得コマンドで先に準備する。推論と評価は別環境で実行するため、本体のtorchやnumpyを旧版へ下げない。

## 保存・再開・失敗

`contract.json` に入力PCM、実装、重み、依存版、選択方式、帯域、seed、スレッド数、評価方法を固定する。同じ出力先で条件が変わっていれば拒否する。成功した合成は再開時にスキップし、`--retry-failed` で元の失敗JSONを履歴へ保存して失敗だけ再試行する。評価の部分記録も `evaluation_partial.json` に原音・方式ごとに逐次保存する。再開時は条件記録のSHA-256、入力PCM・生成波形のSHA-256、標本化周波数・言語・発声様式が一致する評価だけを再利用する。完了した音響評価・MOSは再計算せず、未評価分だけを進める。音響のみの再実行でも同じ波形のMOSは消さない。失敗した評価は `--retry-failed` 指定時だけ再試行し、元の行を `evaluation_history.json` に残す。原音のMOSも同じ扱いにする。

`--stage acoustic` は合成・音響診断、`--stage mos` は保存波形の評価、`--stage report` は保存結果の再表示。未計測のMOSを0点にはしない。全体は `--stage all`（既定）。`--stage acoustic` の後に `--stage mos` を実行すると、保存済みの音響評価は再利用し、未評価のMOSを追加する。再開直後に中断しても、まだ巡回していない行の途中評価を削除しない。1方式の準備・推論失敗で他方式を消さず、スタックトレースをログへ保存する。`--timeout` は方式のワーカー全体の上限秒数。長い集合には増やす。初期値は3600秒。

`native/方式/` に未調整の全長生成波形（npy）、出力ハッシュ、解析秒数・合成秒数・出力長差・ピークを残す。`logs/` にワーカーとネイティブ警告を残す。`results.json`、`summary.json`、`index.html`、`audio_samples.json` が比較の結果。表のRTFは単回推論の集計で、前回のウォームアップ付き5反復速度試験そのものではない。

### Git・Pagesへの保存

`runs/` に出力しただけではGitにもPagesにも残らない。結果を比較PRへ含めるには、次を実行する。

```sh
uv run --locked python -m vocoderbench.references.publish \
  --source runs/references-120 --topic reference-methods \
  --title '既存7方式の固定120音声比較'
uv run --locked python scripts/build_site.py
```

保存先は測定開始日（日本時間）の `experiments/YYYY-MM-DD/reference-methods/results/run-NNN/`。元のHTML・JSONはバイト列を変えずコピーし、`publication.json` に各SHA-256と保存日時を記録する。`experiment.json` の一覧登録日時は元の `generated_at` を保持し、過去の測定を新規実験に見せない。既存のrunを上書きせず、同一の測定結果を重複登録しない。CIから復元する場合は `--provenance 出典.json` で元の実行ID・成果物ID等を追加できる。

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

新しい比較の音声例は正式集合の公開許諾された英語例のみを保存する。過去のCI結果にある2音声はLLSM2のテスト素材（CMU ARCTIC、unfaのFreesound 258342）で、元実装のREADME記載の出典を保持する。過去結果の再表示・保存では当時の範囲と帰属を維持する。JVSの音声をこの追加によって自動公開しない。

## このPRの範囲

再合成・実行時間・既存指標の比較入口を提供する。属性操作、表現保存形式の共通化、距離学習、下流TTS学習、GPU、ストリーミングを新たに実装したものではない。固定120録音全体の品質比較・MOS校正・方式採否は研究実験として記録する。CIの推論、DAC未取得の自己検査、HTML再表示・保存・一覧生成の予行は削除した。正式比較と結果保存のコマンドは維持する。

評価の再開処理を修正する前の条件記録とはソースSHAが異なるため、旧実行先へ上書きして再開しない。修正後の実行は新しい出力先を使用する。過去に公開したHTML・JSONは変更しない。再試行履歴は結果保存コマンドでもコピーする。


## 現ベースを併記する正式レポート

`--include-current-base` を指定すると、測定時の `BASELINE.json` のHNM v3を標準7方式と同じ固定集合・合成seed 0で測る。入力は現ベースが対象とする16 kHzに限る。`BASELINE.json` は変更せず、新方式の採用とは区別する。DACは引き続き明示選択だけで、今回の正式比較には含めない。

```sh
uv run --locked python -m vocoderbench.reference --include-current-base \
  --output runs/formal-hnm-v3-reference-120
uv run --locked python -m vocoderbench.references.publish \
  --source runs/formal-hnm-v3-reference-120 --topic formal-hnm-v3-references \
  --title 'HNM v3と既存7方式の固定120音声比較'
```

新しい `study_role: current_base_and_references` のときだけ、公開コマンドは正式ベース情報を許可する。測定契約のベース・比較相手・方式・seed・入力件数を照合し、通常の `existing_references` に自作ベースを混ぜない。準備の取得元・失敗と修復・ログhashを含む `preparation.json` も存在すれば保存する。過去のHTML・JSONを表示のために再生成しない。

HTML冒頭を、予測音質・明瞭性・スペクトル、帯域・包絡・音量、変調・F0推定整合性・振幅上限の目的別表に分ける。平均と同一録音での「各方式−HNM」差、有効/予定・対比較可能/予定を併記する。予測MOSは原音を含む全長ネイティブ波形、音響補助値は方式ごとの原音との16 kHz共通先頭区間で、対象を混ぜない。生成長差・全長一致件数・原音と出力の被覆率の最小/平均も表示する。短い出力の末尾は補助値に入らず、対応差・区間推定でも比較区間の違いは残る。

対応差の95%区間は、配布元の男女属性内で話者を復元抽出し、その話者の全有効録音対を保持する2000反復の百分位bootstrap（seed 20261012）。録音等重みを維持し、話者情報が欠落、または有効話者が2人未満なら区間は算出しない。多重比較補正はなく、再利用した開発集合での記述的な区間であって知覚品質優越の確証ではない。配布属性F/M別の集計も示すが、声から性別を推定せず、属性の因果効果とは解釈しない。

詳細表とJSONには既存のスペクトル窓別・帯域別・包絡窓別・変調帯域別・音量・低エネルギー区間などの保存指標、および全表示指標の欠測理由を残す。F0は未知の真値との誤差ではなく推定整合性で、有声の測定数と併読する。振幅上限割合は16 kHz共通区間由来、ネイティブ全長ピークとは区別する。RTFは単回解析・合成の録音間中央値であり反復速度測定ではない。合成seed 0の今回と、従来の8 seed音響研究を混ぜない。原音の自己音響比較は追加しない。

管理権限がない環境では、SPTK 3.9を配置済みのディレクトリを `VOCODERBENCH_SPTK_BIN` で明示できる。未指定時のdpkgによる通常取得経路は変わらない。今回の準備ではDebian公式SPTK 3.9-3をローカル展開し、CMake 3.31.10はPyPIから導入した。固定条件・対象外は[正式比較の調査記録](../research/formal-reference-comparison-2026-10-13.md)に記す。
