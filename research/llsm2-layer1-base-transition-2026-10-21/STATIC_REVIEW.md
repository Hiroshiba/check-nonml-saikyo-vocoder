# Layer1 ベース切替の静的確認

- 起点は main `62acf3cadcd8a49f37e2e63826f2966ed2d8ce28`。PR #117 の `docs/STATUS.md` と人工10刺激の文書、PR #118 のユーザー編集を保持し、`USER_INSTRUCTIONS.md` を本変更で編集していない。
- 比較 ID `llsm2` は `references/adapters_dsp.py` の Layer0 のまま。現在の作業ベースは別 ID `apron` として `BASELINE.json`、`references/current_base.py`、`reference.py`、`worker.py` に接続する。
- 最初の日本語抽選はユーザーの英語指定より前の履歴として保持。英語候補8語を先に固定して `secrets.choice` で再抽選し、Apronを採用した。リポジトリと公開検索で、同名の音声・信号処理・ML手法は確認できなかった。英語の候補・抽選・検索範囲は別JSONに保存した。
- 固定上流ヘッダーの field 番号・型は F0=0(float)、HM=1、NM=2、PSDRES=3、RD=10、VTMAGN=11、VSPHSE=12。解析は既存の固定 `speed_encode(...,1)` で Layer0 から `llsm_chunk_tolayer1(...,2048)` を呼ぶ。保存時は元 HM と PbP field 8/9 を除き、その他の未知 field は拒否する。
- C の `llsm_create_chunk` は config をコピーし、`llsm_delete_chunk` は frame/config を破棄する。保存からの復元は所有権付き `llsm_container_attach_` と実体の destructor/copy constructor を使う。復号ごとに別の chunk を構築し、合成前の HM 不在を確認する。上流合成が live chunk へ HM を追加しても保存配列は変わらない。
- 音高は固定 ±3 半音のみ。上流例と同じ phasepropagate(-1) → F0倍率 → VTMAGNのdB補正 → phasepropagate(+1)。各解析・復号前にPython/NumPy/libc seed 0。未対応の音量・時間長・補間・48 kHzは暗黙処理しない。
- 新CLIは native 24 kHz 単声道のみ。正式比較入口は元16 kHz入力を明示的に24 kHzへ変換し、nativeレートと全長を記録する。既存評価器の native 全長と元帯域の共通先頭区間を分け、旧16 kHz同長ベンチマークへ24 kHzを渡さない。
- 実行入口は本体Python 3.12、比較方式の隔離環境はPython 3.10.22。`verify_prepared` は上流ソース・wrapper・build記録・実 `.so` を照合し、固定のwrapper本文・build argvも照合する。実 `.so` のSHAを来歴に記録する。起点ビルドSHA `d8da444d9c3298899065de57d5efbea69574d38ec1c4d9f42a50c2cb1a730c2a` は履歴値で、別toolchainの正規ビルドを拒否する配布条件にはしない。
- 正規準備は `/workspace/llsm2-layer1-preparation-20261021-v2/invocation.json` の終了0。上流Cの `layer0.c` の `nfrm` 警告は stderr に残る。警告を隠さず、ビルド成功を品質成功と呼ばない。
- PMLの保存済みHTML/JSON/音声を変更せず、旧専用実行コードを退役。歴史的結果の再現先は変更前commit。保存JSONを読む表示・集約は維持した。
- レビュー後の静的修正では、ApronのLayer1表現を試行ごとの新規directoryへ保存し、失敗後の再試行で部分保存物を上書きしない。公開入口は現Apronと歴史的PMLの識別子を区別して受け付ける。旧VCTK合成・再開・監視入口とPML依存の区間生成入口は現ブランチに残るが、削除済み実装への依存があり、現行での実行はできない。当時の再現先は変更前commitに記録した。
- 移行HTMLと命名記録は `artifact-manifest.json` へ固定し、`research/pages-reports.json` の案内専用項目からPagesへ掲載する。未測定のLayer1へ得点・順位・音声を付けない。固定された旧PML `REPRODUCE.md` は元の6060 bytes/SHAへ戻し、過去manifestは変えない。
- Python AST、JSON構文、キャッシュ付きRuff、`git diff --check` は通過。上流C ABIと所有権をヘッダー・実装で照合した。対象moduleのimport、音声生成、科学計測、tests、smokeは実施していない。
- 日本語は natural-japanese の短文・主語明示・断定範囲の確認を適用。移行HTMLの最初に「ユーザー指定」と「Layer1未測定」を置き、Layer0/PMLの保存結果と区別した。新しい音声や品質順位を掲載していない。
