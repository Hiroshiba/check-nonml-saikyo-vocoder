# RAW_FULL の仕様

この変更ではRAW_FULLを16 kHzの研究baseに選定する。互換package名は `vocoderbench.pml`、版識別は `raw-full-fwcep60-v1`。旧PML独立復号モードはない。

公開 `encode(x, sr=16000, *, seed=DEFAULT_SEED, trace=None)` は連続F0・60 FWCEP・二値NMと、必須の `A_raw` / `L_raw` を持つ `RAWFullParameters` を返す。基礎解析直後、同じ原音と未編集F0でA/Lを計算する。16 kHzのみ。自動resampleはしない。

`save(params, path)` / `load(path)` のpathはdirectoryへ変更する。新規directoryに `parameters.pml` と非圧縮 `raw.npz` を保存し、両方が必須。上書きしない。途中失敗したdirectoryは完了扱いせず、別の保存先を使う。既存directoryも拒否する。これは測定driverのexist_ok=Trueより厳しい保存境界で、保存bytesと数値式の変更ではない。

旧単体PMLの自動変換・復号はできない。過去の特徴読取りには明示的に `vocoderbench.pml.storage.load_parameters` を使える。内部PML成分serializerのschemaは、その成分だけを示す。公開 `save_parameters` / `load_parameters` もRAW directory用であり、旧API名を旧形式の継続と解釈しない。

`decode(params, *, seed=None, trace=None)` は保存A/LとPML成分のみを参照する。seed省略時は保存seed。外部原音・事前波形は参照しない。

`edit_parameters(params, *, pitch_semitones=0, gain_db=0, time_scale=1)` は既存計算を保つ。FWCEP第0係数に `gain_db*ln(10)/20` を加え、F0に半音倍率を掛ける。保存A/Lは据え置き、編集後F0から再解析しない。累積±3半音・50<F0<700・time_scale=1限定。RAWのgain追従性能は未測定であり、厳密な波形倍率を保証しない。

A/Lを含む全表現の距離・補間・因子分離は未測定。従来のPML射影の再利用と、RAW全表現が良い特徴空間であるという主張は区別する。source周期由来の包絡が残り得るため、任意target Hzで周期性を独立制御できるとは言わない。48 kHz、確率F0/VUV、生物・音響モデルは本統合では解決していない。

測定sourceは2026-10-19純RTF run003のpure_rtf。feature計算はbyte同一、controller数値本体と既定edited合成経路を移植。非既定counterfactual分岐とcallbackなし旧復号を除いた。これは静的設計であり、統合packageが測定sourceとbyte同一、同じ速度、波形一致を実測済みという意味ではない。
