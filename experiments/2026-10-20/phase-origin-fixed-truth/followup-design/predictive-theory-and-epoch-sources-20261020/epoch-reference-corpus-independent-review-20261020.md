# epoch / VUV 参照資料の独立事実レビュー

レビュー日時：2026-10-20 UTC  
対象：`epoch-reference-corpus-source-review-20261020.md`。MOCHA-TIMIT、CMU ARCTIC、Keeleの3候補に限定。

## 判定

**主要な事実主張に修正必須の誤読は見つからなかった。限定付きで採用可能。**

人数・発話数と版の切り分け、同期収録とoffsetゼロの区別、GCIイベントとF0/VUV参照の区別、歴史的条件と現行配布条件の区別は適切。100音声を100話者という採用要件へ変更していない。EGGを完全な生理的GCI真値・校正済確率ともしていない。

以下の2点は、結論を変えない精度向上として反映を推奨する。

1. **ARCTIC 2005年論文の直接本文を読める著者掲載URLを追加する。**
   - https://www.cs.cmu.edu/~cbennett/papers/Interspeech2005b.pdf
   - 今回このPDFを直接閲覧できた。著者はJohn Kominek、Christina Bennett、Brian Langner、Arthur Toth。§2.2、§3.1(1)、§3.5(1)を確認した。
   - 元資料のBrian Langner掲載URLは今回もtimeoutしたが、「2005年論文は検索索引のみ」という証拠上の留保は、この別著者の大学掲載本文により改善できる。
2. **baseline pitchmarkの対象を限定し、同じ論文のEGG由来改良版も一言区別する。**
   - 推奨文：「2005年CMU Blizzard entry論文のbaseline voiceでは、pitchmarkを音声からEST pdaで作成していた。同論文はEGGを主として音声に合わせて調整した改良pitchmarkも報告する。どちらも現在の全ARCTIC配布物の仕様や、生理的GCI完全真値の証明とはしない。」
   - 元資料の「baseline」限定は誤りではない。ただし「ARCTICの既存pitchmarkはすべて音声由来」と短縮・一般化しないこと。

## 独立照合結果

### MOCHA-TIMIT

**一致。** README v1.2の§1.1–1.4、§2.2相当のSpeakers、§2.4–2.5、§2.8–2.9、個別README、LICENCEと公式索引を照合した。

- msak0男性・fsew0女性の基本2話者、460短文の設計。920は名目上の算術数であり、検品済み正常ペア数ではないという留保が適切。
- 音声`.wav`とlaryngograph`.lar`は16 kHz・16 bit・NISTヘッダー。3台への同時収録・serial-port通信・慎重な同期という記述はあるが、数値offsetや残留誤差の記述は確認できない。
- `.lab`は開始・終了時刻とラベルを持つ区間形式。`.mlf`はHTK master label file。これを周期ごとのGCIラベルとしない扱いは妥当。
- msak0の073／236の無音部clipping、268の音声・laryngograph破損、fsew0 v1.1の約6%の転記誤りは原文と一致。
- 現存索引にはfsew0_v1.1、msak0_v1.1、maps0、unchecked/へのリンクがある。READMEの2話者や38追加予定を、現行全配布話者数へ外挿していない。
- 無償許諾の用途制限、条件・免責・著者名保持、改変明示、商用の事前書面許諾という整理はLICENCEと一致。索引のリンク確認はアーカイブ取得成功・中身の確認とは異なる。

直接照合した資料：

- https://www.cstr.ed.ac.uk/research/projects/artic/mocha.html
- https://data.cstr.ed.ac.uk/mocha/
- https://data.cstr.ed.ac.uk/mocha/README_v1.2.txt
- https://data.cstr.ed.ac.uk/mocha/LICENCE.txt
- https://data.cstr.ed.ac.uk/mocha/README.msak0
- https://data.cstr.ed.ac.uk/mocha/README.fsew0.v1.1

### CMU ARCTIC

**版限定の主張として一致。** 2004年著者掲載論文、2003年原報告の既掲公開複製、2005年著者掲載論文を照合した。

