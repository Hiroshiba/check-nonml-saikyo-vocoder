# 数値根拠対応表

初版の「保留」「結果待ち」は当時の記録。追加の確定値は末尾の段階B追補を参照。

帯域が2値で並ぶ箇所は1.5–3 kHz、3–8 kHzの順。出典ファイルはこの資料内の公開用投影で、全精度の保存値を残す。私用の実行パスや内部識別子は含めない。

|根拠ID|本文の主張|値・状態|出典ファイル|対応キー|解釈上の制約|
|---|---|---|---|---|---|
|E01|対象と同一性|64,720標本 / float64 / 全byte一致|observation-data.json|identity_wave|今回の再観測対SAVED。公開PCM16ファイルSHAとは別|
|E02|観測窓和集合の同一性|208標本 / 全byte一致|observation-data.json|identity_union|直接144標本と区別|
|E03|訂正版の成功|全9必須確認passed / 7capture / 元一覧24ファイル一致|observation-data.json|gates; manifest_rows_verified|初回失敗は上書きしない|
|E04|初回の失敗理由|native float32と観測側float64仮定の不一致|attempt-history.json|attempt001.captures; attempt001.unreached|初回では208標本再構成と分解は未実行|
|E05|固定範囲|9中心 2.0945–2.1025秒 / 2帯域|observation-data.json|centers_s; bands_hz|窓中心をonsetと呼ばない|
|E06|row419自己項平均|1.0589159274968033e−6 / 6.762879395019362e−7|observation-data.json|mean_self_terms[0][4]; mean_self_terms[1][4]|帯域順1.5–3 / 3–8 kHz。線形算術平均|
|E07|row420自己項平均|2.8151602522975955e−5 / 1.5753816070866997e−5|observation-data.json|mean_self_terms[0][5]; mean_self_terms[1][5]|品質点数や原因割合ではない|
|E08|419×420交差項平均|−2.8941625467535e−7 / −9.014706710852715e−8|observation-data.json|mean_cross_row419_row420|各時刻すべて負という意味ではない|
|E09|全21交差項平均の和|−2.875019293906706e−7 / −9.001969044371242e−8|observation-data.json|mean_all_signed_cross|符号を保持。自己項の和とともに直接合成powerへ|
|E10|直接合成power平均|2.8923112698043105e−5 / 1.6340092647267214e−5|observation-data.json|saved_mean_direct_power|dB平均ではない|
|E11|最大自己項の行|最初2中心419 / 残り7中心420（両帯域）|observation-data.json|largest_self_row_each_center_band|自己項の大小順位であり良さの順位ではない|
|E12|他5kernel自己項平均和|9.617696101479204e−11 / 8.32734199436661e−12|observation-data.json|mean_other_five_self_terms|低域や波形全体への無関係を意味しない|
|E13|全項の保存|自己126値＋交差378値＝504行|full-terms.csv|全504データ行|0・負値・全21組を保持|
|E14|全合計の保存|2帯域×9中心＝18行|full-totals.csv|全18データ行|直接・再構成・既存観測powerを区別|
|E15|複素STFT最大残差|1.5085363209261804e−16 / 許容比0.03927307603828837|observation-data.json|residuals.Z_residual|保存された事前固定許容値の検査。FFT再実行なし|
|E16|power最大残差|2.0328790734103208e−20 / 許容比0.00037889994616513396|observation-data.json|residuals.power_residual|尺度0は残差厳密0|
|E17|既存powerとの最大残差|2.371692252312041e−20 / 許容比0.0004112769101634411|observation-data.json|residuals.saved_power_residual|保存値転記|
|E18|Hermitian厳密一致の補助診断|false / 最大差1.1863790904493606e−21|observation-data.json|residuals.hermitian_residual|必須ゲートではない。対称化していない|
|E19|row420実支持|[2.096125, 2.1389375)秒|observation-data.json|saved_actual_nonzero_support[5] / 16000|band窓中心の2.0945秒とは別|
|E20|row422実支持と対象重なり|[2.1046875, 2.1474375)秒 / 直接0標本、最後の窓5標本|observation-data.json; saved-terms.json|saved_actual_nonzero_support[6]; self_terms[8][:][6]|最後の自己項3.776977269898238e−19 / 6.114331673383064e−16|
|E21|広帯域RMS|row417 0.00832717089217942 / row419 0.014608556249456827 / row420 0.007996615184969687|observation-data.json|saved_direct_interval_rms[3:6]|直接144標本。帯域powerと範囲も量も異なる|
|E22|row419限定2倍操作（別診断）|早期−12.461385/−12.367156 dB、残留−0.080471/−0.157427 dB|earlier-row419-data.json|rows[].conditions.FRESH_DOUBLE.db_vs_FRESH_1_primary|分母FRESH_1。今回のSAVEDとの完全一致主張へ流用しない|
|E23|row419理想支持|F0 97.32718106858442 Hz / 2倍右端2.1027059665秒 / 下限187.5 Hz|geometry-data.json|rows[0]|理想幾何。実装丸め支持未確定|
|E24|row420理想支持|F0 99.82274096508216 Hz / 2倍右端2.1075133180秒 / 下限500 Hz|geometry-data.json|rows[1]|500 Hz推奨ではない|
|E25|既存PML音声との対応|元NPY SHA 082bd02b2d99751a844f503d91a3c6df5c7f98d60aef01c2c8d9ee481295c776|existing-audio-links.json|selected_audio[variant=PML].source_NPY_sha256|今回保存参照NPYと一致。音声の新規生成・複製なし|
|E26|27条件の追加観測|一部再構成確認で停止。寄与結果未採用|observation-data.json|pending_27_conditions|成功扱いしない。数値診断・照合後に更新|
|E27|固定7kernelの全周波数実効mask|14343 / 14343binが厳密M=1。M=0、分数Mは0|mask-counts.json|aggregate_by_band.all_4096_rfft_bins_including_DC_Nyquist|857pulse全体ではなく442–448のみ。DC/Nyquist含む|
|E28|帯域内の実効mask|1.5–3 kHz 2688bin、3–8 kHz 8960bin、すべてM=1|mask-counts.json; mask-counts.csv|aggregate_by_band; records 全21行|合成FFT4096。帯域観測FFT128と区別。比率はpower寄与率でない|
|E29|理想モデルでの条件付き平均|全M=1とGaussian列の符号対称性・正規化の偶性から0|README-ja.md|第9節|有限seed平均の実測ではない。有限精度全実装の厳密期待値とは別。品質改善を含意しない|
|E30|追加9条件のM集計|175セル枠 / 358575bin。M0=32132、分数=7000、M1=319443|additional-mask-summary.json|conditions[].all_bins; scope|1条件3方式でMは共通。1コピーだけ数え、失敗decompositionを使わない|
|E31|全周波数M1のセル枠|38/175。残り137に分数Mあり|additional-mask-summary.json|conditions[].all_spectrum_M_one_cell_ids|sample3 +3固定7kernelを一般化しない。独立標本数ではない|
|E32|条件09の強部3–8kHz|12セル×1280bin=15360binすべてM1、全周波数M1は4セルのみ|additional-mask-summary.json|region_support_counts[condition-09, own_band_strong_potential_support, band_index=1]|8セルの低域M<1由来の帯域混合を除けず、完成帯域の平均0は言えない|
|E33|停止4点の補助診断|80桁直接DFT。窓掛け・FFT差約1e−17～1e−16、OLAと最終減算0、Z加算約1e−21|fft-four-point-diagnosis.json|rows[0:4]; formal_interval_guarantee=false|旧失敗不変。全9条件の新契約合格やFFT実装の形式証明ではない|

