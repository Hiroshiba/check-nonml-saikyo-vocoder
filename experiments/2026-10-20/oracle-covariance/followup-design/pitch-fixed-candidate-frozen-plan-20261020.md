# 固定候補BF診断：二段階の凍結実行計画

2026-10-20。独立レビュー用の紙上計画。**実行指示ではなく、実装・実測は未開始。**

## 0. 目的と非目標

保存された同じcodに対し、既存log-g Laplaceの数値保存値、同じLaplace式の高精度評価、exact hyper-g参照の差を分離する。その後、三つの指定priorを個別に凍結し、固定2周波数内での次数周辺化とconditional oddsへの影響だけを読む。

対象は既存人工3系列の309frame、固定f*/2f*×K1..10の6180参照。全gridのF0推定、H0/VUV、元B時間再帰の再実行、音声生成、品質評価、新方式採用、既存BMA条件の変更は含めない。

以下は数学的定義、入力・所有権・停止・保存契約を凍結する案である。BF/r/exp/oddsの実計算、candidate実行/import/tests、Git操作は本作成で行っていない。環境は未割当で、新Cloud作成失敗を理由に他環境へ自動代替しない。親が接続・割当と実行開始条件を別途確認する。

## 1. 固定入力と既存監査

入力はv1選択bundleのみ：

- Library ID：`libfile_d1835dacce008191a65d4eb28ac5c680`
- file ID：`file_0000000003b481fda7569d6cffbf34d4`
- ZIP：1213332 bytes
- SHA256：`2c5524d0156d490ea174e31a47ba5c8e49ad6e6ba54a3de952c3aad9332f8f4d`
- 読取監査場所：`/workspace/shared/pitch-bf-selected-input-review-v1-20261020`

事前監査：

- `/workspace/shared/pitch-bf-selected-input-audit-20261020.md`
- `/workspace/shared/pitch-bf-b-prior-input-audit-20261020.md`
- `/workspace/shared/pitch-bf-selected-deduplication-audit-20261020.md`

確認済みの入力構造は6180参照→4180 unique `(K,cod bits)`。旧logBFの同key内衝突0、既存1080支持との交差0。各Kには418 unique key。旧A11ファイルはv1でもbyte不変。B log_prior6180値とlog_prior_H0の309値は有限で内部bit整合。

同梱manifestの整合と、元NPZとの同一性は別である。元NPZ/source本体は未同梱なので、producerの原bit照合報告をconsumerが独立再確認済みとはしない。

## 2. indexと参照対応の凍結

### 2.1 unique keyの順序

keyは `(K整数, r_bitsのunsigned 64-bit整数)`。r_bitsは保存cod.bits_beをbig-endianとして読む。K昇順、次にbits整数昇順の辞書順で並べ、unique_id=0..4179を付す。

十進表示値・frame順・評価の難易度・BF差・priorの大きさによる並べ替えはしない。bitsから元binary64値とexact整数比を得ることは表現変換であり、J/energyから新しいrを算出することではない。保存value/hex/bitsの整合を再照合し、rはその保存値だけを使う。

入力codを保存bitsから復元した時点で、非finite、r<0、r≥1のいずれかがあれば数値評価の前に停止する。clip、floor、端点への置換、該当候補の黙った除外はしない。

### 2.2 owner

    owner = unique_id mod 3

- owner0：1394 key。
- owner1：1393 key。
- owner2：1393 key。

各ownerは自分のunique_idを昇順に処理する。別ownerへの移送、完了後の余剰予算による他shard補完、結果を見た並べ替えはしない。

### 2.3 必須index成果物

実装準備段階で、以下をデータのみとして生成し別レビューで固定する。今回は未生成。

1. unique index：unique_id/K/r_bits/r_hex/exact整数比/owner。
2. reference index：元(condition,frame_id,f_index,K)→unique_idの全6180対応。
3. frame index：309frame、各20参照、energy・支持・A/B prior参照先。
4. input/source/index manifest：全ファイルbytes/SHA、生成規則、候補軸、元v1 ZIP pin。

