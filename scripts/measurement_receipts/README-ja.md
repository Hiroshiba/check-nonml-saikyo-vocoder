# Torch 終了時の一時モジュール欠落の事後監査

科学値は再計算せず、既存の receipt・summary・個票・run plan・evaluator を変更しない。Torch の instantiator.py は TemporaryDirectory を生成し、atexit cleanup を登録する。最初の該当 stage ではプロセス内 receipt 作成時に存在した生成モジュール2個が終了後に消失した。54 artifact 中52個は実 SHA が一致した。

repair_postexit_receipt.py は元 receipt に登録された全存続 artifact を再ハッシュし、summary 全行と個別保存行の同値を確認する。欠落を許すのは work/tmp/tmp*/ 内の _remote_module_non_scriptable.py と同 __pycache__/_remote_module_non_scriptable.cpython-312.pyc の同一ディレクトリのペアだけ。生成 .py の実測既知 SHA も固定する。任意の work ファイルや科学個票の欠落は許容しない。

root が個別 receipt SHA、plan SHA、tool SHA、stage、chunk、欠落2件の旧SHAを明示した認可を作成してから実行する。各プロセス終了後に同事象が発生した場合も、別途その receipt の認可が必要。非該当欠落があれば停止して調査する。

出力は同 attempt 内の postexit-repair-audit.json と receipt-postexit.json。元 receipt は保持し、新 receipt の artifact に元 receipt、audit、helper、認可、元 plan/runtime、Torch generator source を追加する。元 artifact の欠落記録は audit に旧SHAとともに残る。後段 receipt map は新receiptを明示的に参照し、科学条件は元 plan のまま。修復は事後監査上の例外として公開来歴へ記載する。

呼出形：python repair_postexit_receipt.py --receipt <元receipt> --plan <元plan> --runtime-bundle <固定runtime-bundle> --authorization <root認可>

この修復は科学成功の追加・失敗の救済ではない。新計算を行わず、元の measured / upstream_failed 等の全数値と状態を維持する。
