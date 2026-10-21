# AR1残差の三点事前は、既存D1比較と別の実験群にする

2026-10-21。公開前の編集用骨子。GitHubの現行指示と保存済み資料を読み、文章だけを作成した。Git・Cloudへの書き込み、推定・合成・品質計算、テスト、数値probe、音声の切り出しは行っていない。

## 公開先は「残差の相関」を主題に分ける

推奨タイトルは「残差に相関を許すと、F0候補と再合成はどう変わるか」。副題は「三点AR(1)事前と一次差分平滑化による、既観測3録音の開発比較」とする。「AR3」は三つの原子を持つAR(1)事前の内部略称であり、AR(3)モデルとは呼ばない。

新グループ案は experiments/2026-10-21/pml-ar1-three-atom-residual/、初回結果は results/run-001/。今回は雑音の尤度を変えた問いなので、既存 pml-first-difference-post のrunを置き換えない。旧51品質値、HTML、15短例、PR103の公開URLはそのまま保持し、新報告から前回比較としてリンクする。

- 旧公開報告: https://hiroshiba.github.io/check-nonml-saikyo-vocoder/experiments/2026-10-21/pml-first-difference-post/results/run-001/index.html
- 旧報告のマージ: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/commit/862b0285b8838006d12bdaaa2f50f89af70e042a

グループのREADMEは今回の問い・到達点・判断できないこと・次の確認を記す。experiment.jsonのdateは2026-10-21、timezoneはAsia/Tokyo。created_atとruns[].recorded_atには実際の案内・掲載記録日時を入れ、nativeや品質の実行開始・終了時刻は別に保存する。予定時刻やファイル更新時刻で補わない。

## 冒頭にPMLとの比較と音声を置く

HTMLの並びは、短い結論、PML・既存対照を含む録音別の品質表と固定対応差、比較音声、その後に方法・診断・実行証拠とする。品質受領前の冒頭案は次のとおり。

「同じ1話者の既観測3録音で、残差に三点AR(1)事前を用いた新しいL/Fの6枝は音声生成に成功しました。品質評価75値は結果を未受領で、改善の有無はまだ判断できません。PMLを唯一の正式ベースとして維持します。」

これは現時点の状態文であり、最終結論の雛形ではない。品質の実終了・個票・入力対応を受領照合してから、得られた事実にだけ置き換える。成功予定数を測定済み件数にしない。旧IIRの失敗、旧段階B・残り117録音への展開停止も保持する。

一覧は新しい実行の日時、上記テーマ、1話者3録音の範囲、受領済みの最小限の個票、短音声への入口を表示する。欠測や未受領を0で埋めず、既存の集計欄へ仮の平均・中央値を入れない。旧D1の掲載形式を参考にできるが、新しい群・6条件・新測定の識別を保つ。

## 変えたのは残差の族、固定したのは比較の条件

H0/H1とすべてのq,Kで、aが−0.8、0、0.8を各1/3で取る同じ事前を使う。これはモデルそのものの有限離散事前で、連続事前の三点求積近似ではない。固定aの周辺密度を有限和で混ぜる。aごとの最大値、対数密度の平均、固定aのBFの等重み平均とは区別する。

q=52..512、K=1..10、16 kHz・400標本窓、完全cos/sin対の基底、係数事前I/K、scale事前IG(3,2c)・c=1、H0=0.3と各(q,K)=0.7/4610の候補事前を維持する。物理窓ごとのRMSは一回だけで、whitening後の再正規化を加えない。定常初期行とdeterminantを含む式、欠測扱いも維持する。

局所選択Lと系列選択Fの規則、gate規則、DPの係数、D1、seed、保存・復号・合成backend、評価器・入力区間を固定する。規則が同じでも、入力される候補評価値が変わればgateと経路は変わり得る。REAPERの下限65 HzとL/Fの下限50.78125 Hzの違いも残る。旧hyper-gの係数事前へ読み替えない。

## 対応差は先に決めた組だけを録音別に示す

対象IDは librispeech_1089-134686-0008、0011、0032の全3録音。6条件はPML、R_d1、L_d1、F_d1、L_ar3_d1、F_ar3_d1。新規nativeは後ろの2条件×3録音だけで、前の4条件は保存済みnativeのバイト参照である。

