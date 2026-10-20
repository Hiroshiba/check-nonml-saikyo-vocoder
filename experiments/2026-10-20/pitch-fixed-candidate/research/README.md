# 研究・監査文書の読み方（2026-10-20）

23文書とMANIFEST.jsonをLibrary `libfile_330726d089c48191ac19fcb65b2d141f` v1から変更せず保存しています。未開始・起動不可などの記述は各文書の執筆時点の状態です。初期の指摘を削除せず、修正版のレビューと実行後の監査を分けて読むための記録です。

初期のstage1実行境界レビューのB1はv1で解消と報告されています。stage2実行境界は初版のB1/B2、v1の修正確認、v2の外部終了証拠との連携確認の順です。保存値算術のprior参照先の指摘はv1で修正確認され、入力manifestは未確定のv0と最終確認のv1を区別します。報告HTMLの初期監査に残った文面修正は、v2の最終限定差分レビューで解消と記録されています。これらの静的レビュー単独を、実行成功や品質改善の証明として扱いません。

## 実行前の契約と段階別レビュー

- [固定候補BF stage1 adapter：実行境界・保存契約の静的レビュー](pitch-fixed-candidate-execution-review-20261020.md)
- [固定候補BF stage1 adapter v1：B1差分再レビュー](pitch-fixed-candidate-execution-review-v1-20261020.md)
- [固定候補 stage2：保存値集約の出力契約案](pitch-fixed-candidate-stage2-output-contract-20261020.md)
- [固定二候補log oddsとK正規化の安定性：紙上設計メモ](pitch-fixed-candidate-odds-stability-20261020.md)
- [固定候補stage2：出力契約と安定性メモの横断レビュー](pitch-fixed-candidate-stage2-independent-review-20261020.md)
- [固定候補stage2 source v0：実行境界・owner採用の静的レビュー](pitch-stage2-execution-review-20261020.md)
- [固定候補stage2 source v1：実行境界の差分再レビュー](pitch-stage2-execution-review-v1-20261020.md)
- [固定候補stage2 v2：実outer証拠連携の最終静的レビュー](pitch-stage2-execution-review-v2-20261020.md)
- [Stage2 source v0 保存値算術の静的独立レビュー](pitch-stage2-saved-arithmetic-review-20261020.md)
- [Stage2 source v1 限定再レビュー](pitch-stage2-saved-arithmetic-review-v1-20261020.md)
- [stage2 入力 manifest v0 原本照合](pitch-stage2-input-manifest-v0-independent-review-20261020.md)
- [stage2 入力 manifest v1 最終静的レビュー](pitch-stage2-input-manifest-v1-independent-review-20261020.md)

## 保存成果物・報告の監査

- [固定候補BF stage1：3 owner実行・保存証拠の独立監査](pitch-fixed-bf-results-execution-review-20261020.md)
- [固定候補BF stage1：全3 ownerの保存数値artifact独立監査](pitch-fixed-bf-stage1-numerical-artifact-review-20261020.md)
- [固定候補stage2実行成果物：実行・保存証拠監査](pitch-stage2-results-execution-review-20261020.md)
- [Stage2 保存値・出典整合の独立監査](pitch-stage2-saved-artifact-review-20261020.md)
- [Stage2 符号遷移sidecar独立監査](pitch-stage2-sign-artifact-review-20261020.md)
- [固定二候補BF 日本語HTML報告：独立静的監査](pitch-fixed-bf-report-static-review-20261020.md)
- [固定二候補BF報告v2：最終限定差分レビュー](pitch-fixed-bf-report-static-review-v2-20261020.md)

## 紙上検討と次の限定対比計画

- [log-g Laplace 全域符号：変数変換の障害と残課題](pitch-logg-laplace-global-sufficient-condition-note-20261020.md)
- [全域符号の十分条件メモ：独立レビュー](pitch-logg-laplace-global-sufficient-condition-independent-review-20261020.md)
- [同一保存観測の条件間対比：次の最小保存値診断計画](pitch-matched-observation-history-contrast-plan-20261020.md)
- [同一観測・旧履歴対比計画：独立批判レビューと最小凍結契約案](pitch-matched-observation-history-contrast-independent-review-20261020.md)

次の対比計画は準備対象です。計画文書を実行結果として扱いません。
