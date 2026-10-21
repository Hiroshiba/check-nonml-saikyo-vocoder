# 残差に相関を許すと、F0候補と再合成はどう変わるか

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

文書束 `pml-ar3-model-geometry-20261021.zip`（9,971 bytes、5ファイル）は公式Libraryへ保存済みです。

- SHA256: `1f4708e18147c13ff540675a802dd215c5bf93a6f4a24a0db6530509f819d3a6`
- Library: `libfile_f65bb8cab3fc81919d133720ac0e8017`、version `0`
- 保存ファイル: `file_000000006894823082baf582b1ecbdd2`