主比較と補助比較の順を固定する。

1. L_ar3_d1 − L_d1。局所選択のまま、残差モデルを変えた差。
2. F_ar3_d1 − F_d1。系列選択のまま、残差モデルを変えた差。
3. L_ar3_d1 − PML、およびF_ar3_d1 − PML。正式ベースとの総合的な出力差。
4. F_ar3_d1 − L_ar3_d1。同じ新残差モデル・D1内の系列選択の差。

R_d1も生値と音声に残す。旧標準8方式は今回と評価条件が一致しないため、過去値をこの表の同条件比較へ混ぜない。UTMOS・ECAPA cosine・eSTOIは高い方向、SCOREQ natural参照距離は低い方向が有利。差の符号と有利方向を併記し、条件間・録音間・指標間の平均、総合順位、有意差は作らない。

品質が全件成功した場合の予定数は、6条件×3録音×4指標=72値と、原音UTMOSのみ3値の計75値。参照4条件の品質も今回新規測定し、旧51値を流用しない。UTMOSは保存native・原音の全区間、他3指標は固定した同録音の共通先頭区間を使う。新旧参照値に差が出た場合は差を隠さず、入力SHA、区間、評価器、seed、thread、runtimeを照合する。数値を合わせるために再測定しない。

順位の扱いには注意が必要である。USER_INSTRUCTIONS.mdには指標順位の表示要件がある一方、現行PUBLISHING.mdは保存順位の引用を原則とし、順位が保存されていなければ追加計算しないと記す。旧D1公開も個票・対応差のみだった。本骨子では依頼範囲どおり順位を作らず、特にこの1話者3録音から全方式の順位を捏造しない。公開担当は指示の優先関係と直近の許可範囲を確認し、未作成の順位を保存済みのように表示しない。

## clamp減少は、品質と別の保存観測として添える

保存JSONの照合では、旧white D1から新AR3 D1への全6対でclamp件数が減り、rawでgate=0となったフレーム数が増えた。この二つを品質表の代わりにせず、説明用の診断欄に置く。

clamp件数は、rawの0を正値で補間した後、65..700 Hzへ制限する直前の範囲外件数である。正のraw F0が65 Hz未満だった件数とも、真の低F0誤り率とも一致しない。低い正値の選択とgate変更に伴う補間先の変化を、この集計だけで分離できない。post範囲外0件も保存値の範囲整合に限られる。新しい尤度採点や原因の証明として扱わない。

## 音声は同じ先頭2秒を21枠にそろえる

掲載案は3録音×「原音＋6条件」の21枠。先頭2秒・16 kHzの同一区間を使い、旧D1報告と同じround(x×32767)のPCM16変換条件を採る。新しい音量補正、alignment、無音除去、clippingは加えない。丸め後の範囲を確認できなければ黙ってclipせず、問題を報告する。

本骨子では短例を作っておらず、21枠を「掲載済み」と書かない。将来作成する音声manifestには、元archiveの連鎖とmember、入力・出力SHA、区間、変換式、長さ、LibriSpeech / CC BY 4.0の出典と変更内容を記す。掲載用PCM16を品質計測へ戻さない。全長音声はGitに含めない。

詳細には全21枠を置き、一覧は同じ0008の原音・PML・事前指定した新候補など必要最小限を参照する。品質結果を見て都合のよい録音や代表候補へ差し替えない。掲載時の短音声・帰属・SHA・サイズ確認は現行公開規則に従う。

## 実行時間は三つの範囲を分けて記録する

- 新nativeの実行証拠: 実終了0、elapsed_seconds=188.8887625670004、最大RSS=346104 KiB。これは今回のランチャー記録の値として引用し、局所尤度だけの時間や純RTFへ読み替えない。枝別計時は保存された対象範囲を併記する。
- 参照4条件の過去計時: バイト再利用であり、新解析・新復号・同環境の再計時ではない。新nativeと速度比を作らない。
- 今回品質の実行証拠: 受領後に実終了、全件数、wall、RSS、警告を転記する。native時間、品質モデル準備、品質推論、掲載用音声作成を一つのRTFへ足さない。

