# 確率的F0/VUVとclock/event表現：研究判断記録

2026-10-19 UTC（2026-10-20 JST）。対象：[Hiroshiba/check-nonml-saikyo-vocoder](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder)。基点は[PR #63](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/pull/63)マージ後の[main 113ac2dc](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/commit/113ac2dc65a7ac8fd383097802b4715139f847ce)。

**本記録は文献・公開実装の調査を整理した方式選定である。新しい音声実験の結果ではない。現base `pml-lowband-fwcep60-v1` を維持し、RAW_FULLは採用していない。** 以下の初期計画に対する初回結果は末尾に追記した。完成codecとしての採用はなく、完成codec、音質改善、自然音声での分離成功、48 kHz対応を主張しない。

## 決定

1. 有声／無声、F0・オクターブ候補の確率的扱いと、生体構造・音響物理を重点研究として継続する。単一F0の早期確定、確信度と物理雑音率の混同、周期成分と非反復成分の時間契約を主な論点とする。
2. 次の小試作は、**既知source時計・既知共通安定filterの下で、周期noise分散と最大2個の非負局在分散包絡を混合波形から競合推定する表現**を選ぶ。単発eventは絶対時刻に残し、調波平均と周期noise分散だけをtarget時計へ移す。
3. 初手に検討した決定的2waveletの平均event表現は選ばない。局在したnoise分散増加を表せないことが既知で、風状音に関係し得る確率的成分の検討へ直結しにくいためである。両表現を同時に追加しない。
4. F0候補を変えれば包絡やPDDが変わるという既知の感度だけを再測定しない。候補の保持／棄却が次の方式選定を変える段階で、局所証拠と追跡後分布の比較を行う。これは確率研究の打切りではなく、識別力のある実装着手順の選択である。
5. 共通filterと異なる経路のfilterを同時に変更しない。時間帰属が機能し、共通filter不足を示す証拠が出た場合だけ二filter比較へ進む。全生理analysis-by-synthesisは、当面は反例生成の参考とする。

## 既存の測定と、今回の推論の境界

- [固定120録音・40話者のRAW_FULL比較](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html)では、既存予測MOSの話者等重み差は +0.0767604、保存区間は [+0.0651134, +0.0878215]。編集miss差には +0.154538ポイントの不利が残る。これは当該固定条件・評価器の結果で、人の聴感や局所雑音の解消を証明しない。
- [H1時間再割当](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/h1-time-reassignment-2026-10-19/index.html)では単独成分の集中が見えたが、混合の弱先行成分でsigned対差が32対応中4対応で負となり、安定分離は支持されなかった。負値を物理的成分の消失とは読まない。
- [保存AM診断](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-am-diagnostic-2026-10-19/index.html)の包絡構造には、調波の差周波・AM/FM・雑音AMが交絡する。真の乱流AMを取得したとはしない。
- P/Fや低域maskには品質未評価の範囲がある。未評価を「音質で失敗」と総括しない。一方、全ての旧分岐を完走することを次の研究の条件にしない。

単一マイクから、sample3注目箇所の音素、生理機構、真のF0/VUV、乱流発生部位、マイクへの気流混入を確定していない。今回の選定はこれらの真値の推定成功に基づくものではない。

## 計画中の最小試作

詳細な格子・包絡形・罰則・境界・資源上限は実装前に一つへ固定する。本記録はその完成仕様の代用ではない。

- encoder入力：混合波形、既知source時計、既知共通安定filterのみ。正解event個数・時刻・幅・強度、調波係数、周期AM係数、noise実現・生成seed、分離正解は渡さない。
- 平均：source時計の第1〜4調波、8係数。局在する決定的波形を追加しない。
- 分散：正の周期部分と最大2個の非負・有限支持event包絡。eventは時刻・幅・強度を保存し、原音、残差波形、自由時系列包絡、元noiseは保存しない。
- 推定：候補分散ごとに調波を再fitし、Gaussian負対数尤度と事前固定の記述長型罰則で比較する。近似探索なら大域最適性を主張しない。
- 復号：調波平均と周期分散はtarget位相へ、event包絡は絶対時刻へ。新しい評価noiseを用い、正解波形の貼戻しで再構成を稼がない。初回はAM位相差固定とし、時間遅延固定を混ぜない。
- 初期案の小条件は16 kHz・4096標本、source 120→target 140 Hz、既知H=1+0.5z⁻¹・初期状態0。これは予定値で、測定結果や48 kHz検証ではない。通常PMLの±3半音範囲に合わせ、実行前に170 Hz案から変更した。

## 次の行動と、広げる条件

1. 最初は一定noise、周期AMのみ、局在増分のみ、加算混合、乗算的な分散変化、平均だけの急なAMの6群を予定する。複数noise実現で帰属の揺れを観測する。格子外時刻・異なる包絡形・pressure impulse・複数重複burstなどは、初回結果が次の判断を変える場合の追加候補であり、初回の実施済み条件には数えない。
2. event時刻・幅・強度の保持、周期AMのtarget追従、source時計残留、誤event、候補間の配分、seed感度を別々に観測する。単一noiseの二乗波形を期待分散真値とは呼ばない。
3. 成功範囲は既知時計・既知共通filterの条件に限定する。次はoracleを一つ外すか、固定契約の自然音比較へ進む。自然音で候補選択が判断を変える場合にF0×調波次数の比較を行う。
4. 試作と原因を限定した修正を経ても同じ反例・同じ失敗説明が残るなら、その段の局所調整を止める。追加試行は新しく判別できる問いを示す。実装バグ修正と科学仮説の変更を区別する。
5. 時間帰属が崩れる場合、二filterや辞書拡張で救済しない。色の異なるsource条件だけで崩れるなら、同じ時計・event予算で共通／別filterを比較する。全clock/event方針や確率F0/VUV研究を一例で棄却しない。
6. 候補採用は、native／編集の品質、制御、局在、生成成功率、保存量、encoder／decoder別RTFを別々に確認してから行う。既存120録音を再利用する場合は固定benchmarkとし、未見testとは呼ばない。16 kHz成功と48 kHz達成も分ける。

## 読む順序

- [生体構造・音響物理と表現選定](vocal-physics.md)：異なる時計・発生位置・単一マイクの限界
- [確率的F0/VUVと絶対Hzの契約](probabilistic-pitch.md)：候補選定、非同定性、評価の分離
- [Bayesian実装監査の要約](bayesian-implementation-audit.md)：固定ソースのAPI・状態・単位・移植リスク
- [一次資料・参照実装](bibliography.md)：根拠と確認範囲

5役の検討は科学的論点を点検する仮想レビューであり、独立した人間専門家5名の査読や追加の実測ではない。

## 初回結果と公開登録

[初回HTML](results/run-001/index.html)・[分析](results/run-001/analysis-ja.md)を保存した。計測は2026-10-19 19:28:57.800–19:30:17.655 UTC、24ケース・240合成出力は全ok。ただしPML raw F0 fallbackは5/24、提案のC5では平均変化を周期雑音へ誤帰属した。正常終了は品質成功を意味しない。提案にはoracle位相・既知Hを与え、PML/WORLDは通常F0推定を使う条件差がある。PML現baseを維持し、次は調波meanに共通するgainだけを変更する計画とする。次版の実装・計測は未実施。

公開登録の正本は `research/pages-reports.json` の既存 `navigation-only` 経路であり、当PRの `experiment.json` は取り除いた。独自のcompact数値を標準results schemaとして登録しない。[公開先](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/clock-event-variance-2026-10-20/index.html)（マージ・公開後）へmanifestに固定した成果物のみを掲載する。案内作成日時はbundle作成の2026-10-19T19:38:44.700599+00:00で、測定時刻とは別。

元bundleの293公開ファイルはbyte不変。artifact-manifestだけ各recordの `path` を既存形式の `name` に変換し、音声帰属ページ `audio_credits.html` を追加してmanifestのbytes/SHAを再固定した（manifest込み295成果物）。CLI source・元NPZ・floatWAV・params・logsはGitへ追加しない。一覧のC5 seed 0の3音声はcompact数値のケース対応と音声来歴の元波形SHA／公開SHAを照合して選定した。

## 共通mean gainを追加した比較

[run-002の比較HTML](results/run-002/index.html)（[公開先](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/clock-event-mean-gain-2026-10-20/index.html)、マージ・公開後）を追加した。C5全4例で誤qが消失し、σ²比は7.13–7.18から0.976–1.028、140 Hzの平均KLは0.928339から0.00560181へ改善。C0–C4の旧分布・seed 0波形は同一だった。これは既知位相・Hの人工機構比較で、自然音声品質の採用結果ではない。PML/WORLDは初回値を引用し再計測していない。現base PMLを維持する。初回run-001は保持し、run-002も既存navigation-only登録で公開する。

## 周期・局在分散の結合を追加した比較

[run-003の比較HTML](results/run-003/index.html)（[公開先](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/clock-event-coupling-2026-10-20/index.html)、マージ・公開後）を追加した。3段階の実測は、初回のC5平均変化の誤帰属、v2共通mean gainによる改善、v3結合flagによる改善と誤判定を記録する。v3ではC4 target局所KLが0.0310446→0.0112895、一方C3は0.000642280→0.00832401に悪化した。C4の結合選択2/4、C3の誤選択1/4であり、追加自由度を一律の改善としない。一覧音声は事後選択した人工音の失敗例C3_seed104729 native。正式音質評価・自然音改善・採用判断ではなく、現base PMLを維持する。
