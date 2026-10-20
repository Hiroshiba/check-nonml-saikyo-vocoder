# phase-origin source v1：入力・保存の独立差分レビュー

2026-10-20。対象 `phase-origin-source-review-v1-20261020/package`、比較元v0。V1-REVIEW-RESPONSE、INPUT/SEED/SCHEMA/BYTE-BUDGET、model/worker/preflight/storage/calibrationの差分と関連入口を静的読取。独立stdlibによる保存JSON/hash/整数照合のみ。候補import・実行・PRNG初期化・科学数値計算・testsは行っていない。

## 結論

**本担当範囲でPASS。v0入力レビューのB1/B2/C1は解消を確認し、新たな開始阻害は見つからなかった。** これは科学開始許可でも、数値収束・実行時間・全500完走・保存cap適合の実測保証でもない。数理詳細・process lifecycle・開始時の全ホストclaim一意性は別レビュー/証拠を必要とする。

## 1. 入力・seed・truthとpins

- SOURCE-MANIFEST SHA `237b2ff1ec1e2f4c51f78f4b79ebecc8047f9d28b0edd4fe71946b8166d1ced7`。全49 entriesのfile集合・bytes・SHAが実packageに一致。
- INPUT-MANIFEST SHA `b60194d8460f6499dfd7fc9549707b688587ef35c835074837232c0f06b523e4`。JSON比較で変更は `calibration_trig_basis` 一項目の追加だけ。study名、truth値、N/L/K、全500行、digest_words、精度/gateは不変。owner件数167/167/166も確認。
- SEED-OWNER-MANIFEST、DEPENDENCIES、source/storage.pyはv0とbyte同一。seed mappingとtrain/test split/component入力の変更なし。実依存環境やPRNG出力は今回検証していない。
- input hash変更の理由は、50/80dpsごと独立64位相三角表を作り、n昇順の各Y項をmp.fsumする計算法の明示。Yの位相別事前集約はない。理想周期OLSは同じだが、従来のn全域角評価とは有限精度手続きが異なり、v0校正値のbyte同一性を主張しない。実測前変更として明記され、truth/生成/seed変更と混同しない。

## 2. B1：推定側各精度の返却保存

model.scoresは各density返却直後に `persist(digits,list(map(txt,estimate)))` を呼び、次精度/比較gateへ進む前にworkerのsave_estimateで `estimated_score60/90` とreturned stageを保存する。Pair.save→atomicはpartial書込・file fsync・replace・directory fsyncであり、60側の永続化を終えてから90側へ進む。後続失敗で字段を削除しない。

SCHEMAのadditionalProperties=falseに対し、estimated_score60/90の4文字列配列字段を追加。順序はdensityのlogdet/Q/constant/scoreでoracleと同じ。二精度統合scoresとは別に保存される。これによりv0の「90側失敗時に60側をRAMから失う」不備は解消。

ただし返却直後から保存完了までのkill/I/O障害をゼロにする保証ではない。原partial・intent・終端証拠を監査し、保存が確認できない値を返却済み保存値と称さない。また正常/数値失敗後のstageは広い工程名で上書きされるため、単精度字段自体も証拠として確認する。

## 3. C1：oracle残差・raw枠

oracle診断残差はtrain/test生成後、oracle density前、校正前に一度保存。estimated残差はestimated geometry後に一度だけ保存する。SCHEMA residual_stageも同じ規則を明記し、校正失敗でoracle残差まで欠ける旧仕様を解消した。oracle以前の生成失敗等まで残差存在を要求するものではない。

保存順の変更で各blobの実offsetはv0と同じとは限らない。descriptorのoffset/bytes/shape/hashを正本とし、固定offsetを外挿しない。配列の重複追加はなく、raw cap334960、metadata cap16384、root各12288、Pair予約375920は維持。新estimated字段はmetadata枠内でguardされ、枠超過は失敗であり切捨てなし。現実のmetadata長が必ず枠内と今回実測認証したものではない。

BYTE-BUDGETはclaim/RUN枠、protocol/terminal partial枠とparent原文の別evidence工程を更新。pair raw増量による変更ではない。ownerの固定1MiB/終端2MiBの予約を保つ設計であり、runtime cap停止も予定分母500から除外しない。

## 4. train-only隔離とassert排除

calibrateは依然 `calibrate(records[0],pair.roots)` のみで、test・truth・oracle scoreを引数に渡さない。callbackは保存用。modelの生成部分は変更されず、train/test別seed・初期AR・innovation/s/jとtestへのcarryなしを維持。共有oracle geometryは決定的定数であり乱数実現共有ではない。二heldout scoreのみ、noise refit/勝者選択なし。

稼働sourceのassertは検索上ゼロ。preflightは明示check→RuntimeErrorへ変更し、load冒頭にrequire_unoptimizedを置く。sys.flags.optimizeとPYTHONOPTIMIZEを明示検査し、workerはloadを科学import前に実施する。external、supervise、handshake/process入口、保存工程にも最適化拒否がある。v0の「-Oで必須pins検査を消せる」不備はこの静的構造で解消される。

model.rnもmp.isfiniteをtuple分解前に要求し、float変換OverflowErrorをGateにする。これは非有限値を有限値へclip/補修する変更ではない。

## 保存結果監査への引継ぎ

[保存成果物監査計画](phase-origin-saved-artifact-audit-plan-20261020.md)の未確定事項のうち、estimated単精度字段とoracle残差保存時点は本v1で確定可能。schemaだけでは成功時の全必須集合を完全強制しないため、worker工程と照合する。parent-tool原文はowner内memberではなく別evidenceの全bytes/typed proofとして確認する。終端の具体的selector・claim一意性・実waitは実成果物到着まで未確定のまま維持する。

旧500・科学raw・PML・音声工程・Gitは変更していない。