「三点なので約3倍」は固定aの局所処理量の目安に限られ、実時間や全pipelineの保証ではない。今回の実測として使わない。

## 公開束は結果と証拠に限定する

推奨構成はexperiment.json、README.md、設計・二巡の議論、results/run-001/index.html、results.json、録音別品質個票、paired-differences.json、実行証拠、監査verdict、受領照合、警告を含む全イベント、短音声、帰属HTML、audio-manifest.json。診断は同じ主比較のsupplementまたは本文へまとめ、一覧カードを増やさない。

結果JSONにはPMLと版pml-lowband-fwcep60-v1、既観測の開発1話者3録音、6条件、実行/参照の別、指標ごとの方向・区間・status・個票参照を残す。失敗・未実行・適用不能は区別し、nullを0にしない。新旧の品質・source・native identityを混ぜない。新群用study_roleが必要なら公開表示だけを限定的に扱い、旧D1の識別を偽装しない。

候補実装・監査実装・品質ソース、モデル、全長波形、生特徴、原ZIPはGitへ置かない。候補ソースは既存Library保存を参照し、公開文書では版・manifest SHA・依存版などの来歴を示す。保存配列監査のpassedは選択・D1・保存契約の整合であり、全(q,K,a)尤度の独立再計算、高精度解、波形の独立再現、真F0、品質保証ではない。監査自身のapproved_for_quality=falseと、後続の親による品質実行承認を区別する。

編集時に対応を照合する保存束は次のとおり。これはGitへの同梱一覧ではない。

- 新native delivery: 41,442,909 bytes、SHA256 dcbcc49b9cffcded4188adcb32bf61c068344ebf767c76c8bb3591de0506fbe2。Library libfile_a244bfdf237481919e016453b40ec273、version 0。
- その中の新native ZIP: 41,430,719 bytes、SHA256 8431e6fb7c206413a00e0ee5bf07e4827076525c390469a168baf722b1cdaafd。
- 入れ子の旧D1 delivery参照: 18,504,522 bytes、SHA256 43ffc10cdcdd739fb6f0583287af787a39d17050f09a801abe1aa1bd4ec0a21f。旧51品質値とは別のnative出典。
- 新native source: ZIP SHA256 a4b4f84d1e913a34439a14cacd335d1a24ad11a64d990a9bab45878662c5c469、manifest SHA256 20937857f1bd6422b9ef6d84c5e572f3331540d79c0b8649e4030fc076648494。実装本体はLibraryのみ。
- 監査・承認: 実native独立監査verdict、ファイルmanifest、受領receipt、親の品質admission receiptを別の証拠として保持する。
- 今回品質delivery: まだ未受領。受領後に新しいarchive identity、実終了、75個票とeventsの実数、採点入力のarchive連鎖とSHAを登録する。旧51値の束をこの欄へ代入しない。

品質受領までは結果の空欄を埋めない。受領後も、独立validation、F0/VUV真値校正、全120完了、方式採用、48 kHz適用の実績は主張しない。今回の報告が決めるのは、固定条件の開発3録音で新旧出力の違いがどう観測されたかまでである。

## 文面と公開規則の参照

natural-japaneseのSKILL.md、メモ型・レポート型、手動チェックリストを参照し、結論先行、比較を冒頭に置く構成、専門語の説明、事実と未確定の区別を確認した。今回はコード実行禁止のためlintスクリプトは実行していない。公開HTML・一覧の実文を作る際にも同スキルを適用し、許可された範囲で静的文面検査と最終通読を行う。原文保存の設計資料は黙って改稿しない。

- ユーザー指示: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/USER_INSTRUCTIONS.md
- 記録の構成: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/experiments/README.md
- 公開規則: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/PUBLISHING.md
- 比較と集約の規則: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/EVALUATION.md
- 作業の範囲と停止線: https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/main/docs/WORKFLOW.md
- 日本語文面: https://github.com/Hiroshiba/hiho_ai_coding/blob/main/base/skills/natural-japanese/SKILL.md

編集用の照合元は共通AR1設計、三原子補遺、AR3+D1比較計画、保存観測の範囲メモ、実native独立監査verdict、親の品質admission receipt。公開束には実在する相対リンクで必要な証拠だけを写し、作業機の絶対パスを公開リンクにしない。
