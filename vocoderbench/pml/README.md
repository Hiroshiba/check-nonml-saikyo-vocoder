# PML・低域雑音マスク拡張・60 FWCEP

非 ML の 16 kHz 用研究実装です。元波形を保存せず、連続 F0・包絡の 60 係数・二値雑音マスクから復号します。48 kHz、時間伸縮、ストリーミング解析には未対応です。短音声を黙ってパディングするなど、測定外の補修は加えません。

```python
from vocoderbench.pml import encode, decode, save_parameters, load_parameters

params = encode(mono_float_wave, 16000)
save_parameters(params, "speech.pml")
restored = load_parameters("speech.pml")
y = decode(restored)
```

- `encode(x, sr=16000, *, seed=20261015, trace=None)` は `PMLParameters` を返します。入力は有限の `[-1, 1]`、mono、0.2 秒以上。完全なゼロ信号は明示的に拒否します。解析には pyreaper と pyworld が必要です。
- `decode(params, *, seed=None, trace=None)` は float64 の波形を返します。NumPy と SciPy のみで復号できます。出力の正規化・クリップは行わず、ピークが ±1 を超えた場合は警告をログに流します。保存値以外の seed を指定すると別の雑音実現になります。
- `save_parameters(params, path)` / `load_parameters(path)`、短縮名 `save` / `load`。保存先が存在すれば例外とし、意図しない上書きをしません。
- `edit_parameters(params, *, pitch_semitones=0, gain_db=0, time_scale=1)` はコピーを返します。音程編集は保存元から累積 ±3 半音までの実験的機能です。時間伸縮は `NotImplementedError`。ゲインは FWCEP の第 0 係数に加算しますが、DC floor と float32 丸めのため厳密な波形倍率ではありません。

## 特徴量と解析経路

`PMLParameters.f0` は float64 の正の合成クロックです。無声区間でも 0 にせず、REAPER の有声区間から補間します。全区間で F0 が未検出なら上流仕様に従って 65 Hz を使用し、警告します。これはその区間に声帯周期があるという主張ではありません。REAPER の int16 入力変換は `rint(x * 32767)`。返却された float32 F0/時刻は float64 テーブルに変換し、負の F0 を 0 にします。

`fwcep` は `(フレーム数, 60)` の float32。StoneMask で調整した F0 を CheapTrick に渡し、そのパワー包絡の平方根を振幅包絡とします。自然対数を取り、上流 sigproc の周波数ワープ・ケプストラムを 59 次まで保持します。StoneMask の F0 は包絡推定だけに用い、PDD と合成には元の後処理済み F0 を用います。

`noise_mask` は `(フレーム数, 2049)` の bool。周期同期解析から求めた PDD の閾値 0.75 と形態演算で作ります。PDD 自体は保存・復号に不要です。二値マスクの低域処理は合成時に行います。

## 合成経路

F0 からパルス時刻を作り、最寄りフレームの包絡とマスクを選びます。2 F0 境界の最初の非保護ビンのマスク値を低域にも延長し、周波数方向で平滑化します。0.5 F0 の高域通過応答と最小位相包絡をパルスに掛け、パルス間隔に応じてエネルギー補正します。正規化したガウス雑音の複素スペクトルをマスクでべき乗して掛け、逆 FFT と加算で波形を作ります。周期音と雑音を単純に足す方式ではありません。

音程を変えるとパルス時刻だけでなく、高域通過応答・低域マスク境界・雑音の時間支持・エネルギー補正も変わります。±3 半音の既測定条件でも有声／無声判定に変化があり、編集品質は保証しません。

## 保存仕様

形式は研究用旧 `PMLFWC28` とは異なる `PMLFWC01` です。互換読み込みや推測変換はしません。

1. 8 バイトの magic `PMLFWC01`
2. little-endian uint32 の UTF-8 JSON ヘッダー長
3. JSON ヘッダー
4. F0 `<f8` をフレーム順、FWCEP `<f4` を C 順、二値マスクを行ごとに little-bit-order で pack した順の本体

ヘッダーは `schema=pml-fwcep60-lowband-v1`、`sample_rate=16000`、`nfft=4096`、`step=0.005`、`frames`、`n_samples`、`seed`、`pitch_shift_semitones`、`body_sha256`。時間軸は `arange(frames, dtype=float64) * float64(0.005)` で復元します。マスクは 2,049 有効ビット＋末尾ゼロ 7 ビット、257 バイト／フレーム。フレーム本体は 8＋240＋257＝505 バイトです。

量子化 codec ではなく、16 kHz・16 bit PCM より高いビットレートです。無劣化の包絡保存でもありません。

## 診断と再現性

任意の辞書を `trace` に渡すと、encode は解析特徴量と診断値、decode はパルス時刻・実効マスク・雑音統計を追加します。decode の `pulse` は 0.25 秒以後のパルスがある場合のみ存在します。短音声でその項目を必須として扱わないでください。大きい診断配列は通常の保存表現には入りません。

encode成功時は `trace['reaper']` に `pm_times`・`pm`・`f0_times`・`f0`・`corr` の元dtype・値の独立コピーも追加します。既存の負値を0にしたfloat64 `raw_f0` と異なり、負F0 sentinelを保持します。イベント格子と5 msフレーム格子、型・単位・解釈の留保、CLIの明示保存オプションは[REAPER任意診断の仕様](../../docs/PML_REAPER_TRACE.md)を参照してください。`trace=None` ではコピーせず、解析経路・返り値・保存仕様は同じです。

合成乱数は局所 `numpy.random.RandomState(seed)` です。旧測定 runner の `np.random.seed(seed)` と同じ MT19937 初期化および `normal` 呼び出し順を用います。これは実装の静的対応の説明であり、別バージョンの依存環境まで bit-exact と保証するものではありません。Ruff の整形、相対 import、公開 API の検証、ログ追加、未使用の描画・デバッガー・設定分岐の削除は数学的な演算順を変更しないように行っています。

エラーは呼び出し元へ伝搬します。CLI 側でスタックトレース付きログに記録してください。SciPy の系列長不足などのエラーを黙って握りつぶしません。

## ライセンス・出典

上流コードは University of Cambridge, Engineering Department (2016)、Gilles Degottex、Apache-2.0。ライセンス全文は `LICENSE-PML-SIGPROC.txt`。出典と改変対応は `PORT_MAP.md` に記載しています。
