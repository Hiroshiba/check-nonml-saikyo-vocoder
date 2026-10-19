# PSHF5 保存結果の独立確認

終端状態: completed / 行状態: {'completed': 30}

数値は記述観測です。power/rho の増減で音質の優劣を判定しません。
欠測・未実行をゼロ扱いせず、全 seed の結果と照合誤差は analysis.json に保存しています。

## pitch +0

候補 − PML（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.00292769; 個別 [librispeech_1089-134686-0008: 0.00266873; librispeech_1188-133604-0003: 0.00366707; librispeech_121-121726-0012: 0.00287448; librispeech_1221-135766-0005: 0.00274872; librispeech_1089-134686-0032: 0.00267943]
- difference_peak: 全5平均 0.0730298; 個別 [librispeech_1089-134686-0008: 0.0702532; librispeech_1188-133604-0003: 0.0963132; librispeech_121-121726-0012: 0.0768576; librispeech_1221-135766-0005: 0.0697998; librispeech_1089-134686-0032: 0.0519253]
- global_rms_delta_db: 全5平均 -0.0130826; 個別 [librispeech_1089-134686-0008: 0.00445549; librispeech_1188-133604-0003: -0.0546564; librispeech_121-121726-0012: -0.0120378; librispeech_1221-135766-0005: -0.00231329; librispeech_1089-134686-0032: -0.000861092]
- global_peak_delta: 全5平均 -0.000409568; 個別 [librispeech_1089-134686-0008: 0.00031248; librispeech_1188-133604-0003: -0.00375921; librispeech_121-121726-0012: 0.00137738; librispeech_1221-135766-0005: 4.87223e-05; librispeech_1089-134686-0032: -2.72122e-05]
- source_common_rho_delta: 全5平均 0.0229814; 個別 [librispeech_1089-134686-0008: 0.0209245; librispeech_1188-133604-0003: 0.0396742; librispeech_121-121726-0012: 0.00371534; librispeech_1221-135766-0005: 0.00510429; librispeech_1089-134686-0032: 0.0454885]
- target_common_rho_delta: 全5平均 0.0229814; 個別 [librispeech_1089-134686-0008: 0.0209245; librispeech_1188-133604-0003: 0.0396742; librispeech_121-121726-0012: 0.00371534; librispeech_1221-135766-0005: 0.00510429; librispeech_1089-134686-0032: 0.0454885]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -20.0445/2.91017/8/3.5/2.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -15.5958/0.758983/8.5/3.5/0; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -11.5847/-1.24378/3/6/1; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -11.551/1.39116/1/5/1.5; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 1.24871/1.72116/-5.5/1/7; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -0.483034/1.10535/-1/1/6; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -2.50776/0.62809/0/2/7; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -16.3084/-0.326085/6/6/3.5; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -19.9971/0.690443/9/5/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -12.952/0.203882/6/1.5/6; crossing欠測 {}

