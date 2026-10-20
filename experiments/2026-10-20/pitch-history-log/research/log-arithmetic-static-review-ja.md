# 保存logBFによるlog-domain比較の独立静的レビュー

2026-10-20。対象は log_filter.py と run.py のテキスト全体、および指定された研究設計 review.md。対象Pythonの実行、import、smoke、tests、編集は一切していない。sha256sumによるテキストの同一性確認のみ実施した。

- run.py: 36e383c78c0fa44cc34159b378a4f7235c76998b2bc796dc723b2209d594bcec
- log_filter.py: f73219b6f195d23d2ea671039a01a7a21e5a925dfa3af8252f4cf84175bb1d67

## 判定

指定された有限full-grid、固定保存入力、同じ実数数学モデルという前提では、読めたコードに限定的比較実行を妨げる算術上のblockerは見つからない。これは実行結果の正しさ、全入力検証、資源予算の実装保証、あるいはunderflowだけへの因果帰属の承認ではない。storage.py、SOURCE_MANIFEST.json、保存309フレームは本レビュー環境では未読であり、その内容・完全性は未確認である。

## 確認した整合性

1. Gaussianと行列の向き
   log_filter.py:6,10–12,28–29はF0=52..512×16000/16384、SD=2Hz、K=1..10、SD=1を使い、各source行でlogsumexpを引く。したがってrow-stochastic A/Bを有限log kernelとして直接作る。exp後に0になった値をlogへ戻す処理や追加の切捨てはない。
   49–52行では最初にsource F0を和し、次にsource Kを和する。各target (j,l) の項は sum_i,k Q[i,k] A[i,j] B[k,l] であり、A^T Q Bに一致する。F0の16列chunk化は和の対象を切り捨てず、出力target列を分割するだけである。

2. 初期値・通常遷移・正規化
   31–32,39–42行でh=.3、R=1/4610、初回Q prior=.7/4610とし初回には遷移を掛けない。51–57行の通常更新はlog(.7 A^T Q B + .4 hR)、log(.3 sumQ + .6h)。sumQ=1-hを実数上使っているため指定式と同じであり、floatで1-hを引く取消し誤差を避ける。
   58–60行で観測logBFをH1だけに足し、H1全セルとH0を一緒に正規化する。記憶再注入を一様再始動へ変えるコードはない。

3. 記憶の条件・source
   38,62–70行で使用前のmemory_frameを取得し、log h<log(.5)のときのみlogQ-logsumexp(logQ)でRを更新する。そうでなければ記憶本体とsourceを保持する。返り値sourceは今回使用した過去の記憶、出力のmemory_source_afterは今回更新後の記憶で、時点が区別されている。初回source=Noneも妥当。

4. skip
   run.py:74–80はenergy/400<1e-10の既存判定とstatusを照合する。energy_floor時にはupdateを呼ばず、Q/h/R、記憶source、last_updateを変えず、skippedという監査カウンタだけ増やす。最初の有効フレームが遅れてもmass=Noneにより初回処理になる。無音中の遷移やresetは導入されない。

5. finiteとMAP
   log_filter.py:15–17,37,61,66で入力ellおよび計算後prior/p0/Q/h/Rのnonfiniteを停止対象にする。固定full-gridに数学的zeroがない今回の前提に合う。run.py:81–83はell shapeを検査する。log_filter.py:20–23のravel(order='F')→argmax→unravel(order='F')はFortran順の最初の最大セルという指定に一致する。run.py:91–92は主指標log_MAPとexp表示のdisplay_MAPを分離している。

6. 保存と比較範囲
   run.py:57,62は3入力×103フレーム固定。既存logBFを読み、通常確率版を再実行しない。モデル・計測モジュールはimportせず、manifest対象ファイルのハッシュを読むだけである。87–99行は表示用expのunderflowを許容し、baseline hやdisplay hの微小な1超過をclipしない。
   100–108行はprior/H0、posterior、遷移/再注入項、記憶を保存し、109–117行で状態時点とフレーム別ハッシュを記録する。skip時のlog_state_joint空配列は「まだ有効更新なし」の表現で、初期h/Rは別途保存される。初回にlog_transition/log_reentryがないことも処理と整合する。

## 非blockerの注意点と具体的改善候補

