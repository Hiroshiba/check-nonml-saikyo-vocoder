# V 求積の計算量・停止条件の静的診断

2026-10-20。対象: evidence-source-review-v2-20261020/oracle-evidence-preparation/quadrature_disk.py とその数値契約。親から「実run最初6組がpartial、先頭V trainは200万評価点上限、jointはnot_converged」という通知を受けた。詳細 saved diagnostics は本担当ではまだ読んでいない。

**結論:** small 集合の作り方には、閾値を緩めず改善すべき停止条件上の過剰制約がある。また全 cell の最終再評価だけで大きな評価点予算を消費する。前者を修正し後者の重複を除く案は科学モデル・prior・精度目標を変えずに設計できる。ただしこれが今回の実runの支配原因だとは断定できず、変更後の改善も未実測である。

新しい計測、候補実行/import、tests/smoke、コード変更は行っていない。本書は次の判断用であり、進行中の run の条件変更・中断・再開を指示しない。

## 1. 現在の small/omitted gate が解けない状態を作る理由

現実装125–154行では、全cellを積分massへ含めた上で、各 upper/M<1e-10 の cell を全て small とし、Σ_small upper/M≤1e-8 を別途要求する。active risk は small を除外して集計する。

「省略していないのだから小cellの質量gateは全く不要」とまではいえない。small を active の詳細誤差判定から免除するため、その寄与を upper で管理する設計は合理的である。しかし個別閾値と集合総量閾値が連動していない。

概念例（データの再計測ではない）:

- small が200個あり、各cellの真質量が全体の0.75×1e-10とする。
- 接線upperが真質量に極めて近くても全200個は個別閾値を通る。
- その合計は1.5e-8で、集合gateは不合格。
- 同じ領域をさらに細分すると子cellはもっと小さくなってsmallに残るが、その領域の真質量は変わらない。
- 従ってこの領域をsmallのまま保持する限り、upperをいくら締めても1e-8未満にはならない。

loose envelope の締まりによってたまたま改善する状態もあるため、細分化が常に無効という意味ではない。しかし停止条件そのものに保証された進捗はなく、細分化により新しいcellがsmallへ入って総量が増えることもある。

4096 cell上限で個別閾値だけから言える総upperの上限は4.096e-7で、求める1e-8より大きい。個別1e-10という値だけでは集合gateを担保できない。

加えて selected=max(cells, risk) は small も再分割候補にする。active riskの改善が必要な局面でも、免除済みsmallへ評価点を使う可能性がある。

## 2. 精度閾値を緩めない修正候補

### 推奨: 集合総upper予算から small を割り当てる

各現在partitionで M を求めた後、upper の小さい順に並べ、logsumexpで累積upperを管理し、累積upper/M≤既存1e-8 を保つ範囲だけ small に割り当てる。残りは active に戻す。

元の個別1e-10閾値まで保ちたい場合は、まず upper/M<1e-10 の候補だけを並べ、その候補集合の中で同じ累積割当を行えばよい。これは既存smallの部分集合だけを免除するため、以前より診断を弱めない。

- small 合計upper/M≤1e-8は構成上満たす。
- smallから溢れたcellも捨てず、active riskの判定対象に戻す。
- selectedはactiveの中から最大riskを選ぶ。
- 正のcell massは従来通り全て積分へ含める。
- 全支持coverage、各上界、GL次数、GL差、別則/別座標差、2e-7/5e-7/1e-8、model/prior/Jacobianを保つ。
- 最終partitionでは再度分類・累積upper・riskを確認する。分母を更新するならどのmass基準なのかを保存する。

これにより「既に十分正確に計算した小cellの真質量が大きいこと」を永久に未達理由とせず、総量免除の範囲を越えた部分には通常の精度診断を要求できる。active risk自体は現行同様に heuristic であり、certified boundへ昇格しない。

log領域での累積比較を使い、丸めで予算を超えた場合もfail-closedとする。空集合・非有限値・cell上限・評価点上限の扱いは明示する。新しいrunで採用するなら修正後の契約と静的レビューを先に固定する。旧run結果へ黙って違うgateを適用しない。

### 代替: 全cellをactiveにする

smallを空にし全cellのriskを合計すれば、small総量による不可能な停止条件は消える。全支持を保持し、activeリスク上限1e-8を全体へ要求する保守的な案。ただし小massのloose envelopeへ多くの点を使う可能性があり、累積small方式より必ず速いとはいえない。omittedを単に0としながら元smallをrisk集計から外したままにするのは不可。

## 3. 点数予算の静的算術

初期cell数を C0、最終cell数を C とする。1回の二分でcell数は1増える。

