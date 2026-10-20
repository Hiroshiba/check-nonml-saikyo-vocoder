# 固定候補BF stage1 数値呼出し静的レビュー

## 判定

数値部分の静的条件通過、未実行。今回のadapterに数式・精度・gate・point累積予算の変更や、domain違反をclipして成功させる経路を認めなかった。数値実行の開始許可、実測一致、certified errorの認定ではない。

対象: `pitch-fixed-candidate-source-review-20261020/pitch-fixed-bf-adapter-20261020` の numerics.py、worker.py、preflight.py、CONFIG/CONTRACT。旧 `pitch-exact-scalar-source-review-v2-20261020/source/numerics.py` と比較した。

- numerics.pyは旧v2とbyte同一、8188 bytes、SHA256 `0e0572196e6f1a53e49cfff1ba990a00993bf331538467378ff1647997d23065`。
- SOURCE-MANIFEST SHA256 `2a9f8d7e59d283831acff16cd5d3d63bc7a6094005148a6d13bc42e0402b2ec9`。記載11ファイルのbytes/SHA一致、7 PythonのAST読取成功。
- source/候補の実行・import・BF再計算・testsは行っていない。

## 1. 固定入力とbinary64 lift

preflightは4180件、unique_id順、owner=id mod3、Kがboolでない整数1..10、(K,r_bits)のソート済みuniqueを確認する。r_bitsをbig-endian binary64に復元し、finiteかつ0≤r<1、r_hex、as_integer_ratioの一致を検査。kernel側でもK/整数比/hex対応を再確認する。

50/80桁の各workdps内で `mp.mpf(num)/mp.mpf(den)` を作る。binary64の有限値は53bit以下の有効仮数を持つdyadic rationalであり、この精度で元r自体を正確に持ち上げられる。10進文字列からのr再解釈、J/energyからの再推定、clip/floorはない。subnormal等で1−rが丸めで1になる可能性は元kernelが `epsilon_rounded_to_one` に記録し、rの正確なliftと後続算術の丸めを区別している。

原rawのcodとindex各参照の対応自体は、固定index manifestの内容と別index監査に依存する。本reviewで元raw全参照へのjoinを再実施したとは主張しない。

## 2. 固定式と独立な経路

N=400、δ=3はkernelの200、q=K+1/2、p=200−q、係数1/2として固定され、CONFIGと一致する。K範囲からq>0、p>0である。

- A: r=0なら解析値−log(2K+1)。小rでは正項hypergeometric級数、残りはunregularized incomplete betaを直接評価し、1−丸めCDFの減算を避ける。級数route境界とratio<1条件は元binary64整数比による整数不等式で判定。tailのlog寄与≤1e-9を要求し、満たせなければ項予算まで継続して失敗する。
- Q: x=(1−r)g、s=log xに移した元integrandを直接積分する。Jacobian込みのlog integrand、元係数−log2−p log(1−r)を保持。beta/gamma/2F1をQ内で再利用しない。左右tail解析式はp−1>0、q>0の条件で正しく、計算値を用いた非認証上界として記録する。各拡張でtail log寄与と推定求積error log寄与を各≤1e-9とする。
- L: 同じs=log x座標はlog gの平行移動であり、mode/Jacobian/curvatureは同じ。mode根は符号に応じた相殺回避形を使用。非正mode/curvature、非有限値は例外で停止する。

Qの解析tail式も浮動小数評価であり、mp.quadのerrorは推定値である。A/Q独立経路と50/80桁一致は有用な診断だが、厳密丸め誤差証明ではない。

## 3. 精度gateと累積予算

各keyにつき50桁A→Q→L、80桁A→Q→Lを一度だけ実施する。finite確認後、A50/Q50/A80/Q80の全spread≤1e-9かつL50/L80差≤1e-9ならmatched_noncertified。それ以外はmismatchで、採用用delta_A80/delta_Q80をnullにし、raw差は保存する。

同じBudget(counts,index,deadline)が両精度・全求積拡張に渡される。明示series項100000、quadrature callback評価200000の上限前に検査し、精度切替・extension切替でcounterをresetしない。旧counter共有構造はkey毎に2項目。r=0のA解析式はseries項を消費しないがQは通常予算を使う。

重要な留保: incomplete-beta内部反復は公開counterで数えておらず、diagnosticsもinternal_iterations=Noneである。100000は明示series経路の項数上限であってmpmath内部演算全体の上限ではない。特殊関数呼出前後のdeadline確認と外部監督による強制停止は別の制約である。

## 4. 呼出し境界の数値上の性質

workerはpreflightを再実施し、受領rowsが検証済みowner subsetと一致することを確認してからmpmathをimportし、固定dependencyの実originを検査する。kernelは同じreviewed manifestの全ファイル検査でpinされる。CONFIGのkernel_sha256を単独で再比較する分岐はないが、source manifest期待SHAとfile bytes/SHA検査が現在の固定kernelを拘束する。

PointBudgetはpoint_budget、GlobalBudgetはglobal_budget、その他例外はerrorとして保存し、例外を一致へ昇格しない。mismatchの採用deltaはnull。stageごとの元多倍長文字列と求積途中診断をemitし、workerはackを待つ。保存失敗や途中停止を数値成功と扱わない設計である。再試行、旧支持生成器、stage2評価呼出はない。

外部時計・claim一回性・OS終了・保存容量の完全な監査は別担当。本稿は数式・入力表現・数値呼出し・gateに限定する。全key成功や精度達成、stage2比較、tracking/VUV/音質改善は未確認である。
