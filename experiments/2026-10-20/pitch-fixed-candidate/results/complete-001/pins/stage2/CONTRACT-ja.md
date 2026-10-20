# stage2 保存値集約 source（準備版・未実行）

正式取得した3文書のうち independent-review の最小契約を優先する。本packageは新sourceの独立レビュー用。stage1を起動せず、stage2の値集計も実行していない。AST/cached Ruffだけを確認した。

## 必須停止線と未確定入力

INPUT-MANIFEST.template.json は state=UNRESOLVED_TEMPLATE_DO_NOT_RUN。結果ZIP/pinsはまだ存在しないため、数値や成功receiptを捏造して埋めない。templateそのものを入口へ渡すとclaim作成前に拒否する。

将来、親が全結果を監査し、全必須path/bytes/SHA/owner外部manifest SHA/親wait字段selectorを埋めた別入力manifestを独立承認する。state=frozen_reviewed、adoption=all_owners_complete_onlyを必須とし、入口にその期待SHAを渡す。hash未確定、pin不一致、未知owner、partial/unknown ownerは開始不可。sourceの再レビューと別の一回開始指示も必要。未完owner救済・snapshot例外機能は今回実装しない。

未確定：3owner結果ZIPのbytes/SHA/ZIP内prefix、各EXTERNAL-MANIFESTのSHA、各external.py最終stdoutの原ファイルbytes/SHA、親の実wait記録bytes/SHAとexitcode/reaped/elapsed_secondsへの配列selectorとpost_fsync_observation=["external_post_fsync"]、両証拠のowner ZIP内完全member名、全consumer-local path、完成入力manifestの承認SHA、実行環境。親wait記録はexternal_post_fsyncオブジェクトを保存する実schemaに対応。残る終了字段selectorは入力manifestで固定する。選択字段の意味とstdoutへの結び付けは入力manifest独立レビューで確認する。

## 採用層

固定A/B ZIP、固定index ZIP、B1修正済stage1 source ZIPのSHAをcodeで固定。各ZIPの安全なmember名・重複・容量を確認し、read-onlyで読む。ZIPを元pathへ展開・書換えない。stage1数値sourceはhash照合のみでimportしない。

owner=id mod3。3owner全完了のみ採用。external/内部receiptのsuccess/exit0/reaped/termination_known/無signal、内部最終fsync観測、external.py最終stdoutのpost-fsync観測、親の実waitを確認する。各wall<900秒。外部manifest、内部manifest、source/index/input pins、counter不確定性補足receiptも照合。

journalの単一attempt・昇順owner・stage_start順序・A/Q/L×50/80の6値・point_done matched_noncertifiedを最終ledgerと照合する。累計counterと全4180台帳・他owner未試行も確認。worker PID/実mpmath由来確認/512MiB設定/正常owner終了の保存eventを確認。stage1 gateを再評価しない。未知event、欠測raw、矛盾は全体停止。rawの全診断・delta・counterはpin付きjournalの行範囲で復元できる。

## 算術とschema

mpmath1.3.0、87 sourceファイルのSHAと実import由来を確認。worker単体512MiB設定後に実importする。80 decimal digits固定、dependency既定の最近接丸めを使用。保存binary64はvalue/hex/bits照合後にas_integer_ratioからlift。保存A80/L80は元十進文字列を保持し80桁で読込む。後段結果は90有効桁の十進文字列で保存し、80桁で元結果へroundtripすることを確認。精度の正しさを保証するものではない。

S=保存logBF、L=L80、E=A80。L−S/E−L/E−Sを指定順で独立減算する。和への強制置換なし。Q80はraw証拠のみ。A/Q平均、逆方向の重複表、closure/envelope、通常確率表示、追加距離等は作らない。

staticは同condition/frame0のinitial_prior_payload、Aは当該prediction_prior、Bは当該保存log_prior。Bはlog値としてliftしexp→log往復しない。A/staticの正priorだけlog、zeroは支持外を表す内部Noneとし、負priorは事故。元prior表現はpin付きmember/line/fieldで復元する。

正支持のK昇順にx=b+sを作り、maxを引いてexpを逐次sum、G=max+log(sum)。G1−G2が固定二候補log odds、x−Gが各群10成分K log分布。全20セル完備を先に要求する。欠測を理由にKを除外・再正規化しない。現採用条件では不完全ownerそのものを拒否するが、number/schemaとしてmissingと支持zeroは別に定義する。

number.kindはfinite/positive_infinity/negative_infinity/missing/undefinedのみ。非finite JSONリテラル禁止。全zero群のKはundefined/zero_support_group、∞−∞はundefined/infinite_minus_infinite、両群zeroのpairはundefined/both_zero_support。missing評価のgroup-levelタグは全S/L/E・両群・全Kへ展開する。個別支持zeroのK log値はnegative_infinity。未知タグ、本来有限の入力異常、算術非finite、負priorは全体停止。既知支持分岐と混同しない。

## 最小出力

