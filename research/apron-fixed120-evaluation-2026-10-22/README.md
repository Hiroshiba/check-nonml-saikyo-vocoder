# Apron固定120録音評価の公開範囲

このPagesレポートは、保存済みの研究計測から集計値と公開可能な短い音声2例を提示する。測定原本、全個票、全長音声、モデル重み、実行ログはGitに入れない。

- 科学sourceはcommit `06b6da5e5822500993bdfc44b3bf35f84acaea46`。入力は固定manifest `research/pml-package-evaluation-2026-10-16/input-manifest.json`、SHA-256 `1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193` に記された120録音・40話者。話者ごと3録音で、全件が分母に入る。
- 固定LLSM2 revision `d18cdf02b31819670e3bc23ead933ad9467da06d`、ciglet revision `895ba9b1c0eabee83d3544208bbc82420efa3206`。Apronは録音ごとに一度解析し、保存したLayer1状態から0/−3/+3半音を独立に復号。比較方式Layer0は無編集だけ。解析前と各復号前のseedは0、DSP threadは1。
- UTMOSv2はnative全長。無編集ECAPA・SCOREQ・eSTOIは固定16 kHz共通先頭区間。編集ECAPAは元入力の全抜粋と編集出力全長をそれぞれ16 kHzへ変換。品質threadは2。使用したモデル・版・元source SHAは`provenance.json`にある。
- 計測ではnative120件・480波形と品質1440個票がすべて成功し、欠測は0。個票JSONを十進数として読み、指標・条件・範囲ごとに全120個の合計を120で割った。平均、合計、最小・最大を`results.json`に保存した。全話者に3録音ずつあるが、有意差や人の評定はこの平均から判断しない。
- 同じ環境の別集計コードで保存個票を読み、入力・native波形・採点PCMなどのbytes/SHAを照合した。独立環境での再測定ではない。照合の識別値とチェック件数は`provenance.json`にある。
- 最初のv1呼出しは`/usr/bin/time`不在で科学子の起動前にexit127・0/168波形。原ログはローカルに残し、今回のv2成功と同一視しない。
- 公開プレビューは`docs/CORPUS.md`の2つの`public_audio_example_ids`に限定した5秒PCM16。元の16 kHz入力と24 kHz出力を各サンプルレートのまま載せる。元の全長指標波形とは別物で、ゲイン・clip・時刻合わせは加えない。全10件のSHAと変換は`audio-manifest.json`にある。出典・改変表示は`audio-credits.html`。

旧PMLは異なる時点の歴史的結果で、今回の二方式の順位には入れない。Layer0の±3半音対照、48 kHz、日本語音声、人工10刺激の未完了部分は今回測定していない。現在の作業ベースはApronのままで、この表を方式の総合優位や採用資格の検定とはしない。
