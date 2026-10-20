# 固定候補BF stage1：全3 ownerの保存数値artifact独立監査

## 結論

数値保存artifact側はstage2への採用条件を満たす。unique4180件すべてmatched_noncertified、欠測0、重複attempt0、保存数値診断の不整合0。owner0/1/2は1394/1393/1393件で承認indexと一致する。

ただし外部終了・manifest完全性・資源・receipt採用条件の全体判定は別担当の確認を必要とする。この監査はBF真誤差の認証でもstage2起動許可でもない。

対象 `/workspace/shared/pitch-fixed-bf-results-review-20261020/{owner0,owner1,owner2}` と承認index。候補import/実行/tests、BF/exp/log/LSEの再計算はしていない。保存十進文字列のDecimal読取・差・比較、整数条件、件数/最大値の監査のみ。

## input/source対応

各ownerのprovenanceは source SHA `035680bb789c45729d6cf54aa0d2cf491cf438f517ea2f8550e0b9a3a6f11197`、index SHA `da1c9a665be12767773bcef15c1376cdea780f82ad4b0135065338c99edf600d`、input ZIP SHA `2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d` で一致。保存source manifest自体のSHAも一致し、numerics.pyは承認済8188 bytes/SHA `0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065` を指す。

journalはunique_idをキーとしK/rを全eventに重複埋込しない。固定indexへjoinし、K整数1..10、owner=id mod3、r_bits/r_hex/整数比、finite 0≤r<1を確認した。owner外のledger行はunattempted/attempt0/counter0を維持。全uniqueの成功集合は0..4179と完全一致。

## 六値とgate

全4180件でpoint_start→50桁A/Q/L→80桁A/Q/L→point_doneの順序、各六値の一意性、有限十進文字列、stage/owner境界、Q extensionの0からの連続順序、最後のQ progressとQ valueの文字列/診断完全一致を確認。

保存reference_spread、laplace_precision_differenceは非負かつ≤1e-9。保存A50/Q50/A80/Q80文字列からのspreadとL80−L50の絶対値も独立にDecimal差で≤1e-9を確認。新しいBF評価や許容閾値変更はしていない。

| 診断最大値（保存値による） | owner0 | owner1 | owner2 |
|---|---:|---:|---:|
| 四参照文字列spread | 9.1382544831e-10 | 9.4449947647e-10 | 9.0160127423e-10 |
| L50/80文字列差の絶対値 | 6.8726170628e-48 | 6.8484810383e-48 | 6.6666589346e-48 |
| A series tail log | 9.5688246898e-10 | 9.8776627133e-10 | 9.4007301276e-10 |
| Q tail log | 5.3284814824e-11 | 5.3023840305e-11 | 5.3451328588e-11 |
| Q error log estimate | 1.0936047788e-52 | 1.0971864438e-52 | 1.1016808025e-53 |

A routeは元index整数比による分岐と一致。positive_seriesのtail_ratio≥0、0≤last_ratio<1、tail_log≤1e-9、finite log partial/tailを確認した。実消費項数から最後のnを読み、Q_n<1の整数不等式も確認した。beta routeはfinite log incomplete beta、内部反復/tail欄は仕様どおりnull。r=0 routeは今回現れない。

Qは正のscaled_H、非負error/tail、finite L/U/scale/tail log、L<U、非認証tailラベルを確認。最終tail/errorの両log gate≤1e-9。Lはfinite modeと正のcurvature。中間Q extensionは未収束値を保持する正当な過程であり、各中間値のgate合格を要求していない。

## 直列化による差の扱い

保存A/Q precision difference、採用delta/raw_delta、spread、L precision differenceは、元内部mp値から差を計算した後に直列化される。一方、監査で先に直列化された六値を引き直すと最終桁が一致しない場合がある。

最大差異は約9.8285688827e-48。各入力文字列の最終桁単位から得た直列化余裕内で整合を確認した。これは1e-9 gateの緩和ではなく記録照合の丸め幅である。六値から得たspread自身にも元1e-9 gateを適用している。採用deltaと同名raw_deltaは原文字列のまま完全一致する。stage2で保存L80/A80を引き直した値と旧raw_deltaをexact一致へ強制してはならない。

## counterと完全性

全eventでcounterが非負整数、同key内単調、series≤100000、quad≤200000。両精度・全extensionでresetなし。point_doneと最終ledger counterが一致し、counters_complete=true。

- 最大series累積: owner0/1=34、owner2=32。
- 最大quad累積: 全owner9532。
- primaryはquadを増やさず、series routeだけ明示項counterを増やす。betaは明示series counter0。Qはquadだけ、Lは両counter不変。全件整合。
- A route件数は六値のうち50/80のA単位で owner0:series122/beta2666、owner1:122/2664、owner2:120/2666。unique件数と混同しない。
- 全Q最終extensionは0/1/2のいずれか、64回拡張上限内。

incomplete-beta内部反復は計数対象外でNone記録。counterの低さを特殊関数の全内部計算量が小さいという保証には使わない。

## 解釈の限界

matched_noncertifiedは固定参照・精度・tail/error推定gateの合格であり、A/Qの真値誤差≤1e-9証明ではない。科学的な新odds/三差分布/平均等は集計していない。stage2では引き続き全owner外部証拠・完成pins・別開始指示が必要。音質・VUV・全grid・exact再追跡の改善は示していない。

機械可読監査（journal/ledger SHA、owner別件数、閾値、エラーリスト）:
`/workspace/shared/pitch-fixed-bf-stage1-numerical-artifact-audit-20261020.json`
