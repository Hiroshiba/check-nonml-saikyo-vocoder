# full-grid exact BF 再評価の入力可用性：静的段階記録

2026-10-20。指定evidenceのproducer-run.py、model.py、inputs.json、EVIDENCE-MANIFEST.jsonと既存逆写像レビューを読んだ。source実行/import、数値計算、コード作成、原波形再生成はしていない。full-grid開始承認ではない。

## 結論

**今回確認した保存BF/priorと固定2周波数の十分統計だけでは、元と同じr bitsによるfull-grid exact BF再評価には足りない。** ただしproducerは原入力と全観測窓の `.npy` を保存する設計なので、最初の次工程は再生成ではなく、それら既存artifactの所在・実在・hashを読取り確認することが合理的である。今回のevidenceディレクトリには該当 `.npy` はなく、保存処理の存在と原artifactの現在の取得可能性を区別する。

## 1. 本文で確認できた範囲

- modelはQ=52..512、K=1..10、N400、FS16000、hop160、FFT16384、VAR_SPEECH=5e-6。Projection.costsはframe全候補のJを一時的に作り、log_bayes_factorはr=J/(energy+N*VAR_SPEECH)を一時的に作る。
- producerの各frame NPZはfull-grid logBF、prediction_prior、filtered_joint、local_joint、initial_prior、transition_term、memory_term等を保存する。一方、J/fit/codは `*_fixed_cells_all_k` として `j[list(CELLS)]` の2周波数×全Kだけを保存する。full-grid J/r配列を保存する文はこのproducerにない。rowのj_min/j_max/r_min/r_max等は全配列の代用ではない。
- producerはnoise-unscaled.npy、clean-U-block.npy、clean-E-block.npy、各条件の `*-input.npy` と `*-observations.npy` を保存する。後者はzero paddingを含む全frameのN400観測窓。modelのcostsは渡された観測を直接FFT・投影し、この本文にdemean/windowの追加処理はない。
- inputs.jsonはnoiseと各input/observations **ファイル全体** のSHAを保存し、suffixは配列のtobytes()をhashする。各frame JSONのobservation_sha256もy.tobytes()であり、ファイルSHAとは対象が異なる。照合対象を混同しない。
- EVIDENCE-MANIFESTは3本文について元path、SHA、byte_identical=trueを記載する。この段階では配布本文を静的に読んだのであり、元pathのファイルや元観測artifactを独立取得してbyte比較したとは主張しない。

## 2. 投影の再計算はいつ必要か

full-grid r bitsまたはfull-grid Jと元energyの完全な保存artifactが別に見つかれば、それを優先して入力契約を作れる。しかし今回のproducerではそれを保存していないため、**この出力形式から進むなら、原観測を取得してProjection.costsを再計算する必要がある**。これは保存値の引算とは異なる新しい科学計算であり、別承認・固定契約を要する。

原observations.npyが回収できれば波形生成のやり直しは不要。input.npyだけがあれば既存支持・padding規則で観測を切り出す段階が追加される。どちらも元hash照合を先に行う。原観測がbit一致でも、FFT/三角関数/Gram/Cholesky/総和などの再計算が元J/r bitsを再現することは、入力一致だけから保証されない。source、依存版、数値backend、実行環境を固定し、既存固定セルと旧full-grid S等を照合する契約が別途必要である。旧S一致だけを全grid r bitsの証明にはしない。

既存逆写像レビューは理想Laplace式の厳密単調性を認める一方、丸め済み実装Sからoriginal binary64 rの一意復元を一般保証しない。これを再導出・再適用しない。「一切のケースで復元不能」とも強めない。今回のfull-grid欠落を、逆変換で確実に補えるとは扱わない。

## 3. metadataだけでraw bit一致再構成を主張できるか

**できない。** seed/PCG64、NumPy版、共通scale、生成式、hashは再構成候補と検証基準を与えるが、raw標本そのものではない。sin・sqrt・乱数normal変換・演算順・dtype/backend等を含む生成過程のbit再現は、metadataがあるだけで実証済みにならない。producerはPython/NumPy/SciPy版とthread設定も制約するが、その記載だけで再生成結果の同一性を保証しない。

原artifactが失われていて再生成を提案する場合は新計算として扱い、生成後に保存ファイルSHAとframe payload hashをそれぞれ正しい対象で照合する。hash不一致を「ほぼ同じ」で元実験のbit同一入力と呼ばない。今回は再生成も照合実行もしていない。PCM16音声への置換も元float64観測の復元ではない。

## 4. 次契約で保持すべき最小情報

1. 原入力または原観測のlossless binary artifact、ファイルSHA/bytes、dtype・endianness・shape/order、frame支持とpadding、観測payload hash、来歴manifest。元artifactをまず回収し、再生成の必要性を判定する。
2. 全Q/Kの候補軸、frame/条件ID、energy、**full-grid r/codの元binary64配列またはbits**。Jも全gridで保存し、計算式とλ・Nを併記する。将来のBFだけの比較にはrを直接残すのが最小で、J/energyだけから再算出する丸め経路を避けられる。fitは補助でありrの代用品としない。
3. sourceと依存/backend/environment pins、Gram監査・projection failure・energy-floor・欠測状態、r範囲判定。clip/floor/候補除外を追加しない。再投影の一致/不一致を旧rそのものの確認と区別して報告する。
4. BF評価のS/L/E保存値・精度/非保証性・失敗台帳と全予定候補。旧prior凍結比較ならfull-grid旧prior/H0を保持する。再追跡なら同一状態表現のL/Eそれぞれのprediction prior、posterior、H0、memory・更新/skip履歴と初期/transition契約を保存し、旧prior固定と混同しない。

この段階の停止点は「保存十分統計は固定2周波数のみ、原観測保存処理は存在、原artifactの現在の取得可能性は未確認」の確定である。全grid再評価・再追跡の実施、資源枠、採用判断はまだ決めない。

## 参照

- `/workspace/shared/pitch-history-contrast-source-review-v1-20261020/package/evidence/` の上記4ファイル。
- `/workspace/shared/pitch-laplace-inverse-independent-review-20261020.md`：理想逆写像と丸め済みSの識別可能性の区別。
- 既存 `pitch-exact-bf-existing-artifact-coverage-20261020.md` の保存範囲調査を更新する限定的source確認であり、新BF検証の重複実施ではない。

## 後続追記：原NPY回収後の取得可用性確認

2026-10-20。上記「現在の取得可能性は未確認」はsource読取時点の履歴として残す。その後、原NPY9件が回収され、独立byte監査が完了した。

- noiseと3条件のinput/observations計7件は元inputs.jsonのSHAと一致。clean U/Eの2件は元SHAがなく、今回取得bytesのhash確認に限定する。
- 全309 observation row payloadのhashが元selected framesのhashと一致。固定100履歴pairは左右row bytesも一致し、PAIRSのhashへ接続した。
- これにより**原観測の取得可用性のみ確定**した。波形再生成、J/r再投影、fullgrid統計取得・BF評価・追跡は未実施。保存full-grid J/rの不足が解消したとは扱わない。

詳細と確認限界: [原入力回収の独立レビュー](pitch-original-input-recovery-independent-review-20261020.md)。本追記は文書更新だけで、新計算・実行開始ではない。
