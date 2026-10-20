# RAW-only核心統合案 独立ソースレビュー

2026-10-19 UTC。対象はGit外の `raw-base-integration-proposal-20261019/proposed/`。比較元は同案の `base/`（記載commit d2fb3101898e91cec9377ceb28f08dd88e80af81）、および `raw-full-pure-rtf-job-v3-20261019/pure_rtf/`。計画、proposal.patch、REVIEW-ja.md、STATIC.jsonも読んだ。

## 結論

**指定された核心範囲に、修正必須の具体的blockerは見つからなかった。** 測定済みRAW_FULLの既定数値経路を保持するという静的説明と、読んだソース差分は整合する。公開APIのRAW必須化、gainのFWCEP経路、累積±3半音、source由来A/Lを維持したedited clock、旧PML単体拒否を確認した。

これは**核心のみの静的レビュー**。中央metadata・consumer・結果HTML等は未完了と明示されており、採用可能なbundle全体の承認ではない。統合版の実行、波形同一性、保存往復、性能・品質・gain追従を証明しない。追加計測やテストを採用gateとして要求しない。

## 実施範囲

cat/nl/grepによる読取り、diff/cmp、raw_featuresのsha256sumのみ。vocoderコード編集、package import、テスト、AST/lintの再実行、音声計算、Git操作はしていない。本レビュー文書のみ新規保存した。STATIC.jsonのlint成功は提案者の記録として読み、自分の実行結果とはしていない。

## 1. featureと基礎解析

- `codec.py:13–79` は旧encode本体の関数名変更とimport整理のみで、基礎解析の式・呼出し順は不変。測定sourceのpml/codec.pyと比較用base/codec.pyもdiffなし。
- 公開encodeは `codec.py:82–88` で基礎解析後に同じ入力xと新規・未編集params.f0をraw_featuresへ渡す。編集済みF0や別音声を参照する経路はない。
- `raw_features.py` は測定features.pyと同一hash：`d68ac4c3af3de5e13750104201b91ddae205921f3bbcd818a0371feb43efe174`。
- 65tap高域FIR、Gaussian、direct/same畳込み、8標本間隔A、source F0支持半径の5 ms L、境界支持、EPS、診断配列計算を維持。
- FWCEP、analysis、PDD、helpersはそれぞれbase・proposed・測定pml間でcmp一致。RAW backend側helpersと提案helpersも一致。共有部の差替えによる数値変更は見当たらない。

## 2. RAW controller・RNG・original D0

測定RAW backendとのsynthesis diffは、説明文、reference_f0/reference_modeと非既定source_value/source_mask分岐の削除、callback引数必須化、callback省略分岐の削除だけ。

- `pml_synthesis.py:34,232`：同じRandomState(seed)、同じpulse順・同じ長さでnormalを1回ずつ呼ぶ。追加乱数呼出しなし。
- `:251–259`：元の非変調gaussnoise4winのrFFTからD0を計算し、元GNをD0で割った後、同じnoiseとoriginal D0をcontrollerへ渡す。
- raw_noiseはrequireのローカル定義以外diffなし。a=sqrt((A+EPS)/(L+EPS))、両者小値ならratio=1、録音外a=1、rfft(a*noise)/D0を維持。D1等への再正規化なし。順序・dtype・D0・shape・有限性guardsも維持。
- mask拡張、nearest SPEC/NM row、最小位相、複素64パルス、複素べき、taper、OLAは変更なし。
- 必須noise_modifierを省略すれば呼出し時エラー、明示Noneでも旧復号分岐へ落ちない。公開decodeは常にRawNoiseControlを作る。任意callbackを内部関数へ直接渡すことはPython上可能だが、公開旧PMLモードや自動fallbackではない。

## 3. gain・pitch・二つのclock

経路を一続きで確認した：

`pml_cli.py --gain-db / methods.edit → 公開edit_parameters → parameters.py:144のFWCEP[:,0]加算 → dataclasses.replace → codec.py:109のdecode_log/exp → SPEC → RAW synthesis`。

