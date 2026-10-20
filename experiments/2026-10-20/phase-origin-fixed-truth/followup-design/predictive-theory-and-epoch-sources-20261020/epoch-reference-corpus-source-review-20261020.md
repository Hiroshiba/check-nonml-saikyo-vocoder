# 自然音声の epoch / VUV 参照資料：一次資料の限定確認

閲覧日：2026-10-20（UTC）。対象：CMU ARCTIC、MOCHA-TIMIT、Keele の3候補のみ。

## 結論

- **confirmed**：音声と EGG / laryngograph を同時収録した既存の自然音声資料は存在する。原配布ページの現存と明示的利用条件まで今回確認できたのは、MOCHA-TIMIT の下記基本サブセット。
- **unconfirmed**：生理学的 GCI の完全真値、校正済み VUV 確率の実配布は確認できなかった。MOCHA基本版とARCTIC初期版には100以上の発話があるが、話者数・収録条件は限られる。
- ユーザー要件の「100音声以上のいろいろな種類のきれいな音声」を、100話者／100独立セッションという新しい採用条件へ変更しない。発話数と話者・収録条件の数を分けて記すのは一般化の限界を明示するためであり、少話者であることだけで採用不可とはしない。
- これは将来の参照・校正資料の所在確認であり、採用決定でも校正実施でもない。人工500研究、品質採用の固定120、現在の phase 研究と PML base は変更しない。音響的 epoch、EGG 由来イベント、生理的閉鎖を同一視しない。
- 公開HTML、README、ライセンス、論文だけを閲覧した。コーパス・モデル・コードのダウンロード、実行、申請、同意、アカウント操作、Git変更は行っていない。

## 判定語

**confirmed** は「明記された資料の内容を確認」の意味で、データ実体の検品を意味しない。**unconfirmed** は記載なし・現行版未検証・閲覧経路で取得できず、のいずれかを併記する。古い仕様を現在の全配布物へ外挿しない。

## 1. MOCHA-TIMIT：現行一次配布ページを確認できた候補

配布・作成：University of Edinburgh CSTR / Queen Margaret University College、Alan Wrench。

### confirmed

- README v1.2 の基本版：英語、msak0（男性）と fsew0（女性）の2話者、各460短文の設計。名目920発話だが、完全な有効ペア920本とは断定しない。
- 音声・Fourcin laryngograph はともに16 kHz・16 bit、NISTヘッダー。別ファイル `.wav` / `.lar`。
- serial-port通信を使う3台のコンピューターへの同時収録で、同期を調整したと記載。
- 公式索引は閲覧可能。fsew0_v1.1、msak0_v1.1、maps0 のアーカイブと unchecked/ が掲載されている。READMEの「2話者」は基本版の説明であり、現在の全公開人数とは扱わない。
- msak0 の既知問題：073の冒頭無音と236の末尾無音でlaryngograph clipping、268は音声とlaryngograph破損。fsew0 v1.1には転記誤り約6%の記載がある。音素／転記ラベルの問題と、GCI精度を混同しない。

### unconfirmed

- 全公開版の実話者数、正常な音声/EGGペア総数、独立収録セッション数。40話者は古い計画であり実配布確認ではない。
- 残留同期誤差、音響伝搬・機器遅延、EGGと音声の数値offset／補正済みか。
- 生理GCI時刻、EGG由来GCI時刻、VUV参照の実配布。READMEの `.lab` / `.mlf` は区間ラベルの説明で、GCIラベルとの明記なし。現時点では、GCI用途にはEGGからの参照イベント推定が必要と扱う。
- アーカイブの取得成功・中身・破損状況は未検証。リンク掲載の確認に止めた。

### 利用・再配布

**confirmed**：研究・教育・個人用途に限定して、利用、複製、改変、配布を無償許諾。ライセンス／著作権表示／免責の保持、改変の明示、原著者名の保持が必要。商用利用は著者の事前書面許諾が必要。今回は許諾申請・同意なし。

一次資料（すべて閲覧日2026-10-20）：