候補 − RAW_FULL（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.000799006; 個別 [librispeech_1089-134686-0008: 0.000581176; librispeech_1188-133604-0003: 0.00103041; librispeech_121-121726-0012: 0.000963346; librispeech_1221-135766-0005: 0.000739443; librispeech_1089-134686-0032: 0.000680657]
- difference_peak: 全5平均 0.023355; 個別 [librispeech_1089-134686-0008: 0.0145563; librispeech_1188-133604-0003: 0.0432619; librispeech_121-121726-0012: 0.0271202; librispeech_1221-135766-0005: 0.0175195; librispeech_1089-134686-0032: 0.0143171]
- global_rms_delta_db: 全5平均 0.00200925; 個別 [librispeech_1089-134686-0008: 3.80294e-05; librispeech_1188-133604-0003: 0.00690871; librispeech_121-121726-0012: 0.00148518; librispeech_1221-135766-0005: 0.000263335; librispeech_1089-134686-0032: 0.00135101]
- global_peak_delta: 全5平均 0.000254345; 個別 [librispeech_1089-134686-0008: 1.97753e-05; librispeech_1188-133604-0003: 0.000320365; librispeech_121-121726-0012: 0.0011455; librispeech_1221-135766-0005: -0.000222014; librispeech_1089-134686-0032: 8.10227e-06]
- source_common_rho_delta: 全5平均 0.00159899; 個別 [librispeech_1089-134686-0008: 0.0030809; librispeech_1188-133604-0003: 0.00184381; librispeech_121-121726-0012: 0.00400639; librispeech_1221-135766-0005: 0.00240336; librispeech_1089-134686-0032: -0.00333952]
- target_common_rho_delta: 全5平均 0.00159899; 個別 [librispeech_1089-134686-0008: 0.0030809; librispeech_1188-133604-0003: 0.00184381; librispeech_121-121726-0012: 0.00400639; librispeech_1221-135766-0005: 0.00240336; librispeech_1089-134686-0032: -0.00333952]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.000545321/8.91665e-11/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -9.89068e-06/-4.07052e-11/0/0/0; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 2.38276/-0.0619621/3/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 2.68654/0.116812/-4.5/0/0; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 1.39359/-0.182371/-10/-6.5/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -0.501628/-0.165751/-8/-6/0; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.129073/0.00393019/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/6.13858e-05/0/0/0; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.558805/-0.142566/0/0/-0.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/0/0/0/0; crossing欠測 {}

## pitch -3

候補 − PML（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.00313576; 個別 [librispeech_1089-134686-0008: 0.00306648; librispeech_1188-133604-0003: 0.0044971; librispeech_121-121726-0012: 0.00279114; librispeech_1221-135766-0005: 0.00281292; librispeech_1089-134686-0032: 0.00251117]
- difference_peak: 全5平均 0.0789308; 個別 [librispeech_1089-134686-0008: 0.0769125; librispeech_1188-133604-0003: 0.111163; librispeech_121-121726-0012: 0.0738342; librispeech_1221-135766-0005: 0.0824524; librispeech_1089-134686-0032: 0.0502918]
- global_rms_delta_db: 全5平均 -0.00568312; 個別 [librispeech_1089-134686-0008: 0.00263747; librispeech_1188-133604-0003: -0.0309542; librispeech_121-121726-0012: -0.00179856; librispeech_1221-135766-0005: 3.32894e-05; librispeech_1089-134686-0032: 0.00166642]
- global_peak_delta: 全5平均 0.00369932; 個別 [librispeech_1089-134686-0008: 0.00082282; librispeech_1188-133604-0003: -0.00309393; librispeech_121-121726-0012: 0.020153; librispeech_1221-135766-0005: 0.0004012; librispeech_1089-134686-0032: 0.000213547]
- source_common_rho_delta: 全5平均 0.0377276; 個別 [librispeech_1089-134686-0008: 0.0405935; librispeech_1188-133604-0003: 0.0508211; librispeech_121-121726-0012: 0.0244871; librispeech_1221-135766-0005: 0.0154757; librispeech_1089-134686-0032: 0.0572606]
- target_common_rho_delta: 全5平均 0.0188939; 個別 [librispeech_1089-134686-0008: 0.0246155; librispeech_1188-133604-0003: 0.0323875; librispeech_121-121726-0012: -0.000749292; librispeech_1221-135766-0005: 0.00605441; librispeech_1089-134686-0032: 0.0321613]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -14.9803/1.09995/1/4.5/3; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -11.8557/0.187765/0.5/5.5/0.5; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -17.3128/0.675417/5/4/4; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -5.88899/1.08244/2/4.5/4; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -15.6064/-0.301855/1/3/11.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -13.5578/0.255489/1.5/2/9.5; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -0.217484/1.77642/0/1.5/-6.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -0.541341/-0.468052/2/2/1; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -18.7839/0.128443/4/5/5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -6.46434/-1.85818/4.5/1/1.5; crossing欠測 {}

