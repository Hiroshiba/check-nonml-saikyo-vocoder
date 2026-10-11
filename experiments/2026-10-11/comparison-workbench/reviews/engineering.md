# 実装・再現性レビュー

担当: 5人議論の実装・再現性担当。2026-10-11。これはAIによる設計・調査記録であり、ユーザー指示を追加・上書きしない。

## 結論

まず複数の比較対象と比較方法を作る。WORLDを最初の実行可能な比較対象として構築し、DIO＋StoneMaskとHarvestを分析部の違う2設定として比較する。両者の合成部は同一なので、独立した2種類のボコーダーが揃ったとは数えない。LLSM2を異なる表現・合成部の比較対象として追加し、独自HNMは提案・診断用候補として扱う。比較基盤が動くことと、高品質なボコーダーが完成したことは別である。

正式baseは未選定の初期状態を明示してよい。初回HTMLには「現在の正式base: 未選定」「baseとの差: 該当なし（初期比較）」を表示し、比較対象間の測定値と原音参照値を載せる。未実行や構築失敗を品質劣位に読み替えない。

## 読んだものと実環境

`repo/USER_INSTRUCTIONS.md`を全文確認した。環境をread-onlyで調べた結果は次のとおり。

| 項目 | 確認結果 |
|---|---|
| Python | 3.12.14 |
| NumPy / SciPy | 2.3.5 / 1.17.0 |
| C++ / C | g++ 13.3.0 / gccコマンドあり |
| make / ar / git | あり / あり / 2.51.1 |
| CMake | なし |
| pyworld / Cython / pytest / soundfile | Pythonモジュールなし |

WORLD公式READMEは音高・非周期性・スペクトル包絡による分析合成を説明し、modified-BSDで公開している。Makefileは自己完結したC++ソース群をビルドする。LLSM2公式READMEは位相付き調波＋時間構造を持つ雑音の層と、音源フィルタ側の層を分ける。現行Makefileのライブラリ本体はcigletを利用し、libpyin/libgvpsのリンクは主に同梱テストに必要である。READMEの古い構築手順だけでLLSM2を構築不能と判定しない。

出典（2026-10-11確認、公開一次資料）:

- https://github.com/mmorise/World
- https://github.com/mmorise/World/blob/master/makefile
- https://github.com/mmorise/World/blob/master/LICENSE.txt
- https://github.com/Sleepwalking/libllsm2
- https://github.com/Sleepwalking/libllsm2/blob/master/makefile
- https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/master/setup.py

## WORLDの実装経路

PyWorldが既に導入可能なら既存wrapperを使うのが保守上は簡潔だが、現環境では未導入でCythonもない。一方、WORLDの公開ヘッダはC ABIを提供し、g++は利用可能である。固定commitのソースを取得し、共有ライブラリにして標準ライブラリctypesから呼ぶ経路が現実的。CMakeも独自C shimも必須ではない。実際のコンパイル・ABI呼出はまだ未実施であり、ここは実装可否の静的レビューである。

共通APIは`encode`/`decode`/`edit`を定める一方、保存表現には方式IDとschema versionを持たせる。WORLDのパラメータ形を全方式の共通表現に固定しない。少なくともサンプルレート、元サンプル数、frame period、time origin、FFTサイズ、分析設定、dtype、配列形状を保存する。元波形を表現の隠れた経路として保存しない。

ctypes境界で最も危険なのは、2次元配列を`double**`に誤って渡すことと、構造体ABI・配列寿命の不一致である。連続float64配列を所有したまま各行ポインタの配列を作り、全引数型・戻り型を明示する。オプション構造体は固定commitのヘッダに一致させ、上流のInitialize関数で初期化する。フレーム数・FFTサイズは上流の計算関数を使う。無効入力はCへ渡す前に止める。

公式APIの根拠:

- https://github.com/mmorise/World/blob/master/src/world/dio.h
- https://github.com/mmorise/World/blob/master/src/world/harvest.h
- https://github.com/mmorise/World/blob/master/src/world/cheaptrick.h
- https://github.com/mmorise/World/blob/master/src/world/d4c.h
- https://github.com/mmorise/World/blob/master/src/world/synthesis.h

## 再現性と乱数

WORLDの`Synthesis`は呼出時に局所`RandnState`を作り、`randn_reseed`を実行する。同関数は固定4整数に状態をリセットする。公開offline APIには任意seed引数がない。したがってstock合成を8回呼ぶことを「独立8seed評価」と呼んではいけない。

実装後は同じ入力・設定を同一processと別processで合成しhashを比較する。同じなら「固定RNG、当該環境での再実行一致」と報告する。コンパイラ・OSを跨ぐbit一致やchunk分割合成の連続状態を保証したことにはしない。異なる方式に同じseed番号を与えただけでも共通乱数とは呼べない。fixture生成seedと合成器の乱数方針を別項目で記録する。

- https://github.com/mmorise/World/blob/master/src/synthesis.cpp
- https://github.com/mmorise/World/blob/master/src/matlabfunctions.cpp

実験manifestには、repo commit、上流commit、取得ソースのdigest、build commandとcompiler版、Python/NumPy/SciPy版、入力hash、操作設定、fixture seed、合成RNG方針、出力hashを記録する。`master`や最新releaseだけに依存して再現可能としない。自動評価の途中で依存を更新しない。

