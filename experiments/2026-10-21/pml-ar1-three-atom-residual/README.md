# 残差に相関を許すと、F0候補と再合成はどう変わるか

## 保存値の差は、raw変更行だけには局在しなかった（観測：2026-10-21 UTC）

[保存段階の差の補足レポート（Pages）](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/experiments/2026-10-21/pml-ar1-three-atom-residual/results/saved-stage-propagation-v1/index.html)に、従来AR3とACGの同じL/Fを、raw・D1後・保存F0・FWCEP・NM・波形の順に比べた観測を記録しました。rawは枝別47行、重複を除く41時点で変わり、raw不変行にも下流差がありました。これはF0選択の違いに由来する可能性を否定するものではなく、個々の変更の因果範囲も特定しません。

6枝の全行・セル・標本の分母を示し、全マスク・区間・全ログと独立確認へ案内します。完全一致しない位置数であり、大きな誤差や品質悪化の面積ではありません。FWCEP/NMは元SPEC/PDDの圧縮・派生表現で、元SPEC/PDDは未保存です。既存18短音声を参照し、新しい品質測定や音声生成はしていません。PMLとrun-001/002の数値・音声・日時は保持します。

## ACG音声の品質は新規24値と引用39値で比較した（2026-10-21）

[ACG音声とPML・従来AR3の比較（Pages）](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/experiments/2026-10-21/pml-ar1-three-atom-residual/results/run-002/index.html)に、同じ録音・同じ後段処理で候補の重み付けを替えた結果を記録しました。PML比では新L/Fの全6枝でECAPA・eSTOIが低く、SCOREQ距離が高い方向でした。UTMOSは0008・0011で低く、0032で高くなりました。従来AR3の同じL/Fとの変化は指標・録音で混在し、正式ベースはPMLを維持します。

63値・48対応差と、録音・指標ごとの合成5条件の記述的順位を示し、原音UTMOSは順位外にしました。18短音声は既存JSONを参照し、再生成・再変換していません。品質計測用のソースv2の科学コードは変更せず、通常の実行用ラッパーで実行し、独立確認9項目はすべて通過しました。今回の捕捉警告25件と過去の起動前停止・保持不確実の履歴を分けて残しています。

既知の同一話者3録音の冒頭の固定区間による開発比較です。PMLとACGの差を密度だけの原因へ帰属させず、音高精度・一般化・有意差・採用は判断しません。旧run-001の75品質値・21短音声・日時はそのままです。以下は従来のAR3比較と追補の記録です。

有限3原子のAR1残差事前（AR3）だけを変更し、L/F選択・D1・後段の解析と復号を固定した別実験群です。[結果と21短例](results/run-001/index.html)に、既知の1話者3録音の75品質個票と指定60対応差を掲載しました。平均・総合順位・有意差・採用は主張せず、PMLを維持します。全120録音や独立検証ではありません。

対応する旧L/Fより新L/FのECAPAは全3録音で上昇しました。eSTOIとSCOREQは0008/0032で改善方向、0011で悪化方向、UTMOSは0008/0011で悪化方向、0032で改善方向です。PML比では新2条件とも3録音すべてでECAPA・eSTOI・SCOREQが劣り、UTMOSは混在します。SCOREQだけ低い方向、他3指標は高い方向です。原音はUTMOS参考のみで、旧標準8方式の条件未一致値は混ぜません。

新6枝はnative成功し、参照12枝の音声は今回のZIP内に一度だけ保存されたnested priorから原バイトで再利用しました。品質75値は参照4条件を含めて全件新規測定で、過去51値の代入ではありません。独立受領監査4089検査は通過し、新たに測定した参照＋原音51値は前回D1と完全一致しました。この掲載でも全75個票のmember・ペイロード・採点区間SHAを受領nativeへ照合しています。

## 有限3原子は事前そのもので、他の処理は固定した

