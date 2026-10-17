# 終端成果の表示専用組立て

全件確定後の保存値を、日本語・システム設定連動のlight/dark表示へ接続する準備コード。標準ライブラリと同じディレクトリの表示モジュールだけを使用する。実入力・結果・音声・公開registryは含めていない。

## 表示の範囲

- 入口は現PML・候補・WORLDの代表MOSと承認済み固定短音声から始める。通常品質71軸＋編集8軸の原HTMLは変更せず、そのまま複製してリンクする。全79軸を再実装しない。
- 特徴ABX・読み出し、費用は別ページにする。通常順位は保存整数だけを表示し、特徴順位はnullのまま保持する。
- 特徴の単独支持の定数train平均基準、次元数、定数次元数、行列rankを引用する。対応支持と単独支持を混ぜない。
- 未保存項目は「保存なし」。全体予定120録音・40話者、ABX4960三つ組を省略せず、欠測をゼロにしない。
- 費用の原状態 `partial_derived_preparation_not_final` を維持し、保存範囲を別注記する。速度順位やcodec合計時間は作らない。
- 統計・順位・音声の再計算、原HTMLの変更、Pages一覧への登録は行わない。原HTMLには軸単位の深いリンクがない制限を明記する。

## 入力と完了条件

全10区間の `chunk_validated_end`、全120録音・40話者・79軸の正式集約、特徴の必要終端が揃うまでHTMLは生成しない。原集約・原HTMLは既存の評価工程で作成する。候補採用は未決定、現baseはPML `pml-lowband-fwcep60-v1` のまま。

入力manifestは `schema_version: 1`、`scope: terminal-presentation-only`。`sources` の各行は `id, role, path, sha256, bytes` の5列で、次の40入力だけを明示する。

1. 公開元8個：idとroleが同名の `plan`, `ordinary_summary`, `ordinary_html`, `axis_metadata`, `feature_public`, `cost_report`, `audio_manifest`, `audio_attribution`
2. 区間保存20個：role `checkpoint` のgzip10個と `checkpoint_storage` の保存対応JSON10個。`checkpoint_bindings` の `checkpoint_id, storage_id` で結合する
3. 特徴終端11個：role `comparison_summary` が候補3view、`readout_summary` と `abx_summary` が候補3view＋PML1viewずつ
4. 費用監査1個：id/role `cost_coverage_audit`。原費用JSONと同一plan、候補/PML/WORLD各10区間の終端receiptのSHA、原coverageを結合した監査

`publication_approval` には公開元8roleと確認済みSHAを対応させる。`recorded_at` には原集約・原HTML・費用監査の実記録日時をUTC offset付きで保存する。日時を推定して補わない。

`ordinary_html_binding` は `html_sha256, summary_sha256, plan_sha256, metadata_sha256, approved_audio_manifest_sha256, renderer_audio_manifest_sha256` を持つ。元report用音声manifestと公開用manifestは別形式として扱う。

公開音声manifestは `schema_version: 1`、`scope: approved-fixed-native-clips`。固定2録音×原音/PML/WORLD/候補の8組について収録または上流生成失敗を記録する。収録音声はWAVのdata URI、native、先頭0、16kHz mono、最大32000samples、CC-BY-4.0に限定する。凍結HTMLの録音/方式captionと音声SHAを照合する。別録音への差替えや未準備状態の失敗扱いはしない。

入力の内容・公開範囲・元成果との対応は事前に確認する。コードのSHA照合や簡易path検査だけで、入力の科学的正しさや公開可能性が証明されるわけではない。元データに存在しない条件別予定数・失敗理由件数は推測しない。必要なら別の件数付録で、既存raw行の分類と分母を確認して保存する。

## CLI

Python 3.12以上。リポジトリルートからscriptとして起動する。以下の入力名・SHA・出力名は説明用で、実入力を作る例ではない。

    uv run --no-project --no-sync python scripts/report_assembly/assemble.py \
      --manifest input-manifest.json \
      --manifest-sha256 <確認済み64桁SHA256> \
      --output-dir output-new \
      --log-file assembly-new.log

このディレクトリ内では `python assemble.py` と同じ引数で起動できる。既存出力への上書きは禁止。出力先の親だけは存在させ、ログは新規ファイルとして公開出力外に置く。入力は読み取り専用で、前後にSHA/bytesを照合する。各公開ファイルは10MiB未満。異常はスタックトレース付きで記録し、部分出力の存在だけで完成扱いしない。

## 出力と確認範囲

出力は入口・特徴・費用の3HTML、元8ファイルの同一bytesコピー、特徴scalar付録・費用範囲・来歴の3JSON。来歴には入力と組立てソースのSHAを残し、ローカル入力path、密配列、係数、traceback、payloadは公開しない。14成果物のmanifestと、そのSHA sidecarを最後に保存する。入力manifestとログは公開しない。

準備段階でソースAST、cached Ruff、ソースサイズと独立静的レビューを実施済み。実行・HTML生成・テスト・smoke・科学処理・Pagesビルドは未実施。今後の実入力レビュー、Pages一覧adapter、公開と公開後の実URL・音声・明暗表示の確認は別工程とする。
