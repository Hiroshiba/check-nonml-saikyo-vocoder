# 独立trainによる音素距離と属性読み出し（復旧後の新run）

この計画と欠落していたtrain/readout/ABX入口は新規実装であり、旧sourceの復元ではない。旧runの数値、raw、固定manifestを会話の要約から生成しない。全長音声・表現の多GB永続保存方針が確定するまで、音声取得・encode・target推定・DTW・学習・bootstrapは開始しない。コードのテスト・スモーク・自己検査を追加しない。静的解析と差分レビューのみを準備中に行う。

## 対象と入力契約

- 主評価は凍結LibriSpeech test-clean 40話者120録音、各先頭最大6秒。独立trainはdev-cleanの40話者120録音、各話者3録音。選択に評価値・特徴・音声内容の良否を使わない。
- 新trainの具体IDは別の選択manifestを測定前に固定する。旧trainの入力SHAや120 ID集合との一致を仮定しない。入力/選択manifestのSHA、選択規則、元索引/ラベルSHAを契約へ保存し、主群との話者・発話・ID・入力SHA重複を拒否する。
- train manifestはschema_version=1、split=dev-clean、空でないselection_ruleとselection_inputs_sha256、entriesを持つ。entriesはid/speaker/source_utterance_idを含む。inputs.jsonは同じID/話者順で既存のpath/sha256/samples/sample_rateを持つ。新runの入力契約をfreezeした後で既存成功値と違う条件へ変更しない。
- 120/40未満のtrainへ勝手に縮小して尺度やモデルを学習しない。特徴抽出失敗と未到着を区別し、train全件成功がなければpending/incompleteとする。属性targetだけが未定義の場合は属性ごとに有効train数/ID/話者を保存する。
- 全予定trainが終端になった時点で、120件すべての特徴校正に成功した方式集合をstatusだけで一度固定する。1方式以上欠ける場合、全8主群の値/順位はnullのまま残し、成功方式すべてに共通する評価録音/三つ組だけの補助値・CI・分母・除外理由を別欄へ保存する。補助順位は作らず、値の大小で方式を除外・再選択しない。同じrun内でこの固定方式集合は変更しない。
- 運用上、全trainの再試行方針と許可済み再試行を終えてからassessを起動する。assessによる方式集合freeze後にtrainを再試行して構成を変えることはできない。その場合は旧結果を保持した別runとして固定し直す。

## 共通の特徴出典

8方式はHNM、WORLD Harvest、FACodec、HiFi-Glot、GOLF-ff、SiFi-GAN、LLSM2、MagPhase。各固定adapterの実decoder入力に由来する連続特徴を使い、離散code番号をEuclidean座標としない。全native frameを用い、任意downsample・評価群での次元選択・評価群での尺度学習をしない。

MagPhaseのlf0=-1e10は無声カテゴリであり、0の数値と別のvoiced maskに投影する。既知sentinel以外の無声値は拒否する。trainは各発話内frame等重みのfloat64平均と二次母積率を保存する。元float32 frame配列のNPY/hash/canonical SHAとshapeを記録するが、trainのdecoder payloadや全frameを保持したとは記載しない。

原音区間のABX時刻はHNM/WORLDの保存時刻、固定格子方式のnative hopと原点0、MagPhaseの元analysis shift累積を使用する。録音長からlinspaceで伸縮せず、MagPhaseのlf0から再計算したdecoder epochは原音token境界へ使わない。このMagPhase readout時刻の修正は新runだけに適用し、旧sourceと同一条件と主張しない。操作応答用のadapter.frame_timesは維持する。

## #14 音素ABX

公式abxLSラベルの全triphone区間を、凍結原音の先頭6秒以内へ結合する。実際に三つ組へ使用する全録音について、公式配布PCMと凍結原音の元PCM同一性を別の照合manifestで確認する。公式未掲載や非使用の録音は理由・件数を別表示し、全120が公式配布に存在すると仮定しない。onset <= native frame time < offsetを採用する。無frame token、抽出失敗、距離失敗はnullで記録する。

旧runで予定されていたacross 4774三つ組/113録音/39話者、within 186三つ組/62録音/26話者は歴史的予定値にすぎない。今回のmanifestがない段階で現在値・実測分母として出力しない。新manifestにある予定三つ組と全8共通有効三つ組から、token/録音/話者数を別々に数える。

距離尺度はtrain120の発話等重み・発話内frame等重み母分散によるstd。std<=1e-12は1、他の次元重みはすべて1。固定Euclidean local cost、既存無制約DTWの累積cost最小pathとpath長正規化、最大2,000,000 cells。距離差abs<=1e-12の同点誤り率は0.5。これを制御音の時間合わせへ流用しない。

