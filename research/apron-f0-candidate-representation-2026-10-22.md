# ApronでF0候補を残すときは、重みと音響表現を分けて考える

Apronは一本のF0系列で声源と声道を解析します。複数候補の重みを保存する案では、重みの意味に加え、別の候補を選んだときに復号器が使う音響表現をどう得るかが未解決です。以下は固定版ソースの読取と紙上議論であり、新方式の採用や品質改善を示す結果ではありません。[現行ApronのF0解析メモ](apron-f0-assumptions-2026-10-22.md)と[固定120録音の品質レポート](https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/apron-fixed120-evaluation-2026-10-22/index.html)を前提にします。

## F0を替えると、残差と声道側の解析にも届く

LLSM2では、選んだF0が調波の本数・振幅・位相を決め、その調波を再合成して元音声から引いた残差を雑音解析に渡します。雑音のPSDと残差PSD、帯域ごとのエネルギーと包絡もこの経路にあります。さらにLayer1は調波とF0からRdを推定・時間平滑化し、声道の振幅応答（VTMAGN）と声源の調波位相（VSPHSE）を求めます。[調波と残差](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L478-L506)／[雑音PSD](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L318-L406)／[雑音包絡](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L417-L456)／[Layer1のRdと声道](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer1.c#L48-L123)

雑音PSDの計算は残差だけでなく、元音声から作るスペクトルにも候補F0に応じた窓長と包絡推定を使います。その系列から時間方向の分散を求め、平滑化にも用います。調波解析の窓長もF0に応じて変わり、FFTサイズは系列全体で最も低い正のF0に依存します。現在のラッパーはHMPPを選び、上流の既定はHMCZTです。したがって、ある時刻のF0が同じでも、その時刻の保存済み音響値を別系列で安全に使い回せるとは一般には言えません。これは依存関係の話で、すべての数値が必ず変わるという意味ではありません。[元音声と時間平滑化](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L324-L385)／[窓と調波解析](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/dsputils.c#L175-L228)／[FFTサイズ](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/dsputils.c#L318-L325)／[上流の既定と現ラッパー](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L27-L42)、[現ラッパー](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d3cc76850949049e2c947e3d1b2e5aa7abfaeae6/vocoderbench/references/native.py#L15-L29)

入力PCM・標本化周波数・固定フレーム格子・解析設定は共通にできます。高域の帯域エネルギーを元音声から取る箇所には部分的な再利用の余地も見えますが、その共用は実装していません。候補間の解析境界としては、系列全体を元音声から解析し直すのが保守的です。所要時間は測っていません。現行Apronの保存形式は元の調波成分（HM）とPCMを残さないため、保存済みF0だけの編集は音高の変換にあたり、別候補で解析した結果は得られません。[高域の元音声参照](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L433-L445)／[保存項目](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d3cc76850949049e2c947e3d1b2e5aa7abfaeae6/vocoderbench/apron/storage.py#L16-L40)／[解析入力と保存](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d3cc76850949049e2c947e3d1b2e5aa7abfaeae6/vocoderbench/apron/engine.py#L68-L96)

## libpyinの一本の出力と、経路の重みは別物

Sleepwalking版libpyinは候補の重みにベータ分布と有声寄りの係数を使い、相関の条件を満たした候補を5倍した後、候補重みの合計を元に戻します。しかし公開関数が返すのは、系列を選んで出力時の補正を加えた一本のF0配列です。候補配列と選択経路は解放されます。[候補の重み](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.c#L115-L182)／[系列選択と出力](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.c#L189-L218)／[公開関数](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.h#L37-L54)

このlibpyin版の[readme](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/readme.md#L7-L18)と[makefile](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/makefile#L4-L8)は外部libgvpsへの依存を示しますが、その版を固定していません。以下のlibgvps `2f1b4106` は別途読んだ版であり、当時のlibpyinが実際に使った版とは確認できていません。

この別版では、隠れ状態それぞれに同じ「1から候補重みの和を引いた値」を下限付きで与え、隠れ状態数では割りません。遷移にはlibpyin側の同一・有声無声切替係数を使い、行ごとの確率正規化はありません。処理は最大値と逆追跡で経路を選び、全経路の重みの和は計算しません。[隠れ状態への重み](https://github.com/Sleepwalking/libgvps/blob/2f1b4106d72f8f8138dc447bf0123820c0772cbd/gvps_viterbi.hc#L157-L172)／[遷移と選択](https://github.com/Sleepwalking/libgvps/blob/2f1b4106d72f8f8138dc447bf0123820c0772cbd/gvps_viterbi.hc#L181-L293)／[最大経路の逆追跡](https://github.com/Sleepwalking/libgvps/blob/2f1b4106d72f8f8138dc447bf0123820c0772cbd/gvps_viterbi.hc#L301-L362)／[libpyinの遷移係数](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.c#L53-L66)

有効な候補と初期状態について有限の正の因子を指定すれば、全潜在経路の重みを足した分配和 `Z` により、経路重み `W/Z` を定義できます。これは数学的なモデル内の正規化で、実測による校正は前提ではありません。ただし元実装が返す事後確率でも、生理的な有声・無声確率でもありません。隠れ状態の数と未正規化の遷移係数は、最大化から経路の総和へ替えたときの重みに影響します。

隠れ状態はすべて0 Hzへ写され、候補の状態も音高区間から最も近い候補周波数へ戻されます。有声区間の開始を前へ延ばす補正もあります。このため、異なる潜在経路が同じ完成F0系列になり得ます。選んだ一経路の重みは、その系列へ写る全経路の重みの一部にすぎず、選外の経路にも保存した系列と同じ出力が含まれ得ます。上位二経路だけの重みを合計1へ直して全体の被覆率とは呼べません。[経路からF0への変換](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.c#L69-L79)、[出力補正](https://github.com/Sleepwalking/libpyin/blob/b38135390b335c3e8cea6ef35cf5093789b36dac/pyin.c#L189-L218)／[状態の写像](https://github.com/Sleepwalking/libgvps/blob/2f1b4106d72f8f8138dc447bf0123820c0772cbd/gvps_viterbi.hc#L322-L339)

この議論は因子と候補設定が有効な範囲に限ります。別版libgvpsには到達不能状態用の有限な番兵値もあり、不正な設定で見かけの経路を作らない保証までは確認できません。[番兵値](https://github.com/Sleepwalking/libgvps/blob/2f1b4106d72f8f8138dc447bf0123820c0772cbd/gvps_viterbi.hc#L301-L319)

## 既存の状態モデルにも、候補ごとのApron音響値はない

librosa 0.11.0のpYINは、音高区間ごとに有声・無声の二状態を置き、一様な初期分布と行ごとに正規化した音高遷移に、有声無声の切替行列を組み合わせます。候補を丸めた区間へ割り当てるとき、同じ区間に入った重みは加算せず代入します。有声区間の重みの和をフレームごとの `voiced_prob` とし、残りを無声区間へ均等に配ります。この値は時間方向の経路を選ぶ前の支持です。公開F0と有声フラグはViterbiの選択結果で、全状態の事後周辺確率や全経路の分配和は返しません。別途、前向き・後ろ向き計算を定義するなら、観測行列・遷移行列・初期分布と状態の写像が必要です。[状態と公開出力](https://github.com/librosa/librosa/blob/0.11.0/librosa/core/pitch.py#L865-L893)／[候補の割当て](https://github.com/librosa/librosa/blob/0.11.0/librosa/core/pitch.py#L950-L970)／[遷移の行正規化](https://github.com/librosa/librosa/blob/0.11.0/librosa/sequence.py#L2032-L2051)

原著者の[c4dm/pyin固定版](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/MonoPitchHMM.cpp#L25-L44)も、音高区間ごとの有声・無声状態と重み付き遷移を持ちます。Vamp出力では候補周波数・候補重み・フレームごとの有声支持を、平滑化したF0系列と別に取り出せます。遷移には局所重みの正規化が含まれます。ただし、これらを全経路の事後周辺確率とは扱えません。[観測と遷移](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/MonoPitchHMM.cpp#L48-L135)／[公開項目](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/PYinVamp.cpp#L320-L385)、[値の出力](https://github.com/c4dm/pyin/blob/1d68cac9c5ecb1d81054d25d90158e5838dd78c2/PYinVamp.cpp#L530-L551)

これらは、libgvpsの最大経路得点から重みを作る前に読むべき既存の状態モデルです。状態の明示は品質や確率校正の優位を示しません。どの実装も候補別のLLSM2音響枝や、保存しなかった枝の扱いを解決しません。この記録では前段の置換も新しい復号器も選びません。

## 二系列案は設計上の問いで、実行条件は決まっていない

五つの仮想専門役で二巡しました。実在の五人による査読ではありません。

| 役割 | 第1巡の指摘 | 第2巡で絞った論点 |
| --- | --- | --- |
| 確率 | 候補重みの由来を確認する必要があります。 | モデル内の正規化と、保持した系列の重み・選外の重みを分けます。 |
| 音響物理 | F0の不確かさと雑音のエネルギーは別です。 | 重みを物理的な雑音量へ変換しません。 |
| LLSM2実装 | 候補ごとの音響解析が必要です。 | 二つの系列をそれぞれ解析し、同じApron復号器を使う案に限定します。 |
| 評価 | 復号器がどの系列を使うかが不明です。 | 機構の診断と音質による採否を分け、後者には固定100録音以上の比較が必要です。 |
| 批評 | 保存項目を増やすだけでは前進を示せません。 | 候補生成・系列選択・計算予算が決まるまで採用を認めません。 |

議論後の補正として、モデル内で正規化された経路支持を定義するだけなら経験的な校正は不要と整理しました。一方、その重みの因子、完成F0系列への写像、保持系列と選外系列の重みを明示する必要があります。二つの音響枝を保存しても、確率モデルの全経路の音響表現は揃いません。復号時に元PCMを使えないなら、選ばれ得る系列の音響値をどう用意するかが残ります。

候補の作り方、最終的な重みの分解、復号器による枝の選び方、保存量と計算量の上限は未決です。F0をHzで平均したり、候補波形を平均したり、重みを雑音量へ写したりする方針は置いていません。二系列案は未採用の設計問いです。現ベースApronは維持します。
