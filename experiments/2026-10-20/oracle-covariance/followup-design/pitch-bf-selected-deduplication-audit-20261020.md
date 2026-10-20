# 保存固定候補の重複構造監査

2026-10-20。対象：`/workspace/shared/pitch-bf-selected-input-review-v1-20261020`。

## 0. 結論

保存6180候補は、**(K, 保存codのbinary64 bits)** で分類すると **4180 unique key** になる。

- 2180 keyは1参照。
- 2000 keyは各2参照。
- 3参照以上のkeyは0。
- 各K=1..10につき418 unique key。
- 同じkeyに旧logBFの異なるbitsが現れる衝突は0。

同一kernel・同一数値手順を固定するなら、将来の候補別スカラー評価を4180 unique入力に対して行い、元6180参照へ戻せる。2000件分の重複入力評価を省ける構造がある。ただし今回その評価・結果転記はしていない。

保存済み1080支持との完全一致keyは0。今回確認した支持から再利用できる一致点はない。近いrへの補間、丸めて同じkeyとする処理はしない。

## 1. 読取対象と方法

使用したもの：

- v1 selected.jsonlのK、cod/J/fit/logBFのbits_be、候補ID。
- v1 frames.jsonのenergy.bits_be、frame/condition。
- 保存1080支持の`/workspace/shared/pitch-scalar-union-source-review-20261020/SUPPORT-PINS.json`。

監査は既存JSON値の同一性・集合・件数の照合だけ。codをJ/energy等から再計算せず、保存bitsの文字列をkeyにした。BF、exp、odds、差分BF、posterior、波形、候補sourceの実行・import、testsは行っていない。

selectedとframesの全字段・bit内部整合、候補ID完全性は先の監査文書を前提とする：

- `/workspace/shared/pitch-bf-selected-input-audit-20261020.md`
- `/workspace/shared/pitch-bf-b-prior-input-audit-20261020.md`

元NPZとのbyte一致はproducer報告であり、本監査も未同梱のNPZを直接再照合していない。

## 2. 6180参照の分類

keyは `(K, cod.bits_be)`。元参照IDは `(condition, frame_id, f_index, K)` のまま保持する。

保存cod bits単独のunique数も今回4180だった。これは今回たまたま異なるK間に同一cod bitsがないという観察であり、keyからKを外せるという意味ではない。BFはKに依存する。

重複2000 keyの条件ペアは以下の二群に尽きる。

- E-UとU-Uの組：1000 key。
- E-EとE-Uの組：1000 key。

異なるframe番号間の重複keyは0。異なるf_index間の重複keyも0。三条件すべてに共有されるkeyは0。

したがって、重複は同frame・同f_index・同Kの条件間共有であり、次数や周波数の候補を統合しているわけではない。

## 3. 条件間の保存値照合

各条件ペアについて同frame・同f_index・同Kの2060候補を比較した。

### U-U 対 E-U

- frame53..102の50frameで、各frame全20候補のcod、J、fit、旧logBFがそれぞれbit一致。
- 各字段の一致候補数は1000/2060。
- energyも同じ50frameでbit一致。他frameでは一致しない。
- frame53..101はsecond_complete、102はpadding。paddingの数値一致をclean F0正誤ラベルの存在と取り違えない。

### E-U 対 E-E

- frame0..49の50frameで、各frame全20候補のcod、J、fit、旧logBFがそれぞれbit一致。
- 各字段の一致候補数は1000/2060。
- energyも同じ50frameでbit一致。他frameでは一致しない。
- frame0/1はpadding、2..49はfirst_complete。ここでも同値性とcleanラベルの利用可能性は別。

### U-U 対 E-E

- 同frame・同候補のcod/J/fit/旧logBF一致は各0/2060。
- energy一致は0/103frame。

境界frame50..52には、上の二つの共有区間に属する一致はない。今回の一致は保存値についての厳密なbinary64一致であり、閾値付きの「ほぼ同じ」判定ではない。

