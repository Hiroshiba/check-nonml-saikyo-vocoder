# 確率的F0・H0診断：固定5録音の質量・事前分布・欠測

現在のbaseは `pml-lowband-fwcep60-v1`（PML）を維持する。今回の直接harmonic射影は固定5入力の確率診断であり、新しい音声合成器の採用比較ではない。新候補音声を生成しておらず、自動MOSなどの品質指標は未測定。音声を捏造・複製せず、[既存PSHF・PML・RAW_FULL比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/pshf-residual-envelope-2026-10-20/index.html)へ案内する。

[結果HTML](results/run-001/index.html)、[集計JSON](results/run-001/summary.json)、[表示数値の記録](results/run-001/numerical-display.json)、[研究文書一覧](research/README.md)を保存した。調査文書は提供された固定資料であり、この保存作業で新たな調査や検証を行ったものではない。執筆時点の未実行表記はそのまま保持し、実行後の経過は本READMEを参照する。

## 固定実行と解釈

run-001は5/5録音、計2614フレームを完了した。2540がvalid、74がsample3（121-121726-0012）のenergy-floorによる観測欠測で、未処理0。実行wall時間は24.328012433019467秒（約24.328秒）。録音別RTFや独立反復の推定には使わない。元の計算package SHA256は `91bbb8aa6847da965cdb31bcb82f97b985dedf7d7cc4a469debc240a5fdc3819`。

16 kHz、25 ms窓、10 ms hop、F0範囲50.78125–500 Hz、K≤10の固定設定。H0は有限harmonic/whiteモデル内の相対的支持であり、生理的VUV、雑音電力、校正済み確率や真F0ではない。重複窓と時間事前分布による集中を独立証拠の増加や音質改善と解釈しない。作者MATLABとのbit一致再現は主張しない。

補助図のPML由来参照clockは、既に公開済みのmetadataにある `source_f0_hz` と `center_seconds` を使う。PSHF観測格子へ補間した時計であり、元PML格子そのものや正解ではない。`voiced` は使わない。欠測をH0=1や過去posteriorで埋めない。octave対の存在数には微小な峰が含まれるため、強い音声的競合の件数とは呼ばない。

## 保存解析と描画の経過

1. 初回保存解析はNumPy boolのJSON直列化で `TypeError: Object of type bool is not JSON serializable` となり停止した。部分出力を完了扱いせず、`.item()`による報告上の直列化修正後に保存解析v2が完了した。F0推定は再実行していない。
2. 初回描画はF0 marginalの厳密な `[0,1]` 検査で `ValueError: Invalid marginal mass` となり停止した。保存値の最大は1.0000000000000548で、元モデルが宣言した丸めbound内の1超過だった。
3. 保存配列診断で大きなlog残差の上位例にsubnormalのpost質量を確認した。報告修正版の保存解析v3ではraw残差を残し、normal/subnormal/zeroを層別化し、octave対の小側local領域質量の全validフレーム分布を追加した。推定器・logBF・posteriorは変更していない。normal支持の最大絶対残差はcell log-updateが2.220446049250313e-16、octave oddsが1.7053025658242404e-13。解析summary SHA256は `1274a9381cc2750454d6df9be337bb44efa1c9401e6b57da4ee3573fe8caf012`。
4. 描画修正版は生値をclip・再正規化せず、元モデルと同じ `128*461*10*float64_epsilon` の丸めboundを許容し、実値をnumerical-display.jsonへ保存した。最終renderer v3では主図の参照線を除き、参照線付き図と固定log色尺度図を補助表示に分離し、sample3 frame 212の保存値による説明を追加した。これは表示の変更で、推定・解析を再実行していない。

sample3の主図・log図・参照線付き図と、別1録音の主図を実PNGで確認した。主図で参照線による遮蔽が解消し、log図で微小質量が見える。比較軸・固定色尺度・灰色欠測を確認した。Cloudで報告した補助図タイトル上端の欠けは、親側の同SHA画像では再現せず、タイトル全体と上端23 pixelの白余白を確認したため、追加修正は行っていない。ブラウザ操作と本番Pages確認は今回未実施。

## 公開成果物と保存範囲

実際の最終描画日時は **2026-10-19T21:47:23.432775+00:00**（日本時間2026-10-20）。測定時刻とは別で、一覧登録はこの実時刻を使用する。公開用は131件＋manifestの132ファイルで、全SHA256・byte数を照合した。manifestは22,576 bytes、SHA256 `be345414b33b6afeba3ed80b0fbaff1bb69d2824325b9ec06ec0efe8c2641756`。元のHTML/PNG/CSV/JSON/gzipとmanifestのbytesを変更していない。

既存navigation-only registryから `research/probabilistic-pitch-diagnostic-2026-10-20` へ登録する。HTMLの `../pshf-residual-envelope-2026-10-20/index.html` は公開配置で既存比較へ解決する。全HTML参照51件と実成果物の整合性を確認済み。元音声、full joint、実行ソース、private解析ログはGitに含めない。研究文書とその提供manifestは `research/` に分離し、公開成果物manifestへ追加しない。

PRでは静的lintと実成果物照合までとし、build_siteの予行・Pages実行・マージは行わない。DraftのレビューとCI、後の明示された公開工程が残る。新しい計測・候補採用やbase変更をこの記録から自動的に開始しない。
