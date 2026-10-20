# 初回 native 失敗の保存結果診断

## 結論
実測された初回 production 実行は exit 2、86.123181257 秒。baseline PML 3 枝は成功し、L/F 6 枝はすべて、解析から返った後の PMLParameters 構築時に停止した。合成・保存 payload の再読込には進んでいない。

## 保存配列で確認した事実
全 L/F の raw 正値は 50.78125 Hz 以上で、50 < F0 < 700 を満たす。raw の 0 は gate=0 および q_index=-1 と完全一致し、post では全て正値になる。厳密範囲違反の post 20 フレームは全て gate=1 にあり、700 Hz 以上は 0 件。

- librispeech_1089-134686-0008:
  - L: post 43.7784036381094–500.723677413371 Hz、≤50 Hz 6 件。0 始まり index: 294, 315, 496, 563, 985, 1155。raw zero/gate=0 は 47 件。
  - F: post 45.1769431662198–500.760855449525 Hz、≤50 Hz 2 件。0 始まり index: 474, 496。raw zero/gate=0 は 48 件。
- librispeech_1089-134686-0011:
  - L: post 24.2771100993262–506.594037835613 Hz、≤50 Hz 8 件。0 始まり index: 346, 746, 1029, 1047, 1056, 1057, 1067, 1077。raw zero/gate=0 は 75 件。
  - F: post 40.4331405549314–516.026333451623 Hz、≤50 Hz 1 件。0 始まり index: 346。raw zero/gate=0 は 75 件。
- librispeech_1089-134686-0032:
  - L: post 44.1992703152028–504.72580194647 Hz、≤50 Hz 2 件。0 始まり index: 158, 180。raw zero/gate=0 は 24 件。
  - F: post 44.0696979420017–504.536460799569 Hz、≤50 Hz 1 件。0 始まり index: 158。raw zero/gate=0 は 24 件。

L/F の raw/submitted/selector は同一で、raw→post の時刻列も全枝 bitwise 同一。resampled=false、フレーム数は 0008/0011 が各 1200、0032 が 818。exact-zero window は全記録 0、z_valid は全フレーム true。全 raw/post/refined の min/max・範囲外件数・完全な index mask・refined の zero index は JSON に記録した。

## source に基づく機構推定
byte 固定 source と実行 staging/保存 manifest の一致を確認した。pml_analysis.py:38–50 は raw の無声区間を補間し、65–700 Hz に clip した後、8 次 Butterworth と filtfilt による step removal を適用する。後段に再 clip はなく、最終チェックは finite・正値のみ。したがって平滑化の下振れが 50 Hz 以下の正値を残し得る構造と、保存 post および診断の outside-bounds 件数が整合する。filter replay はしておらず、未保存の clip 直後の配列を再構成していない。

native_adapter.py:49–50 が PMLParameters に渡すのは post F0 であり、StoneMask refined F0 ではない。parameters.py:49–50 の 50 Hz 超・700 Hz 未満チェックが、保存 traceback と一致して拒否した。refined の zero/範囲逸脱は記録したが、今回の直接の拒否対象ではない。

## 境界と停止状態
保存 ZIP と配列の読取・算術、source の静的読取のみ。元音声読取、candidate/vendor import、解析、再合成、filter replay、テスト、品質指標、clip/修復/調整、Cloud/Git/Library 操作は未実施。immutable delivery の SHA-256 は作業前後で同一。Quality phase B と残り 117 件への拡張は引き続き blocked。成功 native 用 auditor は使用していない。

詳細: pml-native-first-failure-diagnosis-20261021.json
