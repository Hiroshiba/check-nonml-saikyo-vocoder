# F0候補の識別と声質の分離は、評価対象が異なる

F0候補を識別することと、声門源・声道を分離して声質を物理的に解釈することは、別の評価課題です。以下は、一次PDFの該当節を確認した調査報告に基づく整理です。

Hosom（2005、§2.1/2.4/2.5/3/5）[1]は、声門傾斜や声道共鳴包絡を明示分離せず、十分強い調波を等重み投票してF0を評価しました。12 dB閾値、Viterbi、半周期候補の抑制も併用しており、等重み単独の効果ではありません。

評価は男性1人450文のlaryngograph基準50〜250 Hz内と、小児35人各1単語の母音中心計70点に限られます。判定困難5点は別区間で評価し、有声・無声（VUV）は推定しません。投票の等重みは、現候補のGaussian係数等分散1/Kとは別です。

Perrotin・McLoughlin（2017、§1/4.1–4.2）[2]は、単一ドイツ語女性の12母音×3発声努力、825刺激・22.05 kHzでGFM-IAIFを検討し、努力に伴う高域傾斜変化を声門側へ配分しやすいと報告しました。声質の物理的解釈に関する知見ですが、声門流の真値はなく、F0・オクターブ識別の改善は未評価です。

前者を、声門・声道の明示分離がF0識別に必須だとする根拠にはできません。同時に、全音声で分離が不要、オクターブ問題が解決したとも言えません。2本から現ACGの品質、次の係数事前・モデルの採用は判断できず、PMLを維持します。この調査記録で新規音声・品質測定は行っていません。

- [1] [Hosom 2005, F0 Estimation for Adult and Children’s Speech](https://www.isca-archive.org/interspeech_2005/hosom05_interspeech.pdf)
- [2] [Perrotin & McLoughlin 2017, On the Use of a Spectral Glottal Model for the Source-filter Separation of Speech](https://arxiv.org/pdf/1712.08034)