- run.py:75,79: energyがNaN/Infの場合を独立には拒否しない。固定入力の事前検証済みという前提なら実害は確定しないが、堅牢化するならfiniteかつ非負を先に確認する。今回の凍結入力の内容はここでは未確認。
- run.py:89–99: baseline filtered_jointのshape/finiteとstate_nullのscalar/finiteの検査がない。異常shapeがbroadcast可能ならTV計算が無言で誤る余地がある。必要ならa.shape==(461,10)、aとahがfinite、state_nullが単一値を検査する。微小な確率1超過を認める要件とは分離し、clipはしない。
- run.py:98: raw baselineが丸めにより厳密な確率分布でない場合、TV_with_H0は厳密にはraw配列間の半L1距離である。値は保存どおり使い、報告ではこの注意と双方のmass totalを併記する。baseline totalは保存baselineから後処理で再計算できる。
- run.py:34–48: manifest検査、storage import、Budget生成、最初のexecution.json書込みはtry/finallyより前にある。そこで失敗するとfailure.jsonやbudget.finishが保証されない。計算式のblockerではないが、起動失敗を「実行されなかった」ものとして別に扱う。必要ならBudget生成後のセットアップをtryの内側へ置く。
- run.py:123–126: 途中失敗時execution.jsonはrunningのままになり得る。failure.jsonとプロセス終了も見て判定する必要がある。receiptのcompletedは個別入力完了であり、全体execution.jsonのcompletedとは区別する。

## 資源・来歴の確認限界

run.py:13–15で主要数値ライブラリのthread数をimport前に1にし、46行でBudget生成、63行でフレームごとの追加2MiB/disk検査、log_filter.py:46–50で16target列ごとのcheck、run.py:118で入力末尾disk検査、128でfinishを呼ぶ構造は確認した。chunkの主要入力配列だけなら461×16×10×8=590080 byteで、F0全targetを一度に展開することは避けている。ただしSciPyの一時配列、圧縮、JSON、manifestハッシュ読込等を含めた実ピークはこれだけでは保証できない。storage.BudgetのRLIMIT設定、壁時計制限、disk閾値、checkのextra既定値、停止動作は未読なので未確認。コメントの「import前にaddress-space limit適用」は本レビューでは検証できない。

manifest辞書に列挙されたファイルは35–37行で検査されるが、必要な全入力・全依存が辞書に含まれるかはmanifest未読のため不明。コードSHA一致だけから全入力の凍結を推認していない。

## 解釈の境界

この比較は通常算術と安定log算術の差であり、同じ実数モデルだが浮動小数点の演算順、sumQ対1-h、Rの正規化の丸めも変わる。差が出ただけではunderflowが唯一の原因とは言えない。有限log値なのに通常保存値がzeroになる位置、最初の差、候補odds、MAP、posterior距離を分け、必要なら選択セルの高精度参照で原因を絞る。

保存スキーマは後処理で候補帯域和・log odds・記憶寄与・U-U/E-U間距離を求められるが、このrunner単独では研究設計の「最初の差」「許容差内の一致」「53–101での持続」等の最終解析まで完結しない。後処理は必要であり、事前許容差を結果に合わせて選ばない。観測尤度計算そのものの安定性は、保存ellを固定するため今回の検証範囲外。

## 親レビューとの統合追記

親からstorage.py全文確認結果を受領した（本担当が直接読んだという意味ではない）。SHA a02527453ecc36036f13b3068f978b045f890d5469ee11c59dfbc9639be703ea。WALL=1800秒、RAM=2GiB、OUTPUT=1GiB、RESERVE=8MiB。Budget constructorでSIGALRM/setitimer、RLIMIT_AS soft=2GiBを設定し、既存hardを拡張しない。checkはelapsed/RSS、disk=True時はroot全filesbytes+extra+reserveを検査する。finishはtimer解除のみ。write_jsonはallow_nan=Falseでtmpを書きos.replaceする。この情報とrun.pyの呼出順を統合すると、数値ライブラリimport前に壁時計・アドレス空間制約を置く構成に整合する。

容量検査は予約でもhard disk quotaでもないため、検査後の書込みで1GiBを一時的に超過しないという保証にはならない。extra=2MiBは1フレームの実サイズ保証ではなく事前見積りであり、run.logや途中tmpも考慮する必要がある。固定461×10配列・309フレームという今回の規模に対し、静的に明白な予算超過や停止不能の欠陥は見当たらないが、実測時間/容量の断定はしない。

統合結論: 読めた二つのソースと親によるBudget確認に基づき、今回の限定的保存入力比較を妨げるblockerは検出しなかった。上記の防御的検証・失敗状態表示は改善候補、manifest/保存入力の網羅性は本担当未確認、実行結果の研究的解釈は別途必要。
