# 現base PMLの位相・F0・有声確率の契約監査

2026-10-20 10:56–10:58 UTC。GitHub connectorによる読取りと本資料の保存のみ。ソース実行・import・tests/smoke・音声生成・計測・Git変更はしていない。PMLを唯一のbaseとして維持し、PR67は既存制限どおりDraftのまま変更・mergeしない。本資料は新実験やPML変更の承認ではない。

## 結論

**現base PMLから、測定された共通位相原点・全周期の生理的境界・有声確率・F0候補分布は取得できない。** 取得できるのは正の合成F0時計、振幅包絡表現、雑音マスク、および任意の診断値である。内部の調波位相や復号時のpulse_timesをoracle phaseへ読み替えない。

これは新発見ではない。既存の `cyclic_noise_identification_design_20261020.md` 第7節（116–118行）に同じ結論があり、`phase-uncertainty-control-20261020.md` 第1節が引用していた。今回は可変main参照を固定commitの証拠へ更新した。合成ファイルのblob SHA `966ffa84578ad365a7062c04d70582976d64ac4a` は既存監査と同じである。

したがって既存設計の「trainからPMLでF0と位相原点を得る」E読出しは未対応のまま。この一点を未確認のTODOとして再調査し続ける必要はない。既知clockのoracle共分散理論や既知phaseの未知平均解析は独立に有効だが、PMLによってその前提を外したことにはならない。

## 確認対象

GitHub mainを確認した時点のcommitは [d749113af9fa365ea76ddbd4454802da70c3376a](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/commit/d749113af9fa365ea76ddbd4454802da70c3376a)（2026-10-20 10:30:41 UTC）。以下のSはこの固定commitの `vocoderbench/pml/` を表す。

