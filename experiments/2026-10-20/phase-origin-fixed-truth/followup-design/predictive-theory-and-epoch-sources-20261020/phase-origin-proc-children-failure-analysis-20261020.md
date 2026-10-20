# phase owner終了証拠：proc children読取失敗の暫定整理

2026-10-20。原因は未確定。source v2とLinux公式文書の読取のみ。候補実行/import、再計測、PRNG、新テスト、proc環境への観測コマンド、receipt修正は行っていない。

## 現時点の区別
親報告はowner1/2ともworker exit0、outer exit2、children読取失敗によりall_child_waits_complete=false/immutable=falseで通常packing拒否、原証拠回収中というもの。本担当は今回の実行原artifact/errno/tracebackをまだ独立照合していない。167/166行や値の完了報告と、子孫process全終了の証明は別である。

source `lifecycle.py:57–59` は `/proc/self/task/{os.getpid()}/children` を読む。直接子の `proc.wait` 後、同90行と128行で列挙し、読取例外ならpending=Noneとerrorを残す。all_reapedにはpending==[]かつerrorsなしが必要なので、今回報告されたfail-closedはsourceに整合する。これは「workerが動き続けている」という断定ではなく、追加子の終了証明が完成していないという状態。

## 一次仕様と原因候補
1. **kernel機能不在**：childrenはLinux 3.5以降の機能で、4.2以降CONFIG_PROC_CHILDREN、それ以前CONFIG_CHECKPOINT_RESTOREに依存する。ファイル不在だけではcloudの故障・仮想化とは断定できない。[Linux man-pages: proc_tid_children](https://man7.org/linux/man-pages/man5/proc_tid_children.5.html)
2. **PID namespaceの数字不一致**：proc mountが見せるPID namespaceとcallerのnamespaceは異なり得る。/proc/selfのリンク先はproc mount側namespaceのPIDなので、そこへcallerのos.getpid()をtask名として継ぎ足す設計は同一namespaceを暗黙に仮定する。不一致ならENOENTの候補になるが、今回一致/不一致は未確認。[Linux man-pages: pid_namespaces](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)
3. **TID/main-thread前提**：task配下はthread ID。/proc/thread-selfは実際の呼出threadを指す。main thread終了後にはtaskが利用不能な場合もある。今回sourceはmain threadでcleanupする通常CLI設計なので、一般的なthread差だけを第一原因とは断定しない。[Linux man-pages: proc_pid_task](https://man7.org/linux/man-pages/man5/proc_pid_task.5.html)
4. **mount制限・権限・cloud proc仮想化**：パスの一部非公開、proc互換実装の不足、アクセス制御も候補。ただしこれらは今回の実証のない推測。errnoがENOENT、EACCES、EPERM、EIO等のどれかで優先順位は変わる。namespaceが存在することだけで「仮想procが原因」とはいえない。

さらにchildrenは、子がexit中に読むと残存子まで列挙から漏れ得ると公式文書が注意する。従って将来も「一度空で読めた」を一般的な全reap証明として過大評価しない。これは今回の**読取例外原因**とは別の設計上の限界である。[同 children仕様](https://man7.org/linux/man-pages/man5/proc_tid_children.5.html)

## 最小のread-only証拠（収集提案、今回は未実施）
まず既存の原保存物を優先する：
- supervisor/outerの原stderr全文、例外型・errno・完全な失敗path・tracebackと時刻。
- 両段のcleanup/direct_returncode/direct_reaped/errors/pending/adopted_waits、および親toolの実wait原文。
- birth/ack/exec-authorizedのPID/start_ticks/PPID、当時のstat/cmdline、RUNとsource SHA。

原因切分けの環境資料が既にあれば取得し、なければ別途許可した限定read-only観測として、同じ環境のkernel release、proc mountinfoの該当行、既存kernel configのCONFIG_PROC_CHILDREN、namespace pid/mntリンク、/proc/selfと/thread-selfのreadlink、statusのPid/Tgid/NSpid/NStgid/Threads、task子名とchildrenの存在/読取errnoを時刻付きで記録する。**selfは読むprocess自身**なので、別々のshellコマンドのPID値を同一process値として比較しない。別観測processは元runの当時状態を復元しない。存在しないconfigを新たに生成/インストールせず、mount/setns/security変更は行わない。

今のPID不在、psに出ないこと、後日の空childrenから当時の実reapやexitcodeを作らない。原receiptはそのまま、別監査ノートとして証拠の由来と観測時刻を保持する。

## 将来の修正候補（今回runへ遡及しない）
- proc機能とnamespace前提の検証を将来の環境契約へ加える。children不在を[]へ置換するfallbackは禁止。
- thread-self等を使う場合も、呼出threadと子の所有・adoptionの対応を明示する。単なるパス変更で全子終了証明が完成するとはしない。
- 既存のdurable PID/starttime台帳と直接子実waitを主証拠として、subreaperのadopted子に対するwaitpid/waitidの状態を組み合わせる設計を検討する。WNOHANGの0は「未終了の子が存在し得る」、ECHILDもSIGCHLD設定/所有関係を含めて解釈する必要がある。新しい監視sourceを別レビューし、現在のproc失敗receiptを上書きしない。[Linux man-pages: wait](https://man7.org/linux/man-pages/man2/waitpid.2.html)
- 正常worker計算とrun監視失敗は分離して保存する。今は契約済みの親側失敗証拠保全経路で、必要ならmutable snapshotとして原物を回収する。通常packing gateを削らず、科学再実行をしない。

## 現結論
原因断定なし。source側のproc機能/namespace前提が環境で満たされなかった可能性はあるが未実証。workerの実wait0が一次証拠で確認できればその限定事実は保持できる一方、all_child_waits_complete/immutable=falseは現時点で維持する。
