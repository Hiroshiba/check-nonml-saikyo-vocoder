# phase-origin source v0：入力・生成・来歴の独立静的監査

2026-10-20。対象 `/workspace/shared/phase-origin-source-review-v0-20261020/package`。model.py、worker.py、preflight.py、storage.py、external.pyの関連部分、CONTRACT/SCHEMA/INPUT/SEED/DEPENDENCIES/SOURCE manifestを読取。候補import・実行、PRNG初期化、draw、tests/smoke、科学計算は行っていない。独立stdlibによるJSON/hash・整数ID/seed配列比較のみ実施。

## 判定

**入力集合・seed mapping・train/test隔離は静的PASS。ただし返却済推定scoreの保存と必須pin検査の無効化防止に未解消事項があり、v0のまま開始可とはしない。** 数値root/密度式の詳細、実資源・reap保証は別担当レビューの対象とする。

## 1. 開始前に修正すべき事項

### B1：返却済estimated60が90側の失敗・killで失われる

model.scoresはestimated densityを60/90dpsで順に呼ぶが、結果をRAMの辞書だけへ入れ、両精度と差・gate計算が終わってからrecordを返す。workerはその返却後に初めてpair.doc["scores"]を保存する。

従ってestimated60が返却済みでも、90側の例外・kill、後続gate用処理の例外でその60値が保存されない。oracle側は各精度直後に保存しており非対称。返却済片側値の保持・失敗時の証拠回収という契約を満たさない。

最小修正は、各estimated densityの返却直後にlogdet/Q/定数/scoreの原値と精度をatomic/fsync保存し、その後に次精度へ進むこと。全score比較/gate recordとは分ける。SCHEMAはadditionalProperties=falseでestimated単精度字段を現在持たないため、保存字段追加とschema更新をセットでレビューする。返却前killの値を捏造して保存する要求ではない。

### B2：assertに依存する必須pin検査

preflight.loadのsource hash・file集合・依存hash・Python version/hash・thread環境等はほぼassertである。externalはPYTHONOPTIMIZEを除去せず、sys.flags.optimize非zeroを明示拒否しない。子起動の `python -B` も環境由来最適化を無効にしない。

そのため-O/PYTHONOPTIMIZEで必須確認が消える状態を、現在のentrypoint自身は排除していない。実環境が現に最適化されていると認定したものではないが、開始条件として未防止。

最小修正は必須チェックを明示的if/raiseへ変更すること、または全entrypointでassert以外の方法により最適化を拒否し、child環境でも禁止を保証すること。少なくとも固定開始契約と実runtime証拠で「assertが有効」を確定しない限り、必須pinを検証済みとしない。

### C1：oracle score residualの保存時点

workerはoracle scoreを校正前に保存するが、test/score_residual_oracleとestimatedの両診断配列は校正成功・estimated geometry生成後にまとめて保存する。校正失敗pairではoracle診断残差もない。

Yとoracle qは校正前に保存済みなので、原科学入力は失われない。一方CONTRACTの「test両score residualを保存」を全生成済みpairへ適用するなら不一致。oracle段で先に保存するか、これらを「両geometry到達時のみの派生診断」と明示し、欠測理由を保持するかを一つに固定する。未保存残差を保存済みと呼ばない。SCHEMAのarraysは任意名を許し、全成功/失敗状態に必要な配列集合までは検証しない。

## 2. manifest・台帳・seedの独立確認

SOURCE-MANIFEST自身のSHA:
`19def7ce47119e65677f7feb2d96d5a87b5f9fbe06a3721ea5d9d335cbaaf585`

自己除外全file集合、各bytes/SHAがpackageと一致。INPUTの500行を個別照合し、
`global_id=100*truth_id+pair_id`、truth順W/A/V/S/J、pair_id0..99、owner=global_id mod3を確認。owner件数167/167/166はINPUT/SEED記録と一致。

study名 `phase-origin-fixed-truth-analytic-q-20261020-v1` のUTF8 SHA256をlittle-endian uint32×8へ独立分解し、digest_wordsと一致。各行×split0/1×component0..3の4000 seed入力を整数列として構築し、SEED-OWNER-MANIFESTの全4000列と順序も一致、重複なし、各長さ13。

これはPRNG初期stateや出力列の非重複証明ではない。将来workerは全4000初期stateを生成してhash重複検査し、その後各実生成初期stateを対応hashへ照合する設計。今回その初期化はしていない。旧6語mappingとの非同一は長さによる入力識別であり、PRNG出力の独立性証明ではない。全ホストのstudy名・claims唯一性は親の開始時確認が別途必要。

