# REAPERの未加工観測を任意で保存する

PMLの解析を行う利用者向けの診断仕様です。通常の解析では診断ファイルを作りません。既存の解析を呼び出す際に明示指定すると、その一回のREAPER呼出しが返した5配列を保存できます。過去の保存データから、捨てた配列を復元する機能ではありません。

## APIでは成功時に `trace['reaper']` を追加する

```python
trace = {}
params = encode(x, 16000, seed=20261015, trace=trace)
reaper_arrays = trace['reaper']
```

`encode(..., trace=None)` の署名・返り値は変わりません。辞書を指定したときだけ、REAPERの戻り配列をそれぞれ `.copy()` し、元のdtype・形状・値で保持します。型変換、負F0の置換、補間はこのコピーに加えません。成功時に既存の `features`・`diagnostics`・`raw_f0` とともに追加します。

以下の型と意味は、固定依存pyreaper 0.0.11についての[既存の一次ソース調査](../experiments/2026-10-20/phase-origin-fixed-truth/followup-design/frozen-contract-and-reaper-20261020/reaper/reaper-epoch-observation-provenance-20261020.md)と[独立確認](../experiments/2026-10-20/phase-origin-fixed-truth/followup-design/frozen-contract-and-reaper-20261020/reaper/reaper-epoch-observation-independent-review-20261020.md)に基づきます。APIのコピー自体はdtypeを強制しません。

| キー | 型・形状 | 単位・意味 | 時間格子 |
| --- | --- | --- | --- |
| `pm_times` | float32 `(N,)` | 発話始点からの秒、pitch mark時刻 | イベント格子（event grid） |
| `pm` | int32 `(N,)` | 無次元の0/1旗。0=無声、1=有声 | `pm_times` と対 |
| `f0_times` | float32 `(M,)` | 発話始点からの秒 | 5 msフレーム格子（frame grid） |
| `f0` | float32 `(M,)` | Hz。wrapperの負値sentinel（−1）も保持 | `f0_times` と対 |
| `corr` | float32 `(M,)` | 無次元の正規化相互相関（NCCF）値 | `f0_times` と対 |

NとMは別の長さで、同じ長さでも同じ格子を意味しません。`corr[j]` を `pm_times[j]` の信頼度として対応させないでください。`f0_times` は0起点でframe_period×iをfloat32で評価した時刻です。保存パラメーターのfloat64時間格子とは区別します。

既存の `trace['raw_f0']` は時刻/F0の2列float64配列で、負F0を0に置換した解析入力です。新しい `trace['reaper']['f0']` はその置換前の戻り値です。`PMLParameters.f0` はさらに後処理した正の合成クロックであり、これら3種類を混同しません。

## CLIは5配列だけを別NPZへ保存する

```sh
uv run --locked python -m vocoderbench.pml_cli encode input.wav features.pml \
  --reaper-trace-npz observations.npz --timing-json analysis.json
```

`--reaper-trace-npz PATH` はencode専用です。NPZのキーは上表の5個だけで、数値配列を非圧縮で保存します。SPEC・PDD・波形・メタデータは含めず、pickleも使いません。読み出す場合は `numpy.load(path, allow_pickle=False)` を使えます。これは診断専用ファイルであり、通常のPML保存・復号形式や既存研究のNPZ保存形式を変更しません。

入力WAV、特徴量出力、任意のtiming JSON、任意の診断NPZには、それぞれ異なるパスが必要です。相対パスやシンボリックリンクを解決して衝突を調べ、既存の出力先（リンクを含む）は拒否します。各書込みも排他的に新規作成します。ファイルハンドルをNumPyへ渡すため、PATHに `.npz` を黙って追加しません。

特徴量の保存後に診断を保存し、最後にtiming JSONを保存します。保存失敗は既存の `run_cli` へ伝わり、スタックトレース付きログと非ゼロ終了になり、完了とは報告しません。完成した他の出力は削除しません。失敗箇所の不完全なファイルも残り得るため、再実行には別の出力先を指定してください。

## markや相関を校正済み確率・完全GCI真値と解釈しない

既存調査のGetFilledEpochsの読取りでは、無声部分には区間の基準時刻から10 ms間隔で人工的なmarkが補充されます。発話全体で共通の0起点格子でも、境界を隙間なく補充する規則でもありません。有声markも選択経路の残差ピークに基づく音響的な推定時刻であり、完全な声門閉鎖時刻（GCI）の真値ではありません。`pm=1` は現在または直前のperiodが有声という規則による旗で、独立したフレームの有声確率ではありません。

同じ調査のBacktrack・規則格子化の読取りでは、`corr` は選択periodのlag等のNCCF値です。F0を決めるlagと常に同一ではありません。ゼロ初期化後、経路点を丸めたフレームへ割り当て、内部の隙間を直前値で埋め、終端へ値を延長します。同じフレームは後の経路点で上書きされ得て、先頭0番が未割当なら初期ゼロが残ります。全域一様な前値補間とは呼べず、wrapperは無声という理由だけで相関をゼロにしません。`corr` は各epochの元の相関値でも、校正済みの有声確率やGCIの信頼度でもありません。

これらは上記の固定一次ソース調査の引用・要約で、今回の新しい音声観測ではありません。内部の疑似確率 `prob_voiced_` やepochごとの内部診断は5戻り値に含まれず、今回も追加取得しません。[過去の保存物の棚卸し](../experiments/2026-10-20/phase-origin-fixed-truth/followup-design/frozen-contract-and-reaper-20261020/reaper/pml-epoch-saved-artifact-inventory-20261020.md)を含む旧文書の「未保存」は、各調査時点の記録として保持します。

## 診断コピー負荷を通常の速度順位へ混ぜない

CLIの解析時間は従来どおり `pml.encode` の前後だけを計り、WAV読込・特徴量保存・診断NPZ保存・JSON保存を含みません。診断指定時は5配列のコピー負荷を解析時間に含むため、timing JSONに `reaper_trace_capture_included: true` と説明を追加します。この時間を診断なしの速度順位へ混ぜません。

CLIは必要な5配列を取り出した直後に大きな `features` 等へのtrace参照を解放します。フラグ未指定時は `trace=None` で、診断辞書・コピー・保存を作りません。APIも診断の有無によらずREAPERは一回だけ呼び、元の `times/f0 → float64 raw_f0（負値を0）→ analyze` を使います。解析・合成の式、F0後処理、seed、乱数呼出し、雑音マスク、FWCEP、保存パラメーターは変更しません。

今回の確認は静的AST・キャッシュ付きRuff・ソース行数・差分とデータフローの読取りに限定しました。テスト、PMLのimportやCLIの動作確認、音声処理、再解析、F0・位相計算、品質・MOS測定は実施せず、実行結果の一致を測定したとは主張しません。
