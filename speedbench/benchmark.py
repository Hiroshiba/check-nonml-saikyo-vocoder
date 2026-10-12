"""Serial CPU timings of seven published implementations, with strict checkpoint loading."""
from __future__ import annotations
import argparse, ast, ctypes as ct, gc, hashlib, json, math, os, pathlib, platform
import re, resource, shutil, statistics, subprocess, sys, time, traceback
from types import SimpleNamespace
import numpy as np
import soundfile as sf
import scipy.signal
import torch
OUT=pathlib.Path('speed-results').resolve()
SRC=pathlib.Path('/tmp/speed-src')
MODELS=pathlib.Path('/tmp/speed-models')
NAMES=['dac','facodec','hifiglot','golf','sifigan','llsm','magphase']

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def total_params(*models):return sum(p.numel() for m in models for p in m.parameters())

def build_dac(src,models,out):
    sys.path.insert(0,str(src/'dac'))
    import dac
    path=dac.utils.download(model_type='44khz');model=dac.DAC.load(path).eval()
    def enc(x,p):return model.encode(model.preprocess(torch.from_numpy(x.astype(np.float32))[None,None],model.sample_rate))[0]
    return SimpleNamespace(sr=model.sample_rate,encode=enc,decode=model.decode,info=dict(variant='44khz official pretrained; full RVQ',parameter_count=total_params(model),checkpoint_sha256=digest(path),n_codebooks=model.n_codebooks))

def build_facodec(src,models,out):
    sys.path.insert(0,str(src/'facodec'))
    from ns3_codec import FACodecEncoder,FACodecDecoder
    ep=models/'naturalspeech3_facodec/ns3_facodec_encoder.bin';dp=models/'naturalspeech3_facodec/ns3_facodec_decoder.bin'
    enc=FACodecEncoder(ngf=32,up_ratios=[2,4,5,5],out_channels=256)
    dec=FACodecDecoder(in_channels=256,upsample_initial_channel=1024,ngf=32,up_ratios=[5,5,4,2],vq_num_q_c=2,vq_num_q_p=1,vq_num_q_r=3,vq_dim=256,codebook_dim=8,codebook_size_prosody=10,codebook_size_content=10,codebook_size_residual=10,use_gr_x_timbre=True,use_gr_residual_f0=True,use_gr_residual_phone=True)
    enc.load_state_dict(torch.load(ep,map_location='cpu',weights_only=False));dec.load_state_dict(torch.load(dp,map_location='cpu',weights_only=False));enc.eval();dec.eval()
    def encode(x,p):
        x=torch.from_numpy(x.astype(np.float32))[None,None];x=torch.nn.functional.pad(x,(0,(-x.shape[-1])%200))
        z,codes,_,quantized,spk=dec(enc(x),eval_vq=False,vq=True)
        return z,spk
    return SimpleNamespace(sr=16000,encode=encode,decode=lambda z:dec.inference(*z),info=dict(variant='FACodec v1 all six codebooks incl. residual',parameter_count=total_params(enc,dec),checkpoint_sha256=[digest(ep),digest(dp)]))

