# 固定格子直接射影＋著者式posterior：実装契約

## 状態と経路選択

実装のみ。音声処理、動作試験、smoke、回帰、自己roundtripは未実施。
静的ASTの構文確認は動作・数値同一性の証拠ではない。独立した静的レビュー後にCloud Bで一回だけ使う。
Octaveが利用できないため、既存NumPy/SciPyの経路へ明示的に変更した。
依存導入、別tracker、合成器変更、再試聴、追加品質gateはない。
著者MATLAB全再現・bit一致・校正済み確率を主張しない。

## 固定値

INPUTS.jsonの5本のみ。保存済original.npyのSHA256、長さ、1次元real配列を確認する。
元コーパス未切出し全長は確認していない。パスだけ変更可能、信号/ID/hash/設定は変更不可。
Fs=16000, N=400, hop=160, FFT=16384, K=1..10, q=52..512。
実格子は50.78125..500 Hz、ΔHz=.9765625。全461×10候補が有効。
中心は元配列のsample 0,160,...で中心<len(input)。支持[center-200,center+200)、外はzero-pad。
支持の実中央はcenter-.5 sample。FFT基底原点はn-199.5。観測の平均中心化はしない。
録音全体をRMS=sqrt(3.1623e-5)へ一回だけscale。zero録音は除算せず別記。
矩形、DC列なし、epsilon=0、white経路、varSpeech=5e-6、delta=3。
初期joint=.7/(461×10), H0=.3。F0遷移SD=2Hz、K遷移SD=1、各行正規化。
C=[[.7,.3],[.4,.6]]。録音ごとreset、無音中resetなし。

## 数式と宣言差分

C[n,h]=cos(2πhq(n-199.5)/16384), S[n,h]=sin(同)。
G=CᵀCとSᵀSをfloat64で直接計算。CᵀS=0は厳密算術の対称性。
前計算でcross block・対称性・Cholesky残差・condition_2を記録する。
数値整合性boundは32 K epsilon_machine ||G||inf、cond*K*eps<1。
これは演算整合性であり音質閾値ではない。失敗時は固定支持を保てないblocker。
FFT(x)[hq] exp(+i2πhq199.5/F)のReと負Imを右辺とし、各最大次数Lをforward solve。
J(q,K)は両solveの先頭K項の二乗累積和。著者Imの符号との差は二次形式では消える。
逆行列、pinv、ridge、rank切捨て、grid削除なし。

r=J/(E+.002)。v=1,w=(400-2K-3)/2,u=200、a=(1-r)(v+w-u)、b=(u-v)r+2v+w-u。
b<0ではg=2v/(sqrt(b²-4av)-b)、他は著者の(b+sqrt(...))/(-2a)。
tau逆数=g(1-r)u/(1+g(1-r))²-gw/(1+g)²。
ell=log(g/2)+w log1p(g)-u log1p(g(1-r))+.5[log(2π)-log(tau逆数)]。
H0 logBF=0。安定正根、log1p、SciPy logsumexpは数学的同値な浮動小数点変更。
RMSもoverflow回避のscaled RMS。NumPy FFT/BLASの丸め・加算順はMATLABと異なる。
F0 GaussianはHz単位の差から計算し、共通正規化定数を除いて行正規化する。
全中心・末尾paddingは著者wrapperの末尾フレーム規則と異なる。

U=.7 AᵀQ B+.4 p0 R、u0=.3(1-p0)+.6p0。
U exp(ell)とu0をlog域正規化。初回有効frameは遷移せず初期priorを使用。
更新後p0<.5の時だけR=Q/(1-p0)と出典frameを更新。
local/baseは固定初期prior、local/log-HzはF0 priorだけ1/fで離散正規化。同じellを使用。
log-Hzをfilterへ渡さない。PMFへΔHzを掛けない。

## 欠測・失敗

E/N<1e-10はstateを更新しない。rowはenergy_floorまたはrecording_zero、配列はNaN sentinel。
観測のないNaN sentinelと計算のNaNは明確に区別。無音をH0=1と扱わず、stale stateを新posteriorとして出力しない。
有効frameの非有限値、J<0/J>E、r範囲外、g/tau非正、正規化不整合は失敗。
J>Eは丸め程度でもclipせず保守的に停止。J/E、excess、生値を記録する。
著者NaN→-inf処理は実装しない。一候補失敗も全候補の支持を変えずその入力を停止。
失敗frameと残り未処理範囲を区別。次の独立入力は処理可能。
エラーはrun.logへスタックトレース付き。JSON非有限diagnosticは{"nonfinite":"..."}として保持。
IEEE underflowはfloat64で0となり得る。posterior/priorの0セル数を保存。人工clip・候補排除とは別。
入力失敗は入力別failureと全体resultに記録。RAM/wall/output blockerは全体を停止。