indexレビューは4180数、owner数、全6180参照の一意対応、重複2000key各2参照、旧logBF衝突0を確認する。全gridやMAP追加点は含めない。既存1080結果の混合・最近傍再利用はしない。

## 3. 第1段：byte不変の数値kernel

承認済みscalar kernelを変更せず使用する。既存v2 manifestでの対象：

- `source/numerics.py`：8188 bytes
- SHA256：`0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065`
- 既存source manifest pin：`320865684480581408525899ace68a373d1abedee29350565a5bdbe8fc5c2497`
- 依存契約：Python 3.12系、mpmath 1.3.0。実行環境の詳細と依存ファイルpinは実装レビューで再確認する。

新adapterは支持index、所有権、外部監督、保存だけを担当する。旧1080支持生成器を呼ばず、数理kernelを書き換えず、結果を通すためのfallback・精度変更・gate緩和を加えない。

既存packageの運用contractには旧wall/output上限が含まれるため、新4180入力のadapter運用契約と区別する。旧contract全体をそのまま新実行の運用設定と称さない。byte不変を要求する数理kernelと、別レビューする新adapterの境界を明示する。

### 数学的不変条件

- N=400、δ=3、d=2K、K1..10、white、同じBF定数。
- 保存r=cod、元定義J/(energy+400×5e−6)を維持。ただしその除算は再実行しない。
- binary64 rをexact整数比から多倍長へlift。
- 50/80桁でprimary A（既存分岐の正項級数／不完全beta）、独立求積Q、log-g Laplace Lを評価。
- 既存gate：A/Qの50/80桁四値のspread≤1e−9 nats、L50/L80差≤1e−9 nats。
- 級数・求積の分岐、tail診断、quadrature範囲拡張、Jacobian、曲率、例外を既存kernelどおり保持。
- point累計series上限100000、quad上限200000。50/80桁や拡張ごとに予算をリセットしない。

成功ラベルは既存のmatched_noncertified。これは有限精度での経路間一致であり、厳密な真値誤差区間ではない。gate通過を音声推定の成功条件に読み替えない。

「各keyへ一度」は、必要な50/80桁A/Q/L一式を1 attemptとして実施する意味である。1回の特殊関数呼出しに削減する意味ではない。自動再試行、失敗点の再投入はなし。

## 4. 第1段の資源・停止・保存

### 4.1 上限

- 1 worker/shard、最大3同時。
- 各shard総wall上限15分。最大合計45 worker-minutes。
- 数値worker単体にRLIMIT_AS=512 MiBを設定する。数値workerは子processを生成しない。
- supervisorのメモリ使用量は別に計測・記録する。この512 MiBはprocess tree全体に対するOSの合算保証ではない。
- 各shardの結果出力上限64 MiB。
- owner間の予算融通なし。進みが遅くても上限延長しない。

運用案として各15分の末尾60秒を停止・保存・reapに予約し、科学評価のdeadlineは開始から14分以内に設定する。新keyの開始もそのdeadline前に限る。終了余裕は15分に追加しない。起動・監督側の時刻起点とhard-stopを実装レビューで確認し、workerの自己申告だけに依存しない。

保存・receiptを確保できない容量になる前に追加評価を停止する。64 MiBへ収めるためrawを切り捨てたり、診断字段を黙って省いたり、上限に達してから新評価を続けない。既存入力sourceの読取領域と新規結果領域を分離し、出力容量計数の対象・最終receipt予約を実装レビューで固定する。

### 4.2 状態と伝播

全4180keyの台帳を評価前に持ち、各keyの状態をunattempted / running / matched_noncertified / mismatch / point_budget / global_budget / interrupted / error等、実装契約で明示する。成功値がないkeyをzeroや−∞のBFへ置換しない。

deadline、memory、output、例外で止まった場合、終了時刻、理由、最後のkey/stage、point累計消費、worker exit、外部kill/reapの有無を残す。終了確認が不確かな場合は再起動せず、状態を確認する。