候補 − RAW_FULL（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.000760822; 個別 [librispeech_1089-134686-0008: 0.000550481; librispeech_1188-133604-0003: 0.000947204; librispeech_121-121726-0012: 0.000741022; librispeech_1221-135766-0005: 0.000711993; librispeech_1089-134686-0032: 0.000853409]
- difference_peak: 全5平均 0.0199371; 個別 [librispeech_1089-134686-0008: 0.0114863; librispeech_1188-133604-0003: 0.0314727; librispeech_121-121726-0012: 0.0270321; librispeech_1221-135766-0005: 0.0129923; librispeech_1089-134686-0032: 0.0167023]
- global_rms_delta_db: 全5平均 0.000778136; 個別 [librispeech_1089-134686-0008: 0.0015058; librispeech_1188-133604-0003: 0.00229693; librispeech_121-121726-0012: -0.000511508; librispeech_1221-135766-0005: -0.000351145; librispeech_1089-134686-0032: 0.000950607]
- global_peak_delta: 全5平均 0.000422244; 個別 [librispeech_1089-134686-0008: 2.79985e-05; librispeech_1188-133604-0003: -0.000291532; librispeech_121-121726-0012: 0.00177304; librispeech_1221-135766-0005: 0.000595652; librispeech_1089-134686-0032: 6.06139e-06]
- source_common_rho_delta: 全5平均 -0.00156966; 個別 [librispeech_1089-134686-0008: -0.00470106; librispeech_1188-133604-0003: 0.000426752; librispeech_121-121726-0012: 0.00019776; librispeech_1221-135766-0005: -0.00110571; librispeech_1089-134686-0032: -0.00266605]
- target_common_rho_delta: 全5平均 -0.000796833; 個別 [librispeech_1089-134686-0008: -0.00464397; librispeech_1188-133604-0003: -0.00281136; librispeech_121-121726-0012: 0.00807591; librispeech_1221-135766-0005: -0.000997757; librispeech_1089-134686-0032: -0.00360699]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -3.30295e-06/0/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 3.80979e-06/0/0/0/0; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 3.14344/0.108939/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 1.6683/-0.0160555/-3/0/0; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 4.77905/0.267224/-9.5/-8.5/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 2.41781/0.0253208/-9.5/-9/0; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.0357232/0.0068826/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/-1.31244e-06/0/0/0; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.333735/-0.204088/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/0/0/0/0; crossing欠測 {}

## pitch +3

候補 − PML（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.00310982; 個別 [librispeech_1089-134686-0008: 0.00289654; librispeech_1188-133604-0003: 0.00409205; librispeech_121-121726-0012: 0.00327104; librispeech_1221-135766-0005: 0.00272785; librispeech_1089-134686-0032: 0.0025616]
- difference_peak: 全5平均 0.0749238; 個別 [librispeech_1089-134686-0008: 0.0556398; librispeech_1188-133604-0003: 0.129784; librispeech_121-121726-0012: 0.0814652; librispeech_1221-135766-0005: 0.0705131; librispeech_1089-134686-0032: 0.0372173]
- global_rms_delta_db: 全5平均 -0.00347127; 個別 [librispeech_1089-134686-0008: -0.0105078; librispeech_1188-133604-0003: -0.0110269; librispeech_121-121726-0012: -0.00423267; librispeech_1221-135766-0005: 0.0116114; librispeech_1089-134686-0032: -0.00320041]
- global_peak_delta: 全5平均 -0.00332746; 個別 [librispeech_1089-134686-0008: -0.000118838; librispeech_1188-133604-0003: 0.00134241; librispeech_121-121726-0012: -0.0167696; librispeech_1221-135766-0005: -0.000914015; librispeech_1089-134686-0032: -0.00017726]
- source_common_rho_delta: 全5平均 0.0333873; 個別 [librispeech_1089-134686-0008: 0.0392028; librispeech_1188-133604-0003: 0.0609391; librispeech_121-121726-0012: 0.0164752; librispeech_1221-135766-0005: 0.00700212; librispeech_1089-134686-0032: 0.0433173]
- target_common_rho_delta: 全5平均 0.0148908; 個別 [librispeech_1089-134686-0008: 0.0239483; librispeech_1188-133604-0003: 0.0156861; librispeech_121-121726-0012: 0.00585525; librispeech_1221-135766-0005: 0.000212443; librispeech_1089-134686-0032: 0.0287518]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -19.2026/0.841267/8.5/6/4.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -14.7792/0.258555/6/6/4; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -15.5337/-2.15139/2/5.5/9; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -16.831/0.71526/4/9/5.5; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -12.5702/0.319283/6/6/5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -10.9631/0.402597/6/4.5/5; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -0.364342/0.685838/0/0/0.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -16.3784/0.510048/5.5/6/-1; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -18.9361/1.59576/9/6/2.5; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -13.5035/-0.235831/0/5.5/7.5; crossing欠測 {}

