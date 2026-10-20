# REAPERのepoch観測と保存来歴

2026-10-20 12:04–12:06 UTC。公式一次ソースの読取りのみ。実装変更・候補実行・tests/smoke・新計測・音声処理・Git変更は行っていない。本資料は今の固定phase studyへの追加でも、将来の実装・実行承認でもない。PMLを唯一のbaseとして維持し、PR67には触れない。

## 結論

**PMLが呼ぶpyreaperには既にpitch-mark時刻列、二値VUV旗、F0格子の相関値がある。しかし現PMLは時刻列・VUV旗・相関値を捨てている。** 将来、同じ呼出しの戻り値を保存するなら推定器を二度動かす必要はない。一方、既存のPML保存ファイルから失ったepoch列を逆算して回収することはできない。

さらに重要なのは、**pitch-mark列の無声部分は等間隔の人工補充点**ということ。有声側の点も最適経路から選んだ音響的推定値であり、生理的GCI真値ではない。`corr` はNCCFの値で、epoch時刻の校正済confidenceやVUV posteriorではない。

出発点は `pml-phase-contract-audit-20261020.md`。前の「PMLの公開保存契約に測定位相原点なし」という結論は変わらない。今回は、その一段手前で捨てられる情報だけを特定した。

## 固定した一次ソース

