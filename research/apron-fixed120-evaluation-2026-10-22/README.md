# Apron固定120録音評価の公開範囲

このPagesレポートは、保存済みの研究計測から集計値、公開入力の全1440個票、短い音声2例を提示する。後発の補助対照としてLayer0編集240波形と品質720個票も別に掲載する。全長音声、モデル重み、実行ログはGitに入れない。

- 科学sourceは凍結commit `06b6da5e5822500993bdfc44b3bf35f84acaea46`。現在の`BASELINE.json`に測定完了を追記しても、この計測sourceや保存結果は変更しない。入力は固定manifest `research/pml-package-evaluation-2026-10-16/input-manifest.json`、SHA-256 `1f392fc60fbca4003c236f03ffd9edba82b048737f23cf250295c1b4c6c85193` に記された120録音・40話者。話者ごと3録音で、全件が分母に入る。
- 固定LLSM2 revision `d18cdf02b31819670e3bc23ead933ad9467da06d`、ciglet revision `895ba9b1c0eabee83d3544208bbc82420efa3206`。Apronは録音ごとに一度解析し、保存したLayer1状態から0/−3/+3半音を独立に復号。比較方式Layer0は無編集だけ。解析前と各復号前のseedは0、DSP threadは1。
- UTMOSv2はnative全長。無編集ECAPA・SCOREQ・eSTOIは固定16 kHz共通先頭区間。編集ECAPAは元入力の全抜粋と編集出力全長をそれぞれ16 kHzへ変換。品質threadは2。使用したモデル・版・元source SHAは`provenance.json`にある。
- 計測ではnative120件・480波形と品質1440個票がすべて成功し、欠測は0。個票JSONを十進数として読み、指標・条件・範囲ごとに全120個の合計を120で割った。平均、合計、最小・最大を`results.json`に保存した。全話者に3録音ずつあるが、有意差や人の評定はこの平均から判断しない。
- 同じ環境の別集計コードで保存個票を読み、入力・native波形・採点PCMなどのbytes/SHAを照合した。公開用の`individual-results.json`は元の個票から録音ID・値・採点範囲・標本数・関連SHAだけを抜き出し、このファイルから集計値を再照合した。独立環境での再測定ではない。照合の識別値とチェック件数は`provenance.json`にある。
- 最初のv1呼出しは`/usr/bin/time`不在で科学子の起動前にexit127・0/168波形。原ログはローカルに残し、今回のv2成功と同一視しない。
- 公開プレビューは`docs/CORPUS.md`の2つの`public_audio_example_ids`に限定した5秒PCM16。元の16 kHz入力と24 kHz出力を各サンプルレートのまま載せる。採点した元波形とは別物で、ゲイン・clip・時刻合わせは加えない。採点は指標ごとに定めた全長または固定先頭区間で行った。元の10件と追加4件のSHAと変換は`audio-manifest.json`にある。出典・改変表示は`audio-credits.html`。

旧PMLは異なる時点の歴史的結果で、今回の二方式の順位には入れない。Layer0の±3半音対照は元評価の集計後に計画し、固定source commit `9440f7e6997c1a6f0262809b88ce5c3b253cc7f9` で追加測定した。新規720個票は `supplement-individual-results.json`、元評価から引用したUTMOSv2の480個票と編集Apron全長ECAPAの240個票は元 `individual-results.json` の位置まで `supplement-provenance.json` に固定した。無編集の全長ECAPAは今回新たに測定し、元の固定先頭区間ECAPAと混ぜない。録音ごとの対応差とその単純平均は `supplement-results.json`、保存値の別経路照合は `supplement-saved-result-audit.json` にある。3担当のnativeおよび6品質起動は終了0・回収済み、240波形と720個票が全件成功、欠測0、警告1713件、エラー0件。

最初のsystem Python環境のpreflightは `pyworld` 不在で科学子の起動前に停止した。指定済みvenvで正式な照合を通し、その後の計測と分けて記録した。元の `/usr/bin/time` 失敗も別原本として保持している。結果は16 kHz英語朗読からの24 kHz出力に限り、F0精度・生理的な話者性・48 kHz・日本語音声・人工10刺激は今回確認していない。現在の作業ベースはApronのままで、この表を方式の総合優位や採用資格の検定とはしない。