候補 − RAW_FULL（各録音2 seed平均 → 5録音等重み）
- difference_rms: 全5平均 0.000840813; 個別 [librispeech_1089-134686-0008: 0.000461827; librispeech_1188-133604-0003: 0.00098721; librispeech_121-121726-0012: 0.00107567; librispeech_1221-135766-0005: 0.000708326; librispeech_1089-134686-0032: 0.000971037]
- difference_peak: 全5平均 0.0223686; 個別 [librispeech_1089-134686-0008: 0.0102344; librispeech_1188-133604-0003: 0.0423249; librispeech_121-121726-0012: 0.0225758; librispeech_1221-135766-0005: 0.0151513; librispeech_1089-134686-0032: 0.0215563]
- global_rms_delta_db: 全5平均 0.000828684; 個別 [librispeech_1089-134686-0008: 0.000150533; librispeech_1188-133604-0003: 0.000402925; librispeech_121-121726-0012: -0.000326353; librispeech_1221-135766-0005: 0.000478122; librispeech_1089-134686-0032: 0.0034382]
- global_peak_delta: 全5平均 -0.000319499; 個別 [librispeech_1089-134686-0008: -7.32113e-06; librispeech_1188-133604-0003: 0.000207703; librispeech_121-121726-0012: -0.00156191; librispeech_1221-135766-0005: -0.000221982; librispeech_1089-134686-0032: -1.39804e-05]
- source_common_rho_delta: 全5平均 0.000970949; 個別 [librispeech_1089-134686-0008: 0.0050953; librispeech_1188-133604-0003: 0.00178467; librispeech_121-121726-0012: 0.000725057; librispeech_1221-135766-0005: -0.000963221; librispeech_1089-134686-0032: -0.00178706]
- target_common_rho_delta: 全5平均 0.00137849; 個別 [librispeech_1089-134686-0008: 0.00104645; librispeech_1188-133604-0003: 0.00241294; librispeech_121-121726-0012: 0.0129634; librispeech_1221-135766-0005: 0.00109207; librispeech_1089-134686-0032: -0.0106224]
- librispeech_1089-134686-0008: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 2.00451e-05/6.19793e-11/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: -1.33958e-06/-8.61977e-12/0/0/0; crossing欠測 {}
- librispeech_1188-133604-0003: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 3.76512/-0.228912/-0.5/-3.5/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 5.31712/-0.0302228/-5.5/0/0; crossing欠測 {}
- librispeech_121-121726-0012: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 1.17973/-0.0799016/-8.5/-8.5/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 1.44327/-0.154147/-9/-8.5/0; crossing欠測 {}
- librispeech_1221-135766-0005: 帯域0 early/strong dB・−30/−20/−10 crossing ms: -0.00709061/0.00463184/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/8.61487e-06/0/0/0; crossing欠測 {}
- librispeech_1089-134686-0032: 帯域0 early/strong dB・−30/−20/−10 crossing ms: 0.132653/0.0618153/0/0/0; 帯域1 early/strong dB・−30/−20/−10 crossing ms: 0/0/0/0/0; crossing欠測 {}

## 診断と費用

