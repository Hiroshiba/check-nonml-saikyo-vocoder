# 固定二候補BF 日本語HTML報告：独立静的監査

2026-10-20 UTC。対象 `pitch-fixed-bf-report-review-20261020/package`。原保存bytes/hash/gzip復元、保存表/行列/表示座標・HTMLリンクのみを確認。新BF/LSE/log/exp/統計・符号再集計、候補実行/import/testsなし。ブラウザ描画は別工程。

## 結論

**原本保持・数値転記の静的監査は通過。既知の本文修正2点を除き、新たな数値/原本blocking issueなし。** 公開前には下記本文修正と公開状態表示の整理が必要。実builder取込み・live到達性・描画の通過は本監査から主張しない。

## 公開前の文章修正

1. footerの「進行中の500組BMA」は現在の状態と合わないため削除/正確な履歴表現へ修正する。BMA条件を本診断で変更していないことと、別実験が現在進行中かは別。
2. 「履歴AとBでは有限窓数や正負の件数が違います」は、正負件数が**有限D比較に限る**ことを明記する。Aの+∞141/−∞64を含む全窓符号分布と混同させない。
3. 追加の公開時注意：listing.jsonの `publication_pending:true` とfooter「公開は親の最終照合後」は現候補の状態。live配布時にこのまま現在状態を表すと誤解されるため、作成時点の履歴へ限定するか公開状態に合わせて更新する。

## manifests・原本保持

ARTIFACT-MANIFESTとDISTRIBUTION-MANIFESTの掲載file集合・全bytes/SHAを独立照合し一致。publicは95files、最大2,789,723bytes（frame-results gzip）、全file10MiB未満。

byte-preservation.jsonの87対応すべてについて、公開bytes/SHA、gzip時の復元bytes/SHA、無変換時の元bytesを照合した。復元/無変換SHAは、既監査stage1三owner・stage2・符号sidecar・承認source/index/input関連のローカル原本hashと全件一致。producer自身の対応表同士だけで済ませていない。

stage1 journal/ledger/終了証拠、stage2 canonical/CSV/summary、sign sidecarと終了証拠、必要pinsが元の文字列・bytesを保つ。`.json.gz`にJSON Linesやstdout等を入れる場合の元形式はaudit説明と対応表に区別されている。科学source `.py`、`.pyc`、実装ZIP、その他ZIPはpublicにない。preservedの元ZIPはpublicと分離。

公開fileの最終suffixはhtml/css/csv/json/gz/md/svg。複合suffixにcandidate.json、log.json.gz、stderr.json.gz、stdout.json.gzを含む。危険な実行source形式は含まれないが、既存builderの実際の許可suffix規則/95file取込みは本担当環境で確認していない。最終登録時に既存builderの許可規則と照合し、取込み通過を確認すること。

## 表・行列・SVG

- ranges.csv全12行のmin_original/max_originalは元stage2 summaryの保存文字列と一致。
- HTML12行はranges.csvの6有効桁表示と完全一致。保存端点を表示丸めしただけで、新極値を探していない。
- 符号行列は3prior×3遷移=9組すべて、原sign-transitions.jsonの9セル/有限比較数と一致。static309（負154/正155）、A104（負95/正9）、B309（負159/正150）。保存strict_reversalsは各0、reversal_framesは各空。
- Aの非有限205窓は+∞→+∞141、−∞→−∞64として元sidecarと整合。Dの非有限と差のundefined、missing/差0を区別する本文は適切。
- SVG XMLの3本はstatic/A/Bの保存E−L範囲に一致。x軸−0.016〜0を280〜820へ線形表示変換した端点と0.001px丸め以内で一致。これは表示変換であり科学量の再計算ではない。
- 図はCI/真誤差保証でなく保存min/max、対象A有限104窓/staticとB各309窓と明記。個別BFの増加とpair Dの負方向変化を混同していない。

## リンク・科学的範囲

index.html/audit.htmlのローカルhref/src計98参照はpublic内実fileへ解決。外部既存音声比較3URLのlive到達性は未検証。

固定人工309窓、二候補f*/2f*、K1..10、6180参照と4180unique、三prior履歴固定、S/L/Eと差の向き、A80のAと履歴Aの区別、PML維持、品質/MOS未測定、全候補再探索/時間再追跡なし、非保証有限精度という制約は適切。重複参照を独立標本にしない。最大差から品質改善・採用へ飛躍していない。

「厳密な符号反転」は保存十進値の負↔正というsidecar上の定義で、数学的真値の符号保証ではない。本文は非保証参照/固定有限比較を明記しており、この意味で読む。将来の要約でもその限定を落とさないこと。

公開候補の一回完了・stage2 9.089秒等の履歴は既監査証拠と整合。候補report生成者のstatic PASSは描画やPages実ビルドのPASSではない。ここでもそれらを未確認として分離する。

機械可読要約: `pitch-fixed-bf-report-independent-audit-20261020.json`。

## 親のbuilder読取による追加停止線（10:13 UTC受領）

親が既存builder実装を確認し、public直下 `artifact-manifest.json` が必須、schemaはfilesをname/bytes/SHAのlistとすることが判明した。現publicにはこのmanifestがないため、**現版は公開登録未通過**。外側DISTRIBUTION-MANIFESTだけで代替しない。親から追加修正依頼済み。

親確認のallowed suffixは `.html/.json/.json.gz/.svg/.wav/.md/.csv/.png/.css`、各10MiB未満。現95filesのsuffixはこの集合へ適合する。manifest追加後のfile集合/全hashを最終版で再照合する。listing publication_pending削除・実created_at記録も依頼済み。上記87原値対応のbyte不変を維持した限定差分レビューを待つ。
