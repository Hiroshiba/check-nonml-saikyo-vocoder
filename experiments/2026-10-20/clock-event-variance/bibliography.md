# 一次資料・参照実装

調査日：2026-10-19 UTC（2026-10-20 JST）。本文で使った主な根拠と確認範囲をまとめる。論文での性能と本repositoryでの性能は分ける。本資料の編集時に新しい実験やリンク先の再実行はしていない。

## 生体構造・音響物理

- [Koenig & Lucero (2008)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2651765/)：口腔閉鎖中の圧力・voicing。単純な閉鎖＝無音の説明を避ける根拠。
- [Stevens (1993)](https://www.sciencedirect.com/science/article/pii/016763939390035J)：停止子音の初期過渡、frication burst、声門音源等の区別。確認は公開abstractまで。
- [Birkholz & Jackél (2006), 著者PDF](https://vocaltractlab.de/publications/birkholz-2006-rib.pdf)：位置別noise源と伝達。4話者・持続摩擦音・対話的適合という範囲。
- [Birkholz (2014), 著者PDF](https://vocaltractlab.de/publications/birkholz-2014-issp.pdf)：調音形状からの摩擦noise、閉鎖の扱い。source切替をfilter補間だけへ任せない動機。
- [Jackson & Shadle (2000), 著者稿](https://personalpages.surrey.ac.uk/p.jackson/pub/jasa00/JacksonShadle_JASA00_preprint.pdf)：周期／非周期成分の変調位相と遅延。3話者、glide部分は1話者3例。機構推測の限界を含む。
- [Pincas & Jackson (2006), 著者稿](https://personalpages.surrey.ac.uk/p.jackson/pub/jasa06/PincasJackson_JASA06_preprint.pdf)：英語摩擦音のvoicingに伴うAM、持続16話者・連続8話者。
- [Jackson & Shadle (2001), 著者稿](https://personalpages.surrey.ac.uk/p.jackson/pub/t-sap01/JacksonShadle_T-SAP01_preprint.pdf)：PSHF、波形推定と電力推定、transient／voicing境界の限界。
- [Titze (2008)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2811547/)：非線形source–filter相互作用の理論。
- [Palaparthi & Titze (2020), 著者稿](https://pmc.ncbi.nlm.nih.gov/articles/PMC7485927/)：source–filter相互作用とglottal inverse filteringの計算実験。level-2 feedbackを含む全面検証ではない。
- [Derrickら, 大学保存全文](https://ir.canterbury.ac.nz/server/api/core/bitstreams/0902e3cb-e4e8-45c7-babc-1bf9512b58e7/content)：/pa/における伝搬音響と空気puff。一般音声の自動pop分離ではない。
- [Panchapagesan & Alwan, 大学保存稿](https://www.seas.ucla.edu/spapl/paper/panchi_jasa_2010.pdf)：調音逆推定の非一意性、初期化、話者較正。
- [Drugman, Bozkurt & Dutoit, 著者稿](https://arxiv.org/html/1912.12602)：複素cepstrumによる混合位相分離、窓・GCI・高F0／低F1の限界。
- [Kafentzis, Rosec & Stylianou (2012)](https://www.isca-archive.org/interspeech_2012/kafentzis12_interspeech.pdf)：aQHMのstop再構成。16 kHz・100成分・1標本hopの局所例と、1/2/4 ms hopの大規模比較を区別。
- [Boyer & Abed-Meraim (2002), DAFx公式abstract](https://www.dafx.de/paper-archive/details/31lvBCRXU5a9pXMeYbmBzA)：共通遅延付き減衰正弦波群PDDS。本文精読・音声分離の実証として扱わない。
- [Gaoら (2019)](https://www.isca-archive.org/interspeech_2019/gao19e_interspeech.pdf)：VTL型analysis-by-synthesis。41ドイツ語単語・男性1話者、音素転写由来初期化を含む。

## 確率的F0/VUV・非定常モデル

- [Degottexら, PML accepted版](https://gillesdegottex.eu/pdf/DegottexG2017pmlj_acceptedversion.pdf)：現方式の音響表現と留保の参照。
- [Shiら, Robust Bayesian Pitch Tracking Based on the Harmonic Model, accepted版](https://vbn.aau.dk/ws/portalfiles/portal/308359830/Robust_Bayesian_Pitch_Tracking_Based_on_the_Harmonic_Model.pdf)：F0×K、null、時間追跡。自然発話のposterior校正や48 kHz編集vocoderの実証ではない。[著者preprint](https://arxiv.org/html/1905.08557v1)
- [Nørholmら, harmonic chirp論文の著者稿](https://vbn.aau.dk/ws/portalfiles/portal/285859520/chirp_ultimate.pdf)：F0傾斜・区間長・モデル選択。自然音試験は8 kHz。対応する完成公式APIは今回未監査。
- [Zhang & Godsill, 大学保存稿](https://api.repository.cam.ac.uk/server/api/core/bitstreams/5b1300dc-2538-493d-8952-b0985e99a8c5/content)：variable-rate particle filter。短い有声区間、既知初期周期、主に加算Gaussian雑音。無声全発話へ外挿しない。
- [Dasら (2017), DAFx原著](https://www.dafx17.eca.ed.ac.uk/papers/DAFx17_paper_21.pdf)、[2020 AES原著情報](https://aes.org/publications/elibrary-page/?id=20719)：ECKFによる局所pitch追跡。多峰octave分布の代替ではない。
- [Kaldi pitch原著 (2014)](https://www.danielpovey.com/files/2014_icassp_pitch.pdf)：ASR用の連続pitch特徴。
- [PEFAC著者学位論文](https://spiral.imperial.ac.uk/entities/publication/33612eb5-f29c-41bb-8d51-31c8db151ea9)：VUV用GMM学習の根拠は検索索引本文と公式sourceを照合。PDF全章の精読はしていない。
- [Simulation-Based Calibration](https://arxiv.org/html/1804.06788v2)：Bayesian実装整合性検査の参考。自然音モデルの妥当性とは別。

## 公開実装・API

- [pYIN固定版 PYinVamp.cpp](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/PYinVamp.cpp)、[MonoPitchHMM.cpp](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/MonoPitchHMM.cpp)、[SparseHMM.cpp](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/SparseHMM.cpp)：公開voicedprob、HMM入力、Viterbiの区別。
- [REAPER公式](https://github.com/google/REAPER#the-reaper-algorithm)、[pyreaper API](https://pyreaper.readthedocs.io/en/latest/generated/pyreaper.reaper.html)：通常出力と内部latticeの範囲。
- [Praat Pitch object](https://praat.org/manual/Pitch.html)、[raw autocorrelation](https://praat.org/manual/pitch_analysis_by_raw_autocorrelation.html)：候補・strength・pathと選択cost。
- [Bayesian tracker固定tree](https://github.com/LimingShi/Bayesian-Pitch-Tracking-Using-Harmonic-model/tree/ad9a3fcfe60d2e97a635a92c2076ff1978ae3697)、[fastF0Nls固定tree](https://github.com/jkjaer/fastF0Nls/tree/5047004bc2e1fb1a141da5ec5be0d09e5965a2bc)：[静的監査要約](bayesian-implementation-audit.md)に取得点と移植リスクを掲載。
- [ECKF固定実装](https://github.com/orchidas/Pitch-Tracking/blob/d14e9fb3b4cd2077c3629af5133db2d610080202/eckf_pitch_final/eckf_pitch_modified.m)：内部共分散normはF0校正分散のAPIではない。コード再利用許諾は未確認。
- [PEFAC固定実装](https://github.com/ImperialCollegeLondon/sap-voicebox/blob/46a4a0662cb42cc8acbeec9069206db02f22a9f3/voicebox/v_fxpefac.m)：候補とGMM VUV経路。
- [Kaldi公式source](https://github.com/kaldi-asr/kaldi/blob/master/src/feat/pitch-functions.cc)、[YANG vocoder](https://github.com/google/yang_vocoder)：特徴量の意味と候補条件付き観測の参考。
- [COVAREP IAIF](https://github.com/covarep/covarep/blob/master/glottalsource/iaif.m)：pitch非同期版、前処理・端処理を含む。transient真値ではない。
- [GlottDNN公式](https://github.com/ljuvela/GlottDNN)、[設定説明](https://aalto-speech.github.io/GlottDNN/vocoder_config/)：非学習fixed-pulse／original-pulse経路もある。提案全体が既実装という意味ではない。
- [GIF評価の著者repository](https://github.com/SpeechSalleBcn/inverse-filtering-evaluation)：IAIF／QCP等とOPENGLOT-I。依存別license確認が必要。
- [VocalTractLab開発backend](https://github.com/TUD-STKS/VocalTractLabBackend-dev)、[公式配布入口](https://vocaltractlab.de/index.php?page=vocaltractlab-download)：forward synthesisの参照。自動逆推定encoderや48 kHz品質の保証ではない。

## 本repositoryの既存公開観測

- [RAW_FULL固定120比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html)
- [保存AM診断](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-am-diagnostic-2026-10-19/index.html)
- [H1時間再割当](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/h1-time-reassignment-2026-10-19/index.html)
- [P/F比較・低域mask付録](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/frame-color-pf-comparison-2026-10-19/index.html)
- [aHM/Cartesian比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/ahm-cartesian-multimetric-2026-10-17/index.html)

これらは今回新しく行った試験ではない。新しい局在分散包絡の実験結果へのリンクではない。
