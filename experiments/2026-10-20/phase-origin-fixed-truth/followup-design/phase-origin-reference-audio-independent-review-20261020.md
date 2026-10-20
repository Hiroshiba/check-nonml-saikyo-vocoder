# 人工test入力・参考音声表示契約の独立レビュー

2026-10-20。対象 `phase-origin-reference-audio-presentation-contract-20261020.md` の紙上レビュー。原array読取、音声生成、候補実行、数値計算、tests、Git操作、既存レポートの変更は行っていない。

## 結論

**科学raw不変、固定5枠、共通gain、欠測非代替、科学失敗との分離は妥当。表示工程の開始前に、範囲検査の表現を統一し、演算・出力bytes再現性の保証範囲を明記することを推奨する。** 本レビューは音声生成・配布・公開を開始する指示ではない。

## 1. 要修正：丸め前と丸め後の検査

本文は「丸めた整数qを範囲検査してからint16へ変換」と定める一方、manifest項目には「丸め前後の範囲検査」とある。丸め前のscaled値へそのまま整数PCMの許容範囲を適用すると、丸め後には許容範囲に入る値まで拒否し得るため、成功集合が別契約になる。

最小修正文案：

> 原sample、gain適用後、32768倍後について有限性を確認する。丸め前にPCM整数値域を適用しない。ties-to-evenで丸めたqの有限性・整数性と−32768〜32767の範囲を確認し、その後だけint16へ変換する。

manifestも「各段の有限性検査、丸め後整数の範囲検査、cast前検査」に統一する。丸め前のmin/maxを診断として保存することと、それを別の拒否条件にすることは区別する。非有限値を整数へ変換してから検査する手順は禁止する。

## 2. binary64・ties-evenの再現性

契約の順序 `x/4 → ×32768 → ties-even整数丸め → 範囲検査 → int16` は明確であり、32767 scaleや飽和処理への置換は不可。次を実装仕様・manifestに明記すればより一意になる。

- 原binary64値を正しくdecodeし、各段をIEEE binary64のround-to-nearest ties-to-evenで評価する。float32や整数への途中変換をしない。
- 2段を積にまとめる最適化・演算順変更・隠れた拡張精度を許さない。2の冪の倍率でも、subnormal/overflow等を含む全入力で無条件に経路同一とは保証しない。
- subnormalの扱いを通常のgradual underflowとして固定するか、利用runtimeの挙動を明示する。FTZ/DAZ等の隠れた設定に依存したままbyte再現性を称さない。
- ties-evenの「整数丸め」は切捨てcast・half-away-from-zeroではない。範囲確認を完了するまではint16へ落とさない。

これは新しいgainや数値閾値の提案ではなく、指定済み変換の意味を固定する補足である。実際の5入力が範囲内か、どのsampleで量子化差が出るかは本レビューでは未確認。

## 3. 固定対象・欠測と科学状態

W/A/V/S/Jそれぞれpair_id=0のtestを一つずつ固定し、未作成でも5枠を残すことは事後選別を防ぐ。train、他pair、短縮片への代替、gainの個別変更を禁止する規則も整合する。

入力生成の完了と、noiseモデル適合・score計測の成功は別字段である。完全で同一性確認済みのrawがあり科学適合に別の失敗がある場合、その科学状態を明示したうえで参考入力を表示するかは表示契約の範囲として扱う。音声が作れたことを科学fit成功へ昇格させず、科学失敗を表示失敗の一語へ潰さない。

原規定rawの未生成・破損・ID不一致、非有限、量子化後範囲外はclip単位のpresentation_not_createdとし、成功WAV参照をnullにする。部分ファイルが生じた場合は完成品として公開せず、残存partialの扱いを記録する。完了WAVだけを原子的に公開する方式が契約と整合する。

## 4. 原本・manifestとWAV

原artifactのSHAに加え、archive member、dtype/endianness、shape、testを選ぶaxis/index、4096 sampleの順序を明示する。container hashだけで選択された音声内容を一意にしたと見なさない。sampling-rateも元studyの16 kHz規約に由来すると記録し、再推定値として表示しない。

gain・scale・演算順・丸め・非加工処理、変換source SHA/runtime、各5枠のstatus、成功WAVのbytes/SHAを残す案は適切。科学rawの変換前後hash不変を照合し、WAVを解析へ戻さない。

ただし、**PCM payloadが決定的であることと、WAVファイル全体がbyte再現可能であることは別**。同じPCMでもencoderが任意metadata、時刻、追加chunkを含めればファイルSHAは変わる。WAV全体のbyte再現性まで求めるなら、PCM format tag、RIFF/WAVE・fmt/data構成、追加chunkや時刻metadataの禁止、writer/versionを固定する。そこまで固定しないなら、manifestは「当該出力の同一性追跡」と「PCM内容の再現性」を区別し、全file bytesの再現保証とは呼ばない。

後段確認はheaderの16 kHz/mono/signed PCM16/little-endian、4096 frames、data長とファイル構造、manifestの実bytes/SHAを対象とし、音声の意味や科学結果の正しさまで認証しない。

## 5. 表示と停止線

「人工test入力の参考音声」、短い入力、共通1/4 gain、量子化済み表示という説明は適切。vocoder出力・BMA復号音・自然音声・品質改善例ではない。自動再生・loop、fade、repeat、dither等を追加しない方針も科学入力の参考表示として一貫する。

現base PMLと本来の品質比較への案内を保持し、人工truthラベルを聴覚的原因の同定として提示しない。今回の契約は今後の当該レポートだけに適用し、ユーザー指示ファイル・過去レポート・既存PCM規約を遡及変更しない。

範囲検査表現と再現性の保証範囲が固定され、別途明示された表示作業があるまでは生成へ進まない。本レビューは文書保存で完了する。