1. 現repo main確認値：[7ff437a4d2652947118c26c331f31a5607798a3d](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/commit/7ff437a4d2652947118c26c331f31a5607798a3d)。[uv.lock 466–472行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/uv.lock#L466-L472) はpyreaper 0.0.11、sdist SHA256 `e306d20d7e77a73a2af18a3e6d88731a456eebed95e8a8ae1ed070a51e929857` を記録。
2. pyreaper公式tag v0.0.11：[0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0](https://github.com/r9y9/pyreaper/tree/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0)。このtagの`.gitmodules`とgit treeから、同梱REAPERはGoogle upstreamの最新mainそのものではなく、作者fork `r9y9/REAPER` の [205332b3451989d6b690d0831db4f18aee89aa88](https://github.com/r9y9/REAPER/tree/205332b3451989d6b690d0831db4f18aee89aa88) と確認した。
3. 以下はこのtagと同梱forkの静的契約。配布sdistを取得してtagとの全bytes一致を検査したわけでも、既存実測環境のbinaryを確認したわけでもない。過去の実行が必ずこのソース・ABIと同一だったとは認証しない。

## Python公開戻り値と粒度

[pyreaper/__init__.py 19–96行](https://github.com/r9y9/pyreaper/blob/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0/pyreaper/__init__.py#L19-L96)、[creaper.pyx 127–207行](https://github.com/r9y9/pyreaper/blob/0975a3c62c068c04c3c0fa4323164c4cc1c4b7f0/pyreaper/creaper.pyx#L127-L207) の戻り値は：

- `pm_times`：float32、発話始点からの秒、pitch-mark列。
- `pm`：int32、対応するmarkの0/1旗。0=unvoiced、1=voiced。
- `f0_times`：float32秒。`frame_period*i` の0起点の規則格子。
- `f0`：float32、Hz。wrapperは非正値を−1にする。
- `corr`：float32、f0と同じ長さ・同じ時刻格子のcorrelation。

`pm_times/pm` と `f0_times/f0/corr` は別の格子・長さである。`corr[j]` を `pm_times[j]` のconfidenceとして添付してはならない。float64へ昇格しても元のfloat32量子化は戻らない。

## pitch markとVUV旗はどう作られるか

[同梱epoch_tracker.cc 1020–1085行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1020-L1085) は最小累積costの経路を終端からbacktrackし、残差peak index、voiced bool、F0、NCCF値を保存する。複数経路を周辺化したposteriorではない。F0は対応NCCF周期から求めており、隣接mark間隔の逆数と常に同一とも限らない。

[同1089–1135行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1089-L1135) のGetFilledEpochsでは：

- 保存された経路点について、現在periodがvoicedまたは直前periodがvoicedならmarkに1を付ける。これは有声periodの両端を扱うための規則であり、観測区間外を含む全有声periodの終端が必ず追加される保証ではない。「その時刻の独立frame VUV判定」とも異なる。
- 無声領域は区間ごとの基準時刻に `unvoiced_pm_interval` の整数倍を加えて補充し0を付ける。現PMLの設定は0.01秒。有声再開が見つかれば、その時刻より `1/max_f0_search` 前の位置を補充の上限とする。初期無声の基準を0にする場合も最初の補充点はinterval後であり、全発話共通の0起点格子や隙間のない境界補充ではない。検出epochではなく処理用のmarkである。
- 有声mark時刻は `resid_index/sample_rate`。標本位置からの音響的推定時刻であり、外部生理計測と時間校正済みではない。

## 相関と「確率」という名前の限界

[同1064–1075行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1064-L1075) のnccf_valueは選択periodのlag（範囲外では近傍NCCF peak lag）の相関値である。F0を決めるlagとcorrを読むlagも常に同じではない。[同1138–1179行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1138-L1179) はzero初期化後、経路点を丸めたframeへ割り当て、内部gapを直前値で埋め、終端へ値を延長する。同じframeは後の経路点で上書きされ得る。先頭frame 0が書かれなければ初期zeroが残るので、全域一様な前値補間ではない。`RoundUp` は [41–43行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L41-L43) の非負値に0.5を加えて整数castする規則で、ceilではない。全epochごとの元の値を保存した配列ではなく、ソースの「nearest」という概説だけで補間規則を決めない。

別に内部 `prob_voiced_` があるが、[header 287–290行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.h#L287-L290) は明確にpseudo-probabilityと呼ぶ。[実装436–465行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L436-L465) は発話全体の帯域制限RMSの最小・最大からscale/offsetするヒューリスティックで、ラベル付き真値による確率校正やposterior計算ではない。標準Python戻り値の`pm`や`corr`と同じものではない。

## ファイル出力と内部診断

同梱CLIの [epoch_tracker_main.cc 29–88行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker_main.cc#L29-L88) は `-p` pitch marks、`-f` F0、`-c` correlations、`-a` ASCII、`-d` 診断出力を区別する。通常trackはEST形式、ASCIIは [core/track.cc 236–265行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/core/track.cc#L236-L265) の時刻・VUV旗・channel値を出す。pitch-mark trackの意味のある観測は時刻と旗であり、余分なchannelをconfidenceだと推測しない。

`-d`で書ける内部診断には`.pvoiced`、`.onsetp`、`.offsetp`、`.bestcorr`、`.f0ap`、`.pmlab`等がある。[WriteDiagnostics 1209–1246行](https://github.com/r9y9/REAPER/blob/205332b3451989d6b690d0831db4f18aee89aa88/epoch_tracker/epoch_tracker.cc#L1209-L1246) の`.f0ap`はepochごとの時刻/F0/NCCF、`.pmlab`は経路の時刻をblue/redで出す。これはGetFilledEpochsの無声補充列とも別物。これらはpyreaper.reaperの通常5戻り値には含まれず、同wrapperは末尾でCleanUpする。内部に存在することだけで現在PMLが保存しているとは言わない。

## 現PMLで保持・破棄されるもの

[codec.py 37–78行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/7ff437a4d2652947118c26c331f31a5607798a3d/vocoderbench/pml/codec.py#L37-L78) は `_, _, times, f0, _ = pyreaper.reaper(...)`。従ってpm_times、pm、corrは捨てられる。REAPER設定はmin/max 65/700 Hz、high-passあり、Hilbertなし、inter_pulse 10 ms、frame_period 5 ms、unvoiced_cost 0.9。入力int16化は `rint(x*32767)`。

- 任意のencode traceには負F0を0へ変換したraw_f0（時刻/F0）を残す。これが実際に保存済みならF0規則格子の正/非正という点判断は読めるが、epoch列・mark旗・NCCFはない。ただし確認したwrapperは非正F0を一律−1にするため、この版と未加工raw_f0の来歴が確実なら0→−1でwrapperのF0 sentinelは復元できる。「元の負値をそのまま保存していない」と「sentinelすら復元できない」は区別する。この例外は通常PMLファイルの正の合成F0から元VUVを回復できる意味ではない。
- 通常PMLParameters/ファイルはさらに補間・平滑化した正の合成F0、FWCEP、noise_mask等だけ。元VUVの0は失われる。
- decodeのpulse_timesは前資料どおり0起点の合成clock。捨てたREAPER epochを復元したものではない。

## 回収可能性と停止線

1. **将来の同じREAPER呼出しで保存だけ追加すれば保持できるもの**：5戻り値全部、元dtype、入力音声hash・int16化規則・fs・全設定・package/source版。pm_timesとpmは常に対で保持し、corrはf0_timesと対にする。これは「既に返る情報」の範囲で、追跡器本体の変更や2回目の解析を必要としない。ただし現在のadapterに保存経路を足す変更は必要で、今回は実施・承認しない。
2. **過去分で原戻り値が未保存なら再実行が必要なもの**：epoch時刻、mark旗、corr。元音声・同一前処理・版が必要。再実行は新たな来歴の観測であり、過去runの失われたbytesと同一だと無確認で扱わない。内部pseudo-probabilityやper-epoch NCCF等は標準5戻り値だけでは得られず、診断出力・wrapper対応を別契約にする必要がある。既に別保存があるかの棚卸しは今回していない。
3. **外部根拠・校正が必要な主張**：真のGCIとの対応精度、時刻bias・不確かさ、VUVの確率校正、epochごとのconfidence、欠落/余分なmark率、自然音声の生理的原因同定。音響mark・NCCF・pseudo-probabilityだけでは成立しない。全周期のground truthやF0候補posteriorも通常戻り値からは得られない。

今回の問いは「どの既存出力を保持できるか」の読取りで閉じる。新仮説や性能改善は提案・主張しない。今の既知q・固定F0の人工位相原点対照へREAPERを追加しない。

### 独立確認後の限定修正（2026-10-20 12:10 UTC）

`reaper-epoch-observation-independent-review-20261020.md` の固定一次sourceによる独立確認を読み、無声補充の区間基準・境界、corrのzero初期化と上書き、wrapperの−1 sentinelの可逆性を本文へ反映した。主要結論は不変。原戻り値の別保存がなく通常PMLファイルまたはraw_f0だけを持つ場合に、原epoch・mark旗・corrを逆変換で回収する根拠はないという限定である。全過去artifactを棚卸しして不在を証明したわけではない。修正は文書だけで、source実行・計測・Git変更はしていない。
