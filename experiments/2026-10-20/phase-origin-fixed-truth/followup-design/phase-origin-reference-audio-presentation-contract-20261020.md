# phase-origin 人工入力の参考音声表示契約

2026-10-20。新studyの将来の表示工程だけに適用する案。既存レポートは変更しない。ユーザーの音声に関する質問と「なるほど、再開」を、新しい恒久指示や今回の音声生成許可に読み替えない。本書作成では音声生成・array読取計算・候補コード実行・Git操作を行わない。

## 対象と位置づけ
- 既に計画で固定したtruth W/A/V/S/Jの各pair_id=0、test入力を1本ずつ、計5本だけ対象とする。train行や他pairへ置き換えない。
- 各入力は科学原本のfloat64、4096 samples、16 kHz相当の0.256秒。元入力のdtype/shape・train/testの行規約と生成完了状態を後段の表示工程で確認し、不一致なら表示未作成とする。
- 見出しは「人工test入力の参考音声」。vocoder出力・BMA復号音・自然音声・品質改善例ではない。truthラベルは人工生成条件であり、聴覚的原因の診断ではない。
- レポート冒頭では現base PMLと自然120録音・標準8方式の本来の比較への案内を維持する。人工5本を品質順位・採用判断・自然音声に対する優越の根拠にしない。

## 決定的な変換仕様
全5本に共通の固定gain **1/4**。出力は16 kHz・mono・signed PCM16・little-endian WAV、4096 samples。リサンプリング・補間・長さ変更なし。

float→整数のスケール係数を曖昧にしないため、次の写像を契約に固定する：

`q = round_to_nearest_ties_to_even((x / 4) * 32768)`

xは原float64 test sample。元のendiannessでbinary64を正しくdecodeし、処理順はx/4、その結果の32768倍とする。各段はIEEE binary64のround-to-nearest ties-to-even、subnormalはgradual underflowで評価する。float32への途中変換、2段の積への統合、演算順変更、隠れた拡張精度、FTZ/DAZは許さない。元sample・gain適用後・32768倍後の各段で有限性を確認する。丸め前にはPCM整数値域を適用しない。ties-to-even整数丸め後のqについて有限性・整数性・−32768〜32767の範囲を確認し、合格後だけint16へ変換する。切捨てcastやhalf-away-from-zero丸めへ置換しない。丸め前min/maxを診断として保存しても、別の拒否条件にはしない。32767倍など別規約への変更は別版契約とし、clipごとに混在させない。PCM16の値域は−32768〜32767で非対称なので、正側限界を飽和させて救済しない。

clip別/全体peak正規化、聴取後の選別、fade、repeat、denoise、DC除去、dither、clip/saturateを行わない。自動再生やループ指定をせず、短さと共通gainを説明する。端点クリックや小音量も加工で隠さない。PCM16量子化は不可逆であり、原float64のlosslessコピーとは呼ばない。

WAV全体の再現性も仕様として固定する：RIFF/WAVE形式、little-endianのRIFF size、続く16-byte fmt chunk（format tag=1、1 channel、16000 Hz、byte rate=32000、block align=2、16 bits）、続くdata chunkだけとする。dataは元sample順の4096個のsigned int16、8192 bytes。RIFF size=8228、ファイル全体=8236 bytes。追加chunk・任意metadata・時刻・末尾余剰bytesは禁止。writer/source versionをmanifestへ記録する。この構造と上記演算仕様に基づく再現性の設計であり、今回実出力のbyte再現性を実証したとは主張しない。

## 未作成・欠測の扱い
- 原規定pair/test未生成、input参照・dtype/shape不一致、非有限sampleまたは変換中の非有限、丸め後qのint16範囲外を検出したclipは、ファイルを成功出力せず `presentation_not_created` と具体理由を残す。
- 範囲検査はint16 cast前に行い、overflow/wrapを避ける。違反sampleだけ削除して短縮することも禁止。
- 他pairへの差替え、gain低下、部分だけ音声化、後から都合のよい例へ選別はしない。他4本が有効なら固定ラベルのまま表示できるが、5本全枠と未作成理由を残す。
- この表示上の未作成は科学測定の失敗・未収束と別状態。科学側に問題があればその状態も別記し、音声化成功を科学計測成功の証明にしない。

## 原本保護・来歴
科学raw float64・score・ID・生成条件は読取専用で不変。WAVは別の表示用directory/artifactに作り、解析・推論・score・モデル選択へ再投入しない。

manifestは各5枠について次を保持する：
- study/input契約の識別子、truth、pair_id=0、split=test、testを選ぶaxis/indexと4096 sampleの順序。
- 原artifact/archiveのSHA256・bytes、pathと該当member名、配列dtype（endianness含む）・shape、sample数とsampling-rateの根拠。container SHAと選択sampleの識別を区別する。
- gain=1/4、float演算順、32768 scale、ties-to-even、各段の有限性・binary64丸め/gradual underflow規約、丸め後整数の範囲検査・合格後のcast、上記の非実施処理、変換実装version/SHAとruntime。
- status/reason。成功ならWAV相対path・bytes・SHA256、PCM format/bit depth/channel/sample rate/sample count、PCM payload SHA256とWAV全体SHA256を別に記録。失敗なら出力参照はnullとし、完成ファイルを装わない。完成WAVは検査後に原子的に公開対象へ移し、途中失敗のpartialは公開しない。残存partialがあればstatusと所在を記録する。

生成後は別工程としてWAV header・4096 frames・16 kHz mono PCM16、manifest/実bytes SHAと原本SHA不変を確認する。科学原本の抽出規約と変換仕様を固定してから行い、確認のために科学実験を再実行しない。

## 実施境界
この契約は表示案の固定であり、今回の生成・配布・公開を開始する指示ではない。後段の明示された表示作業でのみ実施する。既存レポートや既存PCM変換方式を遡って変更しない。

## 独立レビュー反映（2026-10-20）
独立レビュー文書 `phase-origin-reference-audio-independent-review-20261020.md` を受け、各段の有限性→整数丸め→範囲検査→castを統一し、binary64演算順・subnormal・固定WAV構造・partial非公開を明示した。完全な原rawがあり適合/scoreだけが失敗している場合は、科学状態を別記して参考入力表示を許容する。raw未生成/破損/ID不一致とは区別する。実5入力の有限性・量子化範囲・実runtimeの演算挙動・出力bytesは未検証であり、後段の明示作業まで生成しない。