- 公式説明：https://www.cstr.ed.ac.uk/research/projects/artic/mocha.html
- 公式配布索引：https://data.cstr.ed.ac.uk/mocha/
- 仕様：https://data.cstr.ed.ac.uk/mocha/README_v1.2.txt
- 利用条件：https://data.cstr.ed.ac.uk/mocha/LICENCE.txt
- 既知問題：https://data.cstr.ed.ac.uk/mocha/README.msak0
- fsew0の注記：https://data.cstr.ed.ac.uk/mocha/README.fsew0.v1.1
- maps0の注記：https://data.cstr.ed.ac.uk/mocha/README.maps0

## 2. CMU ARCTIC：初期版の同時EGG収録は確認、現行配布は未確認

作成：Carnegie Mellon University、John Kominek / Alan W Black。

### confirmed（版を限定）

- 著者の大学掲載論文（2004）は、英語1132プロンプト、当時4話者、音声・EGG・pitchmarkの配布を記載。
- 技術報告 CMU-LTI-03-177 の原著本文を公開ミラーで閲覧した。付録Dでは、EGG付き初期版は BDL男性1131、SLT女性1132、JMK男性1114発話。合計3377はこの表の算術合計で、現行版の実ファイル数ではない。AWBは16 kHz mono・EGGなし。
- 同報告§4：音声とEGGを32 kHzの2ch ADCで同時収録。channel間delayへの注意を明記。同期収録でもoffsetゼロではない。
- 2005年CMU Blizzard entry論文の **baseline voice** では、pitchmarkを音声からEST `pda` で作成していた。同論文は改良案として、EGGを主とし音声に合わせて調整したpitchmarkも報告する。音声由来という記述はこの論文のbaselineに限定し、現在の全ARCTIC配布物に一般化しない。どちらの報告も、現行GCIラベルの配布や、完全な生理的GCI真値の証明とはしない。

### unconfirmed

- 現行全体の話者数、EGG付き話者数、実発話数、配布版ごとの32 kHz原音と16 kHz加工音の対応。上の初期版数を現在の全ARCTICへ適用しない。
- 数値delay、補正履歴、全発話に対応する独立GCI参照ラベルの現行配布。
- festvoxの原配布ページ・COPYINGは今回の取得経路で読み出せず、現行取得可否と現行配布物の再配布条件は未確認。サイト全体が停止したとは断定しない。
- 技術報告の公式掲載URLは著者ページで確認したが、本文は第三者公開ミラーによる閲覧。公式ホスト本文とのバイト同一性は未検証。この留保のある記載は、現行原配布の検証に代わらない。

### 利用・再配布

**confirmed（歴史的原著記載）**：2004年の著者掲載論文は商用・非商用の制限なしと記載。技術報告付録Aは、用途を問わず利用・複製・改変・licenseする許諾と、著作権／条件／免責の保持、改変明示、著者名保持を定め、録音者がその条件での配布に同意したと記す。**unconfirmed**：現在取得する各配布物のCOPYINGとの一致。

一次資料と閲覧経路（閲覧日2026-10-20）：

- 著者大学ページ（2003年報告への書誌・公式リンク）：https://www.cs.cmu.edu/~awb/index.html
- 著者大学掲載の2004年論文：https://www.cs.cmu.edu/~awb/papers/ssw5/arctic.pdf
- 原技術報告の公式URL（取得できず）：https://festvox.org/cmu_arctic/cmu_arctic_report.pdf
- 同報告の閲覧に使ったミラー：https://ahmed-fau.github.io/fwgan_demo/cmu_arctic_report.pdf （§4、付録A/D/E。一次報告の複製であり、配布元ではない）
- 著者大学掲載の2005年論文（初回調査の経路）：https://www.cs.cmu.edu/~blangner/papers/eurospeech2005/cmu_blizzard.pdf （§3.1、検索索引の本文で確認。直接取得はtimeout）
- 同じ2005年論文の別著者大学掲載本文：https://www.cs.cmu.edu/~cbennett/papers/Interspeech2005b.pdf （2026-10-20の独立レビューで、§2.2、§3.1(1)、§3.5(1)の直接閲覧が報告された。本追補はそのレビュー文書を読んで反映したもので、このノートの作成者が同URL本文を直接再閲覧したという意味ではない）
- 原配布ページ（今回取得できず）：https://www.festvox.org/cmu_arctic/
- SLT COPYING（今回取得できず）：https://festvox.org/cmu_arctic/cmu_arctic/cmu_us_slt_arctic/COPYING

## 3. Keele Pitch Extraction Reference Database：原著の定義は有用、現行取得・条件は未確認

