# 確率的F0/VUVと絶対Hz編集の契約

2026-10-19 UTC（2026-10-20 JST）。一次論文・公開ソース調査の要約。方式比較は提案であり、新しい数値実験・音質順位ではない。

## 1. 保持するのは何の不確かさか

次の量を同じconfidenceへまとめない。

- 周期仮説のscore：NCCF、Praat strength、REAPER costなど
- 明示した波形モデル・priorの下のF0×調波次数Kの事後確率
- 自然音声で予測確率と正解頻度が対応する校正状態
- 候補条件付きの包絡・PDD・非周期性
- 合成noiseの振幅・分散・seedによる変動
- モデル不適合、無音、弱い周期、単一F0では表せない不規則性

harmonicモデルとnoise-onlyモデルが両方不適切でも、二者比較のharmonic確率は高くなり得る。狭いposteriorはモデル妥当性の証明ではなく、広いposteriorは物理noise量の多さを意味しない。P(voiced)をそのまま周期振幅やnoise powerに写さない。

現在のPMLは無声区間にも正の連続F0を時計として持ち、保存noise maskの後に複数の変換・平滑化を行う。「F0=0で音を切る」「全経路がhard mask」とは説明できない。[PML原著](https://gillesdegottex.eu/pdf/DegottexG2017pmlj_acceptedversion.pdf) また同じF0/maskを使うRAW_FULLとPMLの差を、F0推定誤りだけへ帰属しない。

## 2. 主な候補の位置付け

| 候補 | 使える点 | 留保と選定 |
|---|---|---|
| pYIN | 公開APIに候補Hz・重み・voicedprob・最終trackがある | 公開重みとHMMへ入る重みが低振幅時に異なる。Viterbi内部値はforward marginalではない。候補生成の参照 |
| REAPER | pitch marks、VUV、最終F0、corrと内部候補lattice | corrはposteriorではなく、通常pyreaper APIは全latticeを返さない |
| Praat | frameごとのHz・strength・無声候補とpathを分ける | strengthはposteriorではない。scoreのsoftmaxは校正の代わりにならない |
| ShiらBayesian harmonic | F0×Kとnull状態、局所証拠と時間priorを区別できる | 自然音声で校正済みではない。MATLABとC++の公開量・安全性が異なる。分布構造の主参照 |
| harmonic chirp | 静的harmonicモデルへF0傾斜を追加する対照 | 調査論文は8 kHzの自然音試験。完成公式APIは今回確保・監査していない |
| variable-rate particle filter | 周期ごとのsource–filter状態と分布を扱える | 原著試験は短い有声区間、既知初期周期などに限定。未知全発話の直接根拠ではない |
| ECKF | 局所の周波数・振幅・位相追従 | 単一局所状態で離れたoctaveモードを保持できない。内部共分散normはF0校正分散でない |
| PEFAC | log-frequency filterbankによる候補処理 | VUVに学習済みGMMを含む全体は厳密非MLの主候補から外す。前段のみの変種に元方式の性能を引き継がない |

一次論文・固定ソースは[文献一覧](bibliography.md)を参照。Kaldiの連続pitchもASR特徴の先例だが、NCCFと一本のpitchは多峰payloadではない。YANGSAFのIF／aperiodicity mapも有用な候補条件付き観測だが、既試行と重複する完成案として数え直さない。

## 3. 次の研究に残す二層

**推論用記録：** 観測支持、fs、grid・有効セル、候補score／局所尤度、F0×K、prior、local／filtered／smoothedの区別、前処理、状態更新有無。

**将来payloadの候補：** 少数モードの領域・質量・モード内幅・切捨て質量・条件付き音色。全格子の常時保存を完成仕様とはしない。モード間質量とモード内分散は別であり、平均Hzと一つの分散だけでは離れたoctave族を表せない。

これは設計案で未実装。候補ごとに包絡や非周期性を保存すると、その保存量・計算量も増える。F0分布だけの小容量をcodec全体の小容量と呼ばない。

## 4. target時計だけでは曖昧性は解けない

200 Hzの同じ成分を、100 Hz仮説の第2調波と200 Hz仮説の第1調波の両方で説明できる場合がある。同じ絶対targetを指定しても、調波番号を保存すれば移動先は異なる。sourceの非同定性をtarget指定で解消したとはいえない。

候補を同時に鳴らしたり候補波形を平均したりすることも、「一つの指定Hz」の自動的な実現ではない。内部target位相、調波番号対応、最低反復周期、知覚pitch、周期AMを区別する必要がある。

- 無音では内部時計だけを動かし、energyを増やさない。
- 純摩擦・ささやきでは、周期枝がない間はHz指定に音響効果がない契約を認める。revoicingは別編集とする。
- 弱い有声では、F0不明を無声の確定にしない。
- 周期交替やcreaky様発声では、イベントrate・波形反復・知覚pitchの全てを一つの数値に一致させる保証をしない。厳密周期化は声質変更を伴う。

## 5. 検証を行う条件と停止条件

既知source時計のclock/event試作を先に進める。自然音で候補選択が表現の決定を左右するときに限り、以下を追加する。重点である確率VUV/F0/octave研究自体は継続する。

1. **保持／棄却を変えられるか。** 同じ支持・帯域・複雑度で、局所F0×K証拠、追跡後質量、event配分を比べる。文脈・priorだけを変えた対照も分離する。文脈は追加情報なので、posterior変化自体を誤りとしない。
2. **数値的整合か、自然音の妥当性か。** モデル一致の反復と、欠落基音、偶数次のみ、AM/FM、色付きnoise、過渡などのモデル外対照を分ける。PMF／density、単位変換、格子、mode切捨て、信用集合の幅とcoverageを別に見る。[SBC](https://arxiv.org/html/1804.06788v2)は実装整合性の参考で、自然音のモデル妥当性を保証しない。
3. **時間情報の重複か。** localとfilteredを分け、hop変更では物理時間当たりの遷移priorも揃える。重複窓による過信は懸念であり、今回測定した結果ではない。
4. **編集に使えるか。** octave曖昧例、周期AM、周期交替に同じ絶対targetを与え、source時計残留・調波位置・event時刻を確認する。native適合だけで採用しない。

単なる候補別出力差しか増えず、候補の保持／棄却や方式選定が変わらないなら感度診断を終える。どの候補も同じ構造残差を残すなら、今回の局所問題をF0不確実性へ帰属する仮説を下げる。prior・窓・gridの探索を無期限に続けない。C++ API不整合は実装障害であり、Bayesian仮説の反証ではない。

## 6. 48 kHzと費用

F0専用の低rate支流と、元48 kHzの包絡・高域・過渡経路を分ける設計は可能。ただしanti-aliasing、群遅延、timestamp、観測支持を対応させる。16 kHzのcodec出力をupsampleしても48 kHz検証にならない。

F0×K分布は1frameでO(PK)保存するが、denseな追跡演算はそれより重い。[実装監査](bayesian-implementation-audit.md)を参照。候補条件付き音色を増やす費用も含め、実測RTFと算術見積もりを区別する。

## 7. 5役・2巡のレビュー要約

仮想レビューによる論点整理であり、独立した測定や人間査読ではない。

| 観点 | 第1巡の指摘 | 第2巡の反映 |
|---|---|---|
| 統計 | 正規化scoreとposteriorと校正を混同しない | measure、prior、local／filtered、モデル検査を分離 |
| 音声分析 | F0誤りとAM/FM・声道変化を混同しない | 候補条件付き残差と、非定常モデルの限定対照を置く |
| 合成制御 | 同じtargetでも調波番号が違えば移動先が違う | target時計、source仮説、無声revoicingを別契約にする |
| 実装計算 | APIや無音buffer、全格子保存を確かめる必要 | 必要な取得点だけ確認し、C++全修理を初手にしない |
| 批評 | 「確率なら改善」と先に結論しない | 候補選別が決定を変える場合だけ診断し、既知時計試作を妨げない |
