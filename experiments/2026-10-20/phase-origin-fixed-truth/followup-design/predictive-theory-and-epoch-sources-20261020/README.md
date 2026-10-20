# 位相予測理論・epoch参照資料の文書bundle

2026-10-20。Hiroshiba/check-nonml-saikyo-vocoder の参照用文書10点を、原文のbytesを変更せず収録した。コード、音声、コーパス実体、実500の原成果物は含まない。

## 資料の区別

- 理想Wの理論：predictive-integralの本稿・独立レビュー、equivariance-riskの本稿・独立レビュー、primary-precedents。proper円周priorによる共有位相のfull-circle posterior predictiveと、理想global OLSに対する固定φの反復期待riskを扱う。追加の対称性証明は理想Wだけに適用する。各train条件付き・各test実現の優越、有限精度・数値gate・成功subsetへの保証ではない。
- コーパス調査：epoch-reference-corpusの本稿・独立レビュー。MOCHA-TIMIT、CMU ARCTIC、Keeleの公開一次資料を限定確認した記録であり、データ実体の取得・検品・採用・校正は未実施。EGG由来イベントを完全な生理的GCI真値や校正済みVUV確率と同一視しない。
- 実行失敗分析：proc-children-failure-analysis、child-wait-portability-design、failed-snapshot-acceptance-boundary。原因候補、将来の監視設計、既存失敗snapshotの報告・採用停止線を区別する。将来案は過去runの成功認定や再実行の許可ではない。

## 実500の現在の停止線

最新追記では全3 workerの実wait0・全500行complete・各hostの保存値/raw/hash読取監査の不一致0が報告されている。ただしouter/supervisorはexit2、過去の全子終了はunknown、immutable=falseで通常packingは拒否された。Library転送のHTTP403により親への完全転送・原本独立監査は未完了であり、正式集計不可。host別暫定集計も実施しない。過去の状態を残した本文は、各文書の追記・留保と合わせて読む。

理論を実500の結果、音質優越、W以外のtruthへ拡張しない。現在の二score契約を変更せず、第三score、再計算、追加実験、採用をこのbundleで承認しない。

## 同一性

MANIFEST.jsonは原文10点と本READMEのbytes・SHA-256を記載する。自己参照を避けるためMANIFEST.json自身は一覧の対象外。元文書は無修正であり、時点の違いを解消するための書換えも行っていない。