- make(cell): tangent center 1点 + GL8の64点 + GL16の256点 =321点。
- 初期C0個と各二分の子2個を作るので、探索点数は321(2C-C0)。mode探索等は別。
- 最終partitionのGL8/16/32は64+256+1024=1344点/cell。
- angular .37分割のGL24は2×24²=1152点/cell。
- 従って最終polar照合は2496C点。
- 合計は3138C-321C0点にmode探索とCartesian照合を加えたもの。

初期半径点は最大5、角度点は最大12なのでC0≤44。Cartesian側はuが最大6区間、各uでvが最大6区間のため24/48の合計は最大36(24²+48²)=103680点。全てがこの最大数になるとは限らない。

C=600なら探索と最終polarだけで約188万点、Cartesianを加えると約200万点に近づく。これは保存データを評価せずソースのループ数から数えた見積もりで、実際に600 cellsへ到達したという報告ではない。cell上限4096より遥かに早く、200万点上限が最終照合中に作動し得る。

したがって探索が収束していても、final GL32/angular/Cartesianの時点で予算切れになり得る。探索中の難しさと「最終必須照合用の予算が残っていない」を区別する必要がある。

## 4. 数値要件を変えない重複仕事の除去

### 4.1 最終GL8/16の再利用

各現存cellはmake時にGL8とGL16を既に計算する。現在保存するのはGL16 massだけで、最終stageで両方を再計算している。

両値をcellに保存し、最終partitionで同じ順序のlogsumexpを取れば320C点の重複を除ける。GL32、angular別則、Cartesian照合はそのまま残す。この場合の点数は2818C-321C0 + mode/Cartesianとなる。約10%程度の全体点数削減であり、それだけで大幅改善や全件完走を保証しない。

計算順序や丸めの再現性を不用意に変えないため、既存のcell内結果と集計順序を保存する形が望ましい。

### 4.2 roots_legendre の次数別キャッシュ

同じGL次数のnodes/weightsを多数のcellやCartesian inner loopで繰り返し求めている。必要次数のnodes/weightsを固定の小さなキャッシュとして再利用する。評価点数自体は減らないが、求積則生成のCPU負荷と一時確保を減らせる。最終node/weight/次数を変えない最適化。

### 4.3 small判定の集合操作

active=[c for c in cells if c not in small] は辞書同士の等価比較を使った線形探索を各cellに行う。smallが多いと各iterationで二次時間となる。cellの安定ID/indexまたは一回の分類でactiveを構成すれば、意味を変えずにこの負荷を除ける。累積small方式ではソートを伴うが、辞書リストの全照合を避けるだけでも構造は明確になる。

### 4.4 既に必須gate失敗と分かった後の高価な照合

最終GL8/16/32差が未達なら、既定gateの下でそのpartitionの成功は不可能。未達を保存して高価なCartesianを「未評価」とする早期停止は、成功判定を弱めず無駄を減らせる。ただし診断欠測の表現を明示し、未評価を合格扱いにしない。これは既存診断出力の完全性を変えるので、最小の修正候補より優先度は低い。

## 5. すぐには勧めない変更

- 200万点・30分・精度閾値を事後に緩めること。
- 別座標照合や全支持coverageを黙って省くこと。
- 小cellのupper総量を記録せず捨てること。
- 今回の6組の失敗を見てprior支持やmodelを変更すること。
- 収束差を真誤差保証と読み替えること。

最終高次数をsmallで省略する案はあり得るが、各則の省略影響を同じ予算内で扱う追加設計が必要。単純なキャッシュ再利用と異なり、本書ではそのまま採用可とはしない。

## 6. 今回の実run原因を切り分ける既存証拠

欲しいものは各Vのstatus/reason/evaluations、cells、partition_refinement_log_mass、active_log_risk_ratio、omitted_ratio、levels、alternate、cartesian_log_j、例外stackである。

- omitted>1e-8だけが未達なら第1節の停止条件が直接の候補。
- active riskも大きいならloose envelope/未解像cellの探索問題が並存。
- partition gate通過後のstackで予算切れなら第3節の最終照合点数負担が候補。
- Cartesian差だけが未達なら別座標の解像度が主因候補で、small修正では解決しない。
- mode/KKT失敗ならさらに別問題。

予算例外経路では途中meshを保存しない旧設計なので、一部の値は既存成果物に存在しない可能性がある。未保存のcells/risk/omittedを推測で補って原因を断定しない。未達はそのまま保持し、今回のrunと今後の修正版を区別して報告する。

## 7. 次の判断に向けた優先順位

