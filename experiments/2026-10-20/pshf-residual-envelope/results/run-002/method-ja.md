対象は実際の終端 receipt と SHA-256/bytes を確認した保存配列のみ。合成・再観測ジョブ・ML・fixture は実行しない。
波形上の独立再計算: 全サンプル RMS/peak、候補−参照の直接差分 RMS/peak。正規化・clip・位置合わせなし。
固定イベントは元の onset JSON の半開区間。周期 Hann 80 samples、hop 16、FFT 128、中心 +40、片側 power / (128 sum(w²))、内部 bin は2倍。
局所帯域 [1500,3000), [3000,8000)、global [0,1000), [1000,4000), [4000,8000)。Nyquist は除く。
early/strong は区間内中心 power 平均。crossing は固定 P* の −30/−20/−10 dB を初めて満たす既存 search 中心。既存 ε=1e−12 と欠測理由を保持。
dB差は10 log10(power比)、RMSは20 log10(比)。ゼロをεで置換しない。未到達・欠測を0で埋めない。
rho は保存済み source/target 支持が一致する候補・PML・RAW_FULLの3者共通 measurable nodeだけ。8 bin保存profileの第1調波振幅を独立再計算して保存rhoと照合。波形からrho全工程の再推定はしない。
pitchは分離。各録音内の2 seed差を平均した後、5録音を等重み平均。2 seedまたは5録音が欠ければ集約値はnull。全5録音の個別値と全seed値をJSONに残す。
境界maskとearly/strong/searchの重複数を元の全評価区間のまま数える。サンプルmaskはsample座標、A maskは8 samples、L_truncatedは80 samplesの中心座標。境界は除外しない。
残差 x−m_hat の一致と、保存FIRによる残差→2回convolution→stride 8のA_resも独立再計算する。L_resは保存範囲とpayload一致を確認し再推定しない。
数値照合は最大絶対誤差と構造/状態不一致の記録であり、新規閾値による合否判定ではない。
時間: numerical_seconds は観測本体、fresh_VUV_seconds は別のREAPER取得、worker_wall_seconds は子プロセス起動/保存を含む。重複するため加算しない。
decode_secondsは各候補のspectral decode+synthesisであり、観測・出力保存・評価時間を含まない。過去参照時間とは実行環境/時期が異なり、速度優劣は断定しない。
power/rhoの増減は音質順位ではない。残差は不偏noise推定ではなく、時計同期はsource/target・event・周期AMの因果分離ではない。既存品質指標の欠測を改善・安全と扱わず、採用判断はしない。
