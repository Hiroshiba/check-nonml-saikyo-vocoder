# 全8方式の軸別集約と日本語HTML（復旧後の新source）

## 状態と境界

2026-10-14の復旧環境で作成した新source。旧ソースの完全復元とは呼ばない。現時点では正式rawが存在せず、集約・HTML生成・測定・動作確認・テストを実行していない。確認は静的Ruffとsource読取レビューのみ。旧会話の途中件数や平均値をrawへ補わない。

## 入口とモジュール

- `scripts/all_metrics_rankings.py`: 正式新runのrawだけを読み、別の保存先へJSON/HTMLを生成する。既存結果は上書きしない。
- `all_metrics_rankings_core.py`: 許容状態/有限値、宣言比較方式共通群、話者等重み値、話者復元抽出2000回/seed20261014、paired HNM差、競技順位。
- `all_metrics_rankings_inputs.py`: MOS/共通品質/操作・表現群/native速度のconsumerと出典SHA照合。公開音声は元dataset許諾2IDと実WAV SHAを照合。
- `all_metrics_rankings_acoustic.py`: 既存音響値の明示registry。符号付きRMS、quiet比率・RMS・peakなどは方向なし。
- `all_metrics_rankings_extra.py`: ASR、独立VCTK、#13/#14/#15専用推定対象。元の専用区間を継承し再計算しない。
- `all_metrics_rankings_coverage.py`: 全18群×全8方式144セル。派生軸件数を録音数・独立指標数へ加算しない。
- `all_metrics_rankings_html.py`: 冒頭HNM比較、各軸の値/順位/区間/差/状態/分母、許諾音声例。
- `all_metrics_final_gate.py`: 予定manifestから原recordと全pointを列挙し、未到着を検出。終端は成功とは別。

## 集約条件

各群の指定methodsを比較集合とするが、状態rowは全8方式を保つ。同じ録音の方式値から話者内平均、話者等重み平均を作る。共通0なら値/順位/区間null。欠測を0・最下位へ変換しない。

方向はlower/higher/nullを明示。descriptive入力はnullへ変換。順位は未丸め値を絶対1e-12・相対1e-9で同点群先頭と比較する競技順位。CI重なりによる同順位は作らない。一般群は2話者未満ならCIなし。比較群のbootstrap drawは方式間共通、HNM差も録音/話者を対応させる。

一般群の補助比較は、全予定工程終端後に、許容状態かつ有限値が1件以上ある全方式を先に固定し、その全方式の共通録音を使う。共通数を増やすための再選別は禁止。全有効録音の方式別平均は別の無順位補助。

#13/#14/#15は専用sourceの全8primaryを維持する。固定train校正失敗でprimaryがnullでも、auxiliary_successful_methodsの固定成功集合、除外理由、分母、値、CI、HNM差を別の無順位補助として継承する。ABXは2話者条件×3推定対象の6表、読み出しは3属性の3表。analysis_complete=false/terminal=falseの中間表を終端扱いしない。

#18.shared_assetsは方式定数8行だけで録音rowを持たない。平均/話者bootstrap/順位を作らない。容器bytes・bit/sは宣言容器量の順序であり、品質付き圧縮効率や総合品質ではない。analytic_identityは群が許した厳密同一性の0だけを受理し、直接実測とは別計数。

## 入力と終端gate

通常MOS/ASR/音響/VCTK/nativeのrawは対象ID/方式/話者/条件と固定科学契約SHAを照合。共通品質はactive manifestと一致する最新attemptの全状態を採用し、適合attempt間のready評価器signatureの不一致を拒否する。control/latent群は各入力raw SHAの変更・喪失を拒否。

未到着はpending、未実行/未要求も未完。上流失敗・失敗・未対応・適用外を別状態として保持。gateはcontrol/curve予定集合に加え、latent全5点と量子化後操作、各MOS/ECAPA、native特徴、独立train、原音target、ASR認識と評価、VCTK/human特徴、専用集約を列挙。予期しない集約例外でshared summaryがない場合は未完のまま。成功宣言に必要な証拠がない場合も最終化しない。

主120録音、ASR全文55/32話者と残65、VCTK126/7話者、ASV105録音84対28話者の分母を混ぜない。ABXの実予定数は新manifest/専用成果から読む。旧4774/186等を新runの現在値へ書かない。

## 保存と音声例

最終生成前に `all_metrics_audio.py --output 保存先` が作る `audio_samples.json` を `--audio-manifest` へ渡す。audioのみ配置済みの保存先は認めるがresults.json/index.html/artifact-manifest.jsonは上書きしない。最終HTMLには音声例が必要。`--allow-incomplete` は正式run途中の未完集計であり、動作確認用の試作データを許可しない。

JSONはローカル研究用の出典path/SHAを含む。全長wave/model/private保存先をリンクとしてHTMLへ出さない。公開rawの圧縮・redaction・許諾・10MiB上限は公開工程で別途確認する。集約sourceの静的成功を実測や公開完了と呼ばない。
