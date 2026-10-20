# PR95 独立静的レビュー

2026-10-20 UTC。対象: [PR95](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/pull/95)。base `8ff2aea6e9583661841fe14aecb27c60e3366e90`、head `aa60946abeb66cbe35f86340145c12d55878fde7`。

## 判定

**今回の限定範囲では、修正必須の問題は見つからなかった。静的な契約は支持する。** 実行結果・配列/保存bytes・音声の一致、NPZ往復、性能、CLIの動作を確認したという判定ではない。CI・マージ・本番公開の判定も本レビューに含めない。

- 必須指摘: なし。
- 任意事項: NumPy pinを将来変更する際は、`savez` の `allow_pickle` 引数契約を再点検する。現行固定版への修正要求ではない。
- 任意事項: 5配列だけの診断NPZに音声hash・前処理・依存binary等の完全な来歴は含まれない。現在の文書もメタデータを含めないと明記しており不整合はないが、将来の利用時も自己完結の再現認証資料とは扱わない。

## 確認範囲と方法

6変更ファイルの原文・diff、基準codec/CLI/storage/説明文書、固定依存を記す `pyproject.toml` と `uv.lock`、既存のREAPER一次ソース調査・独立確認を読んだ。保存された6候補ファイルのGit blob SHAを計算し、`files-and-patches.json` の6 SHAとすべて一致することを確認した。

候補Pythonは `ast.parse` による構文木の静的比較だけを実施。PML・NumPy・SciPy・pyreaper・候補モジュールはimportしていない。候補CLI、`--help`、実装の動作確認、tests/smoke/regression/self-tests、dummy配列、NPZ roundtrip、音声取得・解析・生成、新計測は一切行っていない。候補コードは変更していない。本レビュー自身ではRuffも実行していない。

## 1. encodeの元データフローとdefaultの保持

