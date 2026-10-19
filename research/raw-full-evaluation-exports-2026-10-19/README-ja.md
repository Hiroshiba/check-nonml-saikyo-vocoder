# RAW_FULL評価：120録音の保存数値原表

固定120録音・40話者、PML / RAW_FULL × 音高0・−3・+3 × 2 seed（1,440条件）の保存済み数値を収録した、未集計の原表です。RAW_FULLの採用、品質優越、最終順位を示しません。再合成・品質再計測は行わず、保存JSONの整合性を照合して投影しました。元波形・モデルの内容を再検証した成果物ではありません。

`public-exports.zip` は3,930,511 bytes、SHA256は `aa15ada9dadc8728c29b3de904fe3b0fb6da4a29ec92910b0faa085dc1582f18` です。ZIPの内容は保存時から変更していません。

| 内容 | manifestのSHA256 |
|---|---|
| scalar/manifest.json | `785321ad9884278005d7e8dd960f5ed6495b3e9de58238d0994b017a2cf95fab` |
| signal/manifest.json | `0fd1a923362378246a6178464927e606cbb620bdf6cb86550de8f200a8ec6cb9` |
| cost/manifest.json | `3b089ff367f6fe364ce311beb17e4210d2d4e7c7f6554c1f5731c9a0eb60a85f` |

ZIP直下の `bundle-manifest.json` と各manifestに、ファイル別bytes・SHA256・件数を記録しています。

- 品質表は12,960指標セル＋原音MOS 120セル。available 7,500、not_applicable 4,800、unavailable 780です。欠測780は公式抜粋正解未準備によるものです。適用外には未編集条件の相対F0/missと、編集条件のnative補助指標を含みます。null・欠測・適用外をゼロ誤差や無害と解釈しません。
- 全10chunkを提供済みです。信号表のgeneral（120録音）とlegacy（固定5録音）は別集合で、母数や率を混ぜません。legacy表も全予定キーを保持し、対象外は適用外です。
- 費用表のinstrumented decode計時は編集・補間・合成・監査処理等を含み、純粋decoder速度ではありません。PML encoder、pure decoder、総encoder RTFは未測定です。保存payload読込、解析、書込を区別し、過去runの時間と混ぜません。
- 元音声、NPY、モデル、私有設定・auditは収録していません。この原表の保存は最終HTMLレポートやPages登録ではありません。
