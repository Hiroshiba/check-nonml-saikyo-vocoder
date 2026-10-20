# 既存F0 kernelのlog-g Laplace近似差・表示版

PML base維持。自然120録音の既存比較: https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/raw-full-full120-comparison-2026-10-19/index.html
PML正式120録音: https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/pml-package-evaluation-2026-10-16/index.html
過去の標準8方式: https://hiroshiba.github.io/check-nonml-saikyo-vocoder/research/all-method-final-2026-10-15/index.html

固定1080点/108r/欠測0、N400・δ3・K1..10のscalar診断。品質/MOS/採用ではない。Δ_A80=L80−A80は、同じ既存priorの数学的exact積分対象に対するlog-g Laplace差の、80桁非保証参照による保存値。単位nats。80桁設定は80桁正確性の保証ではない。

A80基準の全点で負という保存観測を示すが、連続全域を証明しない。Q基準全点符号は集計していない。50/80桁・2方式一致はcertified errorではない。支持は意図的配置かつ区分重複があり、自然r分布の平均を意味しない。

表とSVGは保存min/maxの表示だけ。CIではない。K順で、近似差順位や音質順位は付けない。新平均、特殊関数、BF、gate、真誤差上界の計算なし。CSV/summary/必要証拠/source/input manifestは原bytes。canonicalはgzip mtime0、解凍SHAをdistribution-manifestに保存。

canonical-rows.json.gzの解凍内容は元canonical-rows.jsonlのJSON Lines。既存builderのsuffix許可に合わせた配布名であり、JSON配列へ変換していない。original INPUT-MANIFEST内のLibrary ID/version/file IDとZIP/member SHAから不変の原本を復元する。

旧548成功＋回復532を保持。旧index548のpartialとquad2664を捨てず累計に継承。原supervisor_failureを変更しない。3担当終了を保存し、union外部実wait2.813秒。原計算HTML/元README/全原outputはレビューbundleのpreserved/union-originalにbyte保存し、公開対象から分離。

作成時刻UTC: 2026-10-20T08:37:45.863230+00:00。union独立監査通過という履歴を反映。Git/PR公開は本作成作業で未実施であり、将来のlive状態を断定しない。ブラウザ描画、Pagesビルド、liveリンク確認はこの作業では未実施。新音声生成なし。
