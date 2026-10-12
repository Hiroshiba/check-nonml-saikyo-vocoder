# 既存人間評定の重複台帳：資料・学習経路の確認

2026-10-12。**校正は未実施、未見の人間評定付き波形はまだ確保できていない。** 本書は取得済みUTMOSv2コードと一次資料から、次に照合するファイルを特定した台帳である。軽量の公開評定テキストと学習呼出元を追加取得した。音声アーカイブの取得や重い推論は行っていない。資料を列挙した件数を、波形照合済み件数や校正標本数に数えない。

対象の評価器は `fusion_stage3`、fold 0、実装commit `cc2700db57bb83ee13dc31ebe1b868c254e15d09`。重みはrevision `506474f2b33dc77c234d668cc419be1861899cad` の `fold0_s42_best_model.pth`、SHA256 `c8149d988e4bbf3f347e6966b5d769de347a5f8c59ffca1dc4bd4bf5b8585e57`。モデル条件は[自動MOS評価](MOS.md)を参照する。

## 集合単位の台帳

| 聴取実験・元データ | 確認できた重複・分割 | 学習・選択との関係 | 手元のファイルと未見性 |
|---|---|---|---|
| BVCCの元の統一MOS実験 | 固定実装 `get_data()` は `train_mos_list.txt`、`val_mos_list.txt`、`test_mos_list.txt` を結合する。元のTESTSETという名前を保持しても、そのままモデルの保留集合にはならない | `spec_only`、`ssl_only_stage1/2`、`fusion_stage2/3` がすべて `use_bvcc=True`、`external_data="all"`。fold 0の具体的な学習・検証IDは未復元 | 学習リスト・個別評定・BVCC波形は本作業のローカル `data/` と `.cache/` の検索では未発見。波形単位の学習使用有無は不明。独立校正には数えない |
| SOMOSの元のMOS実験、split1/clean | 固定前処理はtrain/valid/testのMOSリストを結合し、ファイル名末尾から方式IDを作る | 上記各段階の外部データ候補へ入る。元のtestの所属だけでは未見でない | アーカイブ・3つのMOSリスト・波形hash未取得。fold 0への実際の所属は不明 |
| Sarulabの追加MOS実験 | `VMC2024_MOS.csv` の発話IDからBVCCの前処理済み波形を参照する。評定が新しくても波形は別資料にならない | 各段階の外部データ候補に含まれる。dataset名と方式ID接頭辞を変えても、BVCC側と同一波形のfold跨ぎを防いだ証拠にはならない | 公開元は平均・95%区間・1〜5の回答度数・総数を示す。個別リスナーIDまで利用可能とは未確認。公開評定テキスト3610行を取得・集計済み。BVCC元リスト未取得のため集合間照合は未実施 |
| VoiceMOS 2024 Track 1の検証・評価用再評定 | 主催者論文はBVCCと同一16 kHz波形で、評定だけ新規と明記。検証は上位50%由来、評価は上位25%／12%由来 | 新しい公式zoom-in学習評定は配られず元BVCCの評定利用が案内された。ただし今回の配布モデルには別のSarulab再評定の経路もある。競技時の提出モデルと今回の `fusion_stage3` を同一学習履歴と断定しない | `val_list.txt`・`eval_list.txt`・公式評定・匿名ID対応表未取得。再評定への適合確認候補にはなるが、未見波形への独立検証とは扱わない |

