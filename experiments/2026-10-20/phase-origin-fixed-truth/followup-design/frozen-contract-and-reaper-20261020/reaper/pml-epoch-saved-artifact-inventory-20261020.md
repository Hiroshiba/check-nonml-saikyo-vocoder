# PML公開保存物の限定棚卸し：REAPER観測の参照

2026-10-20 12:11–12:17 UTC。GitHub connectorで確認したmainは `7ff437a4d2652947118c26c331f31a5607798a3d`。公開manifest、来歴、再現手順、保存schemaを静的に読んだ。原音解析・再実行・候補import・tests・音声処理・Git変更はしていない。PML維持、PR67変更なし。

## 結論と範囲

**説明用経路には合成側traceの保存参照・部分的な派生データが残る。一方、今回読んだ公開manifest／説明JSONではraw_f0 traceやREAPERの元5戻り値の保存参照は未発見。** 正式package評価の公開native解析driverと1録音CLIはtraceを要求しない。この契約を説明用artifactにも一律に当てはめてはいけない。

これは全環境での不存在証明ではない。Library、実行環境の非公開run、全履歴、全研究branchは調べていない。圧縮結果本体を展開して全nested項目を走査したわけでも、旧mechanism HTMLの埋込みデータ全体を調べたわけでもない。参照が見つからないので、新規計測による復元には進まない。

調査対象は次の範囲：

- `research/pml-package-evaluation-2026-10-16/` のartifact/input manifest、provenance、REPRODUCE。
- 対応する `scripts/pml_evaluation/run_native.py`、native-driver-provenance、report生成時の保存schema。
- `vocoderbench/pml_cli.py`、PMLParameters/storage、`docs/PML.md` の統合CLI1例。
- `research/pml-kernel-pathway-2026-10-19/` のmanifest、README、mask-counts、observation-data、earlier-row419-data、Stage Bのsource-array-hashes/source-evidence/observation-contract。
- `experiments/2026-10-18/transient-envelope-pathway/` のmanifest、analysis-results、measurement-provenance、summary、waveform-results/display-data、band-observations、baseline-provenance-comparison。音声本体は読んでいない。
- 補助的に旧 `research/pml-fwcep-2026-10-16/artifact-manifest.json` の参照名のみ。

以下のリンクはすべて上記commitに固定。Git blob SHAとmanifest記載のファイルSHA256は別種のhashであり、混同しない。SHA256は記載値の引用で、今回全実体を再hashした値ではない。

## 公開artifactと列

1. [正式artifact-manifest.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-package-evaluation-2026-10-16/artifact-manifest.json)
   - Git blob：`c1acbd8c9e8a6e4cf0dbe7c7b12cc3fb6a4d1f0d`。
   - schema_version=1、scope、filesの各要素はname/bytes/sha256。27項目は短WAV、HTML、入力・来歴・一覧JSON、圧縮結果等。raw_f0、pm_times、pm、corrの独立ファイル参照はない。通常`.pml`やnative recordそのものもこの公開manifestにない。
2. [input-manifest.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-package-evaluation-2026-10-16/input-manifest.json)
   - Git blob：`f048426289955601929741299ea75030e13766b5`。manifest記載SHA256：`1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193`。
   - casesにはid/speaker/cohort/common_samplesとinputのsample_rate/excerpt_start_sample/excerpt_samples/sha256/bytes/path。これは入力NPYの識別で、REAPER観測配列ではない。
3. [provenance.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-package-evaluation-2026-10-16/provenance.json)
   - Git blob：`8d3f699747159a4737bbd732ec8b289136f73209`。manifest記載SHA256：`de5ad945bcdd930c7b36faa0b50921c39256b920f1c575fc1f70b0a6691b6998`。
   - top-levelはsource_files/package/runtime/native_contract/quantization_contract/mos_reuse/publication。source_filesは元集約・契約ファイルのbytes/hash。例えばnative-contract.jsonのSHA256は `8163d533b228a15b438b3ab0cd4703f45e29375dd774d5cf2a435645cc851ea1`。raw_f0や元REAPER配列への参照は未発見。依存のpyreaper表記やsource hashは観測配列の保存を意味しない。
