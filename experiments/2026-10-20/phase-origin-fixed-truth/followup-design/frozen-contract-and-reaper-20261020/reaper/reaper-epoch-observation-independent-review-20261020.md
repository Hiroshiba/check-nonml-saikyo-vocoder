# REAPER epoch観測の独立事実確認

2026-10-20。対象：`reaper-epoch-observation-provenance-20261020.md`。記載された固定sourceをGitHubの読取APIで独立取得し、静的に確認した。実装実行・import・音声処理・計測・tests・Git変更は行っていない。現在のphase studyは変更しない。

## 判定

**主要結論を支持する。重大な誤読は見つからない。** PMLはpyreaperのepoch時刻・mark旗・corrを捨てており、通常保存形式からその原配列を回収できる契約はない。pitch markの無声補充、F0とmarkの別格子、corrをconfidenceとみなせない点も正しい。ただし次の細部は限定・修正すると正確になる。

1. 無声補充の等間隔は区間内の規則であり、全発話共通の0起点格子ではない。
2. corrの直前値埋めは内部のgap処理。先頭zero初期化、同じ格子への上書き、終端延長もある。
3. raw_f0の「元の負値はない」は保存表現の説明としては正しいが、「−1 sentinelすら復元不能」という意味なら強すぎる。確認したwrapperは非正F0を一律−1にしており、この版と未加工raw_f0の来歴が確実なら0を−1へ戻せる。epoch/corrの復元不能性とは別。

## 1. tag・submodule・lock

- [v0.0.11 ref](https://api.github.com/repos/r9y9/pyreaper/git/ref/tags/v0.0.11)のcommitは`0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0`で一致。
- [`.gitmodules`](https://github.com/r9y9/pyreaper/blob/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0/.gitmodules)はr9y9/REAPERを指す。[libのgit tree](https://api.github.com/repos/r9y9/pyreaper/git/trees/1b5cc8f59d610fca2efd765feb986c0fee34c8cd)のgitlinkは`205332b3451989d6b690d0831db4f18aee89aa88`で一致。Google upstreamの現在mainを代用していないのは適切。
- [固定PML commitのuv.lock](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/uv.lock#L466-L472)のversionとsdist hashは資料に一致。

固定commitの内容を確認したのであり、過去実行binary、sdistとtagの全bytes一致、当時のmainの指先を新たに認証したものではない。

## 2. 公開配列と格子

[Python公開説明](https://github.com/r9y9/pyreaper/blob/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0/pyreaper/__init__.py#L19-L96)と[Cython実装](https://github.com/r9y9/pyreaper/blob/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0/pyreaper/creaper.pyx#L94-L207)を確認。

- pm_timesはfloat32秒、pmはint32の0/1。GetFilledEpochsの時刻・旗をコピーする。
- f0_times、f0、corrはfloat32。f0/corrは同じ長さで、時刻はfloatのframe_period×i。数学的に厳密な実数等間隔配列という意味ではなく、指定格子のfloat評価である。
- f0の非正値は−1に置換。corrはそのままコピーし、無声という理由だけでzero化しない。
- pmとf0/corrは別の配列系列であり、同じ添字をepoch別confidenceとして対応させる根拠はない。たまたま長さが等しい例があっても同一格子にはならない。
- float64への昇格は失われた時刻精度を回復しない。

## 3. mark・無声補充・境界

[Backtrack/GetFilledEpochs](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1020-L1135)は資料の説明と整合する。

- backtrackは選んだ終端から最小累積cost経路を追い、各選択periodの始点残差peakとvoicing等を保存する。候補経路を周辺化したposteriorではない。
- 出力経路の現在periodまたは時間上の直前periodがvoicedなら、その保存markの旗は1。独立frame VUVとは違う。これは保存された経路点についての規則であり、観測区間外を含む全有声periodの終端が必ず追加されるという保証ではない。
- 無声補充は基準時刻＋整数倍inter_pulseで旗0。有声再開が見つかれば、その時刻から1/max_f0_searchを引いた位置より手前で補充を止める。初期無声では基準を0にする場合があるが、最初の補充点はinter_pulse後。したがって「発話全域で一定grid」「境界を隙間なく埋める」とは読まない。
- 有声側はresid_index/sample_rateの時刻。これを外部生理計測で確認したGCI真値と同一視しないという留保は正しい。

## 4. F0・corrとpseudo-probability

[Backtrack](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1048-L1075)の有声F0はsample_rate/closest_nccf_period。mark間隔を使う変更はTODOとして残る。従ってF0が隣接mark間隔の逆数と常に一致するという主張はできない。

corrの取得lagは選択periodのlagで、探索範囲外ならclosest_nccf_period側。F0を決めるlagとcorrを読むlagも無条件に同じではない。[規則格子化](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1138-L1179)はzero初期化後、各経路点を丸めたframeへ割当て、内部gapを前値で埋め、終端へ前値を延長する。同じframeは後の経路点で上書きされ得る。先頭frame 0が経路点で書かれなければ初期zeroが残るため、全域を一様な前値補間と呼ばない。[RoundUp](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L41-L43)は名前に反してceilではなく、非負値に0.5を加えて整数castする規則。

[header](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.h#L287-L290)がprob_voicedをpseudo-probabilityと呼ぶ点は一致。[実装](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L436-L465)は帯域RMSの発話内min/max、min_rms_dbのfloor、rangeの下限、結果の負値clipを使う。単純な無条件min-max変換より少し詳しいが、確率校正やposteriorではないという結論は変わらない。

## 5. 診断とPML保存

[CLI説明](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker_main.cc#L29-L88)、[EST ASCII出力](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/core/track.cc#L236-L265)、[WriteDiagnostics](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1209-L1246)の記述も整合。f0ap/pmlabは内部経路由来であり、無声補充済みpm列とは別。通常wrapperの5戻り値にも含まれない。

[codec](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/codec.py#L37-L78)の戻り値捨て、int16化、REAPER引数、raw_f0の負値→0、任意traceへの格納は確認した。[F0後処理](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/pml_analysis.py#L14-L80)は補間・平滑化等を行い、[parameters](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/parameters.py#L14-L64)と[storage](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/storage.py#L16-L40)はepoch/corr/raw VUV列を保持しない。[synthesis](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/pml_synthesis.py#L103-L110)のpulse列は0起点の再帰合成clock。

「過去保存から復元不可」は、**原戻り値の別保存がなく、通常PMLファイルまたはraw_f0だけを持つ場合に、原epoch/corrを逆変換で回収できる根拠がない**という意味で支持する。全過去artifactを棚卸しして不在を証明したわけではない。元音声からの再解析は別来歴であり、過去bytesの回収と呼ばない。

raw_f0が未加工で残り、確認したwrapper版が確実なら、0→−1によってwrapperのF0 sentinelは戻せる。この小さな例外はmark時刻・mark旗・NCCFの回収を可能にせず、通常PMLファイルの正の合成F0から元VUVを回復することも意味しない。

## 範囲と停止線

source取得は読取りだけ。web経由の取得失敗後にGitHub読取APIで同じ固定URLの内容を確認した。既存音声や保存artifact、過去環境の実体は調べていない。新しい推定器・実験・性能主張・phase studyへの追加・source変更を提案しない。
