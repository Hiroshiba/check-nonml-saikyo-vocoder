# run-001 回収・分割実行・merge 契約（実装準備のみ）

2026-10-20。実結果ZIPの正式Library取得、SHA照合、JSON schema/保存値読取を行った。候補コード・recovery adapterの実行/import、再求積、tests/smokeは行っていない。

## 変更しない回収元

- Library `libfile_b820743f5a648191980befe78f3ea7e2` version 0。
- ZIP 514502 bytes、SHA256 `f06e7bd1f1ae7a2f2e4e8e22aeb66dcc1fd76928c78c45a27406ed297d41e3d8`。
- `run-001/results.json` SHA256 `7b819eb2308e1310c636c5ce6f76f3313f25814653d058bc7417978aa2140e3d`。
- 旧source manifest SHA256 `1b54832860d9744576e071d36cc70256291c145571bc3f372b1cbeefa17e0cec`。
- 入力index SHA256 `79c47c6b1926359d636d63eca6b6bab161e2b2d5f28015bc16d5209a100350d2`。
- 旧契約SHA256 `8c7b21a29f0d8a711db0af280c0af3f99b1bcd6ec1f6e95881139fdff5c7f9fb`。

元ZIPをread-onlyで開く。旧manifest/契約の原bytesをソースに同梱し、旧resultsのembedded manifest/入力SHA/モデル集合/PML/PR67/単位/実数ライブラリ版を照合する。W/A/S/Jを担うcore.py・quadrature_1d.py、入力読込・依存指定は旧sourceのbytes/SHAと同一を要求する。現在の入力indexと全1908ファイルの検証は従来どおり行う。

## 読み取った実schemaと成功392件

resultsの`pairs`はround-robinの500要素。各行に`id,truth,old_score_status,old_plugin_scores,train,joint`、試行済み行には`statistics`がある。各積分entryは`status,log_i,levels,alternate,omitted_ratio,diagnostics`。

成功392件は非V390件とV2件。V2件はA-001/train/V、W-004/train/V。親から受領した独立レビューにより、同じ科学モデル・入力・priorの積分として旧gateのまま再利用可。旧meshは保存されておらず、新small分類を実施・新gateで再評価済みとはしない。成功entryの値・levels・診断・評価点数・時刻情報を変更せずIntegralへ転記し、provenanceはentry外のslot_provenanceへ付ける。

`converged`だけでは再利用しない。型、有限性、3levels、別則差、omitted、評価点数・時間、モデル別必須diagnostics、train/joint寸法、proprietyを旧gateで検査する。旧Vは旧Cartesian24/48と旧active risk/omittedの保存値を検査し、新分類・64/96を適用しない。392件または2件のV IDが一致しなければ回収全体を停止する。schema不正や成功entry不整合を黙って再計算へ置換しない。

新出力の`recovery/run-001-results.json`に元results JSON bytesをそのまま保存する。各slotに旧results SHAとJSON pointer、旧source SHA、新出力source SHA、入力SHA、originを付ける。旧失敗は原JSONとpointerに残し、新しい成功で遡及的に書換えない。元旧2500scoreを先に全件原値保存し、現在のindexのmerged scoreと一致を確認する。新workerは成功slotをskipし、失敗・未試行だけ求積する。成功値の代替、旧scoreの再fit、残差再生成なし。

## 停止理由・実時刻

外部execution記録の開始は2026-10-20T05:42:37.128986+00:00、終了は05:56:20.596984+00:00。worker開始は05:42:37.235495+00:00。親の明示的早期停止要求は05:56:05.221180+00:00、SIGUSR1送信は05:56:05.221569+00:00。27分上限未到達である。

旧runのtime_budget_exhausted等は当時の共通停止ラベルとして原文保持し、外部early-stop記録を併記する。新runはstop-request.jsonのcategory、reason、requested_utcとsignal受信observed_utcを記録する。親の明示停止はparent_explicit_early_stop、監督の27分停止はtime_budget_exhausted、根拠ファイルなしのSIGUSR1はexternal_stop_signal。外部signalを勝手に親判断や時間上限と断定しない。旧記録は訂正上書きしない。

## 最大3分割の明示範囲

実行入口は`--recovery-zip`と`--pair-id-start/--pair-id-end`を必須にする。認める範囲は全件0–99、または0–32・33–65・66–99の3候補だけ。各pair_idのW/A/V/S/Jを常に同じ担当へ置く。worker1・各実行30分/1GiB等の制限は維持する。並列計測はまだ開始しない。

すべての出力が全500組・旧2500score・同じ固定母集団を保持し、旧392成功は各出力で同じ不変回収元から引き継ぐ。担当外の残りslotはoutside_shard。担当内の時間切れ/親停止/数値未達とは別状態にする。shardの全5000slotを保持するが、派生値・比較・bootstrapは未統合としてunionに留保する（元runの派生値は原results JSON内に保存）。新slotのorigin/source SHA/attempted/開始終了UTC/結果状態を保存する。

## 機械的mergeの契約（文章のみ、未実装）

1. 全入力成果物のZIP/results/source SHAとreceiptを明示indexで固定する。3分割は互いに非重複かつ0–99を被覆し、同じ新source manifest、科学契約、入力index、旧回収元SHAであることを要求する。
2. mergeキーは(pair id,train|joint,model)。全5000slotを一意に列挙する。旧392は旧source/旧results pointerとentry値・診断が完全一致するコピーだけ重複排除する。旧成功をnew originで再計算したslotはエラー。
3. 残り4608slotの新計算は所属範囲の出力だけから採用する。範囲外のnew slot、新slotの二重所有、同値でも重複したnew slot、異source/入力、旧score不一致を拒否する。片方を任意選択しない。
4. 欠けた担当、未試行、時間/親停止、数値未達は別々に保存し、全件成功へ繰上げない。missing slot一覧と理由を出し、部分成果物としてのみ成立させる。outside_shard自体は失敗測定ではなく、そのowner出力を探すための状態。
5. 全500組の旧scoreと母集団を維持し、各pairの10積分が成功した場合だけ同じ数式でBMAを派生する。候補だけの再正規化は禁止。原出力を変更せず、mergeは新出力へ保存する。
6. 3つの条件付き平均/CIを平均しない。merge後の固定pair順で25 paired比較・指定PCG64 bootstrapを一度だけ再集計する。欠測があれば元100組の平均/CIはnull、成功subsetは別欄。
7. merge manifestは全採用slotの親成果物SHA/pointer・旧/新sourceを記録する。検査不一致は停止理由とともに保存する。merge実装・実行は今回の範囲外。

## 次版の資源枠・unionの分離

3 shardの新規slotは1258/1650/1700、合計4608。各1 worker・元と同じ30分外部上限/worker RLIMIT_AS1GiB/管理出力128MiB/log8MiB。最大同時3計測worker、合計90 worker-minutes、shard出力合計384MiB。監督RSSは別枠で、全プロセス3GiB hard capではない。

unionは計測再実行なしの集計専用、最大5分、管理出力128MiB。各shardは未統合slot記録だけを出し、最終bootstrapを重複実施しない。unionで全5000slotから派生値と25比較bootstrapを一度だけ算出する。unionの機械的merge/集計コードは未実装であり、実行可能と称さない。計測開始はレビュー後の別指示まで待つ。
