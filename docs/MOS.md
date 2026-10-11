# 自動MOS評価

人による新しい聴取評価を行えないため、固定したUTMOSv2で**予測MOS**を測る。エンコーダー・デコーダーは非MLのまま、測定器だけに学習済みモデルを使う。値は新しい音声に対する人間の評定ではない。

## 最初に採用する測定器

UTMOSv2は、高品質な合成音声の自然性評定を扱うVoiceMOS Challenge 2024 Track 1で検証された方式である。[原論文](https://arxiv.org/html/2409.09305v1)では、発話単位・方式単位のMSE、相関、順位相関を報告している。今回の利用設定は論文の5モデル・各5回抽出の平均とは異なるため、その競技成績を今回の精度として扱わない。

選択理由は、合成音声に関する既存評定での検証、CPUで動く公式実装、現在のPython環境への導入可能性である。自作方式に良い点を付けるかどうかを見て選択しない。

| 項目 | 固定値 |
|---|---|
| モデル | UTMOSv2、`fusion_stage3`、fold 0 |
| 実装commit | `cc2700db57bb83ee13dc31ebe1b868c254e15d09` |
| 重みの配布元 | `sarulab-speech/UTMOSv2`、revision `506474f2b33dc77c234d668cc419be1861899cad` |
| ファイル | `fold0_s42_best_model.pth`、818,531,314 bytes |
| 重みSHA256 | `c8149d988e4bbf3f347e6966b5d769de347a5f8c59ffca1dc4bd4bf5b8585e57` |
| MOS実験の条件ID | `bvcc` |
| 計算 | CPU、4スレッド |
| 内部抽出の乱数 | 各波形で同じ `20261012` に戻す |
| 反復数 | 1。自然6秒・CPU4スレッドの初回実行18.74秒を確認し、比較結果を見る前に確定 |
| 無音除去 | 無効 |
| 実装と重みのライセンス | 配布元のMIT表記。ダウンロードした配布物はGit管理外 |

条件IDは、MOS実験間の評定バイアスに対応する入力であり、適用領域が一致した証明ではない。今回は初代HNMからWORLDまでを同じ条件で比較するため、`bvcc`へ事前固定する。結果を見て`bvcc`と`sarulab`を選び直さない。

## 入力と結果

自然音声、及び同じ自然音声を各方式で再合成した波形を測る。今回の正式集合はLibriSpeech test-cleanの英語通常朗読120録音（女性20話者・男性20話者、各3録音）で、原音を含む480波形を測る。通信制約により日本語60録音を確保できず、比較結果を見る前に集合を改訂した経緯は[固定コーパス](CORPUS.md)に残す。取得済みJVS 12録音は別の補助集合であり、日本語・ささやき・裏声へ正式集合の結論を一般化しない。評価APIはこれらの発声も探索的に測れるが、JVS・LibriSpeechの今回の再合成に対する独自校正は未実施である。人工正弦波、インパルス、人工雑音は音声自然性MOSの対象にしない。

- 各入力の原音、自作ベース、候補、WORLD（Harvest）の値と差を保存する。
- 正式MOS用の合成雑音seedは0に事前固定する。8 seedの音響測定とは分ける。MOSについて合成乱数を変えた場合の変動は未評価である。
- MOS値、処理失敗、対象外を区別し、失敗を0や他の指標で埋めない。非有限値も失敗として`null`と理由を保存する。
- 元の秒数、サンプルレート、実際に渡したfloat32波形のSHA256、言語、発声、計算秒数、抽出条件を各行へ残す。
- 初期化と推論の例外は、スタックトレースを含め既存のログへ出す。
- 個別の欠測と分母を残す。平均だけでなく言語・発声・話者別の結果も確認する。

UTMOSv2内部では16 kHzへ変換し、音声特徴の枝は3秒、スペクトルの枝は1.4秒の区間を抽出する。短い入力は公式実装に従って繰り返し延長する。入力秒数、枝ごとの処理長と延長回数を結果へ保存する。スペクトルの枝には複数区間の混合もあり、固定seedはこの処理の乱数も固定する。これらの反復は独立した人間の評定ではない。

評価器の内部にはレベル正規化を含む特徴計算がある。したがって予測MOSだけでゲイン操作やレベル保持の正しさを判断せず、波形側の音響測定を併記する。値を1〜5へ切り詰めて誤差を隠す処理は加えない。

## 導入と再現

`vocoderbench/mos.py`の`MosEvaluator`を使う。環境と依存は`pyproject.toml`及び`uv.lock`で固定する。CPU版のPyTorch、TorchAudio、TorchVisionを使い、学習やGPUを必要としない。現在の実行環境ではNNPACKの初期化が失敗するため、この高速化を無効にして通常のCPU処理を使う。C/C++の標準エラー出力もスタック情報とともにログへ記録する。

自然音声6秒・CPU4スレッドで、キャッシュからのモデル読み込み7.56秒、読み込み後の1件目4.74秒、同一モデルでの2件目3.52秒を実測した。これらは速度確認であり、反復数をMOS値で選ぶための比較ではない。モデルは一度だけ読み込み、`prepare()`の完了後に各音声を逐次処理する。

キャッシュは既定で`.cache/mos/`。`VOCODERBENCH_MOS_CACHE`又は`cache_root`で変更できる。重みの固定revision URLとSHA256を確認し、各実行の来歴にも残す。Gitには配布重みを入れない。

ライブラリを読み込む間と推論中は、一時ファイルの出力先もキャッシュ内の`tmp/`へ固定し、処理後に呼出元の設定を復元する。PyTorchが動的に生成するPythonコードを作業ツリーへ残さない。

公式の初期化は、最終重みに含まれている音声・画像backboneの学習前重みも別に取得する。今回の読み込みではその冗長取得を省き、公式のネットワーク構造を生成してから、完全な公式checkpointを`strict=True`で読み込む。構築用の置換は直後に復元し、公式の特徴計算と予測処理を利用する。依存バージョンを含む実行情報を記録する。

音声特徴の構造・前処理設定は、`facebook/wav2vec2-base`のrevision `0b5b8e868dd84f03fd87d01f9c4ff0f080fecfe8`に固定する。

| ファイル | SHA256 |
|---|---|
| `config.json` | `4937977e24d12d1bba70cdce8709c3c04807a8e4ae8ddac4229c48c436ae99ae` |
| `preprocessor_config.json` | `b225d617c025463b9e157e06afea8b90dc7078fc70b013c533328423e0486b4a` |

`MosEvaluator(cache_root=..., repetitions=1, seed=20261012, threads=4)`で生成し、`predict(waveform, sr, language=..., style=...)`から`value`、`status`と条件を受け取る。来歴は`provenance`にある。先に`prepare()`を呼ぶと、重みの取得と読み込みを独立して実行できる。

## 他の候補との比較

サイズは確認した配布物のサイズで、Python環境や追加の事前学習モデルを含めない。UTMOSv2以外は今回の環境での推論をまだ実施していない。

| 候補 | 合成音声との関係 | 確認した配布物・導入上の特徴 | 今回の判断 |
|---|---|---|---|
| UTMOSv2 | 高品質合成音声の既存評定で検証 | 1 fold約819 MB。公式実装が現在のPython環境に対応。MIT表記 | 最初に固定して導入 |
| UTMOS22 strong | BVCC由来のVoiceMOS 2022で検証 | 公式デモに約1.24 GBのcheckpointと約951 MBのwav2vec重み。fairseqなど旧依存を含む | 今回は未導入 |
| SHEET SSL-MOS | MOS-Benchの合成音声・通信等の複数領域で検証 | 現行WavLM large版のBVCC単独重み約1.26 GB。CPUが既定、入力16 kHz、MIT表記 | 独立した外部確認の次候補 |
| NISQA-TTS | 合成音声の自然性向け。16データ集合で評価した論文がある | 重み約1.24 MB。公式環境はPython3.9等の旧版。コードMIT、重みCC BY-NC-SA 4.0 | 通常NISQAと混同しない。今回は未導入 |
| TorchAudio SQUIM subjective | BVCCとDAPSで学習 | 公式表示約360Mの重み。16 kHz、別内容でもよい清浄参照が必要。重みCC BY-NC 4.0 | 参照選定を別途固定する必要があり今回は未導入 |

SHEETのモデルカードは、科学論文における聴取評価の完全な代替としては未成熟と明記している。どの候補でも、配布元の検証が今回のボコーダー劣化への検証になったとはみなさない。

## 既存の人間評定による校正に残る作業

現在の480波形には新しい人間評定がなく、原音の予測値を併記しても評価器の正しさは校正できない。次の作業は、既存評定とその対象だった音声を使い、今回と同じ固定設定で予測の誤差と順位を確認することである。以下は今後の測定手順であり、今回実施した結果ではない。

**最初に重複の台帳を作る。** [公式の再現手順](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/docs/reproduction.md)はBVCC・Sarulab Data・Blizzard 2008〜2011・SOMOSを使用する。[入力処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/utils/_task_dependents/initializers.py)はBVCCの元のtrain/val/testを結合し、[外部データ処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/preprocess/_preprocess.py)もSOMOSのtrain/valid/testを結合する。Sarulab評定はBVCCと同じ音声ファイルを参照する。したがって、元データの「test」という名前や評定実験名が異なるだけでは、配布モデルに未見とはいえない。

台帳には聴取実験、元データ集合、波形IDと復号音声のhash、方式ID、話者ID、評定人数、各学習段階・モデル選択への使用有無を残す。異なる名前で再配布・再評定された同じ波形も対応付ける。今回のfold 0だけでなく、その前段の音声・スペクトルモデルを含め、学習や選択との関係を確認する。照合できないものは「重複不明」とし、独立した検証に数えない。まず上記のデータ系列以外の既存聴取実験を候補にし、方式や話者の重複は波形の重複と別に示す。自己教師あり事前学習での音声利用と、MOS評定を使った学習も区別する。

**高品質域の順位を別に測る。** [原論文](https://arxiv.org/html/2409.09305v1)の高品質域の検討と、[公式の評価処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/utils/_task_dependents/metrics.py)の発話・方式別評価を踏まえ、全体のMSE・Spearman順位相関だけで終えない。今後の検証では、人間の評定に基づく上位25％などの範囲を予測前に定義し、その範囲での順位相関と方式間の順位正答率を併記する。順位正答率は人間評定差の大きさ別に示し、小差・同点・評定の不確実さが大きい組を明確な正誤へ押し込まない。高品質域を予測器自身の値で選ばない。

**信頼区間は独立性に合わせる。** 次の校正では発話単位の点数を独立標本として一括再抽出せず、方式への一般化は方式を、話者への一般化は話者を単位にした再抽出・保留で別に点検する。同じ文・話者・方式の対応は維持する。話者と方式が交差する資料では両方の依存を扱い、必要なIDや群数が足りなければ、その一般化の信頼区間は未算出とする。個別聴取評定がある場合は評定のばらつきも残す。フレームや全ペアの組合せ数で標本数を増やさない。この信頼区間の設計は本プロジェクトの今後の手順で、上記公式コードに実装済みという意味ではない。

**校正と探索を分ける。** 異なる聴取実験のMOSを共通の絶対尺度として混ぜず、実験ごとの順位・差・欠測分母を保存する。換算式を当てはめる場合、その当てはめに使った資料と評価資料を分け、未見資料でだけ補正後の成績を示す。評定の対象だった音声を切り直したり、自作ボコーダーで処理したりした結果へ、元の評定を引き継がない。予測MOSを符号化器の損失や波形・パラメータの直接探索目標にはせず、固定した候補の確認に使う。繰り返し見て候補を選んだ資料は開発用になったと記録し、以後は未使用の最終確認資料と呼ばない。

次に実行できる作業は、公開済みの評定音声候補について上の台帳を用意し、利用条件・波形入手可否・重複不明を整理すること。未見性を確認した後に、現在の固定モデル・条件ID・抽出seed・反復数で予測して、聴取実験別・高品質域・方式別の結果をHTMLへ追加する。今は新たなデータ取得や校正計算を行っていない。

## 調査した一次資料

- [UTMOSv2論文](https://arxiv.org/html/2409.09305v1)：方式、MOS実験の条件ID、既存評定データ、5 fold・5反復、結果を確認。
- [UTMOSv2公式実装](https://github.com/sarulab-speech/UTMOSv2/tree/cc2700db57bb83ee13dc31ebe1b868c254e15d09)：依存、設定、入力処理、モデル構築、推論を確認。
- [UTMOSv2推論ガイド](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/docs/inference.md)：条件IDと反復の意味を確認。
- [再現手順](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/docs/reproduction.md)、[入力処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/utils/_task_dependents/initializers.py)、[外部データ処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/preprocess/_preprocess.py)、[評価処理](https://github.com/sarulab-speech/UTMOSv2/blob/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2/utils/_task_dependents/metrics.py)：取得済みの固定commitを再読し、データ準備節、`get_data`、`_get_external_data`、`calc_metrics`を確認。元test集合の結合、同一波形の別評定、発話・方式別指標を確認した。個々の学習ファイル一覧は未取得で、重複なしの証明は未完了。
- [UTMOSv2配布重み](https://huggingface.co/sarulab-speech/UTMOSv2/tree/506474f2b33dc77c234d668cc419be1861899cad)：容量、LFS SHA256、MIT表記を確認し、fold0を実取得して照合。
- [UTMOS22公式実装](https://github.com/sarulab-speech/UTMOS22)と[公式デモ](https://huggingface.co/spaces/sarulab-speech/UTMOS-demo/tree/main)：使用対象、配布物、依存を確認。
- [SHEETモデルカード](https://huggingface.co/unilight/sheet-models)と[モデル一覧](https://wenchinhuang.com/sheet/pretrained-models/)：検証範囲、CPU利用、版の区別、限界を確認。
- [NISQA公式説明](https://github.com/gabrielmittag/NISQA)と[自然性評価論文の要旨](https://www.isca-archive.org/interspeech_2020/mittag20_interspeech.html)：NISQA-TTSとの区別、ライセンス、合成音声への評価を確認。
- [TorchAudio SQUIM subjective](https://docs.pytorch.org/audio/2.8/generated/torchaudio.pipelines.SQUIM_SUBJECTIVE.html)と[利用説明](https://docs.pytorch.org/audio/2.8.0/generated/torchaudio.pipelines.SquimSubjectiveBundle.html)：学習データ、参照要件、入力、重み条件を確認。

## 批評との往復

第1案では英語を主な適用先と考えたが、批評担当から、評価器に合わせて日本語を除くと目的から外れると指摘された。日本語・ささやき・裏声も探索的に測り、言語・発声別の集計と未校正表示を必須に修正した。

条件IDについても、BVCCを選んだだけで未見の音声への領域適合が示されるわけではないとの指摘を受けた。IDの固定は再現条件であり、英語を含む今回の再合成への独自校正は未実施と明記した。予測値・欠測分母・原音との対応・固定hashを残し、競技成績と今回の精度を同一視しない点で合意した。


正式比較は2個の独立プロセス、各4CPUスレッドで実行する。各プロセスでモデルを1回読み込み、発話内の原音・3方式を順番に処理する。入力ごとに同じ抽出seedを設定するため、タスクの実行順で乱数条件は変わらない。音声単位で結果ファイルを分けて書き込みを競合させず、初回ダウンロードの一時ファイルもプロセス別にして、同じSHA確認後に置換する。