def build_hifiglot(src,models,out):
    sys.path.insert(0,str(src/'hifiglot/src'))
    from neural_formant_synthesis.third_party.hifi_gan.env import AttrDict
    from neural_formant_synthesis.feature_extraction import feature_extractor,Normaliser,MedianPool1d
    from neural_formant_synthesis.models import SourceFilterFormantSynthesisGenerator
    from safetensors.torch import load_file
    h=AttrDict(json.loads((src/'hifiglot/configs/hifiglot/config_hifigan.json').read_text()))
    fm=AttrDict(json.loads((src/'hifiglot/configs/hifiglot/config_feature_map.json').read_text()))
    path=next((models/'HiFi-Glot/hifiglot').rglob('model.safetensors'))
    model=SourceFilterFormantSynthesisGenerator(fm_config=fm,g_config=h,pretrained_fm=None,freeze_fm=False)
    model.load_state_dict(load_file(str(path)));model.eval()
    extractor=feature_extractor(sr=h.sampling_rate,window_samples=h.win_size,step_samples=h.hop_size,formant_ceiling=10000,max_formants=4)
    mf=MedianPool1d(kernel_size=7,stride=1,padding=0,same=True);norm=Normaliser()
    def encode(x,p):
        formants,energy,centroid,tilt,pitch,voicing=extractor(torch.from_numpy(x))
        formants=mf(formants.T.unsqueeze(1)).squeeze(1).T;pitch=pitch.squeeze(0);voicing=voicing.squeeze(0);linear_pitch=pitch
        pitch,formants,tilt,centroid,energy=norm(pitch,formants,tilt,centroid,energy)
        feat=torch.cat((pitch.unsqueeze(1),formants,tilt.unsqueeze(1),centroid.unsqueeze(1),energy.unsqueeze(1),voicing.unsqueeze(1)),dim=-1).T.float()[None]
        return feat,linear_pitch[None]
    return SimpleNamespace(sr=h.sampling_rate,encode=encode,decode=lambda z:model(*z)[0],info=dict(variant='official HiFi-Glot44.1k inference recipe',parameter_count=total_params(model),checkpoint=str(path),checkpoint_sha256=digest(path)))

