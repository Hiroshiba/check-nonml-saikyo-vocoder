# 固定120録音の段階保存契約案

新規実行の開始前に凍結する評価・保存契約。旧120連続実行の続きや同一SHAの復元とは扱わない。合成アルゴリズムは変更しない。測定値を見る前に10区間を確定し、良い区間だけ残さない。

## 全体計画

元の固定120 manifestの順序を保ち、先頭から12件ずつ10区間に分割する。話者や録音の抽選をし直さない。全120/40話者/各3録音を予定分母とし、主71軸、±3編集品質、原音MOS120、全文ASR55/対象外65を開始前に予定表へ固定する。

計画には入力manifest・評価ソース・候補source freeze・現PML/WORLD source・DSP/品質runtime・モデルasset・前処理・seed・thread・条件・case順のdigestを保存する。波形や原音の実path、候補実装本体、payload、モデル、保存サービスのIDはprivate配置ファイルだけに置く。公開計画はcase/speaker/原音SHA/N/SR/共通窓、公開method名、予定metric/conditionとdigestに限定する。

PMLは現正式base pml-lowband-fwcep60-v1、seed0。候補nativeはCartesian q0で、直接native decodeはq1参照費だけ。WORLD Harvestはnativeのみ、編集はunsupported。ASR原音CERゲート・eSTOI/音響/ERB/SCOREQ/ECAPAの既存共通先頭窓・MOS全長を維持する。旧8方式の値は完全identityが別途証明できた軸だけ別引用する。

## 区間内の順序

1. 同区間12件の候補native/±3生成、ケース単位保存
2. 同区間12件のPML native/±3、WORLD native生成
3. 原音を含む同区間の純粋評価。音響→ERB→SCOREQ→MOS→ECAPA→ASR→編集追従/品質を直列
4. 各stage終端で入力/source/runtime/model/採用波形を再照合し、区間validated_endを発行
5. 数値・失敗・分母・公開可能な来歴だけ小さなcheckpointへ射影し、独立公開監査後にGitへ保存
6. Git側の保存commitを確認して次区間へ進む。private復元に必要なpayload等は別の許可済み保全先へ。コード/JSONをGitへ保存しただけでprivate波形が復元可能とは言わない

科学CPU処理を同時実行しない。モデルprocessの終了を確認して次の候補計時を開始する。import/build/初期化費とcodec費を分離する。

## 過去との非同一性

区間ごとのprocess/model再初期化でwarm状態/RNG列が変わり得る。各recordのseed、batch=1、thread=2、UTMOS抽出seed20261012等を新runで固定し、状態の初期化単位を明記する。旧120連続runやtorch2.5 pilotと同値とは主張しない。初期化時間を品質の差やcodec速度へ混ぜない。

現quality_backends.UtmosLocal.scoreを静的確認したところ、各score呼出しでNumPy/Python/Torch seedを20261012へ再設定し、呼出し後にRNG状態を復元している。batch_size=1/num_workers=0/num_repetitions=1/bvcc/remove_silent_section=Falseも既存実装に固定されている。この既存関数をそのまま利用する。chunk化のための新RNG処理や新しい音響数式・合成処理は導入しない。runtime/初期化/warm状態は別のため、旧runとの全体同値や速度同等は依然として主張しない。

## 欠測と終端

区間receiptは予定12件×全方式×条件について、measured/failed/unsupported/not_applicableのいずれかと具体的reason_codeを必須にする。起動失敗・中断・pendingは終端成功へ変換しない。品質モデル起動失敗は全予定recordの失敗を明示できる新routingを設計するか、修復まで当該区間を未完のまま保持する。

診断stage失敗と波形生成失敗を区別する。上流native参照decode失敗が後続条件をblockedにした場合、その因果を保持する。運用中断・process消失・出力衝突・Ctrl-Cは別履歴とし、成功再試行後も削除しない。

各attemptは新しい番号で保存し、元失敗やreceiptを上書きしない。再試行後の採用recordはrun-plan内で固定した選択規則に従い、その履歴全体をprivate監査できるようにする。

## 公開checkpointと最終集約

checkpointは『12/120、区間終端、全体未完』と明示し、順位・採否・全体平均の結論を付けない。公開checkpointへ投入するrecordの自由文/path/command/tracebackを直接転記しない。公開数値・支持数・理由code・許可済み例外種別・数値診断だけをallowlistで出力する。

10区間すべてのreceiptとsource/plan同一性、重複なし・欠落なし、全予定ケース×軸の終端を確認した後だけ全体validated_end。最終集約は区間平均の平均ではなく全recordへ戻り、話者平均→話者等重み、現PML pairwise支持、全方式common支持、固定bootstrap seed20261014/2000反復で行う。途中未完軸を順位化しない。総合点・平均順位を作らない。

feature/readout別train120は通常71軸・編集品質保存後の別stageとして計画する。通常品質の実行を全train完了へ依存させない。

## 出自・権利

本追加は独自の評価入出力・来歴検証コードのみ。候補合成アルゴリズムや第三者モデル実装を含めない。既存repoの関数をimportして評価数式を利用する場合、既存の出典・依存ライセンス記録を維持する。repoルートの包括LICENSEは現在確認できないため、第三者への新しい再許諾文面や外部codeの転載を追加しない。原音/短音声の公開判断は別の既存掲載規約に従う。
