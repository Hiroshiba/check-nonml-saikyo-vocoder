# 時間伸縮で区別する三つの長さ

2026-10-27。静的読解だけの検討で、実装・音声生成・品質評価はしていない。現在のベースはApron24。現main 16e2036ce3e39cc6cabee9ffc2a6c93926f10753 のengine・wrapper・CLIを照合した。

## 元入力、フレーム中心、native出力は同じ長さではない

元PCMのサンプル数、フレーム中心の端点間隔 (NFRM−1)×THOP、native出力長 round((NFRM+1)×THOP×fs) を分ける。保存した native_input_samples は解析時の元入力の来歴であり、新しく要求する出力長で上書きしない。

現engineはnativeが返すny個のサンプルを全て返し、元入力長へ切り詰めない。wrapperも復号時にTHOPを5msへ戻さず、chunkをそのまま合成器へ渡す。現公開APIに時間伸縮の引数がないことと、内部の変更が復号時に無効化されることは別である。

上流demoのNFRMを2倍にする処理では、同じhop Hに対してnative長が round((N+1)H) から round((2N+1)H) になる。native出力を正確に2倍にする操作ではなく、概ね1hopだけ短い。任意の整数サンプル長を指定するなら、端点と掲載・配送時の長さの規則が必要になる。

## THOPだけを変える案の交絡

THOPは周期位相の時計だけでなく、調波の重ね合わせ窓、雑音包絡窓、雑音のFFT長にも使われる。24kHz・5msで、時間倍率0.75なら名目hopは120→90サンプル、窓は240→180、雑音FFTは512→256になる。倍率1.5ならhop180、窓360、雑音FFT512となる。これは式の代入であり、実測ではない。

調波中心の整数変換と雑音中心のroundも同じ規則ではない。固定16サンプルのfadeと窓長の比も変わる。したがってTHOP変更案を、音高と時間座標だけが変わる処理と説明しない。

固定hopでフレームを再配置する案なら、このhop由来の窓・FFT変更は避けられる。ただし、Layer1状態、旧周期時計を除いた位相、V/UV境界、調波数が異なる場合の尾部、PSDRESの配置を別途決めなければならない。PSDRESの補間が必須とは限らず、demoの近傍からの乱択も、根拠とseedが必要な一つの方針にすぎない。

## 将来の編集契約に残す項目

- 元artifactの識別子と解析時の入力・配列hashを不変にする。
- 倍率が何の長さに対するものかを決め、24kHzの target_output_samples と丸め規則を明示する。
- 時間写像、出力THOP/NFRM、元フレーム位置、終端・外挿規則を残す。
- native長と返す長さを分け、切出しが必要なら開始位置と長さ、不足時の扱いを明示する。
- 元の周期時計を旧THOPで除き、新しい時計を新しいF0とTHOPで加える。調波だけでなく雑音包絡の調波位相も対象になる。
- HM/PbPを持たない独立した編集用Layer1状態を使い、編集前のHMを誤って再利用しない。

比較をする場合は、元artifact、目標長、F0のHzでの意味、seed、端点規則を揃える。THOP変更と固定hop再配置の違いは有用な設計上の区別だが、このメモだけで両方を計測することや採用を決めたわけではない。

## 静的根拠

この区別は独自の懸念だけではない。上流libllsm2の[2.1の説明](https://github.com/Sleepwalking/libllsm2#changes-in-version-21)は、時間伸縮で雑音PSDの変動が平滑化されることを理由に、定常PSDと残差PSDRESを分けて処理するよう説明している。[VT ServerのWORLD処理の公式説明](https://egaudrain.github.io/VTServer/modules.html#module-vt_server_module_world)も、相対倍率と絶対秒数の指定を分け、記載対象のv0.2.8ではduration未指定時に1フレーム長くなると注意している。後者を現在の全WORLD実装へ一般化せず、出力長を明示的に契約化する先行例として参照する。

固定上流src/llsm/layer0.c: 出力長639–643、Layer1窓159・中心173、雑音包絡293・307、雑音窓とFFT559–567、位相時計694–705。frame.c:152–165は調波・雑音包絡・VSPHSEの位相更新。test/demo-stretch.c:159–185は旧時計除去、固定hop再配置、残差配置、新時計付加。

現mainのreferences/native.py、apron/engine.py、apron_cli.py、references/current_base.pyで、復号後の元入力長への隠れた切詰めがないことを確認した。保存packetのstock-wrapper SHA-256は 6a2abdf3b87f4af1dc402dbaec4340ad9907a1f35f27222641f7f6dda40724b9。上流固定ソースと現mainを同一のファイルだとは扱わない。
