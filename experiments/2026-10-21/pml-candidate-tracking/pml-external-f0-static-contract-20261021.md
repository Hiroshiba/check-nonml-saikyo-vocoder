# PML 外部 raw F0 注入の静的契約

対象: `Hiroshiba/check-nonml-saikyo-vocoder`、commit `2251f947032296c6cdf03e8022c74eefbeef17e8`。現 PML を唯一の base とし、変更しない。6 ソースファイルを読み取った静的判断であり、実装・import・実行・help・tests・smoke・Cloud 起動・Git/Library 変更は行っていない。

## 結論と最小境界

候補ライブラリ側 adapter から既存 `pml_analysis.analyze(x, 16000, raw_f0s, seed=同一値)` を呼ぶ境界がすでにある。REAPER 部を含む `codec.encode` 全体の copy は不要。ただし、encode の入力検証、SPEC の正値/形状検証、保存グリッド検証、FWCEP 化と `PMLParameters` 組立てには独立 helper がなく、adapter が同じ契約を薄く維持する必要がある。[C][A]

経路は、外部 raw F0 → 既存 postprocess → StoneMask/CheapTrick の SPEC と既存 PDD/NM の再解析 → 既存 `fwcep.encode_log(log(SPEC),16000,59)` → 既存 `PMLParameters` → 既存 save/load → 既存 `codec.decode`。保存済み F0 だけの置換はこの実験ではない。H0 重みを VUV/NM 確率に代入する経路は使わない。[C][A][S]

StoneMask F0 は CheapTrick にだけ使い、SPEC はその power の平方根。PDD・保存 F0・合成には postprocess 後 F0 を使う。NM は PDD の 0.75 threshold、形態学処理、1.5 F0 未満の保護から再計算し、独立の VUV 保存 field はない。[A:81–128][P]

## 1. 時刻・端点・下限

- **保存前の必須検証**: 解析後の時刻列を `float64 arange(N) * float64(0.005)` と uint64 view で bitwise 比較する。近似的な 5 ms、一定間隔、開始時刻が非 0 の系列では不十分。保存ファイルは時刻列を持たず、decode はこの式で再生成するため、adapter が検証を省くと時刻を黙って変える。[C:73–85][P:62–64][S]
- raw は有限・厳密単調増加の `[time,F0]` を最低 3 行。1 次元 F0 入力も受けるが、実験契約は明示的な float64 の 2 列とするのが曖昧でない。postprocess は浮動小数点入力の dtype を保持し、代入丸めと時間 jitter 判定もそれに依存する。[A:14–56]
- 無声 `F0<=0` は正の観測間で線形補間され、両端は最寄りの正の観測で延長される。その後 65..700 Hz に clip、8 次 Butterworth の往復 filter。平均 raw 間隔が 5 ms なら cutoff は 50 Hz。filter 用細密 grid は 0 始まり・raw 最終時刻を含まないので、最終 F0 の戻し補間にも端点延長がある。[A:34–50]
- jitter が `2 * finfo(dtype).resolution` を超えると、`arange(raw先頭, raw末尾,0.005)` に再標本化する。末尾非包含で、フレーム数も変わりうる。均一 grid でも「保存 grid に bitwise 合うか」は別検証。raw の時間範囲と波形長の対応は既存コードで検証しないため、N、先頭/末尾、波形末尾のカバレッジを実験側で先に固定する。[A:51–77][C]
- **3 行は成功保証ではない**。F0 filter の細密 grid と PDD の pitch-synchronous grid の双方に `filtfilt` 長さ条件がある。標準 pad 実装では各 filter 入力長が 27 超を要する。例えば 0 始まり 5 ms raw の 3 行は F0 filter だけでも短すぎる。正規格子ならこの段階だけの必要条件は概ね raw 15 行以上だが、PDD 側の長さは F0 と時間幅次第であり、単一の raw 最低行数には置換できない。codec の音声下限 0.2 秒も adapter で保持し、十分な全区間 dense 系列を設計する。[A:43–49][D:154–164][F]
- 全零**波形**は codec が拒否。一方、非零波形に対する全零/全非正 **raw F0** は警告のうえ 65 Hz の連続クロックへ fallback する。H0 は PML の入力型ではないので、「全 H0」を非正 raw F0 へどう変換するかは adapter の未設計事項。その変換を選んだ場合でも、全無声 NM や無音になる保証はなく、SPEC/PDD/NM は波形から再解析される。[C:21–64][A:24–40,105–115]
- filter 後に再 clip はしない。診断には範囲外の数だけを残す。`PMLParameters` の受理範囲は **50 Hz 超・700 Hz 未満**で、解析側 clip の上限 700 と一致しない。上限ぴったりや overshoot は保存拒否になりうる。黙った追加 repair は別条件になる。[A:72–77][P:45–54]

## 2. 同じ保存・seed・decoder を維持する条件

入力は元 codec と同じ 16 kHz、mono、実数、有限、[-1,1]、3200 sample 以上、非零で、正規化/clip/再標本化なし。analyze 単体はこの全条件を保証しない。seed は整数 `0<=seed<2**32` を明示する。**analyze の既定 123 と codec の既定 20261015 は異なる**。本計画の seed は別途明示指定予定。[C:21–33][A:99–104][P:7–11]

保存精度は連続 F0 float64、FWCEP 60 係数 float32、NM 2049 bin の bool。body は little-endian F0/FWCEP と little-bitorder の packed NM、header は schema、16 kHz、4096 FFT、5 ms、frames、n_samples、seed、pitch_shift_semitones、body SHA-256。既存 saver は新規作成のみ。raw F0、H0、PDD、StoneMask F0、選択器状態は保存 field に追加せず、別 trace に置く。[P:22–60][S:12–39]

