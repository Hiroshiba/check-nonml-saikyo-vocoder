# 依存と利用条件

| 部分 | 一次出典 | 固定版 | 条件 |
|---|---|---|---|
| WORLD | https://github.com/mmorise/World | c794856b537758a3d300757db2e5e31685a822c2 | BSD-3-Clause。上流LICENSE.txtを含め内容を照合 |
| NumPy / SciPy | https://numpy.org / https://scipy.org | uv.lock | 配布パッケージのライセンスを保持 |
| LibriSpeech | https://www.openslr.org/12 | data/manifest.json | CC BY 4.0。帰属と抜粋範囲はdata/ATTRIBUTION.md |
| pystoi | https://github.com/mpariente/pystoi | 0.4.1 | MIT。eSTOI測定用 |
| UTMOSv2 | https://github.com/sarulab-speech/UTMOSv2 | cc2700db57bb83ee13dc31ebe1b868c254e15d09 | MIT。配布重みの版・ハッシュ・適用条件はdocs/MOS.md |
| PyTorch / TorchAudio / TorchVision | https://pytorch.org | 2.8.0 / 2.8.0 / 0.23.0、CPU版 | 配布パッケージのライセンスを保持。評価器の実行に使用 |
| Transformers / librosa / timm | 各パッケージの公式配布 | uv.lock | 配布パッケージのライセンスを保持。評価器の実行に使用 |

自作HNMはNumPy/SciPyによる独自実装で、WORLDの解析・合成へ処理を渡さない。WORLD（Harvest）は比較対象としてのみ呼ぶ。エンコーダー・デコーダーには学習済みモデルを使わず、自動MOSの評価器だけに使用する。固定120録音の情報は `data/clean_speech_v1.json` と `data/ATTRIBUTION.md` に残す。

過去の比較ではLLSM2とcigletを使用した。現在はユーザー指定により比較対象から外し、アダプターと取得・ビルド実装を削除した。当時の版・ライセンス情報は保存済みの結果JSONとGit履歴に残る。過去のコードに適用したGPL-3.0の本文 `vocoderbench/COPYING.LLSM` は帰属の記録として保持する。


## PML低域拡張＋60FWCEP

`vocoderbench/pml/` は Gilles Degottex / University of Cambridge の公開PMLとsigproc（Apache-2.0）を限定的に移植・変更したものです。上流commit・対応ファイル・変更点・同梱ライセンスは [PML実装](../vocoderbench/pml/README.md) を参照。REAPER解析は `pyreaper==0.0.11`、CheapTrick包絡は `pyworld==0.3.5` を利用します。コード・配布物のライセンスを維持し、学習済み重みは合成器に不要です。MOS評価器の依存と音声データの利用条件は別です。