- [USER_INSTRUCTIONS.md](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/USER_INSTRUCTIONS.md) を最初に確認。STATUSはrootにはなく、treeで確認した [docs/STATUS.md](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/docs/STATUS.md#L3-L43) を使用。7行・27–32行・43行のPML維持、人工診断と音質の区別に整合する。
- [current_base.py 9–26行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/references/current_base.py#L9-L26)：selected PMLのみを認め、現在のpml.encode/decodeへ接続する。別研究の確率的pitch診断をbase APIに混ぜていない。
- 既存3資料の該当箇所を参照。未知平均資料の単純周期平均は「既知phase・固定L」を保持するため、そこで得た共有誤差の式もPMLの位相性能を示さない。

## 入出力と時間軸

1. **公開保存契約**：[S/parameters.py 7–28, 41–64行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/parameters.py#L7-L64) はfs=16000 Hz、FFT=4096、step=0.005秒、F0 float64、FWCEP `(frames,60)` float32、noise_mask `(frames,2049)` boolを規定する。F0は50 Hz超・700 Hz未満を要求する。時刻は0起点の `arange(frames)*0.005`、従って名目hopは80 samples。位相列、候補重み、voicing probabilityのフィールドはない。
2. **時刻の保証範囲**：[S/codec.py 37–78行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/codec.py#L37-L78) はREAPER出力中のtimesとf0だけを取り、後処理後の時間軸と上記0起点gridをbit単位で照合する。これはファイル内の時刻規約であり、声門閉鎖が0秒にあるという意味でも、推定遅延の校正でもない。保存は [S/storage.py 16–34行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/storage.py#L16-L34) の3配列とメタデータに限られる。
3. **単位**：保存f0はHz（cycles/second）、times/pulse_timesは秒。公開APIにradians/cyclesのphase列はない。内部の `angle/unwrap/exp(1j*x)` はradians。研究資料のcycles位相と等置せず、角度変換だけで失われた原点が復元するとはしない。

## F0、無声、欠測、有声確率

- [S/pml_analysis.py 14–78行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_analysis.py#L14-L78)：負F0をcodecで0にした後、正のF0から線形補間（端は端値）し、全未検出なら65 Hz、65–700 Hzへclip、filtfiltによる段差除去、必要なら等間隔へ再標本化する。最後は有限かつ正値が必須。後処理後の範囲逸脱を無条件に再clipする契約ではなく、公開パラメーター側の検証もある。
- 従って保存値だけでは、元の無声音・未検出フレームを復元できない。任意のencode traceにはraw_f0とraw_unvoiced集計等があるが、raw_f0はすでに負値を0へ変換済み。検出器の点判断・未検出記号であり、校正された有声確率ではない。
- [S/pml_analysis.py 105–123行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_analysis.py#L105-L123)：StoneMaskのrefined F0はCheapTrick包絡だけに使用。PDD・保存・合成のclockは後処理済み元F0である。ここにも複数候補やposteriorはない。
- encodeは全波形入力を要求し、補間・非因果filtfilt・中心窓を使う。通常online trackerの遅延保証やtrain終端から独立testへのclock外挿仕様は提供しない。decodeの端値補間をその統計的外挿保証と呼ばない。

## 内部位相は何を意味するか

- [S/pml_pdd.py 16–31行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_pdd.py#L16-L31)：解析格子も0秒から `1/(4F0)` 刻みで作る。PDDを5 ms格子へ戻す際はnearestではなく「target以上の最初の時刻」を選ぶ。これは実測GCIに同期する処理ではない。
- [同71–117行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_pdd.py#L71-L117)：2.5周期の奇数長Blackman窓を `int(0.5+fs*t)` に中心化し、端はzero padding。DFT位相へ窓中心補正を加え、周波数方向にunwrap・補間・wrapする。これは局所音響調波の位相であり、生理的位相原点ではない。空窓には乱数位相を置く。
- [同136–190行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_pdd.py#L136-L190)：DC位相を0にし、`rp=p−h*p1` で基本波位相に対する相対位相へ変換、調波差分と時間trend除去、円周統計からPDDを得る。元の調波phase列や基本波原点はanalyze_pddから返さず、encode traceにも保存しない。PDDは位相ばらつきの量で、位相そのものでもvoicing probabilityでもない。
- [S/pml_analysis.py 81–96行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_analysis.py#L81-L96)：PDD閾値0.75と形態演算等から二値noise_maskを作る。boolや平滑化後の0–1値を「有声である確率」と解釈する校正契約はない。

## 合成位相の自由度と生理的clockの境界

[S/pml_synthesis.py 103–145行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_synthesis.py#L103-L145) は `ts=[0.0]` から `t_next=t+1/interpF0(t)` でパルスを置く。traceのpulse_timesはその列である。変動F0の厳密な積分phaseの整数交差と一般に同一ではなく、全音声長を覆うため末尾を越えるパルスも生成して加算時に範囲を切る。コードのコメントにGCIとあっても、入力から検出・校正したGCIの列ではない。

[同178–254行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/pml_synthesis.py#L178-L254) はsubsample遅延、振幅から作る最小位相包絡、エネルギー補正、正規化Gaussian雑音の複素スペクトルをマスクでべき乗する処理を使う。解析の絶対調波位相を再現する入力はない。公開decodeには独立のphase-origin指定もなく、原点は固定規約、雑音実現はseedで変わる。周期間隔・noise shaping・最小位相は合成モデルの選択であり、真の声帯時計やaspiration原因の同定を保証しない。

## 採用元の証拠と未確認

[S/PORT_MAP.md 5–32行](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/d749113af9fa365ea76ddbd4454802da70c3376a/vocoderbench/pml/PORT_MAP.md#L5-L32) はPML上流を `gillesdegottex/pulsemodel@f1d0fbb397368e019efa4dfc96bde09482cd734b`、sigprocを `289d9dffe1f6ba84fa1fe962d6fb6e1062ec1cf6` に固定する。PML上流の [synthesis.py 131–138行](https://github.com/gillesdegottex/pulsemodel/blob/f1d0fbb397368e019efa4dfc96bde09482cd734b/synthesis.py#L131-L138) を直接読み、同じ0始点時計を確認した。上流222行・248行も最小位相化・複素雑音変調を実装する。

sigprocの固定tree取得はGitHub API 404で内容未確認。拒否を迂回する取得・別revisionへの差替えはしていない。従ってsigprocとの全演算一致は今回認証しない。この未確認は、実際の現baseの公開入出力・保存・合成原点の監査結論を妨げない。REAPER内部の能力一般、別版のAPI、未採用実装に位相や候補を追加できる可能性も今回の結論の対象外である。

## 停止点

「PML phaseをそのままEの独立測定位相として使えるか」は **不可** として閉じる。新仮説・実験案は追加しないため、新たな5役討論も行わない。

次の最小問いが必要なら一つだけ：**既存の人工既知q・既知一定F0・同始点独立反復に限定したtrain-only原点校正について、全候補共通の目的関数・同値解・失敗規則・clock依存共分散と周期境界を、oracle境界を流用せず文書で固定できるか。** これは既存phase不確実性資料の未確定契約を埋める問いであり、新規提案ではない。必要な証拠はその仕様と代数上の整合性。ここまでを停止線とし、実装・校正run・F0未知化・自然音声評価・PML変更へ進まない。既存結果から音質改善を主張しない。