decoder は保存 seed をそのまま使い、既存の低域 NM 拡張、周波数方向 mask 平滑化、pulse 時刻、0.5 F0 high-pass、周期エネルギー補正、出力長、非正規化を保持する。保存 NM と合成時の effective NM は同じものではない。同じ seed は再現条件だが、F0 が変わると PDD の fallback draw 数や合成 noise segment 長も変わるため、各時刻で同一雑音が割り当たる意味ではない。[C:95–125][Y:28–32,78–143,198–254][D:98–131,179–190]

## 3. 必要 trace と既存の取得範囲

- **既存から取得可能**: raw F0（base は encode trace）、post F0、StoneMask の `refined_ct_f0`、SPEC、PDD、NM、F0 の raw dtype/無声数/fallback/clip 数/jitter/resample/出力行数/filter 後範囲外数、PDD の seed/pitchsync 行数/空窓・padding・fallback 観測診断。[C:50–90][A:24–78,105–128][D:83–133,179–190]
- **decoder trace にある**: lowband cut/replacement、pulse times/F0、effective masks、Gaussian 診断、0.25 秒以後の最初の pulse（該当時刻がある場合）。[Y:84–143,233–278]
- **既存 API から配列としては得られない**: 無声補間直後・clip 直前/直後・filter 直後かつ再標本化前の F0、および clip 位置 mask。`clipped_frames` は無声補間後の範囲外数で、raw の範囲外数ではない。PDD 内部の sinusoidal/pitchsync 中間配列も analyze の返り値にはない。これらを必須 trace にするなら、PML を変えずにどう外部診断するかを別途設計する。`f0_postprocess` 出力を analyze に再投入すると二重処理になり、同一経路ではない。[A][D]
- adapter が別に残す最小 provenance: 波形と base commit/依存版、raw 系列の時刻・dtype・由来・hash、H0 の変換規則、選択結果と post F0 の対応、seed、保存 grid 検証、保存パラメーター/hash、失敗した stage。候補 trace の REAPER 観測を捏造しない。

## 4. 局所選択・系列選択・追加平滑化の解釈

postprocess は多対一になりうる。全非正値は同じ 65 Hz fallback、65 Hz 未満の正値は同じ clip 値、無声区間の異なる H0 配置も同じ補間曲線になりうる。8 次往復 filter は急変の差を抑えるが、任意の異なる raw 系列を必ず bitwise 同じにするという主張ではない。[A:34–77]

比較の主軸は raw の選択差だけでなく、**同じ保存 grid 上の post F0 差**（bitwise 一致、最大差、RMS/log-F0 差、clip/fallback 数）に置く。同じ波形・post F0・seed・全設定なら下流への F0 入力差はなくなる。逆に差が残っても SPEC/PDD/NM の同一性を仮定しない。

「局所選択＋追加平滑化」対照も同じ既存 postprocess を通す。系列選択が良くても、その改善を連続性制約固有の効果と直ちに断定できず、単純平滑化・clip/H0 補間との差を分ける必要がある。追加平滑化の強さ・適用領域・端点・H0 扱い・調整用データは事前固定事項。追加平滑化後の post F0 まで一致した条件は、下流音声だけでは選択器を識別できない。

## 5. 実装前に残る決定

1. dense 観測の hop、窓、端点支持、raw grid/フレーム数と base との合わせ方。既存研究の疎な 12 非重複窓は全区間軌跡として直接再利用しない。新 dense 解析は未承認の設計段階。
2. H0 を出力しない時計区間へどう渡すか、局所/系列選択の state・遷移・同点規則。H0 weight を NM に流用しない。
3. 研究候補の 50.78125..500 Hz と PML の 65..700 Hz は同じ範囲ではない。低域候補の clip が結果を潰す割合を区別し、範囲変更を暗黙に導入しない。
4. 上限/overshoot、短い系列、非正値、非有限値、解析失敗時の扱い。追加 repair をせず失敗を記録するか、別対照として明示するか。
5. 既存 API にない中間 trace を本当に必要とするか、同一依存環境での保存/復号再現性をどう後日確認するか。本監査は成功率・音質・bitwise 実行再現性を検証していない。

## 一次根拠

各リンクは対象 commit のコード。blob SHA は取得内容の固定根拠。

- [C: codec.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/codec.py) — `4fe77b9986718774476ab91a26f5ab6ea4785481`
- [A: pml_analysis.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_analysis.py) — `61f71548f8afc88fe0f44c8ebbcff19b311a5489`
- [P: parameters.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/parameters.py) — `3a525f78d9e21b5ac7c9270ba40428f3823a657f`
- [S: storage.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/storage.py) — `3a9b80c16540d243cec4dad4cb21ef88263993e1`
- [D: pml_pdd.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_pdd.py) — `841cb92999a072092fb78af24a23f79243f82053`
- [Y: pml_synthesis.py](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/2251f947032296c6cdf03e8022c74eefbeef17e8/vocoderbench/pml/pml_synthesis.py) — `966ffa84578ad365a7062c04d70582976d64ac4a`
- [F: SciPy 1.17.0 標準 pad 実装](https://github.com/scipy/scipy/blob/v1.17.0/scipy/signal/_signaltools.py#L4490-L4541)、[filtfilt 公式説明](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html)。利用予定環境は NumPy 2.3.5 / SciPy 1.17.0（uv.lock と Cloud metadata 照合済み情報）。本監査では v1.17.0 公式ソースの `ntaps=max(len(a),len(b))`、既定 `edge=3*ntaps`、`入力長<=edge` の拒否を読み取り確認した。対象の 9 係数 filter の長さ 27 超はこの固定版に基づく静的条件であり、実行検証はしていない。
