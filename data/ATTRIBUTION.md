# 自然音声の出典と利用条件

最初の2区間は実装と測定器の動作確認用です。固定120録音へ拡張した比較も英語の通常発声に限られ、音声品質を広く代表するコーパスではありません。
初回比較に使用したLibriSpeech音声の取得URL、固定版、内容照合用のハッシュ値、変換内容は [manifest.json](manifest.json) に記録しています。unfaの音声は調査時の候補であり、この取得用一覧には含めていません。

## LibriSpeech

- 出典データセット：[LibriSpeech, OpenSLR SLR12](https://www.openslr.org/12)。
- データセット作成者：Vassil Panayotov、Guoguo Chen、Daniel Povey、Sanjeev Khudanpur。元の朗読音声はLibriVoxのボランティアによる録音です。
- ライセンス：[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)。
- 取得元ミラー：[langtern/librispeech-test-en](https://github.com/langtern/librispeech-test-en/tree/aa69814de02d7d9eca5e61456c8fee8a0e85dd92)。同リポジトリはLibriSpeechのテスト音声であることと、CC BY 4.0の表示を記載しています。
- ファイル：`librispeech_5142-36586.wav`、`librispeech_7021-79759.wav`。
- 変更内容：元のFLACをFFmpegで符号付き16-bit PCMのWAVへ復号しました。サンプルレート、チャンネル数、レベル、全体の長さは保持しています。比較実験で一部を切り出す場合は、正確なサンプル区間と出典を実験のデータ記録に残します。
- ミラーは朗読の章単位でファイルを提供しています。対応する書き起こしにはそれぞれ5件と6件の発話IDが含まれます。実験用に切り出した区間を、元コーパスの1発話として扱わないようにします。

## unfa

- 作者：unfa。
- 原作品：[Clean male shout: “Are you readyyy?!”](https://freesound.org/people/unfa/sounds/258342/)、2014年12月20日。
- 原作品のページに表示されたライセンス：[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。
- 取得元ミラー：[Sleepwalking/libllsm2/test/are-you-ready.wav](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/test/are-you-ready.wav)。libllsm2のREADMEに、元のFreesoundのURLが記載されています。
- ファイル：`unfa_are-you-ready.wav`。
- 変更内容：取得したミラーのWAVは変更していません。ミラーは44.1 kHzのモノラルPCMですが、原作品は96 kHzのステレオFLACと説明されています。ミラーで行われた変換の設定は不明です。
- 原作品のページには、作者が生成系の機械学習への利用に同意しない旨も記載されています。本プロジェクトで想定する用途は、非MLの解析・合成の評価です。生成モデルの学習には使用しません。

出典とライセンスのページは2026-10-11に確認しました。ミラー側リポジトリのコード用ライセンスを、音声のライセンスとして扱ってはいません。

## 初回の使用範囲

今回の比較レポートで使用したのはLibriSpeechの2ファイルの先頭各6秒です。unfaの音声は調査時の取得候補で、初回レポートにも取得スクリプトの一覧（manifest）にも含めていません。取得した章単位の録音全体はGit管理していません。WORLD Harvestをベースにした比較以降は、LibriSpeechの各固定区間の先頭最大2秒を音声例としてレポートに同梱します。原音と合成後の音声は浮動小数点WAVの形式でJSON・HTMLに埋め込み、Git管理・Pages公開します。出典・ライセンスは上記のLibriSpeechと同じで、合成後の音声には各方式による解析・再合成を施しています。

## 固定120録音への拡張

2026-10-12の比較では、[OpenSLR公式test-clean](https://www.openslr.org/resources/12/test-clean.tar.gz)から40話者・各3録音を固定しました。著者・ライセンスは上記LibriSpeechと同じです。元FLACと復号PCMのハッシュ、発話ID、書き起こし、先頭最大6秒の測定区間を [clean_speech_v1.json](clean_speech_v1.json) に保存しています。16 kHz・モノラルを保持し、雑音除去・音量正規化・時間整列はしません。

公開する音声例は固定ID `1089-134686-0008` と `1188-133604-0003` の先頭最大2秒です。原音は抜粋と浮動小数点WAVへの変換、各方式の例はそれに加えて解析・再合成を施しています。評点を見て選んだ区間ではありません。レポートの各方式名が変換内容に対応します。

JVSの取得済み12録音は補助資料として分離しています。正式120件へ含めず、元音声・変換音声とも今回の公開物へ同梱しません。[取得範囲と制約](../docs/CORPUS.md)を参照してください。
