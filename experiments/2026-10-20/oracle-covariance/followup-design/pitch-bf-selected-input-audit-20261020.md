# 固定候補入力bundleの読取監査

2026-10-20。対象：`/workspace/shared/pitch-bf-selected-input-review-20261020`。

## 0. 結論

納品bundle内部のファイルハッシュ、309frame/6180候補IDの完全性、value/hex/binary64 bitsの整合に不一致は見つからなかった。固定2周波数×K1..10の保存cod/logBFによる、将来の部分集合BF比較に必要な字段は存在する。

ただし、反事実計画の適用には次の重要な限定がある。

1. `prediction_prior` は旧Aの更新前H1無条件joint予測質量であり、static priorでもfiltered posteriorでもない。
2. `initial_prior_payload` はframe0以外では帳簿用zero。local対照に各frameのこの字段を使ってはいけない。同条件frame0の保存初期値を参照する。
3. 旧Aの `prediction_prior` 自体に2056個の保存zeroがある。205frameでは片方の周波数の全10次数がzero。そこでは有限なBF補正だけでその周波数を復活させられない。
4. 元NPZ/JSON・source本体はbundleにない。producerが主張する元NPZとのbit一致は独立再確認していない。
5. MAP追加点は0。今回の計画実施範囲に補助MAP評価を含めない。全grid、VUV、自己整合的なexact再追跡は依然対象外。

今回行ったのは標準ライブラリと読取コマンドによるJSON/ハッシュ/bit表現/ID/保存zeroの監査だけ。候補コードの実行・import、BF評価、r再計算、新しいodds計算、科学計算tests、新測定、Git変更、外部送信は行っていない。packageは変更せず、この監査文書だけをpackage外へ保存した。

## 1. 転送とbundle内部の完全性

親からの転送確認：

- ZIP: 958799 bytes。
- SHA256: `3818e41f4780be5a6ed0e86c5cc1d40b70a1093b7d3cd9edb4320f93b579c0f6`。

ZIP自体のこの検証は親担当の報告として記録する。本担当は展開済みbundleを監査した。

bundleは11ファイル。`extraction-manifest.json` が列挙する自己以外の10ファイルについて、実bytes数とSHA256を再照合し全一致。主要ファイル：

- selected.jsonl: 5809411 bytes、SHA256 `545007f3557d9e6ebab78aed3a60dddd3c7e7e8f5b9f4fb75a1e068d8b8e5645`。
- frames.json: 378229 bytes、SHA256 `0e84f914c74ab196e4c4c13cdd0bd3f40e642e0b2d1e6f398c37040d8dbd52dc`。
- source-references.json: 114858 bytes、SHA256 `976f6d73fa5ab3c5a6f89a16ac6ce36a2707db64d3dd89e1b7fc49e4b2122cd9`。

これは納品内容とmanifestの内部整合確認であり、manifest自体が元実行の正しさを保証するという意味ではない。

## 2. IDs・候補軸・字段の確認

### 2.1 実際のJSONレコード

- frames.jsonは309件、(condition,frame_id)の重複なし。
- U-U/E-U/E-Eの各frame0..102が完全に存在。
- selected.jsonlは6180件、(condition,frame_id,f_index,K)の重複なし。
- 各条件2060件。各frameでf_index48/148×K1..10の全20候補が存在し、欠落・余分なIDなし。
- f_index48→fixed_row0→97.65625 Hz、148→row1→195.3125 Hzの対応が全件一致。
- Kは1-based。f_indexは0-based。NPZ軸ラベルそのものは未添付なので、意味は同梱FIELDS/configの対応契約に依存する。

候補valuesは全レコードでJ、fit、cod、logBF、prediction_prior、initial_prior_payload、transition_term、memory_termの8字段。MAP専用レコードなし。

### 2.2 元NPZのshape/dtypeとの区別

inventoryは、元309NPZに共通のfloat64[2,10]のJ/fit/cod、float64[461,10]のlogBF/prediction_prior/initial_prior等を報告する。今回直接確認したのはその選択抽出JSONの20候補/frameであり、元NPZのdtype/shapeを独立再読取したのではない。

JSON自体にNumPy dtypeはない。binary64表現の一致を確認したことと、元NPZファイルとのbyte一致は別の証拠である。

## 3. value / hex / bitsの整合

selectedとframes内のbits_beを持つ全57147オブジェクトを走査した。