- 2004年論文の1132プロンプト・当時4話者、音声／EGG／pitchmarkの説明は一致。これは全4話者が同じEGG仕様という保証ではなく、元資料はAWB例外を別途明記している。
- 2003年報告付録DのBDL 1131、SLT 1132、JMK 1114、合計3377、AWBの16 kHz mono・EGGなしは一致。
- §4のdual-channel ADC 32 kHz、およびchannel間delayへの注意は一致。付録Dは複数日・修復収録も示すので、発話数から独立セッション数を推定しないこと。
- 2005年論文のbaselineの音声由来pitchmarkは確認できた。EGG由来改良pitchmarkの研究報告もあるが、現行配布GCIラベルの存在・精度まで確定しない。
- 2004年論文の商用／非商用制限なしという歴史的説明と、2003年報告付録Aの条件は一致。現在の各配布物のCOPYINGと一致したとは扱わない。

閲覧経路の区別：

- 直接読めた2004年著者掲載本文：https://www.cs.cmu.edu/~awb/papers/ssw5/arctic.pdf
- 直接読めた2005年別著者掲載本文：https://www.cs.cmu.edu/~cbennett/papers/Interspeech2005b.pdf
- 2003年原報告は既掲の第三者公開複製で照合：https://ahmed-fau.github.io/fwgan_demo/cmu_arctic_report.pdf
- 原報告のfestvox URLおよび原配布ページは今回の閲覧経路でも502、SLT COPYINGは取得できなかった。原配布停止の断定や、複製との同一性の証明はしていない。
- https://festvox.org/cmu_arctic/cmu_arctic_report.pdf
- https://www.festvox.org/cmu_arctic/
- https://festvox.org/cmu_arctic/cmu_arctic/cmu_us_slt_arctic/COPYING

### Keele

**1995年原著の記述として一致。** PDFの機械抽出が壊れているため、dot側クラウドブラウザーで印刷頁837–839を目視照合した。

- §3.1は同じ“The North Wind Story”を読む15人、成人男性5・成人女性5・子供5。本文上のcore構成と成人10人版を区別した記述は適切。
- 同時収録、head-mounted microphone、laryngograph、DAT、両方20 kHz・16 bit、`.pes`／`.pel`／文句区間`.pet`は一致。
- §3.2の`.pev`は10 msごとのpitch estimateとVUV判断。EGGから25.6 msのfloating autocorrelationで算出する。周期ごとのGCI時刻列ではない。
- uncertainは一方だけに周期性が見えるなどの不一致区間であり、約2.5–5%という記載は一致。正の推定値、無声の0、EGGのみの周期性を表す負の推定値、音声のみの周期性を表す−1という符号化を持つ。確率ではない。
- asynchronyを単一の機器時間遅れと決めつけない説明は妥当。原著は不一致区間を比較から可能な限り除外する立場。
- 原著のopen／anonymous FTPだけで現行取得や再配布許諾を確認済みとしない判断は正しい。

直接閲覧した原著：

- https://www.isca-archive.org/eurospeech_1995/plante95b_eurospeech.pdf

## EGGに関する補足主張

Herbstら2014年研究の著者所属大学掲載抄録を照合した。摘出イヌ喉頭、TTLで0.037 ms以内に同期、dEGGピークと画像上イベントの差0.02–0.61 ms、接触・離開が有限区間にわたる、という数値と要約は一致。

この結果をヒト自然発話全体の共通補正値・誤差上限にしないという留保は必要で、元資料は明記済み。コーパスの音声／EGG系のdelayとイベント定義・測定対象の差を混ぜていない。

- 確認した掲載先：https://ucrisportal.univie.ac.at/de/publications/glottal-opening-and-closing-events-investigated-by-electroglottog/
- DOI：https://doi.org/10.1242/jeb.093203

## 範囲・未確認の維持

公開説明・README・利用条件・論文の閲覧のみを実施した。コーパス、モデル、コードは取得せず、アーカイブのダウンロードリンクも開いていない。申請・同意・コード／音声処理・実験・テスト・Git変更は行っていない。

元レビュー資料は編集していない。今回作成した成果物は本レビュー文書のみ。人工500、固定120、phase研究、PML baseの状態確認・変更は本作業の対象外であり、保全を前提とする。MOCHAのfsew0_v1.1を「次に確認対象として残す」という文言は、取得・実験・採用の実施許可とは扱わない。
