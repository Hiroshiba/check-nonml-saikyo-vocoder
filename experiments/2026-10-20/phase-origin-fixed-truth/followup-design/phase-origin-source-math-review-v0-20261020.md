# Phase source v0：独立数理・静的監査

2026-10-20。対象 `/workspace/shared/phase-origin-source-review-v0-20261020/package`。主対象は `source/model.py`、`source/calibration.py`、`CONTRACT.md`、`SCHEMA.json`、`INPUT-MANIFEST.json`。呼出し・保存接続の必要箇所だけworker.py、storage.pyを読んだ。候補import、実行、数値計算、tests、smoke、source修正は一切行っていない。

## 判定

**現版は修正待ち。開始可とは判定しない。** 数学的な平均、OLS係数、多項式化、各truthの有限窓密度に式の誤りは見つからなかった。ただしRN64変換が非有限mpfをzeroへ変換し得るため、失敗契約に違反する。固定truthの通常評価が実際にその経路へ入るという主張ではないが、静的に明確な誤動作なので修正が必要である。

二精度一致・root分類・残差検査はいずれもnoncertifiedの範囲。global minimizer認証や理想生成lawとの厳密一致には昇格しない。局所Fisher参照を計測仕様へ追加する必要はない。

## 1. 修正必須：rn入力の非有限検査

model.py L16–22のrnは、x._mpf_を通常の有限数としてFractionへ変換した後、出力floatだけにisfiniteを要求する。

pinされたmpmath 1.3.0の `libmp/libmpf.py` をファイル読取りで確認すると、特殊値は

    fnan  = (0, 0, -123, -1)
    finf  = (0, 0, -456, -2)
    fninf = (1, 0, -789, -3)

というzero mantissaの符号化である。したがって現rnはこれらを有限zeroのFractionへ写し、末尾のisfinite検査を通してしまう。q/h等で非有限が生じた場合に、そのままzeroへ隠され得る。v/Pminusの正値検査だけではq/hの異常を検出しない。

**要求**：tuple分解前に入力mpfの有限性を明示検査し、非有限ならGateで失敗させる。有限mpfからfloatへのoverflowについても、owner停止とpair数値失敗のどちらへ分類する契約か明確にしておく。今回の指摘確認には特殊値を候補関数へ入力する実行を用いていない。

依存source読取場所：
`/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages/mpmath/libmp/libmpf.py` の定数定義。実ファイルhashの再計算・dependency全件監査は本担当の範囲外。

## 2. 平均、真θ、geometry

- qの積形式とFourier正本は代数的に一致。q′は `4π sin³(πu)cos(πu) envelope − 0.6π sin⁴(πu)sin(2πu)` のc倍であり、hの−1/c_dも正しい。
- u∈[0,1)ではsin(πmin(u,1−u))=sin(πu)。h内のcos(πu)を保つことで微分の符号は正しく、minの折返しを誤微分していない。
- INPUTの5truthは計画の値と一致。a/τ²をbinary64化し、sigma2/bから80dpsのvを構築してRN64する区別はCONTRACTに明記されている。
- Zφは当該位相64値から作る。Pminusは丸めvとbinary aから周期初期分散を近似評価して丸める。scoreのP0はa²Pminus+v0。これは明示された丸めGaussianの入力契約であり、厳密周期定常実数法則と無条件に同一ではない。
- 生成はφ0=0だけなので64周期効果を用いることは整合。推定側はFractionのmembershipから部分周期を作る。両端の効果共有、部分周期再norm、truth分散再校正は見られない。

## 3. OLSから多項式、gate

cos(h(x_n+x))の展開からA_h=−2c_hΣY cos(hx_n)、B_h=+2c_hΣY sin(hx_n)となり、実装の符号は正しい。位相非依存定数ΣY²−96ΣY/√4081+Nも正しい。

F′_xのLaurent係数はz^hにh(B_h+iA_h)/2、z^(−h)にh(B_h−iA_h)/2。z³倍後の配列を逆順にしてsolverへ渡す操作は整合する。最高調波を拒否gateで確保した上で6根を要求しており、次数落ちを黙って受け入れていない。