def build_golf(src,models,out):
    import yaml,pyworld
    from importlib import import_module
    sys.path.insert(0,str(src/'golf'))
    from ltng.ae import VoiceAutoEncoder
    from models.audiotensor import AudioTensor
    cfg=src/'golf/ckpts/interspeech24/golf-ff/config.yaml';config=yaml.safe_load(cfg.read_text())['model']['init_args']
    def obj(c):
        if isinstance(c,list):return [obj(v) for v in c]
        if not isinstance(c,dict):return c
        if 'class_path' in c:
            mod,cls=c['class_path'].rsplit('.',1)
            return getattr(import_module(mod),cls)(**obj(c.get('init_args',{})))
        return {k:obj(v) for k,v in c.items()}
    path=next(cfg.parent.rglob('*.ckpt'));model=VoiceAutoEncoder(**obj(config))
    model.load_state_dict(torch.load(path,map_location='cpu',weights_only=False)['state_dict']);model.eval();sr=model.sample_rate
    adapter=SimpleNamespace(sr=sr,info=dict(variant='GOLF-ff Interspeech24; WORLD DIO F0 included',parameter_count=total_params(model),checkpoint=str(path),checkpoint_sha256=digest(path)),stage_times={})
    def encode(x,p):
        t=time.perf_counter();f0,_=pyworld.dio(x,sr,f0_floor=60,f0_ceil=1000,channels_in_octave=2,frame_period=5)
        f0=AudioTensor(torch.tensor(f0,dtype=torch.float32)[None],sr//200);adapter.stage_times['external_f0_s']=time.perf_counter()-t
        a=AudioTensor(torch.tensor(x,dtype=torch.float32)[None]);params=model.encoder(a,f0=f0)
        params.pop('f0',None);params['phase']=torch.where(f0==0,150,f0)/sr
        if 'voicing_logits' in params:params['voicing']=torch.sigmoid(params.pop('voicing_logits'))
        return params
    adapter.encode=encode;adapter.decode=lambda z:model.decoder(**z)
    return adapter

def build_sifigan(src,models,out):
    import yaml,joblib,pyworld as pw,pysptk
    from hydra.utils import instantiate
    from omegaconf import OmegaConf
    sys.path.insert(0,str(src/'sifigan'))
    from sifigan.bin.anasyn import convert_continuos_f0,ALPHA
    from sifigan.utils.features import SignalGenerator,dilated_factor
    path=next(p for p in models.rglob('*.pkl') if 'checkpoint' in p.name);stats=next(models.rglob('*.joblib'))
    base=yaml.safe_load((src/'sifigan/sifigan/bin/config/anasyn.yaml').read_text());base.pop('defaults',None)
    gen=yaml.safe_load((src/'sifigan/sifigan/bin/config/generator/sifigan.yaml').read_text());base['generator']=gen;base['f0_floor']=60;base['f0_ceil']=1000
    config=OmegaConf.create(base);model=instantiate(config.generator)
    state=torch.load(path,map_location='cpu',weights_only=False);model.load_state_dict(state['model']['generator']);model.remove_weight_norm();model.eval()
    scaler=joblib.load(stats)
    sg=SignalGenerator(sample_rate=config.sample_rate,hop_size=int(config.sample_rate*config.frame_period*.001),sine_amp=config.sine_amp,noise_amp=config.noise_amp,signal_types=config.signal_types)
    adapter=SimpleNamespace(sr=config.sample_rate,info=dict(variant='published24k multispeaker speech+singing; WORLD Harvest included',parameter_count=total_params(model),checkpoint=str(path),checkpoint_sha256=digest(path),stats_sha256=digest(stats),config=OmegaConf.to_container(config,resolve=True)),stage_times={})
    def encode(x,p):
        t0=time.perf_counter();f0,t=pw.harvest(x,config.sample_rate,f0_floor=60,f0_ceil=1000,frame_period=config.frame_period);adapter.stage_times['external_f0_s']=time.perf_counter()-t0
        sp=pw.cheaptrick(x,f0,t,config.sample_rate);ap=pw.d4c(x,f0,t,config.sample_rate)
        mcep=pysptk.sp2mc(sp,order=config.mcep_dim,alpha=ALPHA[config.sample_rate]);mcap=pysptk.sp2mc(ap,order=config.mcap_dim,alpha=ALPHA[config.sample_rate]);bap=pw.code_aperiodicity(ap,config.sample_rate)
        uv,cf0=convert_continuos_f0(f0);uv=uv[:,None];f0=f0[:,None];cf0=cf0[:,None]
        features=dict(uv=uv,f0=f0,cf0=cf0,mcep=mcep,mcap=mcap,bap=bap);c=np.concatenate([scaler[k].transform(features[k]) for k in config.aux_feats],axis=1)
        dfs=[np.repeat(dilated_factor(cf0,config.sample_rate,df),us) for df,us in zip(config.dense_factors,np.cumprod(config.generator.upsample_scales))]
        cf0=torch.tensor(cf0,dtype=torch.float32).view(1,1,-1);c=torch.tensor(c,dtype=torch.float32).T[None];dfs=[torch.tensor(df,dtype=torch.float32).view(1,1,-1) for df in dfs]
        return cf0,c,dfs
    adapter.encode=encode;adapter.decode=lambda z:model(sg(z[0]),z[1],z[2])[0]
    return adapter

def build_llsm(src,models,out):
    import pyworld as pw
    class Output(ct.Structure):
        _fields_=[('ny',ct.c_int),('fs',ct.c_float),('y',ct.POINTER(ct.c_float)),('y_sin',ct.POINTER(ct.c_float)),('y_noise',ct.POINTER(ct.c_float))]
    lib=ct.CDLL('/tmp/speed-native/libllsm_speed.so');arr=np.ctypeslib.ndpointer(dtype=np.float32,ndim=1,flags='C_CONTIGUOUS')
    lib.speed_encode.argtypes=[arr,ct.c_int,ct.c_float,arr,ct.c_int,ct.c_int];lib.speed_encode.restype=ct.c_void_p
    lib.speed_decode.argtypes=[ct.c_void_p,ct.c_float,ct.c_int];lib.speed_decode.restype=ct.POINTER(Output)
    lib.llsm_delete_chunk.argtypes=[ct.c_void_p];lib.llsm_delete_output.argtypes=[ct.POINTER(Output)]
    a=SimpleNamespace(sr=24000,info=dict(variant='LLSM2 Layer0 peak-picking; maxnhar400 npsd128 hop5ms; DIO+StoneMask',parameter_count=0,compile='Release -Ofast float32'),stage_times={})
    def encode(x,p):
        t=time.perf_counter();f0,ts=pw.dio(x,a.sr,f0_floor=60,f0_ceil=1000,frame_period=5);f0=pw.stonemask(x,f0,ts,a.sr);a.stage_times['external_f0_s']=time.perf_counter()-t
        z=lib.speed_encode(x.astype(np.float32),len(x),a.sr,f0.astype(np.float32),len(f0),0)
        if not z:raise RuntimeError('llsm_analyze returned NULL')
        return z
    def decode(z):
        p=lib.speed_decode(z,a.sr,0)
        if not p:raise RuntimeError('llsm_synthesize returned NULL')
        y=np.ctypeslib.as_array(p.contents.y,shape=(p.contents.ny,)).copy();lib.llsm_delete_output(p);return y
    a.encode=encode;a.decode=decode;a.release=lib.llsm_delete_chunk
    return a

def build_magphase(src,models,out):
    sys.path.insert(0,'/tmp/magphase-port/src')
    import magphase as mp
    def encode(x,p):return mp.analysis_compressed(str(p),mag_dim=100,phase_dim=45,b_const_rate=False)
    def decode(z):return mp.synthesis_from_compressed(*z[:4],z[5],b_const_rate=False,b_out_hpf=False)
    return SimpleNamespace(sr=48000,encode=encode,decode=decode,info=dict(variant='MagPhase2 compressed100/45/45 pitch-synchronous; SPTK3.9+REAPER; Python3 compatibility patch',parameter_count=0,analysis_file_io_included=True))

def prepare_native():
    subprocess.run(['sudo','apt-get','update','-qq'],check=False);subprocess.run(['sudo','apt-get','install','-y','-qq','sptk'],check=False)
    native=pathlib.Path('/tmp/speed-native');native.mkdir(exist_ok=True);results=[]
    def run(cmd,cwd=None):print('BUILD',cmd,flush=True);subprocess.run(cmd,cwd=cwd,check=True)
    try:
        run(['make','CONFIG=Release','-j2'],SRC/'ciglet');run(['make','install',f'PREFIX={native}'],SRC/'ciglet')
        run(['make','CONFIG=Release',f'CIGLET_PREFIX={native}','-j2'],SRC/'llsm')
        wrapper=native/'wrapper.c';wrapper.write_text('#include "llsm.h"\nllsm_chunk* speed_encode(float* x,int nx,float fs,float* f0,int nfrm,int l1){llsm_aoptions* a=llsm_create_aoptions();a->thop=.005;a->maxnhar=400;a->maxnhar_e=5;a->npsd=128;a->hm_method=LLSM_AOPTION_HMPP;llsm_chunk* c=llsm_analyze(a,x,nx,fs,f0,nfrm,0);llsm_delete_aoptions(a);if(l1&&c)llsm_chunk_tolayer1(c,2048);return c;}\nllsm_output* speed_decode(llsm_chunk* c,float fs,int l1){llsm_soptions* s=llsm_create_soptions(fs);s->use_l1=l1;llsm_output* o=llsm_synthesize(s,c);llsm_delete_soptions(s);return o;}\n')
        run(['gcc','-shared','-fPIC','-fopenmp','-Ofast','-DFP_TYPE=float','-I'+str(SRC/'llsm'),str(wrapper),'-Wl,--whole-archive',str(SRC/'llsm/build/libllsm2.a'),str(SRC/'ciglet/libciglet.a'),'-Wl,--no-whole-archive','-lm','-o',str(native/'libllsm_speed.so')]);results.append(dict(method='llsm',status='built'))
    except Exception:traceback.print_exc();results.append(dict(method='llsm',error=traceback.format_exc()))
    try:
        run(['cmake','-S',str(SRC/'reaper'),'-B',str(SRC/'reaper/build'),'-DCMAKE_BUILD_TYPE=Release']);run(['cmake','--build',str(SRC/'reaper/build'),'-j2'])
        port=pathlib.Path('/tmp/magphase-port');shutil.copytree(SRC/'magphase',port,dirs_exist_ok=True);bins=port/'tools/bin';bins.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/'reaper/build/reaper',bins/'reaper')
        for p in pathlib.Path('/usr/lib/sptk/bin').glob('*'):
            if not (bins/p.name).exists():(bins/p.name).symlink_to(p)
        if not (bins/'mcep').exists():raise FileNotFoundError('SPTK3.9 mcep missing')
        files=list((port/'src').glob('*.py'));run([sys.executable,'-m','lib2to3','-w','-n']+list(map(str,files)))
        class Div(ast.NodeTransformer):
            def visit_BinOp(self,n):
                self.generic_visit(n)
                return ast.copy_location(ast.Call(func=ast.Name(id='old_div',ctx=ast.Load()),args=[n.left,n.right],keywords=[]),n) if isinstance(n.op,ast.Div) else n
        for p in files:
            txt=re.sub(r'np\.(int|float|complex|bool)\b',lambda m:m[1],p.read_text())
            for w in ['hanning','hamming','blackman']:txt=txt.replace('signal.'+w,'signal.windows.'+('hann' if w=='hanning' else w))
            tree=ast.fix_missing_locations(Div().visit(ast.parse(txt)));p.write_text('from past.utils import old_div\n'+ast.unparse(tree)+'\n')
        results.append(dict(method='magphase',status='built',patch='lib2to3, Python2 scalar division, numpy/scipy removed aliases; no algorithm replacement'))
    except Exception:traceback.print_exc();results.append(dict(method='magphase',error=traceback.format_exc()))
    (OUT/'native_build.json').write_text(json.dumps(results,indent=2))