canonicalはunique-results.jsonl（4180行）とframe-results.jsonl（309行）。後者に三prior、支持mask/count、S/L/EのG/D/K log分布と三方向pair差をnested保存。主要point-summary.csvとpair-summary.csvはcanonical recordから転記し別計算しない。kind/decimal/reasonを保持。

共通出力はsummary.json、schema.json、pins.json、start/worker/final receiptとOUTPUT-MANIFEST。異常時だけworker-failure.jsonやpost-fsync-failure.jsonを追加。summaryはunique/owner/frame完備数、prior支持、数値tag数、標準三差のmin/max・正負zero件数・極値IDのみ。極値同値はcanonical順の先頭IDを記録。K log分布等の追加表は作らない。

pin付き元入力/index/owner rawへの参照を保存し、raw全体を繰返し複製しない。元ZIP/rawは削除・上書きしない。partial出力はそのまま保持し、行数・phase/location・例外tracebackを失敗receiptへ残す。normal completionと混同しない。

## 予算と一回性（提案・実行前再レビュー）

入口source/run.pyは別開始指示後の --authorized-stage2-once と承認済source/input manifest期待SHAを要求する。新output directory、同じinput manifestに対する共通claims-dirの排他的claim。失敗claimを消さずretryしない。跨ホストの一回性と環境割当は親が管理する。

全wall300秒をsupervisor入口直後から測定。科学deadlineは240秒（pin確認/読取/集約を含む）、末尾60秒を停止/reap/保存に予約する。数値worker1、RLIMIT_AS512MiB、子process生成なし。supervisor RSSは別。上限延長なし。240秒で残存workerをkillし250秒をreap目標とする。未reapは終了unknown・exitcode null・progressは観測下限・成功不可・再起動なし。

管理出力64MiB、通常出力の前に末尾4MiBとclaim4096bytesを予約。stream行ごとに容量確認・fsync。原入力は出力容量へ複製しない。事故・容量・期限で全体停止、partial/raw参照と例外位置を残す。精度変更、再試行、結果選別で続行しない。

成功にはworker exit0/reaped/無signal、4180/309出力、全owner採用、最終manifest/receipt fsync後に300秒以内、総出力64MiB以内、supervisor exit0と親の実process wait確認が必要。事前・途中receiptのcompleteだけでは成功採用しない。OS/ディスク障害で保存不能なら成功不成立。実動作のテストは今回行っていない。

## 範囲の限界

固定人工309frameの条件付き保存値診断のみ。独立標本CI/p値、F0正答率、全grid/VUV、品質、exact時系列再追跡、採用判断なし。80桁やstage1 gateから真値誤差boundを作らない。第1段をこのsourceから起動する経路は存在しない。

## version1：独立レビュー3点への限定修正

1. 構造化JSONのwriteは新規.partialへ書込み・fsyncしてからatomic renameで公開する。240秒kill等で中断した.partialは削除せず保持する。worker receipt読取側は欠落・partial/不正JSON・不正型・必要字段欠落を捕捉しworker_receipt_state=unknown、理由・traceback、complete=falseを最終receiptへ残す。progress snapshotと最終manifest保存へ進み、算術成功へ昇格させない。正常reapの有無とは別のreceipt信頼状態として扱う。
2. journal control eventはworker_started→dependency_verified→worker_finishedのみ。point eventはpoint_start/stage_start/quadrature_progress/value/point_doneのみ。未知event、null/不正unique_id、owner不一致、control前後のpoint、stage/valueの順序違反、求積stage外progress、拡張番号の順序違反、6値未完でのpoint_doneを停止理由とする。数理gateの再計算はしない。
3. A/static prior pointerのfieldはvalues.prediction_prior / values.initial_prior_payload。Bのlog_prior直下、Sのvalues.logBFは変更しない。

数式・三差・三prior・支持規則・資源上限・claim前の未確定入力拒否に変更なし。原raw/partialを上書き補修しない。candidate import/実行、実集計、tests/smoke/fixtureなし。ASTとcached Ruffのみ。


## version2：実outer-end証拠との照合

parent_wait_selectors.stdout_sha256の要求を廃止し、post_fsync_observation=["external_post_fsync"]へ置換。外側原recordへ架空hashを後付けしない。別pinのexternal.stdoutをUTF-8厳格JSONちょうど1行として読み、親の保存オブジェクトと型を保ったcanonical JSON文字列の一致を要求する。Python dict ==は使用しない。canonicalはkey sort・空白なし・ensure_ascii=false・allow_nan=false。重複keyと非標準NaN/Infinityは拒否。bool/int/floatは異なるJSON tokenとして区別する。

external_stdoutとparent_waitにowner ZIP内の完全member名を必須化。prefix相対ではない。原fileのbytes/SHAを確認した同じbytesをZIP memberの原bytesと完全照合する。stdoutのtype/success/elapsed<900、parentのexitcode/reaped/elapsed<900検査は維持。証拠file・ZIP・outer-endの変更や後付けは禁止。

今回はsource/template/schema/契約だけの最小修正。実ownerデータを取得・集計せず、候補import/実行/tests/smokeなし。算術・支持・予算・未確定入力のclaim前拒否は不変。
