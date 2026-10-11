# 依存と利用条件

| 部分 | 一次出典 | 固定版 | 条件 |
|---|---|---|---|
| WORLD | https://github.com/mmorise/World | c794856b537758a3d300757db2e5e31685a822c2 | 上流LICENSE.txtはBSD-3-Clause。buildスクリプトが同ファイルを含めhash検査 |
| LLSM2 | https://github.com/Sleepwalking/libllsm2 | d18cdf02b31819670e3bc23ead933ad9467da06d | GPL-3.0-or-later。直接結合するllsm_shim/adapter/build/testに同条件を表示。COPYING.LLSM同梱 |
| ciglet | https://github.com/Sleepwalking/ciglet | 895ba9b1c0eabee83d3544208bbc82420efa3206 | 上流の著作権表示と外部FFT等の条件を依存checkout内に保持 |
| NumPy / SciPy | https://numpy.org / https://scipy.org | uv.lock | 配布パッケージに含まれるライセンスを保持 |
| LibriSpeech | https://www.openslr.org/12 | data/manifest.jsonの固定mirror | CC BY 4.0、原音はLibriVox。帰属・変更内容をdata/ATTRIBUTION.mdに記録 |

依存本体・nativeバイナリ・音声をこのリポジトリへコピーして再配布せず、固定版取得とビルドを行う。ビルド先の依存にある著作権表示・ライセンスを削除しない。LLSMアダプターのGPL条件を他の方式のライセンスと混同しない。