対象: [codec.py L38–65](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/vocoderbench/pml/codec.py#L38-L65)、[L80–91](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/vocoderbench/pml/codec.py#L80-L91)。

- encode署名のAST、REAPER呼出しの引数ASTは基準と同じ。呼出し箇所は1個であり、診断用の再呼出しはない。int16前処理、65/700 Hz、high-pass/Hilbert、10 ms/5 ms、unvoiced_costも不変。
- 5コピーは `trace is not None` 分岐の中だけ。元dtype/shape/値の `.copy()` を `pm_times/pm/f0_times/f0/corr` の5キーへ保存し、コピーにcast・負値置換・補間を加えていない。
- `del pm_times, pm, corr` が `analyze` より前にあり、defaultで新たなpm配列を重い後段まで保持しない。従来の `_` がcorrを保持していた状態より保持を増やす構造でもない。`times/f0` は従来のraw_f0生成にそのまま使う。
- `raw_f0 = column_stack(...).astype(float64)` とF0列の負→0処理は基準そのまま。元配列のコピーから独立している。成功時の既存trace更新に `reaper` を加えるだけで、返り値を変更しない。
- 新docstring、戻り値を受ける変数名、任意コピー分岐、不要参照のdel、trace更新の新キーを正規化して除くと、encodeの残り全処理のASTは基準と一致した。SPEC/PDD/NM/F0・FWCEP・seedに計算変更を読み取れない。
- decode全体のASTとCLI `read_audio` のASTは基準と一致。保存形式/parameters/解析・合成実装はPRの6変更ファイルに含まれず、通常PMLへ診断配列やNPZ参照を追加していない。これは差分による静的判断であり、bit-exact出力を測定したものではない。

## 2. NPZの5キーと固定NumPy API

対象: [CLI L55–69](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/vocoderbench/pml_cli.py#L55-L69)。

`pyproject.toml` L8、`uv.lock` L354・389–392はNumPy 2.3.5を固定する。[公式v2.3文書](https://numpy.org/doc/2.3/reference/generated/numpy.savez.html)と、独立に取得した[公式v2.3.5実装](https://github.com/numpy/numpy/blob/v2.3.5/numpy/lib/_npyio_impl.py)で確認した。

`savez` の `allow_pickle` はkeyword-onlyの明示引数で、配列用の `kwds` には入らず、内部の保存関数へ制御引数として渡る。したがって `np.savez(handle, allow_pickle=False, **reaper_arrays)` は固定版では「allow_pickleという第6配列」を作らない。5キー辞書しか展開しておらず、非圧縮保存の経路である。古い未対応NumPy版のAPIを現行固定版の不具合として扱う根拠はない。

公式実装はfile-like objectを受け取った場合は拡張子追加分岐を通らない。CLIが `open('xb')` のhandleを渡すことは、厳密な指定PATHと排他的新規作成の契約に整合する。pickle無効化は実装上の引数契約として確認したもので、ファイルを実際に作ったり読み戻したりはしていない。

## 3. 衝突・上書き・失敗・計時

対象: [CLI L34–86](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/vocoderbench/pml_cli.py#L34-L86)。

- 新オプションはencode側のparserのみ。defaultは `trace=None` で、診断dict/コピー/NPZ保存は発生しない構造。
- 入力と全出力を `resolve()` し同一宛先を拒否する。出力事前検証は解析前で、既存ファイル・directory・symlink（danglingを含む）を拒否する。
- 特徴量は既存storageの `xb`、診断は `xb`、timing JSONは `x`、decode WAVも `xb`。事前exists判定後に同じ最終宛先が作成されても、排他的作成により上書き/truncateする構造ではない。悪意ある並行ancestor-directory差替えまで防ぐ、という追加のセキュリティ保証はしていない。
- decode WAVの変更はhandle渡しによる排他的作成。[固定SciPy 1.17.0の公式実装](https://github.com/scipy/scipy/blob/v1.17.0/scipy/io/wavfile.py#L789-L939)もopen file handleを受け取る経路を持つ。dtype=float32、sample rate、合成処理の変更はない。
- 特徴量→診断→JSONの順で保存し、例外を握りつぶすcatchや完成済み出力のunlink/rollbackはない。完了logは全保存の後。[既存run_cli](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/vocoderbench/logging_utils.py#L50-L64)の `logging.exception` と非ゼロ返値へ伝播する。不完全な失敗先ファイルが残り得る点も文書が明示する。
- 計時は既存どおりencode/decode呼出しの前後のみ。5配列コピーはencode内部なので計時へ入るが、診断時はJSONへ `reaper_trace_capture_included: true` と非比較の説明を付ける。NPZ等の保存I/Oは計時外。通常速度順位へ混ぜないという文書と整合する。
- CLIは `reaper_arrays` を取り出して `del trace` した後に保存するため、不要な大きいfeatures/diagnosticsへのtrace由来参照を残す構造ではない。paramsが必要とするNM/F0まで解放するという意味ではない。

## 4. 文書の意味とリンク

対象: [REAPER任意診断仕様](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/aa60946abeb66cbe35f86340145c12d55878fde7/docs/PML_REAPER_TRACE.md)。

- L19–27はmark系列とF0/corr系列を別格子・別長として扱い、同じ添字でepoch-confidenceへ対応させない。float32の生値、負F0 sentinel、float64 raw_f0、後処理済み正F0を区別している。
- L44–48は無声人工補充・区間基準・境界留保、有声markの音響推定性、pmの有声period端点規則、corrの非校正/非posterior、格子への割当て・前値埋め/上書き/先頭zeroを説明し、既存の限定修正済み調査と整合する。
- 通常5戻り値に内部pseudo-probabilityやper-epoch内部診断を含めず、新たな生理的GCI真値や校正済みconfidenceを主張していない。
- L3は今後の同じ呼出しの値保持であり、過去に捨てた配列を復元する機能ではないと明記。旧調査の「未保存」は調査時点の記録として残す。通常PMLの保存・復号方式を変更せず、新ボコーダー採用や音質/速度の新実測として扱っていない。
- 新しいPML/STATUS/READMEから仕様書への相対リンクはそれぞれのdirに対して正しい。仕様書の3つの既存調査・棚卸しリンク先は、固定headのGitHub contents読取で3ファイルの存在を確認した。親から保存された資料の内容とも整合する。リンク検査用サイト生成や実行はしていない。

## 限界

実際のpyreaper戻り値・配布binary、過去の全保存物、完成NPZ、WAV、性能は未観測。通常処理と診断時処理の出力一致・速度不変を認定しない。今回の合格相当の意味は、指定された静的変更契約に必須修正が見つからなかった、という範囲に限る。
