"""人工診断信号と入力条件を生成する。品質の合否判定・自然音声の代用ではない。"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.io import wavfile

from ..logging_utils import LoggedArgumentParser, run_cli


def generate(output):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    sr = 48000
    n = 57600
    t = np.arange(n)/sr

    def js(name, data):
        (root/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        return name

    def wav(name, audio):
        wavfile.write(root/name, sr, np.asarray(audio, dtype=np.float32))
        return name

    def sha(name):
        return hashlib.sha256((root/name).read_bytes()).hexdigest()

    x = .2*np.sin(2*np.pi*220*t)
    wav('original.wav', x)
    cents = 300*t/1.2
    freq = 220*2**(cents/1200)
    wav('pitch-ramp.wav', .2*np.sin(2*np.pi*np.cumsum(freq)/sr))
    wav('gain-ramp.wav', x*10**((6*t/1.2)/20))
    for db in (-1,0,.1,.5,1,3,6):
        wav(f'gain{db:g}.wav',x*10**(db/20))
    rng=np.random.default_rng(42)
    noise=.02*rng.normal(size=n)
    f=np.fft.rfftfreq(n,1/sr)
    slope_filter=(np.maximum(f,40)/1000)**(3/(20*np.log10(2)))
    filtered=np.fft.irfft(np.fft.rfft(noise)*slope_filter,n=n)
    wav('noise.wav',noise)
    wav('tilted.wav',filtered)
    events=[.2,.6,1.0]
    mapa=[0,.4,.8,1.2]
    mapb=[0,.5,.9,1.4]
    ytime=np.arange(round(sr*1.4))/sr
    expected=np.interp(events,mapa,mapb)
    wav('events.wav', sum(.3*np.exp(-((t-z)/.003)**2) for z in events))
    wav('events-warp.wav',sum(.3*np.exp(-((ytime-z)/.003)**2) for z in expected))
    wav('events-missing.wav',sum(.3*np.exp(-((ytime-z)/.003)**2) for z in expected[:2]))
    wav('silence.wav',np.zeros(n))
    wav('short.wav',x[:20])
    wav('mismatch.wav',x[:-1])
    wav('nonfinite.wav',np.r_[np.nan,x[1:]])
    for alpha in (0,.5,1):
        wav(f'alpha{alpha:g}.wav',.2*10**((alpha*3)/20)*np.sin(2*np.pi*(220*2**(alpha*6/12))*t))
        np.save(root/f'alpha{alpha:g}.npy',np.array([alpha]))

    items=[]
    for s in range(3):
        for phone in range(2):
            for repeat in range(2):
                key=f's{s}p{phone}r{repeat}'
                features=np.tile(np.array([1.+phone,2.-phone,1.+repeat]),(3,1))
                np.save(root/f'{key}.npy',features)
                items.append({'id':key,'features':key+'.npy','speaker':f'speaker{s}', 'phone':str(phone),
                              'context':'a_t','utterance_id':key,'split':'evaluation' if s==2 else 'train',
                              'targets':{'f0_hz':100+30*features[0,0], 'level_db':2*features[0,2]}})
    triplets=[]
    for s in range(3):
        for p in range(2):
            for condition in ('within_speaker','across_speaker'):
                other=s if condition=='within_speaker' else (s+1)%3
                triplets.append({'a':f's{s}p{p}r0','b':f's{s}p{1-p}r0',
                                 'x':f's{other}p{p}r1','condition':condition})
    js('features.json',{'representation':'analytic-vector-probe-not-vocoder','extraction_revision':'probe-v1',
                       'target_units':{'f0_hz':'Hz','level_db':'dB'},'items':items,'triplets':triplets})
    np.save(root/'tie.npy',np.ones((3,3)))
    js('ties.json',{'representation':'collapsed-probe','extraction_revision':'probe-v1',
                   'items':[{**i,'features':'tie.npy'} for i in items], 'triplets':triplets})

    def transcript(name, output, output_text, reftext='alpha beta'):
        return js(name,{'evidence_kind':'synthetic_token_fixture','recognizer':'none-symbolic-calculation-only',
              'recognizer_revision':'none','language':'en','normalization':'nfkc_casefold_whitespace','word_tokenization':'whitespace',
              'reference_audio_sha256':sha('original.wav'),'output_audio_sha256':sha(output),
              'truth':'alpha beta','reference_text':reftext,'output_text':output_text})
    transcript('transcript.json','gain3.wav','alpha gamma')
    transcript('transcript-zero.json','original.wav','alpha beta')
    transcript('transcript-high-error.json','gain3.wav','wrong words','wrong words')
    transcript('transcript-bad-hash.json','gain3.wav','alpha gamma')
    bad=json.loads((root/'transcript-bad-hash.json').read_text())
    bad['output_audio_sha256']='0'*64
    js('transcript-bad-hash.json',bad)

    jobs=[]
    def job(metric,id,**kw):
        jobs.append({'id':id,'metric':metric,'method':'analytic-probe','case':'probe-'+metric,'condition':'declared-operation',
                     'seed':0,'speaker':'artificial-1','language':'not_applicable','style':'synthetic','kind':'artificial_probe',**kw})

    job('incremental_content','content',reference='original.wav',output='gain3.wav',transcripts='transcript.json',maximum_reference_cer=.25)
    job('auditory_local','erb-identity',reference='original.wav',output='original.wav',method='identity')
    job('auditory_local','erb-gain',reference='original.wav',output='gain3.wav',intervals=[{'start':.3,'end':.5,'label':'既知区間'}])
    job('pitch_tracking','pitch-dynamic',reference='original.wav',output='pitch-ramp.wav',target_cents={'times':[0,1.2],'values':[0,300]})
    job('gain_tracking','gain-dynamic',reference='original.wav',output='gain-ramp.wav',target_gain_db={'times':[0,1.2],'values':[0,6]})
    job('local_time','local-events',reference='events.wav',output='events-warp.wav',probe_kind='isolated_energy_events',
        time_map={'reference_seconds':mapa,'output_seconds':mapb},event_seconds=events,search_half_width_seconds=.05,minimum_peak_ratio=.2)
    job('timbre_tracking','spectral-slope',reference='noise.wav',output='tilted.wav',low_hz=300,high_hz=3000,target_delta_db_per_octave=3)
    job('interference','gain-interference',low_hz=300,high_hz=3000,
        attribute_scales={'pitch_cents':100,'level_db':1,'slope_db_per_octave':1,'duration_seconds':.1},
        sweeps=[{'control':'gain','control_unit':'dB','delta':1,'control_scale':1,'minus':'gain-1.wav','plus':'gain1.wav',
          'expected_response':{'pitch_cents':0,'level_db':1,'slope_db_per_octave':0,'duration_seconds':0}}])
    job('quality_curve','content-only-curve',reference='original.wav',control='gain',control_unit='dB',maximum_reference_cer=.25,
        points=[{'amount':0,'output':'original.wav','transcripts':'transcript-zero.json'},
                {'amount':3,'output':'gain3.wav','transcripts':'transcript.json'}])
    job('phoneme_abx','abx',dataset='features.json',feature_weights=[1,1,1],distance='euclidean',distance_calibration_id='probe-fixed')
    job('phoneme_abx','abx-ties',dataset='ties.json',feature_weights=[1,1,1],distance='angular',distance_calibration_id='probe-fixed',condition='ties')
    job('attribute_access','readout',dataset='features.json',targets=['f0_hz','level_db'],ridge_alpha=1e-8)
    job('interpolation','interpolation',endpoint_relation='same_phone',interpolation_rule='analytic sine F0 in log Hz and amplitude in dB; not encoder interpolation',
        low_hz=300,high_hz=3000,attribute_tolerances={'pitch_cents':1,'level_db':.01,'slope_db_per_octave':.01,'duration_seconds':1/sr},points=[{'alpha':a,'output':f'alpha{a:g}.wav','feature_artifact':f'alpha{a:g}.npy'} for a in (0,.5,1)])
    rob=[]
    for level in (0,.1,.5):
        np.save(root/f'perturb{level:g}.npy',np.array([220.,.2*10**(level/20)]))
        rob.append({'amount':level,'output':f'gain{level:g}.wav','feature_artifact':f'perturb{level:g}.npy'})
    job('robustness','rough-input',reference='original.wav',perturbation='analytic amplitude parameter error',perturbation_unit='dB',decoder_revision='analytic-sine-v1',points=rob)
    ratepoints=[]
    for bits in (8,12,16):
        q=np.rint((np.clip(x,-1,1)+1)*(2**bits-1)/2).astype(np.uint32)
        restored=q.astype(float)*2/(2**bits-1)-1
        payload=np.packbits(((q[:,None]>>np.arange(bits-1,-1,-1))&1).astype(np.uint8),axis=None).tobytes()
        header=json.dumps({'bits':bits,'sample_rate':sr,'samples':n,'scale':1}).encode()
        (root/f'packed{bits}.bin').write_bytes(len(header).to_bytes(4,'little')+header+payload)
        wav(f'quant{bits}.wav',restored)
        ratepoints.append({'configuration':str(bits)+'bit','output':f'quant{bits}.wav','feature_artifact':f'packed{bits}.bin'})
    job('information_rate','bits',reference='original.wav',serialization_rule='unsigned fixed-width waveform quantization; JSON length/header plus big-endian packed sample codes',
        decoder_revision='analytic-waveform-storage-probe-v1-not-a-vocoder',points=ratepoints)
    js('manifest.json',{'schema_version':1,'baseline_method':'identity',
        'scope':'既知の人工信号と記号列による動作確認。実ボコーダー・自然音声・ASR・MOS・人間評定の評価ではありません。', 'jobs':jobs})
    failures=[]
    for id,metric,kw in [
        ('length','gain_tracking',{'reference':'original.wav','output':'mismatch.wav','target_gain_db':0}),
        ('silence','pitch_tracking',{'reference':'silence.wav','output':'silence.wav','target_cents':0}),
        ('short','auditory_local',{'reference':'short.wav','output':'short.wav'}),
        ('nonfinite','gain_tracking',{'reference':'original.wav','output':'nonfinite.wav','target_gain_db':0}),
        ('missing','gain_tracking',{'reference':'original.wav','output':'missing.wav','target_gain_db':0}),
        ('hash','incremental_content',{'reference':'original.wav','output':'gain3.wav','transcripts':'transcript-bad-hash.json','maximum_reference_cer':.25}),
        ('inaccurate-asr','incremental_content',{'reference':'original.wav','output':'gain3.wav','transcripts':'transcript-high-error.json','maximum_reference_cer':.25}),
    ]:
        failures.append({'id':id,'metric':metric,'case':id,'condition':id,'method':'invalid-probe','seed':0,
                        'speaker':'artificial-1','language':'none','style':'synthetic','kind':'artificial_probe',**kw})
    js('failure-manifest.json',{'schema_version':1,'baseline_method':'unselected','scope':'異常・定義域外の保存確認。品質の合否判定ではない。','jobs':failures})
    print(root, 'jobs',len(jobs))


def main():
    parser = LoggedArgumentParser(description="指標計測用の人工入力を新しいフォルダへ生成する")
    parser.add_argument("--output", required=True, type=Path)
    generate(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(run_cli(main, "assessment-probes"))
