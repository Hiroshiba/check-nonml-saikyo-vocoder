# RAW_FULL：研究baseと互換package pml

本変更では、限定16 kHz・今回評価した0/±3半音の研究baseとして **RAW_FULL（family/packageキー `pml`、version `raw-full-fwcep60-v1`）を選択します**。比較相手は前base PML / `pml-lowband-fwcep60-v1` です。固定120録音・40話者・2seedの既存結果に基づく事後の工学的選択であり、統計的な採用証明・普遍的最良ではありません。

[採用判断・厳密値・比較音声](../research/raw-full-adoption-selection-2026-10-20/index.html) ／ [全120録音の保存比較・順位](../research/raw-full-full120-comparison-2026-10-19/index.html) ／ [純解析・復号RTF](../research/raw-full-pure-rtf-2026-10-19/index.html)

予測MOS平均差+0.07676と小さいnative忠実度・話者類似度の利得を、MOS負差195/720・警告22/720、編集有声取りこぼし+0.1545ポイント・警告28/480、GT付き55録音のCER/WERの不利、保存約17.1%増・純復号wall RTF約5.24%増と交換します。単回・固定順の速度測定を普遍的性能比とはせず、新統合packageを計時済みとはしません。

## 保存表現とAPI

`vocoderbench.pml.encode(x, sr=16000, *, seed=DEFAULT_SEED, trace=None)` は、連続F0・60 FWCEP・二値NMと必須 `A_raw` / `L_raw` を持つ `RAWFullParameters` を返します。基礎解析の直後、同じ原音と未編集F0からA/Lを求めます。16 kHzモノラル限定で、自動resampleはしません。基礎解析の由来は[前PMLの図解](../research/pml-fwcep-2026-10-16/mechanism.html)、移植範囲と帰属は[package説明](../vocoderbench/pml/README.md)を参照してください。

公開 `save/load` と `save_parameters/load_parameters` は、`parameters.pml`（PMLFWC01成分）と非圧縮 `raw.npz`（A/L）の両方を含むpayload directoryを扱います。旧単一fileからの破壊的変更です。保存先は未存在のdirectoryに限定し、既存directoryを上書きしません。途中失敗したdirectoryは完成payloadではなく、別の保存先を使います。自動削除・rollbackはしません。

旧単体PMLからA/Lを復元する自動変換や旧独立decode fallbackはありません。履歴特徴の明示的読取りは内部 `vocoderbench.pml.storage.load_parameters` を使いますが、旧source-freezeの照合は緩和しません。公開 `decode(params, *, seed=None, trace=None)` は保存成分だけを読み、元WAVや事前波形を再参照しません。seed省略時は保存seedです。

`edit_parameters(params, *, pitch_semitones=0, gain_db=0, time_scale=1)` はFWCEP第0係数へ `gain_db*ln(10)/20` を加え、F0へ半音倍率を掛けます。A/Lは据え置き、編集F0で再解析しません。累積±3半音・50<F0<700・time_scale=1限定です。CLI/methods.editからこの経路を保ち、波形末尾の倍率や原音倍率再解析で代用しません。DC floor・丸めを含む近似契約であり、厳密倍率やRAWの実測gain追従性能を保証しません。

## 実行

