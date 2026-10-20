# 同一保存観測の条件差・近似変更interaction：準備版

source/input準備のみ。candidate import/実減算/実行/tests/smoke/fixtureなし。AST/cached Ruffのみ。開始には独立source/input/算術レビューと親の別指示が必要。Git/HTMLなし。

## 入力と固定100

INPUT-MANIFEST.jsonに3ZIPのconsumer-local絶対path/bytes/SHAおよび全member bytes/SHAを固定。stage2結果はLibrary libfile_81d872dde6b0819188f2c9cadbe42082 v0、SHA1caa151838a24d9c15326c455ff1d174e9d44514c0f8b22a6448c70520b694e5。selected/indexは不変版。計画bundleは公式consumer-local転送、xattrs適用、ZIPと文書MANIFEST照合済み。parent絶対pathの自動共有は仮定しない。別環境への配置変更が必要なら、pathを再固定してinput/source再レビューする。自動探索・最新path採用なし。

PAIRS.jsonを先に固定：pair_id0..49はH50 E-U−U-U frame53..102、50..99はC50 E-U−E-E frame0..49。主要H49/C48、padding H102/C0/C1の3件を全台帳へ保持。効果・有限性・符号による選別なし。

PREPARATION-AUDITは保存JSON/bit/hash/IDの照合のみ。100全件の観測hashをselected frames原字段へ照合。f_index48/148×K1..10、unique_id/K/r/Sbitsをindex/selected/stage2 unique結果に照合。staticは各条件frame0初期prior、CのA/Bはそれぞれ元prior bitsを比較。reference_id自体を条件間で同一とは要求しない。runtimeも必要memberを逐次読み同じ前提を確認し、pair不一致は全体停止する。黙って除外しない。

観測hashはproducer run.py（SHA852c6faf72398e196b1ce969a974739ba94c4eb56a48f38d0b9504b4ae81d3fe）のy.tobytes()。FS16000/N400/hop160、中心frame×160、support中心±200、範囲外は0埋め、共通scale済み雑音付き入力のnative float64連続400標本（producer x86 little endian）。demean/window処理前。padding102も今回保存hashを個別照合した。原NPZ/波形を新しく読んで同一性を計測したとは主張しない。

元inputs.jsonにはseed20261020/PCG64、共通雑音SHA、共通scale0.004589219874983008が保存され、元run.pyは各条件でFilter()を別初期化する。Cの解釈は同じprefix/初期状態/処理条件と未来ブロックだけの違いに限定する。全grid/VUV/内部全状態・一般的な未来漏洩不存在の証明ではない。Hもmemory等の単一要因の因果効果ではない。

## Decimalと正本

stdlib Decimal、新規Context: prec256、ROUND_HALF_EVEN、Emin−999999/Emax999999、capitals1/clamp0、flags初期空。Inexact/Rounded/InvalidOperation/DivisionByZero/Overflow/Underflow/Subnormal/Clamped/FloatOperationをすべてtrap。保存十進stringからexact構築、float経由なし。256桁で足りる保証はしない。丸め/trapは全体停止、精度変更・retryなし。

X[s]=保存D[E-U,s]−保存D[比較条件,s]。I[t]=保存within-frame差g[E-U,t]−保存g[比較条件,t]だけを計算する。tはL_minus_S/E_minus_L/E_minus_S。IをXから再合成せず、I_totalを他の和へ置換しない。元D/gの数理的な関係を保存十進値の厳密恒等式と扱わない。

許可は上記有限Decimal減算、型/文字列/hash/bits/集合/順序/件数等の照合のみ。BF/特殊関数/r再算出/exp/log/LSE/再追跡、closure、KL/TV、確率変換、新gate、前段Dの符号反転追加集計なし。今回のcanonical X/Iの符号・大小比較と整数計数は許可。Decimal出力はstr、その値がzeroなら"0"。normalize/quantize/float変換なし。元の符号付きzero等は原pointerで保持。

片方frameがfull20未完なら全prior全X/Iをmissing。XはD双方finiteのみ減算し、missingを優先、他の非finiteはundefined/nonfinite_condition_contrast。Iは必要なXの両評価と双方のgがすべてfiniteの時だけgを減算する。missingを優先し、それ以外はundefined。source_fieldsで不足入力を明示。既知undefined/missingは通常出力、未知タグ・不正finite・算術trapはrun failure。∞−∞をzeroにせず、支持・元タグ一致は別bool。AをBで補修しない。

## 保存と一回運用

正本contrasts.jsonlは全100固定順、各行に3priorのX/I、元D/gタグ、支持mask、原frame member/行pointerと同一性検査結果を保持。K分布等は同じframe pointerから復元し大量複写しない。contrasts.csvは同じrecordから必要列だけ転記。summaryはgroup×main/padding×prior×quantity(X/I)×directionごとにfinite/undefined/missing件数、finiteのnegative/zero/positive件数、min/maxと該当する全pair_idを保存する。finiteが0件ならmin/maxはnull。canonical X/Iの十進文字列をexactにDecimal構築して符号・大小だけを比較し、減算や丸めを再実施しない。前段Dの符号反転集計・平均・CIは追加しない。

一回wall60秒をsupervisor入口から計測、算術deadline50秒、残り10秒を停止/reap/保存へ予約。worker1、子processなし、単体RLIMIT_AS128MiB。supervisor RSS別。tree合算保証ではない。50秒で残存workerをkill、54秒をreap目標とする。末尾保存後60秒以内・worker exit0/reaped/無signal・全100行・output8MiB以内・supervisor exit0が必要。親の外側実process waitも60秒内を確認し、post-fsync stdoutと原receiptを保持して最終採用する。

同stage2原ZIP SHAに対する共通claims-dirの排他claim、失敗でも削除しない。跨ホスト一回性は親管理。package/input/claimsと分離した新output。原結果・raw・旧failureは不変。全予定100ledgerを開始前に保存、異常時は完了/停止/未着手を残す。未reapは終了unknown、progressは観測snapshot、success不可・自動再起動禁止。

出力8MiB、通常保存前に末尾1MiBとclaim4096 bytesを予約。構造化JSONは.partialをfsync後atomic公開、raw streamは追記fsync。partial/例外は削除せず保持。member hashはストリーム確認、stage2frameはD/g等必要字段だけ投影しG/K配列を保持しない。巨大journal常駐・複写なし。実行時間/128MiB内完了は本準備では実測していない。

## 未確定・限界

入力値/pinsとpair indexは固定済み。未確定なのは独立source/inputレビュー、実行環境割当と別開始指示。原309frameは人工選択・重複窓・共有雑音。CI/p値/bootstrap/独立反復/音質/採用/全grid改善は対象外。成功時も保存十進減算に追加丸めが生じなかったという限定主張のみで、元80桁の真値精度・符号保証へ昇格しない。


## version1 準備修正

summaryの件数のみという旧制限を訂正し、確定planの許可範囲でX/I正本の符号・range・全極値IDを保存する。summary.pyは比較と整数計数だけを行い、値を再計算・再丸めしない。ゼロ件のextremaはnull、同値の全pair_idを固定順に保持。

evidence/に原producer-run.py、元inputs.json、原Filterを含むmodel.pyをbyte-identicalで同梱。EVIDENCE-MANIFEST.jsonに原出所/bytes/SHAと確認箇所を記録。独立に読むための証拠のみで、runtime import/実行は禁止。原hash定義、共通scale/雑音、各条件state=Filter()と初期化本文を確認できる。元raw/PAIRS/入力ZIPは不変。