within/acrossを混ぜず、以下の3値を別に出す。

1. flat-stratum: 層=(条件,有向phone A/B,左右文脈,A話者,X話者)内三つ組平均→層等重み平均。
2. X話者macro: X話者内flat層平均→X話者等重み平均。
3. 明示nested: 有向phone対×文脈内の話者対等重み→phone対内の文脈等重み→有向phone対等重み。

三つ組単純平均は別の補助値でありflat-stratumと置換しない。nestedは本研究で明示した補助推定量であり、公式ZeroSpeech scorerとの厳密同値性は未検証。公式abxLS全corpusの順位とも呼ばない。

within/acrossの各conditionに実際に登場する全8共通支持話者集合を個別に作り、そのconditionの話者数だけ復元抽出するnode bootstrapを2000回、default_rng seed20261014で行う。同じconditionのdrawだけを8方式で共有し、異なるconditionの話者集合を混ぜない。層内値は固定し、within層はm_sを一度、across層はm_A*m_Xで重み付けする。Xmacroは内側A multiplicity（A=Xなら1）、外側X multiplicityを一度だけ使う。nestedはspeaker pairの重み付き平均後、支持のあるcontext/phone対をそれぞれ等重みとする。0支持は除外し、条件の支持が消えた反復はnull相当の未定義。各反復の支持数、有効/未定義反復、同じdrawのHNM差を保存する。

## #15 線形読み出し

各録音のnative frame平均から原音の独立推定属性を読む。対象はvoiced YINのln F0平均、全録音RMS dBFS、300–5000 HzのdB/octaveスペクトル傾斜。YINは80 ms窓/10 ms hop/65–700 Hz/threshold .15/rms_threshold 1e-5/prefilter 2000 Hz。傾斜とF0の適用外は理由つきnullとし、真の人間評定や手操作性の正解とは呼ばない。

属性ごとに有効train targetの録音meanをtrain-only平均/stdで標準化する。これはABXのframe母統計尺度と異なる。std<=1e-12は1。Ridge alpha=1を固定し、targetのtrain平均を切片とするSVD解。評価結果でalpha、次元、尺度、属性推定器を調整しない。属性ごとの係数/尺度/切片/有効train IDを保存する。train平均だけを予測する定数baselineも併記する。

順位は属性ごとの全8共通有効評価録音に限定し、録音絶対誤差→話者内平均→話者等重みMAE。録音等重みMAE/RMSEは補助値。評価話者を2000回復元抽出し、同じdrawを8方式へ適用してHNM paired差を保存する。trainの再学習を含む不確実性ではない。

## 順位・保存・実行

低いほど良い指標の点推定だけを競技順位にする。同点判定はabs1e-12/rel1e-9、ソート済み各同点群の先頭値に比較し、連鎖的に許容幅を拡大しない。欠測に順位を付けず、CIの重なりで同順位にしない。95%百分位区間は条件付き記述区間であり、多重比較未補正。

全8共通群を保つためmeasure(method)入口は合同計算を行う。共有出力はfeature-assessment/abx-rankingsとreadout-rankings、各方式の既存results.json入口にも共有結果を保存する。入力契約、特徴記録、train母統計、target、係数、距離、層、共通三つ組、bootstrap配列をSHAでつなぐ。raw生成・測定は保存承認後の正式研究だけで行う。native速度phaseの排他gateより後に評価を実行し、trainはgate取得後に既存ML直列lockを取得する。

trainと既存人間評定特徴の成功batchは、正式process開始時のsource/input snapshot、完了時のmean/moments/記録/契約SHAをreceiptとして保存する。終了コード0だけでskipせず、実成果の存在・SHA・source契約が一致する場合のみ省略する。成果が失われた場合は復旧待ちを明示し、成功扱いにも無言の再推論にも変えない。中断時は起動したprocess groupの終了を確認してからML/gate lockを解放する。

既存#13の独立train尺度入口もこの新manifest契約へ接続する。旧train SHAを新runへ強制しない。1方式以上の固定120校正が終端失敗なら#13の全8主値はnull、失敗分母と理由つきの終端結果を保存する。同じstatus-only固定成功方式集合に共通の人間評定対だけを補助群として測り、値/CI/分母を別保存する。補助順位は作らず、HNMが集合外ならHNM差もnull。#13統計式自体は回収済みのものを維持し、入力契約改修を旧凍結sourceと同一とは扱わない。
