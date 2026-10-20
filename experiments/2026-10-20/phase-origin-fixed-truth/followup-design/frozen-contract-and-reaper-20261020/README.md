# 位相原点校正v2の固定契約とREAPER調査（2026-10-20）

source v2は静的レビューを通過し、500組を167・167・166組に分けた3ownerへ、それぞれ一回の開始指示を送りました。実計測の進捗・成功はまだ未確認で、結果はありません。ここで保存するのは契約・監査と並行調査の記録です。PMLを維持します。

準備版CONTRACTの「別開始待ち」と12:27 UTCの親判断は、その時点の原文として保持しています。v0・v1の未通過記録も残し、後のv2受入れ・開始指示と区別します。静的レビューの通過から完走や数値精度の保証を主張しません。

## 固定契約と版の識別記録

- [準備版CONTRACT](phase-contract/CONTRACT.md)、[保存形式](phase-contract/SCHEMA.json)、[容量予算](phase-contract/BYTE-BUDGET.json)。
- [ソースmanifest](phase-contract/SOURCE-MANIFEST.json)と[入力manifest](phase-contract/INPUT-MANIFEST.json)：候補コードや入力の識別・hash記録です。参照先の候補コードをGitへ保存したものではありません。
- [v2への修正対応](phase-contract/V2-REVIEW-RESPONSE.md)。

## 未通過のv1と通過したv2を分けて読む

- v1の監査：[実行境界](phase-review/phase-origin-source-execution-review-v1-20261020.md)、[入力](phase-review/phase-origin-source-input-review-v1-20261020.md)、[数理](phase-review/phase-origin-source-math-review-v1-20261020.md)。
- v2の限定再監査：[実行境界](phase-review/phase-origin-source-execution-review-v2-20261020.md)、[入力](phase-review/phase-origin-source-input-review-v2-20261020.md)。[12:27 UTCの親判断](phase-review/phase-origin-source-v2-parent-decision-20261020.md)も当時の記録です。
- [後段集計の採用契約](phase-review/phase-origin-summary-acceptance-contract-20261020.md)：保存証拠の監査後に、別のソース・レビュー・指示を要する工程です。この保存作業で集計は実行していません。

原文レビューの監査計画リンクには、[既存計画への案内](phase-review/phase-origin-saved-artifact-audit-plan-20261020.md)を付けています。

## REAPERの戻り値とPMLの保存範囲

- [epoch観測と保存来歴](reaper/reaper-epoch-observation-provenance-20261020.md)、[独立事実確認](reaper/reaper-epoch-observation-independent-review-20261020.md)、[公開保存物の限定棚卸し](reaper/pml-epoch-saved-artifact-inventory-20261020.md)。

既存戻り値の来歴と保存範囲の読取記録です。[既存のPML位相契約監査](../../../oracle-covariance/followup-design/calibration-and-base-contract/pml-phase-contract-audit-20261020.md)へ関連づけます。PML変更や自然音声の再解析は行っていません。保存参照が見つからなかった範囲を、全環境での不存在証明に広げません。

Library `libfile_14db2936277c819194b47abcd7766504` v0の16文書・JSONとMANIFESTを、ZIP内の構造と原bytesのまま保存しています。
