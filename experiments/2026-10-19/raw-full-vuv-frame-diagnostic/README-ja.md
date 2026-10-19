# 保存VUVフレーム診断

index.htmlを開いてください。全28条件表、全28条件の保存系列SVG、指定3例のcrop SVG、例Cの時刻拡大SVGを含みます。
JSON/CSVは保存値の公開用projectionです。private selection・抽出receipt・279元source pathは含みません。
音声の実提供状況はaudio-status.jsonを参照してください。未提供時はplayerを生成しません。提供時はcase/pitch/seed/roleと元crop時刻・元波形SHA・WAV SHAを照合します。
通常表示は原音/edited PML/edited RAW_FULL、native2本はdetailsです。このrendererと保存系列の観察は音声合成・品質再評価を行いません。
復旧音声の場合は別工程でRAW_FULL6本を再生成し、元全NPY SHA一致を確認した新receiptへ結び付けています。原音3本とPML6本はbytes/SHA一致バックアップです。
RAWのexpected bytesおよび元array/PCM/RNG期待値は未回収で、個別照合済みとはしません。実提供時の来歴はclip-manifest.json、音声の復旧状態はaudio-status.jsonを参照してください。
元の正式120比較・指標・既定警告・PML維持を変更せず、ここで新順位は作りません。
図は保存値の可視化。整数は全抜粋の値で、代表例crop区間に再集計していません。
時刻は元抜粋内の80 ms窓中心、0Hzは有声線と接続しません。図の帯幅10msは表示セルです。
CC BY 4.0、LibriSpeech（Vassil Panayotov、Daniel Povey協力、LibriVox由来）。詳細はHTMLの出典欄。
