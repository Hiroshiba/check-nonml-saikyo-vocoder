# 履歴対比入力レビュー v1：原producer証拠の追加確認

2026-10-20。対象 `/workspace/shared/pitch-history-contrast-source-review-v1-20261020/package/evidence/`。前レビュー `pitch-history-contrast-input-review-20261020.md` の証拠不足を限定的に再確認した。候補・producerの実行/import、tests、波形計測・再生成、対比減算は行っていない。

## 結論

**入力前提レビューPASS。前回の原producer本文不足は解消し、今回確認対象に残るblockerはない。**

固定100組の保存値同一性に関する前回PASSに、元sourceによる観測hash定義と条件ごとの同一初期化の確認を追加できた。source全体の実行安全性・算術レビューと別開始指示は別条件であり、本書だけで実行を開始しない。

## byte / pin の独立確認

EVIDENCE-MANIFESTの各記載だけでなく、既存selectedのsource-references.jsonに記録された元pathのbytes/SHAと照合した。

|証拠|bytes|SHA256|
|---|---:|---|
|producer-run.py|13416|852c6faf72398e196b1ce969a974739ba94c4eb56a48f38d0b9504b4ae81d3fe|
|model.py|6915|111c5bfda62595a3b5f01208741fc52303dc78c2569d9dbc889b399244c95955|
|inputs.json|44031|d4228d48c618046b37b0b793c66fd88cdd36c53ca108eee2eb41561480183977|

全3ファイルが一致。inputs.jsonは既存selected入力の同名memberともbyte一致。v0→v1のPAIRS.jsonとINPUT-MANIFEST.jsonもbyte不変であり、前回の全100組・20候補・prior bits・pointer照合を変更していない。

## 観測hashの定義

producer-run.pyのexecuteで、model.pyのFS=16000、N=400、HOP=160を使用する。各frameのcenterを0からHOPずつ進め、supportをcenter−N//2からcenter+N//2の半開区間とする。

各条件の `windows=np.zeros((len(supports),N))` はNumPy標準のfloat64・C順配列であり、該当範囲へxの切片を代入する。範囲外部分はzeroのまま。条件の各行yを処理する際、`hashlib.sha256(y.tobytes()).hexdigest()` をrow.observation_sha256へ保存する。行は400標本の連続配列で、native dtypeのbytesである。固定producer環境のlittle-endianという来歴は維持し、別環境へ移せば無条件に同じhashになるとは言わない。

hashはenergy計算・projection.costs呼出しより前に行われる。対象は共通scale済みの雑音付きraw窓であり、mean除去やwindow関数適用後ではない。model.pyのProjection.costsも入力をdemean/window化する処理を持たない。前回確認済みのpadding102を含む保存hash同一性に、定義の本文根拠が付いた。

これは元波形bytesを今回再読・再計測した確認ではない。保存hash metadataと、それを生成したpinned sourceの静的確認である。

## 入力生成・共通noise / scale

producerはblock8192、total16384とし、同じphaseからUを倍音2/3/4、Eを2/4/6の和として一度生成する。U-U=(u,u)、E-U=(e,u)、E-E=(e,e)を構成する。

noiseは条件ループ外でPCG64 seed20261020から一度生成する。同じnoise配列を全条件のcleanへ加え、同じgainを乗じる。gainはclean_power=1.5とnoise_variance=1.5/1000に基づく理論scaleで、各条件の実現RMSから別々に正規化する処理ではない。

inputs.jsonの保存記録はseed20261020、generator PCG64、NumPy2.3.5、common_scale=0.004589219874983008、noise_sha256=`4d26a372d694dd0b17c754c8b8f7e65fd564e65bdebe12d353e2992a826059f4`。このnoise hashは保存npyファイルのhashであり、frameのraw y.tobytes() hashとは対象形式が違う。値は保存記録の転記で、gainやnoiseを再計算してはいない。

したがってHの現在suffixは同じu/noise/scale、Cのprefixは同じe/noise/scaleを使う設計が本文から確認できる。各固定pairの観測hash一致自体は前回監査の独立保存物比較による。

## 条件ごとの共通初期状態

producerは `for name,windows in observations.items()` の各条件ループ内、frameループより前で `state=Filter()` を実行する。前条件のstateを次条件へ渡さない。

model.pyのFilter.__init__は同じFREQ/ORDERからtransition行列を作り、mass=None、null=0.3、memoryは全候補一様、memory_frame=None、last_update=None、skipped=0で初期化する。乱数や条件名への依存はない。最初のupdateでmassがNoneならH1 priorは0.7を全候補へ一様配分、H0=0.3とする。producerのlocal用initialも条件非依存である。

この本文は旧A producerのFilter初期化を直接裏付ける。別B実装の全内部状態を今回再監査したとはしない。CにおけるBの必要な選択prior bitsは前回100組監査で直接同一性確認済みであり、BをAのlog化または新方式再追跡と扱わない。

## 解釈の境界

Cは同じprefix入力・同じ旧A初期化・同じ処理条件に関する限定的negative controlとして裏付けられた。比較する保存20候補・prior字段の一致を、全grid/VUV/内部全状態の実測一致や一般的な未来漏洩不存在の証明へ拡張しない。

Hも旧履歴に関連する凍結prior全体の算術対比であり、memory/transition等の単独機構の因果効果ではない。元NPZ未読、人工選択309frame、重複窓・共通雑音、noncertifiedという既存留保は不変。