4. 圧縮結果の公開参照：
   - `results.json.gz`：1,421,561 bytes、記載SHA256 `d696fef04c7268d0b8256eadb7040e283cd0fdb0d6b7c48232835afe9640c7c9`。
   - `quality-raw.json.gz`：4,683,378 bytes、記載SHA256 `6f9404e925a21f50d8e6e947c041679df88e93ba147a1d4434a4f4e9f6695c7f`。
   - [builder 179–211行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/scripts/build_pml_package_report.py#L179-L211) では前者はquality/native/timing/edits/readout等の保存集約、後者はavailable-comparisonの品質個票を保持するschema。`quality-raw`のrawはREAPER raw_f0という意味ではない。schema上に元REAPER5配列をまとめる項目はないが、今回圧縮実体の全内容まで不在認証していない。
5. [旧探索artifact-manifest.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-fwcep-2026-10-16/artifact-manifest.json)
   - Git blob：`b0b7045a0f3369c29b6aec77087db1979ea2d367`。独立raw_f0/REAPER戻り値の参照名は未発見。
   - `saved-results.json.gz` の記載SHA256は `906c18d6e366c6768dfd3f4cf44a907b7363b00cfbec5c079b6a743aeead0d50`。この圧縮実体とmechanism HTMLは今回の内容走査対象外で、内部に関連図や派生系列がないと断定しない。

## 解析・保存schemaで残るもの

[run_native.py 99–125行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/scripts/pml_evaluation/run_native.py#L99-L125) は `encode(x,16000,seed=0)` にtraceを渡さない。`native/{id}/parameters.pml`、`wave.npy`を保存し、record.jsonには入力識別、audioのpath/hash/samples/fs/bytes/peak/over_one_samples、payloadのpath/hash/bytes/bytes_per_second/frames、各計時を記録する。元REAPER5配列もraw_f0 traceもschemaにない。

[REPRODUCE](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-package-evaluation-2026-10-16/REPRODUCE.md) はそのrun出力を説明するが、各record/payloadが公開manifestに含まれるという意味ではない。[native-driver-provenance](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/scripts/pml_evaluation/native-driver-provenance.json) は測定driver SHA256 `22bdacdef9dab941dfd1c0f0f1e1573f4ec86285de89ba37e46b05da0196765b` と可搬公開driver SHA256 `79ded7fc92c76a0c8d1cd14a22fe93f38071423ddbab37fa85b450ddcce233ea` を区別する。公開driverを読んだことを過去実行全体の認証にしない。

[storage.py 16–34行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/storage.py#L16-L34)（Git blob `3a9b80c16540d243cec4dad4cb21ef88263993e1`）はF0 `<f8`、FWCEP `<f4`、bit-packed noise_maskと固定メタデータだけ。raw_f0、epoch/VUV/corrは含まれない。ここでのF0は後処理済みの正の合成clockである。

## 1録音CLI

[pml_cli.py 47–67行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml_cli.py#L47-L67)（Git blob `63366f466eaa20e80de1f6dbe3db58e89513ec76`）もencodeにtraceを渡さない。出力`.pml`と任意timing JSONだけで、JSONはanalysis_seconds/analysis_rtfまたはdecode_seconds/decode_rtf、method/seconds_audio/measurement。raw_f0保存オプションはない。

[docs/PML.md 46–50行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/docs/PML.md#L46-L50) の説明用1例は録音ID・6秒・計時・payload bytes等を記述するが、raw_f0やREAPER5戻り値のpath/hashを提示していない。この1例に対応する独立trace公開manifestは今回未発見。上述の正式評価短音声を、このCLI1例の同一artifactと推測してはいない。

## 1録音の説明用artifact：部分保存あり

### Kernel pathway

[mask-counts.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-kernel-pathway-2026-10-19/mask-counts.json#L401-L418) は、元 `replay-trace.npz`（103,600 bytes、SHA256 `833c94a61f905178ea964675b505cc207861b38fbd2334f0cd248039e051ee60`）と `kernels.npz`（25,870 bytes、`975416351f0b48005f7aebc0c8469f66a46a510c76c33d49e4d4558f163ca0c1`）への来歴参照を保持する。公開JSON自体のmanifest記載SHA256は `85df031c2ba4c0c0ee8f92600e731b464b16c7add2be25cd1bce138fda3b8810`。列はcondition/sampling、maskの0・中間・1のbin数、band別集約、source hash等。これはraw_f0 countではない。元NPZ名は今回のGit treeに見当たらず、その内部列は未確認。

[Stage B source-array-hashes.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-kernel-pathway-2026-10-19/stage-b/source-array-hashes.json#L162-L177) は9条件のcapture配列名・dtype・shape・bytes・SHA256を公開する。`M`、kernel、spectrum、`pulse_f0`、`pulse_times_s`、source_cell_index、window境界等がある。condition-01のpulse_times_sはfloat64[14]、112 bytes、`85382ebd117421d7b35075b6ee4e13f726edf46d4496071b1e478399f0a68bb2`、pulse_f0はfloat64[14]、112 bytes、`d4f35af15b8ed2e6feb68aad55777f7384b42399ee1227e839cbc309474efa03`。JSON自体のmanifest記載SHA256は `cfc0ad525987ab59d612bc0e84c6d69e503250e1f580d9fad235240e626e99ee`。これは配列の値全体ではなく識別情報であり、名称と既存契約が指すのは合成clock。REAPERのpm_timesではない。

[observation-data.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-kernel-pathway-2026-10-19/observation-data.json)（manifest記載SHA256 `496097cc5f8bcfdcdded886081f246361521df9092557dc46c88723feca4f93a`）には録音121-121726-0012・pitch +3・seed 0、pulse index 442–448と対応frame index、kernel support、既存power集約・一致gateが残る。`full_trace=passed` は当時の検証記録であって元REAPER5列が公開された証拠ではない。[source-evidence.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/research/pml-kernel-pathway-2026-10-19/stage-b/source-evidence.json) にcapture hash参照もあるが、raw_f0/pm_times/pm/corrの保存列は今回未発見。

### Transient-envelope pathway

[analysis-results.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/experiments/2026-10-18/transient-envelope-pathway/analysis-results.json)（291,535 bytes、manifest記載SHA256 `11b7d4bf07bc084e120fbad8b4858be5d293359eec826586a8aadb0b414d62ed`）にはvariantごとのframe、time_s、effective_f0_hz、ideal_window_end_s、band power等がある。[summary.json](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/experiments/2026-10-18/transient-envelope-pathway/summary.json)（SHA256 `87c7c38407210591ef0c2bdb1918a102c3485c7b64e48c2bbe1ecadba13575dd`）のfixed_f0は元StoneMask F0をvariant間で固定したとの説明で、REAPERの未加工F0を意味しない。

band-observationsにはtimes/band_powerとregion集計、waveform-display-dataには派生差分とsource hashが残る。measurement-provenanceのpml_input_sha256は `131e720fd96d9619a67580d1dbf6728285453c3a75112dbbb053f9d84771736c`、analysis-resultsのobservations_sha256は `7d51596613e6e6d1920b6f9e376e5950a38fe2cfa64051b1eaa3cb5272b96738`。入力・観測のhash参照だけから元観測ファイルの全列や現所在は判定できない。この範囲でraw_f0時系列や元REAPER5配列の保存参照は未発見。

## 停止点

今回の公開範囲では、再解析なしで使える原epoch/VUV/corrの保存参照は確保できなかった。ただし合成traceのhash参照と部分的説明データは存在し、「trace全般が保存されていない」とは結論しない。元NPZや未加工raw_f0が他の環境に残る可能性は否定しない。もし既存ファイルを今後提示されるなら、その保存schema／来歴を読むことが次の最小確認であり、hashだけから復元しない。raw_f0のF0 sentinel復元とepoch/corr復元は別問題である。新規計測・追加保存実装・現在phase studyへの追加は開始しない。
