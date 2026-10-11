# 既存方式と比較基盤の初回検証

記録日：2026-10-11（日本時間）。実行開始・終了時刻は初回記録に残っていません。

WORLDとLLSMを同じ入力で比較し、再現・操作の測定と測定器そのものの検査ができるようにするグループです。正式ベース手法は未選定です。

- [初回比較結果](results/run-001/index.html)：32入力・4経路の再合成128行、操作50件、デコーダー単体2件。
- [調査の位置付け](research.md) と [5人の議論](reviews/discussion.md)。
- [独立した測定器監査](reviews/AUDIT_RESULTS.md)。

自然音声の2区間ではLLSMのスペクトル誤差がWORLDより小さかった一方、音高の欠測、無音への微小雑音、LLSMの操作未対応などが残っています。少数例から品質順位や知覚品質を確定しません。次の作業は [現在の状態](../../../docs/STATUS.md) を参照してください。

## 移設記録

旧 `reports/initial-comparison/` を `results/run-001/` へ、旧 `docs/reviews/` を `reviews/` へ移しました。測定JSON・校正JSON・監査JSON・検証JSONは内容を変えていません。JSON内の当時の実行コマンドに旧パスが残っているのは履歴を保持するためです。HTMLは表示・リンクを更新できますが、測定値を再計算したことにはしません。

初回の記録commitは `8309ba4afde277d39dd8a4ab4652da8a590a24ae` です。測定時の親commitと各ソースのハッシュは `results/run-001/results.json` に保存されています。