失敗keyを参照する元候補すべてに同じ欠測状態を伝える。2参照keyの片方だけを成功扱いしない。既存のpartial valueは履歴として保存するが、残り桁や経路を省いて成功へ繰り上げない。

### 4.3 rawとpins

必要な保存：

- 入力ZIP/source/index/依存の固定hashと取得receipt。
- shard/owner/key/参照対応、開始・終了・外部監督記録。
- append-only stage journal、各50/80桁A/Q/Lの元数値文字列とdiagnostics。
- point累計series/quad消費、tail/拡張・中断情報。
- 全keyの最終台帳、成功/未達の全件数、理由別内訳。
- rawファイルのbytes/SHA、最終manifest、結果packageのreceipt。

元数値文字列をfloatへ短縮してから保存しない。集計表だけを残してrawを捨てない。receiptの「完了」はworker終了と保存整合を確認してから記す。

## 5. 第2段：保存point値の参照展開のみ

第1段と別のsource/indexレビューを通し、別の1回枠として実施する計画である。第1段の残時間に自動起動しない。第2段の具体的wall/memory/output上限・環境割当は、後段sourceレビューで固定するまで実行不可。

入力はpin済みv1、unique/reference index、各shardのraw結果と台帳のみ。数値kernelを呼ばず、missing keyのBF評価・補修をせず、保存結果を採用ルールでjoinする。

採用ownerはunique_id mod3で唯一。重複・欠落・別owner結果・pin不一致を停止理由にする。値が好ましい結果を選ばない。成功pointのA80をexact式参照、L80を同じLaplace式の高精度参照として使用し、Q80は既存検証証拠として保持する。A80/Q80を平均して新参照にしない。

後段の算術は80桁を固定案とする。保存A80/L80の文字列を保持して読み、保存binary64の旧ell・prior・B log値はexact整数比でliftする。真値精度を新たに得たとはしない。後段の算術・正規化・schemaを実装レビューし、この段階で特殊関数を再評価しないことを確認する。

第2段の別レビュー・開始指示後には、保存値を入力とする差・和、log、exp、log1p、LSE、条件付き正規化等の後段算術を許可する。禁止するのは新しいBFの特殊関数評価、級数・不完全beta・求積の再評価、rの再算出、元の時系列状態の再推論であり、保存値からconditional odds/K分布を定義するための後段算術まで禁止するものではない。本計画文書を更新している現在、その算術を実行する許可や開始指示が出たとは扱わない。

## 6. 三つの差を分離する

各候補についてS=旧保存logBF、L=L80、E=A80と書く。

    numerical_reproduction_gap = L − S
    integration_approximation_gap = E − L
    total_replacement_gap = E − S

数学的にはtotal=numerical+integration。後段有限精度での合成丸めも無視して字段を書き換えない。

既存kernelの保存delta_A80はL−Eであり、上のintegration_approximation_gapと符号が逆である。元delta_A80/delta_Q80を改名せず保存し、後段字段には向きを明記する。

L80は同じ理想式を高精度評価した有限精度値であり、無限精度の真値ではない。L−Sには元の演算順・浮動小数点実装・丸め等の差が含まれ得る。これを積分近似誤差E−Lへ混ぜない。

同じkeyでは旧Sのbitsも一致しているため、これらのセル差は共有できる。ただし参照のcondition/frame/priorは消さない。

## 7. 三prior条件を完全に分ける

共通候補集合はF={f*,2f*}×{K1..10}。frameとprior条件cごとにlog重みb^c_akを定義する。

### static初期prior条件

各conditionのframe0に保存されたinitial_prior_payloadの各固定セル値pを全frameで固定し、b=log pと定義する。後続frameの帳簿zeroを読まない。初期priorが理論上の一様値であっても、保存binary64値を勝手に理論実数へ差し替えない。

### 旧A prediction_prior条件

