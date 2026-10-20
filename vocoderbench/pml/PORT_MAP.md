# PML 移植元と改変対応

上流の著作権表示・Apache-2.0 を保持しています。原著者は Gilles Degottex、Copyright (C) 2016 Engineering Department, University of Cambridge, UK。

- PML: https://github.com/gillesdegottex/pulsemodel/tree/f1d0fbb397368e019efa4dfc96bde09482cd734b
- sigproc: https://github.com/gillesdegottex/sigproc/tree/289d9dffe1f6ba84fa1fe962d6fb6e1062ec1cf6

## 関数対応

| このパッケージ | 上流 |
|---|---|
| pml_analysis.f0_postprocess | pulsemodel/analysis.py analysis_f0postproc、sigproc/resampling.py f0s_rmsteps / f0s_resample_cst |
| pml_analysis.noise_mask | pulsemodel/analysis.py analysis_nm |
| pml_analysis.analyze | pulsemodel/analysis.py analysis / analysis_spec / analysis_pdd |
| pml_pdd.pitchsync | sigproc/resampling.py f0s_resample_pitchsync |
| pml_pdd.ceiling_resample | sigproc/resampling.py featureresample |
| pml_pdd.extract_peaks | sigproc/cython/sinusoidal.pyx extract_peaks |
| pml_pdd.sinusoidal_params | 同 estimate_sinusoidal_params / compute_dft |
| pml_pdd.estimate_pdd | 同 estimate_pdd |
| pml_synthesis.synthesize | pulsemodel/synthesis.py synthesis |
| pml_helpers | sigproc/sigproc.py mag2db / butter2hspec / hspec2minphasehspec |
| fwcep | sigproc/freqwarp.py FWCEP 変換と sigproc.py lin2mel |

## 保持した挙動

Python 2 の整数標本化率による整数 Hz グリッド、符号付き peak argmin、ceil 側への特徴量リサンプル、filtfilt のトレンド処理、欠けた倍音のゼロ埋め、境界窓のパディング、スペクトルゼロの微小値置換、最小位相化を保持します。FWCEP の全次数時の Nyquist ケフレンシー端点倍化も保持します。これらをより一般的と思われる別の式に置き換えていません。

## 明示的な改変

2026-10-15: Python 3 / NumPy / SciPy への限定移植。F0 範囲 65–700 Hz、FFT 4096、フレーム 5 ms。上流の振幅包絡 `10*sqrt(power)` を校正した `sqrt(CheapTrick power)` にし、合成の `ener_multT0=True` と組み合わせます。StoneMask は CheapTrick だけに適用します。PDD の v<1 分岐は同じ条件の配列演算にしました。未対応の AM/FM 復調や STRAIGHT は含めません。

2026-10-16: 既測定の低域マスク延長を固定し、60 FWCEP float32 に圧縮。パッケージ相対 import、局所 RandomState、公開 encode/decode/save/load API、形状・数値・適用範囲の検証を追加。未使用の代替設定・描画・対話デバッガーを削除。乱数生成アルゴリズム・呼出し順、複素64のパルス処理、float64 の復号包絡を維持します。

独自追加の API と保存形式は、このリポジトリへの統合用です。上流 CLI の抽出と pyreaper API の抽出は同一精度と主張しません。REAPER API の float32 出力を float64 へ昇格させた量子化は残ります。

CLI デモで非推奨警告がフレームごとに出たため、NumPy の `row_stack` 別名を同じ演算の `vstack` に置換しました。警告をフィルターで隠す変更ではありません。

## 2026-10-19 RAW_FULL 統合（本変更で選択）

- `raw_features.py`: run003 `pure_rtf/raw_features/features.py` をbyte同一で移植。診断配列計算も削除しない。
- `raw_noise.py`: run003 `pure_rtf/raw_noise.py` から移植。requireをファイル内へ移動しただけでcontroller数値式・guardsは維持。
- `pml_synthesis.py`: run003 RAW backendを唯一の合成実装へ置換。reference_modeの非既定source_value/source_maskを削除、edited経路を保持。noise_modifierは必須keyword引数となり、Noneなら旧復号する分岐を削除。RNG、D0、clock、nearest row、mask、複素べき、最小位相、taper、OLAは保持。
- `pml_helpers.py` とライセンスは既存共有ファイルを使い、重複backendを追加しない。測定RAW helpersと現main helpersのソースは同じ。
- codecは基礎解析を内部関数へ分離し、A/L生成を追加。公開復号は必須RAW型だけ。native-only pitch==0 guardは採用せず、既存累積±3編集契約を適用。
- storageはPML成分serializerと過去結果読取りとして保持。公開保存境界は新規payload.pyへ移す。

この移植の確認はソース読取り・AST・キャッシュ使用Ruffのみ。新テスト・スモーク・回帰・保存往復・再decode一致・音声計算は実施しない。
