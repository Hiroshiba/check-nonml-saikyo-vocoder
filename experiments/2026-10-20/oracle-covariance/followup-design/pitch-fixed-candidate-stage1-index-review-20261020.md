# 固定候補BF stage1：indexの独立照合

2026-10-20。対象：`/workspace/shared/pitch-fixed-candidate-source-review-20261020/` のadapter/index/reviewと3ZIP。照合元：`/workspace/shared/pitch-bf-selected-input-review-v1-20261020/`。

## 判定

**indexと保存入力の対応に阻害誤りは見つからなかった。**

6180参照→4180key、K/cod bits、旧logBF、A/B行番号、static初期priorのframe0参照、309frameの対応、owner1394/1393/1393、旧1080との交差0を全件照合した。3ZIPと展開ファイル、各manifest、入力17ファイルpinも整合した。

これはindex・保存値・来歴の静的確認であり、実行全体の承認ではない。workerの資源制御、排他claim、実際の停止/reap、gate動作は別担当のレビュー・将来実行の対象。候補sourceを実行/importせず、tests、BF/rの再計算、exp/odds、波形処理は行っていない。

## 1. 固定版とmanifest

### ZIPを直接読取して展開内容と照合

- index ZIP：462946 bytes、SHA256 `6db5cb216f629d37fcf06774dad6a541c9dffbd34663b4e61a4e6c3ecfa7ee1c`。13ファイル、内容一致。
- adapter ZIP：23869 bytes、SHA256 `b934bd61b3785372707c32af5bbd9af286700a161100dac2abeabfdfb4d8da35`。12ファイル、内容一致。
- review ZIP：61438 bytes、SHA256 `6133cbd0ee33f563b6a362e85ba638c6d1c25544ae1d5e0b44d82bd384e53c99`。18ファイル、内容一致。

ZIP内のファイル名は各package root相対。実際のmember集合と展開先集合も一致し、余分な実ファイルは見つからない。

### 各manifest

- SOURCE-MANIFEST SHA256：`2a9f8d7e59d283831acff16cd5d3d63bc7a6094005148a6d13bc42e0402b2ec9`。自己以外11ファイルを照合。
- INDEX-MANIFEST SHA256：`da1c9a665be12767773bcef15c1376cdea780f82ad4b0135065338c99edf600d`。自己以外12ファイルを照合。
- REVIEW-MANIFEST SHA256：`25a2ecacce11fdd9965d2a0d7c5175b25a42f12c8eec3d3798a3db88d41dba55`。自己以外17ファイルを照合。

全列挙ファイルのbytes/SHAと集合が一致。review/PACKAGE-PINSのsource/index hashと、adapter/CONFIGのindex hashも実manifestに一致する。

input-pinsは既定v1 Library/file、1213332 bytes、ZIP SHA `2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d`を指定。入力17ファイルのbytes/SHAを元v1実ファイルへ全件照合し一致した。元入力ZIP全体の転送検証は既存親監査を参照し、本担当の今回の確認は展開入力とpinの照合である。

## 2. unique.json：4180key

元selected.jsonlから保存Kとcod.bits_beだけを読み、key集合と各keyの元行参照を照合した。J/energyからrを再生成していない。

- 4180行、unique_id0..4179の連続順。
- (K整数, unsigned big-endian r_bits整数)の辞書順と一致。
- 各行のK/r_bits/r_hexが元保存codに一致。
- ratioは元binary64のexact整数比表現と全件一致。これは保存値の表現照合であり、rの科学式の再計算ではない。
- owner=unique_id mod3が全件一致。
- owner件数は0:1394、1:1393、2:1393。
- reference_idsの逆対応は元keyに属する参照行と全件一致。
- multiplicityは1参照2180key、2参照2000key。余分な参照・参照の取り落としなし。
- saved_logBF_bitsは各keyの元保存値と一致。同key内の異なる旧logBF bitsは0。

同じkeyの値を共有できることは、同じpriorやposteriorを共有できることを意味しない。unique indexは元condition/frame/frequencyの参照を消していない。

## 3. references.json：6180参照

各reference_id=0..6179について次を確認した。

1. condition/frame_id/f_index/Kが元selectedの同じ行に一致。
2. A_selected_line_1basedが元A行を正しく指す。
3. B_selected_line_1basedが同じ候補IDのB log_prior行を指す。
4. unique_idがその候補のK/cod bitsに対応する。
5. ownerがunique ownerと一致。
6. unique側reference_idsに同じreference_idが含まれる。
7. static_A_selected_line_1basedが同condition・frame0・同f_index/Kの行を指し、initial_prior_applied=trueである。

特にstatic参照は後続frameの帳簿zeroへ向いていない。

元AのF0Hz/fixed_rowとも照合し、f_index48→97.65625Hz/row0、148→195.3125Hz/row1が全件一致。Kは元の1..10で、zero-based列番号との取り違えは見つからない。

## 4. frames.json：309frame

元v1 framesの各字段を全行で比較し、一致を確認。energyのvalue/hex/bits、時刻・支持、cleanラベル、observation SHA、元source path等をそのまま保持している。

追加frame_indexは0..308で元frameに対応。各frameのreference_idsは同condition/frameの20候補と正確に一致する。

B_frame_indexは同condition/frameの元B frameを指し、時刻、support_class、observation_statusが一致。元Bの全309frameはvalid。

A_prior_source/B_prior_sourceの説明はそれぞれ元A prediction_prior、元B log_priorを参照しており、元BF値と別履歴priorを区別する計画と整合する。ただしこの静的index照合だけで、将来stage2が正しくlog重みを扱うことまで検証したわけではない。

## 5. 旧1080支持とoriginコピー

previous-1080-support.jsonは既存union source-reviewのSUPPORT-PINS.jsonとbyte一致。SHA256は
`9f16ecf3ac2fed8c5366d2547459770706ba3a86827492e3f01613ba014ce688`。

旧1080 unique `(K,r_bits)` と新4180keyの交差は0。数値結果の取り込み、最近傍値の使用、支持の再生成はしていない。

origin-source-references、origin-B-provenance、origin-SOURCE_MANIFEST、origin-B-SOURCE_MANIFEST、origin-inputs、origin-environmentの6ファイルは、元v1の対応ファイルとbyte一致した。

元NPZ本体は今回も未同梱。元NPZとのbit一致はproducer監査の記録として扱い、consumerの独立再照合とはしない。

## 6. sourceとの最小整合

review/build_index.pyは読取のみ行い、実行しなかった。保存bitsによるgrouping、unsigned整数順、owner mod3、元A/B/static行参照、frame20候補対応を構成する内容は、今回独立照合した実indexと整合している。

adapterのCONFIGにはN400/δ3/K1..10、50/80桁、1e−9 gate、point累計100000/200000、owner1394/1393/1393、attempts_per_key=1、stage2_implemented=falseが記録されている。

source/numerics.pyは承認済みv2原本とbyte一致。8188 bytes、SHA256
`0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065`。
CONFIGのkernel pinも一致する。

この確認は数理kernel不変の証拠であり、wrapperが実行時に担当外を評価しないことや資源上限を守ることの実測証拠ではない。その運用部分は別レビューへ委ねる。

## 7. 完了点

新しい入力間違い・index blockerは見つからなかった。今回の範囲では固定版の保存入力→unique→reference→frame対応を支持する。

package/index/元入力は変更せず、レビュー文書だけを保存した。科学数値評価と実行開始は行っていない。
