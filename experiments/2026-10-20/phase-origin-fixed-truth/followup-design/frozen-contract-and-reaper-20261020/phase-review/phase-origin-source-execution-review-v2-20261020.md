# Phase source v2：実行契約の限定差分レビュー

## 結論
**静的 PASS。v1既報3点は解消、新規blockingは認めない。** これは実行許可・完走保証・数理認証ではない。独立数理レビューと、親による環境/唯一owner/claims確認・別開始指示が引き続き必要。今回候補import/実行、PRNG初期化、tests/smokeは一切行っていない。

## 対象と照合
対象 `phase-origin-source-review-v2-20261020/package`。V2-REVIEW-RESPONSE、CONTRACT、SCHEMA、BYTE-BUDGETとv1との差分を読取した。

- SOURCE-MANIFEST SHA `ad683e29f1d2ac1bc7200bfa6308e3875e20a45558f6b6947ef728d27d419842`。
- INPUT SHA `b60194d8460f6499dfd7fc9549707b688587ef35c835074837232c0f06b523e4`、v1不変。
- 全52manifest entries＋自身の集合/bytes/SHA一致。source14本をAST読取。
- source差分は diagnostics/lifecycle/processes/supervise の4本だけ。他10本、model/calibration/workerを含む科学kernelはv1とbyte identical。

## 既報阻害の解消
### 1. owner-ledgerのroot JSON混入
広いglobを廃止。pinしたINPUTとplanned-ledger全行一致を検査し、owner所属行から正確なpair-XXX.jsonだけを読む。INPUTのownersは[167,167,166]で実装の参照方法に一致し、rowの5字段も元pair.rowと一致する。

全owner予定行を出力し、欠落をmissing/start_unconfirmed、読取/構造異常をinvalid/unknown、started/inflightをincompleteとして保持。root JSONをpair metadataとして読む経路はない。ledger_completeと診断完全性がsupervisor completedの追加条件となり、欠測を成功へ昇格しない。rawや全descriptorの科学採用監査は後段の独立確認を要するという範囲も維持。

### 2. 未起動失敗の証拠保存
通常packing gateは変更せず、CONTRACTに親の別指示による失敗証拠保全を追加した。元tool、claim、存在するlog/receipt/partial、時刻付きfile一覧・bytes/hashを対象とし、receipt再構成・数値補完・科学再実行を禁止する。

未起動は積極的証拠、終了確認済みは実wait/reapで認定し、それ以外はunknown。mutableかもしれないfileコピーはsnapshotと明示し、ZIP自体のhashが固定できても原runの不変/終了/科学完全性を認定しない。新しい一般化packerを無承認で実装しない。これで通常gateに入れない失敗も、科学採用とは別の明示工程で保持する契約が成立している。

この親側保全は自動実行済みの機能ではない。実際に失敗した場合は親が明示指示し、正式転送経路/容量/原証拠を確認して行う必要がある。

### 3. 非例外異常の呼出stack
signal送信、overflow、非0終了、reap期限、cleanup kill、台帳欠落/不完全にcall stackを追加。検出時にはfile/line/functionのスカラーを最大128frameで凍結し、linecache・整形・file I/Oを行わない。監視側のemitはkill/実wait cleanup後なので、ログ書込失敗が停止処理に先行しない。

128frame超、byte超、整形/書込失敗は不完全flag/counterを保存。例外tracebackと同じ131072bytes/process枠を共有し、raw streamのseen/retainedも残す。faulthandler追加は取得可能なPython stackの補助であり、SIGKILLや全native stackの保証ではない。原出力は親capture capの対象とし、完全保存を偽称しない。

## 新規終了経路の確認
監視中stack取得で例外が出ても外側try/finally cleanupに入り、cleanup内の取得失敗も既存の例外/fallback経路でunknown扱いになる。出力整形はcleanup後。台帳診断のemitはworker runのcleanup完了後であり、容量不足や破損台帳を成功にしない。

同時に、v1のhandshake、親死亡SIGKILL、subreaper、durable identity/ack、非最適化pins、path分離、claim上限、typed packing、summary入口隔離はbyte不変で維持される。838/840/845、865/870/880、supervisor860・outer890・親900の時計や512MiB worker制限も変更なし。

## 保存上限・移送
BYTE-BUDGETの数値枠は不変。167pair×375920＋固定1048576＋終端2097152＋通常partial16384＝65,940,752bytes。64MiBとの差1,168,112bytes。固定caps/終端capsの合計も独立整数算術で一致する。

owner-ledgerは既存131072cap、追加stackは既存stderr cap内。新規無制限ファイルやraw複写は追加されていない。親tool原文と失敗snapshotの保全は別の明示されたevidence/delivery予算であり、科学64MiBの枠内に入ったと主張しない。

Libraryの実上限、staging disk、全part取得/復元hash確認は保存工程時の確認事項として残る。移送失敗で科学再実行せず、immutable原bytesの保存工程だけを扱う。

## 開始時・実測後の条件
親がsource/input期待SHA、環境依存、study未使用、全ホスト唯一ownerとclaims、親の実tool wait原文保存方法を固定すること。実測後は両childとouterの実exit/reap、最後のfsync後時計、全台帳/partial/raw/manifestを独立監査すること。静的通過から時間/RAM内完走、全500科学成功、noncertified gateの認証を推定しない。別の開始許可が出るまで科学実行は不可。