1. 既存診断で未達stageを確認する。現在のrunは当初条件の結果として保存する。
2. 次版案として、個別1e-10候補の中で累積upper≤1e-8となるsmall部分集合を割り当て、溢れたcellはactiveへ戻す。selectedはactiveに限定。
3. 同時に既存GL8/16値と次数別GL則をキャッシュし、不要な辞書集合照合を除く。
4. 修正差分、閾値不変、各失敗gate、全支持とdiagnostic provenanceを静的に再レビューする。
5. 新しい実行判断は別途行う。本書は追加runの実施や成功を意味しない。

## 8. 修正版到着前の追加不変条件（06:02 UTC）

親通知: run-001 は392積分成功、96未達（V評価点上限92、診断4）、earlystop2、未試行4510、BMA0で終端。これは親の実行報告であり、本担当の再計測ではない。途中の手動SIGUSR1停止は27分の自然な時間切れと区別して外部来歴に残す必要がある。

### 8.1 接線upperはpolar変換でもmass上界か

実数演算では上界である。log kernelをell、cell内の評価点をc、gradientをgとする。凹性より全bでell(b)≤ell(c)+g·(b-c)。sector内のg·b最大は半径両端と角度両端、gradient方向が角度区間に含まれる場合のその方向で得られる。現コードはこれを列挙する。

U=area×exp(ell(c)+max_sector g·b-g·c) は ∫_sector exp(ell(b)) db の上界。polar座標では db=r dr dθ であり、area=(r1²-r0²)(θ1-θ0)/2 を使うのでJacobianは落ちていない。prior係数はellに含まれる。

GL radial×angularのweightsは正で、rを含むweight総和はこのareaに等しい（radialの一次式をGLが積分する）。angular .37分割則も両区間の面積を足す。同じ点wise upperから、各GL cell massもU以下。従ってsmall集合を積分へ含めたままでも、真massと当該求積massは双方[0,ΣU]に入り、絶対差はΣU以下である。別々にΣUを足して2ΣUとする必要はない。

全て実数演算での説明であり、計算された接線/面積/weightsの丸めを含むcertified boundではない。現行のhigh>upper+1e-7不整合gateを維持する。

### 8.2 分類分母と最終mass

現在partitionのM16を用いてsmallを選び、最終M32に対してrelative omitted≤1e-8と呼ぶ場合、分母は同じではない。固定したsmallのU合計について

U/M32=(U/M16)×exp(log M16-log M32)。

既存のGL差gate≤2e-7が通っても、境界ぎりぎりの1e-8は最大exp(2e-7)倍になり得る。誤差目標に対しては極小だが、数値閾値の字義どおりの不変条件には再検査が必要。これはtangent上界やキャッシュの正当性が崩れる問題ではない。

最小の扱い:

- 各iterationで、同じ現在partition/M16に基づき個別1e-10と累積1e-8を評価し、分類とactive riskを保存する。
- 最終値をM32基準として報告するなら、固定subsetの個別ratioと総ratioをM32でも検査し、超過を成功扱いしない。
- 最終段階でsubsetを選び直す案も可能だが、そのときは新activeのrisk合計も必ず再計算してgateする。subsetだけ縮小して旧active riskを流用してはいけない。
- 最小修正としては、最終再検査失敗をnot_convergedとして明示する方が、最終stageで未設計の再refinementを始めるより単純。
- M16を分母とする既存の「運用診断」をそのまま保つなら、分母をM16と明記し、M32に対する厳密なratioだと報告しない。どちらを採るか契約で固定する。

M16も数値求積であり、これは厳密な正の本体lowerによる保証への昇格ではない。既存の「非certifiedな収束診断」という解釈を保つ。

### 8.3 キャッシュとrefinementの正確な不変条件

1. GL8/16 cell cacheのkeyは同一の半径/角度端点tuple、次数、offset設定、当該積分のstatistics/geometry/priorに結び付く。最も安全なのは積分呼出内だけのcell objectに保存すること。他pair/train/jointへmass cacheを共有しない。
2. make時のlow=GL8、high=GL16をそのまま保存し、最終現存partitionの同じ順序で集計する。削除済みparentのmassをchildrenと一緒に足さない。分割前parentの結果をchildへ流用しない。
3. childrenを二つとも正常に作成した後でparentを置換する。途中予算例外時には最後の完全なpartitionを保持するか、少なくとも診断を「未commitの分割中」と明示する。片方だけ作成済みを全支持partitionと呼ばない。
4. 各refinement後、coverage、現在cell数、M16、small subset、small upper総量、active riskは同じpartition revisionに属する。small/active分類は新しいM16で再評価する。
5. selectedはactiveのみ。ただし必須finite/符号gate、4096 cell上限、200万評価点上限はそのまま。例外時に許容値を緩めたり全候補成功としない。
6. roots_legendreのcacheは固定次数→nodes/weightsの小規模辞書でよい。node/weight配列は読み取り専用として扱い、in-place座標変換で破壊しない。使用する次数、Jacobian、offset、weightsに変更なし。
7. 既計算mass cacheの再利用では新しいkernel評価は行わないのでevaluation countは増やさない。新しいchild、GL32、angular別則、Cartesian等の実評価は従来通り全点数を加算する。cache導入で評価点上限の定義を曖昧にしない。
8. 最終GL32、angular GL24、Cartesian24/48、各finite/差gate、history gateを維持する。cacheを「もう収束しているはず」という理由に使わない。

