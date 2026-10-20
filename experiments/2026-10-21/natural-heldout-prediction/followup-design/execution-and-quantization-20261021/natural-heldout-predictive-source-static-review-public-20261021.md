# 自然音声の短期予測比較：ソースの独立静的レビュー

2026-10-21 JST。最終判定は **この固定ソースに対する必須修正なし**。設計との整合を静的に確認したもので、動作・所要時間・実メモリー・科学的結果の認定ではない。実行可否の判断、実入力の照合、Cloudでの限定実行は別工程である。

## 対象を固定する識別情報

- ソース束 `natural-heldout-predictive-source-20261021/`：7 Python、README、SCHEMA、requirements、固定入力manifest、SOURCE_MANIFEST。
- `SOURCE_MANIFEST.json` SHA256：`a334bc9ea5a60338bb05bf3cb5277b481ee69b0c4197c09886c287e80d2871e4`。
- 採用対象ZIP `natural-heldout-predictive-source-20261021.zip`：33,291 bytes、SHA256 `6812fca841a12f1ea2ab4477e3328aeb5ad00959138aeef3ae8670352cd16f6e`。
- source manifestの12 entryについてbyte数・SHAを独立照合し、ZIPの全13 fileを展開先へ書き出さず読み、ローカル最終fileとbyte一致を確認した。旧ZIP `c2310a…` は対象外。

## 確認できた契約

1. **式と共通時間**：`model_math.py:57–81, 84–145, 157–199`。q/16384から作る560標本のcos/sin基底をT=0..399とH=400..559に分ける。V0=I/K、A=KI+XᵀX、D=A+WᵀW。Rtrainは残差normとK||μ||²の和、Qpredは残差normと||LAᵀδ||²の和。H0は別枝。α=203、joint α=283、200/80、logdet差、−160logr、Gamma定数が設計に一致する。
2. **比較する不確実性**：同じcomponent予測密度からmix、Tだけによるfirst argmaxのsingle、H0を作る。singleもbとσ²を積分する。重み・混合はlogsumexp、logH1totalはH1のlogsumexpであり、H1総和と最大個別modelを混同しない。c=0.1/1/10を同じR/Qからすべて計算する。Hを用いる選択・prior再設定はない。
3. **固定120入力とowner**：`preflight.py:21–42, 75–116` は同梱入力manifestのGit blobとSHA、120 unique ID・40話者各3録音を確認し、id順に整列する。全120 NPYのbyte/SHA・magic/header・dtype・shapeを数値ライブラリimport前に照合する。`measurement.py:23–83` はそのsorted index mod3でownerを選び、40録音を要求する。ロード直前のSHA再照合、有限性確認、固定tile抽出がある。
4. **全尺度共通の失敗支持**：非零TのRMS underflowは全零扱いにしない。列単位のR/Q失敗は窓全体を全cで無効にし、失敗componentだけを落とす再正規化をしない。scoreで途中のcが失敗しても、その窓のscoresをすべて空にする。NaNは未利用統計のsentinelであり、得点や0点埋めではない。
5. **後から監査できる出力**：`measurement.py:118–150` とSCHEMAは、全model Rtrain/Qpred、各窓r、logdet_A/D、log prior、evidence offset、q/K対応、実際のscalar定数、全3cの得点を保持する。ownerごとの録音平均までにとどめ、3ownerの独立監査前に話者・全体得点を作らない。警告・エラーはstageと録音/tileまたは明示的batch範囲、q/K/c、stackを記録する。
6. **制御された実行と出力**：`run.py:46–127`、`storage.py:15–83`。driverはsubprocess/multiprocessingを作らず、BLAS等の環境設定とthreadpool制限を2にする。`/proc/.../children`、PID消失等から全OS子processの終了を推定しない。外部ツールの実exitを別途保存する。preflight report・出力folder・ZIPはsource/inputと重ならず、既存pathは拒否する。
7. **厳密な容量・最終化**：出力folderは排他作成、各fileはxb。48 MiBはREADME/SCHEMAが明示するarchive前のowner payload上限で、ZIPは別である。書込前にbytesを予約し、失敗した部分書込の予約も返さない。警告・エラーは改行込み4 MiB。上限例外は窓の科学的失敗へ降格せずfatalに伝播する。最終化分も事前に容量確認し、hash manifestを書いてCOMPLETEを最後に置く。archive失敗は確定folderのhashを変えず外部stderrとexit3へ記録する。

## 指摘と最終照合

レビュー中に次を指摘し、最終固定byteで解消を確認した。

- 浮動小数警告を無条件ignoreにする分岐：stage付き警告ログへ変更。有限underflowは救済せず、float64診断の限界として明記した。
- score非有限時のcomponent所在不足：model index/q/K/c/stageを持つ例外とfull tracebackへ変更。
- 部分writeの未計上とlog改行の未計上：I/O前予約、改行込み会計へ変更。

## 静的確認と未実施事項

- 7 Pythonすべてをbyte hash keyed cache付きでAST解析した。候補モジュールはimportしていない。
- 既存Ruffをキャッシュ付き、target py312、select E4/E7/E9/Fで実行し、`All checks passed!` を確認した。新規installはない。
- 固定main `418fb5f029b7e43e58665df4be958f1125416318` の[uv.lock](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/418fb5f029b7e43e58665df4be958f1125416318/uv.lock)（blob `3e915a071f82464e8442a9b9a52920bed8d94944`）を読み、NumPy 2.3.5、SciPy 1.17.0、threadpoolctl 3.7.0のpinを確認した。
- candidateのimport、CLI help、科学数値計算、音声のロード・取得・解析、テスト、smoke、dummy、動作予行は行っていない。実入力120本の検証結果も、このレビュー自身の実測としては主張しない。
- 成功見込み、速度、数値得点、予測改善、F0/VUV精度、校正、音質、PMLとの品質優劣は未確認。

## 最終PythonのSHA256

| file | SHA256 |
| --- | --- |
| contract.py | cf54e8abc4b774ad9580d3a777b59b384d9c653d9de8200041d616d61a5bbc4c |
| diagnostics.py | 26c9d9f3622d8d1db74fec1650e35938643f8d98fcb7c968cd32b68a422e048a |
| measurement.py | 938e62029c89a64cce75e6e63d2a888f84425a73dc79cfae7896d406e423f33c |
| model_math.py | 3d95533238d7c32970a2492a1642fc2b9b1123f5b04fbd43fc3615f4906c4e58 |
| preflight.py | 90f62097480c207af2c95faca4eedd783e831c2334f9d24b5c8b7632c7eda631 |
| run.py | f97a3a2b7eeaa915090e124b121ec7cb55c664ae659c766dc777b12cf4f90316 |
| storage.py | 51f39de9821b68cf44a383e18c9d5c2e296ade6eb2ed2671eb0839b5527c6884 |

上記hashからの変更があれば、影響箇所の再審査が必要である。ソース作成担当のfileには変更していない。

## 公開用の表記調整

私有ソースへの相対リンク3件をファイル名の表記へ変更した。数式・判定・ソース識別は変更していない。未採用の診断コード本体はGitに含めず、Library `libfile_cf7e8cecbae4819188a1f04aab66ff16` version 0に保存した。
