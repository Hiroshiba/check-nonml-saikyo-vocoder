# 復旧後の新入力集合を取得前に固定する計画

旧全件manifestが失われたため、新しい契約と実際に生成されたmanifestのSHAで入力を確定する。旧VCTK126のSHA、旧trainのIDやhash、旧ASV proposalを再現したと仮定しない。reconstructed配下の回収原文は変更しない。この変更は取得・選定・入力保存用sourceの準備のみであり、音声取得、CSV取得、選定実行、推論、テストは未実施。多GB保存方針のユーザー回答前には本体を取得・実行しない。

## 入口と凍結順序

1. `scripts/all_metrics_datasets_contract.py train|vctk|human` はデータを取得せず、今回の規則・この計画・関係source SHAを新runの `corpora/selection-plans/<kind>.json` にfreezeする。trainは主評価の固定manifest SHAも含める。
2. 本体データを取得する前にこの契約が存在することを確認する。今回のtrain/CSV選定入口はダウンロード機能を持たず、後で正式に取得・SHA記録されたローカル原本を受け取る。VCTK/ASV音声取得入口はplanの完全一致確認より先に通信しない。
3. 索引・ラベルのSHAと選択したIDを固定した後に原音を処理する。選定に方式出力、特徴、指標、評定の大きさを使わない。
4. 一度freezeした規則・入力・sourceが変わった場合、同じrunへ上書きしない。失敗や想定数不足を除外済みの成功に変えず、理由と残る分母を報告する。取得失敗はスタックトレースを残す。
5. manifest/inputs/入力契約は新runだけへ保存する。原音バイトSHA、全長PCM SHA、抜粋PCM SHA、保存NPY SHA、source時間範囲を区別する。旧集計値は新runの実測として使わない。

## dev-clean：40話者各3録音の独立train

- 元データは公式LibriSpeech dev-clean。配布元: https://www.openslr.org/resources/12/dev-clean.tar.gz 。音声はCC BY 4.0。後日取得時に記録したarchive SHAを `--archive-sha256` で必須指定し、ローカル原本と照合する。
- 公式SPEAKERS.TXTでdev-cleanと表示される全40話者を使用。各話者のFLACを `SHA256((salt+'|'+speaker+'|'+member).encode('utf-8'))` のhex昇順、同値はmember順に並べ、先頭3件を選ぶ。saltは `all-method-metrics-dev-clean-recovery-20261014`。
- 候補選択のhash順と保存順は区別する。選択後のmanifestとinputsは発話IDの昇順で保存し、tar展開処理の順序は採否や保存順へ影響させない。
- 選択はID・索引・公式話者ラベルのみ。元音声の音量・音高・特徴・良否・指標を選択に使わない。選択した全120 IDを `selected-metadata.json` に固定してからデコードする。
- 入力は16 kHz mono PCM16、元長1秒以上、非ゼロパワー、有限、原音と先頭最大6秒抜粋のフルスケール近傍率0.1%以下。選択後の条件検査で失敗したら差替えず停止。120/40を縮小して学習しない。
- 主test-clean120の元発話ID・話者・入力ID・圧縮原FLAC SHA・全長PCM16 SHA・抜粋float64 PCM SHA・NPYファイルSHAとの重複を拒否。train内の同一音声hashも拒否する。
- schemaは `schema_version:1, split:'dev-clean', selection_rule, selection_inputs_sha256, entries[120]`。entriesには `id, speaker, source_utterance_id, source_member, source_sha256, source_pcm_sha256, excerpt_pcm_sha256, sample_rate, source_samples, excerpt_start_sample, excerpt_samples, input_npy_sha256` 等を保存。inputsは同じ順序の `id, speaker, path, sha256, samples, sample_rate, metadata`。
- 出力先 `RUN/corpora/readout-train/`。特徴標準化と読み出し学習の規則は `all-method-features-plan-recovery-2026-10-14.md` に従う。evalで尺度・alpha・選択規則を変えない。

## VCTK：既知GOLF test7話者各18録音