- 有限値57027個：十進JSON valueをbinary64へ読んだbits、float.hex表現を読んだbits、保存bits_beの3者が全一致。
- 非適用120個：3条件×初回20候補×T/R2字段。status=not_applicable、元bitsはNaNを表し、value/hexは付いていない。
- transition_term/memory_termの非適用はframe0だけ。その他の6120件/字段は有限値表現。
- J/fit/cod/logBF、prediction_prior、initial_prior_payloadは各6180件すべて有限値表現。
- logBF以外の監査対象候補字段に負値は見つからなかった。

これは保存されたbinary64の表現保持確認であり、元数学的真値に対する精度、BF実装精度、rの式の正しさを評価していない。J/(energy+.002)、fit=J/energyは再計算していない。

sourceの範囲外停止契約と「演算別clip/mask/丸め履歴が未保存」は両立する。履歴がないことを、全セルの演算過程を独立確認済みと読み替えない。

## 4. priorとH0の意味：計画へ必須の反映

### 4.1 prediction_prior

FIELDSによれば、当該更新に用いた旧AのH1無条件joint予測質量P(H1,f,K|旧履歴)。F0またはKのmarginalではなく、H1内で条件付き正規化された質量でもない。20セル抽出時にsubset再正規化されていない。

対応するH0予測質量はframes.prediction_h0。モデル上はH1全461×10セルとH0の組で正規化されるが、bundleには20セルしかないので全状態質量和を独立確認できない。今回、質量和や新しい正規化・oddsを計算していない。

名称は「旧A prediction prior固定」とし、「filtered posterior固定」「static prior固定」「exact方式の予測prior」と呼ばない。

### 4.2 initial_prior_payload

初回3×20=60件ではinitial_prior_applied=true、prediction_priorと同一の保存値。後続6120件はinitial_prior_applied=false、正のzero bits `0000000000000000`。

この後続zeroは帳簿上の非適用payloadであり、local priorの質量zero・候補支持zeroとは違う。既存local対照を行う場合は各条件frame0の保存initial値を全時刻で参照する。各frameのpayloadをlogへ変換したり、zeroから支持を判断しない。

### 4.3 transition_term / memory_term

定義はT=.7 AᵀPB、R=.4 h Mの選択値。個々には正規化priorではない。frame0では非適用NaN。今回T+Rを再計算してprediction_priorと比較していない。memory_termには2772個の保存zero、transition_termには2056個の保存zeroがある。

### 4.4 H0字段

framesにあるのはprediction_h0とlocal_h0。local_h0は旧local計算のH0であり、予測H0やfiltered H0の代用ではない。framesにはfiltered_h0字段がない。元inventoryがfiltered_h0を列挙することは、選択bundleにその値が含まれる証拠ではない。

pair条件付き比較にはH0の正規化項は不要だが、全状態posteriorやVUV評価にこのbundleだけで進めない。

## 5. 保存zeroによる反事実比較の制約

保存prediction_priorの厳密なzeroは2056/6180セル：

- U-U: 980。
- E-U: 503。
- E-E: 573。

全10次数がzeroの固定周波数/frame群：

- U-U、f_index148：frame5..102、98frame。
- E-U、f_index48：frame46..52、7frame。
- E-U、f_index148：frame60..102、43frame。
- E-E、f_index48：frame46..102、57frame。

合計205群。両周波数群が同時に全zeroのframeは0。両周波数に少なくとも一つの正prior次数が残るframeは104。これは保存値のzero/support監査であり、BFやoddsの新計算ではない。

### 計画上の帰結

旧Aの保存priorを厳密に凍結する限り、全zero群は有限なexact BFへ置換しても質量zeroのまま。そこで有限のpair log-odds補正を差分計算すると∞−∞等の未定義を作り得る。有限補正の比較対象と、zeroに固定される対象を別ラベルにする必要がある。

周波数内K分布wやc=logΣw expΔは、その周波数群の旧重み総和が正の場合にのみ定義する。全zero群を一様Kへ救済しない。片側全zeroのframeでもセルBF差の評価自体は将来可能であり、prior固定の退化を近似誤差ゼロと取り違えない。

zeroが数値underflow由来か構造的除去かについて、演算別履歴はない。Gaussian遷移等の契約からの推測を全セルの確定原因にしない。保存zeroへfloorを足したり、T/Rから高精度priorを作り直したり、旧log状態Bのpriorを暗黙に使うのは別条件であり今回の範囲外。

同じsubsetの初期prior対照はこの履歴依存zeroと積分近似の影響を分ける一助になるが、exact trackerの復元ではない。

## 6. frame metadata・支持・cleanラベル