def prepare_inputs():
    inputs=[]
    for ident,path,credit in [('arctic',SRC/'llsm/test/arctic_a0001.wav','CMU ARCTIC; libllsm2 test audio'),('ready',SRC/'llsm/test/are-you-ready.wav','unfa, Freesound258342; libllsm2 test audio')]:
        x,sr=sf.read(path,dtype='float64',always_2d=True);x=x.mean(axis=1)[:int(sr*5)];assert np.max(np.abs(x))>1e-6
        p=OUT/f'input_{ident}.wav';sf.write(p,x,sr,subtype='FLOAT')
        inputs.append(dict(id=ident,path=str(p),sample_rate=sr,n_samples=len(x),seconds=len(x)/sr,source=str(path),source_sha256=digest(path),pcm_sha256=hashlib.sha256(x.tobytes()).hexdigest(),credit=credit))
    (OUT/'inputs.json').write_text(json.dumps(inputs,indent=2))

def worker(name):
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(20261012);np.random.seed(20261012)
    affinity=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{affinity[0]})
    meta=dict(method=name,status='failed',device='cpu',threads=1,affinity=[affinity[0]],torch=torch.__version__,python=sys.version,rows=[],warmup_rows=[]);dest=OUT/f'{name}.json'
    try:
        start=time.perf_counter();adapter=globals()['build_'+name](SRC,MODELS,OUT);meta['initialization_seconds']=time.perf_counter()-start;meta.update(adapter.info)
        for spec in json.loads((OUT/'inputs.json').read_text()):
            x,sr=sf.read(spec['path'],dtype='float64');target_sr=adapter.sr;g=math.gcd(sr,target_sr);r0=time.perf_counter()
            if sr!=target_sr:x=scipy.signal.resample_poly(x,target_sr//g,sr//g)
            meta.setdefault('resampling',[]).append(dict(input=spec['id'],seconds=time.perf_counter()-r0))
            path=OUT/f'input_{spec["id"]}_{target_sr}.wav';sf.write(path,x,target_sr,subtype='PCM_16');x,_=sf.read(path,dtype='float64');x=np.ascontiguousarray(x);duration=len(x)/target_sr
            for rep in range(-2,5):
                gc.collect()
                with torch.inference_mode():
                    t0=time.perf_counter();z=adapter.encode(x,path);t1=time.perf_counter();y=adapter.decode(z);t2=time.perf_counter()
                if hasattr(y,'as_tensor'):y=y.as_tensor()
                if isinstance(y,torch.Tensor):y=y.detach().cpu().numpy()
                y=np.asarray(y).reshape(-1)
                if not len(y) or not np.all(np.isfinite(y)):raise ValueError('Output is empty or non-finite')
                rms=float(np.sqrt(np.mean(y.astype(np.float64)**2)))
                if rms<1e-9:raise ValueError('Output is effectively silent')
                row=dict(input=spec['id'],repeat=rep,duration=duration,sample_rate=target_sr,analysis_s=t1-t0,synthesis_s=t2-t1,total_s=t2-t0,analysis_rtf=(t1-t0)/duration,synthesis_rtf=(t2-t1)/duration,rtf=(t2-t0)/duration,output_samples=len(y),output_duration=len(y)/target_sr,rms=rms,peak=float(np.max(np.abs(y))))
                if hasattr(adapter,'stage_times'):row['stages']=dict(adapter.stage_times)
                if hasattr(adapter,'release'):adapter.release(z)
                (meta['rows'] if rep>=0 else meta['warmup_rows']).append(row);print('MEASUREMENT',name,json.dumps(row),flush=True)
                meta['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024;dest.write_text(json.dumps(meta,indent=2))
                if rep==0:sf.write(OUT/f'{name}_{spec["id"]}.wav',y,target_sr,subtype='FLOAT')
                del z,y
        meta['status']='measured';meta['summary']={k:dict(median=statistics.median([r[k] for r in meta['rows']]),min=min(r[k] for r in meta['rows']),max=max(r[k] for r in meta['rows'])) for k in ['analysis_rtf','synthesis_rtf','rtf']}
    except Exception:meta['error']=traceback.format_exc();traceback.print_exc()
    meta['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024;dest.write_text(json.dumps(meta,indent=2))
    print('FINAL',name,json.dumps({k:v for k,v in meta.items() if k not in ('rows','warmup_rows')}),flush=True)
    return 0 if meta['status']=='measured' else 1

def main():
    OUT.mkdir(exist_ok=True,parents=True);ap=argparse.ArgumentParser();ap.add_argument('--method',choices=NAMES);args=ap.parse_args()
    if args.method:return worker(args.method)
    prepare_native();sys.path.insert(0,str(SRC/'dac'))
    try:
        import dac
        dac.utils.download(model_type='44khz')
    except Exception:traceback.print_exc()
    prepare_inputs();(OUT/'environment.json').write_text(json.dumps(dict(platform=platform.platform(),python=sys.version,affinity=sorted(os.sched_getaffinity(0)),cpu_count=os.cpu_count(),run_id=os.environ.get('GITHUB_RUN_ID'),commit=os.environ.get('GITHUB_SHA')),indent=2))
    status=[]
    for name in NAMES:
        print('BEGIN_METHOD',name,flush=True);log=OUT/f'{name}.log'
        try:
            with log.open('w') as f:p=subprocess.run([sys.executable,__file__,'--method',name],stdout=f,stderr=subprocess.STDOUT,timeout=900)
            status.append(dict(method=name,returncode=p.returncode))
        except subprocess.TimeoutExpired:status.append(dict(method=name,error='900-second method timeout'))
        print(log.read_text()[-12000:],flush=True)
    (OUT/'process_status.json').write_text(json.dumps(status,indent=2));summary=[]
    for name in NAMES:
        f=OUT/f'{name}.json';summary.append(json.loads(f.read_text()) if f.exists() else dict(method=name,status='failed',error='No measurement file'))
    (OUT/'all_results.json').write_text(json.dumps(summary,indent=2));print('BENCHMARK_SUMMARY',json.dumps([{k:v for k,v in r.items() if k not in ('rows','warmup_rows')} for r in summary]),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
