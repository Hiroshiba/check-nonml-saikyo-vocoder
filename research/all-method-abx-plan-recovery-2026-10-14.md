# 復旧後のABX公式ラベル取得前契約

これは未実行のABX補助集合の取得・選定入口を補完する計画である。主test-clean120、独立train、VCTK、人間評定群の既存契約や選定規則は変更しない。

- `all_metrics_datasets_abx_contract.py plan` で公式abxLS ZIP URL、ラベルmember、固定主120manifest SHA、関係source SHA、除外規則、SALT、各条件20,000三つ組上限を取得前に固定する。
- `labels` は既存Range取得を使用し、ZIP索引のSHAを本体取得前に追加固定する。公式 `test-clean/triphone-test-clean.item` とREADME/ライセンスのみ取得し、原本バイトSHAを選定前に記録する。ZIP全体は保存しない。
- ラベル選定は既存式のまま、主120の先頭最大6秒へ公式全triphone区間を結合する。同じ左右文脈でA/Bの中心音素が異なり、XはAと同じ中心音素を持つ三つ組をwithin/across別に選ぶ。SALTは `all-method-metrics-abxls-20261014/`。各条件で `SHA256(salt+a+'|'+b+'|'+x)` 昇順の先頭最大20,000件。録音、話者、件数を旧実績から補わない。
- onset/offset、話者、無音・雑音phoneの既存除外規則を維持する。音声特徴、方式出力、評価値を選定に使わず、再alignment・無音除去・正規化もしない。
- 公式WAVと固定LibriSpeech全長PCMの照合は従来通り主120全件を対象とする。公式未収録等の失敗も記録するが、後続ABXに必要なPCM同一性は今回の三つ組で実際に使う録音だけに要求する。未使用の欠測を成功へ変えず、ABXの必要分母に追加しない。
- 他の3補助集合の凍結済みsource契約を壊さないため、共通datasets_contractや既存計画文書を変更せず独立契約にする。ABX source変更の静的レビュー終了後にのみ契約固定・取得・選定を正式実行する。動作確認・推論・テストは行わない。
