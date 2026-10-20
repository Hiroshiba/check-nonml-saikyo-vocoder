# 同一モデルlog領域比較：実行前契約

未実行。親によるソース確認後の実行指示を待つ。基準PMLは維持し、音質比較・採用判断を行わない。

Aは固定済み保存結果の参照だけ。Bのみ、保存logBFを用いてU-U/E-U/E-E各frame0..102を一巡する。Gaussian log kernelは元のF0 SD2Hz/K SD1と同じ有限gridから行正規化する。初期prior .7/4610、H0 .3、T=.7 AᵀPB、R=.4hM、H0予測=.3(1-h)+.6h、H0<.5時の有声条件付き記憶更新を同一実数式として保持。H1和と1-hは実数上同じなのでlogsumexpを用い、減算の桁落ちを避ける。これはbaselineと演算順序・丸めが異なり、bit一致再現ではない。

保存energy_floorを元のenergy/N<1e-10と照合し、該当frameは更新せずskip数のみ増やす。保存失敗・欠落は停止。音声・射影・local posterior・logBFは再計算しない。新しいsigma/floor/reset/temperature/windowはない。E-Eの最小周期195.3125Hzを参照し、97.65625Hzへの復帰を成功条件にしない。

Gaussian支持は実数上正。log値に予期しない非有限が出たら停止。初回T/Rは適用なしでNPZキーを省略。表示用expはunderflowを許容し、有限log値と表示zero数を別記する。主MAPはlog jointに対し列優先first maximum。表示expによる丸めtieが違う可能性をdisplay_MAPで区別する。TVは保存baselineをclip/再正規化せず、H0を含む半L1を保存する。

全log prior/joint/T/R/状態記憶をNPZ、H0/参照元/MAP/表示zero/TVをJSONへ保存。receiptは各frameのhashを持つ。309更新を越えない。失敗時は全体停止し、途中までのreceiptとstack traceを保持。失敗直前の未commitファイルはreceipt外であり完了値として使わない。自動retry/resumeなし。

既存storage.pyをSHA確認して再利用。wall1800秒、address space2GiB、出力1GiB（8MiB予約）。各更新前に2MiBの追加出力余裕を確認し、遷移はtarget F0を16セルずつ処理。budgetは依存import前に開始、入力SHA読取りは開始前。現行Python3.12.14/NumPy2.3.5/SciPy1.17.0のみ。BLAS等6thread設定を1に固定。依存導入なし。

ソース・入力ファイルSHAはSOURCE_MANIFEST.jsonに固定（自己hashを除く）。親は別送manifest SHAも照合すること。新規出力ディレクトリ必須、既存データ上書きなし。manifest対象はrun.py/log_filter.py/本契約、固定storage/model/measurements、入力result/inputs/各receipt/全309 JSONとNPZ。model/measurementsは由来確認だけでimportしない。

予定コマンド（まだ実行しない）:
/workspace/quality-env-v1/venv/bin/python -B /workspace/pitch-log-comparison-job-20261020/run.py --output /workspace/pitch-log-comparison-results-20261020

静的確認のみ許可。テスト・smoke・モデルimport・科学runはしない。GitHub・Library操作も対象外。
