# AR3 + D1 保存観測の読める範囲

2026-10-21。新しい尤度・DP・backend・品質計算なし。stdlibのZIP/bytes/SHA/JSON読取だけで、比較表の全12行を元のpost_diagnostics.jsonと照合し、各analysis_diagnostics.json内のf0診断との完全一致も確認した。旧L/Fは別保存のD1 deliveryと、新artifact内の単一入れ子参照・locator双方で一致。全行で全無声fallback=false、resampled=false、post外側件数=0、返却frame数=raw frame数だった。

## 実際に一致した記述値

順は「旧white D1 → 新AR3 D1」。clampは下記の補間後・D1前の件数である。

- 0008 L: raw無声47→86、clamp443→313。F: 48→86、456→320。各1200frame。
- 0011 L: raw無声75→110、clamp395→275。F: 75→109、427→288。各1200frame。
- 0032 L: raw無声24→36、clamp332→276。F: 24→34、339→274。各818frame。

全6対でclamp件数は減り、raw無声件数は増えた。これは同じ入力・時計・D1/seed/backend条件で得た保存物の記述であり、「真の低F0誤りが減った」「音質が上がった」という結論ではない。

## 二つの件数は違うものを数える

raw_unvoicedは補間前のraw F0<=0件数。今回のL/Fではgate=0に対応する選択結果の0であり、生理的な無声の真値やexact-zero入力窓の件数ではない。

clipped_framesは、その0を正のraw F0で時刻補間した後、65..700 Hzへclampする直前の範囲外件数。端では最初/最後の正値が使われる。全無声の場合だけ65 Hz一括fallbackだが、今回は全12枝で発生していない。したがって「0をそのまま低F0として数えた件数」でも「正のraw F0<65の件数」でもない。元から正で低い点と、元は0で低い値に補間された点が混在し得る。固定L/F支持の正値は最大500 Hzなので、ここで問題になるのは下側65 Hzとの関係である。

この二つの集計だけでは、clamp減少が正の低q選択の減少なのか、gate変更に伴う補間先の変化なのか、その内訳は確定しない。post外側=0も保存postが65..700内に収まったという意味に限られる。

## 次に有用な保存配列の観測案（今回は未実施）

1. 同一frame上の旧→新gateの0→1/1→0対応と、両方gate=1のq分布を分ける。保存rawから、元から正の<65点と元0を補間した<65点を分ければ、clamp内訳を説明できる。再推定・再DP・再solveは不要。
2. 保存raw/postのpaired差を時刻別に示し、gate変更区間と変化の大きい区間を対応させる。品質は既定の共通採点区間の録音別paired生値と併記するにとどめ、追加alignment/gain/silence処理や因果分解を加えない。
3. 保存されたH0/H1別3原子log-responsibility/aggregateをvalid mask・unique物理窓対応で記述する。H1はq,K周辺化後で、selected-qの原子責任度ではない。重複anchorや重なる400窓を独立標本にせず、真noise係数・F0/VUV校正へ読み替えない。全(q,K,a)再計算・追加dump・第二passは不要。

独立監査の3gate合格は、参照bytes、保存選択、D1線形系/返却、params/native契約の整合性に限る。全(q,K,a)尤度の独立証明、真F0、品質改善、採用、全120完了を意味せず、監査自身のapproved_for_qualityはfalseのまま。first3は開発観測であり独立validationではない。

## 照合元

- 比較表: /workspace/shared/pml-ar3-d1-post-metadata-comparison-20261021.json
- 新delivery: /workspace/shared/pml-ar3-d1-first-received-20261021/delivery.zip、SHA256 dcbcc49b9cffcded4188adcb32bf61c068344ebf767c76c8bb3591de0506fbe2。
- 旧D1 delivery: /workspace/shared/pml-d1-first-received-20261021/delivery.zip、SHA256 43ffc10cdcdd739fb6f0583287af787a39d17050f09a801abe1aa1bd4ec0a21f。新native内 references/prior-delivery.zip とbyte完全一致。
- 実監査verdict: /workspace/shared/pml-ar3-d1-first-independent-audit-20261021-v2/verdict.json、SHA256 d81cdc4b1874d818ad520fb1e0dcf8e46b343204b1e265b72a798111569ad352。
- 定義: final native first_difference_post.py のraw_unvoiced計測→正値補間→clipped_frames計測→clamp→D1の順序。保存JSONの読取・静的source確認のみで、新しい配列計算はしていない。