### 8.4 予算例外に残す最小診断

例外で取得できなかった数値を作らず、最後に完了したstageのsnapshotを保存する。

- stage: mode / initial_cells / refinement_children / final_GL32 / final_angular / cart24 / cart48等。
- 最後の完全なpartition revision、cell数、直近history、M16、small数/upper総比、active数/log risk。
- そのsnapshotの時点と、最終失敗時のevaluation countを区別する。
- 完了済みlevel/alternate/cart値だけを保存し、未評価項目はnullと未評価理由を残す。
- 現在のrequested node数と、評価を実際に済ませた点数を混同しない。Budget.tickが呼出前に加算し上限超過を送出する場合、表示countはattempted点数になり得るのでその意味を明示する。
- status/reasonはevaluation_budget_exhausted、cell_budget_exhausted、manual_early_stop、natural deadline等を来歴で区別する。旧runのラベルを書換えるのではなく外部receiptで補足する。

これは新規計測を要求するものではなく、次版sourceで例外時のdiagnostic provenanceを壊さないための仕様案。現runで未保存の値を復元できたと主張しない。

## 9. 実診断通知による原因の更新とCartesian refinement案（06:03 UTC）

親から詳細診断の通知を受けた。ここでも本担当がデータを再計測したわけではない。

- 92件の評価点予算例外は、89件がfinal angular別則GL24、3件がCartesian段階。
- 4件のnot_convergedはいずれもjoint/V、IDはW000、A000、A004、W007。
- cell数は538、571、565、549。
- omitted比は約1.1–1.3e-9で合格。active log riskも約-18.42～-18.44で合格。
- polar GL8/16/32とangular別則は約1e-12で一致。
- Cartesian24と48の差は約1.18–1.31e-6で、2e-7 gateを通らない。

**従って今回観測された主要因は最終照合の点数負担とCartesian24/48の収束差である。第1節のsmall停止条件問題は静的に存在するが、今回の保存診断で原因として観測されていない。** 累積small修正の妥当性と、実runの原因診断を混同しない。

厳密には24/48差だけでは「24だけが誤りで48は正しい」とは証明できない。48とpolarの差も十分小さい証拠があれば24側未解像という見立てが強まるが、高次数refinementは引き続き必要な収束診断であって真誤差保証ではない。

### 9.1 事前固定する最小の追加階層

Cartesian次数列を24,48,64,96と固定し、24/48は必ず計算・保存する。

- 最初の24/48が既存条件を通れば追加なし。
- 通らないときだけ64を追加する。
- 48/64の差≤2e-7、最新64と最終polarの差≤5e-7、他の既存gateが全て合格なら終了。
- それでも通らないときだけ96を追加する。
- 64/96の差≤2e-7、最新96とpolarの差≤5e-7、他の既存gateが全て合格なら終了。
- 96でも未達、非有限値、または200万点/時間予算不足なら未達をそのまま保存する。

全次数値、隣接差、採用次数、最新値とpolarとの差、追加理由、停止理由を保存する。fail-openを復活させない。原点/境界/mode-aware分割とJacobianも変更しない。

これは精度閾値を緩めるものではないが、旧契約の「Cartesian24/48差そのものが必須合格」から「固定階層の最後2次数差が必須合格」への数値手順変更である。実行前に契約版と静的レビューを固定する必要がある。旧runの4件を遡及して合格扱いにする変更ではない。

24/48を失敗した時点で既に元gateは未達なので、追加計算は正規の求積refinementとして位置付けられる。低次数を消したり最良に見える2次数を選ぶのではなく、固定順序の隣接する最後2次数のみで判定する。

### 9.2 Cartesian点数上界

現在の分割方法はu最大6区間、各uでv最大6区間なので、次数qの点数は最大36q²。

- 24:20,736点。
- 48:82,944点。
- 24+48:103,680点。
- 64追加:147,456点。24+48+64は251,136点。
- 96追加:331,776点。全4次数は582,912点。
- 128追加:589,824点。全5次数なら1,172,736点。

これは分割数上界による静的点数であり、実際の各積分で必ずこの点数になるとは限らない。境界付近のclipや重複edge除去で少なくなる場合がある。

