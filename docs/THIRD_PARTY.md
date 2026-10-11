# 依存と利用条件

| 部分 | 一次出典 | 固定版 | 条件 |
|---|---|---|---|
| WORLD | https://github.com/mmorise/World | c794856b537758a3d300757db2e5e31685a822c2 | BSD-3-Clause。上流LICENSE.txtを含め内容を照合 |
| NumPy / SciPy | https://numpy.org / https://scipy.org | uv.lock | 配布パッケージのライセンスを保持 |
| LibriSpeech | https://www.openslr.org/12 | data/manifest.json | CC BY 4.0。帰属と抜粋範囲はdata/ATTRIBUTION.md |

自作HNMはNumPy/SciPyによる独自実装で、WORLDの解析・合成へ処理を渡さない。WORLD（Harvest）は比較対象としてのみ呼ぶ。学習済みモデルは使わない。

過去の比較ではLLSM2とcigletを使用した。現在はユーザー指定により比較対象から外し、アダプターと取得・ビルド実装を削除した。当時の版・ライセンス情報は保存済みの結果JSONとGit履歴に残る。過去のコードに適用したGPL-3.0の本文 `vocoderbench/COPYING.LLSM` は帰属の記録として保持する。