各frameの保存prediction_prior pをそのまま固定。p>0ならb=log p、p=0ならb=−∞。zeroへfloorを入れない。T/Rから再構成しない。

このpriorは更新前のH1無条件joint質量。posterior、F0 marginal、H1内条件付き質量と呼ばない。

### 旧B log_prior条件

各frameの保存binary64 log_prior値bをそのまま実数として固定する。丸める前の理想log priorを復元しようとしない。expして通常確率へ戻し、再びlogを取る操作もしない。

Bの全6180選択値は有限だが、旧Aとは別の数値履歴であり、log(A prior)ではない。同じ保存A logBFを過去に使った旧B軌道を条件にしているだけで、新BFの再追跡ではない。

## 8. 周辺化とconditional oddsの定義

各prior条件c、候補評価s∈{S,L,E}について

    G_a^(c,s) = LSE_(k=1..10)[b^c_ak + s_ak]

とする。両周波数群に正のprior支持があれば

    D^(c,s) = G_1^(c,s) − G_2^(c,s)

が固定2周波数に条件付けたlog odds。

各周波数内のK条件付きlog分布は

    log w_ak^(c,s) = b^c_ak + s_ak − G_a^(c,s).

報告ではlog値を保持し、通常確率を表示する場合は表示underflowと数学的zeroを区別する。ここで定義する確率はP(f*|F,c)、次数分布はP(K|指定f,c)であって、P(f*)やP(f*|H1)ではない。

三段階S/L/Eから周辺化後も

    D^(c,L)−D^(c,S)  ：数値再現寄与
    D^(c,E)−D^(c,L)  ：積分近似寄与
    D^(c,E)−D^(c,S)  ：置換総寄与

を別々に出す。非線形なK周辺化を行うので、セル差の単純平均では代用しない。prior条件cが異なる値同士の差を「同じpriorでの近似差」と呼ばない。

### 欠測とzero

- frame比較は必要な全20セルの成功値が揃うことを要求する。prior zeroで重みが消えるKも、失敗除外の口実にしない。
- 一つでも必要keyが失敗・未達なら、そのframeの比較tripletとK分布比較をmissingとする。成功Kだけで再正規化しない。
- 完了セルの点wise差は別表で保持できるが、欠測frameの完全な比較結果と扱わない。
- 旧Aで片側周波数の全K priorがzeroなら、その側のGは−∞、pair log oddsは拡張実数として片側±∞になり得る。**±∞−±∞を数値Δにせずnot_applicableとする。**
- 全zero側のK条件付き分布は未定義。反対側の分布は数学的に定義できても、比較表では非対称supportを明示する。
- 両側全zeroならpair自体が未定義。現bundleにはないが分岐を残す。
- 後続initial payloadの帳簿zeroは上の支持zeroに一切含めない。

現入力では旧Aに片側全zero205frame、両側positive104frame。Bとstaticはそれとは別に定義する。B条件へ替えた結果を「Aのzeroを新BFが救った」と解釈しない。

## 9. 報告仕様

### 入力と実行範囲

固定pins、環境、開始終了、owner範囲、処理/未処理key数、参照数、予算消費、停止理由を最初に示す。4180unique、6180参照、309frameを独立標本数と呼ばない。

### point表

unique_id/K/r bits/owner、status、50/80桁A/Q/L、既存gate結果、元delta字段、L−S/E−L/E−S、参照一覧、精度・停止留保。

### reference/frame表

6180参照の元IDを維持。309frameについて三prior条件を別欄とし、S/L/Eのpair log odds、K log分布、三寄与、complete/missing/not_applicable理由を記す。片側zeroや欠測を0の効果へ丸めない。

### 科学的結論の限界

最大差・方向・条件付き順位変更等は対象完了点の記述に限る。未達keyを除外して全4180成功、全309frameの傾向と表現しない。gate1e−9は厳密誤差上界ではなく、符号の厳密証明や同等性幅にも流用しない。小さい差や境界では数値精度に対する留保を残す。

