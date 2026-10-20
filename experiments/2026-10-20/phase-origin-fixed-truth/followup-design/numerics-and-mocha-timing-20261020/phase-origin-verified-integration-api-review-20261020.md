# 円周 predictive 積分：検証付き積分APIの限定監査

2026-10-20。対象の数値設計と独立レビュー（同日版）を読み、公式ドキュメントと公式GitHubの公開本文だけを静的確認した。結論は **公開API上の実装経路は存在するが、認証実装・固定資源内の精度達成は未確認**。方式採用や実500の再実行を指示するものではない。

## 1. 版と入口

- 調査時の最新安定版は **python-flint 0.9.0（2026-07-03）** と **FLINT 3.6.0（2026-06-29）**。公式releaseのLatest表示と公式互換表／配布一覧を照合した。python-flint 0.10.0は未公開扱い。0.9.0の対応FLINT範囲は3.0–3.6であり、Python側の版だけから実際にリンクされたFLINT版は決まらない。[S1–S3]
- 公開入口は `acb.integral(func, a, b, …)`。relative／absolute tolerance、degree／evaluation／depth limit、heap、verboseの引数がある。複素ballを返す。対応C APIは `acb_calc_integrate`。以下はPython実装を0.9.0、C仕様・実装をv3.6.0へ固定して照合した。[S4–S6]

## 2. 精度・資源・失敗の契約

- **toleranceと出力誤差は別**：Pythonのrel_tol／abs_tolの既定はともに2^(−p)。Cのrel_goalは相対誤差目標をbit数で表す。各部分区間でabsolute目標とrelative目標から許容幅を選ぶため、分割の累積・相殺・関数評価誤差により最終誤差が両目標より大きくなることが明記される。Cは作業精度を自動増加しない。微小なscaled積分では通常のabsolute既定値だけで相対精度を期待できず、C仕様はabs_tol=0も許す。[S4–S5]
- **実出力の判定手段**：`acb.is_finite()`、`acb.rad()`、実部・虚部へのアクセスが公開される。radは複素ballの誤差の大きさの上界をarbで返す。`arb.lower()`／`upper()`は外向き端点を返す。印字された桁数やradiusを隠した文字列ではなく、保持したballから有限性・正下端・最終log score区間の幅を判定する設計は可能。[S4、S8]
- **上限の意味**：v3.6.0の非正／未設定limitの既定はdeg_limitが0.5 min(prec, rel_goal)+60、eval_limitが1000 prec+prec²、depth_limitが2 prec。eval_limitは多少超過し得る目安であり、厳密な時間・評価数上限ではない。depthは局所二分木の深さでなく同時にqueueされた区間数。degree不足では直ちに全体終了せず、適応分割を試す。[S5–S6]
- **失敗は必ず例外／nanになるわけではない**：Cはeval／depth上限でNO_CONVERGENCEとし、既に得た区間包囲を足して返すため、有限だが粗いballも返り得る。callbackのanalytic照会で非有限を返すこと自体は局所quadratureを断念する正常な合図であり、全体失敗と同一ではない。非有限の局所包囲が最後まで残れば最終結果も非有限になり得る。[S6、S10]
- **Python固有の欠落**：0.9.0のwrapperはCの成功／非収束statusを取得・公開せず、resだけを返す。callbackのTypeError／ValueErrorは捕捉して後で再送出するが、資源上限到達を自動例外としては扱わない。したがって「例外なし＝tol達成」や「有限＝収束成功」は不可。厳密な停止理由・実評価数を構造化記録する公開戻り値も確認できない。verbose文字列を安定したstatus APIとみなさない。[S7]

## 3. callback、端点、精度と共有状態

- callbackは二引数 `(x, analytic)` を受け、**acbを返す**。analytic=Falseでもxは一点とは限らず、区間全体の値を包囲する必要がある。Trueでは経路周辺の複素領域上で正則性を確かめ、成り立たなければ非有限ballを返す。実軸の点値やbinary64計算への置換は契約違反になり得る。sin／cos／expと確定係数から成る本設計の被積分関数はentireなので、分岐関数を追加しない限り正則性の紙上要件は満たせる、というのが本レビューの推論。[S4–S5、S7]
- Cは有限端点と経路上で有界な関数を要求し、端点演算も作業精度precで行う。wrapperはa,bをacbへ変換してそのまま渡すため、πの包囲を持つ端点を渡す入口はある。ただし古い低精度のπ・係数・端点ballを再利用しても、ctx.precを上げただけで入力幅は消えない。精度再試行時は元の厳密表現／理想入力包囲から再生成する必要がある。Python floatの値と意図した十進数は異なる、という公式注意も重要。[S5、S7、S9]
- **共有global precision**：公式資料はflint.ctxをglobal contextと呼ぶ。0.9.0実装ではthectxが一個で、workprecは同じ値を変更・復元するだけ。callbackはCからprecを受けるがPython関数へ渡さず、通常のacb演算はglobal getprecを読む。従って異なる精度の並行処理をcontext managerだけで隔離できるとは扱わない。再試行・定数作成・callback・最終差までの精度固定と、並列時の隔離／同期は未設計事項。[S7、S9、S11]
- C側にはGL節点cacheと内部並列化経路もある。Python callbackのマルチスレッド安全性まで今回の静的調査で認証したわけではない。ctx.threadsの変更を安全性確認なしに追加しない。[S10–S11]

