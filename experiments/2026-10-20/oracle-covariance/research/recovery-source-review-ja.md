# V限定回収 v2 独立静的レビュー

2026-10-20 04:35 UTC。研究コードの実行、import、tests、smoke、数値一致試験、予行runはしていない。

## 対象

親がbytes/SHA照合済みとして渡した次の2ファイルを全文静的通読した。

- refinement.py: 108beb832c01395766d95ff2c40ee814df833cfb4bc56e2b93ffcfcb14e42811
- recover.py: 6e4e8bcf13953c3af468fbcaf9433eb4bff5a5930a203cf6930185a3ba987af1
- 親が提示したv2 source manifest SHA: ed3abc454d5e540c016dcd590895b04511886fc1e07f1286e8c674ad3accf484

既存model_math.py、reporting.py、storage.py、contract.jsonも参照した。これらは元コピー不変との親報告であり、今回のローカル受領ディレクトリには新2ファイルのみ存在する。recovery-contract.json/input-manifest.json/source-manifest.jsonの実体は未受領なので、ここではその内容を自分で照合したとは主張しない。

## 結論

提示された2ファイルには、この固定388件のstrict-interior V回収を阻止する数理・静的問題は見つからなかった。以下の親確認を条件として静的通過とする。

- policyが報告どおり固定され、max_iterations=100、line_search_steps=60、convergence_kkt=1e−10、max_hessian_condition=1e12、objective_roundoff_eps=16、kkt_decrease_fraction=1e−4であり、Armijo係数が適切な固定正値であること。
- source manifestが契約・policy・入力manifestと全import対象をbytes/SHAで固定していること。
- input targetsがunique388で旧failed-V集合と完全一致し、geometry・全500pair JSON・全saved residualsと参照する旧receipt/summary/output-manifestがhash coverage内であること。
- 元gate（KKT1e−8、feasibility1e−10）・半径1.5・他モデル・σ²profile・seed/α/10000 bootstrap・資源上限は変更されていないこと。

静的通過は回収成功率、数値精度の実測認定、資源内完走、研究結論の承認ではない。

## 数理・数値精密化

1. refinement.py 17–32はsaved trainのphase energyだけから元のprofile目的、勾配、中心化共分散Hessianを計算する。testは関与しない。中心化Hessianの.5係数は正しい。
2. 23–25、61–63、73–74はwarm startと候補のstrict-interior/有限性を要求する。フルNewton targetが外側なら減衰で救わず失敗にするのは意図的に保守的な限定solverであり、誤成功にはならない。
3. 55–67は正定値性・条件数上限とNewton降下方向を確認し、regularizationによるモデル変更はない。
4. 69–88は丸め幅を固定機械精度スケールに限定し、目的関数のArmijo+slackだけでなくstrict KKT低下とstep比例の改善を要求する。小さいstepで比率右辺が丸めて1になってもstrict trial_kkt<kktが残る。目的差が丸めで見えない場合の改善を許容するが、最終KKT条件は緩めない。
5. 33–37のprojected-gradientは既存fitと同じ円板投影式。47–52の内部目標1e−10に到達した現bを記録し、90–92で元gateを保持する。現bのvalue/grad/KKTは各反復冒頭で再評価されている。
6. 93–97のσ²復元は元と同じlogsumexp正規化を保持し、非正値・非有限を失敗にする。
7. 最大100 Newton step、各60 backtrackの固定上限があり、失敗はRefinementFailureとしてhistoryを保持する。solver成功flagを旧SLSQPのflagへ偽装していない。
8. 親報告の保存b境界距離は0.583165374853033～1.4832632871408458で、全388件strict interior。調査がtrain fit diagnosticsに限定されたとの前提で、境界solver省略は妥当。境界の接線/法線符号問題はこの実装へ持ち込まれていない。

## 回収・保持・報告

- recover.pyはsource manifest SHAとlisted file hashを確認し、明示execute-recovery flag、single-thread環境、runtime versionを要求する。
- 入力listed filesを全検証してからsaved geometry/residualsを読み、信号生成関数を呼ばない。
- 元pairをdeepcopyしtargets内Vだけを置換する。元Vがfailedであることをその場で確認し、旧成功fit/scoreは呼び直さず同じPython値を保存する。JSONテキスト全体のbyte一致ではなく、保持されるbinary64値の同一性である。元ファイル自体は書き換えない。
- 回収成功Vだけsaved testでlog_densityを計算する。fit失敗・score失敗は例外と診断を残し、0点やWへ代替しない。
- recovery別成果物にoriginal_Vとrecovered_Vを併記する。失敗保存bはhistory末尾から参照できる。
- winnerは5score完備pairだけで再構成し、完全一致同点を保持する。元reporting.summarizeを使ってpaired validsetと既定stream/10000 bootstrapを更新する。
- 出力先はStoreのexist_ok=Falseで新規を要求し、旧結果への上書きを防ぐ。wall alarm/RLIMIT_AS/StoreのRSS・output guardは元契約を使い、resource stopを別statusとする。

## 非blocking留保

- ランナー自体にはtarget unique388/旧failed集合完全一致のassertがない。set化するため重複は取り除かれる。この条件は親によるmanifest静的確認とhash固定で確立する必要がある。親は別途確認中と報告している。
- 入力は最初にhash検証して後で再読するため、実行中に元入力を外部で改変しない運用が必要。元結果をimmutable扱いする今回の運用では新たな探索やモデル変更の問題ではない。
- 保持チェックはPython辞書等値であり、汎用的なfloat bit比較関数ではない。ただし値を操作せずdeepcopy後にJSON再保存する経路であり、今回の有限float値は標準json round-tripで保持される。最終成果物の独立検収で旧2112成功fit/scoreの対応・値を確認できる。
- 未回収Vが元gate1e−8を満たしていても厳しい内部目標1e−10に届かなければ失敗扱いになる。これは保守的であり、成功を捏造しない。
- 出力容量はStore管理artifactを対象とする。外部stderrを含むhard filesystem quotaでない点は既存レビューの留保を継続する。
- nats/cycleの最終表示は元保存whole-record量を64で割る既定の後処理が必要。