GL8/16 cache後のpolarを含む合計は2818C-321C0にCartesianとmode点数を足したもの。例えばC=550の場合、全4次数のCartesianを最大まで使うと合計は約212万点になり得る。従ってcache導入後でも64/96追加が常に200万点に収まるとは限らない。64で通ればより小さな負担で済む。

128は1次数だけで約59万点を追加し、この予算では負担が大きい。今回の最小案には入れず、96未達を正直に残すことを推奨する。128が数理的に不適切なのではなく、現証拠と固定資源の下で自動的に増やす理由が不足している。

各追加次数を始める際、残評価点/時間を把握し、上限超過時は未達のstageを記録する。点数上界の見積もりを理由に既存予算を増やしてはならない。実装で実際のu/v区間数を事前計数する場合も、それは次版の同じ研究求積内の資源管理であり、ここで追加計測したという意味ではない。

### 9.3 判断の整理

優先する最小修正は、GL8/16再利用・GL則cacheによる既知の重複除去、small集合の論理修復、必要時のみCartesian64/96へ進む固定refinementである。科学モデル/prior/支持・主要数値閾値・評価点200万上限は保持する。追加階層が今回の全未達を救済するという保証はしない。

## 10. run-001 の既存V成功2件の再利用判断（06:05 UTC）

実results.jsonを標準ライブラリjsonで読み、A-001/train/VとW-004/train/Vの保存値を確認した。候補import、求積再実行、旧meshの再構成、新しいtestsはしていない。

### 判断: 条件付きで再利用可

科学モデル・入力statistics/geometry・prior・支持・integrand・log I定義が同一で、各slotに旧source/gateとrun-001の来歴を保持するなら、旧版で成功した2件を再利用することは数学的に妥当である。新法の収束成功や新gate適用済みと呼んではならない。新法とbit単位で同じ答えを返す保証でもない。

確認した保存値:

- A-001/train/V: status=converged、log I=-2855.072870914435、GL16/32の保存log Iはともに同値。GL8との差は約1e-12。omitted_ratio=1.2616964018926798e-9。active_log_risk_ratio=-18.424370677114354。cells589、evaluations1,938,790。Cartesian24=-6.926389708236583、48=-6.926389748292067で、差は約4.01e-8。保存partitionのlog J16=-6.9263897482920935との差も約3e-14。
- W-004/train/V: status=converged、log I=-2847.130321633916、GL16/32の保存log Iはともに同値。GL8との差は約1e-12。omitted_ratio=1.3387518632884594e-9。active_log_risk_ratio=-18.436005289532744。cells597、evaluations1,963,750。Cartesian24=-6.957572519941256、48=-6.957572543919294で、差は約2.40e-8。保存partitionのlog J16=-6.957572543919307との差も約1e-14。

両件ともomittedは1e-8の約13%以下で十分余裕がある。M16→M32の共通shift付き保存値が等しいことと、運用gateの2e-7という上限を考慮しても、この分母変更がomitted比を1e-8まで押し上げる見立てにはならない。ただしshift適用後の丸めで差が隠れる可能性まで厳密保証したわけではなく、丸めを含むcertified証明とはしない。

旧small集合は各cell upper/M16<1e-10を満たす全候補で、保存された総比が既に1e-8より小さい。同じ旧partitionと値を固定して累積方式を考えると、全候補を小さい順に追加しても全体が予算内なので、累積方式は旧small全件を収容できる。その意味で「新方式が要求する累積upper予算に旧成功が明らかに反する」ことはない。旧meshは未保存なので、cell単位の再分類・接線upper再検算はしておらず、その実施を主張しない。最終M32基準の個別1e-10境界を各cellで再確認することもmeshなしではできない。

新しいCartesian階層は24/48が合格した場合に64/96を追加しない設計案であり、両件は24/48段階で十分条件を満たしている。GL8/16 cacheは同じ数値の再利用、active-only refinementは次の探索経路の変更であり、旧版で既に得た合法な積分推定値を無効にはしない。

再利用の前提:

1. 入力indexと該当残差/geometry hash、slotのmodel/train-joint識別、N/K/L、prior・shape支持・共通scale測度が同一。
2. 旧slotのstatus、log I、levels、alternate、omitted、全diagnosticsを保持し、旧source-manifest SHAとrun IDを明記する。
3. source最新版で計算済みと塗り替えない。集約結果には複数数値実装版を含むことと、旧gate合格値のreuseであることを記す。
4. 未達のV、budget/earlystop slotを流用成功へ昇格させない。
5. 5モデルのweight/BMAには同じ科学的定義のlog Iだけを集め、各必要slotが成功条件を満たした時だけ確定する。数値版の違いだけで候補を落としたり再正規化しない。
6. 証拠が後から矛盾した場合は該当slotの利用を再検討する。今回の静的効率問題はこの2成功を無効化する数式バグではない。