framesの支持分類はpadding9、boundary9、first_complete144、second_complete147。各条件ではpadding0/1/102、boundary50..52、first_complete2..49、second_complete53..101に対応する。

center_sample、support_start/end_exclusive、support_class、time_secondsは同梱inputs.supportsと全frame一致。complete_suffix_observation_equalityの49行について、U-U/E-Uの対応observation SHAがframesと一致した。これは記録されたハッシュの照合であり、観測波形を再読取して同一性を独立検証したのではない。

clean_minimum_period_f0はclean合成波形の最小周期ラベル。境界/paddingはnullで、noisy波形や生理的真F0のラベルではない。BF比較の対象存在と、精度正誤ラベルがあることは別。

producer inventoryは全309件validと報告する。一方、今回のframesにはobservation_status/state_updated/skipped等の原字段は含まれない。全候補の保存値がfiniteであることは独立確認したが、元実行のskip/update過程を同じ粒度で再監査できたとはしない。

## 7. source/config/原本参照の来歴

source-referencesは635件で、309NPZ、309frame JSON、receipt/result等のJSON、入力/観測6NPY、source3py、契約1md等のpath/bytes/SHA参照を含む。framesの全source_json/source_npzが参照表に存在し、condition/frame番号と整合。producer絶対pathへのアクセスや取得は行っていない。

inventoryのsource_artifact_sha256とsource-referencesに共通する記録は整合。同梱inputsの3条件metadataもinventoryと一致。

SOURCE_MANIFESTのうちrun.py、measurements.py、EXECUTION-CONTRACT-ja.md、model.pyのhashはsource-references側の対応記録と一致。PROPOSAL、pyproject、summaries、storage、PACKAGE_MANIFESTはSOURCE_MANIFESTの記録はあるが同名のsource-references項目はない。これらを不一致とはせず、参照表との二重照合がない範囲として扱う。

主な凍結記録：

- model.py: `111c5bfda62595a3b5f01208741fc52303dc78c2569d9dbc889b399244c95955`
- run.py: `852c6faf72398e196b1ce969a974739ba94c4eb56a48f38d0b9504b4ae81d3fe`
- measurements.py: `0319b0b559654db6e9ec5bef51790f07756605cb140ef90f04586dc41a19e8ab`
- EXECUTION-CONTRACT-ja.md: `55ca4288bf6805a380ba7b54b5584dcb8b97d6ea90efa12e035611eb65b4c43d`

configはFS16000、N400、hop160、FFT16384、q52..512、K1..10、VAR_SPEECH5e−6、固定index48/148を記録。分母専用保存fieldはなく、式としてenergy+N×VAR_SPEECH。δ=3はこのinventory.configの直接字段ではないため、既存correspondence文書の固定source確認を来歴とし、本bundleから独立にsource実装を再検証したとはしない。

SOURCE_MANIFESTのprepared_not_executed/scientific_run_started=falseは準備時記録。後の保存成果が存在することとの時点差を無視して「未実行bundle」と判断しない。一方、producerのsource_unchanged/binary64_exact_source_match=trueも検証報告であり、元source/NPZ本体がないconsumerが独立証明したものではない。

## 8. 既存反事実計画への修正指示

既存 `/workspace/shared/pitch-fixed-candidate-counterfactual-plan-20261020.md` 自体は今回変更しない。適用時には次を上書き限定する。

1. 主prior字段を旧A prediction_priorと確定し、更新前joint・無条件H1質量と明記する。
2. local対照は同条件frame0のinitial_prior_payloadを参照。後続payload zeroは使用禁止。
3. 全zero周波数205群と両群positive104frameを区別し、有限log-odds補正やK分布の定義域を明記する。zeroを回復する計算を追加しない。
4. 309frame/6180固定候補は抽出上完全。MAP補助点は未納品なので除外する。inventoryのEU55例を追加の観測として流用しない。
5. 全grid配列、filtered_h0、原skip/update字段、原NPZ/sourceは未添付。全grid/VUV/再追跡の禁止は維持する。
6. 元NPZとのbit一致はproducer確認、bundle内value/hex/bits一致は本監査確認、と証拠の主体を分ける。

これらは科学モデルの採用変更ではなく、保存字段を誤用しないための適用条件の明確化である。別途スカラー参照検証が完了しても、それだけで本bundleへのBF評価を実施済みとはしない。

## 9. 完了点

保存字段の内部整合と意味の読取監査を完了。入力破損を示す不一致は見つからなかった。主な留保は元NPZとの独立同一性確認がないことと、旧A予測priorに多数の保存zeroがあること。BF値、cod、odds、posteriorは新しく計算していない。