50/80dpsを別々に構築する、片方失敗でも他方の予定評価は行う、追加精度や外側retryをしない、返却済rootをgate前に保存する、という流れを確認した。全複素根相対距離、monic係数再構成、unit/outside/undecided、円周角距離、停留残差、順位gap、正の曲率、6!一対一対応、best対応の検査はCONTRACTに対応している。

ただし有限精度でH=0になったstatusは実数理想目的の恒等zeroの証明ではない。根残差が小さくても悪条件性や共通係数誤りは残る。これらを含めnoncertifiedと明記しているため、運用gateとしての範囲を越えていない。

## 4. φ_evalとfloor

80dpsの有限root位相をFraction化し、整数商と余りからties-to-evenの40桁丸めをする構成は正しい。1→0のmod処理、zero拒否、64φ_evalが整数となる境界拒否、近傍境界診断、50/80/有理代表元のmembership比較、丸め後停留残差と順位の再確認もある。

floor判定を64種類だけで行うことはn=64j+kでlabelがjだけ増える今回のgridと整合する。境界距離の0と1を含む列挙は円周端に対応する。丸め誤差上界はp80からの変換に限定され、真の最小位相の誤差上界ではない。

## 5. W/V/A/S/Jの60/90dps密度

- W/Vの対角logdetと二次形式、AのP0初期項および残りinnovation式は正しい。
- S/JではD^(-1/2)でwhiteningし、w=f/√v、z=e/√v、T=wᵀw、α=wᵀz/Tとした上で

      Q=||z−αw||²+α²T/(1+τ²T)

  を使っている。直交分解からD+τ²ffᵀの逆二次形式に一致し、大きい二項の直接差し引きを避ける。logdet=Σlogv+log1p(τ²T)も正しい。T=0またはτ²=0の分岐、実際の部分blockのnorm使用は適切。
- densityは保存Yとqを二進有理値から読み、保存binary64 residual配列を正本にはしない。この差はCONTRACTに記述されている。
- scoreの60/90比較、保存scoreから90dpsで作るΔ60、主90dps値の並びはSCHEMAと一致する。精度gateは丸めgeometry自体の誤差を検証しない。

生成の丸めsqrtや乗加算、離散PRNG出力から実際に得られる分布は、このGaussian scoreの厳密な連続lawではない。CONTRACTは理想−KLをそのまま有限実装へ適用しないと明記しており適切。完走・精度gate通過率は未測定。

## 6. SCHEMAの範囲

score配列9要素の順序、oracle片側4要素、geometry64値の復元、q→g alias、membership64～65群は数学的対象と対応する。phaseは[0,1)で扱うためlabelの非負制約も整合する。

一方SCHEMAだけでは「completeなら必要全配列・両密度・phaseが存在する」、shapeとbytesの一致、membershipが全Nを隙間なく覆うこと、数値文字列の有限性まで検証しない。これらはsource/後段監査の意味的条件であり、JSON schemaを通しただけで科学契約PASSとは呼べない。schema強化を新しい数値計測項目追加と混同しない。

## 7. 親からの追加問：64位相の三角関数再利用

実数式ではn=64j+kとしてcos(2πhn/64)=cos(2πhk/64)、sinも同様。各precision内でh=1,2,3とk=0,…,63の表を構築し、n昇順の同じ積和で表[n mod64]を使う方法は同じ理想OLSを狙う。

ただし現sourceは丸められたπを含む大きいn角を毎回評価するため、有限mp値まで同じとは限らない。root、gate、φ_eval、scoreのbyte同一性を主張できない。50dps表を80dpsへ流用せず、各precisionで独立に作る必要がある。Yを先に位相別集約してから64項へ縮める方法は、さらに積和の丸め経路を変えるため、この最小表再利用とは別案である。

**変更候補を採るなら計測前だけ**、CONTRACTの係数評価式・表構築順・precision・fsumのn順を明示改訂し、source/hashを凍結し直す。数学的には妥当な候補だが、本レビューは採用・実装を行わない。超越関数の重複評価を減らす構造的理由はあるが、実行時間、900秒完走、成功率の改善は未測定であり保証しない。

## 停止線

rnの入力非有限検査を修正後に限定差分を再確認すること。その他の数学的経路は上記条件付きで整合しているが、noncertified性の受容、運用・来歴監査、別の開始判断を代替しない。今回の作業は読取りと本レビュー保存で終了する。