## 保存schema

各recording_id/receipt.json: 入力hash/path/RMS/scale、package hash、status、total_frames、next_frame、
unprocessed_from、chunk名/hash、資源。completed receiptとhash検証済chunkは再計算しない。
chunk-0000.npz等: float64 logBF, prediction_prior, filtered_joint が(frame,461,10)。
prediction_h0, filtered_h0 が(frame,)。frame_idsは元frame ID。
各chunk末のstate_mass/state_null/state_memory、has_state、memory_frame、last_update、skippedも格納。
chunk-0000.json等: 同順のrow配列。時刻、支持、padding、energy、state_updated、memory出典、欠測理由。
E/(N varSpeech)、E/(E+N varSpeech)、Jのmin/max/excess、r/g/曲率要約、代表filtered joint MAPのJ,J/E,codと座標。
J全部の逆算可能性は仮定しない。ellからJを復元しない。
local_base/local_loghz/filteredにH0・voiced質量・K周辺PMF・joint MAP・F0 marginal MAP・全mode領域。
F0曲線は保存jointのK和（非条件付き）。条件付きはvoiced質量で割った補助表示のみ。
各modeは連続plateauを一峰として保持し峰間の最低谷plateauの中央cellを左側に帰属。
全cellを重複なく分割。単峰の領域端フラグは領域が探索端へ接することを意味し、峰が端にあることとは別。
mode SDはモデル内幅、実誤差SDではない。MAP tieはMATLAB列優先first maximum。
±50 centsはoctave表示検索だけ。mode領域全質量と同じ領域のprior質量、
logsumexp(log prior+ell)、そこから差し引くlog priorを保存。平均logBFを使わない。
予測prior比と領域条件付きBF比の和でposterior領域log oddsを分離できる。

全体grid-transition.npz: f_hz,q,k,valid_mask,A,B,C,fs,n,hop,fft。
environment.json: Python/NumPy/SciPy/platform/NumPy build/thread情報。
gram-audit.jsonl: 前計算診断。result.json: 5入力のstatusと資源。BLOCKER.json: 最終停止理由。
独立の保存結果analyzerが全frame CSVと全長図・実数値の報告を作る。このパッケージだけで報告完成とはしない。
取得済F0/VUV overlayは別成果物が存在する場合のみ。新規REAPER実行はしない。

## 上限と再開

wall=累積1800秒、仮想address space=2GiB（Linux RLIMIT_AS、RSS上限より厳しい場合がある）、実測peak RSSも2GiB監視、出力=1GiB（8MiBログ余白）。
BLAS各種threads=1をNumPy/SciPy import前に強制。グリッド間引き・install等の救済なし。
32frameごとbinary/metadataを書き、hash後receiptをatomic置換。全履歴をRAMへ積まない。
同じoutputで再実行するとcompleted入力はhash確認だけ、部分入力は最後のcommit済chunkから再開。
失敗入力はnumerical_failure receiptを保持し自動再試行しない。
累積wall予算はbudget.jsonで保持。上限到達後は自動延長しない。
プロセス強制kill等でRUNNING.lockやreceipt未登録chunkが残った場合、自動削除や再計算せず停止。
独立レビューで内容と実消費時間を確認するまで再開不可。lock削除だけで計算を継続しない。
上限は演算がOSから返るまでsignal処理が遅れる可能性がある。Cloud Bの外部hard timeoutも同じ1800秒に設定する。
最終logging/receiptのため8MiBを確保。出力サイズの事前見積りは性能保証ではない。

## 解釈の境界

局所/filteredの差はpriorと記憶の寄与。60%重複窓で独立innovationではない。
full-sequence posterior、真F0証明、校正済confidence、H0=生理無声/摩擦、entropy=noise電力とは呼ばない。
25msの低F0は少数周期、K上限と探索端、端部padding、白色残差仮定の限界を残す。
sample3 2.08–2.13秒は全長図への印のみ。追加窓/threshold/prior探索はしない。

float64でvoiced質量が全て0となる時はMAPをNoneとし、50.78125Hzを推定値として表示しない。
領域priorが0ならzero_numerical_support_or_underflowと記録し、欠測観測とは区別する。
