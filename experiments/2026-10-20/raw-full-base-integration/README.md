# RAW_FULLを研究baseへ選定する変更

固定120録音・40話者の保存比較と解析・復号RTFを踏まえ、この変更ではRAW_FULLを16 kHz研究baseに選定する。採用判断は事後的な工学的交換条件であり、全軸優越・音質非劣性・任意音高・48 kHz対応を証明するものではない。

結果と判断は [選定レポート](../../../research/raw-full-adoption-selection-2026-10-20/index.html)、実装の版は BASELINE.json に記録する。旧科学結果の識別と adoption_evaluation_complete=false は変更しない。

reviews/ には核心数値経路、consumerと旧報告表示、結果・文書の独立静的レビューを記録した。レビュー時点で見つかった表示の漏れは修正後に再読し、未解決blockerがないことを記録している。履歴段階の「提案」表記はその時点の状態であり、動作・品質の追加実測を意味しない。

最終束ねでAST、実プロジェクト設定 E4/E7/E9/F・py312 のキャッシュ使用Ruff、最大343行を確認した。package import、テスト、smoke、回帰、保存往復、音声合成、追加指標計測、build_site予行は行っていない。測定済み数値経路を保持する静的統合であり、新しい統合packageのbyte一致や追加実行を主張しない。