a={−0.8,0,0.8}・各1/3は、連続積分の求積近似でも中立事前でもありません。H0/H1共通、物理窓でRMS一回、properなI/K係数事前・IG(3,2)、q/K・L/F選択・D1・後段処理を固定しました。原子診断はH0とH1で別に扱い、H1側はq,K周辺化後の量です。選択qの責任度や校正済みF0/VUV・雑音確率ではありません。

[保存メタデータの比較](results/run-001/post-metadata-comparison.json)では全6対でclampが減り、raw無声が増えました。clampは0補間後・平滑化前の件数で、raw低F0誤り率や低qの直接選択件数ではありません。追加の保存配列観測は今回へ含めていません。

## 個票・時間範囲・失敗履歴を分けて読む

UTMOSは保存native全区間、他3指標は開始0から95840/95840/65280標本です。eSTOI 18個票のscope文字列は評価器説明で上書きされているため、元個票を改稿せず、区間は標本数とprefix SHAを根拠に説明します。2秒の掲載コピーは品質入力ではありません。

局所量の時間、選択・raw保存照合時間、新6枝のD1以降の部分RTFを分けて引用し、足し合わせた新しい速度値は作っていません。参照nativeの過去計時は今回の計測へ読み替えません。品質の70警告とnativeの596警告は別に全イベントを残し、stderr 0を警告0とは扱いません。

native独立監査の初回はPython選択ミスでNumPyがなく、保存配列前に停止しました。同一監査ソースの別v2は既存NumPy 2.3.5環境で実終了0・3項目通過です。native自体の失敗や、全尤度・真F0・音質の証明とはしません。品質source v1は起動前の履歴schema形不一致で未実行、v2は文書schemaとsource-versionのみ訂正との親報告で、D1以前の環境記録失敗と区別します。

## 短音声は21件とも実変換し、独立expected SHAへ照合した

原音＋6条件×3録音、16 kHz・標本[0,32000)の同じ先頭2秒です。round(x×32767)のPCM16変換前に全範囲を確認し、クリップ・音量正規化・位置合わせ・無音除去をしていません。元NPYペイロードと全PCMバイト、WAVヘッダ・SHA・ラベルを照合し、親の独立実変換expected SHAとも21/21一致しました。[音声manifest](results/run-001/audio-manifest.json)に変換・区間・元/出力SHAとLibriSpeech / CC BY 4.0帰属を記録しています。一覧は0008の7条件です。

## 設計7原文を全文で保存した

以下の7原文（Markdown 6件と比較JSON）と[元MANIFEST](design/MANIFEST.json)はLibraryの設計bundleから原バイトで保存しました。連続prior検討と有限3原子の改訂、五仮想役の二巡、数学静的レビュー、報告骨子と保存観測を履歴ごと保持し、要約に置き換えていません。実行前・未実施という原文表現は、それぞれの保存時点の記録です。

- [AR3 + D1 の開発比較で確認すること](design/pml-ar3-d1-comparison-plan-20261021-ja.md)
- [共通三原子 AR1 + D1 source の独立静的レビュー](design/pml-ar3-d1-native-independent-static-review-20261021-ja.md)
- [AR3 + D1 保存観測の読める範囲](design/pml-ar3-d1-observation-scope-20261021-ja.md)
- [AR3+D1 first3 quality75 独立受領監査](design/pml-ar3-d1-quality-v2-independent-review-20261021-ja.md)
- [AR1残差の三点事前は、既存D1比較と別の実験群にする](design/pml-ar3-d1-report-outline-20261021-ja.md)
- [現行調波モデルの共通 AR1 残差を検討する](design/pml-common-ar1-residual-design-20261021-ja.md)
- [三原子 AR1 事前による探索候補の補遺](design/pml-common-ar1-three-atom-addendum-20261021-ja.md)
- [原文の保存メタデータ比較JSON](design/pml-ar3-d1-post-metadata-comparison-20261021.json)

