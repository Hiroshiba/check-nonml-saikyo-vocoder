# Apronは一本のF0系列から声源・声道を解析する

現在の作業ベース Apron（LLSM2 Layer1）は、入力音声から選んだ一本のF0系列を使って解析します。F0や有声・無声の候補を確率分布として保存する方式ではありません。これは2026年10月22日時点の実装確認であり、低い声の品質が悪い、または良いという測定結果ではありません。[固定120録音の評価計画](../experiments/2026-10-22/apron-fixed120-evaluation/README.md)はありますが、Apronの品質値はまだ得られていません。

## F0は外部推定の後、近い値だけを再調整する

ApronはDIOで60～1000 Hzを探索し、StoneMaskで補正したF0配列を5 ms間隔でLLSM2へ渡します。この範囲はDIOの探索設定であり、補正後の全F0値を拘束する保証ではありません。上流の初期設定では内部の再調整も有効です。第1～第3調波の瞬時周波数をそれぞれ調波次数で割ってF0推定値に戻し、現在のF0との差が10%未満の値だけを平均します。該当値がなければ元のF0を保ちます。オクターブ違いの候補を比べ直す処理ではありません。上流の例は確率的YINを使いますが、LLSM2へ渡すのはやはり一本のF0配列です。[Apronの入口](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/700eb3866428a2528ee9f75bba3b833f495a47ca/vocoderbench/apron/engine.py#L73-L97)／[上流の初期設定](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L27-L42)／[再調整](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/dsputils.c#L72-L94)／[上流の例](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/test/test-layer1-anasynth.c#L12-L26)

## 選んだF0は後段の解析にも使われる

F0が0のフレームでは調波解析を飛ばし、声道の振幅応答（VTMAGN）と声源の調波位相（VSPHSE）も保存しません。一方、雑音成分は有声フレームにもあります。合成時はHann窓を重ねて加えるため、二値の有声・無声ラベルだけから波形の瞬間的な不連続は結論できません。調波解析の窓は設定上4周期で、60 Hzなら約66.7 msです。5 msはフレームを進める間隔で、解析窓の長さではありません。雑音包絡の窓はF0が0かどうかで長さが変わります。[調波解析](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/dsputils.c#L175-L210)／[解析と残差](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L487-L506)／[雑音包絡](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L425-L452)／[重ね合わせ](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L263-L310)／[保存条件](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/700eb3866428a2528ee9f75bba3b833f495a47ca/vocoderbench/apron/storage.py#L58-L66)／[上流の項目定義](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/llsm.h#L105-L108)

選んだF0は調波の抽出と残差の減算に加え、Rdと声道の推定にも入ります。保存後にF0だけを書き換えても、別のF0候補で音声を最初から解析したことにはなりません。Rdは64個のLF形状候補を比較し、最良候補の近傍補間も使って一点推定した後、空白補間と時間平滑化を行います。候補の事後分布は保持しません。[残差と雑音解析](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer0.c#L487-L506)／[Rd推定と平滑化](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer1.c#L48-L80)／[最良候補の近傍補間](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/dsputils.c#L566-L574)／[声道推定](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/layer1.c#L86-L123)

## 実装の意図と未測定の影響を分ける

上流の著者はLayer1を声門源と声道を分けて扱う表現として説明し、周期ごとの合成方法も紹介しています。Apronの保存形式はその周期ごとの制御用特徴を除外しています。著者の説明は表現の意図を示しますが、分離の生理学的な正しさや、この固定120録音での音質は証明しません。[上流README](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/README.md#L28-L36)／[周期ごとの合成](https://github.com/Sleepwalking/libllsm2/blob/d18cdf02b31819670e3bc23ead933ad9467da06d/README.md#L75-L81)／[Apronの保存形式](https://github.com/Hiroshiba/check-nonml-saikyo-vocoder/blob/700eb3866428a2528ee9f75bba3b833f495a47ca/vocoderbench/apron/storage.py#L16-L40)

既存の[確率的F0診断](../experiments/2026-10-20/probabilistic-pitch-diagnostic/README.md)のH0支持も、その調波モデル内の値です。生理的な有声・無声の校正済み確率とは扱いません。[F0の識別と声質の分離を区別した文献メモ](../experiments/2026-10-21/pml-ar1-three-atom-residual/followup-design/f0-identification-source-filter-scope-20261021.md)とも、この区別を揃えます。本記録は固定版のソースと既存文書の読取範囲に限り、音声の実行・比較・品質評価は含みません。
