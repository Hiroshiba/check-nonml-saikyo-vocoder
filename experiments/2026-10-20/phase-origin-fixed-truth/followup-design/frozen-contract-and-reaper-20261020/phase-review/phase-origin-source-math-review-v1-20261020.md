# Phase source v1：限定差分の独立数理再レビュー

2026-10-20。対象 `/workspace/shared/phase-origin-source-review-v1-20261020/package`。v0とのテキスト差分とV1-REVIEW-RESPONSE、CONTRACT/SCHEMAを静的に読んだ。候補import、実行、PRNG初期化、数値計算、tests、source変更はしていない。

## 結論

**本担当のv0阻害「rnによる非有限mpfのzero化」は解消した。数理差分に新たな阻害は見つからない。**

64位相cacheは同じ理想OLSを狙う明示的な有限評価経路変更であり、v0とのbyte一致・同一root・同一gate結果は主張しない。root多項式・gate・φ_eval・各densityの数学に不意の変更はない。返却済estimated60/90の段階保存も呼出し順上で確認できる。

これは担当範囲の静的判定であり、開始許可、global根認証、数値精度認証、完走・資源・process lifecycle全体の保証ではない。

## 1. 来歴

親から提示された識別値：

- source manifest: `237b2ff1ec1e2f4c51f78f4b79ebecc8047f9d28b0edd4fe71946b8166d1ced7`
- input: `b60194d8460f6499dfd7fc9549707b688587ef35c835074837232c0f06b523e4`

全49 manifest entries一致は親の確認として扱う。本担当はhashを再計算していない。数理比較の基準は `phase-origin-source-math-review-v0-20261020.md` と、その監査対象v0のmodel.py/calibration.py。

## 2. rn修正

tuple分解より前に `need(mp.isfinite(x), "mpf_nonfinite_before_fraction")` が入り、NaN/±∞の特殊tupleが通常のmantissa/exponentとして解釈される経路を閉じた。float(Fraction)のOverflowErrorは明示的なGateへ変換し、元例外chainを保持している。変換後のfloat有限性検査も残る。

よってv0の具体的な反例経路は静的に解消。有限値の通常変換規則、zeroの扱い、非有限をclip/飽和/zeroで救済しない契約は整合する。特殊入力を関数へ渡す実行検証は行っていない。

## 3. 64位相cache

cosines/sinesは `mp.workdps(digits)` の内側で、h=1,2,3、k=0,…,63の順に作られる。50/80dps間で表を共有せず、それぞれ独立評価する。各係数の積和は従来どおりn昇順のY_nを走査し、table[n mod64]との積をmp.fsumへ渡す。Yの位相別事前集約はない。

実数ではn=64j+kから三角関数の周期性で同じOLS係数になる。有限評価では大きいn角を評価していたv0との差があり得ることをCONTRACTが明記し、`trig_basis`来歴も追加している。これは適切な計測前の契約改訂であり、既測定値を見て最適化した扱いではない。実行速度や900秒内完走は未測定のまま。

## 4. root・phase・densityの不変部分

calibration.pyの科学演算差分は上記表再利用だけ。A/Bの符号、Fの定数項、z³F′の7降順係数、degree拒否、6根、残差・再構成、unit分類、一対一対応、正曲率、順位gap、40桁有理化、境界・membership・丸め後順位gateはv0から変わっていない。

model.pyのq/h/v/Pminus構築、独立record生成、Fractionによる部分周期、W/Vの対角式、Aの初期P0込みinnovation式、S/Jの実部分blockを用いたrank-one式も変更なし。60/90dps、精度比較の閾値、Δ=estimated−oracleの符号は維持される。

したがってv0で確認した数学的整合性は、この限定差分で失われていない。理想解析関数・丸めgeometry・有限生成lawの区別とnoncertified性もCONTRACTに残っている。

## 5. 返却値の段階保存

scoresは各densityが返った直後にpersist(digits, 四つの数値文字列)を呼び、その後に次precisionへ進む。workerのcallbackはestimated_score60/90とreturned stageをmetadataへ入れてpair.saveを呼ぶ。storage.pyの保存経路はv0から不変で、atomic書込み・fsyncを行う。SCHEMAにも両4要素フィールドが追加された。

よって90dps評価中の中断時でも、先行してdurable保存が完了した60dps値は保持する順序になった。oracle residualはoracle scoreより前に一回保存し、estimated residualはestimated geometry完成後に一回保存する。成功経路でraw residualを二重appendする変更ではない。

ただし密度関数のreturnからdurable保存完了までのkill/I/O失敗を、原値が保存済みであるとは呼べない。metadata/partial/rawとprocess証拠から到達段階を読む必要がある。数学的な返却値保持の順序確認と、障害時durabilityの実測保証は別である。

## 6. 例外とschemaの留保

追加のtraceback出力はrootやdensityの値を変更せず、ログ不完全時はowner停止する。通常gate失敗と記録失敗を区別する設計であり、ログが必ず完了するとは本担当は認定しない。

SCHEMAのscore順序・partial値の追加はsourceと対応する。v0で述べた、schema通過だけではcomplete行の意味的完全性、membership被覆、文字列有限性まで証明しないという留保は残る。後段summaryが別レビュー待ちで隔離されたこととも矛盾しない。

## 停止

担当範囲で追加修正要求はない。数理非認証性の受容、他担当の運用・保存監査、別の開始判断は引き続き必要。本レビューを実行許可として用いず、局所Fisher参照や新しい計測列も追加しない。