手動早期停止の外部来歴はrun全体に保持するが、それ以前に完了した上記2slotのconverged状態を時間切れへ書換える必要はない。再利用は新しい科学runの実施許可そのものではない。

## 11. 局所強凹性によるV上界改善の数学的候補（06:29 UTC）

親通知では現行回収runでもV予算未達が続いているが、今回の詳しいstage診断は未着。本節は数理検討のみ。新しい計測、候補実行/import、tests、実装変更はしていない。次の変更を採用/実行する指示でもない。旧runの原因を自動的に今回へ転用しない。

### 11.1 共分散下界の導出

保存geometryをz_l、Fmax=max_l||z_l||、anchor cでの位相確率をp_c(l)∝e_l exp(-c·z_l)とする。零energyの位相は全bで確率0なので、比は正energyのsupportだけで考える。

||b-c||≤δなら、Δ=b-cとして

p_b(l)/p_c(l)=exp(-Δ·z_l)/Σ_j p_c(j)exp(-Δ·z_j) ≥ exp(-2δFmax)=κ。

これは丸めた||z||を1と決めつけず、実geometryのFmaxを使う式である。任意のベクトルvについて、分散の変分表示より

vᵀCov_p_b(z)v=min_a Σ_l p_b(l)(v·z_l-a)²
≥κ min_a Σ_l p_c(l)(v·z_l-a)²
=κ vᵀCov_p_c(z)v。

従って Cov_p_b≽κ Cov_p_c。Hessian ell=-h Covなので、μ=hκ λmin(Cov_p_c)≥0に対して

ell(b)≤ell(c)+g(c)·(b-c)-(μ/2)||b-c||²。

二階微分の積分形でc→bの線分全体に同じμを使えば得られる。sector自体が非凸でも、線分は中心cのδ-ball内にあり、確率比下界はそのball全体で成立するため問題ない。境界modeでもg(c)を0にする操作は不要。線形F項はHessianに影響せず、gradientには保持する。

λmin=0等ならμ=0で既存の接線に戻る。半正定値性を数値上強制するため正のfloorを入れるのは不可。

### 11.2 sectorに対するδと境界geometry

現行sectorをr∈[r0,r1]、θ∈[θ0-a,θ0+a]とする。現行初期幅と二分から2a≤π/4。anchor c=rc e_r、rc=(r0+r1)/2、e_r=(cosθ0,sinθ0)。

δ²=max_{r∈{r0,r1}} [r²+rc²-2r rc cos a]。

距離二乗はrについて凸、角度偏差についてこの範囲で端点が最大なので、上式がsector全域の最大距離。r0=0の中心sector、r1=Rの境界sector、periodic seam隣接sectorでも成立する。seamは現行の各非跨越intervalで扱う。

### 11.3 次に検討する一案: 局所二次上界のrectangle積分

次候補は主求積やCartesian法を置換せず、cell upperだけを強化する方法に絞る。

局所座標x=b·e_r、y=b·e_tにおいて、sectorは次のrectangle内に入る:

x∈[r0 cos a,r1]、y∈[-r1 sin a,r1 sin a]。

μ>0ならm=c+g/μ、A=ell(c)+||g||²/(2μ)と置いて二次上界はexp(A)exp(-μ||b-m||²/2)。そのrectangle積分は二つの1次元Gaussian区間積分の積となる:

U_quad=exp(A) × ∫_[xmin,xmax] exp[-μ(x-mx)²/2]dx
                   × ∫_[ymin,ymax] exp[-μ(y-my)²/2]dy。

sector内でell≤二次式、rectangleはsectorを含み、積分する二次式の指数は非負なのでU_quadは実数演算でmass上界。rectangleのsector外部分で二次式が真ellを上から抑える必要はない。そこでは真密度でなく同じ正の上界関数の積分域を広げているだけである。

U_new=min(U_tangent,U_quad)とすれば、既存上界より悪くならない。同じ局所二次式のsector最大×面積も補助上界になり得るが、最初の実装候補に複数の複雑な極値処理を増やす必要はない。

anchorでのgradient/covarianceは現boundsが既に計算して捨てているので、その値を利用できる。追加kernel nodeが必須な案ではない。ただしGaussian区間積分、eigenvalue、幾何計算のCPU負担は増え、cell数/総時間が減る保証はない。

上界が締まればupper/high>4で大きいままのriskが縮み、同じGL差判定へ早く移れる可能性がある。small分類にも同じ新upperを使えるが、全支持・正weights・個別1e-10/総1e-8・active risk・最終GL/Cartesian各gate・200万点上限は保持する。riskは引き続きheuristicで、上界改善だけで精度達成を主張しない。

