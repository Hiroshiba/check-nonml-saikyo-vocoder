# Stage2 source v0 保存値算術の静的独立レビュー

## 結論

算術式・三prior・支持/欠測分岐・全20完備条件に数理上の阻害矛盾は認めない。ただしA/staticのprior pointerに、実JSON階層 `values.` の欠落がある。完全復元契約の修正点として、source確定前に直すことを推奨する。stage1結果pins未完成は意図された停止状態であり、本レビューによる起動許可はない。

対象 `/workspace/shared/pitch-stage2-source-review-20261020/package`。SOURCE-MANIFEST SHA256 `d57ca7f2f163ad3583a2b01303c42e52d3bb42da3275ec5b5f681db4df28d41e`、全20 filesのbytes/SHA一致、8 PythonのAST読取成功。候補import/実行/tests、BF・log/exp/LSE等の算術実行は行っていない。保存B入力のtag件数だけ追加読取した。

## 修正点 F1: A/static prior pointerの字段パス

arithmetic.prior は selected.jsonlから `record['values'][field]` を読むが、出力するpointerには `field='initial_prior_payload'` または `field='prediction_prior'` と記す。これらはJSON直下ではない。Sのpointerは `values.logBF` と階層を含み、Bのlog_priorはJSON直下で正しい。

A/staticだけ `values.initial_prior_payload` / `values.prediction_prior` に統一し、Bはlog_priorのままとするのが最小修正。archive/member/lineとsourceを併読すれば現状でも推定できるが、字段pointer自体が実際の読取位置を示すという完全復元契約には不足する。数値自体を変更する修正ではない。

## 算術と入力保存

- Sは保存binary64のbits/value/hexを照合し、as_integer_ratioから80桁mpfへliftする。有限binary64のdyadic値はこの精度で正確に表現可能。rやBFの再推定ではない。
- L80/A80は元文字列をcanonicalへそのまま保持し、別に80桁mpfへ読み込む。全50/80 A/Q/L六値の有限十進schemaを確認するがstage1 gateを再判定しない。Qは検証raw pointerに保持し、A/Q平均を作らない。
- L−S/E−L/E−Sは指定した引数順で独立に減算する。E−Sを他二差の和へ強制置換しない。旧kernel raw deltaとの最終桁一致を強制しない。
- mp.workdps(80)内で全保存値算術・summary比較を行う。90有効桁nstrで保存し、同精度へのroundtripを検査。80桁の真値正しさを認証するものではない。
- groupは正支持のK昇順でx=log prior+score、最大項を減算してexp逐次和、G=max+log(sum)を計算。非正和/非有限は算術事故。各K log分布はx−Gで、通常確率へ落とさない。

## 三priorと全20完備

staticは同condition/frame0 initial_prior_payloadのみ。inputsでf_index/Kまで初期行identityを照合し、prior側でもframe0/condition/initial_prior_appliedを確認する。後続帳簿zeroを使わない。

Aは当該prediction_priorをそのまま使用。正値だけlog、zeroは支持外、負値は事故。Bは当該保存log_priorを直接liftしexp→log往復をしない。BをAの支持修復と扱わない。固定保存B全6180行のtagはfiniteであり、Bの非有限入力を拒否する現在のliftはこの固定入力と矛盾しない。一般的な−infinity log priorを扱う汎用実装ではない。

frameは周波数index48/148×K1..10の全20tupleを検査。scoreが1件でも欠ければ全S/L/E評価と三方向差をmissingにし、成功Kだけの再正規化をしない。prior support mask/countは独立に保持する。現在の採用方針では不完全owner自体を拒否するため、通常受入入力にmissing frameは生じないが、schemaの意味は正しく定義されている。

## zero / missing / undefined / infinity

- 個別prior zeroは内部Noneを支持マーカーとし、K log分布ではnegative_infinity/prior_support_zero。
- 群全zeroではGがnegative_infinity、全10K分布はundefined/zero_support_group。支持側のK分布は保持。
- 片側zeroのDは向きに応じた±infinity。両側zeroはundefined/both_zero_support。
- 同一priorのS/L/Eは支持が共通なので、片側zero時の方式差は∞−∞としてundefined/infinite_minus_infinite。0にしない。
- missingは支持zeroとは別。group-levelタグの全S/L/E・両群・全Kへの展開はSCHEMAに記載。
- 本来finiteの不成立・不明tagは例外でworker全体停止。partial行を残し、精度変更・retry・事故を成功欠測へすり替えて続行する経路はない。

## 全Kとsummary分母

frame canonicalはS/L/E各G1/G2/Dと両群10成分のK log分布を保持する。group-level undefined/missingのみ定義済みの展開表現。point/frame CSVはcanonical recordの値を転記し、別計算しない。

summaryはunique単位4180、frame単位309、prior別frame単位309をscope名で分離する。unique差を6180参照頻度で重み付けしない。pair三priorの計927行を独立frame927標本と呼ばない。finite差だけの正/負/zero・min/maxは有限subsetの記述であり、missing/undefined件数は別kind。極値同値はcanonical順の先頭ID。CI/p値・平均・bootstrap・通常odds表示はない。

countsはCounterの疎な辞書なので、出現0件のcategoryはキー自体が省略される。後段表示でabsent=0と解釈する辞書仕様を明示すると安全だが、全4180/309のcanonical行とscopeから分母は復元でき、数理blockerではない。

## 禁止呼出・採用範囲の注意

arithmeticには保存値parse/lift、差・和・log/exp・LSE・条件付き正規化のみ。stage1 numerical module、hypergeometric/beta/quad/Laplace/時系列transitionの呼出はない。stage1 source ZIPはhash検査用でimportしない。

adoptは全owner完了・六値/順序/単一attempt/ledger/終了証拠の採用経路を持ち、stage1数値gateを再計算しない。未知eventを全拒否するというCONTRACT記述に対し、unique_id付き未知eventは現在明示rejectされず読み流せる点は実行境界担当へ共有すべき補強点。実rawのschemaに未知eventがあると確認したわけではない。

SOURCEと算術の静的整合は、未完成結果pinsや将来入力manifestの独立監査を代替しない。全成功・算術完了・真誤差・全grid/VUV/自然音声/音質・採用判断は未認定。
