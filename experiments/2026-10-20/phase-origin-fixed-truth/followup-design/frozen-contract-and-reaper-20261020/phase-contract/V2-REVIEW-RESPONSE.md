# v1再レビューへの最小差分（v2 draft）

1. superviseのpair-*.json globを廃止。pin済INPUTと全planned台帳を突合し、自ownerの正確なpair-XXX.jsonだけを列挙。欠落・破損/必須field欠落・started/inflightを明示し、metadata不完全をcompletedへ昇格しない。root recordは読まない。
2. 例外をraiseしない異常signal/overflow/reap期限/child exit/cleanup/台帳不完全にもfrozen call stack。取得はfile/line/functionのメモリsnapshotだけ、監視側の出力はkill/実wait後。131072bytes/logと不完全flagを維持する。DEVELOPMENT:25に従いCLI faulthandlerで取得可能なPython stackも原stderrへ。
3. 通常packing gateは変更なし。未起動/終了確認済み/終了不明に分けた親の失敗証拠保全をCONTRACTへ追加。元tool/claim/log/receipt/partial/時刻付きfile一覧の科学採用不可artifact。mutable写しはsnapshotでありimmutable run完了/全値保存成功とはしない。新一般化packerは実装しない。

数理kernel、seed、閾値、truth/計測対象、計測予算は不変。科学/import/PRNG初期化/tests/smoke/Gitは行わない。AST/cached Ruff/hashのみ。親からv1最終監査完了を受領し、3点を反映してv2をsource準備版として固定する。科学の別開始指示は未受領であり、実行不可。