### 11.4 浮動小数点の重大な留保

この導出はreal-arithmeticで厳密だが、通常float64実装をcertified upperと呼ぶ根拠にはならない。特にCovをE[zzᵀ]-E[z]E[z]ᵀで計算したλminの過大評価はμを過大にし、上界を不正に小さくする可能性がある。区間演算等で安全方向を保証しない限り、従来同様に解析式に基づく非certified数値診断と表示する。

μが極小だとm=c+g/μとAが巨大になり、exp(A)と極小Gaussian区間確率の相殺が危険。log領域で安定なGaussian区間積分を扱い、直接CDF差のunderflowやAのoverflowを合格へ通さない。数値的に安全な二次上界が得られないときは既存tangent upperへ戻す。誤って0の上界を採ることは不可。正のλminのfloor、gradientの0化、underflow値を正しい上界と見なす操作は禁止。

既存high≤upper+1e-7の整合gateと有限性gateは維持すべき。これらは検出補助であり、不正upperが常に検出される証明ではない。

### 11.5 より単純な候補との比較

- 二次上界の最大密度×sector面積だけ: 実装はGaussian積分より単純だが、狭い峰がcell内にあると面積×最大値という過大評価が残る。既存上界の幾何的弱点を十分に除けない可能性。
- Cartesian主領域のadaptive化: 可能だが主partitionと独立照合の役割、全支持coverage/上界を再設計する範囲が大きい。今回の限定候補にはしない。
- 正weightsのGL値をそのままupperとする方法: 一般には不可。正weightsは正の推定massを与えるだけで真積分との誤差符号を保証しない。log-concavityだけから任意GL則が上界になるとはいえない。pointwise上界にweightsを掛けて得るupperなら可能だが、元の上界の導出が別途必要。

**選ぶ候補は局所強凹性＋回転rectangle Gaussian積分によるcell upper改善の一案だけ。** ただし詳細stage診断が「極端に多いpolar cellsとloose envelopeが最終照合点数を消費」する見立てを支持した場合に限り、次の設計審査へ進める。Cartesian単独の未解像や別の資源失敗が中心なら、この案を採用する理由は弱く、着手判断を保留する。

### 11.6 五つの仮想役割からの批判チェック

以下は一人のレビューを五つの観点で整理したもので、独立した5人の実レビューではない。

1. 数学担当: 共分散変分下界と線分上のHessian boundは成立。実norm Fmaxとsectorのδを過小評価しないことが前提。局所anchorは必ずしもmodeでなくてよい。
2. 数値解析担当: 最も危険なのはλmin過大評価とGaussian区間確率の相殺。real-arithmetic証明を浮動小数点certificateへすり替えない。安全なfallbackなしには採用不可。
3. 計算量担当: anchor covarianceの再利用で追加kernel nodeは不要でも、区間Gaussian計算のコストはある。cell削減と最終照合点数の削減は未実証。200万点枠を増やす理由にはしない。
4. 科学・来歴担当: prior/integrand/支持は不変だが、upper/riskに用いる診断機構は変わる。source/契約を新しい版として固定し、旧結果を新gate合格へ遡及しない。
5. 境界・反例担当: 原点sector、外円境界、seam、零energy位相、低rank covariance、μ→0、強い境界gradientを必ず仕様で扱う。modeでgradient=0とする近似や、rectangle外側の真ell評価を不要なのに仮定する証明は採らない。

## 12. より単純な候補: tiny-cell高次数を省き上界を比較budgetへ課す（06:32 UTC）

紙上比較のみ。採用・実装・新しい計測はしていない。実small_count/active_countが未着なので速度効果は未判断。

### 12.1 絶対差の上界

最終partitionのsmall集合Sを固定し、U=Σ_(i∈S)U_iを接線mass上界の総和とする。正weightsとsector面積の恒等式から、任意の対象GL則qのsmall mass Q_(q,S) とcached GL16 mass Q_(16,S)は双方[0,U]に入る。

activeだけを則qで計算し、smallにはcached GL16を足すhybrid積分を

H_q=Q_(q,active)+Q_(16,S)

とする。全cellを則qで評価した仮想のfull-rule積分F_qとの差は

|F_q-H_q|=|Q_(q,S)-Q_(16,S)|≤U。

各small cellごとに絶対差≤U_i、全体でも≤U。2Uとする必要はない（より保守的な2Uを使うのも可）。このF_qは数学上の比較対象であり、未評価なら「計算済み」と報告しない。

### 12.2 log差への正しい変換

H_q>Uを要求し、L_q=H_q-U>0とする。F_q≥L_qなので