externalは科学前に500全行のplanned-ledgerを保存。各workerは自owner行だけを昇順に処理し、seedにownerを混ぜないため、owner割付変更で科学seedが変わる設計ではない。ただし自動再割付/再試行は契約外。

## 3. 生成とtrain/test隔離

generateは初期AR、innovation、s、jに別componentの新Generator/PCG64/SeedSequenceを作り、それぞれ一回standard_normalを呼ぶ。train/testはsplit IDが違い、初期AR drawを共有せずtestへtrain末尾をcarryしない。zero τでも標準drawとscaled値を保存する。

truth原点0の生成では64周期をn//64で区切る。oracle geometryのq/h/v/Pminusは両recordへ共通の決定的定数として渡し、乱数実現を共有するものではない。ARはsample間でcarryし周期resetなし。s/jは周期ごと独立seed系列のdraw要素を使用する。realizationごとのRMS再正規化・clipはない。

scaled initial、s/j、AR、合成residual、Yを次段前に書く。binary64生成法則と解析Gaussianは別であることがCONTRACTに明示されており、真のGaussian期待KL恒等式を丸め生成器の厳密結果へ移していない。

## 4. 校正と二scoreの隔離

workerの校正呼出しは `calibrate(records[0], pair.roots)`。test、truth parameter、oracle scoreを引数として渡さない。callbackはroot診断保存用で、読取経路としてoracle値を校正へ返していない。oracle scoreは先に保存されるが、選択・tie救済に使うコード経路はこの担当範囲では見当たらない。

校正後geometryはphiから構成し、noise parameterは同じtruth固定。noise再適合、五候補winner/BMA、F0未知化、test alignmentを追加していない。今回の二scoreは**新studyのoracle原点対train-only原点**であり、旧known-q500の再評価ではない。

解析q正本と80dps→binary64 geometry、理想解析OLSと保存Yの区別は契約にある。旧float q定数のbit互換は主張していない。真phi0=0による生成blockと、推定位相のFraction floorによるscore blockは意図して分離される。

## 5. raw復元と状態台帳

Pair.arrayはheaderなしlittle-endian f8をC順でappendし、name/offset/bytes/shape/dtype/SHAをmetadataへ保存。intentを先にfsyncし、raw append/fsync後に完了descriptorへ更新するため、kill時に未完blobを成功配列と混同しない構造がある。既保存標準drawも残し、seedだけから再生成しない。

q/h/vは64要素、Pminusは1要素を保存し、4096座標ではn mod64で参照する。g=q alias、oracle geometryを両recordが参照する規則は明示される。estimatedのmembershipは別保存。raw byte読み出しと位相・周期ラベルから復元でき、端周期をoracleのK列へ無理に押し込めない。

保存score residualはbinary64減算の診断値、密度の差は保存Y/qを各mp精度へliftして引く値であり、同一残差と称さない。B1/C1の修正後もこの区別を保持する。

Gateはpair numerical_failureとして保存し続行、未知例外/capacity/I/Oはowner停止。予定台帳が不変のplanned表なので、後段はpair metadataと終端証拠を照合して未着手・途中・失敗を識別する必要がある。worker全体completedを500科学成功へ読み替えない。配列集合・offset非重複・SHA・owner/run完了を実成果物で監査する工程はまだ実施していない。

## 6. 依存pinの範囲

DEPENDENCIESはPython3.12.14 executable hash/sys.version、mpmath1.3.0の94file（sourceとmetadata）、NumPy2.3.5の904fileを列挙。preflightは配布metadata/version/spec/hashを科学import前に照合し、workerは実import originとmpmath pure-python backendを確認する。thread環境とMPMATH_NOGMPY/NOSAGE等の規約もある。

今回確認したのはpinファイルの内部固定と検査コードの静的構造であり、別実行環境に全依存が存在しhash一致することを実行検証したものではない。B2を解消して初めて、そのruntimeチェックの有効性を開始条件にできる。全OS/libc/CPU・実native thread数・性能を完全再現する証明でもない。

## 停止点

入力/seed/training隔離の追加生成実験は不要。B1、B2とC1の契約解消・更新source/schemaの再レビューを待ち、現v0を実行しない。旧500結果・raw・PML・参考音声工程は変更しない。