## 4. 数値設計への判定と未確定点

将来の「候補B」にはAPI上の障害は見つからなかった。ただし採用前に、入力包囲、scale b、精度再試行、正下端、κ・係数・二つのlog Jと差を含む最終絶対誤差予算、資源終了時の未達扱いを別契約で固定する必要がある。要求tolをそのまま最終scoreの保証とする実装は不可。

特に **Pythonだけで全停止理由を識別する要件は現公開戻り値では満たせない**。最終包囲幅だけで合否を判定し停止理由を「不明」と記録するのか、statusを扱える別のC連携を将来検討するのかは未決定。追加APIや未公開statsを推測していない。固定資源での達成、実際の性能、特定buildの正常性は一切検証していない。

今回行ったのは既存二文書と公開一次資料の読取り、本メモ保存だけ。インストール、import、サンプル実行、tests、積分計算、実験、パッケージ取得、Cloud操作、リポジトリ変更、既存500の再計算は行っていない。取得不能だったarblib.orgのURLは再試行していない。flintlib.orgの現行HTML本文はツールエラーだったため、その本文を確認済みとはせず、別に読めた公式v3.6.0のrst原文を採用した。

## 一次資料（確認版・節）

- S1: [python-flint 0.9.0 release](https://github.com/flintlib/python-flint/releases/tag/0.9.0)（Latest）。
- S2: [FLINT公式配布一覧](https://flintlib.org/downloads.html)（FLINT 3.x series、3.6.0）および[3.6.0 release](https://github.com/flintlib/flint/releases/tag/v3.6.0)（Latest）。
- S3: [python-flint公式README](https://github.com/flintlib/python-flint#compatibility-table)（Compatibility table／0.10.0 Not released／0.9.0）。
- S4: [python-flint 0.9.0公式API](https://python-flint.readthedocs.io/en/latest/acb.html#flint.acb.integral)（acb.integral、is_finite、rad、real、imag。latestという可変URLだが閲覧時は0.9.0表示）。
- S5: [FLINT v3.6.0 acb_calc.rst](https://github.com/flintlib/flint/blob/v3.6.0/doc/source/acb_calc.rst)（Integration／Options for integration／Local integration algorithms）。[本文確認用raw](https://raw.githubusercontent.com/flintlib/flint/v3.6.0/doc/source/acb_calc.rst)。
- S6: [FLINT v3.6.0 integrate.c](https://raw.githubusercontent.com/flintlib/flint/v3.6.0/src/acb_calc/integrate.c)（acb_calc_integrate、quad_simple、eval_limit／depth_limit判定、末尾res/status返却）。
- S7: [python-flint 0.9.0 acb.pyx](https://raw.githubusercontent.com/flintlib/python-flint/0.9.0/src/flint/types/acb.pyx)（acb_calc_func_callback、acb.integral、any_as_acb）。
- S8: [python-flint 0.9.0 arb公式API](https://python-flint.readthedocs.io/en/latest/arb.html#flint.arb.lower)（arb、lower、upper。閲覧時0.9.0）。
- S9: [python-flint 0.9.0 General concepts](https://python-flint.readthedocs.io/en/latest/general.html#global-context)（Global context／Inexact numbers and numerical evaluation）。
- S10: [FLINT v3.6.0 integrate_gl_auto_deg.c](https://raw.githubusercontent.com/flintlib/flint/v3.6.0/src/acb_calc/integrate_gl_auto_deg.c)（acb_calc_integrate_gl_auto_deg、gl_worker、gl_cache）。
- S11: [python-flint 0.9.0 flint_context.pyx](https://raw.githubusercontent.com/flintlib/python-flint/0.9.0/src/flint/flint_base/flint_context.pyx)（FlintContext、PrecisionManager、thectx）と[flint_context.pxd](https://raw.githubusercontent.com/flintlib/python-flint/0.9.0/src/flint/flint_base/flint_context.pxd)（getprec）。
