# 原入力・観測NPY回収の独立byte監査

2026-10-20。対象 `/workspace/shared/pitch-original-input-recovery-review-20261020/package`。

## 結論

**原観測の取得可用性はPASS。** 9 NPYが存在し、元inputs.jsonにSHAのある7件は一致する。3条件×103frameの全309観測row payloadは、既存selected frames.jsonのobservation_sha256と一致した。固定100履歴pairについても両条件row bytesが完全一致し、PAIRSのhashへ接続できた。

clean-U/E-blockの2件は元SHAがない。今回取得bytesとheaderは監査できたが、実験当時のclean bytesとの独立同一性は証明していない。この留保は原input/observation7件の確認を妨げない。

これはfullgrid再計算の開始・完了、統計量の新規取得、品質判断を意味しない。候補/source実行・import、numpy読込み、浮動小数点配列値のdecode、波形生成・算術・FFT・投影・J/r/BF・追跡は一切行っていない。

## 1. package / ZIP / inventory

MANIFESTの自己除外全ファイル集合・サイズ・SHAを独立照合し、一致した。ZIPの全ファイルmemberもpackage bytesと一致。

ZIP: `pitch-original-observations-recovered-20261020.zip`

SHA256: `89a3398cfd6cd300a039cb4a8927d46513e7a13393321468751f6d481d9bee2c`

inventory.csv全9行はinventory.jsonの対応字段と一致。各NPYのサイズ・SHA、version、header、data offset、payload長はinventoryから信じるだけでなく、実ファイルのbytesから確認した。

全9件がNPY1.0、dtype `<f8`、fortran_order=false（C順）、data offset128 bytes。

|分類|件数|shape|各payload bytes|各file bytes|
|---|---:|---|---:|---:|
|入力U-U/E-U/E-E|3|16384|131072|131200|
|観測U-U/E-U/E-E|3|103×400|329600|329728|
|noise-unscaled|1|16384|131072|131200|
|clean U/E block|2|8192|65536|65664|

標準ライブラリのheader literal読取と整数offset/長さ照合のみを使用し、array演算はしていない。

## 2. 元SHAとの接続

inputs.jsonの各条件 `/inputs/{condition}/sha256`、`observations_sha256`、`/noise_sha256`を実NPY全ファイルhashと照合して7件すべて一致。NPYファイル全体のhashとraw frame payloadのhashは別対象として扱った。

provenance/inputs.json、environment.json、SOURCE_MANIFEST.jsonは、以前から親が保有するselected v1の同名ファイルとbyte一致。producer-run.pyとresult.jsonは既存selected source-references.jsonの元path・bytes・SHAに一致した。

- producer-run.py: `852c6faf72398e196b1ce969a974739ba94c4eb56a48f38d0b9504b4ae81d3fe`
- inputs.json: `d4228d48c618046b37b0b793c66fd88cdd36c53ca108eee2eb41561480183977`
- SOURCE_MANIFEST.json: `2f2af39c185450830c6ba0f4f81b2e577c7542035c51159888dc6810823e0e09`
- result.json: `a6bccf9691f67fd21808ab6ca58574978a2584d2b2c3e7c8b65cc88dba201187`

resultのsource_manifest_sha256も上記source manifestに一致。保存statusesはU-U/E-U/E-Eすべてcompleted。SOURCE_MANIFESTのprepared_not_executedは作成時のsource状態であり、それだけで後続実行結果を否定する字段ではない。実行の来歴はresult等と区別して読む。

environmentは保存当時のPython3.12.14、NumPy2.3.5、SciPy1.17.0、thread数各1の記録であり、今回その環境を起動して再検証したものではない。

## 3. 全309 frameのpayload監査

C順103×400、little-endian float64なので、各rowはpayload中の連続3200 bytesとして切り出せる。各condition/frameの3200 bytesをそのままhashし、既存selectedのframes.jsonに記録されたobservation_sha256と比較した。

- U-U: 全103一致。
- E-U: 全103一致。
- E-E: 全103一致。

さらにprovenance inputs.jsonの保存support_start/end、left/right_paddingを使い、rowの非padding部分が対応input.npy payloadの同位置byte切片と一致すること、padding部分が規定長のzero bytesであることを全309で確認した。整数byte offsetの計算とbytes比較だけであり、窓を波形として再生成・計算したものではない。

これにより、以前はproducerの原hash metadataとsource説明に依存した観測同一性を、今回取得した実row bytesまで独立に接続できた。

## 4. 履歴対比100組への接続

承認v1 `pitch-history-contrast-source-review-v1-20261020/package/PAIRS.json` を参照。全100組で、左右conditionの同frame row bytesが完全一致し、そのhashがPAIRS.observation_sha256と一致した。

H50/C50、主要H49/C48とpadding3という固定集合は変更していない。padding102も含め、同一性を完全窓の結果から外挿せず個別に確認した。新たな対比値・割合・oddsは計算していない。

## 5. clean2件と確認限界

clean-U-block.npyの現在SHA:
`e44cd345e691f57c6bb27b1e8cc9430be3728f71b45fd805fd7ba0d61401da5f`

clean-E-block.npyの現在SHA:
`22841355f519efc12cc31d239993752e697d6bf7a5ab384e03ad45e74fc36df5`

両件はproducerにnp.saveの保存箇所があり、inventoryは元SHAなしをnullで正しく表現する。しかし「既知元directoryから複写した」というproducer報告と、実験当時の独立hashアンカーは異なる。現在のhashを過去の検証済みhashへ昇格しない。clean/noiseを足してinputを再構成する検査も行っていない。

consumer側元directoryの現在状態・複写前後不変は回収担当の報告であり、このshared監査から同じfilesystemを直接再確認したとはしない。

## 6. 今回確定できること

既存全grid J/rの保存不足自体は解消していない。一方、その不足を将来別の承認済み計算で扱う場合に必要となる**原raw観測309窓のbytesが、元実験とselected・履歴対比の来歴に一致する形で取得済み**であることは確定できる。

fullgrid統計の再計算・exact再追跡を始めるかは別の問い・別契約・別開始判断である。本監査は保存byte可用性の確認で停止する。
