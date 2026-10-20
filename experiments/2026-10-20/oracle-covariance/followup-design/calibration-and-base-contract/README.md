# 雑音尺度の校正とPMLの位相契約（2026-10-20）

一次資料と現在のベース手法の契約を確認した3文書です。Library `libfile_50ff66e173b48191b3446c7db6feec09` v0の3文書とMANIFESTを原bytesで保存しています。

- [校正条件の一次資料確認](pitch-scale-calibration-primary-evidence-20261020.md)：著者実装の全録音RMS正規化、varSpeech、IG遷移候補、AR-MLの推定条件。
- [一次資料確認の独立レビュー](pitch-scale-calibration-primary-evidence-independent-review-20261020.md)：根拠と解釈の範囲の点検。
- [PMLの位相契約監査](pml-phase-contract-audit-20261020.md)：合成パルスの時刻と、公開保存される情報の範囲。

全録音のRMS正規化とvarSpeechの経験的正則化を、今回検討する外部校正済みのproper noise priorと同一視しません。IG遷移候補は原著では採用されておらず、AR-MLが同じ窓で行う最尤推定・BICによる選択とも別です。

PMLの合成パルス時刻は測定GCIやoracle位相ではなく、有声確率・候補分布・測定された位相原点は公開保存されません。既知のqと既知の一定F0を前提に、学習側のデータだけで位相原点を校正するための残る契約を文書上で検討しています。実装、数値priorの選択、測定、採用は未決定で、ベース手法はPMLを維持します。

関連する紙上検討は、[proper-scale導出](../../../pitch-history-contrast/research/proper-scale-colored-harmonic-evidence-20261020.md)と[独立数学レビュー](../../../pitch-history-contrast/research/proper-scale-colored-harmonic-evidence-independent-review-20261020.md)です。
