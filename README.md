# ボコーダーの比較と開発

**現在の作業ベースは「Apron」です。** 固定版の LLSM2 Layer1 を使います。ユーザーの指定で切り替えたもので、[固定120録音の品質と音高±3半音の結果](research/apron-fixed120-evaluation-2026-10-22/index.html)を記録しました。[切替時点の記録](research/llsm2-layer1-base-transition-2026-10-21/index.html)にある「未測定」は当時の状態です。ユーザー指示の正本は [USER_INSTRUCTIONS.md](USER_INSTRUCTIONS.md) です。

Apronは24 kHzで解析し、元の調波列を含まない Layer1 特徴を保存します。復号のたびに保存特徴から独立した状態を作ります。既存の比較 ID `llsm2` は従来どおり Layer0 です。両者の結果を混同しません。

## 開発ベースの入口

リポジトリ本体は Python 3.12 を使います。上流 LLSM2 と ciglet は[固定版の準備手順](docs/REFERENCES.md)に従い、Git 管理外の隔離キャッシュに準備します。この準備で得る比較用 Python 3.10 環境と、本体の Python 3.12 環境は区別します。Apronの入口は本体 Python 3.12 から、照合済みの native library を使います。Layer1 の音声処理は固定120録音で測定し、48 kHzへの適用は未確認です。

```sh
uv sync --locked
uv run --locked python -m vocoderbench.references.prepare --methods llsm2 --runtime-cache /absolute/new-cache
uv run --locked python -m vocoderbench.apron_cli --runtime-cache /absolute/new-cache encode input-24k.wav features.layer1
uv run --locked python -m vocoderbench.apron_cli --runtime-cache /absolute/new-cache decode features.layer1 output-24k.wav
```

音声 CLI は24 kHz・単声道の入力だけを受け付け、出力も実際の24 kHzで保存します。音高操作は `decode` の `--pitch-semitones -3` または `3` のみです。音量・時間長・補間・48 kHz は未対応です。上記は実行手順であり、この切替 PR での実行結果ではありません。

固定120音声の比較には `vocoderbench.reference --include-current-base` の経路があります。比較時は各方式の native 標本化周波数と全長を保持し、元の16 kHz音声との補助指標は共通区間で別に計算します。今回の[固定120録音の品質評価](research/apron-fixed120-evaluation-2026-10-22/index.html)は別の保存済み研究実行です。後発の補助計画ではLayer0の±3半音対照も測定しました。固定120録音で、Apronの0半音出力を基準とする[YIN（音高推定器）による±3半音の相対追従](research/apron-pitch-follow-2026-10-23/index.html)を測定しました。独立した正解F0に対する精度と真の有声・無声は確認していません。48 kHzの正式計測は全件未実行です。既存方式だけの比較では `--include-current-base` を省きます。

## 保存済みの比較

- [PMLの正式追加評価・比較音声](research/pml-package-evaluation-2026-10-16/index.html)：以前の作業ベースを選んだ当時の記録です。値、音声、版、当時の比較基準は変更していません。旧実行コードの再現先は commit `62acf3cadcd8a49f37e2e63826f2966ed2d8ce28` です。
- [LLSM2 Layer0など既存方式の比較](experiments/2026-10-12/reference-methods/results/run-001/index.html)：Layer1 の評価結果ではありません。
- [当時のHNM v3を含む固定120音声の比較](research/all-method-final-2026-10-15/index.html)：当時の条件と順位を保存しています。

結果の配置は[実験一覧](experiments/README.md)、現在の状況は[ステータス](docs/STATUS.md)、測定仕様は[評価文書](docs/EVALUATION.md)を参照してください。`runs/` 内の入力・出力と上流ソースはGit管理外です。過去のHTML・JSON・音声を新ベースの結果へ読み替えません。

## 制約と帰属

固定120音声の品質評価は、Apronの長所と弱点を調べる工程です。切替時点の優位性を裏付ける測定として扱いません。最終目標の48 kHz、時間伸縮、音量操作、下流合成への適性も未確認です。

上流の LLSM2 と ciglet は固定した版をキャッシュに取得し、Gitへ複製しません。[第三者コードの帰属](docs/THIRD_PARTY.md)と[既存方式の手順](docs/REFERENCES.md)を参照してください。