作成：Keele University、F. Plante / G. F. Meyer / W. A. Ainsworth。

### confirmed（1995年原著）

- 原著のcoreは英語15話者（成人男性5・成人女性5・子供5）が同じ物語を読む構成。15朗読に対応する構成で、区切られた発話区間総数は未確認。一般に引用される成人10話者版と同一視しない。
- head-mounted microphoneとlaryngographをDATに同時収録し、両方20 kHz・16 bitでデジタル化。音声 `.pes`、laryngograph `.pel`、文句区間の `.pet`。
- `.pev` は10 msごとのF0/VUV参照。25.6 ms窓のfloating autocorrelationでEGGから作成。GCIの各周期時刻ラベルとは違う。
- 音声とEGGで周期性が食い違う区間をuncertainと区別する。原著はこれが話者によりフレームの約2.5–5%あり、通常の比較では除外すべきと述べる。確率値ではない。

### unconfirmed

- 現行公開版の成人10／全15話者の内訳と実ファイル数、取得可能性。原著の旧FTP紹介は現行取得の証拠ではない。
- 機器・音響伝搬の数値delay／補正。原著の「asynchrony」は音声とEGGの周期性の不一致を含み、単一時間シフトで解消できるとは読まない。
- 各周期GCIラベルの実配布。時刻用途はEGGから別途参照イベントを推定する必要があると扱う。
- 現行の利用・再配布条件。原著のopen／anonymous FTPという表現だけから再配布許可を推定しない。他者の再掲版に付いたライセンス表示を原著者の許諾と置き換えない。

一次資料（閲覧日2026-10-20）：

- 原著掲載ページ：https://doi.org/10.21437/Eurospeech.1995-191
- 原著本文：https://www.isca-archive.org/eurospeech_1995/plante95b_eurospeech.pdf
  - PDF本文のテキスト抽出が壊れていたため、dot側クラウドブラウザーでpp.837–839を目視。コーパスはダウンロードしていない。
- 大学系ミラー候補（今回取得できず、原著の現行配布とは未確認）：https://lost-contact.mit.edu/afs/nada.kth.se/dept/tmh/corpora/KeelePitchDB/

## EGG / DEGG は完全な生理的閉鎖真値ではない

**confirmed**：Herbstらの原研究（2014、著者所属大学掲載）では、摘出イヌ喉頭の高速撮影とEGGをTTLで0.037 ms以内に同期しても、画像上の開閉イベントとdEGGピークには0.02–0.61 msの差が観測された。接触・離開は有限の時間区間にわたり、dEGGピークは必ずしも完全閉鎖・初期開放と一致しない。

出典：https://ucrisportal.univie.ac.at/de/publications/9a402577-e0c4-49b2-b298-256017deef77/

DOI：https://doi.org/10.1242/jeb.093203

閲覧日：2026-10-20。これは当該摘出喉頭実験の結果で、ヒト自然発話に共通の補正量・誤差上限ではない。コーパスの音声/EGG間offsetと、この測定対象・イベント定義に由来する差は別の問題として残る。EGG波形、DEGG検出値、VUV旗のいずれも、それだけで校正済確率にはならない。

## 数の扱い

- MOCHA基本版の460文／話者、ARCTICの約1100発話／話者は、同一話者・関連する収録条件の多数の発話ファイル。統計的に独立な100話者／100セッションを意味しない。
- Keele原著の15朗読を短区間に分割して100以上にしても、独立した話者・収録の数は増えない。
- 3候補の件数を足して品質採用の固定120や人工500の条件へ充当しない。ここでは校正対象の母集団・分割単位を新たに確定しない。

## 次に確認対象として残す一つの資料

**MOCHA-TIMIT の原配布 `fsew0_v1.1.tar.gz`** に限定する。

公式索引上の直接リンク：https://data.cstr.ed.ac.uk/mocha/fsew0_v1.1.tar.gz

選択理由：音声/EGGの対応形式、基本発話数、利用条件を同じ一次配布元で確認でき、原配布物が索引に残っているため。残る確認対象はその実体の対応ファイル・付属説明であり、GCI真値が入っていると予告するものではない。現時点の状態は **unconfirmed（リンク掲載のみconfirmed、未取得・未検品）**。今回の禁止範囲に従い取得していない。新実験、実装、研究への追加を提案・実施しない。
