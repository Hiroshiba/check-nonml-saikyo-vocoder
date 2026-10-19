# 生体構造・音響物理から見たclock/event表現

2026-10-19 UTC（2026-10-20 JST）。文献に基づく設計動機と限界。新しい音声実験は含まない。現在の選定と予定条件は[研究判断記録](README.md)を優先する。

## 1. 一つの時計で扱えないもの

口腔の閉鎖と声帯の周期的閉鎖は別である。口腔閉鎖中も声帯振動が続く場合があり、内圧・声道容積・壁の変化がその持続に関わる。閉鎖中を常に無音とする説明は不十分である。[Koenig & Lucero 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2651765/)

停止子音では、短い初期過渡、frication burst、その後の声門音源とformant遷移を区別する古典的モデルがある。ただし当該資料の確認範囲は公開abstractである。全ての破裂音を白色雑音一種へ置き換える根拠にはしない。[Stevens 1993](https://www.sciencedirect.com/science/article/pii/016763939390035J)

口腔の閉鎖・開放、圧力放出、jetの成立、声帯振動の停止・再開、伝達系の応答尾は重なり得る。VOTは相対時刻の一つで、全sourceの開始を一つにまとめる量ではない。音素ごとの固定ミリ秒テンプレートを本録音へ導入する判断はしていない。

## 2. 乱流の位置と周期変調

声門付近のaspirationと口腔狭窄由来のnoiseは、発生位置から口までの伝達が異なる。Birkholz & Jackélの複数位置sourceモデルはこの動機を与えるが、4話者の持続摩擦音スペクトルを対話的に合わせた研究であり、自動encoderの完成先例ではない。[Birkholz & Jackél 2006](https://vocaltractlab.de/publications/birkholz-2006-rib.pdf)

断面積列の連続補間だけでは、短い完全閉鎖や音源成立の切替を十分に表せない場合がある。狭窄を作る組織・位置の情報も重要になる。[Birkholz 2014](https://vocaltractlab.de/publications/birkholz-2014-issp.pdf) これはPMLの不具合の証明ではなく、filter補間だけに全時間構造を任せない設計上の動機である。

Jackson & Shadleは3話者の音声とEGGで、周期／非周期成分の変調位相関係が調音場所などで変わることを示した。遅延機構には分解・伝播時間の仮定があり、pitch glideの解析は1話者3glideと限られる。[Jackson & Shadle 2000](https://personalpages.surrey.ac.uk/p.jackson/pub/jasa00/JacksonShadle_JASA00_preprint.pdf) 続く英語摩擦音研究は、持続16話者・連続8話者でvoicing強度に伴うAM増加・飽和と場所差を調べた。[Pincas & Jackson 2006](https://personalpages.surrey.ac.uk/p.jackson/pub/jasa06/PincasJackson_JASA06_preprint.pdf)

**設計への推論：** 周期noise AMはtarget時計へ、非反復eventは絶対時刻へ分ける意義がある。ただし摩擦音の結果をsample3の特定音素・機構へ直接適用しない。位相差固定と秒単位遅延固定はF0編集後に異なるため、初回は前者だけを選ぶ。有効位相差を生理的な対流遅延の真値とは呼ばない。

## 3. source–filter相互作用と逆問題

声道負荷が声門流・声帯運動へ影響するsource–filter相互作用は理論的に重要である。[Titze 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2811547/) 一方、計算実験では相互作用強度と逆フィルタ誤差の単調な悪化が支持されず、F0–F1近接や既知伝達対blind推定の区別が重要だった。声帯運動へのlevel-2 feedbackはその検証に含まれない。[Palaparthi & Titze 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7485927/)

従って、相互作用の存在だけで全生理solverへ飛ばず、有効filterでどこまで足りるかを先に調べる。ただしfilter固定のF0編集を自然発声の物理的再演とも呼ばない。

単純なS=HUにも、可逆Qを用いたH′=HQ、U′=Q⁻¹Uという交換自由度がある。複数sourceでは枝の配分も曖昧になる。安定性・低次元性・支持・時間規約は候補を狭めるが、単一マイクから声道形状、声門流、圧力、乱流発生位置を一意に観測したことにはならない。[Panchapagesan & Alwanの逆推定研究](https://www.seas.ucla.edu/spapl/paper/panchi_jasa_2010.pdf)

minimum-phase化も生理sourceの回復とは異なる。混合位相分離はGCI基準の窓位置、位相unwrap、source／声道の位相仮定に依存し、高F0・低F1では難しい。[Drugman, Bozkurt & Dutoit](https://arxiv.org/html/1912.12602)

## 4. 残差を真のnoiseにしない

harmonic＋residualという代数的加算はできても、residualにはAM/FM、jitter、voice onset、未モデル化位相、burstが含まれ得る。PSHFの原著も波形推定と電力推定を区別し、transient・voicing開始終了での誤差増加を明記している。[Jackson & Shadle 2001](https://personalpages.surrey.ac.uk/p.jackson/pub/t-sap01/JacksonShadle_T-SAP01_preprint.pdf)

生波形の二乗包絡には調波間beatもある。複数周期、候補・帯域・窓への感度、平均モデルの誤差を確認せずnoise AMの真値とはしない。短いburstしか支持がない場合、周期AMと単発eventの分離は結論不能になり得る。

「風が当たる」という聴感だけでもmicrophone popとは断定できない。/pa/の音響と空気puffを区別した研究はあるが、1話者の距離操作等を含む実験で、一般音声の自動分離器ではない。[Derrickら、大学保存全文](https://ir.canterbury.ac.nz/server/api/core/bitstreams/0902e3cb-e4e8-45c7-babc-1bf9512b58e7/content)

## 5. なぜ局在分散包絡を最初に選ぶか

aQHMのstop再構成は、非定常振幅・位相で先行再構成誤差を減らせる先例である。しかし局所例は16 kHz・100成分・1標本hop、大規模側は1/2/4 ms hopで、コンパクトな少数係数と絶対Hz編集の成功を示したものではない。[Kafentzis, Rosec & Stylianou 2012](https://www.isca-archive.org/interspeech_2012/kafentzis12_interspeech.pdf) 遅延付き減衰正弦波群のPDDSにも先行例があるが、今回の確認は公式abstractまでである。[Boyer & Abed-Meraim 2002](https://www.dafx.de/paper-archive/details/31lvBCRXU5a9pXMeYbmBzA)

今回の問いは、再構成の基底を増やすことより、周期分散と非反復分散を混合波から配分できるかである。決定的2waveletでは局在variance burstを表せないため、初手を最大2個の非負局在分散包絡へ変更した。原音断片・全残差の保存、正解event区間の供給で成功を作らない。

共通filterで時間帰属が成立した後にだけ、同じ時計・event表現・予算で経路別filterを比較する。時間帰属が不安定なままfilterを増やすと交換自由度を増やし得る。同程度のnative適合を持つ複数解から編集結果が大きく分かれるなら、制御用表現として未安定である。

## 6. 広い候補を今すぐ主案にしない理由

VocalTractLab型analysis-by-synthesisにはforwardモデルの利点がある。しかし既存の単語研究には音素転写、話者形状、初期化、膨大な探索が関わり、音響距離の順位が知覚順位と一致しない例や鼻音が弱くなる例もある。[Gaoら2019](https://www.isca-archive.org/interspeech_2019/gao19e_interspeech.pdf) 自励声帯モデルは指定Hzを直接保証せず、48 kHzの高域精度も別問題である。

COVAREP IAIF、GlottDNNの非学習励振経路、GIF比較実装、VTLは参照候補だが、本案全体の完成実装ではない。非ML経路、ライセンス、版、帯域、前処理を個別に確認する。具体的入口は[文献一覧](bibliography.md)にまとめた。

## 7. 5役・2巡の科学的レビュー要約

以下は仮想的な観点整理であり、独立した専門家による査読ではない。

| 観点 | 第1巡の疑問 | 第2巡で残した制約 |
|---|---|---|
| 音声生理 | 閉鎖、振動、乱流を一つの時計にしていないか | 解剖学的真値の復元でなく、有効sourceと時間規約を検証する |
| 信号処理 | event固定が旧F0の持戻しにならないか | 周期AMをtargetへ、単発eventのみ秒で固定する |
| 逆問題 | 枝・filterを増やすだけでnativeが良くならないか | 同程度fitの別解の編集安定性を確認し、時間とfilterの変更を分離する |
| 実装・評価 | 少数成功・16 kHz・参照コードを完成codecと混同していないか | 科学的小試験、品質採用、48 kHz、実装導入を別段階にする |
| 批評 | 全残差保存や局所例外の増殖で延命していないか | 固定予算、反例、見切りを置き、改善の実証がないことを明示する |