|logF_q-logH_q|≤log(1+U/L_q)=-log(1-U/H_q)=β_q。

より一般に0<L≤min(H_q,F_q)と分かっていればlog(1+U/L)でもよい。単にU/M16≤1e-8だからlog誤差も無条件に同じと置くのは不十分で、対象H_qに対する正の分母を確認する。

二つのfull-rule差を保守的に検査するには

|logH_p-logH_q|+β_p+β_q≤既存閾値

を要求する。未計算のfull-rule差を閾値内と見なせる実数演算上の十分条件になる。βの分だけ観測差に許される余地は小さくなるので、閾値を緩める方法ではない。

### 12.3 最小のhybrid構成と全比較への課金

GL8/16は既に全cellでcacheされており、そこをhybridへ変更する必要はない。全cellのGL8/16をそのまま使い、β8=β16=0とする。

- GL8対GL16: 現行どおり差≤2e-7。
- GL16対hybrid32: 観測差+β32≤2e-7。
- hybrid32対hybrid angular別則GL24: 観測差+β32+βalt≤5e-7。
- Cartesian最新値対hybrid32: 観測差+β32≤5e-7。
- Cartesian最新2次数間: fullsupportのまま、現行どおり差≤2e-7。
- partition historyはfull GL16のまま、既存の最後2差gateを維持。

smallのcached GL16がhybrid32/alternate間で共通だから観測差から消えることは事実だが、それを誤差0と扱わない。上記β課金が必要。full-rule同士のsmall差に直接Uを用いるさらに鋭い式も導けるが、最初は各βを足す簡潔で保守的なtriangle boundを使えばよい。

hybrid32を最終log Iとして出力するなら「active GL32 + small cached GL16」と明記する。全cell GL32を評価したとは書かない。最終hybrid値自体は正weightsで全支持を積分する別の求積近似であり、科学的integrandは変わらない。参考値としてfull-ruleとの差≤β32を保存するが、真積分とのcertified errorと混同しない。

### 12.4 small集合と分母を凍結する条件

最終高次数評価の前にS/activeを固定することが重要。hybrid32後にSを選び直して、未評価cellがactiveへ戻ったのに「GL32評価済み」と扱うことは不可。

単純な手順案:

1. 現行GL16基準の個別1e-10/累積1e-8から最終Sを選び、S/activeのidentityとUを固定する。
2. activeのGL32/alternateを評価し、H32/Haltとそれぞれのβを計算する。
3. H32-U等の正の下限を使い、固定Sの総upper/個別upper/active riskを最終の保守的分母で再確認する。例えばU/(H32-U)≤1e-8、各U_i/(H32-U)<1e-10は、未計算F32基準の条件を保守的に担保する。
4. 失敗した場合はnot_convergedを保持するか、別途事前固定した再分類・追加評価へ進む。集合だけ変えて既存cacheやriskを流用しない。最小案では明示未達が単純。

H_q≤U、非有限、log差計算不安定はfail-closed。log U、log Hを保持し、log1p/expm1等による安定な差を使う仕様が必要。直接massをexpして0へunderflowさせ、その0を正の下限や厳密なUとして用いるのは不可。

### 12.5 実数演算の厳密性とfloat64の限定

Uが真の上界なら以上の比較換算はreal-arithmeticで厳密。現行のUは浮動小数点の接線/gradient/面積から計算されるため、その丸めまで保証したcertified errorにはならない。もともとの非certified収束診断という限定を保つ。

通常の正GL値自体を上界に昇格させるのではない。独立に導いた接線Uを使って未評価高次数の影響を明示課金する点が重要。βを記録するだけでなく、各該当gateの左辺に実際に加算する必要がある。

### 12.6 点数削減と候補優先度

現cache版の最終polarコストは2176C点（GL32:1024C、angular別則:1152C）。hybrid案なら2176A点、A=active数。削減は2176S点。Cartesian fullsupportの点数は変えない。

例えばC=600、S=500という仮想構成なら1,088,000点削減になるが、これは実診断値ではない。Sが小さければ効果も小さい。まずactual small_count、active_count、final stage/必要点数を読む必要がある。

この案は新しいHessian下界やGaussian CDFを導入せず、既存接線上界だけで精度予算を保守的に配分するため、smallが多い場合には第11節の局所強凹性案より先に審査すべき。強凹性案を同時に積み重ねず、まずこのhybrid案一つの採否を診断から判断する。

契約は「全cell GL32/alternateの実評価」から「smallの未評価差をU由来βで課金したhybrid照合」へ正直に更新する必要がある。閾値、prior、支持、評価点200万上限を変えずに保守的な比較条件を維持できるが、旧契約のまま全GL32が計算済みという表示はできない。今のsource/runにこの変更を採用したという意味ではない。