Python 3.12 / uv。解析時はpyreaper 0.0.11・pyworld 0.3.5が必要で、Linuxの初回依存ビルドにはC/C++コンパイラが必要です。復号APIはNumPyとSciPyを使います。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.pml_cli encode input.wav features.raw --timing-json analysis.json
uv run --locked python -m vocoderbench.pml_cli decode features.raw output.wav --timing-json decode.json
uv run --locked python -m vocoderbench.pml_cli decode features.raw up3.wav --pitch-semitones 3
```

`features.raw` はdirectoryです。短すぎる音声・非有限値・完全な零信号はエラー。F0未検出時の上流65 Hz時計へのfallbackは警告に残します。FLOAT WAV出力を正規化・クリップしないため、ピークが1を超える場合は再生系で歪む可能性があります。

標準無編集比較は `python -m vocoderbench.reference --include-current-base --output runs/raw-full-reference-120`。参照方式の準備は[手順](REFERENCES.md)を参照してください。method familyは `pml` を維持し、新結果にRAW版を保存します。既存結果のPMLラベルをRAWへ書換えません。

候補比較の `benchmark --candidate-package` は `pml.py` にencode/decodeを持つGit外パッケージを受け取ります。標準benchmarkの8seed契約は維持し、本選択の固定120・2seed保存比較とは分けます。今回そのbenchmarkを実行したとはしません。

## 測定と制御表現の限界

RAWのgain追従性能、A/Lを含む全特徴の距離・補間・因子分離、任意target音高、native 48 kHzは未測定・未達のままです。確率的F0/VUVと生物・音響モデルの研究課題も解決済みとはしません。

旧PML部分への射影を再利用できることと、A/Lまで連結した全表現の距離・ABX・下流読み出しが良いことは別です。A_rawは8標本、L_rawは5 ms間隔でsource周期由来の包絡変動を保持し得ます。絶対target Hzで励振時計を変えても、保存包絡の周期成分が移動・除去される保証はありません。時間伸縮は未対応です。

保存費の約17.1%増と純復号約5.24%増は既存研究測定の値です。旧PMLの約805 kbpsをRAW全payloadの値として使いません。run003測定sourceの数値経路を静的に移植したことと、新統合packageの実計時・出力一致を分離します。新テスト・スモーク・回帰・保存往復・再decode自己比較は追加していません。

以下は前base PMLとそれ以前の測定履歴です。数値・版・採用時の比較基準は当時の意味のまま保持します。旧版専用生成入口は新RAW packageでの生成を拒否し、履歴読取りのsource-freezeは保持します。

## 過去実装・測定値

旧HNM本体と専用noise/supplement計算CLIは削除。過去のHTML/JSONは測定時の方式名・版・順位を保持する。履歴の再計算には変更前commit `bbab81f60674ffe5b898ba35575defa399e21d8e` を別checkoutで使う。

`all_metrics_*` / `added_metrics_*` は過去HNMを含む全8方式研究の経路であり、PMLへ機械置換しない。保存値の集計・他参照方式は残すが、旧HNM再計算は明瞭に停止する。当時のPML追加評価は下記の別入口を使います。48 kHz・時間編集は未対応です。旧HNMのAPI互換を偽装しない。

## 前base PMLの正式追加評価と確認範囲

当時のPML統合パッケージの120録音をseed 0で解析・保存・復号し、共通時間窓の品質71軸と編集・量子化61群、ABX・読み出し・ASV等を測定しました。[新結果HTML](../research/pml-package-evaluation-2026-10-16/index.html)と[再現手順](../research/pml-package-evaluation-2026-10-16/REPRODUCE.md)を参照してください。旧38軸探索結果は別測定として保持します。

公開用の追加評価driverは実測後にパスを引数化した版です。静的解析・独立レビューを行いましたが、この可搬CLIで全測定を再実行したという意味ではありません。標準benchmarkだけで全追加評価を自動実行するものでもありません。合成ソースは実測版から変更していません。

未対応・部分欠測・資源不足は[評価記録](PML_EVALUATION_PLAN.md)に残しています。テスト・スモーク・保存往復自己検査は追加せず、科学的な品質・制御評価と区別します。Pagesの本番生成はmainマージ後の既存workflowで行います。

## 統合CLIによる説明用1例（2026-10-16）

LibriSpeech `1089-134686-0008` の先頭6秒を新CLIで解析・保存・復号しました。解析5.185秒、復号0.917秒（単発・冷開始、解析時は後で修正した非推奨aliasの大量警告を含む）でした。この値は速度順位に使いません。新形式payloadは603,219 bytes、出力96,000 samples、peak 0.454845、±1超過0。原音との20 ms STFT収束は0.3160、帯域エネルギーMAEは0.4390 dBでした。

これは説明用の追加生成であり、既存120録音の再測定、旧波形との一致検査、品質採用の十分条件ではありません。初回はpyreaper依存が無い環境で失敗し、既存の解析runtimeを指定して生成しました。ソースの非推奨 `row_stack` aliasは同じ `vstack` 関数へ置換し、警告を隠す処理は追加していません。

追加評価の全群・優先順・再利用条件・終了条件は [評価計画](PML_EVALUATION_PLAN.md) に記録しています。
