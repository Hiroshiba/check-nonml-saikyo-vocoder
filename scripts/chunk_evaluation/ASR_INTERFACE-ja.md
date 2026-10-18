# 区間ASR実行の接続仕様

配置は `scripts/chunk_evaluation/run_asr.py`。同packageの `evaluation_io` が提供する `Context`、`ContractError`、`UpstreamUnavailable`、`add_arguments` を使う。科学処理を始めるには独立レビューと実行許可が別途必要。

起動引数は `--plan --chunk --manifest --bindings --assets --output --dataset --authorization`。共通引数に `--resume-authorization` を含む。`--dataset` は公式転記・切出し位置を含む既存形式の120件の `entries` JSONで、bindingsへ固定しておく。全体120録音・40話者の計画とID・話者・長さを照合し、`source_samples == excerpt_samples and excerpt_start_sample == 0` の55録音32話者だけを認識する。残65録音は原音認識・方式認識・評価とも `not_applicable/full_transcript_unavailable`。

`ctx.cases` は現在12件だけ。各件は `case/speaker/common_samples/reference/outputs`、`outputs[method].native` と `reference` は `path/sha256/samples/sample_rate/status/reason` を持つ。pathは共通IOで絶対化され、`ctx.wave` は凍結した全長float64波形を返す。ASRではcommon windowへ切り詰めず、再標本化・整列・ゲイン・無音除去・クリップをしない。

assets JSONの `asr` は `directory/model/revision/files` を持つ。directoryはassets JSONの親基準、各実ファイルはbindings inventoryにも必要。modelは `facebook/wav2vec2-base-960h`、revisionは `22aad52d435eb6dbaf354bdad9b0da84ce7d6156`。filesは7公式ファイル名→SHA256の辞書。既存の公式取得記録と同じハッシュをrunnerにも固定し、開始時と終了時に照合する。別モデルへの置換・ダウンロード・remote codeは行わない。

原音と各方式の全文nativeをCPU、2 thread/1 interop thread、float32、greedy CTC、1波形ずつで認識する。原音PCMは公式datasetの `decoded_pcm_sha256` と照合する。CER/WERは既存 `vocoderbench.assessment.acoustics.content` をそのまま使用し、NFKC/casefold/空白整理、CER空白除去、WER空白tokenization、原音CER≤0.20を維持する。ゲート超過では主値nullと明示statusを返し、CER/WER生値は `measurement.scores` に残す。

raw summaryは12件×予定方式の `metric=asr/condition=native` 行。各行はcase/speaker/method/status/reason_code/value/measurement、対応認識のSHAを持つ。原音は認識証跡として保存し、主計画にない原音ASR軸を追加しない。初期化失敗は全対象行を `failed/model_initialization_failed` とし、対象外65件の除外理由は変更しない。

`ctx.record` は行を保存、`ctx.finish(rows)` はconfiguration・initialization・全recognitions・全sidecars・行・ログを再帰inventory化し、入力/資産/ソース/runtime/生成receipt/全終端statusを再照合してschema2の `stage_id=asr` receiptを発行する。中断・契約不一致ではfinishへ到達しない。運用再開の新attemptでは監査済み終端個票・認識を同bytesで引き継ぎ、未完分だけ処理する。過去attemptを上書きしない。共通IOが既存検証済みattemptを返す場合だけ明示ログを残して推論せず終了する。

この追加ではテスト・スモーク・科学評価を行わない。AST解析とキャッシュ付きRuffだけを使用する。候補実装のimport、workspace固定path、私的保存IDは含めない。

追記：科学失敗の救済再試行をしない。既終端stageは失敗も含めそのまま使用する。運用中断のみroot監査済み再開許可で未完recordを継続し、過去terminal個票・認識を再計算しない。初期化の科学失敗は再開をまたいで固定する。OSError/MemoryError/KeyboardInterrupt/契約不一致は終端失敗へ丸めずstage全停止。
