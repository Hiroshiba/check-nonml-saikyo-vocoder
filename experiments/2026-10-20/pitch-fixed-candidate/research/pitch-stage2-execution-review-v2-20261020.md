# 固定候補stage2 v2：実outer証拠連携の最終静的レビュー

2026-10-20 UTC。対象 `pitch-stage2-source-review-v2-20261020/package`。v1差分、source/manifest読取、AST、既監査3ownerの実保存JSON比較のみ。候補import/実行/tests、科学算術再計算なし。

## 結論

**source静的レビュー通過。今回変更のblocking issueなし。** 実保存outer-endとstdoutを直接結ぶ方針は適切で、過去receiptへの架空hash字段追加や事後binding receiptは不要。完成input manifestの原path/bytes/SHA/member/selectorsを別途独立確認し、親の開始指示までは起動禁止。

## 実証拠連携

`adopt.evidence_bytes` は別pinされた外側fileのbytes/SHAを読取後再確認し、owner ZIPの指定された完全member名の原bytesと一致させる。prefix-relative名とfull member名を混同しない。source採用前のArchive検査はZIP全体SHA、重複/危険member/容量を従来どおり拒否する。

stdoutは厳密に1 JSON行、object、type=external_post_fsync、success=true、finite elapsed<900を要求。stdoutと親waitはUTF-8・非標準NaN/Infinity拒否・duplicate key拒否で読む。

親wait selectorのpost_fsync_observationは実recordの `['external_post_fsync']` に限定。sort_keys/compact/allow_nan=falseのcanonical JSON tokenでstdout objectと完全一致を要求する。boolとint、intとfloat、signed zeroの違いをPython dict同値だけで混同しない。両file自体の原bytesは別SHAとZIP内一致で保持し、canonical比較をraw書換えには使わない。

3owner実保存値を別の標準ライブラリ読取で確認した。全てstdoutは1行、親保存external_post_fsync objectと型・数値表現込み一致、returncodeはint0、external_reapedはbool true、elapsed_at_real_waitおよびstdout elapsedはfloatで900秒未満。候補関数を呼び出して確認したのではない。

従来の親実exit/reap/elapsed、内部/外部終了・fsync、owner全完了、journal整合、source/index/input pins、unknown拒否は維持される。

## 差分とpin

code変更はadopt.pyとarchive.pyのみ。arithmetic.py、worker.py、run.py、output.py、dependency.py、inputs.pyはv1とbyte同一。科学算術・支持・一回性・300秒総wall/240秒科学deadline/512MiB/64MiB・partial保存・例外出口の変更なし。

SOURCE-MANIFEST SHA `036bd46cc3bb33999040810c5a05df864ccedad68451cd01f00e3c215a298812` は親指定値一致。24掲載filesと自己manifestの集合・全bytes/SHA一致。全8 Python sourceのAST解析成功。

## 完成input manifestの必須確認

各ownerに対し、archive SHA/bytes/prefix、EXTERNAL-MANIFEST SHAと、以下のconsumer-local原file pinを固定する。

- external_stdout：実owner ZIP内 `outer-owner-N/external.stdout` のfull member名・bytes/SHA・絶対path。
- parent_wait：実owner ZIP内 `outer-owner-N/outer-end.json` のfull member名・bytes/SHA・絶対path。
- selectors：exitcode=`['returncode']`、reaped=`['external_reaped']`、elapsed_seconds=`['elapsed_at_real_wait']`、post_fsync_observation=`['external_post_fsync']`。

これらは今回実recordに存在する字段である。異なるZIP prefixならfull member名を実inventoryから確定し、推測しない。source側の型検証が全一般化ケースを担保するとの過大主張はせず、固定実recordのint/bool/float型を今回のように入力レビューでも確認する。

現source通過は、未完成templateを実行可能にしたことを意味しない。完成manifest期待SHAの独立承認、stage1全owner監査、環境割当、外側実wait監督と別のstage2一回開始指示が揃って初めて起動可能。