## 4. 同一keyに対する旧logBFの一貫性

4180 keyごとに保存旧logBF.bits_beの種類数を調べ、すべて1だった。重複2000 keyでも旧logBFに衝突はない。

これは「今回の保存入力において、同じK/rで異なる旧logBFが出た」という矛盾が見つからないことを意味する。旧Laplace値が数学的に正しい、exact積分と一致する、source実行が全環境で決定的である、と証明したわけではない。

新exact値を一つ評価して共有する場合も、旧logBFを消去・置換して保存しない。元6180参照の旧値と来歴を保持したまま、unique評価への参照を付す。

## 5. 保存1080支持との交差

照合したSUPPORT-PINS.json：

- 保存行数1080。
- unique `(K,r_bits)` 数1080。
- SHA256 `9f16ecf3ac2fed8c5366d2547459770706ba3a86827492e3f01613ba014ce688`。

この保存支持と今回4180 keyの集合積は0。該当する元候補参照数も0。

ここで確認したのは保存支持keyの交差であり、1080各点の成功statusや数値結果を新たに再監査・再判定したわけではない。全支持集合に一致がないため、その成功部分集合からも同一keyの結果再利用はない。

数値的に近いr、同じKで同一領域に属するr、同じ表示桁のrを完全一致へ昇格させない。既存1080点の成功や精度条件を、未評価4180点の成功保証ともしない。

## 6. unique入力評価を共有できる条件

今回の数学的kernelは、既存契約におけるN=400、δ=3、d=2K、正則化cod=r、同じ正規化定数を保ったスカラーBFである。この固定条件下では、f_indexやcondition、frame、priorはスカラーBFの追加引数ではない。

ただし実際の評価結果を共有する前に、次を固定する必要がある。

1. N、δ、dとKの対応、hyper-g priorとBFの正規化、log-g LaplaceのJacobian・曲率項が同じ。
2. rは同じ保存cod bitsを使う。分母energy+400×5e−6の定義を変更せず、Jやfitからrを再生成しない。
3. binary64 rの高精度へのlift方式、桁数、exact参照経路、Laplace経路、停止予算、精度確認手順が同じ。例えば既存の整数比liftと十進表示からの再読込を混ぜない。
4. 数値source/contractと依存ライブラリ版・関連設定をpinする。過去のsource pinが存在することと、新しい評価担当がそのpinを実際に使用したことは分ける。
5. 各unique keyに必要な複数精度・複数経路の検証は省略しない。「一度評価」は一つの入力に必要な評価一式を一組作る意味であり、一回の特殊関数呼出しで検証済みとする意味ではない。
6. 失敗・未達・精度保留はkey単位で保存し、そのkeyを参照する全候補へ同じ状態を伝える。一つの参照だけ再試行して成功値を選び、他の失敗履歴を消さない。

以上の条件下で、数学的には4180 unique入力の評価一式を6180参照に共有できる。これは新たな評価の実行承認・開始ではなく、重複を避けられる入力構造の報告である。

## 7. 共有してはいけないもの

同じK/codを共有していても、A prediction_prior、B log_prior、memory履歴は条件ごとに違い得る。したがってBF値の共有から、重み付きscore、K周辺化、pair odds、posterior、時間状態の共有へ拡張しない。

元309frameは重複窓と条件間共通部分を含む。6180参照、4180unique key、重複2000keyのいずれも独立標本数ではない。重複を除いたことは独立化でも、有限標本の有効サンプル数推定でもない。

全gridの未保存rをこの重複構造から補完できない。F0/VUV精度、音質、exact再追跡の主張も引き続き対象外。

## 8. 完了

保存値の重複構造、条件間一致範囲、旧logBF衝突の不存在、保存1080支持との交差0を確認した。元入力packageと計画本体は変更していない。新しいBF評価や数値結果の混合は開始しない。
