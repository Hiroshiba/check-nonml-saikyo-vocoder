# 解析・編集・復号の費用を分離する集約仕様

固定120録音の保存済み測定だけから作る派生集計。途中結果は常に「部分測定・最終値ではない」とする。この補助プログラムは最終全体結果を認定しない。音声、完全特徴量、候補コード、私的なファイル位置を出力せず、数値・状態・支持数・科学的同一性のダイジェストだけを出力する。

## 分母と支持

秒数と実時間比（RTF）は分離する。RTFの分母は各録音を実際に解析した原入力の全抜粋時間。品質比較用の共通先頭区間を分母にしない。各方式・条件・観測項目ごとに平均と中央値を記録し、予定分母120、観測支持数、未観測または失敗数を併記する。失敗を0秒に変換しない。成功音声数は条件の状態列から、費用の観測支持数とは別に把握する。失敗までの処理に保存された費用も観測として残る場合があるため、観測支持数を成功支持数と呼ばない。

## 候補

正式nativeはCartesianの無変換条件（semitone=0）。実験のラベル「Cartesian q=0」を維持するが、ピッチ倍率のq=1とは別の意味である。

- 解析: air_secondsとfinal_fit_secondsを個別表示。進捗診断の負荷を含み、全解析の純時間ではない。encoder total_secondsは入力読込、hash監査、保存、診断等も含むためcodec速度欄に使わない。
- 初期F0: 16→24 kHzの再標本化、DIO/StoneMask、LLSM full encode、refined F0 routeを個別に表示。LLSM全解析を実際に実行した経路であり、F0のみ抽出した理想費用ではない。export_saveとloadは別I/O欄。重複範囲を推測して総和しない。
- 保存: encoder save_secondsだけが独立した保存観測。prepare secondsは特徴量読込・準備・保存を含む複合観測。
- 編集: 正式経路の独立編集時間は未測定。total−renderの差には読込・検証・保存等が混在するため編集時間にしない。
- 復号: render_seconds_including_profileは正式経路のレンダラー区間。profileによる観測・コピー負荷を含む。純復号時間としては未測定。total_secondsは正式経路全体の観測値であり速度順位に使わない。
- parameter secondsは別実行されたパラメーター診断。正式編集費用に加算しない。
- native直接decodeのsecondsはq1比較用の参照診断費用。正式nativeの復号に混ぜない。

## 現PML・WORLD

保存されたanalysis、editor、decodeのwall秒とCPU秒を別々に集約する。load/saveはI/O欄へ分離する。候補は作業者報告では1スレッド（本集約では未照合）、PML/WORLDはcontractで確認した2スレッドの測定であり、同一実行条件による速度順位を出さない。モデル推論・モデル起動・処理起動・source hash監査の経過時間をcodec時間に加算しない。

## 特徴量の大きさ

候補の正式特徴量はpreparationで記録された完全payload_bytes。native解析段階の中間payload_bytesと分ける。PML/WORLDは保存されたpayloadの完全ファイルbytesを使用し、編集後payloadは条件別に分ける。各録音のbytes/sとbits/sを計算し平均・中央値を保持する。これは保存形式全体の量であり、波形の大きさ、診断ZIP、診断配列、実装コードを特徴量に含めない。共有モデル資産は個別payloadに加算せず別欄とし、独立した資産台帳がない現在はunknown（null）。0バイトとは主張しない。

## 出典と実行範囲

候補は終端確認済みchunk receiptとcase receiptのSHA対応、固定入力SHAを確認してscalar投影を読む。compact後に原JSONがZIP内だけにある場合は、原バイトSHAと長さを記録したlossless receiptの同一性を使用する。集約時にZIP全体を再解凍・再検証したとは主張しない。既存のscalar投影と原JSON内容の再照合を新たに行う場合は、原JSONのbyteSHAを先に照合する。

参照は指定したsummaryのSHAと入力SHAを記録する。複数attemptを混ぜず、同一方式・録音・条件・費用の重複はエラーにする。出力先は新規ファイルだけを許し、既存科学生成物を上書きしない。科学コードのimport、音声の読込、モデルロード、encode/decode、推論、新しい測定、人工入力の試験は行わない。

参照のsummaryとcontractは同じattemptの終端receiptに記録されたSHAへ結合する。contractの凍結digestがreceiptと一致し、候補とrun planが一致することを確認する。参照のスレッド数はcontractから読む。候補のスレッド数は作業者からの報告値1を別属性に保持し、未照合の実測属性はnullとする。予定条件数は候補360、PML360、WORLDはnativeのみ120。再開時のprevious_encode_costsは再利用解析として項目名を分けて保持し、新規読込費との合計を作らない。