- 公式VCTK 0.92: https://datashare.ed.ac.uk/handle/10283/3443 、CC BY 4.0。配布済みwav48_silence_trimmedのmic1、48 kHzを使用。
- 話者はp360/p361/p362/p363/p364/p374/p376の7人に固定し、各18録音。GOLFの既知train/validationを外すだけで、全方式について未知話者とは保証しない。
- ZIP内のFLACファイルのuncompressed_bytesが大きい順、同値はSHA256(salt+member)、さらにmember順。saltは旧規則と同じ `all-method-metrics-vctk-20261014/`。これはFLACファイルの符号化後サイズに依存する選択であり、PCM標本数や録音長の厳密な順序ではない。
- 原音のみの条件: mono PCM16 48 kHz、3秒以上、有限、原音/抜粋の非ゼロパワー、abs(x)>=1-1/32768の率0.1%以下。適合候補を順に18件選ぶ。候補順、採用/除外理由、原音hashを保存。取得エラーを品質除外に置換しない。
- 抜粋は先頭からmin(原長,10秒)。原FLACを全長保持し、追加無音除去・正規化なし。抽出時点でのsource/crop PCM SHAとWAV SHAを保存する。
- ZIP索引の実SHAを本体取得前の契約へ追加する。126 IDとsource SHAが一意、話者集合が指定7人で各18件を必要とする。
- `vctk126.json` の新実SHAを入力契約へ固定する。8秒未満/以上の件数は新manifestのsample数から数える。旧102/24は埋め込まない。一般推奨8–10秒より広い3–10秒群であり、8秒以上の実候補数を補助層として別記する。
- 集計は行のcase/method/speaker/契約一致と実測値の有限実数を検査する。実有効話者が2未満なら区間はnull、実bootstrap回数は0とし、要求2000回を実行済みと扱わない。

## ASVspoof2019の既存声同一性評定：ラベル先行選定

- 公式研究CSV: https://raw.githubusercontent.com/nii-yamagishilab/ASVspoof2019-LA-human-assessment-data/master/score_similarity.csv 。原本版をSHA256 `63f173185694582e60610e35c66f58a63ccc85f02114bc8675cbadcc612d21d5` で指定。これは公式入力CSVの版固定であり、旧proposal/出力manifestとの一致要求ではない。
- 音声: https://datashare.ed.ac.uk/handle/10283/3336 。原音ODC-Byを評定CSVへ流用しない。CSVの別ライセンスは未確認。内部研究利用に限り全文CSV・listener ID・実験PDFを公開しない。
- `all_metrics_human_data.py selection --csv <取得済み原本>` と `audio` を分離する。旧REVIEW directoryとproposal hashは不要。
- CSVのbonafide対のみ、対内distinct listener2名以上。target2候補以上とnon-target2候補以上を持つB anchorのある全B話者を対象に、各B話者1anchor・カテゴリ各2A録音を選ぶ。
- saltは `asvspoof2019-bonafide-human-v2-multirater-20261014`。h(text)=SHA256((salt+'|'+text).encode('utf-8'))のhex昇順。speaker:ID、anchor:B.wav、candidate:B.wav:A.wavを使い、カテゴリ順target→non-target。選択時はscore列を参照せず、カテゴリ、録音ID、話者、distinct listener数のみを見る。
- 84対・105独立録音・28実話者・21anchor/21 B話者を事前の成立条件として要求する。不一致なら音声取得/特徴抽出前に停止し、評定値を見て集合を変えない。
- 選択ID/人数を `label-selection.json` にfreezeしてから評定値を読む。個人内反復平均→distinct listener等重み対平均。全trial平均も補助保存。公開0–9をshiftせず保持する。新しい人間評価・復号MOSとは扱わない。
- `selection.json` は新plan hash、ラベル先行manifest hash、原CSV hash、実counts、pairs、録音/話者対応を持つ。後続音声取得はこれを必須にする。
- 音声は選択した録音IDに対応する公式lossless FLACの全長、16 kHz mono。先頭6秒crop・無音除去・正規化をしない。CSV IDと配布FLACの対応であり、ブラウザー再生PCMとの独立照合を済ませたと主張しない。
- 特徴距離は別dev-clean train120の固定尺度を使用。元話者の声同一性の既存判断との一致を調べる補助群であり、一般的な音色距離・自然性・総合品質の正解とは呼ばない。
- 文献: https://doi.org/10.1016/j.csl.2020.101114 、https://doi.org/10.21437/Interspeech.2019-2249 。

## 今回まだ行っていないこと

planをfreezeする入口自体も未実行。選定IDの確定、元データの取得、PCM条件検査、hash disjoint確認、105/126/120件の成立確認はすべて将来の正式処理であり、sourceを用意しただけで成功とは扱わない。今回は静的Ruffと独立レビューに限定する。
