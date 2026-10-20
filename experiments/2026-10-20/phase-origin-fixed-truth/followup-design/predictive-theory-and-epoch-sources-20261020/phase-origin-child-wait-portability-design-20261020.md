# 将来の子終了監視：proc children非依存の条件付き代案

2026-10-20。**採否未決定、紙上設計のみ。** 実装・実行・tests・科学再試行なし。既存runのsource/receiptは変更しない。

## 判断
同じ生存中の親/subreaperがwaitpid(-1,WNOHANG)で実wait結果を集める案は、proc children列挙への依存を減らせる。ただしECHILDだけを全履歴の成功証明にせず、SIGCHLD設定、唯一reaper、直接子status、子孫のadoption、期限を契約化することが条件。

## 一次仕様
- pid>0は返されたraw wait statusを記録し、終了かsignalかを判別する。traced stop等の非終端statusをreaped終了としない。0は未終端子があり得るので完了ではない。ECHILDはその呼出親・選択条件で待つ対象がないという観測。SIGCHLDを明示SIG_IGN、またはSA_NOCLDWAITにすると終了statusが失われ、ECHILDになり得る。SIG_DFLの既定ignoreと明示SIG_IGNは異なる。Linuxの通常waitは非SIGCHLD clone子を選択しない場合もある。[Linux wait(2)](https://man7.org/linux/man-pages/man2/waitpid.2.html)
- subreaperは孤児化した子孫の引取先となるが、まだ別の生存親を持つ孫を直ちにwaitできるわけではない。fork/clone子へ属性は継承されず、execには保持される。outer/supervisorそれぞれで明示設定と結果確認が必要。[PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html)
- PDEATHSIGはfork子では消えるため各子のsetupで再設定する。普通のexecでは保持されるが、setuid/setgid・file capabilitiesや特定credential変更では消える。親threadの死にも反応し、設定前に親が死んだraceは自動救済されない。設定直後の親同一性確認とhandshakeは維持する。[PR_SET_PDEATHSIG](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html)

## Popen競合の重要点
CPython3.12.14のPopen.poll内部はECHILDでreturncode=0にする経路を持ち、wait側もChildProcessErrorをstatus0に置き換える。別のwaitpidが先に直接子をreapしてからPopenに任せると、本来の非0/signal終了を0へ見せる危険がある。Popenの内部lockは外部os.waitpidとの競合を自動では防がない。[公式 subprocess.py](https://github.com/python/cpython/blob/v3.12.14/Lib/subprocess.py)

**設計候補はどちらか一つに固定する。**
1. 直接子は既存Popenのみがreapし、その実status確定後にadopted子だけをwaitpid(-1)でdrainする段階分離。直接子が未終了の間は全子waitを混在させない。Popenの0が本当のwait結果かをSIGCHLD/単一reaper前提で保証する必要がある。
2. 監視層を唯一のreaperとし、全waitpidのPID/rawstatusを台帳へ保存、直接子のreturncodeもそのstatusからだけ決定する。Popen.poll/wait/communicate等の再reap経路を使わない設計が必要。Popen objectの管理・終了時処理まで含め別sourceレビューする。根拠なしにreturncode=0を代入しない。

最小変更としては1が比較的小さいが、例外経路も同じ順序を守ること。新しい中央reaper実装を今回勝手に追加しない。

## 凍結すべき監視条件
- 生成前にSIGCHLD dispositionとsigaction flagsを確認し、SIG_IGN/SA_NOCLDWAIT、statusを消費するhandler/別thread/他のreaperを拒否する。PythonのgetsignalだけではSA_NOCLDWAIT確認を代替できない。設定変更を黙って行わず、将来の明示契約で扱う。
- 対象は既知の通常fork/exec子に限定し、未知clone子や任意daemonを許さない。PID/starttime/owner/parent台帳、subreaperとPDEATHSIGの設定成功証拠を保持する。
- drainは返却PID>0を毎回rawstatus・時刻付きで保持。0なら期限内で待ち、既知の同一性を確認できるgroupのみ停止する。0から未知PIDを推測してkillしない。
- ECHILDは「同じ親に残る待機対象なし」の終端観測として保存するが、既知の直接子statusが欠ける/未知reaperがあるなら成功にしない。既知親が全て終端する前のECHILDを子孫全体の証明としない。
- deadlineで0、EINTR等が継続、未知errno、adopted子の出自不明ならunknownを保持。親の実終了・outer wait・fsync時計も別に確認する。
- 追加のwait/stack/receiptは従来の時間・容量枠内。ログ不備がkill/waitを阻害しない。PID不在・proc空一覧は実waitの代替にしない。

## 過去runへの適用禁止
過去の親は既に終了している。今起動した別processでECHILDが出ても、その新processの子についての観測にすぎず、過去ownerのreap証明を補完しない。既存immutable=false/cleanup unknownを後付けで成功へ変更しない。本案は将来sourceだけの再レビュー候補であり、新しい計測の承認ではない。