旧saved BFに同一key衝突がないこと、B log priorがfiniteであることだけから結果の改善を予告しない。全grid MAP/VUV、自己整合的な時間再帰、音質、自然音声への外挿は結論しない。

## 10. 五仮想視点・二往復の再検討

これは一人の設計者による五観点の机上レビューであり、独立五名の実測査読ではない。

### 第一往復

1. 入力担当：「6180回評価する」。数理担当：「同じK/codが2000件重複する」。修正：4180keyの固定indexを評価し、元参照とpriorは保持。
2. 数理担当：「exact−旧ellだけ報告する」。批評家：「数値再現差と積分近似差を混同する」。修正：S/L/Eと三つの差、旧deltaの符号を固定。
3. 状態担当：「Bのfinite priorを使えばexact追跡になる」。批評家：「Bも旧BFの過去軌道」。修正：三priorを別々に凍結し、再追跡を禁止。
4. 実行担当：「15分いっぱい計算してから保存する」。入力担当：「保存・reap時間が上限外へ出る」。修正：末尾60秒予約、hard-stopと外部監督、raw先行保存。
5. 批評家：「失敗Kを落とせば比較できる」。数理・状態担当：「候補支持と次数priorを事後変更する」。修正：全必要20セル完備を条件にし、失敗はmissing伝播。

### 第二往復と反証条件

1. 入力担当：「bitsが同じなら別source結果も共有できる」。数理担当：「kernel/精度/依存も必要」。反証条件：pin不一致、r再生成、Kを落としたkey、別owner結果の混合。
2. 数理担当：「gate通過なら真値誤差1e−9以下」。批評家：「非認証の経路一致に過ぎない」。反証条件：厳密保証への昇格、未達点への成功外挿、Q/A平均への無断変更。
3. 状態担当：「Aの∞ odds同士の差を0とする」。数理担当：「∞−∞は未定義」。反証条件：not_applicableを数値0へ置換、初期帳簿zeroの誤使用、A zeroの補修。
4. 実行担当：「余ったshardで失敗を再実行」。批評家：「一回性・owner・予算を破る」。反証条件：自動retry、owner移送、45 worker-minutes超過、状態不明のまま再起動。
5. 批評家：「pairが真F0側へ動けば品質改善」。状態・入力担当：「条件付き人工subsetの結果でしかない」。反証条件：全grid/VUV/音質への飛躍、padding/boundaryへのcleanラベル付与、重複参照を独立標本扱い。

## 11. 実行開始前の停止線

以下が揃うまで実行しない：

1. 親による実行環境の割当確認。
2. 新adapter/source・index・dependency pinsの独立レビュー。
3. stage1外部監督、15分/512MiB/64MiB、保存予約と一回性の静的確認。
4. 親によるstage1開始の別指示。

stage2はstage1結果を保存・監査した後、別source/indexレビュー、数値処理と資源上限の固定、1回枠の開始指示を必要とする。stage1終了や本計画の作成だけで自動開始しない。

本計画の作成・保存で今回の作業を完了する。新しい計測・評価は開始しない。

## 12. 凍結前の独立レビュー反映記録

2026-10-20、親から独立レビュー結果として「数理・dedup・zero/欠測の阻害誤りなし」と報告された。原計画から次の3点を明確化した。

1. 第4.1節の512 MiBをprocess tree合算上限という表現から、数値worker単体のRLIMIT_ASへ修正。workerの子process生成禁止、supervisorは別計測、tree全体のOS保証ではないことを明記。
2. 第2.1節に、保存bitsから復元したcodが非finite/r<0/r≥1なら、clip等なしで評価前停止する条件を追加。
3. 第5節に、第2段で許可する保存値のLSE/log/exp等の後段算術と、禁止する新BF特殊関数・求積・r再算出・元時系列再推論を区別して明記。

数学的kernel、入力、4180key/6180参照、owner、数値gate、zero/欠測規則は変更しない。今回の文書更新では実計算を行っていない。
