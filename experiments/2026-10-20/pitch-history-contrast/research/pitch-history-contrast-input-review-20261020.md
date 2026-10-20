# 履歴対比 source/input package：独立入力レビュー

2026-10-20。対象 `/workspace/shared/pitch-history-contrast-source-review-20261020/package` の INPUT-MANIFEST.json、PAIRS.json、PREPARATION-AUDIT.json、UPSTREAM-PINS.json、source/inputs.py。補助的にstorage.py、worker.py、CONTRACTを読んだ。候補コードのimport/実行/tests、BF/r/exp/log、対比減算・科学結果集計は行っていない。独立したstdlib JSON/hash/整数・保存bit比較のみを使用した。

## 結論

**固定100組の保存データと参照対応はPASS。原producer sourceの本文に依存する二前提は未検証であり、全前提を独立確認済みとしての最終入力PASSは保留。**

未検証なのは、観測hashの正確な生成対象・前処理位置、および各条件の共通初期状態への再初期化である。packageは元run.pyのSHAと説明を持つが、元本文を持たない。親側にも対応SHAの本文が見つからず、親がCloudへbyte-identical原sourceの取得を依頼する方針を確認した。別SHAのrun.pyで代用しない。

これは候補実行や新測定が必要という意味ではない。元本文をpin照合して読むだけで解消できる証拠不足であり、保存データの不一致や操作拒否ではない。原source受領まで、Cを原処理の因果順序対照として十分裏付け済みとは表示しない。

## 独立確認した保存物

以下の既存親保存物を INPUT-MANIFEST の全memberサイズ/SHAと照合し、一致した。

- selected: `pitch-bf-selected-input-review-v1-20261020`。
- index: `pitch-fixed-candidate-source-review-20261020/pitch-fixed-bf-index-20261020`。
- stage2: `pitch-stage2-results-review-20261020/package`。

元selected ZIP bytesの今回の再取得・再hashではなく、その全pinned展開memberの独立照合である。consumer-local絶対pathの実在もこのshared環境から確認したとはしない。元NPZ/波形は未同梱・未読であり、新しい波形同一性測定をしたとの主張はしない。

PAIRS.json のSHAは INPUT-MANIFEST の
`b55ecd52d3d4cdac26e2656890b77d3499bbc213e12f06dd2d88ba0b7d622aaa`
と一致する。

## 全100組の独立照合

1. pair_id0..49はH、frame53..102、E-U minus U-U。pair_id50..99はC、frame0..49、E-U minus E-E。台帳の固定順・両向き・範囲に不一致なし。
2. H49はsecond_complete、C48はfirst_complete。paddingはH102とC0/1の3件で、main/padding区分が一致。
3. 全pairの両側line_1based/frame_index/condition/frame_idが実stage2行へ正しく対応。両側time_secondsも保存値同一。
4. 両側stage2 observation_sha256、PAIRSのhash、selected frames.jsonの原字段hashが全件一致。padding102も個別に確認した。
5. 各側20参照の候補軸が48/148×K1..10であり、PAIRS.unique_ids、index unique、stage2 uniqueのK/r_bits/S_bits、selectedのcod/logBF bitsが一致。異なる条件のreference_id自体を同じと誤要求していない。
6. 全prior pointerについてselected archive hash、member hash/name、line_1based、fieldが原入力と対応。
7. staticの参照行は各側の正しいcondition、frame0、f_index、Kであり、両側initial_prior_payload bitsが一致。単にframe_id=0という弱い条件だけでなく全identityを独立確認した。
8. C全件でA prediction_prior bitsとB log_prior bitsがそれぞれ条件間一致。Bの参照行もcondition/frame/f_index/Kを独立確認した。AとBを同じpriorとは見なしていない。

以上はPREPARATION-AUDITの固定数・同一性項目と一致する。Dやgの差・interactionを計算したものではない。

## source/inputs.py の静的評価

Readerは全ZIP bytes/SHA、全member集合とhash、重複/unsafe memberを検査する。receive/premiseは対象frameの重複・不足、候補軸、unique対応、原hash、prior pointer、static/C prior bitsを検査し、不一致を例外にする。固定sourceとinput pinを併用する今回のデータ経路には、確認した範囲でjoinの阻害誤りはない。

ただしruntime検査の強さと独立確認範囲は区別する。

- B行はidentityを読込むが、premiseではその全identityを明示比較していない。
- static行はframe0とbitsを比較するが、condition/f_index/Kを明示比較していない。
- ref配列の添字とreference_id、index unique添字とunique_id等の一般的な自己整合を全て再検査するvalidatorではない。
- stage2 receipt/stdout比較は通常のPython等値を使うため、一般にbool/intなどの型差拒否を保証しない。

今回のimmutable入力については上記identityを独立検査し、receiptの実型も読取確認したため、それだけを理由に今回データをblockingとはしない。別データへの再利用保証ではない。防御的な検査追加を行う場合はsource hash変更と再レビューを要し、無断で変更しない。

## stage2完了証拠

pinned outer-endはoverall_success=true、reaped=true、exitcode=0、signals空、elapsed_seconds=9.089476447999914。receiptはcomplete=true、worker_reaped=true、worker_exitcode=0、worker_termination_unknown=falseであり、worker receiptはunique_rows4180/frame_rows309、complete=true、stage1_all_owners_adopted=trueを保存している。

receiptのsource SHAは
`036bd46cc3bb33999040810c5a05df864ccedad68451cd01f00e3c215a298812`、
input manifest SHAは
`4531e90f76d1246f56162bb7a34f713be129310aff90d94054ef7edf2d819c31`
で既レビュー対象と対応する。これらの数値は保存receiptの転記であり、時刻差の再測定ではない。

## 残る証拠不足と最小解消条件

source-references.json は `/workspace/pitch-prior-history-job-20261020/run.py` の
SHA `852c6faf72398e196b1ce969a974739ba94c4eb56a48f38d0b9504b4ae81d3fe`
を確かに記録する。CONTRACTとPREPARATION-AUDITは、そのrun.pyがraw common-scaled noisy inputのnative float64連続400標本、zero padding込み、demean/window前の `y.tobytes()` をhashし、各条件でFilter()を独立初期化すると述べる。しかしSHAだけからその実装内容は導けない。

元inputs.jsonには共通雑音SHA、common_scale等の生成記録が存在し、今回親保存memberとhash一致した。これは生成来歴のmetadataを支持するが、実際のhashコードや初期化位置の本文確認の代わりにはならない。

最小解消条件:

1. 上記SHAにbyte一致する元run.pyを取得し、hash対象配列の構築、dtype/順序、padding、前処理位置、各条件のFilter初期化位置を読む。
2. そのrun.pyが初期状態を外部moduleに委譲し、本文だけで共通状態が確定しないなら、該当定義のpinned sourceまたは既検証原資料まで確認する。必要以上の全repo取得や実行は不要。
3. inputs.jsonを同梱する場合、既存pinとbyte一致を確認。Cのprefix同一性と初期化の主張を原sourceの範囲に限定する。
4. 元NPZ/波形を再生成・再測定せず、「原hash metadataとproducer sourceに基づく確認」である留保を維持する。

全grid/VUV/内部全状態一致、未来情報漏洩不存在の一般証明、Hの機構別因果効果、音質改善はこの入力レビューの結論ではない。