## 段階B追補：別9条件・27方式行

|根拠|値・対応|出典|限定|
|---|---|---|---|
|E34 新契約の完了|9条件・27行・終了コード0|stage-b/source-evidence.json|旧失敗後の尺度改訂|
|E35 観測一致|η最大3.0547323575163517e−16、閾値1e−12|stage-b/summary.json|notch相対精度や理論誤差上界ではない|
|E36 旧false保持|18点、条件順4/1/4/3/1/0/3/2/0|stage-b/all-18-legacy-Z-failures.csv|初回停止4点を含む|
|E37 固定8強部損失|全8件ΔS<0、絶対ΔS>絶対ΔC、ΔC<0が6、正が2|stage-b/all-18-strong-events.csv|因果割合ではない|
|E38 尺度復元の条件付き差|FULL−SHAPEで6件低下、ID06/08は上昇|stage-b/all-18-strong-events.csv|未採用|
|E39 ID09 band0|強部FULL−SHAPE +0.7645564120491599dB、交差+12ms|stage-b/all-18-strong-events.csv|原音曲線はなし、閾値・交差だけ|
|E40 全符号付き項|1,050自己項行・11,820 pair-region行|stage-b/all-region-self-terms.csv、stage-b/all-region-signed-pairs.csv|負・正・零を保持|
|E41 原音交差|ID01〜08は−1〜+1ms、ID09は+7/+4ms|stage-b/all-18-strong-events.csv|PML相対差と分離|
|E42 全27入力OLA|byte一致、旧condition01の182配列も一致|stage-b/source-evidence.json|旧全波形証拠を再利用、再合成なし|
|E43 元配列の対応|型・形状・SHAを保存|stage-b/source-array-hashes.json|NPZ・全native kernel・S/Z本体は非同梱|