## ライセンス・Git境界

WORLDを再配布する場合は原著作権表示・条項・免責を保持する。LLSM2はGPL-3.0表記であるため、コードや依存を無差別に共通Python層へ混ぜない。実際に採用・配布する前に固定revisionの本体・依存それぞれのLICENSEを保存して条件を確認する。コードライセンスから同梱音声の再配布条件を推定しない。音声ごとに出所・許諾・改変・hashを記録する。

ユーザーの追加指示に従い、比較対象の再現wrapper・設定・取得manifestは比較基盤として複数保持し得る。一方、不採用の新提案実装はGit管理せず、理由・数値・レビュー・HTMLは残す。旧baseを単にcomparatorと改名して残す運用はしない。base交代PRでは結果HTML、選定根拠、正式base参照、新base実装、旧base実装削除を一体にする。過去のGit履歴まで改変する必要はない。

## 有効性を直接確かめるCI

依存追加を避ける初期実装なら`unittest`とNumPyの検査機能で足りる。テストはwrapperの行数を追認するものではなく、失敗時に実際の結果が危険になる境界を検査する。

1. ビルドとABI smoke: 既知周期信号、雑音、無音を分析・合成し、有限値、配列寸法、再実行一致を確認する。空列・短すぎる入力・NaN・不整合フレームはPython例外にする。
2. 保存・読込: parameter schemaと配列が保持され、ロード後の出力が同条件の再合成に一致する。
3. 操作: F0=0境界を跨いで偽の低F0を作らない。spがpowerであるためgainは`10^(dB/10)`で変換する。apは上流定義が線形振幅比なので、power比として再混合しない。
4. 長さ・境界: requested samples、raw synthesis samples、crop/pad数を分けて記録する。crop/padで長さだけ揃え、末尾欠損を精密な時間制御と称しない。既知イベント位置と末尾有効区間のエネルギーを別検査する。
5. レポート: 未定義指標を0補完しない。valid/failure件数と理由、正式base参照、実行条件、比較対象全件のstatusをJSON・HTMLに載せる。

初期の合成fixtureのみでは比較基盤の工学検証に限る。自然音声、独立計測、既存評定との対応を未確認のまま高品質を宣言しない。通常CIは短い決定的fixtureに限定し、自然音声の長い比較は別コマンドで再現できるようにする。

## 5人議論での質問と応答

- 音響担当へ「WORLD採用で最小位相などの限界が共通APIへ固定化しないか」と質問。応答は方式別schema＋共通I/Oに分離し、WORLDはまずcomparator、LLSM2未実行を品質劣位にしない。賛成し、上記API方針に反映した。libpyin/libgvpsが本体必須とは限らないとの指摘も現行Makefileで再確認した。
- 制御担当へ補間で最優先すべき反例を質問。F0=0のlog補間によるNaN、0と有声F0の線形補間による偽の低F0が指摘された。voicing maskと有声音高を分離して有声内のみlog補間する。相手からの「crop/padだけで正確な時間制御を称してはならない」という反論に同意し、raw/requested長と境界検査を追加した。
- 評価担当へ自然音声が取得できない場合とseed不能時の扱いを質問。応答は工学評価なら開始可、品質認定は不可、同一出力の反復を独立seedとしない。一次ソースで固定RNGを確認して返答し、fixture seedとの区別も合意した。音声の個別許諾と未定義指標件数の指摘も反映した。
- 批評家からwrapperだけを完成と呼ばないこと、初代比較、乱数と依存固定を問われた。比較基盤完成と音質完成を分離し、base未選定表示、採否前の候補Git非管理、base交代の一体性、固定RNGを回答した。公開比較対象と失敗新提案の区別、旧baseの改名温存禁止、DIO/Harvestが同一decoderであることを追加指摘され、上記に反映した。

上記は実装前レビューである。後続の実装結果を以下に追記する。

## 実装検証の追記

親エージェントから、指示専用PR #2のマージ完了と比較用wrapper実装依頼を受け、`work/world_adapter`に実装した。上流commitは`c794856b537758a3d300757db2e5e31685a822c2`、25ファイルのSHA-256をlockに保存した。ソースとnative binaryはcache内に置きGit管理外。g++の共有libraryビルドが成功し、ctypes直結でDIO+StoneMask/Harvestの両方が動いた。

7件のunittestが合格した。確認対象は既知150Hz信号の両解析、有効寸法と有限出力、保存読込の再現、同一processの同一出力、無効信号・無効パラメータの拒否、出力長とcoverage検査、完全無音である。完全無音はstock safety noiseによりpeak `4.164751651775776e-08`、RMS `1.0917129771067256e-08`であった。初期の数値sanity閾値1e-8はこの上流挙動に適しておらず、検出結果を保持したうえで数値安全性検査をpeak1e-6（-120dBFS）へ訂正した。聴覚的受入閾値として採用したわけではない。

別processの無音合成2回でも出力hashが一致した。自然音声fixture先頭4秒のDIO解析は801frames、うち441有声frameとなり、LLSM2担当へF0/timeを提供した。ここでは自然音声の品質を合格認定していない。HTML比較は評価基盤側で作成する。