- 加算式はgain_db*ln(10)/20で旧editorと同じ。波形末尾倍率、原音倍率再解析、別gain経路は追加されていない。
- replaceはRAWFullParameters型を保持し、A/Lを変更する指定はない。新インスタンスの検証でA/Lはfloat64コピーとなるが値は保持される。
- pitchは旧式の半音倍率をF0へ掛け、累積量を更新。editorとRAW型で累積±3を検証し、親型で50<F0<700を検証。time_scaleは1以外拒否。
- source F0で計算したA/Lは保存されたまま。decodeはそれを読み、synthesisは編集F0でmask境界・pulse時刻・noise支持・エネルギー補正を作る。Lは編集pulse時刻に対応する最寄り5 ms rowを使う。source時計へ戻す参照引数は除去されている。
- source由来のA/Lを任意target時計へ再マップする機能はない。RAWのgain追従や任意target Hzを保証するものではないという文書上の限定は適切。

## 4. 型・公開保存・legacy拒否

- `RAWFullParameters` は必須keyword-only A_raw/L_rawを持ち、親型のF0/FWCEP/NM検証に加え、A長ceil(N/8)、L形状F0と同じ、実数入力、float64化、finite/nonnegative、コピー・write=Falseを実施。
- `validate_raw` はdecode/edit/save境界でRAW型・A/L形状/精度/有限/非負・pitch制限を再確認する。単体PMLParametersを渡してもA/Lを補完せず拒否。
- `__init__.py` のsave/loadとsave_parameters/load_parametersはいずれもpayload.pyのdirectory境界へ向く。公開PML-only encoder/decode分岐なし。内部 `_analyze_components` と storage.load_parameters は基礎成分・履歴読取りであり、旧合成器の併存ではない。
- `payload.py:12–19` はRAW検証後、新規directoryを排他的作成し、parameters.pmlと非圧縮raw.npzを保存。既存directoryも拒否し、各ファイルもxb。
- `payload.py:22–36` はdirectoryと両ファイルを要求。PML成分の既存header/body長・checksum・padding・型検証を通し、NPZはallow_pickle=False、A/L項目集合、float64、再構築時の全形状/値検証を行う。欠落A/L、旧単一ファイル、不正payloadから旧PMLへfallbackしない。
- 保存成分serializerは冒頭説明のみ変更。測定形式との関係を破る新containerや圧縮は追加されていない。
- methods.scalarsはflatな全ndarrayを数えるためA/Lも含む。CLI seed/gain/pitch引数および計時外I/Oの構造も残る。

## 非blockerの境界・説明上の注意

1. 保存はtransactionalな一括commitではない。途中失敗後のdirectoryを完成扱いせず、別pathを使うという既存の明示契約に合う。自動rollback・再利用を保証しない。
2. 2ファイル間の録音identityやsourceとの結び付けを検証するmanifestはない。互換shapeの別録音A/Lへの入替えは数値・形状検証だけでは識別できない。測定payload_ioもidentity bindingをdriver側へ委ねており、今回は同じ最小形式を採用する計画なので新規blockerとはしない。「由来まで検証済み」とは説明しないこと。
3. write=Falseは通常利用での不意な変更防止であり、Pythonコードによる意図的な配列再書込み・属性改変まで防ぐ保証ではない。親成分の全検証はconstructor/load時が中心であり、validate_rawを任意に改変されたobjectの完全な再検証器と呼ばない。
4. native-only guardの撤去、RAW型へのコピー、公開seed/trace保持、境界検証追加、既存directory拒否は明示的API変更。測定run003と統合packageの全bytes・wall RTFが同じという主張には使えない。

## 採用bundleとの区別

今回の「核心blocker未検出」は中央metadata・consumer・全体docs・adoption HTML/decisionの完成を意味しない。旧labelでRAWを生成しないconsumer整理等の既知作業は別途必要。ここでは未完了項目を重複した新規核心欠陥として数えず、全体採用承認もしていない。