- pitch +0: 候補decode 10本, 秒 min/mean/max=0.420512/0.799394/1.25994。範囲は spectral decode+synthesis のみ。
- pitch -3: 候補decode 10本, 秒 min/mean/max=0.354514/0.640987/1.10368。範囲は spectral decode+synthesis のみ。
- pitch +3: 候補decode 10本, 秒 min/mean/max=0.471835/0.926326/1.70064。範囲は spectral decode+synthesis のみ。
- librispeech_1089-134686-0008: completed; 時間 {"numerical_seconds": 5.209198014999856, "fresh_VUV_seconds": 0.11117514200304868, "worker_wall_seconds": 6.389001955998538}; 範囲 {"residual": [-0.14319969910398705, 0.1587589871548823], "A_res": [3.495835869648384e-09, 0.004604623903956474], "L_res": [8.24576574534507e-09, 0.0020934812046285137]}; 境界数 {"zero_extension_frame_support": 789, "highpass_boundary_support": 64, "gaussian_boundary_support": 96, "combined_filter_boundary_support": 160, "A_highpass_boundary_support": 8, "A_gaussian_boundary_support": 12, "A_combined_filter_boundary_support": 20}。イベント重複・照合誤差はJSON参照。
- librispeech_1188-133604-0003: completed; 時間 {"numerical_seconds": 3.170426087999658, "fresh_VUV_seconds": 0.12593657999968855, "worker_wall_seconds": 4.278297835997364}; 範囲 {"residual": [-0.12461181683693459, 0.15153625868243797], "A_res": [3.136230579208674e-09, 0.0036899465217926286], "L_res": [8.246158839958363e-09, 0.0023476161844591696]}; 境界数 {"zero_extension_frame_support": 0, "highpass_boundary_support": 64, "gaussian_boundary_support": 96, "combined_filter_boundary_support": 160, "A_highpass_boundary_support": 8, "A_gaussian_boundary_support": 12, "A_combined_filter_boundary_support": 20}。イベント重複・照合誤差はJSON参照。
- librispeech_121-121726-0012: completed; 時間 {"numerical_seconds": 2.324192091000441, "fresh_VUV_seconds": 0.13125820300047053, "worker_wall_seconds": 4.040659402999154}; 範囲 {"residual": [-0.543964021797054, 0.35533463123421444], "A_res": [4.670442824276926e-12, 0.03587983475254125], "L_res": [3.902495804904431e-11, 0.012621691428835468]}; 境界数 {"zero_extension_frame_support": 0, "highpass_boundary_support": 64, "gaussian_boundary_support": 96, "combined_filter_boundary_support": 160, "A_highpass_boundary_support": 8, "A_gaussian_boundary_support": 12, "A_combined_filter_boundary_support": 20}。イベント重複・照合誤差はJSON参照。
- librispeech_1221-135766-0005: completed; 時間 {"numerical_seconds": 2.4704081310046604, "fresh_VUV_seconds": 0.1310918040035176, "worker_wall_seconds": 3.676548196002841}; 範囲 {"residual": [-0.236083984375, 0.229888916015625], "A_res": [2.2827722913908208e-07, 0.01460718392913326], "L_res": [4.4223797880067446e-07, 0.008339512619397749]}; 境界数 {"zero_extension_frame_support": 0, "highpass_boundary_support": 64, "gaussian_boundary_support": 96, "combined_filter_boundary_support": 160, "A_highpass_boundary_support": 8, "A_gaussian_boundary_support": 12, "A_combined_filter_boundary_support": 20}。イベント重複・照合誤差はJSON参照。
- librispeech_1089-134686-0032: completed; 時間 {"numerical_seconds": 3.173505856997508, "fresh_VUV_seconds": 0.06600563300162321, "worker_wall_seconds": 4.282032244002039}; 範囲 {"residual": [-0.13971046161991407, 0.1404456403100074], "A_res": [3.517512462330289e-09, 0.0013901047549754746], "L_res": [9.377890425903769e-09, 0.0003627854692945796]}; 境界数 {"zero_extension_frame_support": 0, "highpass_boundary_support": 64, "gaussian_boundary_support": 96, "combined_filter_boundary_support": 160, "A_highpass_boundary_support": 8, "A_gaussian_boundary_support": 12, "A_combined_filter_boundary_support": 20}。イベント重複・照合誤差はJSON参照。

## 正確な方法と解釈範囲

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