独立品質レビューの短い原文noteも上記へ加えています。原文の`/workspace/shared/...`などは当時の照合元パスで、公開URLではありません。今回の比較JSON・元個票・監査判定は[掲載記録の来歴](results/run-001/receipt-verification.json)から辿れます。独立品質監査は親admission・ソース保持receiptを含む来歴とdetailを除いた[公開用チェックJSON](results/run-001/quality-independent-review-public.json)とし、全4089検査名・判定と元JSONの容量・SHAを保持しました。資産本体の再取得や再推論、遠隔実行の独立証明ではありません。

`created_at`はこの群の案内を作った実時刻、runの日時は掲載用記録の作成時刻です。旧D1群・原設計・原結果は変更せず、新しい群として登録しました。候補実装・モデル・全長音声・親のadmission/保持receipt・ユーザー会話はGitへ追加していません。natural-japanese quickは新しい案内・HTML・一覧・要約・STATUS・PR文面へ適用し、原文は改稿していません。

## 固定モデルの幾何を読む紙上追補

[低q選択と固定次数・係数事前の幾何](followup-design/model-geometry-20261021/README.md)へ、議論原文・別担当の紙上確認と親追補を保存しました。親追補が最新の読み方です。Bは次の紙上点検対象であり、原因認定や新モデル・係数尺度・実行条件の採用ではありません。原文の「未受領」は当時の記録とし、別工程の保存配列観測の細目や数値結果は追加していません。公開済み75品質・21短音声とPML維持は不変です。

初版の文書束 `pml-ar3-model-geometry-20261021.zip`（9,971 bytes、5ファイル）は訂正前の記録として公式Libraryに保持しています。

- SHA256: `1f4708e18147c13ff540675a802dd215c5bf93a6f4a24a0db6530509f819d3a6`
- Library: `libfile_f65bb8cab3fc81919d133720ac0e8017`、version `0`
- 保存ファイル: `file_000000006894823082baf582b1ecbdd2`

訂正版を最新とします。独立確認の `If Δ>0 while` を親の原文に合わせ、H0の原子重みをデータ z に条件付けた事後重みと明確にしました。旧Library保存物は変更していません。

訂正版 `pml-ar3-model-geometry-20261021-corrected.zip`（10,186 bytes、5ファイル）も公式Libraryへ保存済みです。

- SHA256: `737617e2e429f479c34c5380daf1b1ec774111533cb7bbf5fb2506167b1fd70a`
- Library: `libfile_216a6268378c81918f457b1dfe8c61ef`、version `0`
- 保存ファイル: `file_00000000de788230bc38a42dc2b48b50`

## 混合差と成分変化の紙上補題

[混合得点の差から、成分の変化をどこまで言えるか](followup-design/logsum-component-bounds-20261021.md)に、30成分logsumの境界と反例を保存しました。lowerとupperは異なる極値への片側制約です。今回の別担当の確認は式・反例・解釈条件の紙上整合性に限ります。実データ診断はexit0との報告がありますが、保存HTTP401で親は本体未受領のため、数値や診断結論は加えていません。既存の原文・親追補と公開結果は保持しています。

最新のリンク訂正文書（UTF-8、5,710 bytes）を公式Libraryへ新規保存しました。Library名は `logsum-component-bounds-20261021(1).md` です。旧版 `libfile_74f320b70644819181d480b3f2eb3e84`（version `0`）も保持しています。

- SHA256: `4f76e69d62ebfdbaedcfc58a95a8093661a0eef1ac15818b65aefe9a5a9ad64d`
- Library: `libfile_fce5d8f31fa881918c3d7e05828f9175`、version `0`
- 保存ファイル: `file_00000000368081fdb33ccdef542807b1`

## 方向密度の別仮説と、未実行の限定感度分析

[同じ連続モデルを方向へ写す別仮説](followup-design/directional-density-20261021/README.md)と、固定3録音の全物理窓を対象にする感度分析計画を保存しました。旧tを誤りとは断定せず、全体尺度の消去と相対λ=1・I/Kの前提を分けます。計画は全13,833成分を保持し、得点定義だけによる対応差を記述する未実行案です。新run・音声・品質値・base変更はありません。旧401/403と未受領の診断・監査成果は別のままです。