BVCCの由来は[主催者のデータ案内](https://sites.google.com/view/voicemos-challenge/resources)、2024の同一波形と分割は[主催者論文2.1.1節](https://homepage.iis.sinica.edu.tw/papers/whm/new-7510-F.pdf)、Sarulabの評定形式は[作者README](https://github.com/sarulab-speech/VMC2024-sarulab-data)で確認した。Track 2/3をTrack 1の学習資料とまとめていない。

SOMOS配布元は、単一のLJ Speech声による20,000合成発話と100自然発話、評定・信頼性情報、方式・聞き手・文を分けた70/15/15の元分割を説明する。しかしUTMOSv2の再結合後に元分割の独立性が維持されたとはいえない。また単一声なので、多話者への一般化を測る資料にはならない。[SOMOS v2配布説明](https://zenodo.org/records/7378801)

## 学習段階と判定できない境界

固定した[再現手順](https://raw.githubusercontent.com/sarulab-speech/UTMOSv2/cc2700db57bb83ee13dc31ebe1b868c254e15d09/docs/reproduction.md)では、音声枝のstage1→stage2、スペクトル枝、融合stage2→stage3という順序になっている。最終foldだけを調べても前段の重みへの利用は除外できない。表の「学習候補へ含まれる」は設定・前処理の確認であり、すべての波形がfold 0の勾配更新に使われたという断定ではない。

固定設定は5分割、`sgkf_kind`、dataset別、方式IDでグループ化、MOS整数値で層化を指定する。追加取得した固定 `train.py` の呼出元まで静的確認した。`get_train_data()` は再現モードでデータ取得・前処理を行い、`split_data(cfg, data)` の返値を `data.iloc[train_idx]` と `data.iloc[val_idx]` へそのまま適用する。一方 `split.py` の `sgkf_kind` はdatasetごとの部分DataFrame内の位置indexを、元DataFrameの位置へ変換せず結合している。この経路は複数datasetの局所indexを全体indexとして扱う問題を含み、別dataset間で同じ整数indexが学習側と検証側に現れ得る。方式単位分割の設定だけでは実際の独立性を保証しない。

これは固定公開コードを読んだ所見であり、配布checkpointがこの経路・入力順で作られたとの実証ではない。実際の入力行順、欠測除去、学習時commit・引数、保存fold一覧が未取得なので、具体的な学習／検証の重複件数や未見リストは未確定とする。コードを修正して再学習したモデルにすり替えることもしない。

論文は検証foldの方式単位SRCCでcheckpointを選び、5fold×5抽出の平均を評価している。この検証集合はモデル選択に使われるため、勾配更新に未使用でも、完全に未使用の最終検証とは異なる。本プロジェクトのfold 0×1抽出を論文の成績で校正済みとは呼ばない。また論文は提出モデルと比較実験モデルの学習手順の差も述べる。[UTMOSv2論文3.5〜4.1節](https://arxiv.org/html/2409.09305v1)

wav2vec2のLibriSpeech自己教師あり事前学習と、MOS評定による学習は別の欄で記録する。今回のLibriSpeech test-cleanが前者に含まれるかはコーパス名だけでは断定しない。今回のHNM再合成波形に既存人間評定があるわけでもない。

## 手元で確認した固定ソース

ローカル基準位置は `.venv/Lib/site-packages/utmosv2/`。以下は2026-10-12に読み取った実ファイルのSHA256である。参照した実装のURLは[固定commitのutmosv2ディレクトリ](https://github.com/sarulab-speech/UTMOSv2/tree/cc2700db57bb83ee13dc31ebe1b868c254e15d09/utmosv2)。インストール来歴 `utmosv2-1.3.1.dev0.dist-info/direct_url.json` は上記commitを指定し、そのファイルSHA256は `94fb3700e7fbf09d57a9484ec8c49f13bd27af66a13ebc4ec35ac8a1bc3e3892`。

| ファイル | SHA256 |
|---|---|
| `utils/_task_dependents/initializers.py` | `07573ebdd7be372d39bfe614ba7a638b9c353edd0970b2cac68dc9335f38f984` |
| `preprocess/_preprocess.py` | `0a86d0d9e0ec7210e1375d33775b38c4752fe088c551389f72207dfbbd3aaeae` |
| `utils/_pure/split.py` | `7bec87d6d2a89b8943cd1edda602d91d20d5b43cf4684b075023a41c49048ba4` |
| `config/spec_only.py` | `42814110a090b590712c65934e2d0e8a8fe364b917c9ddf094a28240a6934c33` |
| `config/ssl_only_stage1.py` | `3e98f812732f3f91235559f741c642fab37f4870b3c3a0f2b2494ca05c1f76ab` |
| `config/ssl_only_stage2.py` | `f395f05995893754e2009032f03129e5c801d9a364dca444fbeec4bd92a1aa9a` |
| `config/fusion_stage2.py` | `cc13ecc5217ffad0036d3bfa8bcd8d52e525470285f4a8bcc90255425b9554dd` |
| `config/fusion_stage3.py` | `9e30618e51ddbcf77cb2d3bbd66e3f194833c06f3141abb626ba385eb38f1c05` |

取得済みなのは評価器のコード・最終重み・音声前処理設定であり、学習データ全体の実行台帳ではない。今回は配布checkpointから学習波形一覧を読み出せたとは主張しない。

## 軽量metadataの実査結果

[固定train.py](https://raw.githubusercontent.com/sarulab-speech/UTMOSv2/cc2700db57bb83ee13dc31ebe1b868c254e15d09/train.py) は4015 bytes、SHA256 `48a7f71ee5886a041bb64fa48e2d0a45d16d180e932e4ebfe0fc530c9f65c237`。CLIの分割seed既定値42と、上記の行選択を確認した。作業資料はリポジトリ外の `../mos_metadata/train.py` に保存した。

[Sarulab公開評定](https://github.com/sarulab-speech/VMC2024-sarulab-data/tree/9c2c4b28eecb55e91ee8de382a336d6879a5763b) をcommit `9c2c4b28eecb55e91ee8de382a336d6879a5763b` で固定した。

| 原ファイル | bytes | SHA256 |
|---|---:|---|
| `VMC2024_MOS` | 296019 | `40e8ebd725e53065dee160476701a7fb7b866bc7f1d89097299f79014d173d83` |
| `README.md` | 1204 | `e7e1bb84b019286da296ad91a0c328fbd539484a0499c39de16041d6b61f2fb7` |
| `LICENSE` | 1071 | `ddefd7cc91936715d038865d38d5ada0cd42d31916a2583f121dfa94242de76d` |

評定本体は3610非空行・3610固有発話ID・重複ID 0・95方式ID。全行が8回答で総回答数28880。全3610行で回答度数の和が総数と一致し、度数から再計算したMOSが記載値と一致した（許容差0.0000005）。これはテキスト内の整合性確認であり、3610個の独立した未見波形を確保した意味ではない。BVCC側のID一覧未取得のため、集合間の一致／不一致件数とPCM重複は未集計。原文・revision・集計は `../mos_metadata/sarulab-*` に保存した。原文には聞き手ごとのIDを含まず、回答度数から個人別評定履歴を復元しない。

[BVCC公開配布](https://zenodo.org/records/10691660) は `main.tar.gz`（表示288.0 MB、公開MD5 `ba4b896801282ca0eae37b9fd81ed94c`）、`ood.tar.gz`、採点プログラムを示す。BVCC mainのmetadataのみを分離した公開ファイルはこの入口では確認できず、音声を含むmainアーカイブは取得していない。SOMOSも4.0 GBの `somos.zip` のmetadata単独経路は未確認。大容量アーカイブをmetadata取得と称してダウンロードしない。

## 次に確認するファイルと順序

新規の大容量取得を始める前に、次の順でmetadataを揃える。上記の軽量資料以外は取得未実行。権限や通信が拒否されたものは迂回せず、入手できたmetadataまでで「不明」を保つ。

1. 固定ソースの呼出経路は上記まで確認済み。次は配布モデルの学習ログ・保存fold一覧・前段重みのfold対応を探し、公開コードの静的所見と実際のcheckpoint来歴を区別する。再学習はしない。
2. [公式配布入口](https://www.codabench.org/competitions/2650/)でBVCC mainのmetadata単独配布の可用性を確認する。Zenodoの `main.tar.gz` の存在は確認済みだが取得していない。必要な内部ファイルは `main/DATA/sets/{TRAINSET,DEVSET,TESTSET,train_mos_list.txt,val_mos_list.txt,test_mos_list.txt}`、`main/DATA/mydata_system.csv`。名称は固定再現手順の期待配置であり、現配布アーカイブの中身を展開確認済みという意味ではない。元分割・発話・方式・評定・聞き手欄を列の意味とともに保存する。登録が必要な場合、登録できたと仮定しない。
3. Sarulab原文の取得と単独集計は上記のとおり完了した。次はBVCC側の一覧を入手して集合間照合する。公開本体名には `.csv` がない。実装が期待する `VMC2024_MOS.csv` へ変換する際は、変換規則・原文hash・派生hashを残し、度数や総数を捨てない。BVCC発話IDとの一致・不一致を全行集計する。別dataset接頭辞を同一波形IDとして正規化した副台帳も作る。
4. SOMOS [v2](https://zenodo.org/records/7378801) の配布ファイルは `somos.zip`、表示4.0 GB、公開MD5 `bdfde4cae256549dfab05d713136e4af`。まず配布metadataとZIP目録の閲覧可否を調べ、`training_files/split1/clean/{train_mos_list.txt,valid_mos_list.txt,test_mos_list.txt,TRAINSET,VALIDSET,TESTSET,train_system.csv,valid_system.csv,test_system.csv}` の可用性を確認する。metadata単独取得経路は未確認であり、存在を仮定したURLは作らない。後の音声取得時に原アーカイブSHA256も記録する。
5. VoiceMOS 2024の `data/DATA/sets/val_list.txt` と `voicemos2024-track1-eval-phase/DATA/sets/eval_list.txt`、それらに対応する公式評定・匿名ID対応表を取得する。2つのリスト名は固定再現手順で確認済み、評定ファイルの現在の名称は未確認。25%・12%は重なるので二つを独立1000/500件として合算しない。Sarulabと公式評定を同じ聴取実験として結合しない。
6. metadataが揃ったら、波形未取得の段階でも `listening_experiment_id, original_split, utterance_id, system_id, speaker_id, listener_count, rating_source_sha256, stage, fold, usage` の行を作る。実行時の学習／検証所属が不明な欄をnullとして残す。保存fold一覧・ログが配布されていなければ、その欠落も台帳に記録する。
7. 波形取得後は元bytesのSHA256に加え、サンプルレート・チャネル・サンプル数・復号PCMのhashを記録する。容器違いだけで別波形にせず、逆にリサンプルや切出しを同一PCM扱いにしない。推論に渡したfloat32 hashは別列へ置く。段階・foldを跨ぐ同一PCM群を照合してから、未見／学習使用／選択使用／不明を確定する。

この3系列はすでに学習・モデル選択・同一波形再評定との接点が見つかっている。最初の用途は重複の監査と再評定条件の違いの確認である。独立校正用には別系列の既存聴取実験も調べる必要があるが、名前が別というだけでは未見としない。評定対象の元波形を切り直したりHNM処理した結果へ元MOSを付け替えない。未見資料の確定後にだけ固定評価器で誤差・順位・高品質域・欠測分母を測り、そこで初めて校正結果として報告する。
