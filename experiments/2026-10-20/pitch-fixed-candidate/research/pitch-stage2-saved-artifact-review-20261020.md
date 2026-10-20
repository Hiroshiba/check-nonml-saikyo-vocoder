# Stage2 保存値・出典整合の独立監査

## 判定

保存artifact側は採用可能。4180 unique、309 frame、927 frame/prior行について出典・保存値・支持タグ・canonical/CSV・既存summary整合に不整合を認めなかった。外側process終了・時間・容量・manifest全体の採用判定は別担当の確認を条件とする。

対象 `/workspace/shared/pitch-stage2-results-review-20261020/package/output` と承認index、原selected/B入力、全stage1 journal/ledger。候補実行/import/tests、BF/exp/log/LSEの再計算はしていない。原文字列/bit/hash比較、Decimalの保存値差、既存summaryの件数・極値整合だけを監査した。

## 1. 4180 uniqueの出典

- unique_id/K/r_bits/owner/reference_idsは承認indexと一致。S_bitsは原selected.jsonlのvalues.logBF bitsと一致。
- S_input pointerは元member SHA、正しい行、values.logBFを指す。
- L80_raw/A80_rawは、各ownerの元journalに保存された80桁L/A文字列と全4180件で完全一致。
- stage1_rawのstart/end行は同一uniqueのpoint_startからpoint_doneを指し、member SHAが元journalと一致。ledger pointerのindexとmember SHAも一致。
- 全pointerのarchive SHAは承認済stage2 input manifestのsaved_input/index/owner archiveと一致。rawに戻る経路は保持される。
- Sは保存binary64からDecimalへ正確に読み、L−S/E−L/E−Sを保存値差として照合した。元BFを再評価していない。

## 2. 309 frame × 三prior

全frameでmetadata、time bits、observation hash、reference IDs、frame index pointerを承認indexと照合。全20セル（48/148×K1..10）がmatched_noncertified、full20_complete=true、missing_keys空。

三priorの全pointerは元行・member SHA・fieldと一致する。staticは同condition/frame0、initial_prior_applied=true、values.initial_prior_payload。Aは当該values.prediction_prior。Bは当該直下log_priorであり、全保存B finiteのまま使用する。

元priorの保存zero/正値からsupport maskとcountを照合し、Bはfinite log支持として扱った。priorのlogやexpを計算していない。

- static/B: 全309 frame両側正支持。各S/L/EのDはfinite309。
- A: 両側正支持104、片側zero205。各S/L/EのDはfinite104、positive_infinity141、negative_infinity64。
- A片側zero205件の方式差は全三方向undefined/infinite_minus_infinite。差0またはmissingへの置換なし。
- 全zero群のK分布はundefined/zero_support_groupの全K展開タグ。正支持群はK1..10の10成分を保持し、個別zero priorはnegative_infinity/prior_support_zero。finite支持成分は有限のlog値。通常確率への変換/和の再検証はしていない。

保存G1−G2とD、保存Dの標準三方向差をDecimalで照合した。G自体のLSE値やK分布の正規化を再計算して認証したものではない。

## 3. canonical / CSV / summary

point-summary.csvの4180行、pair-summary.csvの927行はcanonicalのkind/decimal/reasonとID/支持件数を逐項転記したものとして完全一致。nullを空欄へ投影する仕様も一致し、空欄を数値0と解釈していない。

既存summaryの全countsとranges（元十進文字列・min/max ID・先頭同値選択）をcanonicalから照合し、完全一致。unique4180を6180参照で重み付けした集計ではない。pairはprior毎のframe分母309であり、三prior合計927を独立標本数とは扱わない。欠けたCounterキーは0件である。

保存差の照合における最大差異は1.079521074e-78。80桁算術後の90桁文字列を別のDecimal差で比較した際の記録丸め差である。照合許容1e-74は保存整合用であり、真値誤差boundや新科学gateではない。rawの文字列一致と別の確認項目である。

## 4. 既存summaryの確認済み記述

新しいodds/LSE集計を作らず、既存summaryの保存値を確認した。

- unique L−S: min約−3.3916e-13（ID1643）、max約3.0737e-13（ID2066）。正2042、負2138、zero0。
- unique E−L: 全4180正、約0.00800235..0.12211707 nats。E−Sも全4180正。
- pair E−L: finiteな全recordで負。static309、A104、B309。Aの残205はundefinedであって0ではない。
- pair E−Lの既存範囲はstatic約−0.0154031..−0.0104709、A約−0.0149226..−0.0104709、B約−0.0150503..−0.0104709 nats。
- unique E−Lが正でもpair E−Lが負となることに矛盾はない。pairは異なる二周波数群のlog evidence差であり、セルの共通符号だけで差の変化方向は決まらない。

D自体の符号反転数はsummaryに未実装であり、本監査でも新たに計算していない。「未集計・未報告」であり0件とはしない。

## 留保

80桁算術、stage1 matched_noncertified、今回の保存値整合のいずれも真誤差認証ではない。今回の対象は固定人工309frameの条件付き比較であり、独立標本CI/p値、全grid MAP/VUV、自然音声品質、exact時系列再追跡、モデル採用の根拠ではない。

機械可読監査: `/workspace/shared/pitch-stage2-saved-artifact-audit-20261020.json`。不整合リストは空。
