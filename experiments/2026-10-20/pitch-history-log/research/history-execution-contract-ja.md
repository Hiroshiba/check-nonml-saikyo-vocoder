# 3入力の履歴依存診断：実装準備契約

基準PMLは変更なし。推定機構の研究であり音質改善比較ではない。現時点はソース準備のみ。入力生成・モデル初期化・科学run・試験は未実施。実行には親の静的レビュー後の別メッセージが必要。

## 固定入力と自然5録音との差分

Fs=16000、ブロック8192 samples、全16384 samples。f*=97.65625 Hz。各倍音振幅を1に固定し、n=0..8191のphase=2π f* n/Fsに対するsin(h phase)を昇順加算する。Uはh=2,3,4、Eは2,4,6。生成したU/Eブロックを再利用し、U-U/E-U/E-Eの3本のみ。ブロックはcleanの整数周期で、位相0。境界でcrossfade等をしない。

clean理論電力=3/2。NumPy 2.3.5のGenerator(PCG64(20261020)).standard_normal(16384)を一度だけ生成し、sqrt(1.5/1000)を乗じる。名目30 dB、雑音配列は全3入力で共通。実現雑音RMSへの再調整なし。共通scale=sqrt(3.1623e-5/(1.5+0.0015))をclean+noise全体へ一度だけ掛ける。理論混合RMSをsqrt(3.1623e-5)へ合わせる契約で、実現入力RMSが同じ値になるとは主張しない。

自然5録音の録音別実現RMS正規化を、この共通理論scaleに置換するのが入力前処理の限定差分。条件別・フレーム別RMS正規化は禁止。noiseless、seed変更、SNR探索、AR、新filter、truth resetを追加しない。

## 固定モデル呼出し

既存 /workspace/direct-harmonic-posterior-job-20261019 のmodel.py/storage.py/summaries.pyをhash検証して読取りimportする。既存run.pyは使わない。モデル・既存ディレクトリは変更しない。実行Pythonは /workspace/quality-env-v1/venv/bin/python、Python3.12.14・NumPy2.3.5・SciPy1.17.0。BLAS等6種類のthread環境変数をプロセス内で1に固定。

N=400、hop=160、FFT=16384、q=52..512、K=1..10、varSpeech=5e-6、既存logBF式・Gaussian遷移・初期H1=.7/H0=.3・記憶更新を不変とする。3入力を独立初期状態から順次処理。localは既存posterior関数へ固定初期priorを渡す。log-Hz等の追加推論はしない。Jは既存Projection.costsの返値から保存し、ellから逆算しない。J>Eは丸めでも既存例外に従い停止、clip/floor/候補除去なし。

## 観測支持と保存

中心は0,160,...,16320の103個、支持[center-200,center+200)。padding=3frame（0,1,102）、境界=3frame（50..52）、前半完全支持=48frame（2..49）、後半完全支持=49frame（53..101）。境界・paddingには単一clean真F0を付与しない。定常cleanの最小周期F0はU=97.65625、E=195.3125 Hz。latent f*時計やnoisy観測の最小周期と区別する。

入力NPY、clean2ブロック、共有noise、全観測窓NPYを保存。U-U/E-Uの後半配列SHAと、後半完全支持49窓のbyte一致・両SHAを入力契約として記録。不一致は補修せず推論前に停止。終了後は保存logBFだけのbyte一致も記録し、欠測・未処理は別状態にする。

各frameのNPZに元logBF、prediction_prior、filtered_joint、local_joint、initial_prior、transition_term、memory_term、固定f*/2f*セル(q=100/200、index48/148)の全KのJ/fit/cod、全F0/K周辺質量、更新後状態checkpointを保存。初回には遷移/記憶が適用されないためNaN、初期priorを別保存する。以降の2項は更新前状態から帳簿計算するだけで、Filter.updateへ渡したり変更したりしない。保存priorとのmax絶対差を記録する。

JSONはlocal/filtered全域joint MAPのJ/fit/codと全mode、H0、energy、rho、shrinkage、記憶元、更新元、欠測、zeroセル数、固定2セル全K和と同一Kのlog oddsを保存。joint MAP tieは既存MATLAB列優先first maximum。全K和の有効証拠はprior条件付きBFで、同一Kの点対と混同しない。zero支持で未定義のlog比はnull、underflowは隠さない。CSV/HTMLなどの後処理はこのwrapperに含めない。

## 失敗・資源・実行

既存Budgetでwall1800秒・address space2GiB・出力1GiB（8MiB予約）を維持。観測energy/N<1e-10はstateを更新せずNaN payload・skip記録。数値失敗は状態を戻し、該当frameをfailureとして保存、当該入力の後続を未処理にし、他の固定入力へ進む。いずれか失敗なら全体非ゼロ終了。予算超過は全体停止。ログはstack trace付きrun.logとstderr、Python warningもloggingへ送る。既存出力は受け付けず、自動再試行・resume・再生成はしない。

実行コマンド（まだ実行しない）：

```sh
/workspace/quality-env-v1/venv/bin/python -B /workspace/pitch-prior-history-job-20261020/run.py --output /workspace/pitch-prior-history-results-20261020
```

SOURCE_MANIFEST.jsonは準備ソース・提案・契約と固定モデル依存のSHA256を記録し、実行前に照合する。source hashの照合・キャッシュ付きRuff・AST静的解析のみを準備時に許可。テスト、smoke、fixture、モデルimport実行、信号生成は準備に含めない。GitHub操作・install・公開も行わない。