欠測と科学的失敗を区別した訂正文書束 `ar3-directional-density-design-20261021-failure-clarified.zip`（6,115 bytes、3ファイル）を公式Libraryへ保存しました。こちらが最新です。初版 `libfile_64160b93e5208191a672a5a41c8cd279`（version `0`）も保持しています。

- SHA256: `a8431c4a638b86518ac66133bbd9c5042ba44fd1994272841c3c09b74440605e`
- Library: `libfile_00036892fed48191a9c7319b7244c706`、version `0`
- 保存ファイル: `file_00000000f8d48230a732175834b59b30`

## 同じ観測で得点定義を変えた方向密度の補助解析

[方向密度対比v2の保存値・独立監査・全窓データをPagesで開く](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/experiments/2026-10-21/pml-ar1-three-atom-residual/results/directional-density-v2/index.html)。既存固定prefix最大6秒の1話者3録音、3,209 unique窓・3,218 anchorです。候補ID q=52..66（15候補）対q=67..512（446候補）のlog oddsと、H1/H0の仮説priorを除くlog evidence ratioについて、ACG−tの対応差の録音別中央値を記録しました。PMLを維持し、新音声・品質比較はありません。

旧tの全461候補値は全窓でbit一致し、独立再集計のH1/H0比の全行と録音別中央値も一致しました。低域log oddsのt・ACG・差の3列には842セルの最終桁差があり、最大絶対差は2.842170943040401e-14です。許容差による合格や全計算完全一致とは扱いません。捕捉警告0件の原因は確定せず、安定性・真F0・生理的VUV・音質の改善や採用は主張しません。原計画の未実行という表現は当時の履歴です。

## 倍音係数の固定減衰案は、計測せず紙上で閉じる

[固定減衰案を計測しない判断](followup-design/fixed-harmonic-prior-decay-20261021.md)を保存しました。この固定形状の根拠と追加計測で得られる情報が不足するため例示へ戻し、指数探索・逆順対照の追加計測・実装は行いません。PMLと既存結果・原計画は維持します。

## 保存済みACG重みの音声比較計画と初回失敗

[音声比較計画と初回失敗の記録](followup-design/saved-acg-lf-d1-plan-20261021.md)を保存しました。2026-10-21 09:13 UTCの開始指示後、v3初回は `SOLVER` 定義欠落で初期化停止し、旧t入力監査0/3録音・新ACG生成0/6音声です。親が監査原本を全受領し、三層の終了と全出力の完了まで確認しました。音声・品質結果はありません。旧referenceと同値の辞書を戻したv4は、09:25 UTC時点では公式保存済み・独立静的レビュー中・再実行なしでした。同日09:28 UTCに静的確認と親の具体的計画照合を経て初回開始が指示され、実開始・結果報告はまだ未受領です。開始前の計画・日時付き履歴、科学条件・PML・既存結果は保持します。

音声生成と品質評価の最新状況は、[音声比較計画の冒頭](followup-design/saved-acg-lf-d1-plan-20261021.md)を参照してください。

## F0候補の識別と声質の分離を区別する文献記録

[一次資料2本の評価範囲](followup-design/f0-identification-source-filter-scope-20261021.md)を整理しました。F0識別と声質の物理的解釈を分け、現ACGの品質や次の事前・モデルの採用根拠とはせず、PMLを維持します。

## 得点定義による音高選択の変更を、保存配列で読む補助診断

[6行の集計・47明細・参考音声のレポート（Pages）](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/experiments/2026-10-21/pml-ar1-three-atom-residual/results/saved-raw-f0-changes-v1/index.html)を追加しました。旧AR3との比較は操作上の有声→無声6件・双方有声の音高変更41件で、L/F重複を除くと41時点です。双方有声41件中26件は局所首位が同じでしたが、DPだけを原因とはしません。PMLの時計は行対応せず、品質未評価・PML維持とします。既存の品質run-001は保持し、予定の品質run-002は未公開です。
