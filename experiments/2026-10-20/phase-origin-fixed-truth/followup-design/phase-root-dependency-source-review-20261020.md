# mpmath 1.3.0 root依存関数の一次source確認

2026-10-20。公式GitHubの1.3.0 tag sourceをweb読取した。import、root試行、tests、数値計算は一切行っていない。実環境にある依存bytesとの一致認定ではなく、今後のsourceレビューのチェックポイントである。

## polyroots：支持される指定と限界
`maxsteps=1000, extraprec=20, cleanup=False, error=True, roots_init=None` はすべて当該signatureが受け付ける。

- Durand–Kerner。初期根はPython複素数 `(0.4+0.9j)**n` をmpc化する決定的初期化で、多精度十進0.4/0.9からの構築ではない。
- 最大1000 sweep。更新量最大値が元精度のeps未満なら停止。最後のsweep後も判定する。根同士の差のzero divisionは内部でskipするため、正常return自体を根捕捉証明と扱わない。
- cleanup=Falseは微小成分の切捨てを無効化するが、sortと元精度への出力丸めは残る。
- error=Trueの返却errは最終更新量最大値と元精度由来の下限の大きい方。厳密誤差上界でも全根・global最小の認証でもない。
- 未収束はNoConvergenceをraiseし、根リスト・err・反復履歴をAPI返却しない。正常returnでも実sweep数は返さない。定数多項式はerror=Trueでも空listとなる特殊経路があるため、callerでdegreeを先に検証する。

出典：[公式 polynomials.py、signatureと実装](https://github.com/mpmath/mpmath/blob/1.3.0/mpmath/calculus/polynomials.py#L42-L199)。

## 内部精度
extraprecはdecimal桁ではなく **bit追加**。20指定なら各caller精度に20bitだけ加算し、block終了で元精度へ戻る。50/80dpsから独立に係数を作る契約を、extraprecが代替することはない。[公式 ctx_mp.py](https://github.com/mpmath/mpmath/blob/1.3.0/mpmath/ctx_mp.py#L376-L397)

## mpfからfloatへの変換
`float(mpf)`はcontextのrounding指定を低水準to_floatへ渡す。したがって呼出時の丸めmodeも凍結対象。[公式 ctx_mp_python.py](https://github.com/mpmath/mpmath/blob/1.3.0/mpmath/ctx_mp_python.py#L128-L136)

to_floatは保持mpfの仮数を必要なら53bitへ丸め、math.ldexpでfloat化する。overflow/underflow/非有限の扱いを伴い、単にfloat化できたことを有限正値の保証としない。[公式 libmpf.py](https://github.com/mpmath/mpmath/blob/1.3.0/mpmath/libmp/libmpf.py#L423-L457)

**監査上の推論**：保持mpfをbinary64へ丸める操作と、未丸めの解析的q・sin・sqrt等の真値をcorrectly rounded binary64へ写す保証は別である。80dps近似値が真値のbinary64丸め境界を越えていない証明にはならない。subnormal域や非有限も別検査し、全域correct roundingをこのsourceだけから認定しない。

## source実装レビューで確認する事項
1. 実mpmath version/distribution所属・package bytesを固定し、上のtag仕様と一致させる。Python/backendも固定する。
2. 50/80の各呼出し開始を先にdurable記録し、係数・precision bit数・全kwargs・return/exceptionを保存。精度追加、maxsteps増加、初期根変更、再呼出しを救済として行わない。
3. NoConvergence時の途中根・実反復数は「API非返却」と記録する。hard kill時は「返却未観測」。推測値で埋めず、片方の精度の既保存値を失わない。例外tracebackのframeから内部状態を拾う非標準経路を黙って追加しない。
4. root返却数・有限性・残差・対応・分類・順位等は別の固定gateとして実装する。errが小さいだけで成功にしない。maxstepsはwallclock制限でないため外側hard-stopを維持する。
5. 解析値のcorrect roundingではなく「固定80dps評価器の保持値から、固定丸め規則でbinary64化」という限定を明記する。さらに強い保証が必要なら別の事前証明契約が必要。

指定引数のAPI適合は確認できたが、候補設定の収束率・精度・所要時間・global解保証は未検証。実行許可を意味しない。
