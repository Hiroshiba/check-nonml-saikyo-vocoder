# PP-aDFTの2015拡張・作者実装・費用範囲の追補

2026-10-17。既存のPP-aDFT案について、原著と公式配布元、現在の保存済み費用記録を静的に確認した。音声の新規解析・合成、モデル推論、取得コードの実行、新実装、外部書込みは行っていない。

## 結論

PP-aDFTはAIR反復を高速化する候補として根拠がある。ただし、現在利用できる作者実装の版とソフトウェアライセンスを特定できておらず、そのまま導入可能とは判断できない。2015拡張本文を取得したことで、最終LSを残す理由と、原著の速度倍率を現pipelineへ転用できない理由が明確になった。

## 1. 一次資料と取得できたもの

- [2014著者配布論文](https://gillesdegottex.eu/pdf/MorfiV2014ppadft.pdf)：Morfi、Degottex、Mouchtaris、ICASSP 2014。
- [2015拡張の出版DOI](https://doi.org/10.1109/TASLP.2015.2458580)：Speech Analysis and Synthesis with a Computationally Efficient Adaptive Harmonic Model、IEEE/ACM TASLP。
- [EU公式CORDIS成果一覧](https://cordis.europa.eu/project/id/644283/results)から[Zenodo版2593233](https://zenodo.org/records/2593233)へ到達し、13ページの作者原稿を取得した。先頭に出版Version of RecordへのDOIが示される。出版版そのものを取得したとは扱わない。
- 取得PDFはbare_jrnl.pdf、545339 bytes、SHA256 3ad534488df89727e6680bb7591c62a5ce11f1e430bdf36541bc37a21f79f876。これは論文ファイルの同定であり、コードの版ではない。

Zenodo metadataはCC-BY-4.0を表示する一方、PDFにはIEEEの権利表示と個人利用以外への許諾案内がある。本調査ではこの表示差の法的解決や追加許諾の受諾を行わず、論文本文を転載しない。いずれの表示も未知のPP-aDFTソフトウェアへの利用許諾として用いない。

## 2. 5.5倍と4倍は同じ量ではない

2014報告の5.5倍は録音ごとのLS/PP-aDFT時間比の平均である。2015 §V-AのTable IIはAIRの録音ごとのPP/LS時間比を平均し、aDFTは0.25、FChTは0.13と報告する。その逆数が論文の4倍と7.69倍である。一般に平均した比の逆数と逆比の平均は等しくなく、年の異なる数値をそのまま性能の上下として比較できない。

さらに2015 Table IIIの最終fitではaDFT/LS=3.27、FChT/LS=2.10で、変換法の方が遅い。AIRにPPを採り、最終調波係数推定にはLSを残す構成には、品質だけでなく費用上の根拠もある。通常FFT、PP-FChT、PP-aDFTは別方式であり、速度値を交換できない。

これらは原著の処理区間・実装・録音・機械における測定である。現在のencoder、編集、decoder、評価器を含めた全体が4倍または5.5倍になるという証拠ではない。

2015の品質比較は32発話・16言語、聴取評価は除外後24人。各人6録音×6条件を評価し、95%信頼区間を表示する。著者はaDFT-LSを同程度と解釈するが、非劣性・統計的同等性の検定を示したとは読まない。16kHzへ再標本化したPESQはLS-LS 4.18、aDFT-LS 4.15。2014の4.13/4.12とは別の結果であり、現行corpus・48kHz・±3編集への品質保証ではない。

## 3. 現aHM AIRで置き換わる範囲

現在のAIRは各active frameで瞬時Nyquistまでの全帯域quasi-harmonic基底を解き、そのうち低い調波の補正をF0更新に使う。PP-aDFTは反復中のこの推定と補正規約に対応する。低域の部分bin計算、peak再利用、大きな逸脱の処理なども含むため、LS solverを同じ入出力のまま差し替える操作ではない。

2015本文には入力SWIPEP、one anchor per period、3周期Blackman、窓長の2倍のaDFT長、初期調波数8、部分aDFTとpeak再利用が記載される。これらも現実装と照合すべき条件である。

上流のF0取得、最終strict-harmonic LS、Cartesian編集、波形復号は直接の置換対象ではない。また、最終LSの式を固定してもAIR出力F0が変われば、窓、保持frame、係数、費用と編集結果は変わり得る。

[固定COVAREP sin_analysis.m](https://github.com/covarep/covarep/blob/5a2be5d6b776f14a0b275c69fde90eb13849e60d/sinusoidal/sin_analysis.m)はadaptiveとPPの組合せを拒否し、PP枝は通常FFTとFChT追加TODOを含む。既存optionの切替だけで論文PP-aDFTを得ることはできない。

## 4. 現在の費用から言えること

保存済みの最初の12録音の部分観測では、AIR平均41.248秒、最終fit平均5.813秒、encoder total平均47.330秒だった。AIRと最終fitは診断込みであり、純solver時間ではない。encoder totalには読込・保存等も含まれる。正式renderの支持数はnative11、−3が11、+3が10で、解析費の12例と同一成功支持ではない。

この部分観測は、AIRを費用改善の候補とする動機を支持する。PP-aDFT自体の現環境実測や、固定120全件の費用結果を示すものではない。原著倍率をこの秒数へ掛けて将来実行時間を予測しない。条件付きの一般論として、他の費用が同じなら全体の速度比は(Tother+TAIR)/(Tother+TAIR/s)であり、s>1かつTAIR>0、Tother>0なら1とsの間になる。しかし現段階でsやTother不変を仮定した予測値は置かない。

## 5. 作者コードと未確認事項

[作者research](https://gillesdegottex.eu/research/)、[tools](https://gillesdegottex.eu/tools/)、作者の公開サイトrepository、COVAREP、GitHub repository/code検索、関連する作者共著の下流論文を調べた。今回の範囲では再利用可能なPP-aDFT作者コードと、2014/2015どちらに対応する版か、ソフトウェアライセンスを確定できなかった。全history・全forkを網羅していないため、コード不存在という結論ではない。本文取得とコード取得を混同しない。ZenodoはPDF1個のみで、本文にコード配布URL・release/tag・software licenseは確認できなかった。作者サイトの確認commitはeb72c5b04733918db9979b16b2206b005fdee6b5であり、これは文献サイトの版を指す。

COVAREP内のライセンスや、論文depositのライセンスを、見つかっていない作者コードへ流用しない。著者への問い合わせ、外部投稿、ライセンス受諾は行っていない。

## 6. 次に必要な判断材料

導入前には、aDFT位相・bin規格化、peak補間、partial支持、再利用条件、UV時の大逸脱処理、反復と停止条件、2014/2015の版差を確定する必要がある。擬似コードではゼロ補正時の除算、tolの単位、調波上限/整数化、peak同距離や候補不足等に作者コードとの照合が残る。誤植と断定せず、作者原稿と出版最終版の差も未確認として残す。作者コードが得られなければ論文からの独立実装となり、作者出力との数値同値や原著性能再現は未確認として扱う。

将来実装を検討する場合は別directory・別freezeで扱う。現在の固定runへ混ぜない。新規実験の前に、AIR区間の定義と品質評価の支持を決め、最終LS維持のnativeと±3編集を分けて見る。局所速度が改善しても、失敗率、品質、全体費用の改善が自動的に成立するとは判断しない。

## 批評と再確認

元の文献担当と批評家が2015本文を独立に照合した。「全解析工程を評価」というabstractから全工程4倍と読まないこと、2014/2015の比の集約方向を分けること、final LSを保持すること、未知のsoftware許諾を論文から推定しないことを確認した。批評を受け、一般的な速度上限式にも正の費用とs>1の条件を明記した。公開追補には候補のprivate sourceを転載していない。
