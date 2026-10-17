# 区間保存JSON形式2

公開候補の配置案は scripts/chunk_evaluation/。__init__.py、chunk_contracts.py、freeze_chunk_plan.py、chunk_checkpoint.pyを同じpackageへ置く。既存vocoderbench.logging_utilsを利用し、警告・例外を通常ログへ保存する。実行方法はrepo rootから uv run --locked python -m scripts.chunk_evaluation.freeze_chunk_plan / chunk_checkpoint。

## run-plan.json（公開可能）

- schema_version: 2、scope: fixed120-chunked-evaluation
- cases: 元固定集合の順序で120件。case/speaker/input_sha256/samples/sample_rate/common_samplesのみ
- chunks: id=chunk-01～chunk-10、case_ids=順序通り12件
- methods: 候補/現PML/WORLDの公開識別子。originalは含めない
- formal_base: pml、formal_base_version: pml-lowband-fwcep60-v1
- candidate: ahm_cartesian_node_editor_v1
- axes: id/condition/direction/methods。主native71軸＋編集群。原音originalは1.native_mos/nativeのmethodsへだけ追加
- frozen_digests: cohort/evaluator/generation/runtime/assets/preprocessingのSHA256。generation/runtime等は複数方式・環境の固定manifestを束ねた親manifestのSHA
- required_stage_receipts: candidate-generation、pml-generation、world-generation、acoustic、erb、scoreq、utmosv2、speaker_ecapa、asr、pitch等の正確なstage ID配列。runner分割を含め開始前に確定
- execution: chunk_size=12/scientific_parallelism=1/rank_before_all_chunks=false/generation_before_quality=true

freeze_chunk_planは --cohort（既存public input-manifest形式）、--settings（上記methods/axes/digests/stages等）、--outputを指定する。privatepath等の余分なsettingsキーは出力へ転載しない。

凍結順序は各source/runtime/model設定→各manifest digest→run-plan→実行許可（plan/source SHAを参照）。source内へplanのSHAを書き込んでhash循環を作らない。

## stage receipt（private）

schema_version=2、stage_id（区間集約receipt内の辞書キーと一致）、validation_state=validated_end、run_plan_sha256、chunk_id、case_ids、frozen_digests、artifacts=[{path,sha256}]。pathはreceipt所在directory基準、絶対pathもprivate領域内で許容。生成stage固有のmethod/source/input/runtime/36condition rows/ログhash等を別fieldとして保持してよい。

stage receiptは、対応する生成/評価workerがsource/runtime/input/asset/出力/全予定statusを実照合した後だけ発行する。checkpoint側の一般artifact検証だけで、そのreceipt作成者が音声科学契約を満たしたことを独立に証明するとは扱わない。生成器/評価器/receipt作成adapterを一体として独立レビューする。

## 区間集約receipt（private）

schema_version=2、validation_state=validated_end、run_plan_sha256、chunk_id、case_ids、frozen_digests、stage_receipts={stage ID:{path,sha256}}、rows_path、rows_sha256。

rows_pathのJSONはrows配列を持つ。各rowはcase/axis/condition/method/status/reason_code/value、必要ならsupport_numerator/support_denominator（必ず両方、0以上の整数、分子<=分母）。全12件×axes指定methodsを必須にし、失敗/unsupportedも行として残す。valueはmeasured時に有限数、非成功時null。pendingは区間終端不可。

区間集約adapterは各quality stageのraw summaryを既存定義でaxis行へ展開し、rowがstage証跡に由来することを照合する責任を持つ。このadapterと実指標runnerは別途復元/実装・レビューが必要で、今回の保存codeのみでは科学評価を実行できない。

## 公開checkpoint

chunk_checkpoint --plan ... --receipt ... --output ... で固定列だけへ射影する。source_receipt_sha256は来歴digestとして保持するが実receipt path/保存サービスIDは公開しない。全体未完・12/120・rankings=null・adoption_decision=nullを明記する。自由文reason/例外/command/privateファイルを全コピーしない。

checkpoint自体をGitへ保存したcommit・SHAをrootが確認してから次区間へ進む。これと独立して、再開用のprivate波形/payload保全を確認する。公開checkpointだけからwave/payloadを復元できるとは説明しない。

## 全体終端

chunk_checkpoint --plan ... --checkpoints（全10個）--output ... で全case×axis×methodのcoverageと同一planを検証し、全recordを集約器へ渡す。順位やCIはここでは計算しない。後段の既存集約規則で話者等重み・現base対応差・支持数・全方式common・CIを計算する。

公開checkpointは信頼する保存対象であり、悪意ある改ざんへの認証機構を追加するものではない。公開commit SHA/各checkpoint SHAを保存して復元時に照合する。追加security機構は導入しない。

## 設定の独立レビュー

形式validatorはnative71軸の件数を確認するが、各軸が既存71軸と同じ数式/ID/方向であること、編集群の網羅性、PMLと候補が各軸の予定methodsへ入ることまでは件数のみから証明できない。settingsとraw→axis adapterを開始前に独立レビューし、既存定義との一対一対応・全予定群を別途確認する。設定が揃わない段階で実行承認済みとはしない。
